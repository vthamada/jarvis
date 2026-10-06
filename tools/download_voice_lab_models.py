"""Opt-in public model downloader for the isolated voice lab, never user audio."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import uuid4

MAX_FILE_BYTES = 4 * 1024**3
MAX_METADATA_BYTES = 2 * 1024**2
CHUNK_BYTES = 1024**2
SOURCE_ENGINE = "chatterbox_pt_br_source"
SOURCE_REPOSITORY = "ResembleAI/Chatterbox-Multilingual-TTS-pt-br"
SOURCE_REVISION = "9e515821e826e207cd617a0fdd0223899ed108ea"
SOURCE_PREFIX = "chatterbox/src/chatterbox/"
MODEL_SOURCES = {
    "whisper_turbo": (
        (
            "openai/whisper-large-v3-turbo",
            "41f01f3fe87f28c78e2fbf8b568835947dd65ed9",
            (
                "added_tokens.json",
                "config.json",
                "generation_config.json",
                "merges.txt",
                "model.safetensors",
                "normalizer.json",
                "preprocessor_config.json",
                "special_tokens_map.json",
                "tokenizer.json",
                "tokenizer_config.json",
                "vocab.json",
            ),
        ),
    ),
    "whisper_small": (
        (
            "openai/whisper-small",
            "973afd24965f72e36ca33b3055d56a652f456b4d",
            (
                "added_tokens.json",
                "config.json",
                "generation_config.json",
                "merges.txt",
                "model.safetensors",
                "normalizer.json",
                "preprocessor_config.json",
                "special_tokens_map.json",
                "tokenizer.json",
                "tokenizer_config.json",
                "vocab.json",
            ),
        ),
    ),
    "qwen3_tts": (
        (
            "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "5d83992436eae1d760afd27aff78a71d676296fc",
            (
                "config.json",
                "generation_config.json",
                "merges.txt",
                "model.safetensors",
                "preprocessor_config.json",
                "speech_tokenizer/config.json",
                "speech_tokenizer/configuration.json",
                "speech_tokenizer/model.safetensors",
                "speech_tokenizer/preprocessor_config.json",
                "tokenizer_config.json",
                "vocab.json",
            ),
        ),
    ),
    "chatterbox_pt_br": (
        (
            "ResembleAI/Chatterbox-Multilingual-pt-br",
            "b3952f18bc2eaa72b9bd7c17d2c4653bcad4770d",
            ("t3_pt_br.safetensors", "s3gen_v3.pt", "grapheme_mtl_merged_expanded_v1.json"),
        ),
        (
            "ResembleAI/chatterbox",
            "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18",
            ("ve.pt",),
        ),
    ),
}


class DownloadError(RuntimeError):
    """Content-free failure code safe to print without user paths or URL tokens."""


def validate_public_url(url: str) -> None:
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
        valid_host = (
            host == "huggingface.co" or host.endswith(".huggingface.co") or host.endswith(".hf.co")
        )
        if (
            parts.scheme != "https"
            or not valid_host
            or parts.username is not None
            or parts.password is not None
        ):
            raise DownloadError("public_https_host_required")
        if parts.port not in {None, 443} or parts.fragment:
            raise DownloadError("public_https_host_required")
    except ValueError as error:
        raise DownloadError("public_https_host_required") from error


class PublicRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        validate_public_url(newurl)
        return super().redirect_request(request, response, code, message, headers, newurl)


def public_opener():
    # No environment proxies, authorization handlers, cookies or SDK credential lookup.
    return build_opener(ProxyHandler({}), PublicRedirects())


def _open(opener, url: str):
    validate_public_url(url)
    request = Request(
        url,
        headers={
            "User-Agent": "jarvis-voice-lab-public-model-download/1",
            "Accept-Encoding": "identity",
        },
    )
    response = opener.open(request, timeout=60)
    try:
        if response.getcode() != 200:
            raise DownloadError("public_artifact_unavailable")
        validate_public_url(response.geturl())
        return response
    except Exception:
        response.close()
        raise


def _safe_components(path: Path) -> None:
    # lstat all existing components before making directories or opening files.
    for candidate in reversed([path, *path.parents]):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise DownloadError("redirected_workspace_path")
        if candidate != path and not stat.S_ISDIR(info.st_mode):
            raise DownloadError("invalid_workspace_parent")


def _target_root(workspace_root: Path, engine: str) -> Path:
    if engine not in MODEL_SOURCES and engine != SOURCE_ENGINE:
        raise DownloadError("unsupported_engine")
    workspace = Path(os.path.abspath(workspace_root))
    _safe_components(workspace)
    if not workspace.is_dir():
        raise DownloadError("workspace_directory_required")
    target = (
        workspace
        / ".research"
        / "voice-lab"
        / "models"
        / ("chatterbox_pt_br" if engine == SOURCE_ENGINE else engine)
    )
    if engine == SOURCE_ENGINE:
        target = target / "source"
    _safe_components(target)
    target.mkdir(parents=True, exist_ok=True)
    _safe_components(target)
    if not target.is_dir():
        raise DownloadError("model_directory_required")
    return target


def _artifact_path(target: Path, name: str) -> Path:
    relative = PurePosixPath(name)
    if (
        relative.is_absolute()
        or not relative.parts
        or ".." in relative.parts
        or "\\" in name
        or ":" in name
    ):
        raise DownloadError("invalid_artifact_name")
    destination = target.joinpath(*relative.parts)
    if destination == target:
        raise DownloadError("invalid_artifact_name")
    _safe_components(destination)
    return destination


def _tree_manifest(
    opener, repository: str, revision: str, allowed: tuple[str, ...] | None, *, source=False
) -> dict[str, dict[str, Any]]:
    query = urlencode({"recursive": "true", "expand": "true"})
    resource = "spaces" if source else "models"
    url = f"https://huggingface.co/api/{resource}/{repository}/tree/{revision}?{query}"
    records = []
    seen = set()
    tree_path = urlsplit(url).path
    while url:
        if url in seen or len(seen) >= 8:
            raise DownloadError("invalid_public_metadata_pagination")
        seen.add(url)
        with _open(opener, url) as response:
            raw = response.read(MAX_METADATA_BYTES + 1)
            link = response.headers.get("Link", "")
        if len(raw) > MAX_METADATA_BYTES:
            raise DownloadError("metadata_limit_exceeded")
        try:
            page = json.loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError) as error:
            raise DownloadError("invalid_public_metadata") from error
        if not isinstance(page, list) or len(page) + len(records) > 10000:
            raise DownloadError("invalid_public_metadata")
        records.extend(page)
        match = re.search(r'<([^>]+)>;\s*rel="next"', link)
        url = match.group(1) if match else ""
        if url:
            next_parts = urlsplit(url)
            if (
                next_parts.scheme != "https"
                or next_parts.netloc != "huggingface.co"
                or next_parts.path != tree_path
            ):
                raise DownloadError("invalid_public_metadata_pagination")
    if not isinstance(records, list) or len(records) > 10000:
        raise DownloadError("invalid_public_metadata")
    if source:
        allowed = tuple(
            record["path"]
            for record in records
            if isinstance(record, dict)
            and isinstance(record.get("path"), str)
            and record["path"].startswith(SOURCE_PREFIX)
            and record["path"].endswith(".py")
            and PurePosixPath(record["path"]).name != "app.py"
        )
        if not 1 <= len(allowed) <= 100:
            raise DownloadError("invalid_public_source_manifest")
    found = {}
    for record in records:
        if not isinstance(record, dict) or record.get("path") not in allowed:
            continue
        name = record["path"]
        if name in found or record.get("type") != "file":
            raise DownloadError("invalid_public_metadata")
        size = record.get("size")
        limit = MAX_METADATA_BYTES if source else MAX_FILE_BYTES
        if type(size) is not int or not (0 if source else 1) <= size <= limit:
            raise DownloadError("artifact_limit_exceeded")
        lfs = record.get("lfs")
        if lfs is not None:
            if not isinstance(lfs, dict) or lfs.get("size") != size:
                raise DownloadError("invalid_public_metadata")
            digest = lfs.get("oid")
            if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                raise DownloadError("invalid_public_metadata")
            algorithm = "sha256"
        else:
            digest = record.get("oid")
            if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{40}", digest) is None:
                raise DownloadError("invalid_public_metadata")
            algorithm = "git_blob_sha1"
        found[name] = {
            "size": size,
            "digest": digest,
            "algorithm": algorithm,
            "repository": repository,
            "revision": revision,
            "resource": resource,
        }
    if set(found) != set(allowed):
        raise DownloadError("allowlisted_artifact_metadata_missing")
    return found


def _hashers(metadata):
    sha256 = hashlib.sha256()
    expected = sha256 if metadata["algorithm"] == "sha256" else hashlib.sha1()
    if metadata["algorithm"] == "git_blob_sha1":
        expected.update(f"blob {metadata['size']}\0".encode("ascii"))
    return sha256, expected


def _digest_file(path: Path, metadata) -> str:
    _safe_components(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != metadata["size"]:
        raise DownloadError("existing_artifact_not_verified")
    sha256, expected = _hashers(metadata)
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_BYTES):
            size += len(chunk)
            if size > metadata["size"]:
                raise DownloadError("artifact_limit_exceeded")
            sha256.update(chunk)
            if expected is not sha256:
                expected.update(chunk)
    if size != metadata["size"] or expected.hexdigest() != metadata["digest"]:
        raise DownloadError("existing_artifact_not_verified")
    return sha256.hexdigest()


def _download_one(opener, target: Path, name: str, metadata) -> dict[str, Any]:
    destination = _artifact_path(target, name)
    if destination.exists():
        digest = _digest_file(destination, metadata)
        return {
            "artifact": name,
            "size": metadata["size"],
            "sha256": digest,
            "status": "verified_existing",
        }
    destination.parent.mkdir(parents=True, exist_ok=True)
    _safe_components(destination)
    partial = destination.with_name(f".{destination.name}.{uuid4().hex}.part")
    _safe_components(partial)
    sha256, expected = _hashers(metadata)
    size = 0
    created = False
    try:
        with partial.open("xb") as stream:
            created = True
            prefix = "spaces/" if metadata["resource"] == "spaces" else ""
            url = f"https://huggingface.co/{prefix}{metadata['repository']}/resolve/{metadata['revision']}/{name}"
            with _open(opener, url) as response:
                while chunk := response.read(CHUNK_BYTES):
                    size += len(chunk)
                    if size > metadata["size"] or size > MAX_FILE_BYTES:
                        raise DownloadError("artifact_limit_exceeded")
                    sha256.update(chunk)
                    if expected is not sha256:
                        expected.update(chunk)
                    stream.write(chunk)
            stream.flush()
            os.fsync(stream.fileno())
        if size != metadata["size"] or expected.hexdigest() != metadata["digest"]:
            raise DownloadError("artifact_integrity_mismatch")
        _safe_components(destination)
        if destination.exists():
            raise DownloadError("artifact_created_concurrently")
        # Link creation is atomic and refuses overwrite even on POSIX; remove only our partial.
        os.link(partial, destination)
        partial.unlink()
        created = False
        return {
            "artifact": name,
            "size": size,
            "sha256": sha256.hexdigest(),
            "status": "downloaded_verified",
        }
    finally:
        if created:
            # No glob cleanup; only this invocation's exclusive partial is removed.
            _safe_components(partial)
            partial.unlink(missing_ok=True)


def download_models(engine: str, workspace_root: Path, *, opener=None) -> list[dict[str, Any]]:
    if engine not in MODEL_SOURCES and engine != SOURCE_ENGINE:
        raise DownloadError("unsupported_engine")
    target = _target_root(workspace_root, engine)
    selected = opener if opener is not None else public_opener()
    manifest = {}
    sources = MODEL_SOURCES.get(engine, ((SOURCE_REPOSITORY, SOURCE_REVISION, None),))
    for repository, revision, names in sources:
        for name, record in _tree_manifest(
            selected, repository, revision, names, source=engine == SOURCE_ENGINE
        ).items():
            if name in manifest:
                raise DownloadError("duplicate_artifact")
            manifest[name] = record
    required = sum(
        record["size"]
        for name, record in manifest.items()
        if not _artifact_path(target, name).exists()
    )
    if shutil.disk_usage(target).free < required:
        raise DownloadError("insufficient_workspace_disk_space")
    results = []
    for name, metadata in manifest.items():
        result = _download_one(selected, target, name, metadata)
        results.append(result)
        print(json.dumps(result, sort_keys=True), flush=True)
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=sorted([*MODEL_SOURCES, SOURCE_ENGINE]), required=True)
    parser.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--download",
        action="store_true",
        help="Explicitly fetch public model files; never upload audio",
    )
    arguments = parser.parse_args(argv)
    if not arguments.download:
        print(
            json.dumps(
                {
                    "engine": arguments.engine,
                    "status": "download_not_requested",
                    "public_artifact_count": None
                    if arguments.engine == SOURCE_ENGINE
                    else sum(len(source[2]) for source in MODEL_SOURCES[arguments.engine]),
                }
            )
        )
        return 0
    try:
        download_models(arguments.engine, arguments.workspace_root)
    except DownloadError as error:
        print(json.dumps({"status": "failed", "code": str(error)}), file=sys.stderr)
        return 2
    except Exception:
        print(json.dumps({"status": "failed", "code": "public_download_failed"}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
