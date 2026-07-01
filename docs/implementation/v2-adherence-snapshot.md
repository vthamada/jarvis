# V2 Adherence Snapshot

## 1. Objetivo

Este documento registra um snapshot de aderencia entre o estado atual do repositorio,
a visao canonica do [documento_mestre_jarvis.md](../../documento_mestre_jarvis.md)
e a direcao operacional consolidada nos documentos vivos do projeto.

Ele existe para:

- identificar rapidamente onde o runtime ja esta coerente com a visao;
- separar gap real de deferimento correto por fase;
- orientar a escolha do proximo recorte funcional sem reabrir decisoes ja fechadas;
- manter backlog tecnico subordinado ao Documento-Mestre, e nao a conveniencias locais.

Leitura correta:

- o Documento-Mestre continua sendo a unica fonte canonica de visao;
- este arquivo e uma auditoria derivada e revisavel;
- [HANDOFF.md](../../HANDOFF.md) continua sendo a retomada tatico-operacional;
- [execution-backlog.md](./execution-backlog.md) passa a ser a fila micro ativa, e este snapshot nao deve voltar a carregar backlog executavel;
- [matriz-de-aderencia-mestre.md](../documentation/matriz-de-aderencia-mestre.md)
  continua sendo a taxonomia formal de status.

---

## 2. Fotografia atual

Estado de referencia desta revisao:

- data da fotografia: `2026-05-17`
- ultimo recorte funcional fechado: `v2-native-memory-scope-hardening-cut`
- ultimo recorte estrutural fechado: `v2-repository-hygiene-and-tools-review-cut`
- passo funcional em andamento: lotes `MB-062` a `MB-150` concluidos ate leitura operacional e medicao de aprendizado revisado; nao ha novo item tecnico `ready` sem repriorizacao explicita.

Leitura executiva:

- nao existe hoje divergencia arquitetural grave entre o sistema e o Documento-Mestre;
- a visao canonica tambem ficou mais explicita em tres pontos: LLMs e runtimes agentic entram como substrato subordinado ao nucleo, multiplas superficies devem expor uma unica entidade e o cerebro do sistema inclui estado operacional do ecossistema;
- existe, sim, distancia de materializacao em alguns eixos centrais do `v2`, mas os gaps criticos diminuiram;
- dominios, especialistas promovidos e memoria guiada agora ja operam com contrato soberano ponta a ponta nas rotas promovidas do baseline atual;
- o que resta como backlog correto passa a ser maturacao declarativa adicional, nao correcao de desvio estrutural do `v2`;
- essa explicitude adicional do Mestre continua coerente com a trajetoria atual do runtime, embora a parte de superficies amplas e estado ambiental mais rico siga mais no horizonte do `v3` do que no baseline ativo;
- a soberania de dominios avancou mais um passo: rotas promovidas agora ja aparecem como `promoted_route_registry` soberano nos eventos do runtime, reduzindo recomputacao local no orquestrador e melhorando auditoria de elegibilidade.
- a malha dominio->especialista tambem avancou: packets guiados de memoria agora nascem da rota promovida elegivel do registry e sao validados contra o contrato canonico da rota antes da convocacao especializada.
- a continuidade de projetos/objetivos agora existe como baseline minimo: `project_ref`, `objective_ref`, work items, checkpoints, artefatos, `objective_status` e `next_action_ref` atravessam runtime, memoria, replay, eventos e observabilidade sem abrir autonomia longa.
- o console agora expoe esse estado por `objectives --mission-id ...` e permite transicoes bounded por `objective --mission-id ... --action ...`, sempre via governanca, memoria canonica e evento auditavel, sem transformar objetivos em scheduler autonomo.
- a sintese final agora tambem expoe estado operacional bounded do objetivo ativo quando esse contexto existe, incluindo status, proxima acao, decisao pendente e artefato relevante, sem vazar detalhes internos de especialistas.
- a observabilidade e os relatorios agora medem se essa camada esta sendo util: objetivo consultado, retomado, pausado, bloqueado, concluido, proxima acao redefinida, ausencia de proxima acao e ausencia de artefato.
- a repriorizacao pos-objetivos escolheu estrutura evolutiva e absorcao tecnologica governada como proxima frente: candidatos tecnologicos agora possuem contrato minimo, classe de absorcao, papel subordinado, evidencias, testes, rollback e bloqueio explicito contra violacao da soberania do nucleo.
- o `evolution-lab` agora consegue persistir esses candidatos como propostas `sandbox-only`, com matriz de absorcao, readiness, blockers e politica de promocao manual.
- observabilidade, piloto, relatorio, comparador e console agora tornam esses candidatos visiveis ao operador sem permitir promocao, execucao automatica ou substituicao do nucleo.
- a repriorizacao pos-`MB-125` escolheu experiencia operacional e reflexao
  pos-tarefa governada como proxima frente; isso aproxima o sistema da visao
  autoevolutiva por registros estruturados de missao, outcome, falhas,
  decisoes, evidencias e aprendizados candidatos, ainda sem autoedicao ou
  autopromocao.
- `MB-127` a `MB-131` materializaram essa frente: contratos compartilhados,
  memoria evolutiva bounded, propostas `sandbox-only`, observabilidade,
  relatorio e console read-only, ainda sem promocao automatica.
