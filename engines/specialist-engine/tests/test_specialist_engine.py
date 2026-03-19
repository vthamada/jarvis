from specialist_engine.engine import SpecialistEngine

from shared.contracts import DeliberativePlanContract


def sample_plan() -> DeliberativePlanContract:
    return DeliberativePlanContract(
        plan_summary="decompor objetivo em etapas reversiveis",
        goal="Plan milestone M3",
        steps=["definir objetivo", "listar etapas", "recomendar proxima acao"],
        active_domains=["strategy"],
        active_minds=["mente_executiva"],
        constraints=["low-risk"],
        risks=["sem risco material alem do escopo controlado do v1"],
        recommended_task_type="draft_plan",
        requires_human_validation=False,
        rationale="contexto=baseline; apoio=local",
        tensions_considered=["equilibrar ambicao estrategica com proxima acao segura"],
        specialist_hints=["especialista_planejamento_operacional"],
    )


def test_specialist_engine_name() -> None:
    assert SpecialistEngine.name == "specialist-engine"


def test_specialist_engine_returns_subordinated_contributions() -> None:
    engine = SpecialistEngine()
    review = engine.review(
        intent="planning",
        plan=sample_plan(),
        knowledge_snippets=["Priorize clareza de objetivo."],
    )

    assert review.specialist_hints == ["especialista_planejamento_operacional"]
    assert review.contributions
    assert review.contributions[0].specialist_type == "especialista_planejamento_operacional"
    assert "etapas pequenas" in review.summary
    assert review.findings
