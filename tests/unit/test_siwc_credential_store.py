"""SIWC private storage tests use only owned temporary synthetic credentials."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import asdict, replace
from pathlib import Path

import pytest
from inference_service import credential_store as storage
from inference_service.credential_store import SiwcCredentialStore
from inference_service.siwc_contracts import DIRECT_SCOPE, SiwcCredentials, SiwcError

CLIENT = "oaiapp_storage_test"
SUBJECT = "synthetic-storage-subject"


def credentials(host, **overrides):
    return SiwcCredentials(client_id=CLIENT, host_id=host, subject=SUBJECT,
                           access_token="synthetic-access-secret",
                           refresh_token="synthetic-refresh",
                           id_token="synthetic.id.token", scopes=("openid", DIRECT_SCOPE),
                           saved_at=1_800_000_000, expires_at=1_800_003_600,
                           email="synthetic@example.invalid", **overrides)


@pytest.fixture
def store(tmp_path):
    value = SiwcCredentialStore(tmp_path / "private", authorized=True)
    host = value.initialize()
    return value, credentials(host)


def account_path(store):
    return store.directory / store._name(CLIENT, SUBJECT)


def load(store):
    return store.load(client_id=CLIENT, subject=SUBJECT)


def assert_private(exc):
    assert str(exc.value).startswith("siwc_")
    for sensitive in ("synthetic-access-secret", "synthetic-refresh", SUBJECT,
                      "synthetic@example.invalid", "private OS error"):
        assert sensitive not in str(exc.value)
        assert sensitive not in repr(exc.value)


def sealed(raw):
    if os.name == "nt":
        return storage._WINDOWS_MAGIC + storage._dpapi(raw, decrypt=False)
    return storage._POSIX_MAGIC + raw


def write_record(path, value):
    raw = value if type(value) is bytes else json.dumps(value, allow_nan=True).encode()
    path.write_bytes(sealed(raw))
    if os.name == "posix":
        path.chmod(0o600)


def test_initialization_is_explicit_and_never_default_authorized(tmp_path):
    path = tmp_path / "not-created"
    store = SiwcCredentialStore(path)
    assert not path.exists()
    with pytest.raises(SiwcError, match="siwc_storage_not_authorized"):
        store.initialize()
    assert not path.exists()
    authorized = SiwcCredentialStore(path, authorized=True)
    with pytest.raises(SiwcError, match="siwc_storage_uninitialized"):
        authorized.host_id()
    assert not path.exists()
    with pytest.raises(SiwcError, match="siwc_storage_input_invalid"):
        SiwcCredentialStore(path, authorized=1)
    with pytest.raises(SiwcError, match="siwc_storage_input_invalid"):
        SiwcCredentialStore(str(path), authorized=True)


def test_host_id_stable_after_reload_and_init_does_not_overwrite(store):
    current, record = store
    hostbytes = (current.directory / "host.sealed").read_bytes()
    lockbytes = (current.directory / ".session.lock").read_bytes()
    restarted = SiwcCredentialStore(current.directory, authorized=True)
    assert restarted.initialize() == record.host_id
    assert restarted.host_id() == record.host_id
    assert (current.directory / "host.sealed").read_bytes() == hostbytes
    assert (current.directory / ".session.lock").read_bytes() == lockbytes


def test_real_protection_reload_atomic_overwrite_and_no_plaintext_windows(store):
    current, record = store
    current.save(record)
    path = account_path(current)
    old = path.read_bytes()
    assert load(SiwcCredentialStore(current.directory, authorized=True)) == record
    changed = replace(record, access_token="rotated-synthetic-access", saved_at=1_800_000_001)
    current.save(changed)
    assert load(current) == changed
    assert old != path.read_bytes()
    assert not list(current.directory.glob(".stage-*"))
    if os.name == "nt":
        assert old.startswith(storage._WINDOWS_MAGIC)
        assert b"synthetic-access-secret" not in old
        assert b"synthetic-refresh" not in old
        assert SUBJECT.encode() not in old
        assert record.host_id.encode() not in (current.directory / "host.sealed").read_bytes()
        decoded = storage._dpapi(old[len(storage._WINDOWS_MAGIC):], decrypt=True)
        assert json.loads(decoded)["access_token"] == record.access_token
    else:
        assert old.startswith(storage._POSIX_MAGIC)


@pytest.mark.skipif(os.name != "nt", reason="Requires actual current-user Windows DPAPI")
def test_actual_dpapi_roundtrip_not_mocked():
    raw = b"synthetic bytes only; no production credentials"
    encrypted = storage._dpapi(raw, decrypt=False)
    assert raw not in encrypted
    assert storage._dpapi(encrypted, decrypt=True) == raw
    with pytest.raises(SiwcError, match="siwc_storage_protection_failed"):
        storage._dpapi(b"corrupt synthetic ciphertext", decrypt=True)


@pytest.mark.skipif(os.name != "posix", reason="Requires actual POSIX ownership/mode semantics")
def test_actual_posix_owner_modes_and_permission_refusal(store):
    current, record = store
    current.save(record)
    assert stat.S_IMODE(current.directory.stat().st_mode) == 0o700
    for path in current.directory.iterdir():
        assert path.stat().st_uid == os.geteuid()
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    account_path(current).chmod(0o644)
    with pytest.raises(SiwcError, match="siwc_storage_permissions_refused"):
        load(current)
    account_path(current).chmod(0o600)
    current.directory.chmod(0o755)
    with pytest.raises(SiwcError, match="siwc_storage_permissions_refused"):
        load(current)


def test_records_require_exact_host_and_account_binding(store):
    current, record = store
    foreignhost = "urn:uuid:" + str(uuid.uuid4())
    with pytest.raises(SiwcError, match="siwc_storage_binding_mismatch"):
        current.save(replace(record, host_id=foreignhost))
    assert not account_path(current).exists()
    current.save(record)
    with pytest.raises(SiwcError, match="siwc_storage_record_missing"):
        current.load(client_id="oaiapp_other", subject=SUBJECT)
    with pytest.raises(SiwcError, match="siwc_storage_record_missing"):
        current.load(client_id=CLIENT, subject="other-subject")
    for field, value in (("host_id", foreignhost), ("client_id", "oaiapp_other"),
                         ("subject", "other-subject")):
        tampered = {"schema_version": "jarvis-siwc-credentials-v1", **asdict(record), field: value}
        write_record(account_path(current), tampered)
        with pytest.raises(SiwcError, match="siwc_storage_binding_mismatch") as caught:
            load(current)
        assert_private(caught)


@pytest.mark.parametrize("alter", ["extra", "schema", "scope-type", "issuer", "token",
                                   "bool-expiry", "nan", "overflow", "missing", "duplicate",
                                   "nonobject", "invalid-utf8"], ids=str)
def test_invalid_protected_records_are_private(store, alter):
    current, record = store
    current.save(record)
    document = {"schema_version": "jarvis-siwc-credentials-v1", **asdict(record)}
    if alter == "extra":
        document["unexpected"] = "synthetic-access-secret"
    elif alter == "schema":
        document["schema_version"] = "unrecognized"
    elif alter == "scope-type":
        document["scopes"] = "openid"
    elif alter == "issuer":
        document["issuer"] = "https://example.invalid"
    elif alter == "token":
        document["access_token"] = "bad\nsecret"
    elif alter == "bool-expiry":
        document["expires_at"] = True
    elif alter == "nan":
        document["saved_at"] = float("nan")
    elif alter == "overflow":
        raw = json.dumps(document).encode().replace(b'1800000000', b'1e999')
        document = raw
    elif alter == "missing":
        del document["access_token"]
    elif alter == "duplicate":
        document = json.dumps(document).encode()[:-1] + b',"access_token":"private"}'
    elif alter == "nonobject":
        document = b"[]"
    else:
        document = b"\xff"
    write_record(account_path(current), document)
    with pytest.raises(SiwcError, match="siwc_storage_invalid") as caught:
        load(current)
    assert_private(caught)


@pytest.mark.parametrize("alter", ["plaintext", "wrong-magic", "ciphertext", "empty", "oversize"])
def test_corruption_never_plaintext_fallback_or_private_diagnostic(store, alter):
    current, record = store
    current.save(record)
    path = account_path(current)
    content = {"plaintext": b'{"access_token":"synthetic-access-secret"}',
               "wrong-magic": b"other-version\nsecret",
               "ciphertext": storage._WINDOWS_MAGIC + b"bad",
               "empty": b"", "oversize": b"x" * (storage._MAX_BYTES + 1)}[alter]
    path.write_bytes(content)
    with pytest.raises(SiwcError) as caught:
        load(current)
    assert_private(caught)


@pytest.mark.parametrize("document", [{}, {"schema_version": "wrong", "host_id": "private"},
    {"schema_version": "jarvis-siwc-host-v1", "host_id": "not-a-uuid"},
    {"schema_version": "jarvis-siwc-host-v1", "host_id": "urn:uuid:" + str(uuid.uuid4()),
     "extra": "private"}], ids=["empty", "schema", "host", "extra"])
def test_invalid_host_record_cannot_be_reinitialized_to_new_host(store, document):
    current, _record = store
    path = current.directory / "host.sealed"
    write_record(path, document)
    before = path.read_bytes()
    with pytest.raises(SiwcError, match="siwc_storage_invalid"):
        current.initialize()
    assert path.read_bytes() == before


@pytest.mark.parametrize("suffix", ["OneDrive/private", "onedrive-test/private", "a/../private",
                                    "a:sidecar/private"],
                         ids=["onedrive", "sync", "traversal", "ads"])
def test_explicit_bad_directory_paths_refused_without_initialization(tmp_path, suffix):
    path = tmp_path / suffix
    with pytest.raises(SiwcError, match="siwc_storage_path_refused"):
        SiwcCredentialStore(path, authorized=True).initialize()
    assert not (tmp_path / "private").exists()


def test_relative_root_unc_and_repository_directory_refused(tmp_path):
    unc = Path(r"\\server\share\private") if os.name == "nt" else Path("//server/share/private")
    for path in (Path("relative-private"), Path(tmp_path.anchor),
                 unc):
        with pytest.raises(SiwcError, match="siwc_storage_path_refused"):
            SiwcCredentialStore(path, authorized=True).initialize()
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / ".git").mkdir()
    with pytest.raises(SiwcError, match="siwc_storage_path_refused"):
        SiwcCredentialStore(repository / "private", authorized=True).initialize()
    with pytest.raises(SiwcError, match="siwc_storage_path_refused"):
        SiwcCredentialStore(repository, authorized=True).initialize()
    assert not (repository / "host.sealed").exists()


def test_lock_required_on_exact_owner_thread(store):
    current, record = store
    for invoke in (lambda: current.save_locked(record),
                   lambda: current.load_locked(client_id=CLIENT, subject=SUBJECT)):
        with pytest.raises(SiwcError, match="siwc_storage_lock_required"):
            invoke()
    errors = []

    def foreign():
        try:
            current.save_locked(record)
        except SiwcError as error:
            errors.append(error.code)

    with current.locked():
        worker = threading.Thread(target=foreign)
        worker.start()
        worker.join(timeout=10)
        assert not worker.is_alive()
        current.save_locked(record)
        assert current.load_locked(client_id=CLIENT, subject=SUBJECT) == record
    assert errors == ["siwc_storage_lock_required"]


def test_same_object_and_separate_instance_thread_locks_never_unlink(store):
    current, _record = store
    lockpath = current.directory / ".session.lock"
    before = lockpath.read_bytes()
    errors = []

    def try_lock(value):
        try:
            with value.locked():
                errors.append("incorrect-acquisition")
        except SiwcError as error:
            errors.append(error.code)

    with current.locked():
        for contender in (current, SiwcCredentialStore(current.directory, authorized=True)):
            worker = threading.Thread(target=try_lock, args=(contender,))
            worker.start()
            worker.join(timeout=10)
            assert not worker.is_alive()
    assert errors == ["siwc_storage_busy", "siwc_storage_busy"]
    assert lockpath.read_bytes() == before
    with current.locked():
        pass


def test_real_cross_process_os_lock_is_busy_without_unlink(store):
    current, _record = store
    package_root = Path(storage.__file__).resolve().parents[1]
    child = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from inference_service.credential_store import SiwcCredentialStore
from inference_service.siwc_contracts import SiwcError
store = SiwcCredentialStore(Path(sys.argv[2]), authorized=True)
try:
    with store.locked():
        print('acquired')
except SiwcError as error:
    print(error.code)
"""
    lockpath = current.directory / ".session.lock"
    before = lockpath.read_bytes()
    with current.locked():
        result = subprocess.run([sys.executable, "-I", "-c", child, str(package_root),
                                 str(current.directory)], capture_output=True,
                                text=True, timeout=60)
        assert result.returncode == 0
        assert result.stdout.strip() == "siwc_storage_busy"
        assert not result.stderr
    result = subprocess.run([sys.executable, "-I", "-c", child, str(package_root),
                             str(current.directory)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0
    assert result.stdout.strip() == "acquired"
    assert lockpath.read_bytes() == before


def test_process_death_releases_os_lock_without_deleting_lock_file(store):
    current, _record = store
    package_root = Path(storage.__file__).resolve().parents[1]
    child = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from inference_service.credential_store import SiwcCredentialStore
store = SiwcCredentialStore(Path(sys.argv[2]), authorized=True)
with store.locked():
    print('holding-owned-test-lock', flush=True)
    sys.stdin.readline()
"""
    path = current.directory / ".session.lock"
    before = path.read_bytes()
    process = subprocess.Popen([sys.executable, "-I", "-c", child, str(package_root),
                                str(current.directory)], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    ready = threading.Event()
    lines = []

    def read_ready():
        lines.append(process.stdout.readline())
        ready.set()

    reader = threading.Thread(target=read_ready, daemon=True)
    reader.start()
    try:
        assert ready.wait(timeout=15)
        assert lines == ["holding-owned-test-lock\n"]
        with pytest.raises(SiwcError, match="siwc_storage_busy"):
            current.host_id()
    finally:
        process.kill()
        process.wait(timeout=15)
        reader.join(timeout=5)
        for stream in (process.stdin, process.stdout, process.stderr):
            stream.close()
    # Windows may complete byte-range lock cleanup just after the exited
    # process handle signals. Observe that physical cleanup, without adding a
    # retry to runtime or deleting/replacing the persistent lock file.
    deadline = time.monotonic() + 5
    while True:
        try:
            with current.locked():
                pass
            break
        except SiwcError as error:
            if error.code != "siwc_storage_busy" or time.monotonic() >= deadline:
                raise
            time.sleep(0.01)
    assert path.read_bytes() == before


def test_exception_inside_lock_releases_it_without_stale_file_deletion(store):
    current, _record = store
    before = (current.directory / ".session.lock").read_bytes()
    with pytest.raises(RuntimeError, match="synthetic operation failure"):
        with current.locked():
            raise RuntimeError("synthetic operation failure")
    with current.locked():
        pass
    assert (current.directory / ".session.lock").read_bytes() == before


def test_simultaneous_initialization_keeps_one_host_and_lock(store):
    current, record = store
    before = {path.name: path.read_bytes() for path in current.directory.iterdir()}
    other = SiwcCredentialStore(current.directory, authorized=True)
    with current.locked():
        with pytest.raises(SiwcError, match="siwc_storage_busy"):
            other.initialize()
    assert other.initialize() == record.host_id
    assert {path.name: path.read_bytes() for path in current.directory.iterdir()} == before


def test_invalid_save_input_cannot_create_account_file(store):
    current, record = store
    with pytest.raises(SiwcError, match="siwc_storage_binding_mismatch"):
        current.save(asdict(record))
    assert not account_path(current).exists()


def test_write_bound_and_lock_file_type_cannot_be_bypassed(store):
    current, _record = store
    with current.locked():
        with pytest.raises(SiwcError, match="siwc_storage_invalid"):
            current._write("oversized.sealed", {"data": "x" * 131_073})
    assert not (current.directory / "oversized.sealed").exists()
    assert not list(current.directory.glob(".stage-*"))
    lock = current.directory / ".session.lock"
    lock.write_bytes(b"")
    with pytest.raises(SiwcError, match="siwc_storage_path_refused"):
        current.initialize()
    assert lock.read_bytes() == b""


@pytest.mark.skipif(os.name != "nt", reason="Windows must refuse POSIX plaintext envelope")
def test_windows_refuses_valid_plaintext_posix_envelope(store):
    current, record = store
    current.save(record)
    raw = json.dumps({"schema_version": "jarvis-siwc-credentials-v1", **asdict(record)}).encode()
    account_path(current).write_bytes(storage._POSIX_MAGIC + raw)
    with pytest.raises(SiwcError, match="siwc_storage_protection_refused"):
        load(current)


@pytest.mark.parametrize("failure", ["replace", "fsync", "stage-open"])
def test_os_failure_before_replace_preserves_old_record_and_cleans_only_own_stage(
        store, monkeypatch, failure):
    current, record = store
    current.save(record)
    old = account_path(current).read_bytes()
    original_open = os.open

    def broken(*args, **kwargs):
        raise OSError("private OS error synthetic-access-secret")

    def open_stage(path, *args, **kwargs):
        if Path(path).name.startswith(".stage-"):
            return broken()
        return original_open(path, *args, **kwargs)

    if failure == "replace":
        monkeypatch.setattr(storage.os, "replace", broken)
    elif failure == "fsync":
        monkeypatch.setattr(storage.os, "fsync", broken)
    else:
        monkeypatch.setattr(storage.os, "open", open_stage)
    with pytest.raises(SiwcError, match="siwc_storage_write_failed") as caught:
        current.save(replace(record, access_token="changed-token"))
    assert_private(caught)
    assert account_path(current).read_bytes() == old
    assert not list(current.directory.glob(".stage-*"))


def test_preexisting_stage_collision_is_never_deleted(store, monkeypatch):
    current, record = store
    current.save(record)
    old = account_path(current).read_bytes()
    stage_id = uuid.uuid4()
    stage = current.directory / (".stage-" + stage_id.hex)
    stage.write_bytes(b"another synthetic writer's file")
    monkeypatch.setattr(storage.uuid, "uuid4", lambda: stage_id)
    with pytest.raises(SiwcError, match="siwc_storage_write_failed"):
        current.save(replace(record, access_token="changed-token"))
    assert stage.read_bytes() == b"another synthetic writer's file"
    assert account_path(current).read_bytes() == old


@pytest.mark.skipif(os.name != "nt", reason="DPAPI refusal is a Windows storage contract")
def test_dpapi_failure_never_writes_plaintext_and_preserves_existing_bytes(store, monkeypatch):
    current, record = store
    current.save(record)
    old = account_path(current).read_bytes()

    def failed(*args, **kwargs):
        raise SiwcError("siwc_storage_protection_failed")

    monkeypatch.setattr(storage, "_dpapi", failed)
    with pytest.raises(SiwcError, match="siwc_storage_protection_failed"):
        current.save(replace(record, access_token="must-not-write-this-token"))
    assert account_path(current).read_bytes() == old
    assert not list(current.directory.glob(".stage-*"))


@pytest.mark.parametrize("name", ["host.sealed", ".session.lock", "account"])
def test_hardlinked_private_paths_refused_and_foreign_target_untouched(store, tmp_path, name):
    current, record = store
    current.save(record)
    path = account_path(current) if name == "account" else current.directory / name
    foreign = tmp_path / ("linked-" + name)
    os.link(path, foreign)
    old = foreign.read_bytes()
    invoke = (lambda: load(current)) if name == "account" else current.host_id
    with pytest.raises(SiwcError, match="siwc_storage_path_refused"):
        invoke()
    assert foreign.read_bytes() == old


@pytest.mark.parametrize("kind", ["directory", "ancestor", "host", "lock", "account"])
def test_symlinks_refused_without_read_or_write_of_target(store, tmp_path, kind):
    current, record = store
    current.save(record)
    target = tmp_path / "foreign-target"
    target.mkdir()
    marker = target / "marker"
    marker.write_bytes(b"foreign synthetic bytes")
    link = tmp_path / "link"
    try:
        if kind in ("directory", "ancestor"):
            link.symlink_to(current.directory, target_is_directory=True)
            path = link if kind == "directory" else link / "nested"
            contender = SiwcCredentialStore(path, authorized=True)
            invoke = contender.initialize
        else:
            path = (account_path(current) if kind == "account" else
                    current.directory / {"host": "host.sealed", "lock": ".session.lock"}[kind])
            path.unlink()
            path.symlink_to(marker)
            invoke = (lambda: load(current)) if kind == "account" else current.host_id
    except (OSError, NotImplementedError):
        pytest.skip("Host does not permit creating actual symlinks")
    with pytest.raises(SiwcError, match="siwc_storage_path_refused"):
        invoke()
    assert marker.read_bytes() == b"foreign synthetic bytes"


def test_directory_instead_of_record_and_missing_record_do_not_initialize(store):
    current, _record = store
    with pytest.raises(SiwcError, match="siwc_storage_record_missing"):
        load(current)
    account_path(current).mkdir()
    with pytest.raises(SiwcError, match="siwc_storage_path_refused"):
        load(current)
    assert list(account_path(current).iterdir()) == []


def test_repr_and_exception_diagnostics_do_not_leak_directory_or_credentials(store):
    current, record = store
    assert str(current.directory) not in repr(current)
    assert record.access_token not in repr(record)
    assert SUBJECT not in repr(record)
    current.save(record)
    before = {path.name: path.read_bytes() for path in current.directory.iterdir()}
    with pytest.raises(SiwcError):
        current.load(client_id="oaiapp_x/../bad", subject="private")
    assert {path.name: path.read_bytes() for path in current.directory.iterdir()} == before


def test_profile_ref_is_opaque_stable_exact_account_binding(store):
    current, record = store
    ref = current.profile_ref(record)
    assert len(ref) == 72
    assert ref.startswith("profile-")
    assert all(character in "0123456789abcdef" for character in ref[8:])
    for private in (record.access_token, record.refresh_token, CLIENT, SUBJECT, record.email):
        assert private not in ref
    assert current.profile_ref(replace(record, access_token="rotated-token")) == ref
    assert current.profile_ref(replace(record, email="other@example.invalid")) == ref
    assert current.profile_ref(replace(record, subject="different-subject")) != ref
    assert current.profile_ref(replace(record, client_id="oaiapp_other")) != ref
    with pytest.raises(SiwcError, match="siwc_storage_input_invalid"):
        current.profile_ref(asdict(record))


def test_profile_load_and_catalog_are_readonly_after_encrypted_reload(store):
    current, record = store
    second = replace(record, client_id="oaiapp_second", subject="second-subject")
    current.save(record)
    current.save(second)
    restarted = SiwcCredentialStore(current.directory, authorized=True)
    before = {path.name: path.read_bytes() for path in current.directory.iterdir()}
    expected = tuple(sorted((current.profile_ref(record), current.profile_ref(second))))
    assert restarted.profiles() == expected
    assert restarted.load_profile(current.profile_ref(record)) == record
    assert restarted.load_profile(current.profile_ref(second)) == second
    assert {path.name: path.read_bytes() for path in current.directory.iterdir()} == before
    assert CLIENT not in repr(restarted.profiles())
    assert SUBJECT not in repr(restarted.profiles())
    assert record.access_token not in repr(restarted.profiles())


def test_empty_profile_catalog_does_not_initialize_and_requires_authorization(tmp_path, store):
    current, _record = store
    assert current.profiles() == ()
    unauthorized = SiwcCredentialStore(current.directory)
    with pytest.raises(SiwcError, match="siwc_storage_not_authorized"):
        unauthorized.profiles()
    with pytest.raises(SiwcError, match="siwc_storage_not_authorized"):
        unauthorized.load_profile("profile-" + "a" * 64)
    missing = tmp_path / "uninitialized-profiles"
    other = SiwcCredentialStore(missing, authorized=True)
    for invoke in (other.profiles, lambda: other.load_profile("profile-" + "a" * 64)):
        with pytest.raises(SiwcError, match="siwc_storage_uninitialized"):
            invoke()
    assert not missing.exists()


@pytest.mark.parametrize("ref", [None, True, 1, "", "profile-", "profile-" + "a" * 63,
    "profile-" + "a" * 65, "profile-" + "A" * 64, "profile-" + "g" * 64,
    "profile-" + "a" * 64 + "\n", "profile-../host.sealed", "account-" + "a" * 64,
    "profile-" + "a" * 64 + ":ads"],
    ids=["none", "bool", "int", "empty", "prefix", "short", "long", "uppercase", "nonhex",
         "newline", "traversal", "account-prefix", "ads"])
def test_invalid_profile_refs_cannot_read_or_mutate_store(store, monkeypatch, ref):
    current, record = store
    current.save(record)
    before = {path.name: path.read_bytes() for path in current.directory.iterdir()}

    def no_read(*args, **kwargs):
        raise AssertionError("Invalid references must be rejected before reading records")

    monkeypatch.setattr(current, "_read", no_read)
    with pytest.raises(SiwcError, match="siwc_storage_input_invalid"):
        current.load_profile(ref)
    assert {path.name: path.read_bytes() for path in current.directory.iterdir()} == before


def test_missing_profile_ref_does_not_initialize_account(store):
    current, _record = store
    before = tuple(path.name for path in current.directory.iterdir())
    with pytest.raises(SiwcError, match="siwc_storage_record_missing"):
        current.load_profile("profile-" + "a" * 64)
    assert tuple(path.name for path in current.directory.iterdir()) == before


@pytest.mark.parametrize("binding", ["client_id", "subject", "host_id"])
def test_profile_content_binding_checked_for_load_and_catalog(store, binding):
    current, record = store
    current.save(record)
    values = {"client_id": "oaiapp_foreign", "subject": "foreign-subject",
              "host_id": "urn:uuid:" + str(uuid.uuid4())}
    content = {"schema_version": "jarvis-siwc-credentials-v1", **asdict(record),
               binding: values[binding]}
    path = account_path(current)
    write_record(path, content)
    before = path.read_bytes()
    for invoke in (current.profiles, lambda: current.load_profile(current.profile_ref(record))):
        with pytest.raises(SiwcError, match="siwc_storage_binding_mismatch") as caught:
            invoke()
        assert_private(caught)
    assert path.read_bytes() == before


@pytest.mark.parametrize("corruption", ["plaintext", "schema", "extra", "duplicate", "missingid",
                                      "badscope", "nonobject"], ids=str)
def test_corrupt_profile_catalog_is_all_or_nothing_and_never_returns_private_content(
        store, corruption):
    current, record = store
    current.save(record)
    another = replace(record, subject="second-corrupt-profile")
    current.save(another)
    path = current.directory / current._name(another.client_id, another.subject)
    content = {"schema_version": "jarvis-siwc-credentials-v1", **asdict(another)}
    if corruption == "plaintext":
        path.write_bytes(b"synthetic-access-secret without encryption")
    else:
        if corruption == "schema":
            content["schema_version"] = "wrong"
        elif corruption == "extra":
            content["unexpected"] = "private"
        elif corruption == "duplicate":
            content = json.dumps(content).encode()[:-1] + b',"client_id":"oaiapp_other"}'
        elif corruption == "missingid":
            del content["client_id"]
        elif corruption == "badscope":
            content["scopes"] = "openid"
        else:
            content = b"[]"
        write_record(path, content)
    before = {item.name: item.read_bytes() for item in current.directory.iterdir()}
    for invoke in (current.profiles, lambda: current.load_profile(current.profile_ref(another))):
        with pytest.raises(SiwcError) as caught:
            invoke()
        assert_private(caught)
    assert {item.name: item.read_bytes() for item in current.directory.iterdir()} == before
    assert current.load_profile(current.profile_ref(record)) == record


def test_profile_catalog_exactly_32_and_overflow_refused_before_decrypt(store, monkeypatch):
    current, record = store
    refs = []
    for index in range(32):
        account = replace(record, subject=f"synthetic-catalog-{index}")
        current.save(account)
        refs.append(current.profile_ref(account))
    assert current.profiles() == tuple(sorted(refs))
    overflow = replace(record, subject="synthetic-catalog-overflow")
    current.save(overflow)

    def no_decryption(*args, **kwargs):
        raise AssertionError("Account count budget must be checked before decryption")

    monkeypatch.setattr(current, "_read", no_decryption)
    with pytest.raises(SiwcError, match="siwc_storage_limit_exceeded"):
        current.profiles()


def test_profile_catalog_directory_budget_and_noncanonical_names_ignored(store):
    current, _record = store
    for index in range(253):
        (current.directory / f"unrelated-owned-fixture-{index}").write_bytes(b"synthetic")
    noncanonical = current.directory / ("account-" + "A" * 64 + ".sealed")
    noncanonical.write_bytes(b"not a readable private record")
    assert len(tuple(current.directory.iterdir())) == 256
    assert current.profiles() == ()
    (current.directory / "one-more-owned-file").write_bytes(b"synthetic")
    with pytest.raises(SiwcError, match="siwc_storage_limit_exceeded"):
        current.profiles()
    assert noncanonical.read_bytes() == b"not a readable private record"


def test_profile_catalog_and_lookup_respect_busy_lock_without_deletion(store):
    current, record = store
    current.save(record)
    other = SiwcCredentialStore(current.directory, authorized=True)
    with current.locked():
        for invoke in (other.profiles, lambda: other.load_profile(current.profile_ref(record))):
            with pytest.raises(SiwcError, match="siwc_storage_busy"):
                invoke()
    assert other.profiles() == (current.profile_ref(record),)


def test_profile_lookup_and_catalog_refuse_hardlinked_account(store, tmp_path):
    current, record = store
    current.save(record)
    path = account_path(current)
    link = tmp_path / "hardlinked-profile-copy"
    os.link(path, link)
    before = link.read_bytes()
    for invoke in (current.profiles, lambda: current.load_profile(current.profile_ref(record))):
        with pytest.raises(SiwcError, match="siwc_storage_path_refused"):
            invoke()
    assert link.read_bytes() == before


def test_close_failure_is_private_and_always_releases_object_mutex(store, monkeypatch):
    current, record = store
    original_close = storage.os.close
    calls = []

    def close_then_fail(fd):
        # Actually close the owned descriptor first: no leaked synthetic lock or
        # descriptor persists after the test, even though the OS reports failure.
        original_close(fd)
        calls.append(fd)
        raise OSError("private OS error synthetic-access-secret")

    with monkeypatch.context() as context:
        context.setattr(storage.os, "close", close_then_fail)
        with pytest.raises(SiwcError, match="siwc_storage_unavailable") as caught:
            with current.locked():
                pass
        assert_private(caught)
    assert len(calls) == 1
    assert current._lock_owner is None
    assert current._mutex.acquire(blocking=False)
    current._mutex.release()
    with current.locked():
        current.save_locked(record)
    assert load(current) == record
