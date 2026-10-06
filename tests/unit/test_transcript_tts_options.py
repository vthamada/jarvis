"""Separate audio consent and pure, private local-TTS argument validation."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.jarvis_console import transcript_tts_options as options
from apps.jarvis_console.bootstrap import ROOT


def parser():
    result = argparse.ArgumentParser()
    result.add_argument("--authorized", action="store_true")
    options.add_transcript_tts_arguments(result)
    return result


def configured(**changes):
    values = {
        "tts_authorized": True,
        "tts_engine": "qwen3_tts",
        "tts_reference": "C:/private-marker/reference.wav",
        "tts_model_dir": "C:/private-marker/model",
        "tts_python": "C:/private-marker/python.exe",
    }
    values.update(changes)
    return argparse.Namespace(**values)


def test_legacy_namespace_is_text_only():
    assert options.transcript_tts_config(argparse.Namespace(authorized=True)) is None


def test_all_parser_defaults_are_absent():
    args = parser().parse_args([])
    assert all(getattr(args, name) is None for name in options._FIELDS)
    assert options.transcript_tts_config(args) is None


@pytest.mark.parametrize("flag,value", [
    ("--tts-engine", "qwen3_tts"), ("--tts-reference", "private-marker.wav"),
    ("--tts-model-dir", "private-marker"), ("--tts-python", "private-marker.exe"),
    ("--tts-workspace", "private-marker"), ("--tts-device", "cpu"),
    ("--tts-sdk-source-dir", "private-marker"), ("--tts-timeout", "300"),
    ("--tts-voice-profile", "baseline"), ("--tts-reference-start", "0"),
    ("--tts-reference-duration", "10"),
    ("--tts-reference-transcript", "private-marker"), ("--tts-seed", "0"),
    ("--tts-transcript-confirmed", None), ("--tts-show-output-path", None),
])
def test_actual_parser_cannot_hide_supplied_tts_flag(flag, value):
    args = parser().parse_args([flag] if value is None else [flag, value])
    with pytest.raises(ValueError, match="^transcript_tts_config_refused$"):
        options.transcript_tts_config(args)


@pytest.mark.parametrize("missing", ["tts_engine", "tts_reference", "tts_model_dir",
                                    "tts_python"])
def test_enabled_configuration_requires_explicit_engine_and_local_inputs(missing):
    with pytest.raises(ValueError, match="^transcript_tts_config_refused$"):
        options.transcript_tts_config(configured(**{missing: None}))


def test_show_path_option_does_not_promise_private_absolute_path():
    help_text = parser().format_help()
    assert "safe temporary artifact locator" in help_text
    assert "private paths stay redacted" in help_text


def test_core_authorization_is_not_audio_authorization():
    args = parser().parse_args(["--authorized"])
    assert options.transcript_tts_config(args) is None
    args = parser().parse_args(["--authorized", "--tts-engine", "qwen3_tts"])
    with pytest.raises(ValueError, match="^transcript_tts_config_refused$"):
        options.transcript_tts_config(args)


@pytest.mark.parametrize("field", options._FIELDS)
def test_any_tts_option_requires_its_own_opt_in(field):
    values = {field: True if field.endswith(("authorized", "confirmed", "path"))
              else "private-marker"}
    if field == "tts_authorized":
        values[field] = False
    with pytest.raises(ValueError, match="^transcript_tts_config_refused$") as error:
        options.transcript_tts_config(argparse.Namespace(**values))
    assert "private-marker" not in str(error.value)


@pytest.mark.parametrize("value", [False, 0, 1, "true", [], {}, None])
def test_authorization_is_not_coerced(value):
    with pytest.raises(ValueError, match="^transcript_tts_config_refused$"):
        options.transcript_tts_config(configured(tts_authorized=value))


def test_enabled_defaults_and_paths_without_filesystem_io(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("pure option validation inspected filesystem")

    for name in ("stat", "lstat", "exists", "is_file", "is_dir", "resolve", "open"):
        monkeypatch.setattr(Path, name, forbidden)
    config = options.transcript_tts_config(configured())
    assert config.authorized is True
    assert config.engine == "qwen3_tts"
    assert config.reference_path == Path("C:/private-marker/reference.wav")
    assert config.model_dir == Path("C:/private-marker/model")
    assert config.python_executable == Path("C:/private-marker/python.exe")
    assert config.workspace_root == ROOT
    assert config.device == "cpu"
    assert config.timeout_seconds == 300
    assert config.voice_profile == "baseline"
    assert config.reference_start_seconds == 0
    assert config.reference_duration_seconds == 10
    assert config.reference_transcript is None
    assert config.transcript_confirmed is False
    assert config.seed is None
    assert config.sdk_source_dir is None


def test_all_options_preserve_values_and_reference_transcript():
    exact = "  A referência diz isto.\r\nSem normalizar acentuação: cafe\u0301.  "
    args = parser().parse_args([
        "--tts-authorized", "--tts-engine", "qwen3_tts",
        "--tts-reference", "C:/private-marker/reference.wav",
        "--tts-model-dir", "C:/private-marker/model",
        "--tts-python", "C:/private-marker/python.exe",
        "--tts-workspace", "C:/private-marker/workspace",
        "--tts-device", "cuda:0",
        "--tts-timeout", "120", "--tts-voice-profile", "qwen_icl",
        "--tts-reference-start", "12.5", "--tts-reference-duration", "8.5",
        "--tts-reference-transcript", exact, "--tts-transcript-confirmed",
        "--tts-seed", "42", "--tts-show-output-path",
    ])
    config = options.transcript_tts_config(args)
    assert config.workspace_root == Path("C:/private-marker/workspace")
    assert config.device == "cuda:0"
    assert config.sdk_source_dir is None
    assert config.timeout_seconds == 120
    assert config.voice_profile == "qwen_icl"
    assert config.reference_start_seconds == 12.5
    assert config.reference_duration_seconds == 8.5
    assert config.reference_transcript == exact
    assert config.transcript_confirmed is True
    assert config.seed == 42
    assert args.tts_show_output_path is True


def test_chatterbox_profile_can_be_selected():
    config = options.transcript_tts_config(configured(
        tts_engine="chatterbox_pt_br", tts_voice_profile="chatterbox_conversational",
        tts_sdk_source_dir="C:/private-marker/sdk",
    ))
    assert config.voice_profile == "chatterbox_conversational"
    assert config.sdk_source_dir == Path("C:/private-marker/sdk")


@pytest.mark.parametrize("field", ["tts_reference", "tts_model_dir", "tts_python",
                                  "tts_workspace", "tts_sdk_source_dir"])
@pytest.mark.parametrize("value", ["", "  ", 5, True, [], {}, object()])
def test_path_arguments_are_not_coerced(field, value):
    with pytest.raises(ValueError, match="^transcript_tts_config_refused$"):
        options.transcript_tts_config(configured(**{field: value}))


@pytest.mark.parametrize("field", ["tts_transcript_confirmed", "tts_show_output_path"])
@pytest.mark.parametrize("value", [0, 1, "true", [], {}])
def test_boolean_options_are_strict(field, value):
    with pytest.raises(ValueError, match="^transcript_tts_config_refused$"):
        options.transcript_tts_config(configured(**{field: value}))


@pytest.mark.parametrize("changes", [
    {"tts_engine": "private-marker"}, {"tts_engine": None},
    {"tts_device": "private-marker"}, {"tts_timeout": float("inf")},
    {"tts_timeout": float("nan")}, {"tts_timeout": True}, {"tts_timeout": -1},
    {"tts_voice_profile": "private-marker"},
    {"tts_reference_start": float("nan")}, {"tts_reference_start": -1},
    {"tts_reference_duration": 2}, {"tts_reference_duration": 16},
    {"tts_seed": True}, {"tts_seed": -1}, {"tts_seed": 2**32},
    {"tts_reference_transcript": "private-marker"},
    {"tts_transcript_confirmed": True},
    {"tts_engine": "qwen3_tts", "tts_voice_profile": "chatterbox_conversational"},
    {"tts_engine": "chatterbox_pt_br", "tts_voice_profile": "qwen_icl"},
    {"tts_engine": "qwen3_tts", "tts_sdk_source_dir": "C:/private-marker/sdk"},
    {"tts_voice_profile": "qwen_icl", "tts_reference_transcript": "private-marker",
     "tts_transcript_confirmed": False},
])
def test_invalid_adapter_configuration_is_refused_without_private_details(changes):
    with pytest.raises(ValueError, match="^transcript_tts_config_refused$") as error:
        options.transcript_tts_config(configured(**changes))
    assert "private-marker" not in str(error.value)
    assert error.value.__cause__ is None


def test_adapter_validator_failure_is_sanitized(monkeypatch):
    def private_error(config):
        raise RuntimeError("C:/private-marker/reference.wav private transcript")

    monkeypatch.setattr(options, "validate_local_tts_config", private_error)
    with pytest.raises(ValueError, match="^transcript_tts_config_refused$") as error:
        options.transcript_tts_config(configured())
    assert "private-marker" not in str(error.value)
    assert error.value.__cause__ is None


def test_no_options_never_calls_adapter_validator(monkeypatch):
    monkeypatch.setattr(options, "validate_local_tts_config",
                        lambda config: pytest.fail("text-only call validated audio"))
    assert options.transcript_tts_config(argparse.Namespace()) is None


def _no_read_or_core(monkeypatch):
    from apps.jarvis_console import cli, transcript_review_cli

    def forbidden(*args, **kwargs):
        pytest.fail("invalid CLI/TTS options reached stdin or Core")

    monkeypatch.setattr(transcript_review_cli, "_read_envelope", forbidden)
    monkeypatch.setattr(cli.JarvisConsole, "build", forbidden)
    return forbidden


@pytest.mark.parametrize("output_format", ["text", "json"])
@pytest.mark.parametrize("private_arguments", [
    ["--tts-timeout", "C:/private-marker/private transcript"],
    ["--tts-seed", "private-marker"],
    ["--tts-reference-start", "private-marker"],
    ["--tts-reference-duration", "private-marker"],
    ["--tts-private-marker", "C:/private-marker/reference.wav"],
    ["--tts-reference-transcript", "private-marker-reference", "--tts-private-marker"],
])
def test_real_cli_parse_errors_hide_private_arguments_before_stdin_or_core(
    monkeypatch, capsys, output_format, private_arguments,
):
    from apps.jarvis_console import cli

    _no_read_or_core(monkeypatch)
    assert cli.main(["--format", output_format, "transcript-review", "--authorized",
                     *private_arguments]) == 2
    captured = capsys.readouterr()
    assert "private-marker" not in captured.out + captured.err
    assert "Invalid review command usage" in captured.out + captured.err
    if output_format == "json":
        encoded = captured.out or captured.err
        error = json.loads(encoded)
        assert error["command_id"] == "transcript-review"
        assert error["error_code"] == "invalid_cli_usage"


@pytest.mark.parametrize("changes", [
    {"tts_authorized": False}, {"tts_authorized": 1},
    {"tts_engine": "private-marker"}, {"tts_reference": "private-marker.wav"},
    {"tts_reference": "C:/private-marker/ref.wav:alternate-stream"},
    {"tts_reference": "//private-marker/share/reference.wav"},
    {"tts_reference": "C:/private-marker/../reference.wav"},
    {"tts_timeout": float("nan")}, {"tts_timeout": 1801},
    {"tts_seed": 2**32}, {"tts_reference_start": True},
    {"tts_reference_duration": 2}, {"tts_show_output_path": "private-marker"},
    {"tts_voice_profile": "qwen_icl", "tts_reference_transcript": "private-marker"},
])
def test_run_handoff_refuses_bad_tts_configuration_before_stdin_or_core(monkeypatch, changes):
    from apps.jarvis_console.runtime import ConsoleCommandError
    from apps.jarvis_console.transcript_review_cli import run_transcript_review

    factory = _no_read_or_core(monkeypatch)
    args = configured(**changes)
    args.authorized = True
    args.include_content = False
    args.session_id = "tts-options-boundary"
    with pytest.raises(ConsoleCommandError, match="Transcript handoff refused") as error:
        run_transcript_review(args, factory)
    assert error.value.error_code == "transcript_handoff_refused"
    assert "private-marker" not in str(error.value)


def test_actual_parser_text_only_path_retains_legacy_defaults(monkeypatch):
    from apps.jarvis_console import cli

    args = cli.build_parser().parse_args(["transcript-review", "--authorized"])
    assert args.authorized is True
    assert args.include_content is False
    assert args.session_id == "transcript-review"
    assert all(getattr(args, field) is None for field in options._FIELDS)
    monkeypatch.setattr(options, "validate_local_tts_config",
                        lambda config: pytest.fail("text-only parser activated audio"))
    assert options.transcript_tts_config(args) is None


def test_output_locator_contains_no_private_base_path():
    from apps.jarvis_console.transcript_review_cli import _tts_location

    directory = f"jarvis-voice-lab-{'a' * 32}-synthetic_suffix"
    path = Path(tempfile.gettempdir()).absolute() / directory / "sample.wav"
    result = SimpleNamespace(status="completed", output_path=str(path))
    assert _tts_location(result) == {
        "base": "system_temporary_directory", "relative_path": f"{directory}/sample.wav",
    }


@pytest.mark.parametrize("relative,status", [
    (f"jarvis-voice-lab-{'a' * 32}-safe/sample.wav", "failed"),
    (f"jarvis-voice-lab-{'a' * 32}-safe/other.wav", "completed"),
    (f"jarvis-voice-lab-{'a' * 32}-safe/nested/sample.wav", "completed"),
    ("private-marker/sample.wav", "completed"),
    ("jarvis-voice-lab-not-a-uuid-safe/sample.wav", "completed"),
    (f"jarvis-voice-lab-{'a' * 32}-private marker/sample.wav", "completed"),
    (f"jarvis-voice-lab-{'a' * 32}-safe/../sample.wav", "completed"),
])
def test_output_locator_refuses_non_lab_paths_or_incomplete_results(relative, status):
    from apps.jarvis_console.transcript_review_cli import _tts_location

    path = Path(tempfile.gettempdir()).absolute() / relative
    assert _tts_location(SimpleNamespace(status=status, output_path=str(path))) is None


def test_output_locator_refuses_relative_path_and_none():
    from apps.jarvis_console.transcript_review_cli import _tts_location

    for value in (None, f"jarvis-voice-lab-{'a' * 32}-safe/sample.wav"):
        assert _tts_location(SimpleNamespace(status="completed", output_path=value)) is None


def test_handoff_bad_tts_main_does_not_query_actual_stdin(monkeypatch, capsys):
    from apps.jarvis_console import cli

    class NoStdin:
        def isatty(self):
            pytest.fail("bad TTS options queried stdin")

        def read(self, *args):
            pytest.fail("bad TTS options read stdin")

    monkeypatch.setattr(sys, "stdin", NoStdin())
    _no_read_or_core(monkeypatch)
    assert cli.main(["--format", "json", "transcript-review", "--authorized",
                     "--tts-reference", "C:/private-marker/reference.wav"]) == 2
    captured = capsys.readouterr()
    assert "private-marker" not in captured.out + captured.err
    assert "transcript_handoff_refused" in captured.out + captured.err
