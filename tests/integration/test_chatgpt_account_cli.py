"""Real standalone CLI + loopback + RSA + private store; synthetic HTTPS only."""

from __future__ import annotations

import builtins
import json
import os
import socket
import ssl
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest
from inference_service.credential_store import SiwcCredentialStore
from inference_service.oauth_http import SiwcHttpsClient
from inference_service.siwc_contracts import ISSUER, REQUESTED_SCOPES
from inference_service.siwc_session import SiwcSession

from apps.jarvis_console import cli

ROOT = Path(__file__).resolve().parents[2]
CLIENT = "oaiapp_cli_private_fixture"
SUBJECT = "cli-private-subject"
EMAIL = "cli-private@example.invalid"
ACCESS = "cli-private-access"
REFRESH = "cli-private-refresh"
MODEL = "cli-account-model"


class Response:
    status = 200

    def __init__(self, value):
        self.body = json.dumps(value).encode()
        self.closed = False

    def getheader(self, name, default=None):
        headers = {"Content-Type": "application/json", "Content-Encoding": "identity"}
        return headers.get(name, default)

    def read1(self, size):
        chunk, self.body = self.body[:size], self.body[size:]
        return chunk

    def close(self):
        self.closed = True


class Connection:
    def __init__(self, wire, host):
        self.wire, self.host = wire, host
        self.sock = self
        self.closed = False

    def connect(self):
        pass

    def settimeout(self, value):
        assert value > 0

    def request(self, method, path, *, body, headers):
        self.wire.requests.append((self.host, method, path, body, headers))
        if path == "/.well-known/openid-configuration":
            value = {"issuer": ISSUER, "authorization_endpoint": ISSUER + "/api/accounts/authorize",
                     "token_endpoint": ISSUER + "/api/accounts/oauth/token",
                     "jwks_uri": ISSUER + "/.well-known/jwks.json"}
        elif path == "/.well-known/jwks.json":
            value = self.wire.jwks
        elif path == "/api/accounts/oauth/token":
            value = self.wire.tokens
            assert "Authorization" not in headers
        else:
            assert path == "/v1/models" and method == "GET"
            assert self.host == "api.openai.com"
            value = {"models": [{"visibility": "list", "slug": MODEL,
                                 "display_name": self.wire.display_name},
                                {"visibility": "hidden", "slug": "not-visible"}]}
        assert path != "/v1/responses"
        self.response = Response(value)

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


class Wire:
    def __init__(self, signing):
        self.jwt, self.key, self.jwks = signing
        self.tokens, self.requests, self.connections = {}, [], []
        self.urls, self.threads, self.callback_errors, self.callback_responses = [], [], [], []
        self.invalid_jwt = False
        self.browser_success = True
        self.display_name = "Account model"

    def factory(self, host, *, port, timeout, context):
        assert host in {"auth.openai.com", "api.openai.com"} and port == 443
        assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
        assert timeout > 0
        connection = Connection(self, host)
        self.connections.append(connection)
        return connection

    def browser(self, url, *, new, autoraise):
        assert new == 1 and autoraise is True
        assert url.startswith(ISSUER + "/api/accounts/authorize?")
        self.urls.append(url)
        if not self.browser_success:
            return False
        query = parse_qs(urlsplit(url).query)
        now = int(time.time())
        claims = {"iss": ISSUER, "aud": CLIENT, "sub": SUBJECT, "email": EMAIL,
                  "nonce": "invalid-nonce" if self.invalid_jwt else query["nonce"][0],
                  "iat": now - 30, "exp": now + 3600}
        self.tokens = {"access_token": ACCESS, "refresh_token": REFRESH, "token_type": "Bearer",
                       "scope": " ".join(REQUESTED_SCOPES), "expires_in": 3600,
                       "id_token": self.jwt.encode(claims, self.key, algorithm="RS256",
                                                   headers={"kid": "cli-synthetic-key"})}
        redirect = urlsplit(query["redirect_uri"][0])
        target = redirect.path + "?" + urlencode({"state": query["state"][0],
                                                   "code": "cli-private-code", "client_id": CLIENT})

        def send_callback():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
                    connection.settimeout(5)
                    connection.connect(("127.0.0.1", redirect.port))
                    connection.sendall((f"GET {target} HTTP/1.1\r\nHost: {redirect.netloc}"
                                        "\r\n\r\n").encode("ascii"))
                    response = bytearray()
                    while True:
                        block = connection.recv(4096)
                        if not block:
                            break
                        response.extend(block)
                    self.callback_responses.append(bytes(response))
            except Exception as error:
                self.callback_errors.append(type(error).__name__)

        thread = threading.Thread(target=send_callback)
        self.threads.append(thread)
        thread.start()
        return True

    def finish(self):
        for thread in self.threads:
            thread.join(timeout=6)
            assert not thread.is_alive()
        assert self.callback_errors == []
        assert all(response.startswith(b"HTTP/1.1 200") for response in self.callback_responses)


