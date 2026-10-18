"""Private voice configuration and owned offline worker artifact lifetimes."""

import hashlib
import json
import subprocess
import sys
import tempfile
import wave
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.jarvis_api import voice_profile as module
from apps.jarvis_console.persistent_tts import LocalFinalTtsConfig, validate_local_tts_config
from apps.jarvis_voice_lab import transcribe

SCHEMA = "jarvis-local-voice-profile-v1"


def bounded_id(value):
    return type(value).__name__


def write_profile(path, document):
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def wav_bytes():
    output = BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        audio.writeframes(b"\x01\x00" * 1600)
    return output.getvalue()


@pytest.fixture
def local_files(tmp_path):
    model = tmp_path / "model"
    model.mkdir()
    (model / "config.json").write_text('{"model_type":"whisper"}', encoding="utf-8")
    (model / "model.safetensors").write_bytes(b"synthetic metadata; never load as weights")
    executable = tmp_path / "python-stub.exe"
    executable.write_bytes(b"synthetic executable; never run")
    reference = tmp_path / "reference.wav"
    reference.write_bytes(wav_bytes())
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return SimpleNamespace(
        root=tmp_path, path=tmp_path / "voice.json", model=model,
        executable=executable, reference=reference, workspace=workspace,
    )


def asr_document(files, **overrides):
    values = {
        "model_dir": str(files.model), "python_executable": str(files.executable),
        "device": "cpu", "timeout_seconds": 20,
    }
    values.update(overrides)
    return {"schema_version": SCHEMA, "asr": values, "tts": None}


def tts_document(files, **overrides):
    values = {
        "engine": "qwen3_tts", "reference_path": str(files.reference),
        "model_dir": str(files.model), "python_executable": str(files.executable),
    }
    values.update(overrides)
    return {"schema_version": SCHEMA, "asr": None, "tts": values}


def refuses(path, workspace):
    with pytest.raises(ValueError, match="^invalid_voice_profile$") as error:
        module.load_voice_profile(path, workspace)
    assert str(error.value) == "invalid_voice_profile"


def test_asr_profile_reads_only_explicit_configuration_and_model_metadata(
        local_files, monkeypatch):
    files = local_files
    write_profile(files.path, asr_document(files))
    original_read, reads = Path.read_text, []

    def guarded_read(path, *args, **kwargs):
        reads.append(path)
        assert path == files.path, "profile load must not load model contents"
        return original_read(path, *args, **kwargs)

    def forbidden(*_args, **_kwargs):
        pytest.fail("profile load must not start Core, a process or a model worker")

    monkeypatch.setattr(Path, "read_text", guarded_read)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(module, "transcribe_bytes", forbidden)
    monkeypatch.setattr(module, "synthesize_bytes", forbidden)
    result = module.load_voice_profile(files.path, files.workspace)
    assert type(result) is module.LocalVoiceProfile and result.tts is None
    assert type(result.asr) is module.LocalAsrConfig
    assert result.asr.model_dir == files.model and result.asr.python_executable == files.executable
    assert result.asr.device == "cpu" and result.asr.timeout_seconds == 20
    assert reads == [files.path]
    assert str(files.model) not in repr(result) and str(files.executable) not in repr(result)


def test_tts_profile_converts_only_allowed_fields_and_runs_readonly_preflight(
        local_files, monkeypatch):
    files, seen = local_files, []
    document = tts_document(
        files, device="cuda:0", timeout_seconds=25, voice_profile="qwen_icl",
        reference_transcript="Trecho publico sintetico.", transcript_confirmed=True, seed=7,
        reference_start_seconds=0, reference_duration_seconds=3,
    )
    write_profile(files.path, document)
    monkeypatch.setattr(module, "preflight_local_tts_config", seen.append)
    result = module.load_voice_profile(files.path, files.workspace)
    assert result.asr is None and result.tts is seen[0] and len(seen) == 1
    config = result.tts
    assert config.authorized is True and config.batch_mode is True
    assert config.workspace_root == files.workspace and config.reference_path == files.reference
    assert config.model_dir == files.model and config.python_executable == files.executable
    assert config.engine == "qwen3_tts" and config.device == "cuda:0"
    assert config.reference_transcript == document["tts"]["reference_transcript"]
    assert config.seed == 7 and config.timeout_seconds == 25


