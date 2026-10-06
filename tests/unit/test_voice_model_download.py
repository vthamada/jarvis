"""Public model downloads tested with injected HTTP, never network or real audio."""

from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from tools import download_voice_lab_models as downloader


def metadata(name, data, *, lfs=False):
    record = {"path": name, "type": "file", "size": len(data)}
    if lfs:
        record["lfs"] = {"oid": hashlib.sha256(data).hexdigest(), "size": len(data)}
        record["oid"] = "1" * 40
    else:
        record["oid"] = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
    return record


class Response(io.BytesIO):
    def __init__(self, data, url, *, headers=None, status=200):
        super().__init__(data)
        self.url = url
        self.headers = headers or {}
        self.status = status

    def geturl(self):
        return self.url

    def getcode(self):
        return self.status


class Http:
    def __init__(self, engine, *, payload=b"public-fixture-model", patch=None):
        self.requests = []
        self.files = {}
        self.trees = {}
        self.patch = patch
        for repository, revision, names in downloader.MODEL_SOURCES[engine]:
            records = []
            for name in names:
                records.append(metadata(name, payload, lfs=name.endswith((".pt", ".safetensors"))))
                self.files[f"https://huggingface.co/{repository}/resolve/{revision}/{name}"] = (
                    payload
                )
            self.trees[f"/api/models/{repository}/tree/{revision}"] = records

    def open(self, request, timeout):
        self.requests.append(request)
        assert timeout == 60
        assert not request.has_header("Authorization")
        assert not request.has_header("Cookie")
        if self.patch:
            patched = self.patch(request, self)
            if patched is not None:
                return patched
        if urlsplit(request.full_url).path in self.trees:
            body = json.dumps(self.trees[urlsplit(request.full_url).path]).encode()
        else:
            body = self.files[request.full_url]
        return Response(body, request.full_url)


@pytest.mark.parametrize(
    "engine", ["qwen3_tts", "chatterbox_pt_br", "whisper_small", "whisper_turbo"]
)
def test_public_pinned_manifest_download_verified_existing_and_no_overwrite(
    tmp_path, capsys, engine
):
    http = Http(engine)
    results = downloader.download_models(engine, tmp_path, opener=http)
    expected_names = {name for source in downloader.MODEL_SOURCES[engine] for name in source[2]}
    assert {result["artifact"] for result in results} == expected_names
    assert all(result["status"] == "downloaded_verified" for result in results)
    target = tmp_path / ".research" / "voice-lab" / "models" / engine
    assert all(
        (target / result["artifact"]).read_bytes() == b"public-fixture-model" for result in results
    )
    assert not list(target.rglob("*.part"))
    count = len(http.requests)
    existing = downloader.download_models(engine, tmp_path, opener=http)
    assert all(result["status"] == "verified_existing" for result in existing)
    assert len(http.requests) - count == len(downloader.MODEL_SOURCES[engine])
    assert str(tmp_path) not in capsys.readouterr().out
    for request in http.requests:
        assert request.full_url.startswith("https://huggingface.co/")
        assert "/main/" not in request.full_url


def test_existing_wrong_hash_is_preserved_and_not_refetched(tmp_path):
    http = Http("qwen3_tts")
    target = downloader._target_root(tmp_path, "qwen3_tts")
    original = b"wrong!!"
    (target / "config.json").write_bytes(original)
    with pytest.raises(downloader.DownloadError, match="existing_artifact_not_verified"):
        downloader.download_models("qwen3_tts", tmp_path, opener=http)
    assert (target / "config.json").read_bytes() == original
    assert len(http.requests) == 1