@pytest.fixture(scope="module")
def signing():
    jwt = pytest.importorskip("jwt")
    rsa = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.rsa")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    public.update(kid="cli-synthetic-key", alg="RS256", use="sig", key_ops=["verify"])
    return jwt, key, {"keys": [public]}


@pytest.fixture(autouse=True)
def no_core(monkeypatch):
    def refused(*args, **kwargs):
        pytest.fail("standalone provider CLI constructed Core")

    monkeypatch.setattr(cli.JarvisConsole, "build", refused)


@pytest.fixture
def setup(tmp_path, monkeypatch, signing):
    wire = Wire(signing)
    assert SiwcSession is not None  # Import the stable class before replacing its CLI factory.

    def no_external(*args, **kwargs):
        pytest.fail("CLI integration attempted external HTTPS")

    class InjectedClient(SiwcHttpsClient):
        def __init__(self, **kwargs):
            super().__init__(**kwargs, connection_factory=wire.factory)

    monkeypatch.setattr("inference_service.oauth_http.http.client.HTTPSConnection", no_external)
    monkeypatch.setattr("inference_service.oauth_http.SiwcHttpsClient", InjectedClient)
    monkeypatch.setattr("apps.jarvis_console.chatgpt_account_cli.webbrowser.open", wire.browser)
    yield tmp_path / "private-provider", wire
    wire.finish()


def invoke(capsys, directory, action, *extra, authorized=True):
    args = ["chatgpt-account", "--format", "json", "--credential-dir", str(directory),
            "--action", action, "--timeout-seconds", "5", *extra]
    if authorized:
        args.append("--authorized")
    code = cli.main(args)
    captured = capsys.readouterr()
    for private in (CLIENT, SUBJECT, EMAIL, ACCESS, REFRESH,
                    "cli-private-code", "nonce=", "state="):
        assert private not in captured.out + captured.err
    if code == 0:
        assert captured.err == ""
        envelope = json.loads(captured.out)
        assert envelope["command_id"] == "chatgpt-account" and envelope["redacted"] is False
        return code, json.loads(envelope["outputs"][0])
    assert captured.out == ""
    return code, json.loads(captured.err)


def connect(capsys, setup):
    directory, wire = setup
    code, product = invoke(capsys, directory, "connect")
    wire.finish()
    assert code == 0, {"browser_calls": len(wire.urls),
                       "callbacks": len(wire.callback_responses),
                       "requests": [(item[0], item[1], item[2]) for item in wire.requests],
                       "private_files": sorted(path.name for path in directory.iterdir())}
    assert product["operator_authenticated"] is False and product["authority"] == "none"
    assert product["runtime_capability_promoted"] is False
    return directory, wire, product["profile_ref"]


def test_cli_connect_profiles_catalog_refresh_restart_shared_host(setup, capsys):
    directory, wire, profile = connect(capsys, setup)
    store = SiwcCredentialStore(directory, authorized=True)
    host = store.host_id()
    inventory = {path.name: path.read_bytes() for path in directory.iterdir()}
    code, profiles = invoke(capsys, directory, "profiles")
    assert code == 0 and profiles["profile_refs"] == [profile]
    assert profiles["network_used"] is False
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == inventory
    count = len(wire.requests)
    code, catalog = invoke(capsys, directory, "catalog", "--profile-ref", profile)
    assert code == 0 and catalog["models"] == [{"slug": MODEL, "display_name": "Account model"}]
    assert len(wire.requests) > count
    wire.tokens = {"access_token": "cli-rotated-access", "refresh_token": "cli-rotated-refresh",
                   "token_type": "Bearer", "expires_in": 3600}
    code, refresh = invoke(capsys, directory, "refresh", "--profile-ref", profile)
    assert code == 0 and refresh["operator_authenticated"] is False
    renewed = SiwcCredentialStore(directory, authorized=True).load_profile(profile)
    assert renewed.access_token == "cli-rotated-access"
    assert renewed.refresh_token == "cli-rotated-refresh" and store.host_id() == host
    code, _ = invoke(capsys, directory, "catalog", "--profile-ref", profile)
    assert code == 0
    if os.name == "nt":
        for path in directory.glob("*.sealed"):
            data = path.read_bytes()
            assert data.startswith(b"jarvis-siwc-dpapi-v1\n")
            for private in (ACCESS, REFRESH, SUBJECT, "cli-rotated-access", "cli-rotated-refresh"):
                assert private.encode() not in data
    assert all(connection.closed and connection.response.closed for connection in wire.connections)


def test_returning_login_uses_registration_same_host_and_hint(setup, capsys):
    directory, wire, profile = connect(capsys, setup)
    host = SiwcCredentialStore(directory, authorized=True).host_id()
    assert invoke(capsys, directory, "connect", "--profile-ref", profile)[0] == 0
    wire.finish()
    query = parse_qs(urlsplit(wire.urls[-1]).query)
    assert query["client_id"] == [CLIENT] and query["ext_agent_host_id"] == [host]
    assert query["login_hint"] == [EMAIL] and "id_token_hint" in query
    assert "agent_name_hint" not in query


