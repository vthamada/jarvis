# CHANGELOG

## 2026-04-23

### MB-098 fechou continuidade bounded do estado operacional

- `services/memory-service`, `shared/memory_registry.py` e `services/memory-service/src/memory_service/repository.py` agora persistem `ecosystem_state_status`, `active_work_items`, `active_artifact_refs`, `open_checkpoint_refs` e `surface_presence` em `mission_state`, `session_continuity`, `continuity_checkpoint` e `continuity_replay`;
- `services/memory-service` agora usa esse slice para recovery e retomada bounded, priorizando checkpoint operacional, work item ativo ou artefato vivo sem abrir memoria temporal rica fora de fase;
- `services/orchestrator-service` agora injeta `operation_dispatch` e `operation_result` no `memory-service`, e passou a refletir esse estado em `memory_recorded`, `continuity_replay_loaded`, `continuity_subflow_completed` e `mission_runtime_state_declared`;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-098` como concluido e `MB-099` como o item `ready` atual da fila micro.

### MB-097 fechado no contrato minimo de estado operacional

- `shared/contracts`, `shared/schemas` e `shared/events` agora formalizam `ecosystem_state_status`, `active_work_items`, `active_artifact_refs`, `open_checkpoint_refs` e `surface_presence` como gramatica minima de estado operacional do ecossistema;
- `services/orchestrator-service` agora deriva esse estado a partir de missao, workflow, checkpoints e superficie ativa, propagando o payload por `workflow_composed`, `ecosystem_state_declared`, `operation_dispatched`, `operation_completed` e `workflow_completed`;
- `services/operational-service` agora materializa o estado operacional no artefato produzido e no `OperationResultContract`, incluindo refs de artefatos gerados e checkpoints ainda abertos;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-097` como concluido e `MB-098` como o item `ready` atual da fila micro.

## 2026-04-22

### Repriorizacao explicita da ponte `v2 -> v3` para estado operacional do ecossistema

- `docs/implementation/execution-backlog.md` agora abre `MB-097` a `MB-101` como o novo lote ativo, com `MB-097` em `ready` e foco em `SG-002` + `TA-002`;
- o novo lote traduz a ponte `v2 -> v3` em um recorte pequeno: contrato soberano de estado operacional, aplicacao em continuidade/workflow lifecycle, evidencia auditavel, leitura de release e fechamento documental;
- `docs/implementation/unified-gap-and-absorption-backlog.md` foi sincronizado para promover `SG-002` e `TA-002` a `candidate_for_slicing`, registrar `EV-003` como baseline fechado e ordenar `SG-003` + `SO-002` apenas depois do estado operacional minimo do ecossistema;
- `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para sair do estado "sem item ready" e registrar `MB-097` como o proximo passo correto do projeto.

### Fechamento do lote de compile/optimize loops governados

- `shared/optimization_state.py`, `shared/contracts`, `shared/schemas` e `evolution/evolution-lab` agora tratam `optimization_target_kind`, `optimization_candidate_status`, `optimization_safety_status`, `optimization_readiness`, `optimization_release_status` e `optimization_blockers` como contrato soberano do baseline evolutivo;
- `tools/compare_orchestrator_paths.py`, `tools/internal_pilot_report.py`, `tools/evolution_from_pilot.py`, `tools/verify_active_cut_baseline.py`, `tools/verify_release_signal_baseline.py`, `tools/archive/close_alignment_cycle.py` e `tools/archive/close_sovereign_alignment_cut.py` agora tornam oportunidades, bloqueios e seguranca de compile/optimize loops parte formal da leitura comparativa, do baseline ativo e dos artefatos regeneraveis de fechamento;
- a superficie de testes do lote agora cobre `optimization_*` em `evolution-lab`, comparadores, relatorios, verificadores de baseline/release, fechadores regeneraveis e uma bateria sistêmica e2e da `JarvisConsole`;
- `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para fechar `MB-092` a `MB-096`, promover `EV-003` a `resolved_in_baseline` e registrar que a fila micro voltou a ficar sem item `ready`.

## 2026-04-20

### Repriorizacao do proximo lote micro para compile/optimize loops governados

- `docs/implementation/execution-backlog.md` agora abre `MB-092` a `MB-096` como o novo lote ativo, com `MB-092` em `ready` e foco em `EV-003`;
- o novo lote traduz a proxima prioridade macro em uma sequencia micro curta: contrato soberano de otimizacao, candidatos bounded no laboratorio, evidencia auditavel, leitura de release e fechamento documental;
- `docs/implementation/unified-gap-and-absorption-backlog.md` foi sincronizado para registrar que `EV-003` ja foi corretamente fatiado na fila micro, sem reabrir lotes resolvidos nem antecipar frentes fora de fase;
- `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para sair do estado "sem item ready" e registrar `MB-092` como o proximo passo correto do projeto.

### Politica explicita de bateria de testes ponta a ponta para mudancas novas

- `docs/documentation/engineering-constitution.md` agora deixa explicito que toda mudanca relevante deve incluir bateria de testes suficiente para validar o slice local e o fluxo ponta a ponta afetado, elevando esse criterio tambem para `Definition of Done` e para promocoes de capability;
- `AGENTS.md` agora torna essa expectativa obrigatoria para agentes implementadores, evitando que comportamento novo entre no baseline apenas com cobertura local fragmentada;
- `docs/implementation/execution-backlog.md` agora exige estrategia de validacao automatizada ja na `Definition of Ready` e cobra cobertura ponta a ponta ou justificativa explicita de fase na `Definition of Done`;
- `HANDOFF.md` foi sincronizado para registrar que robustez e resiliencia do repositorio agora dependem formalmente dessa bateria de testes para toda implementacao nova relevante.

### Fechamento do lote de evals expandidas e lane controlada da Onda 2

- `shared/eval_expansion.py`, `services/observability-service`, `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`, `evolution/evolution-lab`, `tools/evolution_from_pilot.py` e `tools/verify_release_signal_baseline.py` agora compartilham a gramatica soberana de `expanded_eval_*`, `surface_axis_*`, `ecosystem_state_*`, `experiment_lane_*`, `experiment_exit_*` e `promotion_readiness`;
- `tools/verify_active_cut_baseline.py`, `tools/archive/close_alignment_cycle.py` e `tools/archive/close_sovereign_alignment_cut.py` agora distinguem readiness de eval expandida, saude da lane controlada, status de release do experimento e blockers de promocao sem transformar release em mecanismo de promocao automatica;
- a superficie de testes de comparadores, `observability`, `evolution-lab`, `evolution_from_pilot`, verificadores de release/baseline e fechadores regeneraveis agora trava essa nova fronteira entre baseline soberano e experimento controlado;
- `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para fechar `MB-087` a `MB-091`, promover `EV-002` e `EV-004` a `resolved_in_baseline` e registrar que a fila micro voltou a ficar sem item `ready`.

### Repriorizacao do proximo lote micro para evals expandidas e lane controlada da Onda 2

- `docs/implementation/execution-backlog.md` agora abre `MB-087` a `MB-091` como o novo lote ativo, com `MB-087` em `ready` e foco em `EV-002` + `EV-004`;
- o novo lote traduz a proxima prioridade macro em uma sequencia micro curta: gramatica de eval expandida, observabilidade/cobertura por eixo, lane controlada de experimentos, integracao com gates de release e fechamento documental;
- `docs/implementation/unified-gap-and-absorption-backlog.md` agora promove `SG-006` a `resolved_in_baseline` e atualiza a ordem recomendada para puxar `EV-002` + `EV-004` antes de `EV-003`;
- `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para sair do estado "sem item ready" e registrar `MB-087` como o proximo passo correto do projeto.

### Fechamento do lote de identidade, missao e politica por request

- `shared/contracts`, `shared/schemas`, `planning-engine`, `governance-service` e `orchestrator-service` agora tratam `request_identity_policy` como contrato soberano do runtime, distinguindo missao ativa, postura executiva, autoridade, risco, reversibilidade e confirmacao por request;
- `observability-service`, `internal_pilot_support`, `internal_pilot_report`, `compare_orchestrator_paths`, `evolution-lab`, `evolution_from_pilot` e `verify_release_signal_baseline` agora auditam e refinam `request_identity_status`, `mission_policy_status` e `request_identity_mismatch_flags` como parte do baseline;
- a superficie de testes do lote agora trava a nova gramatica de identidade/politica por request em `orchestrator`, `observability`, comparadores e `evolution-lab`;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para fechar `MB-082` a `MB-086` e registrar que a fila micro voltou a ficar sem item `ready`.

### Repriorizacao do proximo lote micro para identidade, missao e politica por request

- `docs/implementation/execution-backlog.md` agora abre `MB-082` a `MB-086` como o novo lote ativo do nucleo, com `MB-082` em `ready` e foco em formalizar `request_identity_policy` como contrato soberano do runtime;
- o novo lote traduz a prioridade macro `SG-006` em uma sequencia micro curta: contrato, aplicacao governada, observabilidade/tracing, uso evolutivo e fechamento documental;
- `docs/implementation/unified-gap-and-absorption-backlog.md` agora deixa explicito que `SG-001`, `SG-004`, `SG-005`, `TA-001`, `TA-003` e `TA-005` ja foram resolvidos no baseline e corrige a ordem recomendada da proxima fila micro para priorizar `SG-006`;
- `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para sair do estado "sem item ready" e registrar `MB-082` como o proximo passo correto do projeto.

## 2026-04-19

### Fechamento do lote evolutivo da arbitragem declarativa

- `evolution/evolution-lab/src/evolution_lab/service.py`, `tools/evolution_from_pilot.py`, `tools/compare_orchestrator_paths.py` e `tools/verify_release_signal_baseline.py` agora tratam `mind_domain_specialist_effectiveness` e `mind_domain_specialist_mismatch_flags` como insumo formal de `refinement_vectors`, `evaluation_matrix`, metric deltas e leitura de release;
- a superficie de testes de `evolution-lab`, `evolution_from_pilot`, `compare_orchestrator_paths` e `verify_release_signal_baseline` agora trava a nova gramatica evolutiva da arbitragem declarativa, incluindo mismatch, inefetividade e readiness da matriz;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para fechar `MB-080` e `MB-081` e registrar que a fila micro voltou a ficar sem item `ready` ate nova repriorizacao explicita.

## 2026-04-14

### MB-079 fechado na evidencia auditavel da arbitragem declarativa

- `services/observability-service/src/observability_service/service.py` agora publica `mind_domain_specialist_effectiveness` e `mind_domain_specialist_mismatch_flags`, distinguindo quando a cadeia declarativa ficou efetiva, insuficiente, incompleta ou `not_applicable` sem penalizar traces legados sem contrato novo;
- `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py` e `tools/compare_orchestrator_paths.py` agora carregam esses mesmos sinais para piloto, relatorio textual e comparacao baseline/candidata, incluindo mismatch formal entre cadeia autoritativa, framing e especialista efetivamente consumido;
- a superficie de testes de `observability`, `internal_pilot_support`, `internal_pilot_report`, `compare_orchestrator_paths` e `verify_active_cut_baseline` agora trava a nova gramatica de efetividade e mismatch da arbitragem final;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-079` como concluido e `MB-080` como o item `ready` atual da fila micro.

### MB-078 fechado na politica soberana de consumo final

- `shared/mind_domain_specialist_contract.py` agora tambem deriva uma politica de runtime explicita para `mind_domain_specialist`, separando especialista efetivo, modo de consumo, framing e continuidade sem reabrir heuristica local;
- `engines/specialist-engine`, `services/orchestrator-service`, `services/operational-service` e `engines/synthesis-engine` agora aplicam essa politica na selecao final, no `operation_dispatch`, no artefato operacional e na sintese final, priorizando o especialista canonico da rota promovida quando ele existe e contendo a ultima milha no nucleo quando o contrato pede fallback governado;
- a superficie de testes de `specialist`, `operational-service`, `synthesis` e `orchestrator-service` agora trava esse comportamento como baseline da ultima milha do runtime;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-078` como concluido e `MB-079` como o item `ready` atual da fila micro.

### MB-077 fechado na ultima milha da arbitragem declarativa

- `shared/mind_domain_specialist_contract.py`, `shared/contracts/__init__.py` e `shared/schemas/__init__.py` agora formalizam `mind_domain_specialist_contract_*` como slice soberano para cadeia autoritativa, override bounded e fallback governado;
- `engines/cognitive-engine`, `engines/specialist-engine`, `engines/planning-engine`, `engines/synthesis-engine` e `services/orchestrator-service` agora carregam e propagam esse contrato explicito na ultima milha do runtime, sem reintroduzir heuristica local;
- a superficie de testes de `cognitive`, `specialist`, `planning`, `synthesis` e `orchestrator-service` agora trava esse contrato novo em snapshot, handoff, plano, sintese e payloads de eventos;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-077` como concluido e `MB-078` como o item `ready` atual da fila micro.

## 2026-04-12

### Repriorizacao do proximo lote micro para arbitragem declarativa

- `docs/implementation/execution-backlog.md` agora abre `MB-077` a `MB-081` como o novo lote ativo do nucleo, com `MB-077` em `ready` e foco em arbitragem mais declarativa de `mente -> dominio -> especialista` nos consumidores finais;
- o novo lote traduz a prioridade macro `SG-005` em uma sequencia micro curta: contrato, aplicacao governada, observabilidade/tracing, uso evolutivo e fechamento documental;
- `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para sair do estado "sem item ready" e registrar `MB-077` como o proximo passo correto do projeto;
- `protective intelligence` permanece `deferred`, e a Onda 2 continua tratada apenas como experimento controlado, nao como gatilho automatico de nova frente macro.

### Fechamento do lote de memoria viva ativa

- `shared/memory_registry.py`, `shared/contracts/__init__.py`, `shared/schemas/__init__.py`, `services/memory-service`, `engines/planning-engine` e `services/orchestrator-service` agora formalizam e aplicam `memory_maintenance_*`, compaction e recall cross-session como contrato soberano por request;
- `services/observability-service`, `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`, `tools/evolution_from_pilot.py`, `tools/verify_release_signal_baseline.py` e `evolution/evolution-lab` agora expoem efetividade de manutencao viva, compaction e recall cross-session como evidencia auditavel e insumo formal de refinamento;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para fechar `MB-072` a `MB-076` e registrar que a fila micro voltou a ficar sem item `ready` ate nova repriorizacao explicita.

## 2026-04-11

### Repriorizacao do proximo lote micro para memoria viva ativa

- `docs/implementation/execution-backlog.md` agora abre `MB-072` a `MB-076` como o novo lote ativo do nucleo, com `MB-072` em `ready` e foco em manutencao ativa de memoria viva, compaction e recall cross-session 2.0;
- o novo lote traduz a prioridade macro `SG-004`, apoiada por `TA-003`, em uma sequencia micro curta: contrato, aplicacao governada, observabilidade/tracing, uso evolutivo e fechamento documental;
- `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para sair do estado "sem item ready" e registrar `MB-072` como o proximo passo correto do projeto;
- `protective intelligence` permanece `deferred`, e a Onda 2 continua tratada apenas como experimento controlado, nao como gatilho automatico de nova frente macro.

### Fechamento do lote de decisao soberana de capacidades

- `shared/contracts/__init__.py`, `shared/schemas/__init__.py`, `engines/planning-engine`, `services/orchestrator-service` e `services/governance-service` agora formalizam e aplicam `capability_decision_*` como contrato soberano de elegibilidade, autorizacao, handoff bounded e fallback do runtime;
- `services/observability-service`, `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`, `tools/evolution_from_pilot.py` e `evolution/evolution-lab` agora expõem `capability_decision_status`, `capability_effectiveness` e `handoff_adapter_status` como evidencia auditavel e insumo de refinamento do baseline;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para fechar `MB-067` a `MB-071` e registrar que a fila micro voltou a ficar sem item `ready` ate nova repriorizacao explicita.

### Repriorizacao do proximo lote micro para decisao soberana de capacidades

- `docs/implementation/execution-backlog.md` agora abre `MB-067` a `MB-071` como o novo lote ativo do nucleo, com `MB-067` em `ready` e foco em transformar decisao de capacidade, ferramenta e handoff bounded em contrato soberano do runtime;
- o novo lote traduz a prioridade macro `SG-001`, apoiada por `TA-001` e `TA-005`, em uma sequencia micro curta: contrato, aplicacao governada, observabilidade/tracing, uso evolutivo e fechamento documental;
- `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para sair do estado "sem item ready" e registrar `MB-067` como o proximo passo correto do projeto;
- `protective intelligence` permanece `deferred`, e a Onda 2 continua tratada apenas como experimento controlado, nao como gatilho automatico de nova frente macro.

## 2026-04-10

### Pesquisa e classificacao do TurboQuant

- `docs/architecture/turboquant-review.md` agora registra a leitura aplicada do `TurboQuant` para o JARVIS, com fontes primarias, limites de uso e recomendacao de classificacao;
- `docs/architecture/technology-study.md`, `docs/architecture/technology-capability-extraction-map.md` e `docs/architecture/technology-absorption-order.md` agora tratam `TurboQuant` como referencia de infraestrutura inferencial e retrieval vetorial, util para `KV cache`, `long-context` e busca vetorial em escala, mas fora do nucleo soberano;
- `docs/implementation/unified-gap-and-absorption-backlog.md` agora o encaixa como `TA-008`, bloqueado por fase e por consumidor real, em vez de trata-lo como frente micro imediata.

### Backlog unificado do que ainda falta no sistema

- `docs/implementation/unified-gap-and-absorption-backlog.md` agora consolida em um unico artefato o que ainda falta no JARVIS, separando gaps do sistema, traducao tecnologica, superficies, evolucao, verticais `deferred` e pesquisa;
- `docs/implementation/execution-backlog.md`, `docs/roadmap/programa-ate-v3.md` e `docs/implementation/v2-adherence-snapshot.md` agora apontam para esse backlog unificado como ponte formal entre direcao macro e a proxima repriorizacao micro;
- `HANDOFF.md` foi sincronizado para registrar esse backlog macro unificado como parte do sistema vivo de planejamento e retomada do projeto.

