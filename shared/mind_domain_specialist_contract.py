"""Helpers for the sovereign mind->domain->specialist arbitration contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MindDomainSpecialistContractView:
    """Explicit contract slice for the last-mile arbitration chain."""

    status: str
    summary: str | None
    chain: str | None
    active_specialist: str | None
    override_mode: str | None
    fallback_mode: str | None


@dataclass(frozen=True)
class MindDomainSpecialistRuntimePolicy:
    """Runtime policy derived from the explicit arbitration contract."""

    effective_specialists: tuple[str, ...]
    authoritative_specialist: str | None
    consumer_mode: str
    framing_mode: str
    continuity_mode: str
    fallback_note: str | None


def build_mind_domain_specialist_runtime_policy(
    *,
    contract_status: str | None,
    active_specialist: str | None,
    planned_specialists: list[str] | None = None,
    authoritative_specialist_hint: str | None = None,
    override_mode: str | None = None,
    fallback_mode: str | None = None,
) -> MindDomainSpecialistRuntimePolicy:
    """Return the effective runtime policy for selection, dispatch, and framing."""

    ordered_specialists: list[str] = []
    for specialist in [
        authoritative_specialist_hint,
        active_specialist,
        *(planned_specialists or []),
    ]:
        if specialist and specialist not in ordered_specialists:
            ordered_specialists.append(specialist)

    authoritative_specialist = ordered_specialists[0] if ordered_specialists else None
    status = contract_status or "not_applicable"

    if status == "authoritative_chain":
        return MindDomainSpecialistRuntimePolicy(
            effective_specialists=tuple(
                [authoritative_specialist] if authoritative_specialist else []
            ),
            authoritative_specialist=authoritative_specialist,
            consumer_mode="authoritative_specialist",
            framing_mode="route_and_specialist_locked",
            continuity_mode="preserve_authoritative_chain",
            fallback_note=None,
        )

    if status == "bounded_override":
        return MindDomainSpecialistRuntimePolicy(
            effective_specialists=tuple(
                [authoritative_specialist] if authoritative_specialist else []
            ),
            authoritative_specialist=authoritative_specialist,
            consumer_mode="bounded_override_specialist",
            framing_mode="override_bounded_to_active_specialist",
            continuity_mode="preserve_override_without_reopening_chain",
            fallback_note=override_mode,
        )

    if status == "bounded_degradation":
        return MindDomainSpecialistRuntimePolicy(
            effective_specialists=tuple(
                [authoritative_specialist] if authoritative_specialist else []
            ),
            authoritative_specialist=authoritative_specialist,
            consumer_mode="degraded_specialist",
            framing_mode="core_mediated_degraded_specialist",
            continuity_mode="contain_partial_chain",
            fallback_note=fallback_mode or "specialist_without_full_chain",
        )

    if status == "governed_fallback":
        return MindDomainSpecialistRuntimePolicy(
            effective_specialists=(),
            authoritative_specialist=None,
            consumer_mode="core_only_fallback",
            framing_mode="core_only_governed_fallback",
            continuity_mode="continue_without_specialist_handoff",
            fallback_note=fallback_mode or "core_guidance_without_handoff",
        )

    return MindDomainSpecialistRuntimePolicy(
        effective_specialists=tuple(ordered_specialists),
        authoritative_specialist=authoritative_specialist,
        consumer_mode="not_applicable",
        framing_mode="default_runtime_framing",
        continuity_mode="default_runtime_continuity",
        fallback_note=fallback_mode,
    )


def build_mind_domain_specialist_contract(
    *,
    primary_mind: str | None,
    primary_domain_driver: str | None,
    primary_route: str | None = None,
    planned_specialists: list[str] | None = None,
    selected_specialists: list[str] | None = None,
    active_route: str | None = None,
    arbitration_source: str | None = None,
    capability_handoff_mode: str | None = None,
) -> MindDomainSpecialistContractView:
    """Return a bounded contract describing the effective arbitration chain."""

    planned_specialist = next(
        (item for item in (planned_specialists or []) if item),
        None,
    )
    selected_specialist = next(
        (item for item in (selected_specialists or []) if item),
        None,
    )
    active_specialist = selected_specialist or planned_specialist
    effective_route = active_route or primary_route

    if not any(
        (
            primary_mind,
            primary_domain_driver,
            primary_route,
            active_route,
            active_specialist,
        )
    ):
        return MindDomainSpecialistContractView(
            status="not_applicable",
            summary=None,
            chain=None,
            active_specialist=None,
            override_mode=None,
            fallback_mode=None,
        )

    chain = " -> ".join(
        [
            primary_mind or "none",
            primary_domain_driver or "none",
            effective_route or "none",
            active_specialist or "none",
        ]
    )

    override_mode = None
    if arbitration_source == "mind_registry_recomposition":
        override_mode = "mind_registry_recomposition"
    elif (
        planned_specialist is not None
        and selected_specialist is not None
        and planned_specialist != selected_specialist
    ):
        override_mode = "specialist_override"
    elif (
        primary_route is not None
        and active_route is not None
        and primary_route != active_route
    ):
        override_mode = "route_override"

    has_authoritative_chain = bool(
        primary_mind and primary_domain_driver and active_specialist
    )
    has_partial_chain = bool(primary_mind or primary_domain_driver or effective_route)

    if has_authoritative_chain and override_mode is None:
        return MindDomainSpecialistContractView(
            status="authoritative_chain",
            summary=(
                "cadeia soberana autoritativa preserva "
                f"{primary_mind} -> {primary_domain_driver}"
                f"{f' -> {effective_route}' if effective_route else ''} -> "
                f"{active_specialist}"
            ),
            chain=chain,
            active_specialist=active_specialist,
            override_mode=None,
            fallback_mode=None,
        )

    if has_authoritative_chain and override_mode is not None:
        return MindDomainSpecialistContractView(
            status="bounded_override",
            summary=(
                "cadeia soberana preservada com override bounded em "
                f"{override_mode}: {primary_mind} -> {primary_domain_driver}"
                f"{f' -> {effective_route}' if effective_route else ''} -> "
                f"{active_specialist}"
            ),
            chain=chain,
            active_specialist=active_specialist,
            override_mode=override_mode,
            fallback_mode=None,
        )

    if has_partial_chain and active_specialist is not None:
        return MindDomainSpecialistContractView(
            status="bounded_degradation",
            summary=(
                "cadeia soberana parcial manteve especialista bounded sem "
                "autoridade completa na ultima milha"
            ),
            chain=chain,
            active_specialist=active_specialist,
            override_mode=override_mode,
            fallback_mode="specialist_without_full_chain",
        )

    fallback_mode = (
        "core_guidance_without_handoff"
        if capability_handoff_mode in {"none", None}
        else "core_guidance_without_selected_specialist"
    )
    if has_partial_chain:
        return MindDomainSpecialistContractView(
            status="governed_fallback",
            summary=(
                "cadeia soberana permaneceu contida no nucleo com fallback governado "
                "na ultima milha"
            ),
            chain=chain,
            active_specialist=None,
            override_mode=override_mode,
            fallback_mode=fallback_mode,
        )

    return MindDomainSpecialistContractView(
        status="governed_fallback",
        summary=(
            "especialista permaneceu bounded sem cadeia soberana completa e exigiu "
            "fallback governado"
        ),
        chain=chain,
        active_specialist=active_specialist,
        override_mode=override_mode,
        fallback_mode="specialist_hint_only",
    )