@pytest.mark.parametrize("action", ["connect", "profiles", "catalog", "refresh"])
def test_default_opt_in_off_no_import_storage_socket_browser_or_network(
    tmp_path, monkeypatch, capsys, action
):
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.startswith("inference_service"):
            pytest.fail("unauthorized handler imported OAuth runtime")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    directory = tmp_path / "must-not-exist"
    code, _ = invoke(capsys, directory, action, authorized=False)
    assert code == 2 and not directory.exists()


def test_existing_profiles_missing_store_no_initialization(tmp_path, capsys):
    directory = tmp_path / "missing"
    assert invoke(capsys, directory, "profiles")[0] == 2
    assert not directory.exists()


def test_optional_jwt_missing_before_directory_or_browser(tmp_path, monkeypatch, capsys):
    original = __import__("importlib.util").util.find_spec
    monkeypatch.setattr("apps.jarvis_console.chatgpt_account_cli.importlib.util.find_spec",
                        lambda name: None if name == "jwt" else original(name))
    directory = tmp_path / "missing"
    assert invoke(capsys, directory, "connect")[0] == 2
    assert not directory.exists()


def test_invalid_jwt_no_profile_written(setup, capsys):
    directory, wire = setup
    wire.invalid_jwt = True
    assert invoke(capsys, directory, "connect")[0] == 2
    wire.finish()
    assert SiwcCredentialStore(directory, authorized=True).profiles() == ()
    assert not list(directory.glob("account-*.sealed"))


def test_browser_refusal_no_external_request_or_profile(setup, capsys):
    directory, wire = setup
    wire.browser_success = False
    assert invoke(capsys, directory, "connect")[0] == 2
    assert wire.requests == [] and SiwcCredentialStore(directory, authorized=True).profiles() == ()


def test_private_parser_error_not_echoed(tmp_path, capsys):
    assert cli.main(["chatgpt-account", "--format", "json",
                     "--private-password=unprintable-fixture-marker"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "unprintable-fixture-marker" not in captured.err
    assert "--private-password" not in captured.err


def test_invalid_profile_ref_sanitized_without_mutating_store(setup, capsys):
    directory, wire, _ = connect(capsys, setup)
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    count = len(wire.requests)
    assert invoke(capsys, directory, "refresh", "--profile-ref", "password=private-marker")[0] == 2
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == before
    assert len(wire.requests) == count


def test_sensitive_catalog_names_withheld_whole(setup, capsys):
    directory, wire, profile = connect(capsys, setup)
    wire.display_name = "sk-" + "a" * 48
    code, catalog = invoke(capsys, directory, "catalog", "--profile-ref", profile)
    assert code == 0 and catalog["models_withheld"] is True
    assert "models" not in catalog


@pytest.mark.parametrize("timeout", ["0", "-1", "601"])
def test_invalid_timeout_before_import_storage_network(tmp_path, monkeypatch, capsys, timeout):
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.startswith("inference_service"):
            pytest.fail("invalid timeout imported OAuth runtime")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    directory = tmp_path / "missing"
    assert invoke(capsys, directory, "connect", "--timeout-seconds", timeout)[0] == 2
    assert not directory.exists()


def test_existing_valid_credentials_still_require_new_operation_opt_in(setup, capsys):
    directory, wire, profile = connect(capsys, setup)
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    requests, browsers = len(wire.requests), len(wire.urls)
    assert invoke(capsys, directory, "refresh", "--profile-ref", profile, authorized=False)[0] == 2
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == before
    assert len(wire.requests) == requests and len(wire.urls) == browsers


@pytest.mark.parametrize("case", ["default-off", "private-parser", "missing-profiles"])
def test_actual_subprocess_outside_workspace_no_core_or_writes(tmp_path, case):
    directory = tmp_path / "must-not-exist"
    args = ["--credential-dir", str(directory), "--action", "connect"]
    if case == "private-parser":
        args = ["--private-password=unprintable-fixture-marker"]
    elif case == "missing-profiles":
        args = ["--credential-dir", str(directory), "--action", "profiles", "--authorized"]
    before = sorted(path.name for path in tmp_path.iterdir())
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1",
               DATABASE_URL="postgresql://not-used.invalid/blocked")
    result = subprocess.run([sys.executable, "-m", "apps.jarvis_console", "--format", "json",
                             "chatgpt-account", *args], cwd=tmp_path, env=env,
                            capture_output=True, timeout=60)
    assert result.returncode == 2 and result.stdout == b""
    assert b"unprintable-fixture-marker" not in result.stderr
    assert not directory.exists()
    assert sorted(path.name for path in tmp_path.iterdir()) == before