### Alinhamento documental da visao soberana do JARVIS

- `documento_mestre_jarvis.md` agora explicita melhor tres pontos da visao arquitetural: LLMs e runtimes auxiliares como substrato cognitivo subordinado, multiplas superficies como manifestacoes da mesma entidade e estado operacional do ecossistema como parte do cerebro do sistema;
- `docs/roadmap/programa-ate-v3.md` agora formaliza essas mesmas premissas como criterio transversal do programa ate `v3`, incluindo o enriquecimento futuro do estado operacional do ecossistema;
- `docs/implementation/v2-adherence-snapshot.md` e `HANDOFF.md` foram sincronizados para registrar que essa clarificacao de visao permanece coerente com a trajetoria atual do runtime e com a fila micro ainda sem item `ready`.

### Recuperacao do engineering gate apos o fechamento do lote MB-062 a MB-066

- `engines/planning-engine/src/planning_engine/engine.py` deixou de reinterpretar `specialist_reevaluation` como validacao humana no plano refinado, preservando o carater governado interno dessa intervencao e destravando `governance`, piloto, benchmark e `langgraph_flow`;
- `shared/domain_registry.py` voltou a preservar `workflow_steps`, `workflow_checkpoints` e `workflow_decision_points` em `specialist_route_payload`, evitando perda do contrato soberano de workflow nas rotas promovidas;
- `tests/unit/test_domain_registry_workflows.py`, `engines/planning-engine/tests/test_planning_engine.py` e `services/orchestrator-service/tests/test_orchestrator_service.py` agora travam esses dois desvios como regressao;
- `HANDOFF.md` foi sincronizado com o novo estado real do projeto: `python tools/engineering_gate.py --mode standard` voltou a passar no baseline completo.

### MB-064 a MB-066 fechados na ultima milha e no loop evolutivo da politica soberana

- `engines/synthesis-engine/src/synthesis_engine/engine.py` agora publica uma clausula bounded de `Intervencao adaptativa` na resposta final, explicitando por que o `workflow_profile` priorizou a acao escolhida e qual checkpoint/gate foram preservados;
- `services/orchestrator-service/src/orchestrator_service/service.py` agora propaga esse mesmo resumo estruturado em `response_synthesized`, mantendo a ultima milha do runtime coerente com a prioridade soberana ja decidida no plano;
- `evolution/evolution-lab/src/evolution_lab/service.py`, `tools/evolution_from_pilot.py` e `tools/compare_orchestrator_paths.py` agora tratam mismatch ou fechamento insuficiente dessa politica como insumo formal de `refinement_vectors`, `evaluation_matrix` e propostas sandbox por workflow;
- `engines/synthesis-engine/tests/test_synthesis_engine.py`, `evolution/evolution-lab/tests/test_evolution_lab_service.py`, `tests/unit/test_compare_orchestrator_paths.py`, `tests/unit/test_evolution_from_pilot.py` e o teste focado em `services/orchestrator-service/tests/test_orchestrator_service.py` agora travam a nova gramatica declarativa e seu peso evolutivo;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-064` a `MB-066` como concluidos e devolver a fila micro ao estado sem item `ready`.

### MB-063 fechado na evidencia auditavel da politica soberana de intervencao

- `services/observability-service/src/observability_service/service.py` agora calcula `adaptive_intervention_policy_status` a partir do `workflow_profile` soberano, distinguindo `policy_aligned`, `mandatory_override`, `attention_required` e `not_applicable` sem reabrir heuristica fora do registry;
- `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py` e `tools/verify_release_signal_baseline.py` agora propagam esse novo sinal para piloto, comparadores e leitura de release, inclusive como campo de mismatch formal e decisao resumida;
- `services/observability-service/tests/test_observability_service.py`, `tests/unit/test_internal_pilot_report.py` e `tests/unit/test_compare_orchestrator_paths.py` agora travam os casos de `policy_aligned`, `mandatory_override` e `attention_required`, alem da serializacao do novo campo nos artefatos comparativos;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-063` como concluido e liberar `MB-064` como proximo item `ready`.

### MB-062 fechado na prioridade soberana de intervencao por workflow

- `shared/domain_registry.py` agora carrega prioridade soberana por `workflow_profile` para a escolha entre `memory_review_checkpoint` e `specialist_reevaluation`, sem mexer na precedencia absoluta de clarificacao e contencao segura;
- `engines/planning-engine/src/planning_engine/engine.py` agora seleciona a intervencao adaptativa concorrente a partir desse guidance do registry, inclusive quando a revisao especializada reabre tensao no plano refinado;
- `engines/planning-engine/tests/test_planning_engine.py` agora trava dois casos-chave: workflows analiticos priorizando reavaliacao especializada e workflows de readiness priorizando checkpoint de memoria quando ambos competem;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para abrir o lote `MB-062` a `MB-066`, marcar `MB-062` como concluido e deixar `MB-063` como proximo item `ready`.

## 2026-04-09

### MB-057 a MB-061 fechados na intervencao adaptativa governada do nucleo

- `shared/contracts/__init__.py`, `shared/schemas/__init__.py` e `engines/planning-engine/src/planning_engine/engine.py` agora formalizam `adaptive_intervention_*` como contrato soberano do plano deliberativo, derivado de sinais do runtime e `workflow_profile` sem abrir heuristica paralela;
- `services/orchestrator-service/src/orchestrator_service/service.py` e `services/orchestrator-service/src/orchestrator_service/langgraph_flow.py` agora propagam esse slice por `plan_built`, `plan_refined`, dispatch, `workflow_*` e `response_synthesized`, preservando checkpoints de clarificacao, revisao de memoria, reavaliacao especializada e contencao segura sem dominar a linha principal do plano;
- `services/observability-service/src/observability_service/service.py`, `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`, `evolution/evolution-lab/src/evolution_lab/service.py`, `tools/evolution_from_pilot.py` e `tools/verify_release_signal_baseline.py` agora tratam efetividade de intervencao adaptativa como sinal formal do baseline para auditoria, piloto, comparacao, priorizacao evolutiva e release;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-057` a `MB-061` como concluidos e deixar a fila micro novamente sem item `ready` ate nova repriorizacao explicita.

### Abertura do lote MB-057 a MB-061 para intervencao adaptativa governada

- `docs/implementation/execution-backlog.md` agora abre `MB-057` a `MB-061` como novo lote ativo do nucleo, com `MB-057` em `ready` e os demais itens bloqueados apenas pela ordem de dependencia;
- o novo lote formaliza a proxima prioridade tecnica do JARVIS: transformar `workflow_output_status`, discordancia entre mentes, pressao de memoria, checkpoints de validacao e sinais de retomada em intervencoes adaptativas soberanas antes da sintese final;
- `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para refletir a repriorizacao explicita, corrigir o commit de referencia para `18fc7ac` e sair do estado "sem item ready";
- `protective intelligence` permanece `deferred`, e a matriz de readiness da Onda 2 continua servindo apenas como insumo controlado para o proximo refinamento, nao como gatilho automatico de nova frente macro.

### Template operacional para transicao de chat

- criado `docs/operations/chat-transition-template.md` para padronizar a abertura de novas conversas quando um lote for fechado ou quando a repriorizacao do backlog exigir reset de contexto;
- o template agora separa prompt curto, prompt completo, checklist de transicao e regra pratica de quando continuar no mesmo chat versus abrir outro;
- `HANDOFF.md` passou a referenciar esse artefato como apoio operacional, sem substituir o papel do handoff macro nem da fila micro soberana.

### MB-054 a MB-056 fechados na maturacao adaptativa do nucleo

- `engines/cognitive-engine/src/cognitive_engine/engine.py`, `services/orchestrator-service/src/orchestrator_service/service.py` e `engines/planning-engine/src/planning_engine/engine.py` agora fazem memoria relevante influenciar rota prioritaria, hints especializados, ranking de continuidade e racionalidade do caminho escolhido pelo runtime;
- `engines/synthesis-engine/src/synthesis_engine/engine.py`, `services/observability-service/src/observability_service/service.py` e `tools/compare_orchestrator_paths.py` agora tratam composicao de mentes, discordancia, checkpoint de validacao e cadeia `mente -> dominio -> especialista` como sinais causais mais explicitos de saida, maturacao e release;
- `evolution/evolution-lab/src/evolution_lab/service.py`, `tools/compare_orchestrator_paths.py` e `docs/architecture/technology-absorption-order.md` agora publicam matriz de readiness da Onda 2 subordinada aos sinais do nucleo, mantendo a proxima absorcao externa como experimento controlado;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-054` a `MB-056` como concluidos e fechar a fila micro ativa ate nova repriorizacao explicita.

### MB-053 fechado na maturacao causal final do nucleo

- `shared/memory_registry.py` agora traduz lifecycle de memoria em postura operacional soberana, distinguindo quando recovery, packet guiado e reuso recorrente permanecem ativos, entram em revisao ou devem parar de herdar memoria arquivavel automaticamente;
- `services/memory-service/src/memory_service/service.py` e `services/memory-service/src/memory_service/repository.py` agora aplicam essa politica no recovery e na memoria compartilhada de especialistas, contendo refs e artefatos arquivaveis ate revisao explicita sem quebrar as classes canonicas do sistema;
- `services/observability-service/src/observability_service/service.py` agora marca desalinhamento quando memoria guiada arquivavel continua exposta ao especialista como se estivesse ativa;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-053` como concluido e liberar `MB-054` como o proximo item `ready`.

### MB-052 fechado na maturacao causal final do nucleo

- `shared/contracts/__init__.py`, `shared/schemas/__init__.py` e `engines/planning-engine/src/planning_engine/engine.py` agora tratam mudanca de estrategia cognitiva mid-flow como parte do contrato deliberativo, aplicada no `refine_task_plan` quando a revisao especializada preserva um impasse governado;
- `engines/synthesis-engine/src/synthesis_engine/engine.py`, `services/orchestrator-service/src/orchestrator_service/service.py` e `services/orchestrator-service/src/orchestrator_service/langgraph_flow.py` agora propagam esse slice para a resposta final e para os eventos `plan_refined` e `response_synthesized`, mantendo motivo, gatilho e efeitos observaveis;
- `services/observability-service/src/observability_service/service.py` agora audita a coerencia dessa mudanca mid-flow entre plano refinado e resposta final;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-052` como concluido e liberar `MB-053` como o proximo item `ready`.

### Abertura do lote MB-052 a MB-056 para o nucleo

- `docs/implementation/execution-backlog.md` agora abre `MB-052` a `MB-056` como novo lote ativo do nucleo, com `MB-052` em `ready` para metacognicao adaptativa mid-flow e os demais itens bloqueados apenas pela ordem de dependencia;
- o novo lote formaliza a sequencia seguinte do sistema: lifecycle de memoria como sistema vivo, memoria influenciando rota/especialista, composicao de mentes mais causal e readiness controlada da Onda 2 sem abrir nova vertical;
- `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para refletir esse novo lote, atualizar o commit de referencia para `4008dd1` e corrigir a leitura da fila micro ativa.

## 2026-04-08

### MB-048 a MB-051 fechados na maturacao causal final do nucleo

- `shared/memory_registry.py`, `engines/planning-engine/src/planning_engine/engine.py` e `engines/synthesis-engine/src/synthesis_engine/engine.py` agora distinguem melhor efeitos de `semantic` e `procedural` por `workflow_profile` e por fonte de continuidade, fazendo memoria causal pesar em prioridade, profundidade e recomendacao final do runtime;
- `services/orchestrator-service/src/orchestrator_service/service.py`, `engines/synthesis-engine/src/synthesis_engine/engine.py` e `tools/compare_orchestrator_paths.py` agora tratam a cadeia `mente -> dominio -> especialista` como evidencia primaria mais rica, incluindo planned hints, alinhamento parcial e coerencia do encadeamento no runtime e nos comparadores;
- `evolution/evolution-lab/src/evolution_lab/service.py`, `tools/evolution_from_pilot.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py` e `tools/verify_release_signal_baseline.py` agora promovem `workflow_output_status` e essa cadeia evidence-first a leitura formal de `baseline_saudavel`, `maturation_recommended` ou `attention_required` para piloto, comparadores, laboratorio e release;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-048` a `MB-051` como concluidos e deixar a fila micro sem novo item `ready` ate repriorizacao explicita.

### MB-047 fechado na maturacao causal final do nucleo

- `engines/synthesis-engine/src/synthesis_engine/engine.py` agora distingue validacao generica de output de completude orientada por `workflow_profile`, separando saida coerente, parcial e desalinhada por workflow sem trocar a gramatica minima da resposta;
- `services/orchestrator-service/src/orchestrator_service/service.py` e `services/orchestrator-service/src/orchestrator_service/langgraph_flow.py` agora propagam `workflow_output_status` e `workflow_output_errors` no `response_synthesized`, tornando esse slice auditavel no runtime principal e no caminho opcional de `LangGraph`;
- `services/observability-service/src/observability_service/service.py` agora usa esse slice para fazer `workflow_profile_status` pesar na completude formal do fluxo, distinguindo `maturation_recommended` de `attention_required` quando o problema ja e desalinhamento do output;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-047` como concluido e liberar `MB-048` como o proximo item `ready`.

### Novo lote MB-047 a MB-051 aberto para o nucleo

- `docs/implementation/execution-backlog.md` agora abre `MB-047` a `MB-051` como novo lote ativo de maturacao causal final do nucleo, com `MB-047` em `ready` e os demais itens bloqueados apenas pela ordem de dependencia;
- o novo lote formaliza no backlog o modo de raciocinio recomendado por item: `high` para `MB-047`, `MB-048`, `MB-049` e `MB-051`, `medium` para `MB-050`, e `extra high` apenas para a decisao de abertura ou repriorizacao macro do lote;
- `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para refletir que a fila micro voltou a ter proximo passo explicito sem reativar `protective intelligence`.

### MB-044 a MB-046 fechados na Onda 1 de absorcao disciplinada

- `services/orchestrator-service/src/orchestrator_service/service.py`, `services/orchestrator-service/src/orchestrator_service/langgraph_flow.py`, `services/operational-service/src/operational_service/service.py` e `services/observability-service/src/observability_service/service.py` agora carregam `workflow_checkpoint_state`, `workflow_resume_status`, `workflow_resume_point` e `workflow_pending_checkpoints` como sinais soberanos de durable execution e retomada governada;
- `shared/memory_registry.py`, `services/memory-service/src/memory_service/service.py`, `services/memory-service/src/memory_service/repository.py`, `engines/planning-engine/src/planning_engine/engine.py` e `engines/synthesis-engine/src/synthesis_engine/engine.py` agora materializam artefatos procedurais versionados, reutilizaveis e `through_core_only`, com refs, versao e resumo auditaveis no runtime;
- `evolution/evolution-lab/src/evolution_lab/service.py`, `evolution/evolution-lab/src/evolution_lab/repository.py`, `tools/compare_orchestrator_paths.py`, `tools/evolution_from_pilot.py`, `tools/internal_pilot_report.py` e `tools/verify_release_signal_baseline.py` agora persistem `candidate_refs`, `refinement_vectors`, `evaluation_matrix`, `selection_criteria` e `metric_deltas` como traducao governada de compile/eval loops;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-044` a `MB-046` como concluidos e deixar a fila micro sem novo item `ready` ate repriorizacao.

### MB-043 fechado na Onda 1 de absorcao disciplinada

- `shared/memory_registry.py` agora distingue memoria guiada operacional, fixada e arquivavel sem trocar os labels canonicos de lifecycle, expondo sinais explicitos de consolidacao, fixacao e arquivamento para o runtime;
- `services/memory-service/src/memory_service/service.py` e `services/memory-service/src/memory_service/repository.py` agora propagam esses sinais para packets guiados, resumos de corpus e recuperacao persistida de `specialist_shared_memory`, sem abrir dependencia externa nem schema central novo;
- `engines/planning-engine/src/planning_engine/engine.py`, `services/orchestrator-service/src/orchestrator_service/service.py` e `services/observability-service/src/observability_service/service.py` agora carregam e auditam `memory_consolidation_status`, `memory_fixation_status` e `memory_archive_status` como parte explicita do baseline soberano;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-043` como concluido e liberar `MB-044` como o proximo item `ready`.

### MB-042 fechado na Onda 1 de absorcao disciplinada

- `shared/memory_registry.py` agora formaliza uma politica soberana de contexto vivo compactado e recall cross-session, inspirada em referencias externas, mas sem substituir o `memory_registry` nem inflar a janela de contexto do runtime;
- `services/memory-service/src/memory_service/service.py` passou a distinguir contexto vivo, hints de continuidade e recall cross-session com compactacao disciplinada, preservando `prior_plan`, `session_continuity_*` e resumo cross-session sem reabrir historico bruto;
- `services/orchestrator-service/src/orchestrator_service/service.py`, `engines/planning-engine/src/planning_engine/engine.py` e `engines/synthesis-engine/src/synthesis_engine/engine.py` agora propagam e usam `context_compaction_*` e `cross_session_recall_*` como sinais auditaveis do baseline, com efeito leve e governado em planejamento e resposta final;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-042` como concluido e liberar `MB-043` como o proximo item `ready`.

### MB-041 fechado na Onda 1 de absorcao disciplinada