def test_both_engines_are_independently_optional_but_not_both_missing(
        local_files, monkeypatch):
    files = local_files
    monkeypatch.setattr(module, "preflight_local_tts_config", lambda _config: None)
    document = asr_document(files)
    document["tts"] = tts_document(files)["tts"]
    write_profile(files.path, document)
    result = module.load_voice_profile(files.path, files.workspace)
    assert result.asr is not None and result.tts is not None
    write_profile(files.path, {"schema_version": SCHEMA, "asr": None, "tts": None})
    refuses(files.path, files.workspace)


@pytest.mark.parametrize("document", [
    None, [], 3, "profile", {}, {"schema_version": SCHEMA},
    {"schema_version": "future", "asr": None, "tts": None},
    {"schema_version": SCHEMA, "asr": None, "tts": None, "endpoint": "https://example.test"},
], ids=bounded_id)
def test_root_schema_is_closed(local_files, document):
    files = local_files
    write_profile(files.path, document)
    refuses(files.path, files.workspace)


@pytest.mark.parametrize("raw", [
    '{"schema_version":"jarvis-local-voice-profile-v1","asr":null,"asr":null,"tts":null}',
    '{"schema_version":"jarvis-local-voice-profile-v1","asr":{"device":"cpu",'
    '"device":"cuda:0"},"tts":null}',
    '{"schema_version":"jarvis-local-voice-profile-v1","asr":null,"tts":'
    '{"engine":"qwen3_tts","engine":"chatterbox_pt_br"}}',
], ids=["root", "asr", "tts"])
def test_duplicate_json_keys_never_select_a_different_configuration(local_files, raw):
    files = local_files
    files.path.write_text(raw, encoding="utf-8")
    refuses(files.path, files.workspace)


@pytest.mark.parametrize("raw", [b"", b"{", b"\xff", b"x" * 16385], ids=bounded_id)
def test_empty_malformed_encoding_and_oversized_profile_are_content_free(local_files, raw):
    files = local_files
    files.path.write_bytes(raw)
    refuses(files.path, files.workspace)


def test_size_limit_is_checked_before_reading_profile_contents(local_files, monkeypatch):
    files = local_files
    files.path.write_bytes(b"x" * 16385)

    def forbidden(*_args, **_kwargs):
        pytest.fail("oversized profile must be rejected before content read")

    monkeypatch.setattr(Path, "read_text", forbidden)
    refuses(files.path, files.workspace)


def test_exact_profile_size_limit_is_accepted_with_valid_document(local_files):
    files = local_files
    raw = json.dumps(asr_document(files)).encode("utf-8")
    files.path.write_bytes(raw + b" " * (16384 - len(raw)))
    result = module.load_voice_profile(files.path, files.workspace)
    assert result.asr.model_dir == files.model


@pytest.mark.parametrize("part", ["asr", "tts"])
@pytest.mark.parametrize("value", [[], "config", 3, False, [["engine", "qwen3_tts"]]],
                         ids=bounded_id)
def test_engine_configuration_must_be_a_json_object_not_pairs(local_files, part, value):
    files = local_files
    document = {"schema_version": SCHEMA, "asr": None, "tts": None, part: value}
    write_profile(files.path, document)
    refuses(files.path, files.workspace)


@pytest.mark.parametrize("part,field", [
    ("asr", "model_dir"), ("asr", "python_executable"),
    ("asr", "device"), ("asr", "timeout_seconds"),
    ("tts", "engine"), ("tts", "reference_path"),
    ("tts", "model_dir"), ("tts", "python_executable"),
])
def test_required_engine_fields_cannot_be_omitted(local_files, part, field):
    files = local_files
    document = asr_document(files) if part == "asr" else tts_document(files)
    del document[part][field]
    write_profile(files.path, document)
    refuses(files.path, files.workspace)