- `MB-132` abriu a repriorizacao seguinte em torno do `Operator Learning Loop`:
  o foco deixa de ser criar infraestrutura isolada e passa a fechar o ciclo
  `usar -> registrar -> refletir -> propor -> revisar -> medir` em uma missao
  governada do operador, mantendo autopromocao, voz, realtime, UI rica,
  scheduler autonomo e browser/computer use amplo fora de fase.
- `MB-133` materializou o primeiro passo tecnico desse loop: cada fluxo real
  governado do `orchestrator-service` agora registra automaticamente
  `ExperienceRecordContract` em memoria evolutiva bounded, com sinais de rota,
  workflow, mente, dominio, especialista, plano, execucao, outcome, checkpoints
  e evidencias.
- `MB-134` adicionou reflexao automatica bounded sobre essa experiencia,
  sempre com revisao humana, evidencia, testes sugeridos, rollback e bloqueio
  de autopromocao/mutacao do nucleo; influencia causal em planejamento/sintese
  continua reservada para `MB-135`.
- `MB-135` fechou a primeira influencia causal bounded: o runtime busca
  reflexoes relevantes por workflow, rota e dominio, registra
  `reflection_influence_status`, carrega refs auditaveis no plano e torna a
  influencia visivel na sintese final, sem injecao indiscriminada nem promocao
  automatica.
- `MB-136` criou uma fila humana read-only de revisao evolutiva no
  `evolution-lab` e no console, derivada de propostas sandbox, com estados,
  blockers, testes, rollback e promocao bloqueada sem gate humano.
- `MB-137` adicionou evidencia comparativa baseline vs reflection-assisted em
  observabilidade, piloto interno, relatorio e comparador, mantendo qualquer
  ganho local fora de promocao automatica.
- `MB-138` expos esse ciclo no console por `mission-cycle --mission-id ...`,
  agregando missao, objetivo, plano, experiencia, reflexao, proposta evolutiva
  e status de revisao em modo read-only.
- `MB-139` adicionou `mission-workflow "..." --mission-id ...`, executando uma
  missao governada ponta a ponta ate proposta sandbox e revisao humana pendente.
- `MB-140` fechou a documentacao operacional em
  `docs/operations/operator-learning-loop.md`; o proximo corte deve nascer de
  repriorizacao explicita.
- `MB-141` a `MB-145` foram fechados como lote de controles humanos de revisao
  evolutiva, para aprovar, rejeitar, sandboxar, devolver para revisao ou
  rollbackar propostas sem autopromocao.
- `MB-142` a `MB-145` fecharam esse recorte: contrato compartilhado de decisao
  humana, transicoes no `evolution-lab`, comando `evolution-review` no console,
  observabilidade, relatorio, comparador e docs agora propagam proposta,
  operador, evidencias, rollback, status final e limites de revisao.
- `MB-146` abriu a repriorizacao seguinte: o foco passa a ser transformar
  decisoes humanas aprovadas ou sandboxadas em guidance bounded, filtravel e
  mensuravel para planejamento/sintese, mantendo autopromocao, self-modification
  e alteracao de pesos fora de fase.
- `MB-147` formalizou `ReviewedLearningGuidanceContract`, schema e evento
  canonico, e adicionou derivacao no `evolution-lab` somente para revisoes
  `approved` ou `sandboxed`, mantendo flags de autopromocao e mutacao do nucleo
  bloqueadas.
- `MB-148` conectou esse guidance revisado a memoria, orquestracao, planning e
  synthesis com filtro por rota, workflow e dominio, refs auditaveis, motivo de
  aplicacao ou bloqueio e sem promocao automatica.
- `MB-149` e `MB-150` fecharam a medicao e leitura operacional do feedback de
  aprendizado revisado: observabilidade, piloto, relatorio, comparador,
  console e documentacao agora mostram baseline vs reviewed-learning-assisted,
  refs, motivo, taxas e conclusao `no_promotion_without_release_gate`.