- `shared/schemas/__init__.py`, `shared/contract_validation.py` e `shared/contracts/__init__.py` agora formalizam um primeiro recorte soberano de validacao tipada para `DeliberativePlanContract`, sem introduzir dependencia central nova nem trocar a gramatica canonica do runtime;
- `engines/planning-engine/src/planning_engine/engine.py` agora valida o plano deliberativo contra schema canonico e aplica repair pequeno, deterministico e auditavel quando um campo obrigatorio nasce inconsistente;
- `engines/synthesis-engine/src/synthesis_engine/engine.py` agora valida o output minimo da resposta final, recompõe saida segura quando o texto perde clausulas obrigatorias e expõe `output_validation_status` no runtime;
- `services/orchestrator-service/src/orchestrator_service/service.py`, `services/orchestrator-service/src/orchestrator_service/langgraph_flow.py` e `services/observability-service/src/observability_service/service.py` agora propagam e auditam `contract_validation_status` e `output_validation_status`, distinguindo contrato coerente, contrato reparado, falha de contrato e falha de output;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-041` como concluido e liberar `MB-042` como o proximo item `ready`.

### Ordem oficial de absorcao tecnologica e novo lote do backlog

- criado `docs/architecture/technology-absorption-order.md` para transformar o estudo tecnologico ampliado em uma ordem oficial de traducao disciplinada por ondas, separando o que deve fortalecer o nucleo agora do que deve permanecer como complemento futuro ou horizonte de pesquisa;
- `docs/architecture/technology-study.md` e `docs/architecture/technology-capability-extraction-map.md` agora apontam explicitamente essa nova ordem de absorcao como leitura operacional complementar ao estudo-base e ao mapa de extracao de valor;
- `docs/implementation/execution-backlog.md` agora abre `MB-041` a `MB-046` como lote de absorcao disciplinada da Onda 1, com `MB-041` em `ready` para contratos tipados e validacao soberana inspirados em `PydanticAI` e `Mastra`;
- `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para registrar que a proxima rodada ativa ja nao e apenas repriorizacao abstrata: existe ordem oficial de absorcao e lote micro aberto sem reativar `protective intelligence`.

## 2026-04-06

### Fechamento do lote cognitivo MB-037 a MB-040

- `evolution/evolution-lab/src/evolution_lab/service.py`, `tools/evolution_from_pilot.py`, `tools/compare_orchestrator_paths.py` e `tools/internal_pilot_report.py` agora publicam `refinement_vectors` por workflow e transformam os sinais do nucleo em leitura priorizada de refinamento para autoevolucao governada;
- `engines/planning-engine/src/planning_engine/engine.py`, `engines/synthesis-engine/src/synthesis_engine/engine.py`, `services/orchestrator-service/src/orchestrator_service/service.py` e `services/observability-service/src/observability_service/service.py` agora tratam discordancia entre mentes como restricao, checkpoint governado e leitura auditavel do runtime quando o workflow exige profundidade cognitiva maior;
- `shared/memory_registry.py`, `services/memory-service/src/memory_service/repository.py`, `services/memory-service/src/memory_service/service.py`, `services/observability-service/src/observability_service/service.py` e `tools/internal_pilot_support.py` agora publicam `memory_corpus_status`, `memory_retention_pressure` e cobertura deliberada de corpus no baseline vivo;
- `tools/verify_release_signal_baseline.py`, `tools/verify_active_cut_baseline.py` e `docs/roadmap/programa-de-excelencia.md` agora tratam matriz formal de evals por eixo/workflow como parte explicita do baseline operacional, e nao apenas como direcao abstrata;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-037` a `MB-040` como concluidos e deixar a fila micro sem item `ready` ate nova repriorizacao.

### Abertura do proximo lote do nucleo cognitivo

- `docs/implementation/execution-backlog.md` agora abre `MB-037` a `MB-040`, com `MB-037` em `ready` para transformar sinais do nucleo em vetores priorizados de refinamento por workflow;
- o novo lote ficou explicitamente organizado em quatro frentes: autoevolucao governada, composicao de mentes mais profunda, telemetria viva de memoria e matriz formal de evals por eixo/workflow;
- `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para refletir esse proximo passo sem reativar `protective intelligence`.

### Fechamento do lote cognitivo MB-033 a MB-036

- `shared/memory_registry.py`, `services/memory-service/src/memory_service/service.py`, `engines/planning-engine/src/planning_engine/engine.py`, `engines/synthesis-engine/src/synthesis_engine/engine.py` e `services/observability-service/src/observability_service/service.py` agora distinguem fonte, efeitos, lifecycle e revisao de `semantic`/`procedural` por `workflow_profile` e por fonte de continuidade, separando reasoning final, packet de especialista e recovery de missao;
- `services/orchestrator-service/src/orchestrator_service/service.py`, `services/observability-service/src/observability_service/service.py`, `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py` e `tools/compare_orchestrator_paths.py` agora tratam `mind_domain_specialist_chain_*`, `primary_mind` e `primary_route` como evidencia primaria do runtime e do piloto;
- `tools/evolution_from_pilot.py`, `evolution/evolution-lab/src/evolution_lab/service.py`, `tools/compare_orchestrator_paths.py` e `tools/verify_release_signal_baseline.py` agora promovem metacognicao causal, lifecycle de memoria e coerencia `mente -> dominio -> especialista` a sinais formais de evolucao governada e readiness de release;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-033` a `MB-036` como concluidos e registrar o lote atual do nucleo cognitivo como fechado, sem item `ready`.

### Metacognicao causal no runtime final

- `shared/contracts/__init__.py` e `engines/planning-engine/src/planning_engine/engine.py` agora materializam `metacognitive_guidance_*` no plano deliberativo, distinguindo quando `primary_mind`, `primary_domain_driver` e `dominant_tension` alteraram `success_criteria`, `smallest_safe_next_action` e recomendacao de contencao;
- `engines/synthesis-engine/src/synthesis_engine/engine.py` passou a refletir essa guidance na leitura final e nas respostas governadas, deixando explicito quando a contencao ou a proxima acao foram ancoradas por metacognicao;
- `services/orchestrator-service/src/orchestrator_service/service.py` e `services/observability-service/src/observability_service/service.py` agora propagam e auditam `metacognitive_guidance_applied`, `metacognitive_guidance_summary`, `metacognitive_effects` e `metacognitive_containment_recommendation`;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-032` como concluido e liberar `MB-033` como proximo item `ready`.

### Repriorizacao do backlog para o nucleo cognitivo

- `docs/implementation/execution-backlog.md` foi recentrado no nucleo cognitivo: `MB-027` a `MB-031` passaram para `deferred`, e um novo lote (`MB-032` a `MB-036`) foi aberto para metacognicao deliberativa, memoria causal/lifecycle e relacao `mente -> dominio -> especialista`;
- `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para deixar explicito que a prioridade correta agora e maturacao do nucleo, nao abertura imediata de `protective intelligence`;
- `docs/implementation/pre-v3-protective-intelligence-foundation-cut.md` foi preservado como frente futura candidata, mas deixou de ser tratado como frente ativa da rodada.

### Mapeamento da próxima frente macro sem iniciar implementação

- criado `docs/implementation/pre-v3-protective-intelligence-foundation-cut.md` para abrir formalmente a próxima frente macro do sistema, com escopo defensivo e ordem de implementação explícita;
- `docs/implementation/execution-backlog.md` agora carrega `MB-027` a `MB-031` como fila do novo lote, deixando `MB-027` em `ready` e os demais itens `blocked` apenas por dependência da ordem;
- `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para tratar `pre-v3 protective intelligence foundation` como próxima frente ativa mapeada, ainda não iniciada no runtime.

### Fechamento do lote pre-v3 hardening

- `services/orchestrator-service/src/orchestrator_service/service.py` agora fecha explicitamente o lifecycle de especialistas com `specialist_subflow_completed` e declara `mission_runtime_state` para requests com missao ativa, related mission e readiness de retomada;
- `services/orchestrator-service/src/orchestrator_service/langgraph_flow.py` passou a espelhar o mesmo contrato soberano de `specialist_subflow` e `mission_runtime_state`, reduzindo assimetria entre o caminho nativo e o caminho opcional de `LangGraph`;
- `services/observability-service/src/observability_service/service.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`, `tools/verify_active_cut_baseline.py` e `tools/archive/close_domain_consumers_and_workflows_cut.py` agora tratam `specialist_subflow` e `mission_runtime_state` como sinais agregados de readiness arquitetural pre-`v3`;
- `shared/contracts/__init__.py` passou a expor `MissionRuntimeStateContract`, preparando continuidade longa e missao assincrona sem reabrir a ontologia do sistema;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-024` a `MB-026` como concluidos e registrar o lote `pre-v3 hardening` como fechado.

### Abertura do lote pre-v3 hardening e continuidade stateful nativa

- `services/orchestrator-service/src/orchestrator_service/service.py` agora formaliza a fase de continuidade/HITL/replay como subfluxo nativo do caminho padrao, em vez de manter essa logica apenas inline no `handle_input`;
- o runtime padrao passou a emitir `continuity_subflow_completed`, com `runtime_mode = native_pipeline`, `subflow_name = continuity_stateful`, replay, recomendacao de continuidade e dados de resolucao manual quando existirem;
- `services/orchestrator-service/src/orchestrator_service/langgraph_flow.py` passou a reutilizar o mesmo payload soberano de fechamento da continuidade, reduzindo drift entre o caminho nativo e o caminho opcional de `LangGraph`;
- `services/orchestrator-service/tests/test_orchestrator_service.py` e `services/orchestrator-service/tests/test_langgraph_flow.py` foram ampliados para cobrar esse fechamento explicito;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para abrir o lote `pre-v3 hardening`, marcar `MB-023` como concluido e registrar `MB-024` a `MB-026` como fila ativa seguinte.

## 2026-04-05

### Fechamento da ultima pendencia de robustez do v2

- `tools/verify_active_cut_baseline.py` agora exige, alem de memoria causal e recomposicao cognitiva, cobertura deliberada de `dominant_tension` e alinhamento `mente -> dominio -> especialista` como parte formal do `baseline_release_ready`;
- `tools/internal_pilot_support.py` passou a declarar essas coberturas nos cenarios canonicos promovidos, transformando tensao cognitiva e coerencia `mind_domain_specialist` em sinais deliberados do piloto, e nao telemetria incidental;
- `tools/archive/close_domain_consumers_and_workflows_cut.py`, `docs/archive/implementation/v2-domain-consumers-and-workflows-cut-closure.md` e `docs/executive/master-summary.md` agora refletem explicitamente essa nova readiness de robustez;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para registrar `MB-020` a `MB-022` como concluidos e fixar que o `v2` nao tem mais pendencia tecnica material de robustez dentro do baseline atual.

### Cobertura deliberada do piloto promovida a fechamento e leitura executiva

- `tools/archive/close_domain_consumers_and_workflows_cut.py` agora carrega cobertura do piloto, match por rota/workflow e readiness dos sinais deliberados de `memory_causality` e `cognitive_recomposition` como parte da evidencia regeneravel do corte;
- `tests/unit/test_close_domain_consumers_and_workflows_cut.py` foi ampliado para cobrar essas novas evidencias no payload e no markdown;
- `docs/archive/implementation/v2-domain-consumers-and-workflows-cut-closure.md` e `docs/executive/master-summary.md` agora refletem explicitamente que o baseline do corte combina contratos promovidos com cobertura deliberada do piloto;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para registrar `MB-017` a `MB-019` como concluidos e manter o backlog micro sem item `ready`.

### Cobertura deliberada do baseline ativo por rota e workflow

- `tools/verify_active_cut_baseline.py` passou a combinar os contratos promovidos do registry com um piloto focado em rotas promovidas, `workflow_profiles` promovidos e sinais deliberados de `memory_causality` e `cognitive_recomposition`;
- `tools/internal_pilot_support.py` agora declara `expected_route`, `expected_workflow_profile` e `coverage_tags` nos cenarios canonicos do piloto, cobrindo explicitamente `analysis`, `decision_risk`, `governance`, `operational_readiness`, `software_development` e `strategy`;
- o baseline ativo agora falha se perder cobertura deliberada das rotas promovidas, dos workflow profiles promovidos ou dos cenarios minimos de memoria causal e recomposicao cognitiva;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para registrar `MB-013` a `MB-016` como concluidos e manter o backlog micro novamente sem item `ready`.

### Refinamento da arquitetura de protective intelligence

- `docs/architecture/protective-intelligence-architecture.md` foi enriquecido com o que havia de util no rascunho externo de `SecurityOS`, sem absorver a ontologia paralela do documento-fonte;
- a arquitetura agora inclui especialistas opcionais de maturacao (`detection_correlation_specialist`, `hunt_coordination_specialist` e `case_intelligence_specialist`), familias de ferramentas candidatas por categoria e uma matriz de governanca separando `monitorar`, `investigar`, `responder` e `executar acao critica`;
- o eixo de seguranca continua formalizado como `protective intelligence` subordinado ao dominio canonico e ao nucleo soberano, e nao como novo subsistema soberano do JARVIS.

### Sinais de release e fechamento do lote micro MB-008 a MB-012

- `tools/engineering_gate.py` agora roda `tools/verify_release_signal_baseline.py` no modo `release`, promovendo `workflow_profile_status`, `memory_causality_status`, `mind_domain_specialist_status` e recomposicao cognitiva a gramatica formal de liberacao;
- `tools/internal_pilot_support.py` passou a incluir cenarios deliberados para memoria causal (`guided_memory_followup`) e recomposicao cognitiva por `specialist_route_impasse` (`recomposition_impasse`), com reflexo em `tools/internal_pilot_report.py` e `tools/compare_orchestrator_paths.py`;
- `tools/compare_orchestrator_paths.py` agora marca drift explicito de `workflow_profile_status`, `memory_causality_status`, `dominant_tension`, `primary_domain_driver`, `mind_domain_specialist_status` e recomposicao cognitiva entre baseline e candidata;
- `engines/planning-engine`, `engines/synthesis-engine` e `services/orchestrator-service` agora deixam `dominant_tension`, `primary_domain_driver`, `workflow_response_focus` e recomposicao cognitiva mais declarativos no comportamento final do runtime;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-008` a `MB-012` como concluidos e registrar que o backlog micro voltou a ficar sem item `ready`.

### Arquitetura de protective intelligence defensiva

- criado `docs/architecture/protective-intelligence-architecture.md` para formalizar um eixo defensivo e investigativo integrado ao JARVIS, subordinado ao dominio canonico de seguranca, ao nucleo soberano e a governanca central;
- o documento fixa a separacao entre memoria mutavel e ledger de evidencia, propoe `case-service`, `evidence-ledger-service` e `risk-signal-service`, e explicita limites como `through_core_only`, `advisory_only` e proibicao de retaliacao tecnica;
- a ordem de implementacao ficou organizada por fases, de contratos e cadeia de custodia ate especialistas de OSINT, forense, risco e gates dedicados.

### Mapa derivado de verticais do ecossistema

- criado `docs/architecture/ecosystem-verticals-map.md` para organizar verticais derivadas do ecossistema do JARVIS sem competir com a ontologia canonica do mestre;
- o mapa separa verticais compostas prioritarias, secundarias e tardias, mantendo `DevOS`, `ResearchOS`, `LifeOS`, `ExecutiveOS`, `FinanceOS` e `ProtectiveIntelligenceOS` como empacotamentos de produto e implementacao, e nao como fonte soberana do runtime;
- `docs/architecture/protective-intelligence-architecture.md` foi ajustado para explicitar que `ProtectiveIntelligenceOS`, `SecurityOS` ou `IntelOS` sao apenas rotulos derivados de vertical, nao substitutos do dominio canonico de seguranca.

### Saneamento da visao de ajuste arquitetural

- `docs/architecture/visao_ajuste_arquitetural_jarvis.md` foi regravado sem mojibake e com linguagem alinhada ao baseline atual do JARVIS;
- o documento passou a tratar `subsistemas` como agrupamento de implementacao e produto, sem competir com a taxonomia canonica de dominios, mentes e registries soberanos;
- o eixo de seguranca, OSINT e forense agora aponta explicitamente para `docs/architecture/protective-intelligence-architecture.md` como desdobramento defensivo formal.

### Fechamento integral do backlog micro soberano

- `services/observability-service`, `tools/internal_pilot_report.py` e `tools/compare_orchestrator_paths.py` agora distinguem memoria causal (`causal_guidance`) de memoria apenas anexada (`attached_only`), expondo tambem foco semantico, hint procedural e especialistas associados a esse efeito;
- `tools/internal_pilot_support.py` passou a carregar esses novos sinais de memoria guiada, alem de `dominant_tension`, `primary_domain_driver`, `mind_domain_specialist_status` e dados de recomposicao cognitiva para os artefatos comparativos;
- `cognitive-engine` agora aplica recomposicao observavel em impasses reais de rota especializada, priorizando apoio critico sem quebrar a soberania do nucleo;
- `orchestrator-service` passou a publicar `cognitive_recomposition_applied`, `cognitive_recomposition_reason` e `cognitive_recomposition_trigger` nos eventos do fluxo quando a recomposicao ocorre;
- `observability-service` passou a auditar coerencia da recomposicao cognitiva e a explicitar `mind_domain_specialist_status` como leitura separada da malha `mente -> dominio -> especialista`;
- `docs/implementation/execution-backlog.md` foi sincronizado para registrar `MB-003`, `MB-004` e `MB-005` como concluídos, deixando o lote micro atual sem item `ready`.

### Promocao dos sinais novos para evolucao e fechadores

- `evolution/evolution-lab/src/evolution_lab/service.py` e `tools/evolution_from_pilot.py` agora tratam `workflow_profile_status`, `memory_causality_status`, `mind_domain_specialist_status` e recomposicao cognitiva como sinais comparativos reais de refinamento, com `source_signals`, metricas e `risk_hint` coerentes com o baseline;
- `tools/archive/close_alignment_cycle.py` e `tools/archive/close_sovereign_alignment_cut.py` agora carregam decisoes e taxas de `workflow_profile`, `memory_causality` e `mind_domain_specialist` nos payloads e markdowns regeneraveis de fechamento;
- `evolution/evolution-lab/tests/test_evolution_lab_service.py`, `tests/unit/test_close_alignment_cycle.py` e `tests/unit/test_close_sovereign_alignment_cut.py` foram ampliados para cobrir essa nova evidencia;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para registrar `MB-006` e `MB-007` como concluidos e fixar que o lote micro atual continua sem item `ready`.

## 2026-04-03

### Backlog micro soberano e fluxo continuo de implementacao