@pytest.mark.parametrize("part", ["asr", "tts"])
@pytest.mark.parametrize("field", ["authorized", "workspace_root", "batch_mode", "base_url",
                                  "api_key", "download", "extra"])
def test_browser_or_profile_data_cannot_override_host_controls(
        local_files, monkeypatch, part, field):
    files, preflight = local_files, []
    document = asr_document(files) if part == "asr" else tts_document(files)
    document[part][field] = "not permitted"
    write_profile(files.path, document)
    monkeypatch.setattr(module, "preflight_local_tts_config", preflight.append)
    refuses(files.path, files.workspace)
    assert not preflight


@pytest.mark.parametrize("field,value", [
    ("timeout_seconds", 0), ("timeout_seconds", -1), ("timeout_seconds", 300.01),
    ("timeout_seconds", True), ("timeout_seconds", "20"),
    ("timeout_seconds", float("nan")), ("timeout_seconds", float("inf")),
    ("device", "cuda"), ("device", "cuda:1"), ("device", "remote"), ("device", None),
], ids=bounded_id)
def test_invalid_asr_options_are_rejected_before_any_model_tree_io(
        local_files, monkeypatch, field, value):
    files, visited = local_files, []
    write_profile(files.path, asr_document(files, **{field: value}))
    original = module._plain_path

    def plain_path(path, **kwargs):
        visited.append(path)
        assert path == files.path, "invalid options must precede model/executable inspection"
        return original(path, **kwargs)

    def forbidden(*_args, **_kwargs):
        pytest.fail("invalid ASR configuration inspected model tree")

    monkeypatch.setattr(module, "_plain_path", plain_path)
    monkeypatch.setattr(module, "_local_tree", forbidden)
    refuses(files.path, files.workspace)
    assert visited == [files.path]


@pytest.mark.parametrize("timeout", [0.01, 300])
@pytest.mark.parametrize("device", ["cpu", "cuda:0"])
def test_asr_timeout_and_device_boundaries_are_explicit(local_files, timeout, device):
    files = local_files
    write_profile(files.path, asr_document(files, timeout_seconds=timeout, device=device))
    result = module.load_voice_profile(files.path, files.workspace)
    assert result.asr.timeout_seconds == timeout and result.asr.device == device


@pytest.mark.parametrize("selected", [
    Path("relative.json"), Path("//server/share/voice.json"),
    Path("\\\\server\\share\\voice.json"),
], ids=["relative", "unc-slash", "unc-backslash"])
def test_profile_path_must_be_explicit_absolute_and_local_before_io(
        local_files, monkeypatch, selected):
    def forbidden(*_args, **_kwargs):
        pytest.fail("unsafe profile location was inspected")

    monkeypatch.setattr(module, "_plain_path", forbidden)
    refuses(selected, local_files.workspace)


@pytest.mark.parametrize("field", ["model_dir", "python_executable"])
@pytest.mark.parametrize("unsafe", ["relative", "//server/share/file", "\\\\server\\share\\file"],
                         ids=["relative", "unc-slash", "unc-backslash"])
def test_asr_paths_cannot_select_unc_or_relative_models(local_files, monkeypatch, field, unsafe):
    files = local_files
    write_profile(files.path, asr_document(files, **{field: unsafe}))

    def forbidden(*_args, **_kwargs):
        pytest.fail("unsafe ASR path reached model tree inspection")

    monkeypatch.setattr(module, "_local_tree", forbidden)
    refuses(files.path, files.workspace)


@pytest.mark.parametrize("field", ["reference_path", "model_dir", "python_executable",
                                  "sdk_source_dir"])
@pytest.mark.parametrize("unsafe", ["relative", "//server/share/file", "\\\\server\\share\\file"],
                         ids=["relative", "unc-slash", "unc-backslash"])
def test_tts_paths_are_subject_to_local_path_validation(
        local_files, monkeypatch, field, unsafe):
    files = local_files
    write_profile(files.path, tts_document(files, **{field: unsafe}))
    monkeypatch.setattr(module, "preflight_local_tts_config", validate_local_tts_config)
    refuses(files.path, files.workspace)


