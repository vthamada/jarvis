# Operator Learning Loop

Este guia descreve o uso humano real do ciclo operacional:

`usar -> registrar -> refletir -> propor -> revisar -> medir`

O ciclo existe para transformar uma missao governada em experiencia auditavel,
reflexao bounded e proposta evolutiva revisavel por humano. Ele nao promove
mudancas sozinho, nao altera pesos, nao executa self-modification e nao bypassa
governanca, memoria canonica ou sintese final.

## Fluxo rapido

1. Iniciar uma missao governada:

```powershell
python -m apps.jarvis_console.cli mission-workflow "Plan the controlled rollout." --mission-id mission-demo
```

2. Ver o ciclo completo de uma missao ja executada:

```powershell
python -m apps.jarvis_console.cli mission-cycle --mission-id mission-demo
```

3. Consultar experiencias/reflexoes recentes:

```powershell
python -m apps.jarvis_console.cli experience-reflections --mission-id mission-demo
```

4. Consultar propostas aguardando revisao humana:

```powershell
python -m apps.jarvis_console.cli evolution-review-queue
```

5. Registrar decisao humana sobre uma proposta:

```powershell
python -m apps.jarvis_console.cli evolution-review --proposal-id proposal-123 --action approve --evidence-ref evidence://eval/123 --proposed-test tests/unit/test_learning_loop.py --rollback-plan-ref rollback://proposal-123
```

## Como interpretar a saida

- `mission_workflow_status=closed_with_human_review_pending`: o workflow rodou
  e terminou com proposta aguardando revisao humana.
- `experience_recorded=True`: a missao gerou `experience_record`.
- `post_task_reflection_recorded=True`: a experiencia gerou
  `post_task_reflection` bounded.
- `review_status=needs_review`: existe proposta evolutiva, mas ela ainda nao
  foi aprovada.
- `automatic_promotion=False`: nenhuma mudanca foi promovida automaticamente.
- `next_operator_step=review_evolution_proposal`: o proximo passo humano e
  revisar a proposta, seus blockers, testes e rollback.
- `evolution_review_decision_status=approved|rejected|sandboxed|needs_review|rolled_back`:
  a proposta recebeu uma decisao humana auditavel.
- `evolution_review_limits=automatic_promotion_blocked,core_mutation_blocked`:
  a revisao foi registrada sem liberar autopromocao ou mutacao do nucleo.
- `reviewed_learning_influence_status=applied|no_relevant_guidance|no_workflow_profile`:
  mostra se um aprendizado humano revisado influenciou a missao atual.
- `reviewed_learning_influence_refs=...`: lista os guidance refs usados; `none`
  significa que a execucao rodou como baseline sem aprendizado revisado.
- `reviewed_learning_influence_reason=...`: explica por que o guidance foi
  aplicado ou bloqueado por escopo.
- `reviewed_learning_assisted_eval_status=reviewed_learning_assisted|baseline_no_reviewed_learning`:
  indica se a execucao entrou na comparacao assisted ou permaneceu baseline.
- `reviewed_learning_release_conclusion=no_promotion_without_release_gate`:
  mesmo quando ha ganho aparente, o sistema nao promove mudanca sem gate de
  release e revisao humana.

## Revisao humana

Antes de aprovar qualquer aprendizado, o operador deve verificar:

- evidencia da missao e do resultado;
- se a reflexao e especifica e bounded;
- se `proposed_tests` cobre o fluxo afetado;
- se existe `rollback_plan_ref`;
- se a proposta nao substitui o nucleo nem viola soberania;
- se o ganho foi medido por piloto/eval e nao apenas assumido.

### Comandos de decisao

As decisoes disponiveis sao:

- `approve`: aceita a proposta como decisao humana, mas ainda nao promove
  mudanca automaticamente.
- `reject`: rejeita a proposta e preserva o historico.
- `sandbox`: mantem a proposta em experimento controlado.
- `needs-review`: devolve a proposta para revisao com notas adicionais.
- `rollback`: registra necessidade de rollback ou reversao controlada.

Para `approve` e `sandbox`, informe evidencia, testes propostos e rollback:

```powershell
python -m apps.jarvis_console.cli evolution-review --proposal-id proposal-123 --action sandbox --evidence-ref evidence://pilot/123 --proposed-test tests/unit/test_operator_learning_loop.py --rollback-plan-ref rollback://proposal-123 --note "validar em piloto antes de qualquer promocao"
```

Para rejeitar:

```powershell
python -m apps.jarvis_console.cli evolution-review --proposal-id proposal-123 --action reject --note "evidencia insuficiente"
```

Para rollback:

```powershell
python -m apps.jarvis_console.cli evolution-review --proposal-id proposal-123 --action rollback --rollback-plan-ref rollback://proposal-123 --note "reverter candidato sandbox"
```

Esses comandos registram decisao, operador, evidencia, testes, rollback e
limites. Eles nao executam promocao automatica, nao alteram pesos e nao mutam o
nucleo soberano.

## Medicao

O baseline atual mede uso de reflexao e aprendizado revisado em:

- `observability-service`, por `reflection_influence_status` e
  `reflection_assisted_eval_status`;
- `observability-service`, por `reviewed_learning_influence_status`, refs,
  motivo, `reviewed_learning_assisted_eval_status` e conclusao
  `no_promotion_without_release_gate`;
- `tools/internal_pilot_report.py`, que mostra baseline sem reflexao versus
  execucao reflection-assisted e baseline sem aprendizado revisado versus
  execucao reviewed-learning-assisted;
- `tools/compare_orchestrator_paths.py`, que compara divergencias sem tratar
  melhoria local como promocao.

Leitura correta do fluxo `revisar -> influenciar -> medir`:

- decisao humana aprovada ou sandboxada pode gerar `reviewed_learning_guidance`;
- guidance so influencia planejamento/sintese se bater por rota, workflow ou
  dominio;
- toda influencia deve deixar refs, motivo e status auditavel;
- a medicao compara baseline contra assisted;
- nenhuma conclusao de medicao promove mudanca automaticamente.

## Limites atuais

- sem voz;
- sem realtime;
- sem UI rica;
- sem browser/computer use amplo;
- sem scheduler autonomo;
- sem autopromocao;
- sem self-modification;
- sem alteracao de pesos;
- sem aprovacao automatica de proposta evolutiva.

O proximo avanco deve nascer de repriorizacao explicita apos evidencias do uso
humano desse ciclo.