- criado `docs/implementation/execution-backlog.md` como fila micro soberana do corte ativo, com politicas explicitas de Kanban leve, `WIP limit = 1`, `Definition of Ready`, `Definition of Done` e seed inicial de itens `ready`;
- `HANDOFF.md` passou a apontar explicitamente esse arquivo como fila micro ativa e deixou fixo que o handoff continua macro/tatico, nao backlog executavel;
- `docs/implementation/v2-adherence-snapshot.md` passou a registrar explicitamente que o snapshot continua leitura de baseline, enquanto a fila micro vive em `execution-backlog.md`.

### Propagacao de `workflow_profile_status` para artefatos comparativos

- `tools/internal_pilot_support.py` passou a carregar `workflow_profile_status` dentro de `PilotExecutionResult`, permitindo que esse sinal atravesse a malha de comparacao e serializacao do piloto;
- `tools/internal_pilot_report.py` agora expoe `workflow_profile_status` nas estruturas resumidas e no rendering textual do relatorio;
- `tools/compare_orchestrator_paths.py` passou a incluir `workflow_profile_status` no texto e no payload serializado de comparacao, sem ainda mudar a semantica de decisao do comparador;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-001` como concluido e registrar o novo estado do baseline.

### Classificacao explicita de maturacao por workflow

- `tools/internal_pilot_report.py` agora classifica `workflow_profile_status` em `baseline_saudavel`, `maturation_recommended`, `attention_required` ou `not_applicable`, deixando a leitura operacional mais objetiva;
- `tools/compare_orchestrator_paths.py` passou a publicar essa mesma classificacao por cenario e tambem taxas e decisao agregada de workflow no `comparison_summary`;
- a comparacao continua sem confundir `maturation_recommended` com falha estrutural de baseline, preservando a separacao entre maturacao de workflow e `axis_gate_status`;
- `docs/implementation/execution-backlog.md`, `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para marcar `MB-002` como concluido e registrar a nova leitura do baseline.

### Maturacao causal de memoria guiada no runtime soberano

- `planning-engine` passou a tratar memoria `semantic` e `procedural` como alavancas causais do plano em rotas com `workflow_profile`, priorizando passos guiados de framing e continuidade antes de hints secundarios do workflow;
- `planning-engine` passou a carregar esse efeito tambem em `success_criteria` e `smallest_safe_next_action`, preservando explicitamente o fio procedural quando a continuidade da rota depende dele;
- `synthesis-engine` passou a tratar memoria semantica como ancora explicita do framing final e memoria procedural como fio que a proxima acao precisa preservar;
- `cognitive-engine` e `specialist-engine` passaram a preferir rotas explicitas alinhadas ao `primary_domain_driver` quando esse vinculo ja foi resolvido pelo runtime, sem alterar o baseline de fallback quando a rota ainda nao existe;
- `orchestrator-service` passou a publicar `primary_domain_driver_matches` nos eventos de selecao e conclusao de especialistas, e `observability-service` passou a usar esse sinal para cobrar coerencia explicita da malha `mente -> dominio -> especialista`;
- `observability-service` passou a expor `workflow_profile_status` em paralelo a `workflow_trace_status`, separando baseline saudavel de `maturation_recommended` por `workflow_profile`;
- `HANDOFF.md` e `docs/implementation/v2-adherence-snapshot.md` foram sincronizados para registrar que memoria guiada agora altera mais diretamente o comportamento final de `planning` e `synthesis`, e nao apenas o contexto disponivel.

## 2026-04-02

### Roteamento contratual e auditoria de consistencia do repositorio

- `cognitive-engine` e `specialist-engine` passaram a consumir `domain_specialist_routes` explicitas antes de qualquer fallback local, reduzindo drift entre contratos roteados e a selecao real de especialistas;
- `specialist-engine` passou a expor o papel guiado de analise estruturada de forma consistente tanto na invocacao quanto na contribuicao, e ganhou cobertura para precedencia de rota explicita sobre rederivacao local;
- `tools/engineering_gate.py` passou a rodar `pytest` com `--basetemp` dedicado por execucao, e `conftest.py` passou a suprimir apenas o `PermissionError` ambiental de cleanup que quebrava o gate depois dos testes passarem;
- `HANDOFF.md` foi resincronizado com o commit atual de baseline e agora registra explicitamente o novo comportamento de contratos roteados;
- `docs/implementation/v2-adherence-snapshot.md` e `docs/architecture/mem0-repository-review.md` tiveram links locais absolutos antigos normalizados para paths relativos portaveis;
- `operation_dispatch`, `workflow_composed`, `workflow_governance_declared`, `operation_completed` e `workflow_completed` passaram a carregar o mesmo slice soberano do contrato de workflow (`workflow_objective`, `workflow_expected_deliverables`, `workflow_telemetry_focus`, `workflow_success_focus`, `workflow_response_focus`);
- `operational-service` passou a renderizar esses campos de contrato de workflow no artefato gerado, e `observability-service` passou a tratar drift entre composicao e execucao desse contrato como `attention_required`;
- `auditoria_documento_mestre_jarvis.md` foi arquivado como `docs/archive/documentation/auditoria-primaria-documento-mestre.md`, limpando a raiz do repositorio e preservando a auditoria como referencia historica;
- criado `docs/documentation/repository-map-and-consistency-audit.md` para mapear docs ativos vs historicos, tools ativos vs arquivados, diretorios gerados/locais e candidatos restantes a reclassificacao.

## 2026-04-01

### Fechamento do V2 runtime sovereignty hardening

- `domain_registry` passou a governar ponta a ponta `canonical_domains`, `primary_canonical_domain`, `route_maturity`, `linked_specialist_type`, `specialist_mode`, `consumer_profile`, `consumer_objective`, `expected_deliverables`, `telemetry_focus` e `workflow_profile` no runtime promovido;
- `mind_registry` passou a concentrar ranking, apoio, supressao e tensao dominante das mentes, e o `cognitive-engine` deixou de sugerir especialistas governados por `intent` puro;
- `specialist-engine` passou a exigir coerencia completa entre rota, especialista, modo, memoria guiada e contrato canonico de consumo antes da selecao `guided`;
- `memory_registry` e `memory-service` passaram a tratar `semantic` e `procedural` como memoria `runtime_partial` com politica declarativa por rota e por `workflow_profile`, distinguindo visibilidade para `planning/synthesis` da visibilidade para especialistas;
- `orchestrator-service` passou a emitir `primary_route`, `primary_canonical_domain`, `primary_route_matches`, `primary_canonical_matches` e payload soberano de rotas promovidas, reduzindo recomposicao heuristica nos consumidores posteriores;
- `planning-engine` passou a carregar o contrato da rota primaria promovida e o guidance de workflow para moldar passos, restricoes, criterios de sucesso, rationale e continuidade cognitiva do plano;
- `synthesis-engine` passou a refletir objetivo, entrega esperada, foco de leitura, checkpoint ativo, gate governado e hints de memoria guiada da rota promovida na resposta final;
- `observability-service` passou a auditar drift de alinhamento mais cedo, cobrando coerencia entre rota, dominio, especialista, modo, arbitragem cognitiva e memoria guiada.

### Preservacao documental critica

- `CHANGELOG.md` foi restaurado para o papel correto de changelog cronologico depois de ter sido indevidamente convertido em documento de programa em um commit anterior;
- criado `tools/verify_document_guardrails.py` para validar identidade minima e piso historico de `CHANGELOG.md`, `HANDOFF.md`, `documento_mestre_jarvis.md`, `docs/roadmap/programa-ate-v3.md` e `docs/implementation/v2-adherence-snapshot.md`;
- `tools/engineering_gate.py` passou a executar esse guardrail antes do restante do gate, impedindo nova perda semantica de documentos criticos;
- criada cobertura dedicada para travar essa protecao no baseline.

## 2026-03-31

### Fechamento do native memory hardening e revisao estrutural

- `shared/memory_registry.py`, `memory-service`, `orchestrator-service` e `observability-service` passaram a tratar `user scope` nativo, recorrencia soberana de especialistas promovidos e `organization scope` explicitamente bloqueado sem consumidor canonico;
- o `v2-native-memory-scope-hardening-cut` foi fechado formalmente com artefato regeneravel de encerramento e baseline nativo endurecido;
- o `v2-repository-hygiene-and-tools-review-cut` classificou, arquivou e reorganizou docs e entrypoints historicos de `tools/`, preservando rastreabilidade e regenerabilidade do material encerrado;
- `docs/implementation/v2-adherence-snapshot.md` foi atualizado para refletir o estado real do runtime em relacao ao Documento-Mestre, sem reabrir gaps ja fechados;
- foi criado um framework disciplinado de revisao profunda de repositorios externos, e a primeira aplicacao formal dessa camada ficou registrada para `Mem0` como insumo de arquitetura, nao como promocao direta.

## 2026-03-31

### Abertura do V2 governed benchmark execution cut

- criado `docs/implementation/v2-governed-benchmark-execution-cut.md` como novo recorte ativo para benchmark sandbox por familia de capacidade;
- criado dataset versionado em `tools/benchmarks/datasets/v2_governed_benchmark_execution_profiles.json` para transformar `benchmark_now` em perfis concretos de execucao;
- criado `tools/render_governed_benchmark_execution_plan.py` e `docs/implementation/v2-governed-benchmark-execution-plan.md` como plano regeneravel de execucao sandbox;
- criado `tests/unit/test_render_governed_benchmark_execution_plan.py` para cobrir o renderizador do plano;
- `HANDOFF.md`, `README.md`, `docs/executive/master-summary.md`, `docs/architecture/technology-study.md`, `tools/README.md` e `tools/verify_axis_artifacts.py` foram sincronizados para tratar o novo recorte como frente ativa.

## 2026-03-31

### Sprint 2 do V2 governed benchmark execution cut

- criado dataset versionado em `tools/benchmarks/datasets/v2_governed_benchmark_scenarios.json` para formalizar scenario specs minimos por tecnologia `benchmark_now`;
- criado `tools/render_governed_benchmark_scenario_specs.py` e `docs/implementation/v2-governed-benchmark-scenario-specs.md` como artefatos regeneraveis de scenario specs e fronteiras sandbox;
- criado `tests/unit/test_render_governed_benchmark_scenario_specs.py` para cobrir o renderizador dos scenario specs;
- `docs/implementation/v2-governed-benchmark-execution-cut.md`, `HANDOFF.md`, `README.md`, `docs/executive/master-summary.md`, `docs/architecture/technology-study.md`, `tools/README.md` e `tools/verify_axis_artifacts.py` foram sincronizados para tratar a Sprint 2 como concluida e a Sprint 3 como proxima frente.

### Sprint 3 do V2 governed benchmark execution cut

- criado dataset versionado em `tools/benchmarks/datasets/v2_governed_benchmark_decisions.json` para registrar decisao formal por tecnologia `benchmark_now`;
- criado `tools/render_governed_benchmark_decisions.py` e `docs/implementation/v2-governed-benchmark-decisions.md` como artefatos regeneraveis de decisao, racional curto e sinais de reabertura;
- criado `tests/unit/test_render_governed_benchmark_decisions.py` para cobrir o renderizador das decisoes formais;
- `docs/implementation/v2-governed-benchmark-execution-cut.md`, `HANDOFF.md`, `README.md`, `docs/executive/master-summary.md`, `docs/architecture/technology-study.md`, `tools/README.md` e `tools/verify_axis_artifacts.py` foram sincronizados para tratar a Sprint 3 como concluida e a Sprint 4 como proxima frente.

### Abertura do V2 memory gap evidence cut

- criado `docs/implementation/v2-memory-gap-evidence-cut.md` como novo recorte ativo para provar ou negar a lacuna real de memoria multicamada do baseline atual;
- criado dataset versionado em `tools/benchmarks/datasets/v2_memory_gap_evidence_hypotheses.json` para formalizar hipoteses, sinais de prova e sinais de nao-lacuna;
- criado `tools/render_memory_gap_evidence_protocol.py`, `docs/implementation/v2-memory-gap-evidence-protocol.md` e `tests/unit/test_render_memory_gap_evidence_protocol.py` como protocolo regeneravel do recorte;
- `HANDOFF.md`, `README.md`, `docs/executive/master-summary.md`, `docs/architecture/technology-study.md`, `tools/README.md` e `tools/verify_axis_artifacts.py` foram sincronizados para tratar a Sprint 1 como concluida e a Sprint 2 como proxima frente.

### Sprint 2 do V2 memory gap evidence cut

- criado dataset versionado em `tools/benchmarks/datasets/v2_memory_gap_baseline_scope_rules.json` para formalizar a leitura local por escopo do baseline atual;
- criado `tools/render_memory_gap_baseline_evidence.py`, `docs/implementation/v2-memory-gap-baseline-evidence.md` e `tests/unit/test_render_memory_gap_baseline_evidence.py` como artefatos regeneraveis da coleta local de evidencia;
- a leitura da Sprint 2 ficou fechada assim: conversa, sessao e missao permanecem suficientes; `user scope` e `specialist_shared_memory` sustentam lacuna parcial; `organization scope` continua apenas forma futura;
- `HANDOFF.md`, `README.md`, `docs/executive/master-summary.md`, `docs/architecture/technology-study.md`, `tools/README.md` e `tools/verify_axis_artifacts.py` foram sincronizados para tratar a Sprint 2 como concluida e a Sprint 3 como proxima frente.

### Sprint 3 do V2 memory gap evidence cut

- criado dataset versionado em `tools/benchmarks/datasets/v2_memory_gap_decision.json` para formalizar a decisao de `hold` vs `reopen`;
- criado `tools/render_memory_gap_decision.py`, `docs/implementation/v2-memory-gap-decision.md` e `tests/unit/test_render_memory_gap_decision.py` como artefatos regeneraveis da decisao formal do recorte;
- a decisao da Sprint 3 ficou em `manter_fechado`, preservando `Mem0` como `absorver_depois`;
- `HANDOFF.md`, `README.md`, `docs/executive/master-summary.md`, `docs/architecture/technology-study.md`, `tools/README.md` e `tools/verify_axis_artifacts.py` foram sincronizados para tratar a Sprint 3 como concluida e a Sprint 4 como proxima frente.

### Sprint 4 do V2 memory gap evidence cut

### Sprint 1 do V2 native memory scope hardening cut

- `shared/contracts/__init__.py` passou a expor `UserScopeContextContract` como contrato canonico do escopo de usuario;
- `shared/memory_registry.py` passou a tratar `user` como recovery scope default quando houver `user_id`;
- `memory-service` passou a persistir snapshot nativo de `user scope`, com intents recentes, foco de dominio, missoes ativas e preferencia de continuidade;
- `orchestrator-service` passou a emitir `user_scope_status`, `user_scope_interaction_count` e `user_context_brief` nos eventos `memory_recovered` e `memory_recorded`;
- `observability-service` passou a resumir esse recorte em `user_scope_status` como sinal minimo do baseline;
- `docs/implementation/v2-native-memory-scope-hardening-cut.md` e `HANDOFF.md` foram sincronizados para tratar a Sprint 1 como concluida e a Sprint 2 como proxima frente.

- criado `tools/close_memory_gap_evidence_cut.py` para fechar o recorte com leitura formal da lacuna parcial e recomendacao do proximo corte nativo;
- criado `tests/unit/test_close_memory_gap_evidence_cut.py` para validar payload e markdown do fechamento do recorte;
- criado `docs/implementation/v2-memory-gap-evidence-cut-closure.md` como documento formal de encerramento do corte;
- `tools/engineering_gate.py --mode release` passou a verificar o fechamento regeneravel do recorte de memory gap;
- `HANDOFF.md`, `README.md`, `docs/executive/master-summary.md`, `docs/architecture/technology-study.md`, `tools/README.md` e `tools/verify_axis_artifacts.py` foram sincronizados para tratar o corte como encerrado e `v2-native-memory-scope-hardening-cut` como nova frente ativa.

### Sprint 4 do V2 governed benchmark execution cut

- criado `tools/close_governed_benchmark_execution_cut.py` para fechar o recorte com resumo formal das decisoes e proximo recorte recomendado;
- criado `tests/unit/test_close_governed_benchmark_execution_cut.py` para validar payload e markdown do fechamento do recorte;
- criado `docs/implementation/v2-governed-benchmark-execution-cut-closure.md` como documento formal de encerramento do corte;
- `tools/engineering_gate.py --mode release` passou a verificar o fechamento regeneravel do corte ativo de benchmark em vez do fechamento do corte anterior;
- `docs/implementation/v2-governed-benchmark-execution-cut.md`, `HANDOFF.md`, `README.md`, `docs/executive/master-summary.md`, `docs/architecture/technology-study.md`, `tools/README.md` e `tools/verify_axis_artifacts.py` foram sincronizados para tratar a Sprint 4 como concluida e o recorte como formalmente encerrado.

### Fechamento da Sprint 4 do V2 domain consumers and workflows cut

- criado `tools/close_domain_consumers_and_workflows_cut.py` para gerar o fechamento formal regenerável do `v2-domain-consumers-and-workflows-cut` a partir do baseline `release-grade` já endurecido;
- criado `tests/unit/test_close_domain_consumers_and_workflows_cut.py` para validar payload e markdown do fechamento do corte;
- criado `docs/implementation/v2-domain-consumers-and-workflows-cut-closure.md` como documento formal de encerramento do corte;
- `tools/engineering_gate.py --mode release` passou a exigir também o fechamento regenerável do corte atual, além do verificador de baseline;
- `docs/implementation/v2-domain-consumers-and-workflows-cut.md`, `HANDOFF.md`, `README.md`, `docs/executive/master-summary.md` e `tools/README.md` foram sincronizados para tratar a Sprint 4 como concluída e apontar o próximo recorte recomendado.

Este changelog registra mudanças relevantes na documentação canônica, nos artefatos de continuidade e nas decisões estruturais do projeto `jarvis`.

Ele **não** substitui o Documento-Mestre, o `HANDOFF.md` ou futuros ADRs detalhados. Seu papel é manter rastreabilidade objetiva do que mudou, quando mudou e por que a mudança importa.

