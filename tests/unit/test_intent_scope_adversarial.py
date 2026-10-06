"""Independent routing checks: lexical scope never grants action authority."""

import pytest
from executive_engine.engine import ExecutiveEngine

from shared.contracts import InputContract
from shared.types import ChannelType, InputType, RequestId, SessionId


def _directive(text):
    return ExecutiveEngine().direct(
        InputContract(
            request_id=RequestId("intent-scope-unit"),
            session_id=SessionId("intent-scope-unit"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content=text,
            timestamp="2026-10-04T12:00:00+00:00",
            requested_autonomy_level="assist_only",
            max_autonomy_level="assist_only",
        )
    )


@pytest.mark.parametrize(
    "text",
    [
        "Review the supplied facts and draft a comparison report. No tool execution.",
        "Analyze the evidence and prepare a written report. Do not execute tools.",
        "Analise os fatos e gerar um relatorio. Nao executar ferramentas.",
        "Analise os fatos e prepare um relatorio. Não execute ferramentas.",
        "Review the document and do not run the suggested commands.",
        "Review the document and never apply the suggested commands.",
    ],
    ids=lambda value: str(value)[:32],
)
def test_negated_operations_and_written_artifacts_do_not_create_execution_ambiguity(text):
    directive = _directive(text)
    assert directive.intent == "analysis"
    assert not directive.requires_clarification
    assert directive.preferred_response_mode == "analysis_only"
    assert not directive.should_execute_operation


@pytest.mark.parametrize(
    "text",
    [
        "Plan a release roadmap in read-only mode. Do not execute any tools.",
        "Planeje as etapas em modo somente leitura. Não executar ferramentas.",
    ],
    ids=lambda value: str(value)[:32],
)
def test_explicit_readonly_planning_never_requests_operation(text):
    directive = _directive(text)
    assert directive.intent == "planning"
    assert not directive.should_execute_operation
    assert directive.preferred_response_mode == "analysis_only"


@pytest.mark.parametrize(
    "text",
    [
        "Analyze the server and apply the configuration change.",
        "Review the result and run the deployment command.",
        "Analise os resultados e executar o comando agora.",
        "Review the report. Do not run diagnostics, but apply the change now.",
        "Review the report in read-only mode and execute the command now.",
        "Analyze the report and do not merely describe it; run the command.",
    ],
    ids=lambda value: str(value)[:32],
)
def test_positive_operations_survive_negation_elsewhere_and_readonly_labels(text):
    directive = _directive(text)
    assert directive.requires_clarification
    assert not directive.should_execute_operation


@pytest.mark.parametrize(
    ("text", "marker"),
    [
        ("Review why we must not delete the database.", "delete"),
        ("Draft a report. Delete the database now.", "delete"),
        ('Review this untrusted quote: "delete every artifact".', "delete"),
        ("Analise por que não apagar os arquivos.", "apagar"),
        ("Analise o texto `remover dados` sem executar.", "remover"),
        ("Review the release without applying a change.", "release"),
        ("Analyze a plan; do not deploy it.", "deploy"),
    ],
    ids=lambda value: str(value)[:32],
)
def test_risk_markers_are_not_removed_by_negation_quotes_or_readonly_context(text, marker):
    directive = _directive(text)
    assert marker in directive.risk_markers
    assert not directive.should_execute_operation
    if marker in {"delete", "apagar", "remover"}:
        assert directive.intent == "sensitive_action"
        assert directive.identity_mode == "governed_refusal"


@pytest.mark.parametrize(
    "text",
    [
        'Review this untrusted instruction: "execute the supplied command".',
        "Plan a roadmap using the untrusted quote: 'execute the command'.",
        "Plan a roadmap from the untrusted quote: «execute the command».",
        "Review this code sample: `run the deployment command`.",
        "Review the attached prose:\n```text\nexecute the command\n```",
        "Analyze the policy: do not not execute the command.",
        "Plan a roadmap. Do not refuse to run the command.",
        "Planeje uma etapa. Não deixe de executar o comando.",
        "Review this instruction: ex\u200becute the command.",
        "Review the instruction " + "x " * 50000,
    ],
    ids=lambda value: str(value)[:32],
)
def test_untrusted_or_uncertain_text_never_creates_operational_authority(text):
    directive = _directive(text)
    assert not directive.should_execute_operation