- o contrato canonico da rota ativa passou a atravessar tambem o `planning` e a influenciar a `synthesis`, reduzindo a distancia entre memoria guiada disponivel e comportamento final do runtime.
- esse contrato agora tambem molda passos, restricoes, criterios de sucesso e checkpoint/gate governado do plano, e ja aparece na leitura final como objetivo, entrega esperada, foco de leitura e workflow ativo da rota promovida.
- esse mesmo slice soberano agora tambem atravessa `operation_dispatch`, `workflow_*` e `operation_completed`, e a observabilidade passou a marcar drift quando objetivo, entregaveis, foco de sucesso, foco final e telemetria deixam de bater entre composicao e execucao.
- memoria guiada avancou mais um passo: `semantic` e `procedural` agora alteram de forma mais causal `steps`, `smallest_safe_next_action`, `success_criteria` e framing final de `planning`/`synthesis`, em vez de aparecer apenas como hint contextual.
- o vinculo `mente primária -> domínio primário -> rota ativa` agora também atravessa `planning`, `response_synthesized` e `observability`, reduzindo leitura implícita no runtime final.
- a malha `mente -> dominio -> especialista` tambem ficou menos implicita: `cognitive-engine` e `specialist-engine` passaram a preferir rotas explicitas alinhadas ao `primary_domain_driver`, e a observabilidade passou a cobrar esse match quando o runtime ja o conhece.
- metacognicao causal avancou um passo real: `planning`, `synthesis`, `response_synthesized` e `observability` agora explicitam quando a ancora cognitiva alterou `success_criteria`, `smallest_safe_next_action` ou recomendacao de contencao, em vez de deixar esse efeito apenas implícito no rationale.
- a observabilidade tambem passou a distinguir `workflow_trace_status` de `workflow_profile_status`, separando falha real de baseline de sinais que ainda entram apenas como `maturation_recommended`.
- `internal_pilot_report` e `compare_orchestrator_paths` agora tambem expoem `workflow_profile_status`, tornando esse sinal parte do artefato comparativo e nao apenas da auditoria local.
- esses mesmos artefatos agora tambem classificam explicitamente o workflow em `baseline_saudavel`, `maturation_recommended` ou `attention_required`, deixando a leitura de maturacao separada do gate estrutural.
- `observability-service`, `internal_pilot_report` e `compare_orchestrator_paths` agora distinguem memoria causal (`causal_guidance`) de memoria apenas anexada (`attached_only`), expondo tambem foco semantico, hint procedural e especialistas ligados a esse efeito.
- `internal_pilot_report` e `compare_orchestrator_paths` agora tornam `dominant_tension`, `primary_domain_driver` e `mind_domain_specialist_status` parte explicita da leitura comparativa do baseline.
- `cognitive-engine` agora aplica recomposicao observavel em impasses reais de rota especializada, `orchestrator-service` publica `cognitive_recomposition_applied` e `observability-service` audita esse sinal ao longo do fluxo.
- `evolution_from_pilot` e `evolution-lab` agora tratam `workflow_profile_status`, `memory_causality_status`, `mind_domain_specialist_status` e recomposicao cognitiva como sinais comparativos de refinamento, e nao apenas como telemetria lateral do baseline.
- os fechadores regeneraveis `close_alignment_cycle` e `close_sovereign_alignment_cut` agora carregam decisoes e taxas desses sinais novos, aproximando comparacao sandbox, snapshot e closure docs da mesma gramatica de maturacao.
- `engineering_gate --mode release` agora roda um verificador dedicado (`tools/verify_release_signal_baseline.py`) para tratar `workflow_profile_status`, `memory_causality_status`, `mind_domain_specialist_status` e recomposicao cognitiva como gramatica formal de release.
- o piloto agora inclui cenarios deliberados para memoria causal (`guided_memory_followup`) e recomposicao cognitiva por `specialist_route_impasse` (`recomposition_impasse`), com leitura comparativa e textual coerente.
- `compare_orchestrator_paths` agora marca drift explicito de `workflow_profile_status`, `memory_causality_status`, `dominant_tension`, `primary_domain_driver`, `mind_domain_specialist_status` e recomposicao cognitiva entre baseline e candidata.
- `planning-engine`, `synthesis-engine` e `response_synthesized` agora tornam `dominant_tension`, `primary_domain_driver`, `workflow_response_focus` e recomposicao cognitiva mais declarativos no comportamento final do runtime.
- `cognitive-engine`, `specialist-engine`, `planning-engine`, `synthesis-engine` e `orchestrator-service` agora carregam `mind_domain_specialist_contract_*`, distinguindo cadeia autoritativa, override bounded e fallback governado como contrato explicito da ultima milha do runtime.
- `specialist-engine`, `operation_dispatch`, `operational-service`, `workflow_*` e `response_synthesized` agora aplicam esse contrato como politica viva: a rota promovida ativa prioriza o especialista canonico no consumo final quando ele existe, e a ultima milha fica contida no nucleo quando o contrato exige fallback governado.
- `observability-service`, `internal_pilot_report`, `internal_pilot_support` e `compare_orchestrator_paths` agora tratam `mind_domain_specialist_effectiveness` e `mind_domain_specialist_mismatch_flags` como evidencia primaria da ultima milha, separando alinhamento efetivo de mismatch entre cadeia autoritativa, framing e especialista realmente consumido.
- `OperationDispatchContract`, `OperationResultContract`, `orchestrator-service`, `operational-service` e eventos internos agora carregam `ecosystem_state_status`, `active_work_items`, `active_artifact_refs`, `open_checkpoint_refs` e `surface_presence` como gramatica minima de estado operacional do ecossistema.
- `memory-service`, `shared/memory_registry.py`, `continuity_checkpoint`, `continuity_replay`, `mission_state` e `mission_runtime_state` agora persistem e retomam esse slice como estado soberano bounded de continuidade, sem abrir memoria temporal rica fora de fase.
- `observability-service`, `internal_pilot_report`, `internal_pilot_support`, `compare_orchestrator_paths` e `verify_active_cut_baseline.py` agora expõem `operational_ecosystem_state_status`, cobertura de work items, artefatos, checkpoints e presença de superfície como evidência comparável do baseline.
- `evolution-lab`, `evolution_from_pilot`, `verify_release_signal_baseline.py`, `close_alignment_cycle.py` e `close_sovereign_alignment_cut.py` agora registram readiness do estado operacional do ecossistema como sinal regenerável de release, sem promover multissuperfície ou autonomia ampla automaticamente.
- `SurfaceIdentityContract`, `InputContract`, `OperationDispatchContract`, `OperationResultContract`, schemas, eventos e `apps/jarvis_console` agora carregam `surface_id`, `surface_kind`, `surface_session_id`, escopo de capacidade, operador, usuario canonico e `surface_continuity_status` como contrato minimo de identidade por superficie.
- `orchestrator-service`, fluxo opcional de `LangGraph`, `planning` e `synthesis` agora propagam esse slice pelos eventos centrais e contextos internos do runtime atual, preservando `through_core_only`.
- `memory-service`, `session_continuity`, `continuity_checkpoint`, `continuity_replay`, `mission_state` e `mission_runtime_state` agora persistem e recuperam superficies vinculadas, superficie ativa, ultima superficie conhecida e flags de conflito de identidade.
- `observability-service`, `internal_pilot_report`, `internal_pilot_support`, `compare_orchestrator_paths`, `verify_active_cut_baseline.py`, `evolution-lab`, `evolution_from_pilot.py` e `verify_release_signal_baseline.py` agora expoem continuidade de superficie como status, contagem de superficies vinculadas, flags de conflito e readiness auditavel.
- `MB-106` fechou documentalmente o lote minimo de continuidade multissuperficie; voz/realtime, web rica, API publica, memoria temporal relacional e substrate operacional amplo continuam fora de fase.
- `MB-107` a `MB-109` fecharam a repriorizacao explicita derivada de `EV-001`, escolhendo `SO-003` apenas como recorte minimo de continuidade de projetos/objetivos.
- `MB-110` a `MB-114` fecharam o lote minimo para contratos, runtime, memoria, observabilidade e fechamento documental de projetos, objetivos, work items, checkpoints e artefatos vivos, sem autoexecucao longa.
- `verify_active_cut_baseline.py` agora combina contratos promovidos com um piloto focado que cobre as seis rotas promovidas, seus `workflow_profiles` e os sinais deliberados de memoria causal e recomposicao cognitiva.
- `internal_pilot_support` agora declara `expected_route`, `expected_workflow_profile` e `coverage_tags` nos cenarios canonicos do piloto, tornando a cobertura por rota/workflow parte explicita do baseline ativo.
- o baseline ativo agora tambem exige cenarios deliberados para `dominant_tension` e alinhamento `mente -> dominio -> especialista`, deixando esses sinais como readiness formal de robustez do `v2`.
- `close_domain_consumers_and_workflows_cut` agora carrega coverage de piloto, match de workflow e readiness dos sinais deliberados como parte da evidencia regeneravel do corte.
- a leitura executiva do corte em `master-summary` e no closure doc arquivado agora tambem reflete que o baseline combina contratos promovidos com cobertura deliberada do piloto.
- o caminho padrao do `orchestrator-service` agora tambem fecha a continuidade como subfluxo explicito via `continuity_subflow_completed`, alinhado ao mesmo payload soberano usado pelo caminho opcional de `LangGraph`.
- o lote `pre-v3 hardening` foi concluido no `execution-backlog`; `MB-023` a `MB-026` fecharam continuidade stateful nativa, specialist subflow explicito, `mission_runtime_state` e leitura agregada desses sinais no baseline.
- `observability-service`, `internal_pilot_report`, `compare_orchestrator_paths`, `verify_active_cut_baseline.py` e o fechamento regeneravel do corte agora tratam `specialist_subflow` e `mission_runtime_state` como readiness arquitetural pre-`v3`, e nao apenas telemetria localizada.
- `pre-v3 protective intelligence foundation` foi mapeada e preservada como frente futura candidata, mas deixou de ser a proxima frente ativa;
- o `execution-backlog` foi recentrado no nucleo cognitivo: `MB-027` a `MB-031` passaram para `deferred`, e o novo lote ativo volta a priorizar metacognicao, memoria causal/lifecycle e a relacao `mente -> dominio -> especialista`;
- dentro desse lote, `MB-032` a `MB-036` ja foram fechados; memoria causal/lifecycle, cadeia `mente -> dominio -> especialista` e readiness de evolucao/release agora entram como baseline do nucleo, e nao mais como pendencia do lote atual;
- `memory_registry`, `memory-service`, `planning`, `synthesis` e `observability` agora distinguem fonte, efeitos, lifecycle e revisao de `semantic`/`procedural` por `workflow_profile` e por fonte de continuidade, separando reasoning final, packet de especialista e recovery de missao;
- `orchestrator-service`, `observability-service`, `internal_pilot_report` e `compare_orchestrator_paths` agora tratam `mind_domain_specialist_chain_*`, `primary_mind` e `primary_route` como evidencia primaria do runtime e do piloto, em vez de depender de leitura posterior de `rationale`;
- `evolution_from_pilot`, `evolution-lab`, `compare_orchestrator_paths`, `internal_pilot_report` e `verify_release_signal_baseline.py` agora promovem metacognicao causal, lifecycle de memoria e coerencia `mente -> dominio -> especialista` a sinais formais de evolucao governada e readiness de release;
- `compare_orchestrator_paths`, `evolution-lab` e `evolution_from_pilot` agora publicam `refinement_vectors` por workflow, transformando sinais do nucleo em leitura priorizada de refinamento e nao apenas em relatorio de estado;
- `planning`, `synthesis`, `orchestrator` e `observability` agora tratam discordancia entre mentes como restricao, checkpoint governado e leitura auditavel quando o workflow exige profundidade cognitiva maior;
- `memory-service`, `memory_registry`, `observability` e o piloto agora publicam `memory_corpus_status`, `memory_retention_pressure` e resumo do corpus por classe, tornando o lifecycle de memoria observavel tambem no nivel de corpus;
- `verify_active_cut_baseline.py`, `verify_release_signal_baseline.py` e `programa-de-excelencia.md` agora materializam uma matriz formal por eixo/workflow sobre esse baseline mais maduro;
- a fila micro ja fechou o lote seguinte do nucleo: `MB-037` a `MB-040` foram concluidos e agora deixam vetores priorizados de refinamento, composicao de mentes mais profunda, telemetria viva de memoria e matriz formal de evals como baseline operacional do ciclo;
- memoria, identidade, governanca, observabilidade e soberania do nucleo evoluiram de forma consistente;
- benchmark externo, memory gap e hardening nativo foram tratados corretamente como etapas subordinadas ao baseline,
  nao como desvio de direcao.
