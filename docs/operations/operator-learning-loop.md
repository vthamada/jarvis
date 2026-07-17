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
python -m apps.jarvis_console mission-workflow "Plan the controlled rollout." --mission-id mission-demo
```

2. Ver o ciclo completo de uma missao ja executada:

```powershell
python -m apps.jarvis_console mission-cycle --mission-id mission-demo
```

3. Abrir o cockpit diario consolidado:

```powershell
python -m apps.jarvis_console operator-dashboard --mission-id mission-demo
```

O cockpit e read-only. Ele consolida objetivo, proxima acao, work items,
checkpoints, artefatos, experiencia/reflexao, revisao evolutiva, memoria usada,
autonomia, promotion gate e decisoes humanas pendentes. Os campos
`cockpit_status`, `pending_decisions` e `next_operator_decision` indicam o que
o operador precisa decidir primeiro; o comando nao executa a decisao.

Para selecionar trabalho entre varias missoes/sessoes antes da inspecao
detalhada, use:

```powershell
python -m apps.jarvis_console daily-workspace
```

O workspace multi-missao mostra somente loops abertos, freshness, revisoes e a
proxima decisao. Dentro da missao, prioridade `p0..p3` e dependencias sao lidas
do estado canonico criado pelo operador; o workspace nao inventa prioridade,
nao retoma missao e nao agenda execucao.

Para criar e inspecionar uma cadeia governada de work items:

```powershell
python -m apps.jarvis_console work-item --mission-id mission-demo --action create --work-item-ref work-item://mission-demo/foundation --priority p1
python -m apps.jarvis_console work-item --mission-id mission-demo --action create --work-item-ref work-item://mission-demo/release --depends-on work-item://mission-demo/foundation --priority p0
python -m apps.jarvis_console work-items --mission-id mission-demo
```

O segundo item permanece `dependency_blocked` ate a conclusao do primeiro. A
ordem e somente recomendacao read-only; `autonomous_execution_allowed=False`
permanece fixo. O fluxo completo esta em
`docs/operations/governed-work-item-queue.md`.

4. Gerar um relatorio humano compacto de progresso:

```powershell
python -m apps.jarvis_console progress-report --mission-id mission-demo
```

O relatorio e sintetizado a partir do estado canonico da missao, estrategia de
horizonte longo, artefatos, experiencia/reflexao e sinais observaveis de
memoria. Ele nao grava estado nem executa a proxima acao.

5. Registrar feedback explicito apos a missao:

```powershell
python -m apps.jarvis_console mission-feedback --mission-id mission-demo --assessment correction --rating 2 --comment "faltou evidencia de release" --correction "validar evidencia antes da recomendacao" --next-expectation "mostrar evidencia e rollback" --evidence-ref evidence://mission-demo/release
```

O comando passa por governanca, atualiza a experiencia/reflexao canonica e
cria uma proposta sandbox em `needs_review`. Ele nao aplica a correcao como
regra, nao promove a proposta e nao muta o Core.

6. Consultar experiencias/reflexoes recentes:

```powershell
python -m apps.jarvis_console experience-reflections --mission-id mission-demo
```

7. Consultar propostas aguardando revisao humana:

```powershell
python -m apps.jarvis_console evolution-review-queue
```

8. Registrar decisao humana sobre uma proposta:

```powershell
python -m apps.jarvis_console evolution-review --proposal-id proposal-123 --action approve --evidence-ref evidence://eval/123 --proposed-test tests/unit/test_learning_loop.py --rollback-plan-ref rollback://proposal-123
```

9. Inspecionar a cadeia de evolucao de skills sem executar ou promover:

```powershell
python -m apps.jarvis_console skill-evolution --workflow-profile software_change_workflow
```

A leitura correlaciona pattern evidence, candidata inativa, proposta, review,
sandbox, testes, rollback e blockers. O guia detalhado esta em
`docs/operations/skill-evolution-operator-surface.md`. Mesmo um sandbox verde
permanece pendente de release e promocao humana separada.

## Como interpretar a saida

- `mission_workflow_status=closed_with_human_review_pending`: o workflow rodou
  e terminou com proposta aguardando revisao humana.
- `experience_recorded=True`: a missao gerou `experience_record`.
- `post_task_reflection_recorded=True`: a experiencia gerou
  `post_task_reflection` bounded.
- `review_status=needs_review`: existe proposta evolutiva, mas ela ainda nao
  foi aprovada.
- `operator_feedback_status=recorded`: o feedback passou pela governanca e foi
  anexado ao registro canonico.
- `feedback_memory_status=recorded_bounded`: o conteudo foi normalizado e
  persistido dentro dos limites do contrato.
- `evolution_review_status=needs_review`: o feedback gerou candidato revisavel,
  nao uma mudanca ativa.
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
- `cockpit_status=operator_decision_required|ready_for_next_action|idle`: resume
  se existe decisao humana, proxima acao pronta ou ausencia de trabalho ativo.
- `pending_decisions=...`: ordena revisao evolutiva, blockers do promotion
  gate, confirmacao de autonomia e checkpoints pendentes.
- `next_operator_decision=...`: aponta a primeira decisao humana recomendada,
  sem executa-la.
- `promotion_gate_status=passed|blocked|not_applicable`: mostra o resultado do
  gate; mesmo `passed` preserva `promotion_gate_promotion_authorized=False`.
- `mission_progress_report=read_only`: identifica o relatorio derivado, sem
  escrita de memoria.
- `report_status=completed|in_progress|blocked|needs_operator_decision|unavailable`:
  resume o estado humano do progresso.
- `progress_summary=...`: mostra contagens de work items ativos, artefatos,
  checkpoints, decisoes pendentes e proxima acao.
- o bloco apos `---` e a leitura humana sintetizada de missao, progresso,
  pendencias, riscos, memoria, aprendizado, estrategia e proxima acao.

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
python -m apps.jarvis_console evolution-review --proposal-id proposal-123 --action sandbox --evidence-ref evidence://pilot/123 --proposed-test tests/unit/test_operator_learning_loop.py --rollback-plan-ref rollback://proposal-123 --note "validar em piloto antes de qualquer promocao"
```

Para rejeitar:

```powershell
python -m apps.jarvis_console evolution-review --proposal-id proposal-123 --action reject --note "evidencia insuficiente"
```

Para rollback:

```powershell
python -m apps.jarvis_console evolution-review --proposal-id proposal-123 --action rollback --rollback-plan-ref rollback://proposal-123 --note "reverter candidato sandbox"
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