---

## 2026-03-30

### Revisão da estrutura documental ativa

- ciclos e cortes encerrados foram movidos para `docs/archive/implementation/`, preservando histórico sem mantê-los como documentos ativos;
- `docs/archive/executive/v1-scope-summary.md` e `docs/archive/documentation/estrutura_de_documentos_derivados.md` foram arquivados para reduzir ruído no estado atual do sistema;
- `docs/implementation/mission-continuity-final-increment.md` foi removido por não agregar mais valor operacional nem histórico relevante ao estado atual;
- `HANDOFF.md`, `README.md`, `docs/executive/master-summary.md`, `docs/roadmap/programa-ate-v3.md` e `docs/architecture/technology-study.md` foram sincronizados para refletir `v2-domain-consumers-and-workflows-cut` como recorte ativo único.

### Fechamento do V2 sovereign alignment cut

- criado `tools/close_sovereign_alignment_cut.py` para gerar o fechamento formal regenerável do `v2-sovereign-alignment-cut` a partir de observabilidade local, comparação por eixo e `evolution-lab`;
- criado `tests/unit/test_close_sovereign_alignment_cut.py` para validar payload e markdown do fechamento do corte soberano;
- criado `docs/implementation/v2-sovereign-alignment-cut-closure.md` como documento formal de encerramento do corte;
- `HANDOFF.md`, `README.md`, `docs/executive/master-summary.md`, `docs/archive/implementation/v2-sovereign-alignment-cut.md` e `tools/README.md` foram sincronizados para refletir o corte soberano como materialmente concluído e com artefato regenerável;
- criado `docs/implementation/v2-domain-consumers-and-workflows-cut.md` como novo recorte ativo do `v2`, sem reabrir a soberania interna já fechada.

### Sprint 4 do V2 domain consumers and workflows cut

- criado `tools/verify_active_cut_baseline.py` para verificar coerencia `release-grade` entre rotas ativas, contratos de consumo, workflows e benchmark governance;
- criado `tests/unit/test_verify_active_cut_baseline.py` para cobrir o verificador do baseline ativo;
- `tools/engineering_gate.py --mode release` passou a exigir `tools/verify_active_cut_baseline.py` antes da validacao final do baseline;
- `docs/implementation/v2-domain-consumers-and-workflows-cut.md`, `HANDOFF.md` e `tools/README.md` foram sincronizados para tratar a Sprint 4 como baseline endurecido em andamento.

### Sprint 3 do V2 domain consumers and workflows cut

- adicionadas regras explícitas para quando `absorver_depois` pode virar candidata real de absorção, tanto em `technology-study.md` quanto na matriz regenerável do corte ativo;
- criado `tools/render_governed_benchmark_matrix.py` com dataset versionado em `tools/benchmarks/datasets/v2_governed_benchmark_candidates.json` para regenerar a matriz do recorte;
- criado `docs/implementation/v2-governed-benchmark-matrix.md` como artefato de benchmark governado por familia de capacidade;
- a Sprint 3 passou a declarar todas as tecnologias que podem entrar neste recorte em `workflow_orchestration`, `continuous_operational_agents` e `multilayer_memory`;
- `AutoGPT Platform`, `Mastra` e `Mem0` ficaram formalizadas como `benchmark_now` sem promocao direta;
- `LangGraph`, `OpenAI Agents SDK`, `CrewAI`, `Microsoft Agent Framework`, `OpenClaw`, `Hermes Agent`, `Manus`, `Letta / MemGPT`, `Zep` e `Graphiti` ficaram formalizadas como `reference_envelope` do corte ativo;
- `docs/implementation/v2-domain-consumers-and-workflows-cut.md`, `docs/architecture/technology-study.md`, `HANDOFF.md`, `README.md` e `docs/executive/master-summary.md` foram sincronizados para tratar a Sprint 3 como concluida e a Sprint 4 como frente imediata.

### Sprint 2 do V2 domain consumers and workflows cut

- `shared/contracts`, `orchestrator-service`, `operational-service` e `langgraph_flow` passaram a tratar workflows como estado auditavel, com `workflow_state`, `workflow_governance_mode`, `workflow_decision_points`, `workflow_governance_declared`, `workflow_completed_steps` e `workflow_decisions`;
- `observability-service` passou a auditar `workflow_trace_status`, distinguindo caminhos saudáveis, incompletos, com atenção requerida ou não aplicáveis;
- `tools/internal_pilot_report.py` passou a expor `workflow_trace_status` nos resumos operacionais do piloto interno;
- `shared/domain_registry.py` e `knowledge/curated/domain_registry.json` passaram a permitir workflows canônicos por rota ativa, e o runtime agora propaga `workflow_domain_route` como origem explícita da composição operacional;
- todas as rotas de runtime ativas passaram a ter contrato mínimo de workflow no registry, e `tests/unit/test_domain_registry_workflows.py` passou a impedir regressão dessa malha;

### Sprint 1 do V2 domain consumers and workflows cut

- `knowledge/curated/domain_registry.json` e `shared/domain_registry.py` passaram a carregar metadados canônicos de consumo por rota promovida;
- `shared/contracts`, `memory-service` e `memory repository` passaram a persistir `consumer_profile`, `consumer_objective`, `expected_deliverables` e `telemetry_focus`;
- `specialist-engine`, `orchestrator-service` e `observability-service` passaram a usar esse pacote como contrato e telemetria obrigatória do caminho `guided`;
- novos asserts foram adicionados em `memory-service`, `specialist-engine`, `orchestrator-service` e `observability-service` para cobrir o consumidor canônico de software.

## 2026-03-28

### V2 sovereign alignment cut

- criado `docs/archive/implementation/v2-sovereign-alignment-cut.md` como documento vivo do corte ativo após o fechamento do `v2-alignment-cycle`;
- `HANDOFF.md`, `README.md`, `docs/executive/master-summary.md`, `docs/documentation/matriz-de-aderencia-mestre.md`, `docs/architecture/technology-study.md` e `tools/README.md` foram sincronizados para tratar esse corte como frente ativa e o `v2-alignment-cycle` como histórico fechado;
- `shared/domain_registry.py` passou a expor helpers canônicos de resolução de domínio e compatibilidade curta de labels legados;
- `knowledge-service`, `cognitive-engine`, `specialist-engine`, `orchestrator-service` e `langgraph_flow` passaram a publicar e consumir refs canônicas de domínio com mais rigor, incluindo `routing_source`, `canonical_domain_refs_by_route` e `primary_domain_driver`;
- `shared/mind_registry.py` passou a usar apenas afinidades de domínio baseadas na taxonomia canônica do Documento-Mestre;
- `shared/contracts`, `memory-service` e `memory repository` passaram a carregar explicitamente `consumed_memory_classes`, `memory_write_policies` e `domain_mission_link_reason` para memória compartilhada de especialistas;
- `observability-service` passou a auditar coerência mais rica de domínio, memória e arbitragem cognitiva, mantendo compatibilidade curta com trilhas antigas;
- criado `tools/verify_axis_artifacts.py` e o `tools/engineering_gate.py --mode release` passou a exigir verificação mínima de artefatos por eixo além da validação de baseline.

## 2026-03-27

### Próximo corte do v2

- `knowledge/curated/domain_registry.json` passou a promover também a rota `analysis`, agora ligada canonicamente a `structured_analysis_specialist` em modo `guided`;
- `knowledge-service` passou a priorizar rotas `active_specialist` também no recorte de `analysis`, tornando a rota promovida visível no retrieval do runtime;
- `cognitive-engine` passou a deduplicar `specialist_hints` quando uma rota de domínio promovida coincide com a heurística geral do núcleo;
- `memory-service` passou a gerar `domain_guided_memory_packet` de forma genérica para qualquer rota promovida no registry, e não só para `software_development`;
- `specialist-engine` e `orchestrator-service` passaram a tratar `structured_analysis_specialist` como rota guiada de domínio quando `analysis` estiver ativo;
- novos testes foram adicionados em `knowledge-service`, `cognitive-engine`, `memory-service`, `specialist-engine` e `orchestrator-service` para cobrir a promoção canônica de `analysis`.
- `knowledge/curated/domain_registry.json` passou a promover também a rota `governance`, agora ligada canonicamente a `governance_review_specialist` em modo `guided`;
- `specialist-engine` passou a tratar `governance_review_specialist` como contribuição guiada por domínio quando `governance` estiver ativo;
- novos testes foram adicionados em `knowledge-service`, `memory-service`, `specialist-engine` e `orchestrator-service` para cobrir a promoção canônica de `governance`.
- `knowledge/curated/domain_registry.json` passou a promover também a rota `operational_readiness`, agora ligada canonicamente a `operational_planning_specialist` em modo `guided`;
- `specialist-engine` passou a tratar `operational_planning_specialist` como contribuição guiada por domínio quando `operational_readiness` estiver ativo;
- novos testes foram adicionados em `knowledge-service`, `memory-service`, `specialist-engine` e `orchestrator-service` para cobrir a promoção canônica de `operational_readiness`.
- `knowledge/curated/domain_registry.json` passou a promover também a rota `strategy`, agora ligada canonicamente a `structured_analysis_specialist` em modo `guided`;
- `specialist-engine` passou a tratar `structured_analysis_specialist` como contribuição guiada por domínio quando `strategy` estiver ativo;
- `specialist-engine` também endureceu a seleção para aceitar apenas vínculos domínio->especialista que coincidam com o registry soberano, evitando handoffs inconsistentes;
- novos testes foram adicionados em `knowledge-service`, `memory-service`, `specialist-engine` e `orchestrator-service` para cobrir a promoção canônica de `strategy` e a validação canônica da seleção.
- `knowledge/curated/domain_registry.json` passou a promover também a rota `decision_risk`, agora ligada canonicamente a `governance_review_specialist` em modo `guided`;
- `specialist-engine` e `orchestrator-service` passaram a tratar `governance_review_specialist` como rota guiada de domínio também quando `decision_risk` estiver ativo;
- novos testes foram adicionados em `knowledge-service`, `memory-service`, `specialist-engine` e `orchestrator-service` para cobrir a promoção canônica de `decision_risk`.

### Constituição de engenharia e gate oficial

- criada `docs/documentation/engineering-constitution.md` como política oficial de robustez, segurança, reversibilidade e auditabilidade do repositório;
- criado `AGENTS.md` no root para fixar o comportamento obrigatório de qualquer agente implementador;
- criado `tools/engineering_gate.py` como gate oficial do repositório, com modos `quick`, `standard` e `release`;
- criado `.github/workflows/engineering-gate.yml` para tornar o gate executável também em CI;
- `README.md`, `HANDOFF.md` e `tools/README.md` passaram a apontar explicitamente para a política de engenharia e para o novo gate oficial.

### Sprint 6 do v2-alignment-cycle

- criado `tools/close_alignment_cycle.py` para fechar formalmente o `v2-alignment-cycle`, consolidando evidência de observabilidade, comparação local e backlog classificado entre `next_cut`, `deferred` e `vision`;
- `tools/compare_orchestrator_paths.py` passou a persistir o artefato default em `.jarvis_runtime/path_comparison_v2/`, alinhando o caminho real da comparação ao fechamento formal do ciclo;
- adicionados testes dedicados em `tests/unit/test_close_alignment_cycle.py` e ampliada a cobertura de `tests/unit/test_compare_orchestrator_paths.py` para o caminho estável de artefato;
- `HANDOFF.md`, `docs/archive/implementation/v2-alignment-cycle.md`, `docs/documentation/matriz-de-aderencia-mestre.md` e `tools/README.md` passaram a tratar a Sprint 6 como concluída e o próximo corte do `v2` como frente ativa.

## 2026-03-26

### Sprint 5 do v2-alignment-cycle

- `tools/internal_pilot_support.py` passou a carregar `mind_alignment_status`, `identity_alignment_status` e `axis_gate_status` no resultado estruturado do piloto;
- `tools/internal_pilot_report.py` passou a expor e renderizar os cinco eixos de aderência e o gate agregado de eixo por request;
- `tools/compare_orchestrator_paths.py` passou a comparar `mind_alignment_status`, `identity_alignment_status` e `axis_gate_status`, além de exigir gate saudável para `candidate_ready_for_eval_gate`;
- `evolution-lab` e `tools/evolution_from_pilot.py` passaram a usar `mind`, `identity` e `axis_gate` como sinais formais de proposta e comparação sandbox-only;
- `HANDOFF.md`, `docs/archive/implementation/v2-alignment-cycle.md` e `docs/documentation/matriz-de-aderencia-mestre.md` passaram a tratar a Sprint 5 como concluída e a Sprint 6 como próxima frente ativa.
### Sprint 3 e Sprint 4 do v2-alignment-cycle

- `shared/mind_registry.py` passou a governar a arbitragem do runtime com prioridade, afinidades por intenção e domínio, limite explícito de apoios e supressões e tensão dominante canônica;
- `cognitive-engine` passou a usar o registry de mentes como fonte soberana de mente primária, mentes de apoio e mentes suprimidas, emitindo resumo de arbitragem e sinais observáveis do eixo cognitivo;
- `identity-engine` passou a expor assinatura formal do núcleo, postura, foco de princípios e guardrails de governança, tornando a identidade mais auditável dentro do runtime;
- `governance-service` passou a receber `identity_mode`, `identity_signature` e `response_style`, registrando `identity_guardrail` no contexto da decisão;
- `orchestrator-service` passou a propagar sinais explícitos de identidade em `directive_composed`, `plan_governed` e `response_synthesized`;
- `observability-service` passou a auditar `mind_alignment_status` e `identity_alignment_status`, preparando a Sprint 5 como gate explícito de aderência por eixo;
- `HANDOFF.md`, `docs/archive/implementation/v2-alignment-cycle.md` e `docs/documentation/matriz-de-aderencia-mestre.md` passaram a refletir a Sprint 4 concluída e a Sprint 5 como próxima frente ativa.

### Sprint 2 do v2-alignment-cycle e documentação da visão longa

- `shared/memory_registry.py` passou a ser tratado também na documentação como política operacional por classe, e não apenas como catálogo tipado;
- `HANDOFF.md` passou a registrar a Sprint 2 do `v2-alignment-cycle` como concluída e a Sprint 3 como próxima frente ativa;
- `HANDOFF.md` passou a explicitar a visão longa do JARVIS como sistema cognitivo soberano capaz de absorver o melhor do ecossistema sem terceirizar identidade, memória, governança ou síntese;
- `HANDOFF.md` passou a distinguir `Hermes Agent` como referência principal de runtime persistente, memória viva e skills, e não como referência central do eixo de autoaperfeiçoamento;
- `docs/architecture/technology-study.md` passou a explicitar o fluxo longo de absorção tecnológica governada: radar, classificação arquitetural, memória evolutiva, sandbox e promoção por evidência;
- `docs/architecture/technology-study.md` passou a separar mais claramente as famílias de referência para runtime persistente, memória relacional e autoaperfeiçoamento;
- `docs/archive/implementation/v2-alignment-cycle.md` passou a registrar formalmente a Sprint 2 como concluída e a conectar o ciclo atual à preparação do núcleo para absorção tecnológica futura sem perda de soberania;
- `docs/documentation/matriz-de-aderencia-mestre.md` passou a refletir o novo estado do eixo de memórias e a registrar a camada futura de absorção tecnológica governada como parte do horizonte evolutivo do sistema.

## 2026-03-24

### Execução da Sprint 1 do ciclo v2-alignment-cycle

- `shared/domain_registry.py` foi criado como módulo soberano do registry de domínios, expondo `CANONICAL_DOMAIN_REGISTRY`, `RUNTIME_ROUTE_REGISTRY`, `RUNTIME_ELIGIBLE_ROUTES`, `SHADOW_SPECIALIST_ROUTES`, `FALLBACK_RUNTIME_ROUTE` e funções utilitárias `is_shadow_route`, `resolve_route` e `canonical_scopes_for_route`;
- `knowledge-service` passou a derivar o prior de intenção de `domain_scope` dos `canonical_refs` de cada rota, eliminando o dicionário hardcoded de pesos; domínios com `maturity=canonical_only` são excluídos do runtime; o fallback é derivado do registry;
- `specialist-engine` passou a verificar `is_shadow_route()` antes de acionar `software_change_specialist`, eliminando a heurística residual de shadow mode;
- `cognitive-engine` passou a usar `FALLBACK_RUNTIME_ROUTE` em vez de string hardcoded;
- `HANDOFF`, `v2-alignment-cycle` e `CHANGELOG` passaram a tratar a Sprint 1 do `v2-alignment-cycle` como concluída e a Sprint 2 como próxima frente ativa.

### Política de nomenclatura técnica

- o Documento-Mestre passou a registrar explicitamente a regra de que arquivos,
  módulos, classes, contratos e registries permanentes do sistema devem usar
  nomes estáveis e funcionais, sem marcadores transitórios como `v1`, `v2`,
  `poc`, `draft` ou `temp` no nome técnico principal;
- o `HANDOFF.md` passou a resumir essa política como regra operacional curta
  para as próximas rodadas de implementação.
- o registry canônico de domínios foi renomeado de
  `knowledge/curated/v2_domain_registry.json` para
  `knowledge/curated/domain_registry.json`.
- os scripts permanentes `tools/validate_v1.py`,
  `tools/close_post_v1_cycle.py` e `tools/close_v1_5_cycle.py` foram
  renomeados para `tools/validate_baseline.py`,
  `tools/close_continuity_cycle.py` e
  `tools/close_stateful_runtime_cycle.py`.

### Alinhamento estrutural ao Documento-Mestre