def test_model_tree_failure_is_opaque_and_does_not_start_inference(local_files, monkeypatch):
    files = local_files
    write_profile(files.path, asr_document(files))

    def failure(_path):
        raise ValueError("sensitive private model path token=secret")

    monkeypatch.setattr(module, "_local_tree", failure)
    refuses(files.path, files.workspace)


def owned_tempdirs(monkeypatch, root):
    original, created = tempfile.mkdtemp, []

    def create(*args, **kwargs):
        capture = kwargs.get("prefix", "").startswith("jarvis-web-capture-")
        if capture:
            kwargs["dir"] = root
        result = original(*args, **kwargs)
        if capture:
            created.append(Path(result))
        return result

    monkeypatch.setattr(tempfile, "mkdtemp", create)
    return created


def test_transcription_capture_and_drafts_share_one_owned_lifetime(local_files, monkeypatch):
    files, seen = local_files, []
    created = owned_tempdirs(monkeypatch, files.root)
    source_bytes, cancelled = wav_bytes(), lambda: False
    untouched = files.reference.read_bytes()

    def worker(**kwargs):
        seen.append(kwargs)
        source, private = kwargs["source"], kwargs["private_output_root"]
        assert source.parent == private and source.read_bytes() == source_bytes
        assert private.is_absolute() and private != files.root
        assert kwargs["authorized"] is True and kwargs["cancelled"] is cancelled
        assert kwargs["model_dir"] == files.model
        assert kwargs["python_executable"] == files.executable
        assert kwargs["device"] == "cpu" and kwargs["timeout_seconds"] == 20
        drafts = private / "owned-draft"
        drafts.mkdir()
        (drafts / "transcript.txt").write_text("unconfirmed draft", encoding="utf-8")
        segments = drafts / "transcript.json"
        segments.write_text(json.dumps({"segments": [{"text": "Primeiro trecho."},
                                                     {"text": "Segundo trecho."}]}),
                            encoding="utf-8")
        return {"segments_path": str(segments)}

    monkeypatch.setattr(transcribe, "transcribe_local_wav", worker)
    config = module.LocalAsrConfig(files.model, files.executable, "cpu", 20)
    result = module.transcribe_bytes(config, source_bytes, cancelled)
    assert result == "Primeiro trecho.\nSegundo trecho." and len(seen) == 1
    assert len(created) == 1 and not created[0].exists()
    assert files.reference.read_bytes() == untouched


@pytest.mark.parametrize("stage", ["worker-failure", "cancelled", "malformed-draft"])
def test_transcription_removes_only_owned_artifacts_on_failure(local_files, monkeypatch, stage):
    files = local_files
    created = owned_tempdirs(monkeypatch, files.root)
    untouched = files.reference.read_bytes()

    def worker(**kwargs):
        private = kwargs["private_output_root"]
        drafts = private / "owned-draft"
        drafts.mkdir()
        path = drafts / "transcript.json"
        path.write_text("{", encoding="utf-8")
        if stage == "worker-failure":
            raise ValueError("owned synthetic worker failure")
        if stage == "cancelled":
            raise InterruptedError("owned cancellation")
        return {"segments_path": str(path)}

    monkeypatch.setattr(transcribe, "transcribe_local_wav", worker)
    config = module.LocalAsrConfig(files.model, files.executable)
    with pytest.raises((ValueError, InterruptedError)):
        module.transcribe_bytes(config, wav_bytes(), lambda: stage == "cancelled")
    assert len(created) == 1 and not created[0].exists()
    assert files.reference.read_bytes() == untouched
    assert files.root.exists() and files.model.exists() and files.executable.exists()


