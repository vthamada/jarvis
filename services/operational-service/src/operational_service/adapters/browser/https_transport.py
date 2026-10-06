"""Single numeric IPv4 connection with verified, nonblocking hostname TLS.

No DNS, proxy discovery, connection retry, environment mutation, credentials or
public TLS override. Internal seams support local synthetic TLS fixtures only.
"""

from __future__ import annotations

import errno
import ipaddress
import math
import select
import socket
import ssl
from typing import Callable

from .https_contracts import HttpsReadRefused, validate_hostname, validate_pin

POLL_SECONDS = 0.1
MAX_RECEIVE_BYTES = 65536
_PENDING = frozenset({
    errno.EINPROGRESS, errno.EWOULDBLOCK, errno.EALREADY, errno.EINTR,
    getattr(errno, "WSAEWOULDBLOCK", 10035), getattr(errno, "WSAEINPROGRESS", 10036),
    getattr(errno, "WSAEALREADY", 10037), getattr(errno, "WSAEINTR", 10004),
})
_CONTROL_CODES = frozenset({"cancelled", "deadline_exceeded", "invalid_clock"})


def _dial_address(pin: str) -> tuple[str, int]:
    return pin, 443


def _client_context() -> ssl.SSLContext:
    # Unlike create_default_context(), this does not activate SSLKEYLOGFILE.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    context.load_default_certs(ssl.Purpose.SERVER_AUTH)
    return context