- `shared/mind_registry.py` passou a registrar as 24 mentes canônicas do mestre, incluindo o recorte ativo das 12 mentes nucleares e relações iniciais de suporte preferencial;
- `shared/memory_registry.py` passou a registrar as 11 classes canônicas de memória, com defaults formais de recuperação e elegibilidade para memória compartilhada com especialistas;
- `knowledge/curated/domain_registry.json` passou a separar o mapa canônico completo de domínios das rotas runtime ativas do ciclo, reduzindo o descompasso entre taxonomia do mestre e roteamento operacional;
- `knowledge-service`, `cognitive-engine`, `memory-service` e `orchestrator-service` passaram a consumir esses registries como base inicial do runtime progressivo, sem tratar mais o recorte do `v2` como se ele fosse o mapa completo do sistema;
- `matriz-de-aderencia-mestre`, `HANDOFF`, `README` e `v2-sprint-cycle` foram recalibrados para refletir que os registries canônicos já existem e que a lacuna restante agora está na soberania desses registries sobre o runtime.
- a política de nomenclatura técnica foi endurecida para deixar explícito que o sistema deve privilegiar nomes profissionais, limpos, robustos e duráveis;
- os módulos `shared/canonical_minds.py` e `shared/canonical_memories.py` foram renomeados para `shared/mind_registry.py` e `shared/memory_registry.py`, removendo `canonical` do nome técnico principal.

### Execução da Sprint 5 do ciclo v2

- `observability-service` passou a auditar `domain_alignment_status`, `memory_alignment_status` e `specialist_sovereignty_status` no fluxo de especialistas;
- `internal_pilot_support` passou a cobrir `software_shadow_review`, preservando comparação entre núcleo puro, especialista estrutural e especialista em `shadow mode`;
- `compare_orchestrator_paths` passou a emitir `baseline_axis_adherence_score`, `candidate_axis_adherence_score` e a comparar explicitamente aderência por eixo;
- a rodada local de comparação do `v2` fechou com `overall_verdict=equivalent`, `matched_scenarios=7/7` e `comparison_decision=candidate_ready_for_eval_gate`;
- `evolution_from_pilot` e `evolution-lab` passaram a carregar sinais de domínio, `shadow mode` e aderência aos eixos do mestre para proposals sandbox-only;
- `README`, `HANDOFF`, `master-summary`, `v2-sprint-cycle` e `matriz-de-aderencia-mestre` passaram a tratar a Sprint 5 do `v2` como concluída e a Sprint 6 como próxima frente ativa.

### Fechamento da Sprint 6 e do primeiro corte do v2

- `tools/close_specialization_cycle.py` passou a gerar o artefato formal de fechamento do primeiro corte do `v2`, usando evidência de observabilidade, comparação e aderência por eixo;
- `docs/archive/implementation/v2-cycle-closure.md` passou a registrar a decisão formal de encerramento do primeiro corte do `v2`;
- `docs/archive/implementation/v2-alignment-cycle.md` passou a abrir o próximo ciclo do programa, com foco explícito em `domínios`, `memórias`, `mentes`, identidade auditável e gates por eixo;
- `docs/archive/implementation/v2-alignment-cycle.md` passou a registrar uma matriz explícita conectando todas as tecnologias estudadas aos eixos `domínios`, `mentes` e `memórias`, com regra clara de absorção para cada uma;
- `README`, `HANDOFF`, `master-summary`, `tools/README` e `v2-sprint-cycle` passaram a refletir que a Sprint 6 foi concluída e que o próximo ciclo ativo já não é mais expansão de especialistas por si só, e sim alinhamento do runtime ao Documento-Mestre.

### Execução da Sprint 4 do ciclo v2

- `knowledge-service` passou a carregar `knowledge/curated/domain_registry.json` como registry inicial dos domínios ativos do ciclo;
- `KnowledgeRetrievalResult` passou a expor `registry_domains` e `specialist_routes`, tornando explícita a ponte entre domínio ativo e rota de especialista;
- `cognitive-engine` passou a priorizar hints vindos do registry e `software_development` abriu a primeira rota canônica `domínio -> especialista` do `v2`;
- `specialist-engine` passou a materializar `linked_domain` e `selection_mode`, incluindo `software_change_specialist` em `shadow mode`;
- `orchestrator-service` e o fluxo opcional de `LangGraph` passaram a registrar `domain_registry_resolved` e `specialist_shadow_mode_completed`;
- `README`, `HANDOFF`, `master-summary`, `v2-sprint-cycle` e `matriz-de-aderencia-mestre` passaram a tratar a Sprint 4 do `v2` como concluída e a Sprint 5 como próxima frente ativa.

### Execução da Sprint 3 do ciclo v2

- `shared/contracts` passou a expor `SpecialistSharedMemoryContextContract` e `SpecialistInvocationContract` passou a carregar `shared_memory_context`;
- `memory-service` e seus repositórios passaram a persistir contexto compartilhado por especialista em regime `core_mediated_read_only`, com política explícita de escrita `through_core_only`;
- `specialist-engine` passou a compor handoffs com memória compartilhada relacional resumida, sem entregar escrita direta ao especialista;
- `orchestrator-service` e o fluxo opcional de `LangGraph` passaram a preparar, anexar e auditar `specialist_shared_memory_linked` antes do handoff;
- `tools/benchmarks/harness.py` foi ajustado para ampliar o limite de consulta da trilha observável e evitar truncamento após o novo evento de memória compartilhada;
- `HANDOFF`, `README`, `master-summary`, `v2-sprint-cycle` e `matriz-de-aderencia-mestre` passaram a tratar a Sprint 3 do `v2` como concluída e a Sprint 4 como próxima frente ativa.

### Correção estrutural do Documento-Mestre

- `documento_mestre_jarvis.md` passou a abrir com um mapa editorial rápido para leitura por blocos;
- os blocos residuais de `Próximo passo` e `Encaminhamento` foram convertidos em fechamentos editoriais estáveis, reduzindo a voz de elaboração dentro do mestre;
- as lacunas numéricas `179â€“181`, `215â€“216`, `264` e `275â€“285` passaram a ter notas editoriais explícitas para preservar a numeração histórica sem buraco silencioso;
- as referências quebradas para `docs/operations/v1-production-controlled.md` e `docs/operations/go-live-readiness.md` foram substituídas pelo derivado operacional ativo `docs/operations/v1-operational-baseline.md`;
- foi corrigido o erro tipográfico na seção de critérios de qualidade por mudança.
- o capítulo de escopo do mestre passou a explicitar camadas editoriais, o que o documento não deve virar e a regra de derivação para documentos vivos;
- os blocos de implementação, operação e continuidade passaram a declarar mais claramente seu papel como política canônica, e não como backlog tático ou runbook diário.
- o rótulo do documento deixou de tratá-lo como mera versão `0.1` fundacional e passou a reconhecê-lo como artefato canônico vivo;
- a seção de árvore inicial do repositório foi compactada e realinhada ao estado real do monorepo;
- referências restantes a arquivos inexistentes de implementação, documentação de serviço e subpastas antigas de `shared/types` foram substituídas por caminhos vivos do repositório;
- a checagem final do mestre passou a fechar sem caminhos ausentes apontados em blocos documentais.
- o resumo executivo interno do mestre foi compactado para evitar duplicação desnecessária com `docs/executive/master-summary.md`;
- o capítulo de escopo passou a distinguir melhor o que o mestre guarda como visão canônica e o que ele preserva como recorte estruturante histórico do `v1`.
- o bloco de backlog estrutural do `v1` foi reescrito para preservar apenas frentes canônicas, dependências e ordem macro, removendo detalhamento excessivo de épicos e módulos do corpo do mestre;
- o bloco de blueprint inicial foi consolidado para registrar só a política canônica de organização do monorepo, com nota editorial explícita para a consolidação das antigas seções `130â€“141`;
- as especificações dos quatro pilares deixaram de terminar em tom de plano imediato e passaram a encerrar com fechamentos editoriais estáveis, reduzindo deriva de backlog dentro do mestre.
- a seção `197` teve a árvore inicial do repositório limpa e reescrita sem `mojibake`, com estrutura textual legível e estável;
- foram removidas do mestre as seções editoriais vazias `214â€“216`, `263â€“264` e `274â€“285`, que não carregavam norma nem valor canônico e só aumentavam fragmentação artificial da numeração.
- os blocos editoriais residuais `179â€“181` também foram removidos, e os headings `75.11` e `76.13` deixaram de soar como plano imediato e passaram a funcionar como fechamentos editoriais consistentes;
- foi mantida a numeração histórica restante do mestre, sem renumeração global, para preservar estabilidade de referências cruzadas já usadas na auditoria, na matriz de aderência e nos documentos vivos.
- o capítulo de qualidade por serviço passou a abrir com formulação mais curta e canônica, reduzindo redundância entre política de qualidade e plano de validação.
- o bloco da camada evolutiva (`313â€“327`) foi consolidado para preservar escopo, fluxo, critérios, benchmarks e riscos sem carregar detalhamento operacional excessivo no corpo do mestre.
- o bloco final de operação, readiness, incidentes e transições de fase (`344â€“349`) foi ajustado para tom mais seco e canônico, reduzindo repetição editorial e reforçando que o detalhamento executável pertence aos derivados operacionais.
- as aberturas e sínteses dos blocos evolutivo e de qualidade foram limpas de fórmulas repetitivas, reduzindo eco editorial sem alterar o conteúdo normativo.

### Reescrita da auditoria primária do Documento-Mestre

- `docs/archive/documentation/auditoria-primaria-documento-mestre.md` foi reescrito como auditoria primária baseada em leitura completa do mestre e validação local, substituindo o relatório anterior que misturava achados corretos, exagerados e factualmente incorretos;
- a nova auditoria separa problemas reais do Documento-Mestre, exageros da auditoria anterior, leitura mestre x implementação e plano de correção sem reescrita integral;
- ficou formalizado que a correção do mestre deve partir de evidência confirmada no próprio repositório e continuar usando `docs/documentation/matriz-de-aderencia-mestre.md` como ponte entre visão canônica e backlog.

### Auditoria completa do Documento-Mestre

- `docs/documentation/matriz-de-aderencia-mestre.md` deixou de cobrir só `mentes`, `domínios` e `memórias` e passou a registrar a auditoria completa dos blocos canônicos do mestre;
- a matriz agora classifica todos os eixos em `runtime maduro`, `runtime parcial`, `tipado/documentado`, `canônico apenas`, `deferido por fase` ou `contradição real`;
- a auditoria passou a produzir também classe final de priorização entre `corrigir agora`, `manter deferido` e `apenas preservar como visão`;
- `HANDOFF`, `README`, `master-summary` e `v2-sprint-cycle` passaram a tratar a matriz como ponte oficial entre visão canônica e backlog executável;
- o `v2` foi recalibrado para declarar por sprint o eixo do mestre movimentado, a lacuna dominante atacada e o que permanece conscientemente fora de cobertura.

### Execução da Sprint 1 do ciclo v2

- `shared/contracts` passou a expor contratos explícitos de convocação e fronteira para especialistas subordinados;
- `specialist-engine` passou a materializar invocações internas com limites de runtime, memória, tool layer e canal de resposta;
- `orchestrator-service` e o fluxo opcional de `LangGraph` passaram a emitir `specialist_contracts_composed`, distinguindo convocação de especialista de operação comum do núcleo;
- a resposta final continua sendo consolidada apenas pelo núcleo, e os especialistas permanecem escondidos do usuário final, sem resposta direta, sem tools próprias e sem escrita de memória fora do núcleo.

### Execução da Sprint 2 do ciclo v2

- `specialist-engine` passou a separar seleção, composição de contrato e execução do handoff interno;
- `governance-service` passou a avaliar handoffs internos de especialistas antes da execução, com decisão explícita e rastreável;
- `orchestrator-service` e o fluxo opcional de `LangGraph` passaram a emitir `specialist_selection_decided`, `specialist_handoff_governed` e `specialist_handoff_blocked` quando necessário;
- a convocação de especialistas agora pode ser auditada sem inferência a partir do texto final, preservando o núcleo como única superfície de resposta ao usuário.

### Regra de refatoração do Documento-Mestre e ponte de execução

- `docs/archive/documentation/estrutura_de_documentos_derivados.md` passou a explicitar quando o Documento-Mestre deve ser reorganizado, sem reescrita integral;
- o sistema documental passou a reconhecer artefatos de aderência e tradução entre visão canônica e implementação incremental;
- ficou formalizado que ciclos de sprint devem declarar qual lacuna do mestre fecham e quais eixos permanecem fora de cobertura no ciclo atual.

### Matriz de aderência do mestre

- criado `docs/documentation/matriz-de-aderencia-mestre.md` como ponte explícita entre visão canônica e backlog executável;
- a matriz passou a registrar, por eixo, o estado real de `mentes`, `domínios` e `memórias`, com níveis de maturidade e próximos passos;
- `README`, `HANDOFF`, `master-summary` e `v2-sprint-cycle` passaram a apontar para essa matriz como critério de recalibração do ciclo ativo.

### Leitura operacional por eixo

- a matriz passou a explicitar, para `mentes`, `domínios` e `memórias`, a lacuna dominante, a pergunta de implementação, a prioridade no `v2` e o critério de avanço esperado;
- ficou formalizado que a ordem de correção do descompasso é `domínios`, `memórias` e `mentes`;
- a Sprint 3 do `v2` passou a ser lida explicitamente como avanço prioritário do eixo de memórias, com impacto indireto em domínios.

## 2026-03-22

### Execução da Sprint 6 do ciclo v1.5

- criado `tools/close_v1_5_cycle.py` para consolidar evidência operacional e comparativa do primeiro ciclo do `v1.5` e emitir o corte formal para `v2`;
- criado `docs/archive/implementation/v1-5-cycle-closure.md` como fechamento oficial do primeiro ciclo do `v1.5`;
- criado `docs/archive/implementation/v2-sprint-cycle.md` como novo plano rolante ativo da fase seguinte;
- atualizado `v1-5-sprint-cycle`, `HANDOFF`, `README`, `master-summary`, `tools/README.md` e a estrutura documental para refletir a promoção formal para `v2`;
- o corte do `v2` ficou explicitamente centrado em especialistas subordinados, memória relacional e handoffs governados, mantendo fora do recorte imediato voz oficial, `computer use` amplo, `pgvector` como base canônica e assistente operacional amplo.

### Execução da Sprint 5 do ciclo v1.5

- o piloto passou a incluir cenários explícitos de conflito de continuidade e retomada manual após pausa governada;
- `internal_pilot_support` passou a registrar aderência a expectativas de decisão, operação e continuidade por cenário;
- `compare_orchestrator_paths` passou a emitir `baseline_expectation_score`, `candidate_expectation_score`, `candidate_runtime_coverage` e decisão explícita de comparação;
- a rodada local de comparação do `v1.5` fechou com `overall_verdict=equivalent`, `matched_scenarios=6/6` e `comparison_decision=candidate_ready_for_eval_gate`;
- `internal_pilot_report` passou a resumir também `expectation_status` para leitura operacional rápida do runtime;
- `evolution_from_pilot` e `evolution-lab` passaram a carregar `continuity_runtime_mode`, preservando proposals e comparações sandbox-only sobre o recorte absorvido.

### Execução da Sprint 4 do ciclo v1.5

- o fluxo opcional de `LangGraph` passou a isolar a continuidade em um subfluxo stateful próprio, sem reescrever o restante do orquestrador;
- checkpoint, replay e pausa governada passaram a ser executados dentro desse recorte dedicado antes do restante do caminho deliberativo;
- o fluxo passou a emitir `continuity_subflow_completed` com `runtime_mode=langgraph_subflow`, tornando a absorção parcial observável no trilho local;
- `observability-service` passou a auditar `continuity_runtime_mode`, diferenciando baseline linear e recorte absorvido em `LangGraph`;
- `internal_pilot_report` e `compare_orchestrator_paths` passaram a carregar `continuity_runtime_mode` para sustentar a Sprint 5 de evals e comparação;
- adicionados testes do fluxo `LangGraph`, da auditoria de observabilidade e das ferramentas de relatório e comparação.

### Execução da Sprint 3 do ciclo v1.5

- adicionado `ContinuityPauseContract` como contrato interno de pausa governada e retomada manual da continuidade;
- `memory-service` passou a expor `get_session_continuity_pause()` e `resolve_session_continuity_pause()`, persistindo resolução manual rastreável por sessão;
- checkpoints em `awaiting_validation` ou `contained` agora geram pausa recuperável com `pause_status`, `pause_reason`, `resolution_status` e vínculo com o `checkpoint_id`;
- `orchestrator-service` e o fluxo opcional de `LangGraph` passaram a aceitar `metadata.continuity_resume` e a emitir `continuity_pause_resolved` quando a pausa é resolvida manualmente;
- `planning-engine`, `governance-service` e `synthesis-engine` passaram a tratar pausa governada como estado explícito do runtime, sem retomada silenciosa acima de checkpoint contido ou aguardando validação;
- adicionados testes de pausa governada, resolução manual e recuperação segura em memória e orquestração.

### Execução da Sprint 2 do ciclo v1.5

- adicionado `ContinuityReplayContract` como contrato interno de replay e recuperação governada da continuidade;
- `memory-service` passou a expor `get_session_continuity_replay()` com `replay_status`, `recovery_mode`, `resume_point` e exigência de retomada manual quando aplicável;
- a recuperação passou a incluir `continuity_replay_status`, `continuity_recovery_mode` e `continuity_resume_point` como hints estruturais;
- `orchestrator-service` e o fluxo opcional de `LangGraph` passaram a emitir `continuity_replay_loaded` e `continuity_recovery_governed`;
- `planning-engine`, `governance-service` e `synthesis-engine` passaram a tratar checkpoints contidos ou aguardando validação como retomada governada, sem continuidade automática;
- adicionados testes de replay em memória, orquestração, planejamento, governança, síntese e PostgreSQL.

### Execução da Sprint 1 do ciclo v1.5

- adicionado `ContinuityCheckpointContract` como contrato interno mínimo para checkpoint recuperável da continuidade;
- `memory-service` passou a persistir checkpoints explícitos por sessão, com status, resumo e replay mínimo;
- a recuperação passou a expor esses checkpoints como hints estruturais e a API `get_session_continuity_checkpoint()` passou a permitir inspeção direta do estado recuperável;
- adicionados testes de persistência entre instâncias e integração com PostgreSQL para o novo estado de checkpoint.