def test_asr_orchestrator_uses_guarded_worker_with_no_real_child(local_files, monkeypatch):
    files, processes = local_files, []
    created = owned_tempdirs(monkeypatch, files.root)
    for name in ("OPENAI_API_KEY", "HF_TOKEN", "HTTPS_PROXY"):
        monkeypatch.setenv(name, "inherited-private-value")

    class Process:
        returncode = 0

        def __init__(self, command, **kwargs):
            self.command, self.options = command, kwargs
            processes.append(self)

        def communicate(self, input=None, timeout=None):
            assert timeout is not None and 0 < timeout <= 0.2
            request = json.loads(input)
            output = Path(request["output_directory"])
            assert output.parent == created[0]
            assert Path(request["source"]).parent == created[0]
            assert self.options["cwd"] == output
            assert self.command[0] == str(files.executable) and self.command[1] == "-I"
            assert str(files.reference) not in self.command
            environment = self.options["env"]
            assert environment["HF_HUB_OFFLINE"] == "1"
            assert environment["TRANSFORMERS_OFFLINE"] == "1"
            assert environment["HF_HUB_DISABLE_IMPLICIT_TOKEN"] == "1"
            assert environment["HOME"] == str(output / "home")
            assert environment["TEMP"] == str(output / "tmp")
            assert "inherited-private-value" not in repr(environment)
            assert self.options["stdin"] == subprocess.PIPE
            assert self.options["stderr"] == subprocess.DEVNULL
            if sys.platform == "win32":
                assert self.options["creationflags"] & subprocess.CREATE_NO_WINDOW
            (output / "transcript.txt").write_text("Fala sintetica.", encoding="utf-8")
            (output / "transcript.json").write_text(
                '{"segments":[{"text":"Fala sintetica."}]}', encoding="utf-8")
            self.options["stdout"].write(json.dumps({
                "run_id": request["run_id"], "status": "completed",
            }).encode("utf-8"))
            self.options["stdout"].flush()

    class ConfirmedSupervisor:
        def __init__(self, **kwargs):
            assert kwargs["process"] is processes[0]

        def poll_handshake(self):
            return True

        def confirm_exit(self, **kwargs):
            pass

        def close(self):
            pass

    monkeypatch.setattr(transcribe.subprocess, "Popen", Process)
    # This unit composes orchestration with a guard double, never a kernel proof.
    monkeypatch.setattr(transcribe, "OwnedWorkerSupervisor", ConfirmedSupervisor)
    monkeypatch.setattr(transcribe, "expected_worker_image", lambda path: str(path))
    config = module.LocalAsrConfig(files.model, files.executable, "cpu", 20)
    assert module.transcribe_bytes(config, wav_bytes(), lambda: False) == "Fala sintetica."
    assert len(processes) == 1 and len(created) == 1 and not created[0].exists()
    assert files.reference.exists() and files.model.exists() and files.executable.exists()


def test_synthesis_uses_exact_text_and_validates_all_part_bindings(local_files, monkeypatch):
    from apps.jarvis_voice_lab import lab_batch

    files, seen = local_files, []
    text = "  Final canonica.\nSegunda linha sem resumo.  "
    output = files.root / "synthetic-output.wav"
    output.write_bytes(wav_bytes())
    config = LocalFinalTtsConfig(
        True, "qwen3_tts", files.reference, files.model, files.executable, files.workspace,
        batch_mode=True,
    )
    result = SimpleNamespace(
        status="completed", part_count=1, completed_parts=1,
        text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        part_text_sha256=(hashlib.sha256(text.encode("utf-8")).hexdigest(),),
    )
    monkeypatch.setattr(module, "preflight_local_tts_config", lambda value: seen.append(value))

    def runner(**kwargs):
        seen.append(kwargs)
        assert kwargs["text"] == text and kwargs["authorized"] is True
        assert kwargs["workspace_root"] == files.workspace and callable(kwargs["cancelled"])
        return result

    def validated(selected, candidate, evidence):
        assert selected is config and candidate is result and evidence == "model_real"
        return str(output)

    monkeypatch.setattr(lab_batch, "run_voice_lab_batch", runner)
    monkeypatch.setattr(module, "_validated_output", validated)
    assert module.synthesize_bytes(config, text, lambda: False) == wav_bytes()
    assert len(seen) == 2
    result.part_text_sha256 = ("0" * 64,)
    with pytest.raises(ValueError, match="^voice_unavailable$"):
        module.synthesize_bytes(config, text, lambda: False)