- os documentos vivos que orientam historico, retomada e direcao do projeto passaram a ter guardrail explicito no gate, reduzindo risco de perda semantica por edicao acidental.
- o estudo tecnologico agora ganhou ordem oficial de absorcao, separando melhor traducao imediata de padroes, complementos controlados e horizonte de pesquisa.
- o backlog correto passou a tratar absorcao tecnologica como traducao disciplinada de primitives para o nucleo, e nao como adocao direta de frameworks externos.
- `MB-041` ja materializou o primeiro recorte dessa traducao: `DeliberativePlanContract` agora passa por validacao canonica com repair pequeno e auditavel, a `synthesis` valida o output minimo e `observability` diferencia falha de contrato, falha de output e saida coerente sem trocar a gramatica do runtime.
- `MB-042` ja materializou o segundo recorte dessa traducao: `memory_registry`, `memory-service`, `orchestrator`, `planning` e `synthesis` agora tratam contexto vivo compactado e recall cross-session como politica soberana do baseline, distinguindo memoria viva de contexto descartavel sem reabrir historico bruto.
- `MB-043` ja materializou o terceiro recorte dessa traducao: `memory_registry`, `memory-service`, `repository`, `planning`, `orchestrator` e `observability` agora distinguem memoria guiada operacional, fixada e arquivavel, com sinais explicitos de consolidacao, fixacao e arquivamento sem quebrar a ontologia canonica.
- `MB-044` ja materializou o quarto recorte dessa traducao: `orchestrator`, `langgraph_flow`, `operational-service` e `observability` agora tratam checkpoint, retomada, ponto de resume e checkpoints pendentes como sinais soberanos de continuidade stateful.
- `MB-045` ja materializou o quinto recorte dessa traducao: `memory-service`, `repository`, `planning`, `synthesis` e `orchestrator` agora carregam artefatos procedurais versionados e reutilizaveis, sempre `through_core_only`, como primitive governada do runtime.
- `MB-046` ja materializou o sexto recorte dessa traducao: `evolution-lab`, comparadores, piloto e verificadores de release agora persistem candidatos, vetores de refinamento, matriz de avaliacao, criterios de selecao e deltas metricos como baseline da Onda 1.
- `MB-047` ja materializou o proximo passo do nucleo: `synthesis`, `response_synthesized` e `observability` agora distinguem output coerente, output parcial e output desalinhado por `workflow_profile`, tornando o contrato de workflow criterio auditavel de saida na ultima milha do runtime.
- `MB-048` agora tambem esta fechado: `memory_registry`, `planning` e `synthesis` passaram a distinguir melhor os efeitos de `semantic` e `procedural` por workflow e por fonte de continuidade, fazendo memoria causal pesar em prioridade, profundidade e recomendacao final.
- `MB-049` agora tambem esta fechado: `orchestrator`, `synthesis`, comparadores e laboratorio tratam a cadeia `mente -> dominio -> especialista` como evidencia primaria mais rica, inclusive com planned hints, alinhamento parcial e coerencia do encadeamento no runtime final.
- `MB-050` e `MB-051` agora tambem estao fechados: `workflow_output_status` atravessa piloto, comparadores, `evolution-lab`, `evolution_from_pilot` e `verify_release_signal_baseline.py` como leitura formal de maturacao, e os proximos experimentos do laboratorio passam a ser priorizados por workflow usando esses sinais mais causais do nucleo.
- `MB-052` agora tambem esta fechado: `planning-engine` aplica mudanca de estrategia cognitiva mid-flow no `refine_task_plan` quando a revisao especializada preserva um impasse governado, `synthesis-engine` torna esse ajuste explicito na leitura final, `orchestrator-service` o publica em `plan_refined` e `response_synthesized`, e `observability-service` audita a coerencia desse slice ao longo do fluxo.
- `MB-053` agora tambem esta fechado: `memory_registry`, `memory-service`, `repository` e `observability-service` passaram a conter reuso automatico de memoria arquivavel, fazer recovery marcar `review_before_reuse` quando o lifecycle exige revisao e tratar drift de packet guiado arquivavel como desalinhamento auditavel.
- `MB-057` a `MB-061` agora estao fechados: o runtime usa `adaptive_intervention_*` como contrato soberano de checkpoint/contencao bounded, a observabilidade distingue intervencao efetiva de insuficiente, e piloto/comparadores/evolucao passaram a tratar esse slice como evidência formal do baseline.
- `MB-062` agora tambem esta fechado: `workflow_runtime_guidance` passou a governar a prioridade soberana entre `memory_review_checkpoint` e `specialist_reevaluation`, fazendo o `planning-engine` responder ao `workflow_profile` ativo quando esses sinais competem no mesmo request.
- `MB-063` agora tambem esta fechado: `observability-service`, piloto, comparadores e leitura de release agora expoem `adaptive_intervention_policy_status`, distinguindo `policy_aligned`, `mandatory_override` e `attention_required` como evidencia auditavel do baseline por workflow.
- `MB-064` e `MB-065` agora tambem estao fechados: a sintese final e o `response_synthesized` tornaram explicita a prioridade do workflow com checkpoint/gate preservado, e `evolution-lab`, `evolution_from_pilot.py` e `compare_orchestrator_paths.py` passaram a tratar fechamento insuficiente dessa politica como `review_recommended` por workflow.