### Regra de estudo externo explicitada para o v1.5

- `docs/archive/implementation/v1-5-sprint-cycle.md` passou a explicitar quais estudos externos entram no `v1.5` e quais ficam fora do corte imediato;
- `HANDOFF.md` passou a resumir essa regra para retomada operacional curta, destacando `LangGraph` e `Hermes Agent` como referências mais diretamente ligadas ao ciclo.

### Execução da Sprint 6 do ciclo pós-v1

- criado `tools/close_post_v1_cycle.py` para consolidar evidência operacional do primeiro ciclo e emitir o corte formal entre `v1.5` e `v2`;
- criado `docs/archive/implementation/post-v1-cycle-closure.md` como fechamento oficial do primeiro ciclo do `pós-v1`;
- criado `docs/archive/implementation/v1-5-sprint-cycle.md` como novo plano rolante ativo da fase seguinte;
- atualizado `post-v1-sprint-cycle`, `HANDOFF`, `README`, `master-summary`, `tools/README.md` e a estrutura documental para refletir a promoção formal para `v1.5`.

### Execução da Sprint 5 do ciclo pós-v1

- `observability-service` passou a exigir `continuity_decided` na trilha mínima e a auditar sinais próprios de continuidade, incluindo `continuity_action`, `continuity_source`, lacunas de sinal e anomalias de retomada;
- `orchestrator-service` e a trilha opcional de `LangGraph` passaram a registrar continuidade também em `memory_recovered`, `response_synthesized` e `memory_recorded`, tornando a decisão comparável ao longo do fluxo;
- `tools/internal_pilot_report.py` passou a expor status de continuidade, sinais ausentes e anomalias específicas da continuidade;
- `tools/compare_orchestrator_paths.py` passou a comparar também coerência de continuidade entre baseline e fluxo opcional de `LangGraph`;
- `evolution-lab` e `tools/evolution_from_pilot.py` passaram a tratar saúde de continuidade como sinal explícito de proposta e comparação sandbox-only;
- adicionados testes de observabilidade, relatórios do piloto, comparação de paths, laboratório evolutivo e orquestração para travar a Sprint 5.

### Sincronização executiva pós-Sprint 5

- atualizados `README.md` e `docs/executive/master-summary.md` para refletir corretamente que as Sprints 1 a 5 já foram concluídas e que a Sprint 6 passa a ser a frente ativa do ciclo.

### Execução das Sprints 2 e 3 do ciclo pós-v1

- concluída a Sprint 2 com recuperação e ranking determinístico de continuidade relacionada;
- `memory-service` passou a decidir de forma reproduzível entre missão ativa, loops abertos e missão relacionada, com recomendação explícita de continuidade;
- `planning-engine` passou a distinguir explicitamente `continuar`, `encerrar`, `reformular` e `retomar`, incluindo motivo de continuidade no plano deliberativo;
- `orchestrator-service` passou a registrar o evento `continuity_decided`, tornando a escolha de continuidade observável por `request_id`;
- `governance-service` passou a deferir retomada relacionada quando ela disputa direção com loops ainda abertos da missão ativa;
- `synthesis-engine` passou a refletir a retomada relacionada também no caminho governado, sem esconder a decisão no texto final;
- removido `POC` da nomenclatura técnica da trilha opcional de `LangGraph`, com rename para `langgraph_flow.py`, `LangGraphFlowRunner` e `handle_input_langgraph_flow()`.

### Execução da Sprint 4 do ciclo pós-v1

- `memory-service` passou a persistir um snapshot de continuidade da sessão acima da missão atual;
- a recuperação agora reaproveita `session_continuity_brief`, `session_continuity_mode` e âncoras de continuidade como hints estruturais;
- `synthesis-engine` passou a abrir a resposta com uma linha de continuidade ativa coerente com continuação, encerramento, reformulação ou retomada;
- `orchestrator-service` passou a injetar esses sinais explicitamente na síntese final;
- adicionados testes de persistência e de tom de continuidade para memória, síntese e orquestração.

### Refinamento do fluxo de análise e incorporação tecnológica

- ampliado `docs/architecture/technology-study.md` com perguntas mínimas obrigatórias de estudo, fluxo oficial de incorporação, formas corretas de entrada no sistema e relação explícita com programa, sprint cycle e handoff;
- explicitado no `technology-study.md` quem conduz a análise, como o agente deve estudar a tecnologia, como deve incorporar por recorte, quais evidências precisa produzir e quais condições bloqueiam promoção;
- reforçado `HANDOFF.md` com a regra curta de promoção tecnológica para evitar absorção direta de tecnologia externa no núcleo sem lacuna concreta, classificação e evidência.

### Revisao documental ampla do repositorio

- revisados e atualizados os documentos centrais e os derivados mais importantes para refletir o estado real do projeto: `v1` encerrado, `pos-v1` aberto e Sprint 2 como frente ativa;
- reescrito `HANDOFF.md` para reduzir historico excessivo, atualizar o commit de referencia e consolidar a retomada operacional;
- reescrito `README.md` para apresentar o baseline atual e a leitura correta da fase do projeto;
- atualizados documentos operacionais, executivos, de implementacao e de arquitetura para remover contradicoes sobre fechamento do `v1`, `GO CONDICIONAL`, porta local do PostgreSQL e foco do ciclo atual;
- refinado `docs/architecture/technology-study.md` para refletir melhor o peso atual de `CrewAI`, `AutoGen`, `Microsoft Agent Framework` e da camada de referencias arquiteturais por funcao.

### Restauracao de contexto apos enxugamento excessivo

- reforcado `HANDOFF.md` com um bloco curto de baseline materializado para preservar visibilidade operacional sem voltar ao historico gigante;
- ampliado `docs/operations/v1-operational-baseline.md` com criterios de ampliacao ou contencao e com a lista dos artefatos operacionais do baseline;
- ampliado `docs/implementation/implementation-strategy.md` com uma leitura historica mais concreta da sequencia que fechou o `v1` e das capacidades operacionais que emergiram desse caminho.

### Referencias arquiteturais por funcao formalizadas no Documento-Mestre

- complementado `documento_mestre_jarvis.md` com uma camada explicita de referencias arquiteturais por funcao, separando o eixo de posicionamento na stack do eixo de papel arquitetural;
- formalizada a leitura por `referencia central`, `referencia secundaria` e `benchmark conceitual` para orquestracao, agente de software, computer use, memoria persistente, assistencia operacional e contratos;
- atualizado `docs/architecture/technology-study.md` para refletir os dois eixos de decisao e ampliar a matriz de referencias externas;
- atualizado `docs/archive/documentation/estrutura_de_documentos_derivados.md` para explicitar que o Documento-Mestre guarda tanto o posicionamento oficial de tecnologias quanto as referencias arquiteturais oficiais por funcao;
- atualizado `docs/executive/master-summary.md` e `HANDOFF.md` para refletir a nova regra documental e arquitetural.

### Execucao da Sprint 1 do ciclo rolante

- concluido o modelo interno minimo de continuidade entre missoes relacionadas;
- adicionados contratos compartilhados minimos para candidatas e contexto de continuidade relacionada;
- `memory-service` passou a recuperar candidatas de missao relacionada dentro da mesma sessao, inclusive no primeiro turno de uma nova missao;
- `orchestrator-service` passou a repassar a melhor candidata relacionada para o `planning-engine`;
- `planning-engine` passou a registrar a fonte da continuidade no plano deliberativo e a explicitar alvo e razao da continuidade relacionada na racionalizacao;
- adicionados testes de memoria, planejamento e orquestracao para travar a leitura de missao relacionada sem quebrar a API publica do `v1`.

### Sistema de planejamento em duas camadas ate `v3`

- criado `docs/roadmap/programa-ate-v3.md` como contrato de direcao do `pos-v1` ate `v3`, separando `pos-v1`, `v1.5`, `v2` e `v3` por objetivos, gates e limites;
- criado `docs/archive/implementation/post-v1-sprint-cycle.md` como plano rolante oficial das proximas `6` sprints, com foco total em `continuidade profunda entre missoes`;
- formalizado o sistema documental em tres papeis: `HANDOFF.md` para retomada operacional, `programa-ate-v3.md` para direcao macro e `post-v1-sprint-cycle.md` para execucao imediata;
- atualizadas as referencias em `HANDOFF.md`, `README.md` e `docs/archive/documentation/estrutura_de_documentos_derivados.md` para tornar o novo sistema de planejamento a leitura oficial do proximo ciclo.

---

## 2026-03-20

### Abertura disciplinada do pos-v1

- encerramento do `v1` seguido de abertura disciplinada do `pos-v1` no proprio `HANDOFF.md`;
- definida a trilha prioritaria do `pos-v1` como `continuidade profunda entre missoes`;
- centralizadas as orientacoes operacionais do proximo ciclo no `HANDOFF.md`, sem criar documento novo;
- autorizado estudo externo curto para `LangGraph`, `Hermes Agent`, `Graphiti` e `Zep`, sempre como apoio dirigido e nao como bloqueio da implementacao principal.
- explicitado que `Hermes Agent` entra no estudo como referencia de continuidade e runtime persistente, nao como referencia principal de autoaperfeicoamento;
- explicitado que a trilha de autoaperfeicoamento continua mais associada a `DSPy / MIPRO`, `TextGrad`, `AFlow`, `EvoAgentX`, `SEAL` e `Darwin Godel Machine`, ficando fora do foco imediato do primeiro ciclo pos-`v1`.

### Pacote final de robustez do `v1` e `jarvis-console`

- implementado `tools/operational_artifacts.py` para gerar `baseline snapshot`, `containment drill` e `incident evidence` em `.jarvis_runtime/operational/`;
- ampliado `tools/validate_v1.py` para validar coerencia entre missao, memoria e governanca, gerar snapshot do baseline e executar smoke do `jarvis-console`;
- ampliado `tools/go_live_internal_checklist.py` para validar `defer_for_validation` por conflito de missao, coerencia de `open_loops`, evidencia operacional e drill minimo de contencao/rollback;
- `tools/run_internal_pilot.py` passou a atualizar tambem `latest_pilot.json` e `latest_pilot.md`;
- criado `apps/jarvis_console/` como interface textual minima do `v1`, com modos `ask` e `chat` sobre o `orchestrator-service`;
- endurecido o `memory-service` para preservar o estado de missao aceito quando um turno posterior e bloqueado ou adiado para validacao;
- ampliado o `observability-service` com geracao de `incident evidence` para requests anomalas ou governadas;
- adicionados testes do console, dos artefatos operacionais, da preservacao de missao no orquestrador e da evidencia operacional;
- validados `pytest -q`, `ruff check .`, `python tools/check_mojibake.py .`, `python tools/validate_v1.py --profile development`, `python tools/validate_v1.py --profile controlled`, `python tools/go_live_internal_checklist.py --profile development`, `python tools/go_live_internal_checklist.py --profile controlled`, `python tools/run_internal_pilot.py --profile controlled` e `python tools/internal_pilot_report.py --limit 10`.

---
## 2026-03-20

### Abertura disciplinada do pos-v1

- encerramento do `v1` seguido de abertura disciplinada do `pos-v1` no proprio `HANDOFF.md`;
- definida a trilha prioritaria do `pos-v1` como `continuidade profunda entre missoes`;
- centralizadas as orientacoes operacionais do proximo ciclo no `HANDOFF.md`, sem criar documento novo;
- autorizado estudo externo curto para `LangGraph`, `Hermes Agent`, `Graphiti` e `Zep`, sempre como apoio dirigido e nao como bloqueio da implementacao principal.
### Incremento curto de continuidade entre missoes

- criado `docs/implementation/mission-continuity-final-increment.md` como plano executavel do ultimo incremento cognitivo curto antes do fechamento disciplinado do `v1`;
- ampliado o `planning-engine` para usar `mission_goal` e `mission_recommendation`, explicitar conflito entre o pedido atual e a missao ativa e escolher entre `continuar`, `encerrar` e `reformular` com mais rigor;
- ajustado o `memory-service` para priorizar hints de continuidade de missao na recuperacao e persistir um `identity_continuity_brief` mais util entre turnos;
- ajustado o `orchestrator-service` para repassar objetivo de missao e recomendacao anterior ao planejamento;
- ajustado o `synthesis-engine` para refletir continuidade, fechamento ou reformulacao da missao sem expor o pipeline interno;
- atualizados os testes de planejamento, sintese, memoria e orquestracao; `pytest -q`, `ruff check` e `python tools/validate_v1.py --profile development` passaram apos a implementacao.

---
## 2026-03-20

### Abertura disciplinada do pos-v1

- encerramento do `v1` seguido de abertura disciplinada do `pos-v1` no proprio `HANDOFF.md`;
- definida a trilha prioritaria do `pos-v1` como `continuidade profunda entre missoes`;
- centralizadas as orientacoes operacionais do proximo ciclo no `HANDOFF.md`, sem criar documento novo;
- autorizado estudo externo curto para `LangGraph`, `Hermes Agent`, `Graphiti` e `Zep`, sempre como apoio dirigido e nao como bloqueio da implementacao principal.
### Enxugamento e reorganizacao de `docs/`

- consolidados `docs/operations/go-live-readiness.md`, `docs/operations/v1-go-no-go-decision.md` e `docs/operations/v1-production-controlled.md` em `docs/operations/v1-operational-baseline.md`;
- consolidado o estudo de tecnologia em `docs/architecture/technology-study.md`, substituindo a separacao entre matriz geral e fase 1 aplicada;
- movidos `docs/implementation/sprint-1-plan.md`, `docs/implementation/first-milestone-plan.md` e `docs/operations/internal-pilot-plan.md` para `docs/archive/`;
- movidos `docs/architecture/specialists-v2.md` e `docs/architecture/voice-runtime.md` para `docs/future/`;
- removidos o placeholder `docs/adr/README.md` e a revisao transitoria `docs/documentation/revisao_do_conjunto_documental_2026-03-20.md`;
- atualizadas as referencias vivas em `HANDOFF.md`, `docs/operations/incident-response.md`, `docs/roadmap/v1-roadmap.md` e `docs/archive/documentation/estrutura_de_documentos_derivados.md`.

### Sincronização documental com o estado atual do repositório

- atualizados os documentos executivos, operacionais, arquiteturais e de implementação para refletir o ciclo cognitivo mais unitário já implementado no núcleo;
- atualizados os documentos de `go/no-go`, readiness e piloto para refletir que o `internal pilot` controlado já foi executado com resultado saudável;
- mantida a leitura de `GO CONDICIONAL`, mas com foco deslocado de "executar o piloto" para "consolidar a leitura do piloto e decidir o fechamento do v1";
- a revisao do conjunto documental foi absorvida pela propria reorganizacao de `docs/`, com consolidacao, arquivamento e separacao entre material ativo, historico e futuro;
- preservado o papel canônico de `documento_mestre_jarvis.md` como norte da visão de produto.

---

## 2026-03-19

### Internal pilot executável, comparação de paths e proposals evolutivas

- adicionada auditoria operacional de fluxo ao `observability-service`, com trilha mínima obrigatória, flags automáticas de anomalia e visão de requests recentes;
- ampliado `tools/internal_pilot_report.py` para refletir `trace_status`, `anomaly_flags` e `source_services` por request;
- criado `tools/internal_pilot_support.py` para unificar cenários, bootstrap e coleta estruturada do `internal pilot`;
- criado `tools/run_internal_pilot.py` para executar a janela mínima do piloto e persistir evidência local em `JSON` e `Markdown`;
- criado `tools/compare_orchestrator_paths.py` para comparar baseline e fluxo opcional de `LangGraph` nos mesmos cenários;
- ampliado o `evolution-lab` com entrada de `FlowEvaluationInput` e helpers para comparar sinais reais do piloto;
- criado `tools/evolution_from_pilot.py` para transformar trilhas recentes e comparações de paths em proposals sandbox-only;
- ampliado o corpus curado do `knowledge-service` com domínios de `observability` e `pilot_operations`, mantendo retrieval determinístico;
- atualizados testes de observabilidade, `internal_pilot_report`, `knowledge-service`, `evolution-lab` e utilitários do piloto.

### Preparação do internal pilot e fluxo experimental de LangGraph

- adicionado `tools/internal_pilot_report.py` para resumir trilhas recentes por `request_id`, status operacional, decisão de governança e eventos obrigatórios ausentes;
- criado `docs/operations/internal-pilot-plan.md` como plano mínimo da primeira janela controlada após o `GO CONDICIONAL`;
- endurecido o `JsonlAgenticMirrorAdapter` para espelhar `trace tree` local com root trace e child runs, permitindo validar a estrutura de rastreabilidade mesmo sem credencial externa;
- endurecido `tools/go_live_internal_checklist.py` para exigir árvore de trace no espelhamento agentic;
- adicionada integração experimental opcional de `LangGraph` ao `orchestrator-service`, preservando `handle_input()` como caminho principal e expondo `handle_input_langgraph_flow()` como rota experimental sem breaking change;
- adicionado extra opcional `langgraph` no `pyproject.toml` para permitir o fluxo experimental do orquestrador sem contaminar o bootstrap padrão do `v1`.

### LangSmith complementar e ADR de LangGraph

- endurecido o adaptador `LangSmith` do `observability-service` para espelhar fluxos como `trace tree` por `request_id`, com root trace, child runs e metadata consistente;
- adicionados suporte a `LANGSMITH_ENDPOINT` e `LANGSMITH_WORKSPACE_ID` para cloud, hybrid ou self-hosted;
- ampliados os testes do `observability-service` para validar agrupamento por request e estrutura da árvore de traces;
- criado `docs/adr/adr-001-absorcao-parcial-de-langgraph-no-nucleo.md` para formalizar a absorção parcial de `LangGraph` como próximo salto estrutural do núcleo, sem reescrita ampla imediata do `v1`.

### Estudo aplicado da stack principal