@pytest.mark.parametrize("fault", ["wrong_hash", "oversize", "truncated", "network", "redirect"])
def test_failed_owned_partial_is_cleaned_without_deleting_other_files(tmp_path, fault):
    http = Http("qwen3_tts")
    target = downloader._target_root(tmp_path, "qwen3_tts")
    sentinel = target / "operator-owned.part"
    sentinel.write_bytes(b"preserve")

    def patch(request, _):
        if "/resolve/" not in request.full_url:
            return None
        if fault == "network":
            raise TimeoutError("never-print-this-user-secret")
        if fault == "redirect":
            return Response(b"fixture", "https://attacker.invalid/secret")
        payload = {
            "wrong_hash": b"x" * len(b"public-fixture-model"),
            "oversize": b"x" * 100,
            "truncated": b"short",
        }[fault]
        return Response(payload, request.full_url)

    http.patch = patch
    with pytest.raises((downloader.DownloadError, TimeoutError)):
        downloader.download_models("qwen3_tts", tmp_path, opener=http)
    assert not (target / "config.json").exists()
    assert list(target.glob("*.part")) == [sentinel]
    assert sentinel.read_bytes() == b"preserve"


@pytest.mark.parametrize(
    "url",
    [
        "http://huggingface.co/public",
        "https://huggingface.co.attacker.invalid/public",
        "https://attackerhuggingface.co/public",
        "https://attacker.invalid.hf.co.evil/a",
        "https://user:secret@huggingface.co/a",
        "https://huggingface.co:444/a",
        "https://127.0.0.1/a",
        "file:///tmp/private",
        "https://huggingface.co/a#fragment",
    ],
)
def test_redirect_and_url_allowlist_denies_nonpublic_destinations(url):
    with pytest.raises(downloader.DownloadError):
        downloader.validate_public_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://huggingface.co/model",
        "https://cdn-lfs.huggingface.co/artifact",
        "https://cdn-lfs-us-1.hf.co/artifact",
        "https://cas-bridge.xethub.hf.co/public?signature=token",
    ],
)
def test_public_https_cdn_domains_accepted_without_echoing_signed_urls(url):
    downloader.validate_public_url(url)


@pytest.mark.parametrize("name", ["../../secret", "/private", "..\\secret", "x:secret", "."])
def test_artifact_path_is_exclusive_to_target(tmp_path, name):
    with pytest.raises(downloader.DownloadError, match="invalid_artifact_name"):
        downloader._artifact_path(tmp_path, name)