Em resumo:

- a visao esta preservada;
- o runtime esta coerente com a fase do programa;
- `EV-003` agora tambem faz parte do baseline: compile/optimize loops
  governados para prompts, planos e workflows passaram a existir como
  gramatica soberana do runtime evolutivo, sem autoedicao do nucleo;
- a proxima repriorizacao explicita abriu a ponte `v2 -> v3` em cima de
  `SG-002` + `TA-002`, mas de forma bounded: o lote novo ataca apenas estado
  operacional minimo do ecossistema, sem abrir ainda memoria temporal rica,
  multissuperficie ou substrate operacional amplo.

---

## 3. Leitura por eixo

### 3.1 Nucleo central e fluxo principal

**Status:** `runtime parcial` - forte, sem divergencia material

O que esta aderente:

- o orquestrador permanece como autoridade suprema da relacao com o usuario;
- governanca, memoria, conhecimento, cognicao, especialistas, operacao e observabilidade
  continuam subordinados ao nucleo;
- LangGraph segue complementar e opcional, nao substituto do runtime principal.

Gap relevante:

- nenhum gap estrutural critico neste eixo.

Leitura:

- este eixo esta alinhado com a visao do mestre.

---

### 3.2 Identidade, missao e principios

**Status:** `runtime parcial` - consistente, com gate real