- criado `docs/architecture/technology-study-phase1-core-stack.md` para registrar a Fase 1 do estudo de reaproveitamento tecnológico;
- consolidada a leitura aplicada de `LangGraph`, `PostgreSQL + pgvector` e `LangSmith` contra o estado real do repositório;
- registrada a decisão refinada desta fase: `LangSmith` como complemento imediato do ciclo de `internal pilot`, `LangGraph` como próximo salto estrutural do núcleo sem reescrita ampla imediata, e `pgvector` aprovado arquiteturalmente mas fora do caminho crítico até existir consumidor semântico real.

### Ciclo deliberativo do núcleo

### Memória semântica curta de missão

- ampliado `MissionStateContract` com `semantic_brief` e `semantic_focus` para representar continuidade de missão em nível semântico curto, sem criar serviço novo;
- atualizados os repositórios `sqlite` e `PostgreSQL` do `memory-service` para persistir e recuperar os novos campos com migração incremental de schema;
- ajustado o `memory-service` para emitir `mission_semantic_brief` e `mission_focus` como hints reutilizáveis no turno seguinte;
- ajustado o `planning-engine` para usar esses sinais como continuidade semântica explícita no plano e no rationale, sem substituir o contexto episódico;
- atualizados testes de memória, planejamento, orquestração e integração PostgreSQL; `pytest -q` voltou a passar integralmente e `ruff check` passou nos arquivos alterados.

- introduzido `DeliberativePlanContract` como artefato estruturado do núcleo para resumir objetivo, etapas, riscos, restrições e recomendacao operacional;
 - ampliado o `executive-engine` para produzir diretiva com confiança, ambiguidade, modo preferido de resposta e controle de execução;
- refeito o fluxo do `orchestrator-service` para operar como `entender -> decompor -> arbitrar -> decidir -> registrar -> responder`, incluindo os eventos `directive_composed`, `plan_built`, `plan_governed` e `clarification_required`;
- expandido o `memory-service` para persistir hints deliberativos de plano e resumo de missão, fortalecendo continuidade entre turnos;
- ajustado o `governance-service` para decidir com base no plano pretendido, não apenas na intenção textual;
- ajustados `operational-service` e `synthesis-engine` para consumir e refletir o plano deliberativo no resultado final;
- atualizados os testes de engines, memória, governança, operação e orquestração; a suite `pytest -q` voltou a passar integralmente.

### Matriz de estudo tecnologico

- criado `docs/architecture/technology-study-matrix.md` para consolidar o estudo de tecnologias, frameworks, algoritmos e repositórios citados no Documento-Mestre;
- organizada a classificação entre base do `v1`, complementos controlados, laboratório, inspiracao arquitetural e itens a deferir para `v2`;
- registrada a ordem recomendada de estudo local de repositórios externos e as regras de segurança para clonar e analisar tecnologias fora do repositório principal do JARVIS.

### Benchmark harness e validação local

 - implementado o pacote `tools/benchmarks/` com harness executável, dataset versionado e artefatos auditáveis em `.jarvis_runtime/benchmarks/`;
 - adicionada exportação `trace view` no `observability-service` para validar compatibilidade com tracing externo sem trocar o envelope interno;
 - criada `.venv` local e instaladas as dependências `.[dev]` para validação do baseline no ambiente do projeto;
 - validado o benchmark local com decisões preliminares: `knowledge -> weighted_deterministic`, `observability -> adotar no v1`, `evolution -> manual_variants`, `memory -> manter baseline atual até validar PostgreSQL`;
- validada a suite completa com `pytest -q` e os arquivos novos com `ruff check`.

### Baseline após benchmark

- promovido o ranking ponderado determinístico para o `knowledge-service`, absorvendo no baseline a melhoria escolhida pelo benchmark;
- ajustado o `evolution-lab` para registrar `manual_variants` como estratégia sandbox prioritária, sem promoção automática;
- ampliados os testes de `knowledge-service` e `evolution-lab` para travar o comportamento promovido ao baseline;
- rerodado o benchmark e validado que `knowledge` agora aparece como `manter baseline atual`, refletindo que a melhoria já foi incorporada ao sistema.

### Readiness de PostgreSQL e benchmark CLI

- adicionado suporte de CLI ao harness de benchmark com `--output-dir`, `--dataset-path`, `--postgres-url` e `--print-json`;
- isolado o escopo do benchmark de memória com identificadores únicos por execução para evitar colisão entre rodadas;
- adicionados testes opcionais de integração PostgreSQL para o `memory-service` e para a trilha de memória do benchmark, com `skip` quando `DATABASE_URL` ou `psycopg` não estiverem disponíveis;
- atualizado o handoff com o fluxo correto de validação da candidata PostgreSQL.

### Validação real de PostgreSQL

- instalado o extra `postgres` na `.venv` local para habilitar o backend real com `psycopg`;
- validado o `memory-service` contra PostgreSQL local com teste de integração dedicado;
- ajustado o harness para isolar execuções por identificadores únicos e medir paridade funcional de forma consistente com o comportamento real da memória;
 - recalibrados os limites de latência do benchmark de memória para comparar `sqlite` com PostgreSQL local sem exigir um teto irreal para um banco operacional;
 - rerodado o benchmark com `DATABASE_URL` real e decisão final `memory -> adotar no v1`;
 - alterado o `docker compose` local do PostgreSQL para publicar em `5433`, evitando conflito com um `postgres.exe` local ativo na máquina.

### Alinhamento dos derivados ao baseline consolidado

- atualizados `docs/implementation/implementation-strategy.md`, `docs/implementation/service-breakdown.md` e `docs/roadmap/v1-roadmap.md` para refletir o baseline benchmarkado do `v1`;
- atualizados `docs/operations/v1-production-controlled.md` e `docs/operations/go-live-readiness.md` para tratar `PostgreSQL` como backend operacional recomendado e explicitar que a decisão de `go/no-go` ainda está pendente;
- atualizado `docs/architecture/evolution-lab.md` para refletir `manual_variants` como estratégia priorizada no sandbox do `v1`;
- atualizado `docs/archive/executive/v1-scope-summary.md` para registrar o estado atual do `v1` e a pendencia de fechamento para produção controlada.

### Decisão formal de readiness do v1

- criado `docs/operations/v1-go-no-go-decision.md` para registrar a decisão formal de readiness do `v1`;
- registrada a decisão atual como `GO CONDICIONAL` para produção controlada em escopo reduzido;
- atualizado `docs/operations/go-live-readiness.md` para refletir que a decisão de `go/no-go` já foi tomada;
- atualizado `docs/operations/v1-production-controlled.md` para incorporar o estado formal da decisão;
- atualizado `docs/executive/master-summary.md`, que ainda estava atrasado em relação ao estado real do repositório.

---

## 2026-03-18

### Benchmark dirigido do v1

- implementado um harness local único em `tools/benchmarks/` para benchmarkar memória, knowledge, observabilidade e evolution-lab;
- congelado um dataset versionado em `tools/benchmarks/datasets/v1_benchmark_cases.json` com cenários de `planning`, `analysis`, `general_assistance`, bloqueio por governança e continuidade de sessão;
 - adicionada persistência de artefatos auditáveis do benchmark em `JSON` e `Markdown`;
 - adicionada exportação de trace view no `observability-service` para validar compatibilidade com tracing externo sem substituir a trilha interna;
- adicionados testes do harness de benchmark e cobertura da exportação de trace view;
- atualizado o `HANDOFF.md` para refletir o benchmark dirigido como próximo gate do fechamento do `v1`.


### Core v1 baseline

- implementado o primeiro baseline integrado do `v1`, conectando `orchestrator-service`, `memory-service`, `governance-service`, `knowledge-service`, `observability-service`, `operational-service` e `engines/`;
- reduzido o `orchestrator-service` ao papel de coordenador de fluxo, movendo classificação, planejamento, composicao cognitiva e síntese para engines dedicadas;
- preservado `InternalEventEnvelope` como envelope canônico para observabilidade e rastreabilidade do fluxo ponta a ponta.

### Memory Service

- substituido o armazenamento em `dict` por uma camada de repositório persistente;
- adicionado backend local por `sqlite` e suporte a `PostgreSQL` quando `DATABASE_URL` estiver configurada;
 - adicionada persistência de histórico episódico por `session_id`, resumo contextual de sessão e estado mínimo de missão por `mission_id`;
 - ampliados os testes para validar continuidade entre instâncias do serviço e persistência de estado de missão.

### Observability Service

 - implementado o `observability-service` como coletor estruturado de eventos internos;
 - adicionada persistência local da trilha de eventos e consulta por `request_id`, `session_id`, `mission_id` e `correlation_id`;
- integrado o orquestrador a essa trilha persistente em vez de depender apenas do retorno em memória.

### Knowledge e Engines

 - implementado o `knowledge-service` com retrieval local determinístico sobre domínios prioritários do `v1`;
- externalizado o corpus inicial do `knowledge-service` para `knowledge/curated/v1_corpus.json`;
- implementadas as engines de identidade, executivo, planejamento, cognição e síntese;
- ampliada a cobertura de testes para validar classificação de intenção, composição de domínios ativos e síntese final.

### Governance e Operational

- expandido o `governance-service` para suportar `allow`, `allow_with_conditions`, `block` e `defer_for_validation`;
- adicionadas condições, auditoria e proteção de mutação em memória crítica na decisão de governança;
- expandido o `operational-service` para produzir artefatos textuais reais e preencher `artifacts`, `checkpoints` e `memory_record_hints`.

### Evolution Lab

- implementado o `evolution-lab` como primeiro corte de sandbox evolutivo local;
 - adicionada persistência local de propostas e decisões de comparação entre baseline e candidata;
 - estabelecido regime `sandbox-only`, sem promoção automática, com rollback referenciado ao baseline.

### Bootstrap e validação

- ajustado `tests/conftest.py` para incluir a raiz do repositório no `sys.path` durante a execução dos testes;
- adicionado `conftest.py` na raiz para que testes isolados de serviços e engines carreguem o bootstrap corretamente;
- ajustado `pyproject.toml` para incluir `shared` na descoberta de pacotes do projeto;
- adicionado extra opcional `postgres` em `pyproject.toml` para readiness do backend PostgreSQL;
- desabilitado o cache nativo do `pytest` em configuração para evitar warnings recorrentes de permissão no ambiente local atual;
- validada a suite com `pytest -q` a partir da raiz, sem `PYTHONPATH` manual.

### PostgreSQL readiness

- ampliada a fabrica de memória para normalizar `postgres://` e `postgresql+psycopg://` antes de instanciar o backend PostgreSQL;
- adicionados indices básicos nas tabelas de memória para o caminho local e para o caminho PostgreSQL;
- criado `infra/local-postgres.compose.yml` como infraestrutura local padrao para validar a memória persistente contra PostgreSQL;
- ampliada a cobertura de testes da memória para selecao de backend e parsing de URL.

### Documentação operacional

- atualizados `README.md`, `HANDOFF.md`, `docs/implementation/implementation-strategy.md`, `docs/implementation/service-breakdown.md`, `docs/roadmap/v1-roadmap.md`, `docs/architecture/evolution-lab.md` e documentos operacionais para refletir o baseline atual do `v1`.

---

## 2026-03-17

### Operational Service

- substituido o esqueleto vazio do `operational-service` por um primeiro serviço funcional mínimo para tarefas seguras e deterministicas;
- adicionado suporte a:
  - execução de `draft_plan`;
  - execução de `produce_analysis_brief`;
  - execução de `general_response`;
  - retorno via `OperationResultContract` com status e outputs estruturados;
- ampliados os testes do `operational-service` para cobrir task suportada e task não suportada.

### Orchestrator Service

- integrado o `orchestrator-service` ao `operational-service`;
- o fluxo permitido agora gera `OperationDispatchContract`, executa a operação e incorpora o resultado na síntese final;
- adicionados os eventos `operation_dispatched` e `operation_completed` ao fluxo permitido;
- ampliados os testes do `orchestrator-service` para validar despacho operacional permitido e a ausência de operação em fluxos bloqueados.

### HANDOFF

- atualizado para refletir que o projeto agora possui um fluxo mínimo explícito `orchestrator -> governance -> memory -> operational`.

### Validação

- validada por execução Python direta a cadeia completa `orchestrator -> governance -> memory -> operational`;
- `pytest` continua pendente por ausência de dependência instalada no ambiente local atual.

---

## 2026-03-17

### Memory Service

- substituido o esqueleto vazio do `memory-service` por um primeiro serviço funcional mínimo em memória de processo;
- adicionado suporte a:
  - recuperação contextual por sessão com `MemoryRecoveryContract`;
  - registro episódico simples de turno com `MemoryRecordContract`;
  - janela curta de recuperação para o contexto recente da sessão;
- ampliados os testes do `memory-service` para cobrir sessão vazia e continuidade básica de contexto.

### Orchestrator Service

- integrado o `orchestrator-service` ao `memory-service`;
- o fluxo mínimo agora recupera contexto antes da decisão e grava o turno ao final;
- adicionados os eventos `memory_recovered` e `memory_recorded` ao fluxo principal;
- ampliados os testes do `orchestrator-service` para validar recuperação de contexto entre dois turnos da mesma sessão.

### HANDOFF

- atualizado para refletir que o projeto agora possui um fluxo mínimo explícito `orchestrator -> governance -> memory`.

### Validação

- validada por execução Python direta a cadeia `memory-service -> orchestrator-service` com recuperação contextual na segunda interação da mesma sessão;
- `pytest` continua pendente por ausência de dependência instalada no ambiente local atual.

---

## 2026-03-17

### Governance Service

- substituído o esqueleto vazio do `governance-service` por um primeiro serviço funcional mínimo;
- adicionado suporte a:
  - avaliação de request com base em `InputContract`;
  - classificação determinística de risco;
  - geração de `GovernanceCheckContract`;
  - geração de `GovernanceDecisionContract` com `allow` e `block`;
- ampliados os testes do `governance-service` para cobrir um fluxo de baixo risco e um fluxo sensível bloqueado.

### Orchestrator Service

- removida a política mínima de governança que ainda estava embutida localmente no `orchestrator-service`;
- o `orchestrator-service` agora depende do `governance-service` para obter checagem e decisão;
- preservado o papel do orquestrador como coordenador do fluxo, emissor de eventos e sintetizador de resposta.

### HANDOFF

- atualizado para refletir que o projeto agora possui integração mínima explícita entre `orchestrator-service` e `governance-service`.

### Validação

- validada por execução Python direta a cadeia `governance-service -> orchestrator-service`;
- `pytest` continua pendente por ausência de dependência instalada no ambiente local atual.

---

## 2026-03-17

### Orchestrator Service

 - substituído o esqueleto vazio do `orchestrator-service` por um primeiro fluxo funcional mínimo;
 - adicionado suporte a:
  - recebimento de `InputContract`;
  - classificação simples de intenção;
  - geração de `GovernanceCheckContract`;
  - avaliação inicial de governança com `allow` e `block`;
  - emissão de eventos internos prioritários;
  - síntese textual básica coerente com a identidade inicial do sistema;
 - ampliados os testes do `orchestrator-service` para cobrir um fluxo de baixo risco e um fluxo sensível bloqueado.

### HANDOFF

- atualizado para refletir que o projeto saiu do estado de esqueleto puro do orquestrador e entrou no primeiro fluxo funcional mínimo.

### Validação

- validado o fluxo do `orchestrator-service` por execução Python direta com carga manual de `sys.path`;
- `pytest` continua pendente por ausência de dependência instalada no ambiente local atual.

---

## 2026-03-16

### Documento-Mestre

- preenchida a seção `236.1 Blocos essenciais`, que estava vazia;
- adicionada a seção `235.5 Continuidade editorial e rastreabilidade` para formalizar a preservação histórica de numeração e o papel de capítulos de `Encaminhamento` e `Próximo passo`;
- ampliada a seção `236.2 Itens que podem virar documentos derivados`;
- substituído o fechamento duplicado do fim do documento por capítulos operacionais e de maturidade;
- enxugado o bloco final do Documento-Mestre para manter no arquivo principal apenas definições canônicas e referências para derivados operacionais;
- enxugados os blocos de roadmap de milestones e de implementação, preservando no arquivo principal a sequência canônica e deslocando a leitura tática para derivados;
- realizado pente fino final para reduzir linguagem exploratória em decisões tecnológicas já consolidadas.

### HANDOFF

- reestruturado para formato operacional de continuidade;
- removida a duplicacao excessiva do conteúdo do Documento-Mestre;
- alinhado ao estado do projeto após a consolidação documental;
- atualizado para refletir a materialização da Sprint 1 no repositório real;
- atualizado novamente para refletir o início da Sprint 2 com base semântica compartilhada mínima.

### Estrutura documental

- consolidada a separação prática entre:
  - `documento_mestre_jarvis.md` como artefato canônico;
  - `HANDOFF.md` como documento operacional de continuidade;
  - `CHANGELOG.md` como registro de mudanças relevantes;
- criada a política de desmembramento em `docs/archive/documentation/estrutura_de_documentos_derivados.md`;
- criado o pacote inicial de derivados de implementação, operação, arquitetura, executive summary e roadmap.

### Repositório real

- criada a base estrutural do monorepo na raiz com:
  - `README.md`
  - `.gitignore`
  - `.editorconfig`
  - `.env.example`
  - `pyproject.toml`
  - `package.json`;
- criada a árvore principal do repositório;
- criados os esqueletos mínimos dos serviços centrais e das engines centrais;
- preparada a base compartilhada para a Sprint 2 em `shared/contracts`, `shared/schemas`, `shared/types`, `shared/events` e `shared/state`;
- implementada a primeira camada canônica de `shared/` com tipos, contratos, schemas, eventos e identidade/princípios;
- adicionados testes iniciais de regressão estrutural em `tests/unit/test_shared_layer.py`.

### Validação

- validada a estrutura criada com `rg --files` e inspeção recursiva de diretórios;
- validada a importação dos esqueletos de serviços e engines com `python`;
- validada a importação da nova camada `shared/` com `python`;
- a execução de `python -m pytest` ainda não foi concluída porque `pytest` não está instalado no ambiente local atual.