class PinnedTlsConnection:
    """One owned socket, one handshake, one deadline inherited from the reader.

    check() returns remaining positive seconds or raises an enumerated refusal.
    receive() is a stream read and can return fewer bytes than its maximum.
    """

    def __init__(self, hostname: str, ipv4_pin: str, check: Callable[[], float]):
        self._hostname = hostname
        self._pin = ipv4_pin
        self._check_callback = check
        self._raw = None
        self._stream = None
        self._entered = False
        self._closed = False
        self._bound = None
        self._phase = "https_connect_refused"
        self._validate(hostname, ipv4_pin, check)

    @staticmethod
    def _validate(hostname, pin, check_callback) -> None:
        try:
            validate_hostname(hostname)
            validate_pin(pin)
            if not callable(check_callback):
                raise ValueError("invalid_check")
        except Exception:
            raise HttpsReadRefused("invalid_https_transport") from None

    def _check(self) -> float:
        try:
            hostname, pin, callback = self._bound
            if (self._hostname != hostname or self._pin != pin
                    or self._check_callback is not callback):
                raise ValueError("transport_rebound")
            remaining = callback()
            if (self._hostname != hostname or self._pin != pin
                    or self._check_callback is not callback):
                raise ValueError("transport_rebound")
            if type(remaining) not in (float, int) or not math.isfinite(remaining):
                raise ValueError("invalid_check")
            if remaining <= 0:
                raise HttpsReadRefused("deadline_exceeded")
            return min(remaining, POLL_SECONDS)
        except HttpsReadRefused as error:
            code = error.code if (type(error.code) is str and error.code in _CONTROL_CODES) \
                else "invalid_https_transport"
            raise HttpsReadRefused(code) from None
        except Exception:
            raise HttpsReadRefused("invalid_https_transport") from None

    def _wait(self, stream, *, reading: bool = False, writing: bool = False) -> None:
        while True:
            interval = self._check()
            readable, writable, exceptional = select.select(
                [stream] if reading else [], [stream] if writing else [], [stream], interval,
            )
            self._check()
            if exceptional:
                raise HttpsReadRefused(self._phase)
            if readable or writable:
                return

    def _peer(self, stream, address: tuple[str, int]) -> None:
        self._check()
        peer = stream.getpeername()
        self._check()
        if type(peer) is not tuple or len(peer) != 2 or peer != address:
            raise HttpsReadRefused(self._phase)

    def _close(self) -> bool:
        # Revoke references first, even when a socket's close operation fails.
        stream, raw = self._stream, self._raw
        self._stream = None
        self._raw = None
        self._closed = True
        closed = True
        for owned in (stream, raw):
            if owned is not None:
                try:
                    owned.close()
                except Exception:
                    closed = False
        return closed

    def __enter__(self) -> PinnedTlsConnection:
        if self._entered or self._closed:
            raise HttpsReadRefused("invalid_https_transport")
        self._entered = True
        try:
            # Capture before invoking any control callback; no callback can
            # rebind the destination, SNI name or deadline of this connection.
            hostname, pin, callback = self._hostname, self._pin, self._check_callback
            self._bound = (hostname, pin, callback)
            self._validate(hostname, pin, callback)
            self._check()
            address = _dial_address(pin)
            # Even a test seam must never pass a hostname into connect_ex.
            if (type(address) is not tuple or len(address) != 2
                    or type(address[0]) is not str
                    or str(ipaddress.IPv4Address(address[0])) != address[0]
                    or type(address[1]) is not int or not 1 <= address[1] <= 65535):
                raise HttpsReadRefused("invalid_https_transport")
            self._check()
            self._raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._check()
            self._raw.setblocking(False)
            self._check()
            connected = self._raw.connect_ex(address)
            self._check()
            if type(connected) is not int or (connected != 0 and connected not in _PENDING):
                raise HttpsReadRefused("https_connect_refused")
            while connected != 0:
                self._wait(self._raw, writing=True)
                self._check()
                connected = self._raw.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                self._check()
                if type(connected) is not int or (connected != 0 and connected not in _PENDING):
                    raise HttpsReadRefused("https_connect_refused")
            self._peer(self._raw, address)
            self._phase = "https_tls_refused"
            self._check()
            context = _client_context()
            self._check()
            if (context.verify_mode != ssl.CERT_REQUIRED or context.check_hostname is not True
                    or context.minimum_version < ssl.TLSVersion.TLSv1_2
                    or context.keylog_filename is not None):
                raise HttpsReadRefused("https_tls_refused")
            self._stream = context.wrap_socket(
                self._raw, server_hostname=hostname, do_handshake_on_connect=False,
                suppress_ragged_eofs=True,
            )
            self._check()
            self._stream.setblocking(False)
            self._check()
            while True:
                self._check()
                try:
                    self._stream.do_handshake()
                except ssl.SSLWantReadError:
                    self._wait(self._stream, reading=True)
                    continue
                except ssl.SSLWantWriteError:
                    self._wait(self._stream, writing=True)
                    continue
                self._check()
                break
            self._peer(self._stream, address)
            self._phase = "https_io_refused"
            self._check()
            return self
        except HttpsReadRefused:
            self._close()
            raise
        except Exception:
            self._close()
            raise HttpsReadRefused(self._phase) from None
        except BaseException:
            self._close()
            raise

    def __exit__(self, kind, error, traceback) -> bool:
        closed = self._close()
        if kind is None:
            if not closed:
                raise HttpsReadRefused("https_io_refused")
            self._check()
        return False

    def send(self, data: bytes) -> None:
        try:
            if self._closed or self._stream is None or type(data) is not bytes:
                raise HttpsReadRefused("invalid_https_transport")
            pending = memoryview(data)
            self._check()
            while pending:
                self._check()
                try:
                    written = self._stream.send(pending)
                except ssl.SSLWantReadError:
                    self._wait(self._stream, reading=True)
                    continue
                except ssl.SSLWantWriteError:
                    self._wait(self._stream, writing=True)
                    continue
                self._check()
                if type(written) is not int or not 0 < written <= len(pending):
                    raise HttpsReadRefused("https_io_refused")
                pending = pending[written:]
            self._check()
        except HttpsReadRefused:
            self._close()
            raise
        except Exception:
            self._close()
            raise HttpsReadRefused("https_io_refused") from None
        except BaseException:
            self._close()
            raise

    def receive(self, maximum: int) -> bytes:
        try:
            if (self._closed or self._stream is None or type(maximum) is not int
                    or maximum < 1):
                raise HttpsReadRefused("invalid_https_transport")
            while True:
                self._check()
                try:
                    received = self._stream.recv(min(maximum, MAX_RECEIVE_BYTES))
                except ssl.SSLWantReadError:
                    self._wait(self._stream, reading=True)
                    continue
                except ssl.SSLWantWriteError:
                    self._wait(self._stream, writing=True)
                    continue
                self._check()
                if type(received) is not bytes or len(received) > min(maximum, MAX_RECEIVE_BYTES):
                    raise HttpsReadRefused("https_io_refused")
                return received
        except HttpsReadRefused:
            self._close()
            raise
        except Exception:
            self._close()
            raise HttpsReadRefused("https_io_refused") from None
        except BaseException:
            self._close()
            raise