O que esta aderente:

- identidade entra no fluxo real;
- governanca ja audita coerencia de identidade;
- observabilidade ja trata alinhamento identitario como sinal de eixo.

Gap relevante:

- identidade ainda e mais forte como guardrail e trilha auditavel do que como checklist declarativo completo por request.

Leitura:

- nao ha divergencia de direcao; ha maturacao pendente.

---

### 3.3 Mentes canonicas

**Status:** `runtime parcial` - registry forte, arbitragem ainda hibrida

O que esta aderente:

- o projeto preserva a ontologia das 24 mentes;
- o registry de mentes existe e ja influencia composicao, suporte e tensao dominante;
- o eixo nao foi abandonado nem substituido por heuristica puramente solta.

Gap relevante:

- a arbitragem principal ja foi puxada para helpers soberanos do `mind_registry`, reduzindo regra espalhada no engine;
- a relacao entre mente, dominio e especialista agora ja atravessa runtime, piloto, comparadores e release signals como evidencia primaria;
- o que resta aqui ja e profundidade futura de uso causal desses sinais em consumidores posteriores, nao falta de materializacao basica.

Leitura:

- a visao foi respeitada, mas a materializacao ainda esta incompleta.

---

### 3.4 Dominios canonicos e rotas de runtime

**Status:** `runtime parcial` - principal gap funcional restante

O que esta aderente:

- o sistema ja possui registry canonico de dominios;
- a separacao entre ontologia canonica e rotas operacionais de runtime esta estabelecida;
- existem rotas promovidas, contratos de consumo por dominio, workflows e vinculos com especialistas;
- o `knowledge-service` agora da precedencia explicita a mencoes declaradas de rota runtime
  e dominio canonico do registry, com matching normalizado sem depender de acento.

Gap relevante:

- o `domain_registry` agora governa tambem o contrato soberano da rota primaria em `planning`, `memory`, `specialist`, `orchestrator` e observabilidade;
- `primary_route`, `primary_canonical_domain`, `consumer_objective`, `expected_deliverables`, `telemetry_focus` e `workflow_profile` ja atravessam o runtime sem recomposicao heuristica relevante fora do registry;
- `workflow_profile` agora também governa guidance soberano de planejamento e síntese, incluindo foco de sucesso, leitura final e checkpoint/gate dominante por rota promovida;
- o que sobra neste eixo ja e refinamento fino ou expansao futura para novas rotas, nao correcao de baseline.

Leitura:

- este continua sendo o eixo mais importante para o proximo recorte funcional,
  mas o primeiro endurecimento ja entrou no baseline.

---

### 3.5 Memorias canonicas

**Status:** `runtime parcial` - avancou bastante, sem divergencia de visao

O que esta aderente:

- o sistema mantem a ideia de memoria estratificada e soberana;
- user scope nativo foi endurecido;
- recorrencia soberana de especialistas promovidos foi implementada ainda `through_core_only`;
- organization scope ficou corretamente bloqueado sem consumidor canonico soberano;
- benchmark e evidencia local evitaram reabrir absorcao externa por conveniencia.

Gap relevante:

- `semantic` e `procedural` agora entram como `runtime_partial` em packets guiados por dominio quando existe evidencia persistida e compatibilidade canonica;
- o runtime final ja usa essas classes de forma mais explicita por `workflow_profile`, e a camada de especialista passou a receber `procedural` apenas quando a politica soberana da rota realmente exige isso.
- a politica que libera essas classes saiu de decisao espalhada no servi?o e passou a viver mais explicitamente no `memory_registry`;
- `planning` e `synthesis` ja usam esse apoio sem bypassar governanca, inclusive quando o hint nasce do recovery soberano da propria missao e nao apenas de handoff especializado, enquanto especialistas continuam presos ao contrato elegivel da rota promovida;
- esse uso deixou de ser apenas ornamental: o `planning` agora prioriza passos guiados de framing/continuidade e a `smallest_safe_next_action` preserva o fio procedural quando a rota ativa depende dele, enquanto a `synthesis` ancora o framing final e cobra continuidade explicita da proxima acao;
- o baseline agora tambem distingue fonte, efeitos, lifecycle e revisao de `semantic`/`procedural`, deixando consolidacao, promocao, retencao e review como sinais soberanos do runtime e da observabilidade;
- a camada multicamada nativa ainda pode crescer antes de qualquer absorcao futura, mas isso ja e maturacao incremental, nao correcao urgente.

Leitura:

- este eixo esta consistente com a visao e com a fase atual.

---

### 3.6 Governanca, seguranca e autonomia

**Status:** `runtime parcial` - forte

O que esta aderente:

- o sistema preserva governanca como camada real, nao decorativa;
- decisoes de risco, bloqueio, deferimento e condicoes continuam no fluxo principal;
- a evolucao externa e os benchmarks continuam subordinados ao baseline soberano.

Gap relevante:

- ainda existe espaco para formalizar melhor governanca de memoria e politicas declarativas mais completas.

Leitura:

- sem divergencia material neste eixo.

---

### 3.7 Especialistas subordinados

**Status:** `runtime parcial` - malha promovida fechada, expansao futura pendente

O que esta aderente:

- especialistas continuam subordinados ao nucleo;
- nao existe concessao de identidade propria a especialistas;
- handoffs continuam `through_core_only` e `advisory_only` quando aplicavel;
- memoria compartilhada e recorrencia foram mantidas como mediacao do nucleo.

Gap relevante:

- hints, selecao, handoff e conclusao de especialistas promovidos agora dependem de rota canonica ativa, `linked_specialist_type`, `specialist_mode`, memoria guiada coerente e alinhamento com `primary_route` e `primary_canonical_domain`;
- a observabilidade passou a usar esses sinais diretamente para marcar `attention_required` quando houver drift;
- o que resta neste eixo e ampliar a mesma disciplina para expansoes futuras e formalizar melhor evolucoes alem do nivel promovido atual.

Leitura:

- o eixo esta na direcao certa, mas ainda nao atingiu a forma plena do mestre.

---

### 3.8 Observabilidade e evidencia

**Status:** `runtime parcial` - solido

O que esta aderente:

- o projeto ja opera com trilha auditavel, comparadores, baseline verification e engineering gate;
- decisoes de benchmark, closure de cuts e baseline release-grade ja entram como evidencia regeneravel.

Gap relevante:

- ainda cabe reduzir carga documental sem perder auditabilidade;
- parte dos sinais pode ficar mais consolidada por eixo ao longo dos proximos cortes.

Leitura:

- eixo consistente com a visao.

---

### 3.9 Evolucao, benchmark e absorcao externa

**Status:** `deferido por fase` - correto

O que esta aderente:

- benchmark governado foi usado como filtro de decisao, nao como atalho de arquitetura;
- `Mastra` e `AutoGPT Platform` ficaram como referencia;
- `Mem0` ficou em `absorver_depois` e depois foi mantido fechado por evidencia local insuficiente;
- nada externo assumiu o papel de cerebro do sistema.

Leitura:

- este eixo esta alinhado com a visao e com a sua direcao explicita para o projeto.

---

### 3.10 Voz, realtime e superficies amplas

**Status:** `deferido por fase` - correto

Leitura:

- continuam parte da visao, mas fora do caminho critico do `v2`.

---

## 4. Tabela consolidada

| Eixo | Status | Leitura atual | Prioridade |
|---|---|---|---|
| Nucleo / Orquestrador | runtime parcial | forte, sem gap material | baixa |
| Identidade | runtime parcial | operacional e auditavel | baixa |
| Mentes | runtime parcial | arbitragem forte, mas ainda pouco causal em consumidores finais | alta |
| Dominios | runtime parcial | contrato soberano ja atravessa o runtime promovido | media |
| Memorias | runtime parcial | eixo fortalecido, mas lifecycle e causalidade ainda pedem profundidade | alta |
| Governanca | runtime parcial | solida | baixa |
| Especialistas | runtime parcial | malha promovida fechada e auditavel | media |
| Observabilidade | runtime parcial | forte | baixa |
| Evolucao / Benchmark | deferido por fase | corretamente subordinado, mas pronto para amadurecer com sinais do nucleo | media |
| Voz / Realtime | deferido por fase | corretamente adiado | nao aplicavel |

---

## 5. Proxima sequencia correta de implementacao

Com base no estado atual do repositorio, a sequencia mais coerente agora nao e
continuar puxando lotes ja encerrados. Ela e usar o baseline fechado como
plataforma para repriorizacao explicita do que ainda falta:

### Passo 1 - preservar `MB-037` a `MB-066` como baseline fechado

Foco:

- nao reabrir Onda 1, maturacao causal, maturacao adaptativa ou politica
  soberana por workflow por inercia local;
- tratar gate, snapshot, comparadores e docs vivos atuais como baseline valido.

### Passo 2 - usar `docs/implementation/unified-gap-and-absorption-backlog.md` como mapa macro do que ainda falta

Foco:

- separar `system gaps`, `technology absorption`, `surfaces/operation`,
  `evolution/benchmark`, `deferred verticals` e `research horizon`;