def test_symlink_or_reparse_components_refused_before_network(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable on this host")
    http = Http("qwen3_tts")
    with pytest.raises(downloader.DownloadError, match="redirected_workspace_path"):
        downloader.download_models("qwen3_tts", linked, opener=http)
    assert http.requests == []
    assert list(real.iterdir()) == []


def test_hardlinked_existing_artifact_refused_without_overwrite(tmp_path):
    http = Http("qwen3_tts")
    target = downloader._target_root(tmp_path, "qwen3_tts")
    original = tmp_path / "original"
    original.write_bytes(b"public-fixture-model")
    os.link(original, target / "config.json")
    with pytest.raises(downloader.DownloadError, match="existing_artifact_not_verified"):
        downloader.download_models("qwen3_tts", tmp_path, opener=http)
    assert original.read_bytes() == b"public-fixture-model"


@pytest.mark.parametrize(
    "fault", ["missing", "duplicate", "invalid_hash", "invalid_size", "lfs_size", "type"]
)
def test_invalid_tree_metadata_cannot_download_files(tmp_path, fault):
    http = Http("qwen3_tts")
    records = next(iter(http.trees.values()))
    if fault == "missing":
        records.pop()
    elif fault == "duplicate":
        records.append(records[0].copy())
    elif fault == "invalid_hash":
        records[0]["oid"] = "evil"
    elif fault == "invalid_size":
        records[0]["size"] = downloader.MAX_FILE_BYTES + 1
    elif fault == "lfs_size":
        records[3]["lfs"]["size"] = 1
    else:
        records[0]["type"] = "directory"
    with pytest.raises(downloader.DownloadError):
        downloader.download_models("qwen3_tts", tmp_path, opener=http)
    assert len(http.requests) == 1
    assert not list((tmp_path / ".research").rglob("*.part"))


def test_opt_in_and_failures_do_not_print_paths_or_network_secrets(tmp_path, monkeypatch, capsys):
    def unexpected(*_, **__):
        raise AssertionError("network must not happen")

    monkeypatch.setattr(downloader, "public_opener", unexpected)
    assert downloader.main(["--engine", "qwen3_tts", "--workspace-root", str(tmp_path)]) == 0
    assert not list(tmp_path.iterdir())
    assert str(tmp_path) not in capsys.readouterr().out
    monkeypatch.setattr(
        downloader,
        "download_models",
        lambda *args: (_ for _ in ()).throw(OSError("private-path-secret")),
    )
    assert downloader.main(["--engine", "qwen3_tts", "--download"]) == 2
    assert "private-path-secret" not in capsys.readouterr().err


def test_public_opener_ignores_environment_proxies(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://user:secret@attacker.invalid")
    opener = downloader.public_opener()
    assert not any(getattr(handler, "proxies", {}) for handler in opener.handlers)
    assert not any(
        "Auth" in type(handler).__name__ or "Cookie" in type(handler).__name__
        for handler in opener.handlers
    )


def test_pinned_source_download_is_nonexecuting_prefix_scoped_and_paginates(tmp_path, capsys):
    first = downloader.SOURCE_PREFIX + "__init__.py"
    second = downloader.SOURCE_PREFIX + "tts.py"
    bodies = {first: b"", second: b"raise RuntimeError('must-not-execute')\n"}
    tree = f"https://huggingface.co/api/spaces/{downloader.SOURCE_REPOSITORY}/tree/{downloader.SOURCE_REVISION}"
    next_url = tree + "?recursive=true&expand=true&cursor=page2"

    class SourceHttp:
        def open(self, request, timeout):
            url = request.full_url
            if urlsplit(url).path == urlsplit(tree).path:
                if "cursor=" not in url:
                    records = [
                        metadata(first, bodies[first]),
                        metadata("app.py", b"unsafe"),
                        metadata("chatterbox/src/chatterbox/app.py", b"unsafe"),
                    ]
                    return Response(
                        json.dumps(records).encode(),
                        url,
                        headers={"Link": f'<{next_url}>; rel="next"'},
                    )
                return Response(json.dumps([metadata(second, bodies[second])]).encode(), url)
            name = url.split(f"/resolve/{downloader.SOURCE_REVISION}/", 1)[1]
            assert name in bodies
            return Response(bodies[name], url)

    results = downloader.download_models(downloader.SOURCE_ENGINE, tmp_path, opener=SourceHttp())
    assert {result["artifact"] for result in results} == set(bodies)
    target = tmp_path / ".research" / "voice-lab" / "models" / "chatterbox_pt_br" / "source"
    assert (target / second).read_bytes() == bodies[second]
    assert not (target / "app.py").exists()
    assert not (target / downloader.SOURCE_PREFIX / "app.py").exists()
    assert str(tmp_path) not in capsys.readouterr().out


@pytest.mark.parametrize(
    "next_url",
    ["https://attacker.invalid/tree", "https://huggingface.co/api/models/other/tree/main"],
)
def test_tree_pagination_cannot_change_host_repository_or_pin(tmp_path, next_url):
    http = Http("qwen3_tts")

    def patch(request, value):
        if "/tree/" in request.full_url:
            records = next(iter(value.trees.values()))
            return Response(
                json.dumps(records).encode(),
                request.full_url,
                headers={"Link": f'<{next_url}>; rel="next"'},
            )
        return None

    http.patch = patch
    with pytest.raises(downloader.DownloadError, match="invalid_public_metadata_pagination"):
        downloader.download_models("qwen3_tts", tmp_path, opener=http)


def test_downloader_has_no_sdk_audio_env_or_remote_code_imports():
    source = Path(downloader.__file__).read_text(encoding="utf-8")
    for forbidden in [
        "import torch",
        "huggingface_hub",
        "load_dotenv",
        "os.environ",
        "eval(",
        "exec(",
        "getenv(",
        "subprocess",
        "reference_audio",
    ]:
        assert forbidden not in source
