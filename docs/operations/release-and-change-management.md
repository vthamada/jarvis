# Release And Change Management

## Current documentation baseline

After `MB-152`, documentation cleanup is treated as controlled change. The
current documentation audit artifacts are:

- `docs/documentation/documentation-canonicality-audit-mb151.md`
- `docs/documentation/documentation-backlink-map-mb152.md`

No documentation move, delete, rename or merge should be treated as routine if
the backlink map shows active references or if the document is canonical,
operational, architectural or tied to governance.

## MB-166 Sandbox-To-Release Checklist

Starting with `MB-166`, reviewed learning and evolution candidates must produce
an executable checklist before any release decision. The minimum checklist
contains:

- `human_review_status` equal to `approved` or `sandboxed`;
- reviewable `evidence_refs`;
- `proposed_tests` that validate the candidate;
- a `rollback_plan_ref`;
- the exact `release_scope`;
- `required_gates`, including human review, evidence, tests, rollback, the
  standard engineering gate and a separate release gate;
- `automatic_promotion_allowed=false`;
- `core_mutation_allowed=false`.

`ready_for_release_review` means that the checklist is complete. It is not a
promotion permit. Any blocker retains the candidate in review or sandbox, and
actual promotion still requires a separate release gate and human decision.

## MB-167 Promotion Gate Enforcement

Starting with `MB-167`, the checklist is evaluated into a
`PromotionGateDecisionContract`. The evaluator:

- derives human review, evidence, tests and rollback gates from checklist data;
- accepts only the external `standard_engineering_gate` and
  `release_gate_before_promotion` completion signals;
- adds every missing gate and checklist defect to explicit blockers;
- emits the observable `promotion_gate_evaluated` payload;
- returns `promotion_blocked` whenever any blocker remains.

A passed gate returns `eligible_for_human_promotion_decision` and
`release_gate_passed_pending_human_decision`. It always keeps
`promotion_authorized=false`, `automatic_promotion_allowed=false` and
`core_mutation_allowed=false`. Human authorization remains a separate release
decision outside this gate evaluator.

## MB-179 Skill Candidate Release Chain

Skill candidates add a stricter gate to the generic release checklist. Before
the checklist can become `ready_for_release_review`, the operator must be able
to trace the same skill identity and version through:

1. inactive skill registry candidate;
2. persisted evolution proposal;
3. human review decision with evidence, tests and rollback;
4. `SkillSandboxEvalContract` derived from explicit case checks;
5. sandbox-to-release checklist.

The checklist requires `skill_sandbox_eval` in addition to the standard gates.
Missing, failed or mismatched sandbox evidence blocks release review. A passing
skill eval has status `passed_pending_release_gate`; a passing promotion gate
still has `promotion_authorized=false` and does not activate the skill in
routing, planning or tool execution.

## 1. Objetivo

Este documento operacionaliza a política de **releases, versionamento e mudança controlada** do JARVIS.

Ele deriva principalmente de:

- `documento_mestre_jarvis.md`, capítulo `345. Estratégia de releases, versionamento e mudança controlada`

Seu papel é transformar a política arquitetural de mudança em prática operacional mínima.

---

## 2. Princípios

Toda mudança relevante no projeto deve ser:

- explicitamente versionada;
- rastreável;
- validada antes de promoção;
- reversível quando aplicável;
- avaliada quanto a impacto em contratos, memória e governança.

---

## 3. Classes de mudança

Mudanças devem ser registradas como:

- editorial;
- estrutural sem impacto contratual;
- contratual compatível;
- contratual incompatível;
- operacional;
- governança;
- evolutiva em sandbox;
- promoção evolutiva.

---

## 4. O que deve sempre ser registrado

Para cada mudança relevante, registrar:

- data;
- artefato afetado;
- natureza da mudança;
- motivação;
- impacto esperado;
- risco conhecido;
- forma de validação;
- rollback previsto, quando aplicável.

---

## 5. Versionamento mínimo

Aplicar versionamento explícito em:

- serviços;
- contratos;
- políticas de memória crítica;
- regras de governança;
- componentes promovidos via evolução.

---

## 6. Gates antes de promover mudança

Nenhuma mudança relevante deve ser promovida sem:

- revisão do impacto técnico;
- verificação de contratos afetados;
- testes mínimos aplicáveis;
- análise de risco;
- validação em ambiente compatível com o nível de risco.

---

## 7. Regimes de promoção

Mudanças podem seguir:

- promoção direta de baixo risco;
- promoção gradual;
- promoção condicionada por observação reforçada;
- retenção em sandbox até nova evidência.

---

## 8. Rollback

Toda mudança relevante deve responder:

1. o que volta ao estado anterior?
2. como a reversão será feita?
3. há impacto em memória, estado ou contrato?
4. qual é o gatilho para reverter?

---

## 9. Relação com CHANGELOG e HANDOFF

Usar:

- `CHANGELOG.md` para registrar mudança relevante já consolidada;
- `HANDOFF.md` para registrar impacto operacional e próximos passos;
- Documento-Mestre para regras canônicas e políticas normativas.

---

## 10. Critério prático

Se a mudança altera:

- identidade;
- governança;
- memória crítica;
- autonomia;
- contrato compartilhado;
- operação produtiva;

então ela não deve ser tratada como mudança rotineira simples.