- ligar cada lacuna a fase, tecnologias relacionadas, janela de absorcao e
  possibilidade de slice micro.

### Passo 3 - executar o novo lote micro a partir do eixo priorizado

Foco:

- o eixo escolhido para a nova fila micro foi `SG-001`, reforcado por
  `TA-001` e `TA-005`, por ser hoje o melhor ganho de profundidade do nucleo no
  `v2 restante`;
- esse eixo agora foi fechado como lote `MB-067` a `MB-071`, formalizando e
  aplicando decisao soberana de capacidades, ferramentas e handoffs bounded por
  request, com evidencia auditavel e uso evolutivo coerente no baseline.

### Passo 4 - tratar a arbitragem declarativa como baseline fechado

Foco:

- a prioridade micro `SG-005` foi integralmente fechada como lote `MB-077` a
  `MB-081`, concluindo contrato, consumo final, evidencia auditavel, uso
  evolutivo e fechamento documental da arbitragem declarativa;
- `evolution-lab`, `evolution_from_pilot`, comparadores e verificadores de
  release agora tratam efetividade e mismatch da arbitragem `mente -> dominio
  -> especialista` como insumo formal de `refinement_vectors`,
  `evaluation_matrix` e leitura de release;
- o lote `MB-082` a `MB-086` foi fechado e o lote `MB-087` a `MB-091` tambem ja
  foi absorvido como baseline comparativo controlado para evals expandidas e
  lane da Onda 2;
- a fila micro voltou a ficar sem item `ready`, e a proxima puxada correta
  agora exige repriorizacao explicita a partir do backlog macro.

### Passo 5 - manter frentes fora da fila micro ate mudanca explicita de fase

Foco:

- `protective intelligence` continua `deferred`;
- `voice/realtime`, `OpenClaw`, `Manus`, `Graphiti`, `Zep`, `Mem0` forte e
  auto-modificacao continuam bloqueados por fase ou em pesquisa.

---

## 6. O que nao deve ser reaberto sem evidencia forte

- JARVIS como sistema unificado, nao chatbot simples;
- soberania do nucleo na relacao com o usuario;
- especialistas subordinados, nao identidades paralelas;
- governanca, memoria canonica e sintese final nao externalizadas;
- benchmark externo como apoio ou filtro, nao como substituto do nucleo;
- organization scope bloqueado sem consumidor canonico soberano;
- `Mem0` sem promocao automatica;
- voz, realtime e superficies amplas fora do caminho critico do `v2`.

---

## 7. Conclusao

A leitura correta hoje e:

- o repositorio nao esta divergindo da visao do Documento-Mestre;
- tambem nao esta divergindo da sua direcao macro ja formalizada nos artefatos do projeto;
- o que existe e um conjunto de gaps de materializacao normais para a fase do `v2`.

A divergencia relevante, neste momento, nao e mais de robustez do `v2`.
O que resta e maturacao adicional em tres pontos:

- criterios mais especificos por `workflow_profile` no runtime final;
- uso mais rico de memoria `semantic` e `procedural` sem perder soberania;
- relacao mente -> dominio -> especialista ainda mais explicita em consumidores posteriores.

O lote `MB-057` a `MB-061` foi fechado exatamente para atacar esses tres pontos sem abrir nova vertical: ele transforma sinais causais ja presentes do nucleo em intervencoes adaptativas bounded, auditaveis e priorizaveis pelo loop evolutivo. O lote seguinte tambem ja foi fechado: `MB-062` moveu a prioridade entre revisao de memoria e reavaliacao especializada para o `workflow_profile` soberano, `MB-063` tornou essa politica evidencia auditavel do baseline, `MB-064` a expôs na ultima milha da sintese, `MB-065` a promoveu a criterio evolutivo formal e `MB-066` sincronizou o estado vivo do projeto.

`Protective intelligence` continua como eixo valido e estudado, mas em estado
`deferred` ate que esse lote de maturacao do nucleo seja realmente fechado.

O que resta agora continua melhor descrito como backlog macro de lacunas reais
e traducao tecnologica disciplinada. A ponte minima de continuidade
multissuperficie ja foi fechada no lote `MB-102` a `MB-106`, a repriorizacao
`MB-107` a `MB-109` escolheu `SO-003` em recorte minimo e o lote `MB-110` a
`MB-114` criou a fundacao de projetos/objetivos persistentes, preservando
superficies amplas, voz, web, API publica, memoria temporal rica,
autoexecucao longa e substrate operacional amplo fora de fase.

---

## 8. Referencias

- [documento_mestre_jarvis.md](../../documento_mestre_jarvis.md)
- [HANDOFF.md](../../HANDOFF.md)
- [matriz-de-aderencia-mestre.md](../documentation/matriz-de-aderencia-mestre.md)
- [unified-gap-and-absorption-backlog.md](./unified-gap-and-absorption-backlog.md)
- [v2-native-memory-scope-hardening-cut-closure.md](./v2-native-memory-scope-hardening-cut-closure.md)
- [v2-repository-hygiene-and-tools-review-cut.md](./v2-repository-hygiene-and-tools-review-cut.md)
- [v2-repository-hygiene-and-tools-review-cut-closure.md](./v2-repository-hygiene-and-tools-review-cut-closure.md)
- [programa-ate-v3.md](../roadmap/programa-ate-v3.md)
- [technology-study.md](../architecture/technology-study.md)
