# HANDOFF

## Atualizacao 2026-07-16

`MB-184` foi concluido como integracao da candidata de workflow ao promotion
gate e rollback manual. A versao candidata recebe proposta e review proprios,
separados da revisao do pattern. `WorkflowRollbackPlanContract` registra
baseline, candidata, triggers, procedimento, testes, evidencia e operador com
`execution_mode=manual_only`. O checklist exige identidade/versao coerentes,
eval MB-183 aprovado, rollback verificado, engineering gate e release gate. O
E2E comprova que a cadeia completa termina em
`release_gate_passed_pending_human_decision`; regressao ou rollback ausente
bloqueiam. Candidata permanece inativa, registry ativo inalterado e
`promotion_authorized=false`. `MB-185` e o unico item tecnico `ready`.

`MB-183` foi concluido como eval offline equivalente de workflow baseline vs
candidata. Os contratos `WorkflowVariantEval*` registram casos, checks,
metricas, deltas, melhorias, regressoes e run agregada. O `evolution-lab`
valida as definicoes versionadas e as dimensoes `success_score`,
`contract_adherence`, `rework_rate`, `checkpoint_coverage` e
`memory_causality`; o `observability-service` agrega a conclusao e
`tools/workflow_variant_eval.py` exige candidata registrada e inativa no
side-registry atual. Qualquer regressao falha a run. Mesmo verde, o resultado e
`manual_gate_only`, com `promotion_authorized=false` e registry ativo
inalterado. Esse estado foi sucedido pelo fechamento de `MB-184`.

`MB-182` foi concluido como builder governado de candidata de workflow.
`WorkflowEvolutionRequestContract` declara delta explicito de passos,
checkpoints, decision points e criterios, alem de evidencia, testes, risco e
rollback; `WorkflowEvolutionBuildResultContract` retorna candidata somente
quando nao ha blockers. O `evolution-lab` persiste a proposta do pattern e
confere a decisao humana contra a ultima revisao gravada antes de construir a
variante. O E2E parte de experiencias/reflexoes reais na memoria, gera pattern,
revisa, constroi e registra somente candidata `candidate_inactive/needs_review`
no side-registry, mantendo o registry ativo inalterado. Review forjado, delta
invalido e claims de autoridade falham fechados. Esse estado foi sucedido pelo
fechamento de `MB-183`.

`MB-181` foi concluido como registry versionado de `workflow_profile` ao lado
do registry ativo soberano. `WorkflowProfileVersionContract` e
`WorkflowProfileVersionRegistryContract` registram semver, fingerprint,
passos, checkpoints, decision points, criterios, evidencias, testes e rollback.
`shared/domain_registry.py` gera baselines deterministicas para todas as rotas
ativas e aceita candidata somente em novo snapshot imutavel, com versao
posterior, definicao distinta, baseline/fingerprint coerentes, risco bounded e
sem claims de escrita ou ativacao. O `evolution-lab` apenas delega essas
operacoes. Testes comprovam idempotencia, colisao/drift contidos e payload do
registry ativo inalterado. Esse estado foi sucedido pelo fechamento de
`MB-182`.

`MB-180` foi concluido como superficie read-only da evolucao de skills. Os
novos `SkillEvolutionOperatorItemContract` e
`SkillEvolutionOperatorViewContract` correlacionam pattern evidence,
candidata inativa, proposta, review humano e sandbox no
`observability-service`; `jarvis-console skill-evolution` mostra origem,
recorrencia, escopo, risco, versao, tools, evidencias, testes, rollback,
blockers e proxima acao humana com filtros bounded e sanitizacao. O E2E
comprova a cadeia persistida e que a consulta nao altera candidata nem
propostas. Ativacao runtime, autorizacao de promocao, autopromocao e mutacao do
Core permanecem falsas. Esse estado foi sucedido pelo fechamento de `MB-181`.

`MB-179` foi concluido como cadeia governada de review e sandbox para skill
candidata. `create_proposal_from_skill_candidate` persiste identidade, versao,
escopo, risco, evidencias, testes e rollback sem ativar runtime; review humano
carrega skill/version; `SkillSandboxEvalContract` deriva pass/fail de checks e
mescla o resultado sobre a proposta mais recente sem perder o historico de
review. O checklist exige o gate intrinseco `skill_sandbox_eval` e bloqueia
ausencia, falha ou mismatch. Mesmo a cadeia totalmente verde termina em
`release_gate_passed_pending_human_decision`, com `promotion_authorized=false`
e candidata inativa. Esse estado foi sucedido pelo fechamento de `MB-180`.

`MB-178` foi concluido como Skill Miner bounded. Os novos
`SkillMiningRequestContract` e `SkillMiningResultContract` separam spec
explicita, eligibility e candidata. O `evolution-lab` exige pattern elegivel,
threshold de ocorrencias/outcomes, experiencias e reflexoes distintas,
confidence bounded, evidencia, ausencia de conflitos, interface completa,
tools explicitas e risco no maximo moderado. Qualquer insuficiencia retorna
`blocked` com `candidate=None`; sucesso produz somente candidata
`candidate_inactive/needs_review/inactive`, com identidade deterministica e
registro idempotente. Esse estado foi sucedido pelo fechamento de `MB-179`.

`MB-177` foi concluido como registry canonico de skills candidatas. O novo
`SkillCandidateContract` formaliza identidade logica, semver, workflow,
dominio, especialista subordinado, inputs, outputs, instrucoes bounded, tools,
risco, evidencias, pattern refs, failure modes, testes e rollback. O
`memory-service` persiste o registry em SQLite/PostgreSQL com unicidade
`(skill_id, version)`: retry identico e idempotente, mas mutacao ou colisao de
versao e rejeitada. Toda entrada permanece `candidate_inactive`,
`needs_review`, `inactive`, sandbox-required e sem ativacao, promocao ou Core
mutation automaticas. Esse estado foi sucedido pelo fechamento de `MB-178`.

`MB-176` foi concluido como baseline bounded de pattern evidence. Os novos
`RecurringPatternEvidenceContract` e `RecurringPatternReportContract` agregam
experiencias, reflexoes e feedbacks por workflow, rota e dominio, exigem duas
ocorrencias distintas e expoem outcomes, evidence refs, sinais recorrentes,
confidence, conflitos e blockers. Memoria e observabilidade usam o mesmo
agregador deterministico read-only; amostra insuficiente ou outcomes mistos nao
viram evidencia elegivel. Criacao de skill, promocao automatica e mutacao do
Core permanecem explicitamente falsas. Esse estado foi sucedido pelo
fechamento de `MB-177`.

`MB-175` foi concluido como repriorizacao explicita pos-`MB-174`. A fila
`MB-176` a `MB-189` cobre pattern evidence, skill registry e miner,
review/sandbox, workflow evolution, routing, politica de memoria e metricas
longitudinais. `MB-176` foi sucedido pelo baseline descrito acima; toda
skill/workflow continua nascendo inativa, revisavel e sem promocao automatica
ou mutacao do Core.

`MB-174` foi concluido: `CapabilityReadinessContract` e
`RegressionReadinessReportContract` agora consolidam maturidade por capacidade,
gate/testes, guardrails documentais, backlog e status drift em leitura
read-only. `tools/readiness_dashboard.py` pode atualizar o gate somente por
flag explicita e salva evidencia historica em `.jarvis_runtime/readiness/`; o
console expoe a mesma leitura por `readiness-dashboard`. Capacidades deferred
nao viram falsos blockers e nenhum status autoriza release autonomo. A fila
`MB-161` a `MB-174` esta fechada. Esse estado foi sucedido por `MB-175` e pelo
fechamento de `MB-176` a `MB-184`; `MB-185` e agora o unico item tecnico
`ready`.

`MB-173` foi concluido: `KnowledgeSourceEvidenceContract` e
`KnowledgeEvidenceGovernanceContract` agora carregam proveniencia, freshness,
conflito, incerteza e modo governado de uso desde o `knowledge-service` ate a
sintese e os eventos. O corpus v1 foi identificado como `curated_internal`, com
janela de revisao explicita; corpus sem metadata permanece `missing/unknown` e
exige revisao, sem alterar a permissao principal da request. A sintese mostra
uma clausula `Conhecimento:` e a trilha completa fica em
`knowledge_retrieved`/`response_synthesized`. Resolucao automatica de conflitos
e ingestao externa continuam fora do baseline. `MB-174` e o unico item tecnico
`ready` naquele momento. Esse estado foi sucedido pelo fechamento de `MB-174`.

`MB-172` foi concluido: contratos compartilhados agora formalizam eval case,
pack versionado, resultado por caso e run agregado. O novo runner offline usa
o Core real e o `observability-service` para validar decisao, rota, dominios,
workflow, especialista, resposta, memoria causal, eventos e trace. O pack
baseline de `analysis` passa abertura e follow-up com `pass_rate=1.0`; o segundo
caso comprova `causal_guidance`. Mesmo verde, o resultado permanece
`candidate_ready_for_human_review`, `manual_review_only` e
`promotion_authorized=false`. Esse estado foi sucedido pelo fechamento de
`MB-173`.

`MB-171` foi concluido: `DomainKnowledgePackContract`,
`DomainOnboardingCandidateContract` e `DomainOnboardingAssessmentContract`
formalizam entrada de novos dominios como candidatura governada. O novo
`shared/domain_onboarding.py` valida dominio canonico, rota unica, knowledge
pack versionado, workflow, testes, eval, rollback e fronteira de especialista;
`knowledge-service` avalia o manifest baseline sem escrever nos registries.
Mesmo um candidato coerente termina apenas em `ready_for_human_review`, com
ativacao, promocao de especialista, autopromocao e mutacao do Core bloqueadas.
Esse estado foi sucedido pelo fechamento de `MB-172`.

`MB-170` foi concluido: `OperatorFeedbackContract`, schema e evento
`operator_feedback_recorded` agora formalizam feedback explicito do operador
apos uma missao. `governance-service` valida experiencia/reflexao, assessment,
rating, refs e limites; `memory-service` anexa o sinal ao par canonico;
`evolution-lab` cria proposta `operator_feedback_improvement` sandbox-only; e
`mission-feedback` expoe o fluxo no console. Toda proposta permanece
`needs_review`, com autopromocao e mutacao do Core bloqueadas. Esse estado foi
sucedido pelo fechamento de `MB-171`.

`MB-166` foi concluido: `SandboxToReleaseChecklistContract`, schema canonico e
`evolution-lab` agora produzem um checklist sandbox-to-release com escopo,
revisao humana, evidencias, testes, rollback, gates obrigatorios e blockers. O
checklist rejeita revisao ligada a outra proposta e preserva
`automatic_promotion_allowed=false` e `core_mutation_allowed=false`.

`ready_for_release_review` significa somente que o checklist esta completo;
promocao continua condicionada a decisao humana e release gate separado.

`MB-167` foi concluido: `PromotionGateDecisionContract`, schema e evento
`promotion_gate_evaluated` agora tornam o checklist verificavel por runtime e
release tooling. O evaluator valida gates intrinsecos pela evidencia real,
aceita apenas gates externos conhecidos, bloqueia qualquer ausencia e produz
status, decisao, blockers, evidencias e conclusao de release observaveis.
Mesmo quando o gate passa, a conclusao e
`release_gate_passed_pending_human_decision`, com
`promotion_authorized=false`.

`MB-168` foi concluido: `operator-dashboard` agora consolida objetivo, proxima
acao, work items, checkpoints, artefatos, experiencia/reflexao, revisoes,
memoria usada, autonomia e promotion gate. A fila read-only
`pending_decisions` ordena revisao evolutiva, blockers de release, confirmacao
de autonomia e checkpoints; `next_operator_decision` aponta a primeira decisao
humana sem executa-la.

`MB-169` foi concluido: `MissionProgressReportContract`, `synthesis-engine`,
orquestrador, observabilidade e o comando `progress-report` agora geram uma
leitura humana compacta de progresso, pendencias, riscos, artefatos, memoria
influente, experiencia/reflexao, estrategia e proxima acao. O relatorio deriva
do estado canonico, emite `mission_progress_report_generated` e preserva
`memory_write_mode=read_only` e `autonomous_execution_allowed=false`.
Esse estado foi sucedido pelos fechamentos de `MB-170` a `MB-174`; a fila
tecnica posterior esta esgotada e aguarda repriorizacao.

## Atualizacao 2026-07-04

`MB-163` foi concluido: `observability-service` agora consolida
`memory_influence_used_refs`, `memory_influence_ignored_refs`,
`memory_influence_reasons` e `memory_influence_evidence_refs` a partir dos
sinais semanticos/procedurais ja existentes. O console
`operator-dashboard` mostra esses campos em modo read-only para o operador
auditar o que influenciou a missao, o que foi ignorado e quais evidencias
sustentam a leitura. Nao houve escrita de memoria, promocao de playbook ou
alteracao de decisao final.

`MB-164` foi concluido: `AutonomyLadderContract`, schema e evento
`autonomy_ladder_declared` agora formalizam requested/max/effective autonomy
level, downgrade por limite, confirmacao humana, acoes permitidas/bloqueadas e
bloqueio explicito de autopromocao/core mutation. O contrato atravessa
`InputContract`, plano, governanca, dispatch e eventos do orquestrador, mas
ainda nao aplica enforcement amplo.

`MB-165` foi concluido: governanca agora bloqueia claims proibidos de autonomia
e defere capability acima de `max_autonomy_capability_mode`; `operational-service`
falha dispatch acima do limite sem gerar artefato; observabilidade e
`operator-dashboard` mostram nivel efetivo, status do ladder, limite aplicado,
confirmacao humana e acoes bloqueadas.

`MB-166`, `MB-167`, `MB-168`, `MB-169` e `MB-170` foram posteriormente
concluidos na atualizacao de `2026-07-16`; `MB-171` passou a ser o unico item
tecnico `ready`.

## Atualizacao 2026-05-17

O corte pos-`MB-131` foi repriorizado em `MB-132`: a proxima frente ativa e o
baseline do `Operator Learning Loop`. O objetivo e fechar o ciclo real
`usar -> registrar -> refletir -> propor -> revisar -> medir`, partindo de
missoes governadas do operador, sem abrir produto multicanal, voz, realtime,
browser/computer use amplo, scheduler autonomo, autopromocao ou self-modification.

`MB-133` foi concluido: o fluxo normal do `orchestrator-service` agora gera
automaticamente `experience_record` recuperavel em memoria evolutiva bounded,
com rota, workflow, mente primaria, dominio primario, especialista usado,
resumo de plano, resumo de execucao, outcome, sinais, checkpoints e evidencia.

`MB-134` tambem foi concluido: toda experiencia gerada pelo fluxo normal agora
gera `post_task_reflection` bounded, com evidencia, testes sugeridos, rollback,
revisao humana obrigatoria, `automatic_promotion_allowed=false` e
`core_mutation_allowed=false`.

`MB-135` foi concluido: reflexoes anteriores relevantes agora podem influenciar
planning/synthesis de forma filtrada por workflow, rota e dominio, com
`reflection_influence_status`, refs auditaveis e sintese final explicita. Isso
nao promove mudanca automaticamente.

`MB-136` foi concluido: `evolution-lab` agora expoe uma fila humana read-only
de revisao evolutiva derivada de propostas sandbox, com estados explicitos,
blockers, testes, rollback e promocao bloqueada sem gate humano. O console
possui `evolution-review-queue --evolution-db ... --limit ...`. `MB-137` e o
item seguinte do lote para eval/piloto baseline vs reflection-assisted.

`MB-137` foi concluido: observabilidade, piloto interno, relatorio e comparador
agora exibem `reflection_influence_status`, refs e
`reflection_assisted_eval_status`, permitindo comparar baseline sem reflexao
versus execucao reflection-assisted sem tratar ganho local como autopromocao.

`MB-138` foi concluido: o console agora possui `mission-cycle --mission-id ...`
em modo read-only para mostrar missao, objetivo, rota, workflow, plano,
checkpoints, memoria usada, especialista, experiencia, reflexao, proposta
evolutiva, status de revisao e proximo passo. `MB-139` e o proximo item
`ready` para demonstrar o workflow pratico ponta a ponta.

`MB-139` foi concluido: o console agora possui
`mission-workflow "..." --mission-id ...`, que executa uma missao governada,
registra experiencia/reflexao, cria proposta sandbox no `evolution-lab`, mostra
o ciclo completo e encerra como `closed_with_human_review_pending`.

`MB-140` foi concluido: `docs/operations/operator-learning-loop.md` documenta
como iniciar missao, ver ciclo, consultar reflexoes, revisar propostas e
interpretar o relatorio. O lote `MB-132` a `MB-140` esta fechado; nao ha novo
item tecnico `ready` sem repriorizacao explicita baseada em evidencias de uso
humano.

Repriorizacao fechada: `MB-141` a `MB-145` formam o lote `Human Evolution
Review Controls`. O objetivo e transformar propostas evolutivas pendentes em
decisoes humanas auditaveis (`approve`, `reject`, `sandbox`, `needs_review`,
`rollback`), com evidencia, testes, rollback e bloqueio de autopromocao.

`MB-142` a `MB-145` foram concluidos: existe contrato compartilhado de decisao
humana, o `evolution-lab` registra transicoes revisaveis com historico,
evidencia, testes e rollback, o console expoe `evolution-review`, e
observabilidade/relatorios/comparador propagam status, proposta, operador,
evidencias, rollback e limites (`automatic_promotion_blocked`,
`core_mutation_blocked`). O lote `Human Evolution Review Controls` esta fechado;
nao ha novo item tecnico `ready` apos `MB-145` sem nova repriorizacao explicita
baseada em uso humano real.

Nova repriorizacao aberta: `MB-146` a `MB-150` formam o lote `Reviewed Learning
Feedback Loop`. O objetivo e permitir que decisoes humanas revisadas virem
guidance bounded, filtrado por rota/workflow/dominio, influenciem
planning/synthesis de forma auditavel e sejam medidas contra baseline sem
autopromocao.

`MB-146` e `MB-147` foram concluidos: o backlog foi aberto e
`ReviewedLearningGuidanceContract` agora existe em contratos/schemas/eventos,
com derivacao no `evolution-lab` apenas para decisoes humanas `approved` ou
`sandboxed`. O guidance preserva `automatic_promotion_allowed=false` e
`core_mutation_allowed=false`.

`MB-148` foi concluido: `reviewed_learning_guidance` agora pode influenciar
planning/synthesis de forma filtrada por rota, workflow e dominio, com refs,
motivo, status de influencia e bloqueio de promocao automatica.

`MB-149` e `MB-150` foram concluidos: observabilidade, piloto interno,
relatorio e comparador agora medem baseline vs reviewed-learning-assisted com
status, refs, motivo, taxas e conclusao `no_promotion_without_release_gate`.
O console (`mission-cycle`/`mission-workflow`) e a documentacao operacional
mostram quando guidance revisado influenciou a missao, por que foi usado ou
bloqueado e qual limite de release permanece ativo. O lote `MB-146` a `MB-150`
esta fechado; nao ha novo item tecnico `ready` sem nova repriorizacao
explicita.

`MB-151` foi concluido como auditoria documental governada oficial. A auditoria
esta registrada em
`docs/documentation/documentation-canonicality-audit-mb151.md`, revisou 73
documentos e nao moveu, deletou, renomeou, mesclou ou removeu arquivos.
`MB-152` tambem foi concluido: o mapa de backlinks esta em
`docs/documentation/documentation-backlink-map-mb152.md` e apenas documentos
ativos defasados foram sincronizados. Nenhum documento foi movido, deletado,
renomeado ou mesclado. Nao ha novo item `ready`; qualquer move/archive deve
nascer de decisao humana explicita e plano separado. `SO-001`, `TA-004`,
`TA-006`, `TA-008`, `DV-001` e `RH-*` continuam fora da fila ate decisao
explicita de fase.

`MB-153` foi concluido como primeiro archive fisico conservador:
`docs/documentation/documentation-cleanup-mb153.md` registra seis moves de
historico de implementacao para `docs/archive/implementation/`, rewrite de
backlinks, ausencia de delecao e ausencia de merge destrutivo. Documentos
referenciados pelo Documento-Mestre, como `docs/operations/v1-operational-baseline.md`
e `docs/roadmap/v1-roadmap.md`, permaneceram no lugar.

`MB-154` foi concluido como mapa mestre de implementacao:
`docs/implementation/implementation-master-map.md` decompoe o caminho completo
do JARVIS em trilhas de capacidade, status, dependencias, fases e proximos
slices. Ele nao substitui o Documento-Mestre nem o `execution-backlog.md`; ele
passa a ser a fonte para escolher o proximo lote micro. Nao ha item `ready`
automatico. O proximo candidato recomendado e o lote `MB-155` a `MB-159`,
focado em utilidade operacional do operador.

`MB-155` foi concluido como baseline minimo de dashboard textual do operador.
O console agora possui `operator-dashboard`, que agrega missao, objetivo, work
items, checkpoints, artefatos, ultima experiencia/reflexao, fila evolutiva,
sinais de aprendizado revisado e proximo passo em modo read-only. O dashboard
nao escreve memoria, nao promove proposta e nao cria fonte paralela de estado.

`MB-156` tambem foi concluido: work items agora possuem ciclo operacional
minimo governado por `work-item` e consulta por `work-items`, passando por
governanca, memoria canonica e eventos auditaveis. Isso nao cria scheduler,
atribuicao automatica ou armazenamento paralelo de tarefas.

`MB-157` foi concluido: artefatos vivos agora possuem lifecycle minimo por
`artifact` e consulta por `artifacts`, com refs bounded, versao, owner mission,
objetivo, work item, substituicao e rollback metadata. A transicao atualiza
somente estado canonico e eventos auditaveis; nao le, move, deleta nem edita
arquivos reais.

`MB-158` foi concluido: `FlowAudit` agora calcula
`operator_usefulness_status`, `operator_usefulness_score` e
`operator_usefulness_signals`, e `operator-dashboard` mostra esses sinais ao
operador. As metricas combinam objetivo consultado, work items, artefatos,
proxima acao, memoria causal, experiencia/reflexao e aprendizado revisado, sem
promover release ou autonomia.

`MB-159` foi concluido: `LongHorizonGoalStrategyContract`,
`MemoryService.build_long_horizon_goal_strategy()`,
`OrchestratorService.inspect_long_horizon_goal_strategy()`, evento
`long_horizon_goal_strategy_declared`, sintese final e comando `goal-strategy`
agora mostram estrategia minima de horizonte longo em modo read-only, derivada
de estado de missao, work items, artefatos, checkpoints, anchors de memoria e
proxima acao auditavel. Isso nao cria scheduler autonomo, nao executa passos
entre sessoes e nao promove memoria/proposta automaticamente.

O lote `MB-155` a `MB-159` esta fechado. A repriorizacao seguinte deve partir
de `docs/implementation/implementation-master-map.md`.

`MB-160` foi concluido como essa repriorizacao explicita: o
`execution-backlog.md` agora carrega uma fila maior `MB-161` a `MB-174`,
derivada do mapa mestre. A tese da fila e aprofundar utilidade operacional do
nucleo antes de abrir superficies ou automacoes fora de fase: memoria causal,
autonomia runtime, promocao sandbox-to-release, cockpit do operador, feedback,
dominios/evals, proveniencia de conhecimento e readiness/regressao.

`MB-161` foi concluido: a influencia de memoria semantica agora carrega
`semantic_memory_anchor_refs`, `semantic_memory_evidence_refs`,
`semantic_memory_use_reason` e `semantic_memory_non_use_reason` no plano,
sintese, eventos, observabilidade e console/dashboard. Esse fechamento abriu
`MB-162` naquele momento como proximo item tecnico.

`MB-162` foi concluido: `ProceduralPlaybookCandidateContract` agora formaliza
candidatos bounded de playbook procedural com passos limitados, evidencias,
refs de artefato/reflexao, testes, rollback, revisao humana obrigatoria,
`automatic_promotion_allowed=false`, `core_mutation_allowed=false` e
`memory_write_mode=through_core_only`. `memory-service` persiste/lista esses
candidatos, `evolution-lab` cria proposta sandbox-only a partir deles e o
console possui `procedural-playbooks` read-only. `MB-163` a `MB-174` tambem
foram concluidos; a fila tecnica posterior esta esgotada e aguarda
repriorizacao pelo mapa mestre.

O corte pos-`MB-125` foi repriorizado em `MB-126`: a proxima frente ativa e
experiencia operacional + reflexao pos-tarefa governada. O objetivo e fazer o
JARVIS registrar missoes reais, outcomes, falhas, decisoes, evidencias e
aprendizados candidatos como materia-prima auditavel de autoevolucao.

`MB-127` a `MB-131` foram concluidos: contratos compartilhados, memoria
evolutiva bounded, proposta `sandbox-only` no `evolution-lab`, observabilidade,
relatorio e console read-only agora tratam experiencia/reflexao pos-tarefa como
materia-prima governada de autoevolucao.

Nao ha novo item `ready` depois de `MB-131`; a proxima implementacao deve nascer
de nova repriorizacao explicita.

Limites preservados: isso nao abre self-modification, autopromocao, alteracao de
pesos, scheduler autonomo, voz, web, API publica, browser/computer use amplo,
`TA-004` ou `TA-006`. Toda melhoria derivada de reflexao continua exigindo
evidencia, testes, rollback e revisao humana.

O corte pos-`MB-119` foi repriorizado em `MB-120`: a proxima frente ativa e
estrutura evolutiva + absorcao tecnologica governada. Isso nao abre scheduler
autonomo, voz, web, API publica, browser/computer use amplo ou autopromocao.

`MB-121` foi concluido: `shared/contracts`, `shared/schemas` e
`shared/technology_absorption.py` agora definem o contrato minimo de candidato
tecnologico e sua gramatica de readiness. Tecnologia externa so entra como
referencia, experimento, complemento controlado ou traducao promovivel; tentativa
de assumir papel de nucleo e bloqueada; revisao manual exige evidencia, testes e
rollback.

`MB-122` tambem foi concluido: o `evolution-lab` agora registra candidatos
tecnologicos como propostas `sandbox-only`, com readiness, blockers, matriz de
avaliacao e politica explicita contra promocao automatica.

`MB-123` a `MB-125` tambem foram concluidos: observabilidade, piloto interno,
relatorio, comparador e console agora expoem sinais e candidatos de absorcao
tecnologica governada. O console possui `technology-candidates --evolution-db
... --limit ...` em modo read-only.

Esse lote foi fechado por `MB-125`; a repriorizacao seguinte ja foi registrada
em `MB-126`, e foi fechada ate `MB-131`. Autoedicao,
autopromocao, alteracao de pesos, voz, web, API publica, browser/computer use
amplo e scheduler autonomo continuam fora de fase.

O lote `MB-115` a `MB-119` foi aberto para transformar a fundacao de
projetos/objetivos em utilidade operacional para o operador humano.
`MB-115` foi concluido: o console agora possui `objectives --mission-id ...`
para consultar o estado persistido de projeto/objetivo, status, work items,
checkpoints, artefatos e proxima acao.

`MB-116` tambem foi concluido: o console agora possui comando operacional
bounded para retomar, pausar, bloquear, concluir e redefinir a proxima acao de
um objetivo, sempre por governanca, memoria canonica e evento auditavel.

`MB-117` tambem foi concluido: a sintese final agora expoe estado operacional
bounded do objetivo ativo quando esse contexto existe, incluindo status,
proxima acao, decisao pendente e artefato relevante, sem vazar detalhes internos
de especialistas nem promover autoexecucao.

`MB-118` tambem foi concluido: observabilidade, piloto interno, relatorio e
comparador agora expoem sinais de utilidade operacional de objetivos, incluindo
consulta, retomada, pausa, bloqueio, conclusao, redefinicao de proxima acao,
ausencia de proxima acao e ausencia de artefato.

`MB-119` foi concluido como fechamento documental do lote. Nao ha novo item
`ready` depois desta rodada; a proxima implementacao deve nascer de nova
repriorizacao explicita. Voz, web, API publica, browser/computer use amplo,
scheduler autonomo e memoria temporal rica continuam fora de fase.

## Atualizacao 2026-05-13

A rodada `MB-110` a `MB-114` foi implementada. O baseline agora possui
continuidade minima de projetos/objetivos: contratos compartilhados, runtime,
memoria, replay, eventos, observabilidade e relatorios carregam `project_ref`,
`objective_ref`, work items, checkpoints, artefatos, `objective_status` e
`next_action_ref`.

Limite arquitetural preservado: isso nao abre scheduler autonomo, execucao
longa, produto multicanal, browser/computer use ou memoria temporal ampla.
Essas frentes seguem dependendo de nova repriorizacao explicita.

## Metadata

- Atualizado em: 2026-05-17
- Branch: `main`
- Commit de referência: `02ccc53`
- Artefato canônico do projeto: `documento_mestre_jarvis.md`
- Estado do projeto: `v1` encerrado e congelado para uso controlado; primeiro ciclo do `pós-v1` encerrado; primeiro ciclo do `v1.5` encerrado; primeiro corte do `v2` encerrado; `v2-alignment-cycle` encerrado; próximo corte do `v2` aberto
- Fila micro ativa: `docs/implementation/execution-backlog.md`
- Backlog macro unificado: `docs/implementation/unified-gap-and-absorption-backlog.md`

## Atualização do próximo corte do v2

A primeira implementação do próximo corte do `v2` já foi aberta.

Leitura operacional correta desta rodada:

- as rotas `software_development`, `analysis`, `governance`, `operational_readiness`, `strategy` e `decision_risk` já operam em modo `guided`, ainda subordinadas ao núcleo;
- `specialist-engine` agora aceita rotas canônicas de especialista acima de `shadow`, desde que continuem `through_core_only` e `advisory_only`, e passou a validar se o vínculo domínio->especialista realmente bate com o registry soberano;
- `memory-service` já gera `domain_guided_memory_packet` de forma genérica para rotas promovidas do registry;
- `cognitive-engine` e `specialist-engine` agora consomem `domain_specialist_routes` explicitamente antes de qualquer fallback local, preservando o contrato de rota resolvido pelo runtime;
- `orchestrator-service` passou a emitir `domain_specialist_completed`, além dos sinais legados de `shadow` quando eles existirem;
- `observability-service` passou a auditar alinhamento de domínio por convocação canônica de especialista, não apenas por `shadow mode`.
- `knowledge-service` agora da precedencia explicita a mencoes de rotas runtime e dominios canonicos declarados no registry, com matching normalizado sem dependencia de acento.
- `orchestrator-service`, `planning-engine` e `operation dispatch` agora carregam `canonical_domains` e `primary_canonical_domain` diretamente do `domain_registry`, sem recomputar refs canonicas por heuristica local.
- `cognitive-engine` passou a delegar ranking, suporte, supressao e tensao dominante ao `mind_registry`, e `specialist_hints` agora so nascem de rotas canonicas ativas do registry.
- `memory-service` passou a materializar `semantic` e `procedural` como memoria `runtime_partial` apenas em packets guiados por dominio com evidencia persistida e compatibilidade canonica.
- `domain_registry` agora tambem expõe o slice soberano de `promoted_route_registry`, e o `orchestrator-service` passou a reutilizar esse payload nos eventos de selecao e conclusao de especialistas, reduzindo inferência residual na malha dominio->especialista.
- `memory-service` agora resolve a rota promovida elegivel diretamente pelo registry soberano, e o `specialist-engine` compara `consumer_profile`, `consumer_objective`, `expected_deliverables` e `telemetry_focus` do packet guiado contra o contrato canonico da rota.
- `planning-engine` passou a carregar o contrato da rota primaria promovida (`consumer_profile`, `consumer_objective`, `expected_deliverables`, `telemetry_focus`, `workflow_profile`) dentro do plano deliberativo.
- `planning-engine` agora tambem usa esse contrato para moldar passos, restricoes e criterio de saida do plano sem reintroduzir heuristica local.
- `synthesis-engine` passou a refletir esse contrato da rota ativa na leitura final, usando objetivo, entrega esperada, foco de leitura e workflow ativo como apoio guiado da resposta.
- `domain_registry` agora governa tambem o contrato soberano da rota primaria ponta a ponta, incluindo `consumer_objective`, `expected_deliverables`, `telemetry_focus`, `workflow_steps`, `workflow_checkpoints` e `workflow_decision_points`.
- `cognitive-engine` passou a gerar `specialist_hints` apenas por rotas ativas elegiveis do registry, preservando a ordem das rotas ativas e sem reintroduzir heuristica por `intent` puro.
- `memory_registry` passou a centralizar a politica declarativa que libera `semantic` e `procedural` em packets guiados para `planning`, `synthesis` e especialistas elegiveis.
- `orchestrator-service` agora emite `primary_route`, `primary_canonical_domain`, `primary_route_matches` e `primary_canonical_matches` nos eventos de selecao e conclusao de especialistas, e a `observability-service` usa esses sinais como gate direto de alinhamento.
- `planning-engine` agora usa `workflow_steps`, `workflow_checkpoints` e `workflow_decision_points` da rota promovida para moldar passos, restricoes, criterios de sucesso e rationale sem recompor esse contrato fora do registry.
- `synthesis-engine` passou a tornar esse workflow mais explicito na resposta final, expondo checkpoint ativo e gate governado da rota promovida.
- `operation_dispatch`, `workflow_composed`, `workflow_governance_declared`, `operation_completed` e `workflow_completed` agora carregam o mesmo slice soberano de `workflow_objective`, `workflow_expected_deliverables`, `workflow_telemetry_focus`, `workflow_success_focus` e `workflow_response_focus`.
- `observability-service` passou a tratar drift nesse contrato de workflow como `attention_required`, exigindo coerencia entre composicao, despacho, execucao e fechamento do workflow.
- `planning-engine` agora prioriza passos guiados de memoria semantica e procedural quando a rota ativa traz evidencia compativel, e `smallest_safe_next_action` passou a preservar explicitamente o fio procedural nas rotas elegiveis.
- `synthesis-engine` agora trata memoria semantica como ancora do framing final e memoria procedural como fio causal que a proxima acao precisa preservar.
- `planning-engine`, `orchestrator-service` e `observability-service` agora propagam `primary_mind`, `primary_domain_driver` e `arbitration_source` ate plano, resposta e auditoria.
- `cognitive-engine` e `specialist-engine` agora priorizam rotas explicitas que batem com `primary_domain_driver` quando esse vinculo ja foi resolvido pelo runtime, sem alterar o baseline de fallback quando a rota ainda nao existe.
- `orchestrator-service` e `observability-service` agora registram e auditam `primary_domain_driver_matches` na malha `mente -> dominio -> especialista`, cobrando que pelo menos um especialista selecionado/completado permaneça coerente com o dominio dominante quando esse sinal existir.
- `orchestrator-service` agora deriva hints de memoria guiada tambem do recovery soberano quando a rota ativa autoriza `semantic`/`procedural`, sem depender apenas de handoff especializado.
- `domain_registry` agora expõe guidance soberano por `workflow_profile`, e `planning-engine`/`synthesis-engine` passaram a usar esse guidance para leitura final, foco de sucesso e papel explícito de memória semântica/procedural por rota promovida.
- `memory_registry` e `memory-service` agora distinguem visibilidade de `semantic`/`procedural` entre reasoning final e packet de especialista: workflows analíticos/estratégicos/governados mantém `procedural` no runtime final, mas não o propagam automaticamente ao especialista subordinado.
- `memory_registry` passou a separar a visibilidade de memoria guiada para `planning/synthesis` da visibilidade para especialistas, mantendo o mesmo contrato soberano.
- `planning-engine` agora materializa `metacognitive_guidance` no plano deliberativo, distinguindo quando `primary_mind`, `primary_domain_driver` e `dominant_tension` alteraram criterio de saida, proxima acao segura e contencao.
- `synthesis-engine`, `response_synthesized` e `observability-service` agora propagam e auditam esse slice causal de metacognicao, em vez de deixar a ancora cognitiva apenas como leitura descritiva de rationale.
- `memory_registry`, `memory-service`, `planning-engine`, `synthesis-engine` e `observability-service` agora distinguem fonte, efeitos, lifecycle e revisao de `semantic`/`procedural` por `workflow_profile` e por fonte de continuidade, separando reasoning final, packet de especialista e recovery de missao.
- `orchestrator-service`, `observability-service`, `internal_pilot_report` e `compare_orchestrator_paths` agora carregam `mind_domain_specialist_chain_*`, `primary_mind` e `primary_route` como evidencia primaria do runtime, em vez de depender de parse posterior de `rationale`.
- `evolution_from_pilot`, `evolution-lab`, `compare_orchestrator_paths`, `internal_pilot_report` e `verify_release_signal_baseline.py` agora tratam metacognicao causal, lifecycle de memoria e coerencia `mente -> dominio -> especialista` como sinais formais de evolucao governada e readiness de release.
- `compare_orchestrator_paths`, `evolution-lab` e `evolution_from_pilot` agora publicam `refinement_vectors` por workflow, permitindo que o loop evolutivo sugira prioridade de refinamento do nucleo com base no runtime real.
- `planning`, `synthesis`, `orchestrator`, `memory`, `observability` e o piloto agora tambem carregam `mind_disagreement_status`, `mind_validation_checkpoint_status`, `memory_corpus_status` e `memory_retention_pressure` como sinais auditaveis do baseline.
- `observability-service` agora distingue `workflow_trace_status` de `workflow_profile_status`: o primeiro continua cobrando baseline saudavel, e o segundo passou a marcar `maturation_recommended` quando o workflow esta correto, mas ainda sem sinais ricos suficientes no runtime final.
- `internal_pilot_report` e `compare_orchestrator_paths` agora carregam `workflow_profile_status` ate os artefatos comparativos, deixando esse sinal visivel fora da auditoria local.
- `internal_pilot_report` e `compare_orchestrator_paths` agora tambem classificam esse sinal como `baseline_saudavel`, `maturation_recommended` ou `attention_required` por workflow, sem tratar maturacao recomendada como falha estrutural do baseline.
- `observability-service`, `internal_pilot_report` e `compare_orchestrator_paths` agora distinguem memoria causal (`causal_guidance`) de memoria apenas anexada (`attached_only`), expondo tambem foco semantico, hint procedural e especialistas ligados a esse efeito.
- os artefatos comparativos agora mostram `dominant_tension`, `primary_domain_driver` e `mind_domain_specialist_status`, deixando a malha `mente -> dominio -> especialista` menos implicita na leitura do baseline.
- `cognitive-engine` agora aplica recomposicao observavel em impasses reais de rota especializada, `orchestrator-service` publica `cognitive_recomposition_applied` e `observability-service` audita a coerencia desse sinal ao longo do fluxo.
- `evolution_from_pilot` e `evolution-lab` agora tratam `workflow_profile_status`, `memory_causality_status`, `mind_domain_specialist_status` e recomposicao cognitiva como sinais comparativos de refinamento, em vez de ignorar traces ainda saudaveis mas so parcialmente maduros.
- os fechadores regeneraveis `close_alignment_cycle` e `close_sovereign_alignment_cut` agora carregam decisoes e taxas desses sinais novos, aproximando comparacao sandbox, snapshot e closure docs da mesma gramatica de maturacao.
- `engineering_gate --mode release` agora roda `tools/verify_release_signal_baseline.py` e trata `workflow_profile_status`, `memory_causality_status`, `mind_domain_specialist_status` e recomposicao cognitiva como gramatica formal de release.
- `internal_pilot_support` agora inclui cenarios deliberados para memoria causal (`guided_memory_followup`) e recomposicao cognitiva por `specialist_route_impasse` (`recomposition_impasse`), com cobertura em relatorio e comparacao.
- `compare_orchestrator_paths` passou a marcar drift explicito de `workflow_profile_status`, `memory_causality_status`, `dominant_tension`, `primary_domain_driver`, `mind_domain_specialist_status` e recomposicao cognitiva entre baseline e candidata.
- `planning-engine`, `synthesis-engine` e `response_synthesized` agora tornam `dominant_tension`, `primary_domain_driver`, `workflow_response_focus` e recomposicao cognitiva mais declarativos no comportamento final do runtime.
- `verify_active_cut_baseline.py` agora combina contratos promovidos com um piloto focado que cobre as seis rotas promovidas, seus `workflow_profiles` e os sinais deliberados de memoria causal, discordancia entre mentes, corpus de memoria e recomposicao cognitiva.
- `internal_pilot_support` agora declara `expected_route`, `expected_workflow_profile` e `coverage_tags` nos cenarios canonicos do piloto, tornando a cobertura por rota/workflow parte explicita do baseline.
- o baseline ativo agora tambem exige cenarios deliberados para `dominant_tension` e alinhamento `mente -> dominio -> especialista`, promovendo esses sinais a readiness formal de robustez do `v2`.
- `close_domain_consumers_and_workflows_cut` agora carrega coverage de piloto, match de workflow e readiness dos sinais deliberados como parte da evidencia regeneravel do corte.
- `master-summary` e `docs/archive/implementation/v2-domain-consumers-and-workflows-cut-closure.md` agora refletem que o baseline do corte combina contratos promovidos com cobertura deliberada do piloto, em vez de tratar isso como detalhe tecnico implícito.
- o lote anterior do `execution-backlog` foi integralmente executado, incluindo `MB-020` a `MB-022`; esse fechamento permanece valido e a fila micro atual tambem voltou a ficar sem item `ready`.
- o caminho padrao do `orchestrator-service` agora tambem fecha a continuidade como subfluxo explicito via `continuity_subflow_completed`, alinhado ao mesmo payload soberano usado pelo caminho opcional de `LangGraph`.
- o lote `pre-v3 hardening` foi concluido em `docs/implementation/execution-backlog.md`, com `MB-023` a `MB-026` fechados; esse baseline permanece encerrado e nao deve ser reaberto por inercia.
- o `orchestrator-service` agora fecha o lifecycle de especialistas como subfluxo explicito (`specialist_subflow_completed`) e tambem declara `mission_runtime_state` para requests com missao ativa, related mission e readiness de retomada.
- `observability-service`, `internal_pilot_report`, `compare_orchestrator_paths`, `verify_active_cut_baseline.py` e o fechamento regeneravel do corte agora tratam `specialist_subflow` e `mission_runtime_state` como sinais agregados de hardening arquitetural pre-`v3`.
- a frente `pre-v3 protective intelligence foundation` foi mapeada e preservada em `docs/implementation/pre-v3-protective-intelligence-foundation-cut.md`, mas deixou de ser a proxima frente ativa do programa.
- o lote micro `MB-027` a `MB-031` foi reclassificado para `deferred` em `docs/implementation/execution-backlog.md`; nenhuma implementacao desse eixo deve ser puxada sem repriorizacao macro explicita do operador.
- `CHANGELOG.md` foi restaurado como changelog cronologico e o `engineering_gate` agora protege a identidade minima de `CHANGELOG.md`, `HANDOFF.md`, `documento_mestre_jarvis.md`, `docs/roadmap/programa-ate-v3.md` e `docs/implementation/v2-adherence-snapshot.md` antes da liberacao.

## Meta atual

Leitura atualizada desta rodada:

- o baseline fechado do `v2` agora precisa virar repriorizacao explicita, e nao
  continuacao inercial de lotes ja concluidos;
- `docs/implementation/unified-gap-and-absorption-backlog.md` passa a ser o
  mapa macro do que ainda falta no sistema;
- a fila micro atual nasceu dali, sem abrir vertical nova por impulso.
- esse recorte continua subordinado ao objetivo maior de construir um JARVIS
  soberano, amplo e autoevolutivo, capaz de absorver o estado da arte sem
  terceirizar identidade, memoria ou governanca.
- toda implementacao nova relevante deve agora carregar bateria de testes para
  validar o slice local e o fluxo ponta a ponta afetado, como politica oficial
  de robustez e resiliencia do repositorio.

Consolidar o fechamento operacional do `v2` sobre um runtime já alinhado aos eixos do Documento-Mestre, preservando `EV-002` + `EV-004` como baseline comparativo controlado e evitando reabrir esse lote por inercia local.

A fila micro ja fechou `MB-097` a `MB-106`: `SG-002` + `TA-002` entraram
como estado operacional bounded, auditavel e regeneravel do ecossistema, e
`SG-003` + `SO-002` agora tem contrato minimo de identidade por superficie
propagado pelo runtime atual, persistido em continuidade bounded e auditavel
em observabilidade, piloto, comparadores, baseline ativo, `evolution-lab` e
release, com fechamento documental sincronizado.
A fila micro tambem fechou `MB-107` a `MB-109`, derivada de `EV-001`, e
registrou `SO-003` como proxima frente tecnica apenas em recorte minimo.
O lote `MB-110` a `MB-114` foi fechado como fundacao soberana de projetos,
objetivos persistentes, work items, checkpoints e artefatos vivos.

### Foco operacional atual

Atualizacao desta rodada:

- preservar `MB-037` a `MB-066` como baseline fechado e nao reabrir Onda 1,
  maturacao causal, maturacao adaptativa ou politica soberana por workflow por
  inercia local;
- usar `docs/implementation/unified-gap-and-absorption-backlog.md` como backlog
  macro do que ainda falta, separando gaps do nucleo, traducao tecnologica,
  superficies, evolucao, verticais `deferred` e pesquisa;
- o lote `MB-067` a `MB-071` foi concluido e fechou a decisao soberana de
  capacidades, ferramentas e handoffs bounded como baseline auditavel do
  runtime;
- o lote `MB-072` a `MB-076` foi concluido e fechou manutencao ativa de memoria
  viva, compaction e recall cross-session 2.0 como baseline auditavel do
  runtime;
- o lote `MB-077` a `MB-081` foi concluido e fechou a arbitragem declarativa
  `mente -> dominio -> especialista` como baseline auditavel do runtime;
- `MB-079` agora tambem foi concluido: `observability-service`, piloto e
  comparadores passaram a expor `mind_domain_specialist_effectiveness` e
  `mind_domain_specialist_mismatch_flags` como evidencia formal da arbitragem
  final;
- `MB-080` e `MB-081` agora tambem foram concluidos: `evolution-lab`,
  `evolution_from_pilot`, comparadores e verificadores de release passaram a
  tratar efetividade e mismatch da arbitragem declarativa como insumo formal
  de `refinement_vectors`, `evaluation_matrix` e leitura de release;
- `MB-082` a `MB-086` agora tambem foram concluidos e fecharam o lote do
  nucleo para identidade, missao e politica como checklist executiva por
  request, derivado de `SG-006`;
- `planning`, `governance`, `orchestrator`, `observability`, piloto,
  comparadores, `evolution-lab` e verificadores de release agora tratam
  `request_identity_policy` como contrato soberano, auditavel e refinavel do
  runtime;
- `MB-087` a `MB-091` agora tambem foram concluidos e fecharam o lote de
  `EV-002` + `EV-004` como baseline comparativo controlado;
- `observability`, piloto, comparadores, `evolution-lab`, verificadores de
  release e fechadores regeneraveis agora tratam `expanded_eval_*`,
  `surface_axis_*`, `ecosystem_state_*`, `experiment_lane_*`,
  `experiment_exit_*` e `promotion_readiness` como gramatica soberana de
  eval expandida e lane controlada da Onda 2;
- `MB-092` a `MB-096` agora tambem foram concluidos e fecharam `EV-003` como
  baseline evolutivo governado;
- `shared/optimization_state.py`, `evolution-lab`, comparadores, relatorios,
  verificadores de baseline/release e fechadores regeneraveis agora tratam
  `optimization_target_kind`, `optimization_candidate_status`,
  `optimization_safety_status`, `optimization_readiness`,
  `optimization_release_status` e `optimization_blockers` como gramatica
  soberana de compile/optimize loops para prompts, planos e workflows;
- `MB-097` agora foi concluido: `OperationDispatchContract`,
  `OperationResultContract`, `orchestrator-service`, `operational-service` e
  eventos internos passaram a carregar estado operacional minimo do
  ecossistema;
- `MB-098` agora tambem foi concluido: `memory-service`,
  `shared/memory_registry.py`, `orchestrator-service` e a malha de
  continuidade passaram a persistir e retomar `ecosystem_state_*` como estado
  bounded de missao, checkpoint e replay;
- `MB-099` a `MB-101` agora tambem foram concluidos: `observability`,
  piloto, comparadores, baseline ativo, `evolution-lab`, verificadores de
  release e fechadores regeneraveis passaram a expor readiness do estado
  operacional do ecossistema sem abrir multissuperficie ampla ou substrate
  operacional fora de fase;
- `MB-102` foi concluido: `SurfaceIdentityContract`, `InputContract`,
  `OperationDispatchContract`, `OperationResultContract`, schemas, eventos e
  `apps/jarvis_console` agora carregam `surface_*`, operador e usuario
  canonico como contrato minimo de identidade por superficie;
- `MB-103` tambem foi concluido: console, eventos centrais do orquestrador,
  fluxo opcional de `LangGraph`, contexto de `planning` e entrada de `synthesis`
  carregam o mesmo slice, preservando `through_core_only`;
- `MB-104` tambem foi concluido: `memory-service`, `session_continuity`,
  `continuity_checkpoint`, `continuity_replay`, `mission_state` e
  `mission_runtime_state` persistem e recuperam superficies vinculadas,
  superficie ativa, ultima superficie conhecida e flags de conflito;
- `MB-105` e `MB-106` foram concluidos: continuidade de superficie agora e
  auditavel em observabilidade, piloto, comparadores e release, e o lote minimo
  multissuperficie esta fechado nos docs vivos;
- `MB-107` a `MB-109` foram concluidos como repriorizacao explicita de
  `EV-001`, escolhendo `SO-003` em recorte minimo;
- `MB-110` a `MB-114` foram concluidos como lote de continuidade minima de
  projetos/objetivos persistentes, sem abrir voz/realtime, web rica, API
  publica, memoria temporal rica, autoexecucao longa ou substrate operacional
  amplo;
- o proximo lote tecnico deve permanecer pequeno e subordinado ao nucleo; nao
  abrir voz/realtime, web rica, API publica, memoria temporal rica ou substrate
  operacional amplo sem decisao de fase;
- tratar a Onda 2 apenas como experimento controlado guiado pela matriz de
  readiness ja existente, sem promocao automatica de referencia externa;
- manter `protective intelligence`, `voice/realtime`, memoria temporal forte,
  `OpenClaw`, `Manus` e auto-modificacao fora da fila micro ate mudanca
  explicita de fase.
- o conservadorismo do corte atual e contencao de fase: o radar de tecnologia
  continua vivo, e a ambicao final do sistema nao foi reduzida.

- primeiro: preservar o `domain_registry` como autoridade única do contrato de rota promovida ao longo de `planning`, `memory`, `specialist`, `orchestrator` e observabilidade;
- depois: aprofundar critérios de saída e leitura final por `workflow_profile` sem reintroduzir heurística espalhada;
- depois disso: tornar memoria `semantic` e `procedural` mais causal por `workflow_profile`, sem quebrar a soberania do runtime atual;
- depois disso: separar com mais precisao o que ja e baseline saudavel e o que ainda e `maturation_recommended` por `workflow_profile`;
- depois disso: endurecer a cadeia `mente -> dominio -> especialista` com sinais cada vez menos implicitos e mais auditaveis;
- depois disso: usar o hardening pre-`v3` fechado como baseline para recentrar a fila micro em metacognicao mais causal, memoria mais viva e relacao `mente -> dominio -> especialista` menos implicita;
- `MB-032` a `MB-036` foram concluidos nesse eixo; o lote atual fechou metacognicao causal, memoria causal/lifecycle e evidencia primaria da cadeia `mente -> dominio -> especialista`;
- `MB-037` a `MB-040` foram concluidos; o baseline agora ja carrega vetores priorizados de refinamento por workflow, composicao de mentes mais profunda, telemetria viva de memoria e matriz formal de evals por eixo/workflow;
- a ordem oficial de absorcao tecnologica agora esta formalizada em `docs/architecture/technology-absorption-order.md`, com leitura por ondas e por camada do sistema;
- `MB-041` a `MB-046` foram concluidos como lote de absorcao disciplinada da Onda 1, sem adocao cega de stack externa;
- `MB-041` foi concluido: o runtime agora tem validacao canonica de `DeliberativePlanContract`, repair soberano pequeno no `planning`, validacao/recomposicao minima de output na `synthesis` e observabilidade explicita para `contract_validation_status` e `output_validation_status`;
- `MB-042` foi concluido: `memory_registry`, `memory-service`, `orchestrator`, `planning` e `synthesis` agora tratam contexto vivo compactado e recall cross-session como politica soberana do baseline, sem inflar a janela nem reabrir historico bruto;
- `MB-043` foi concluido: `memory_registry`, `memory-service`, `repository`, `planning`, `orchestrator` e `observability` agora distinguem memoria guiada operacional, fixada e arquivavel, com sinais explicitos de consolidacao, fixacao e arquivamento no runtime e no corpus;
- `MB-044` foi concluido: `orchestrator`, `langgraph_flow`, `operational-service` e `observability` agora carregam `workflow_checkpoint_state`, `workflow_resume_status`, `workflow_resume_point` e `workflow_pending_checkpoints` como sinais soberanos de durable execution e retomada governada;
- `MB-045` foi concluido: `memory-service`, `repository`, `planning`, `synthesis` e `orchestrator` agora tratam artefatos procedurais versionados, reutilizaveis e sempre `through_core_only` como parte explicita do baseline;
- `MB-046` foi concluido: `evolution-lab`, comparadores e verificadores de release agora persistem `candidate_refs`, `refinement_vectors`, `evaluation_matrix`, `selection_criteria` e `metric_deltas` como traducao governada de compile/eval loops;
- `MB-047` a `MB-051` foram concluidos e fecharam o lote de maturacao causal final do nucleo;
- `synthesis`, `response_synthesized` e `observability` agora distinguem output coerente, parcial e desalinhado por `workflow_profile`, e esse sinal atravessa piloto, comparadores, `evolution-lab` e verificadores de release como leitura formal de `baseline_saudavel`, `maturation_recommended` ou `attention_required`;
- `memory_registry`, `planning` e `synthesis` agora tornam `semantic` e `procedural` mais causais por workflow e por fonte de continuidade, fazendo essas memorias pesarem em prioridade, profundidade e recomendacao final do runtime;
- `orchestrator`, `synthesis`, comparadores e laboratorio agora tratam a cadeia `mente -> dominio -> especialista` como evidencia primaria mais rica, incluindo planned hints, alinhamento parcial e coerencia do encadeamento no runtime final;
- `MB-052` a `MB-056` foram concluidos e fecharam o lote atual de maturacao adaptativa do nucleo;
- `MB-052` foi concluido: `planning-engine`, `synthesis-engine`, `orchestrator-service` e `observability-service` agora tornam mudanca de estrategia cognitiva mid-flow observavel quando a revisao especializada mantem um impasse governado;
- `MB-053` foi concluido: `memory_registry`, `memory-service`, `repository` e `observability-service` agora fazem lifecycle de memoria alterar recovery, packet guiado, reuso recorrente e drift de memoria arquivavel no especialista;
- `MB-054` foi concluido: memoria relevante agora influencia rota prioritaria, hints especializados, ranking de continuidade e a leitura causal do caminho do runtime;
- `MB-055` foi concluido: composicao de mentes, discordancia e checkpoint de validacao agora pesam mais explicitamente em planejamento, sintese, comparadores e readiness de release;
- `MB-056` foi concluido: `evolution-lab`, comparadores e `technology-absorption-order.md` agora publicam matriz de readiness da Onda 2 subordinada aos sinais causais do nucleo;
- `MB-057` a `MB-061` foram concluidos e fecharam o lote de intervencao adaptativa governada do nucleo antes da sintese final;
- `MB-057` e `MB-058` agora formalizam e aplicam `adaptive_intervention_*` em `planning`, `orchestrator`, dispatch, revisao especializada e fluxo opcional de `LangGraph`, sem bypassar governanca nem substituir a linha principal do plano;
- `MB-059` e `MB-060` agora tornam a efetividade dessas intervencoes parte do baseline auditavel em `observability`, piloto, comparadores, `evolution-lab`, `evolution_from_pilot` e verificadores de release;
- `MB-067` a `MB-071` foram concluidos e fecharam o lote do nucleo para decisao soberana de capacidades, ferramentas e handoffs bounded, derivado de `SG-001`, `TA-001` e `TA-005`;
- `planning`, `orchestrator`, `governance`, `observability`, piloto, comparadores e `evolution-lab` agora tratam `capability_decision_*`, `capability_effectiveness` e `handoff_adapter_status` como slice baseline do runtime;
- `MB-072` a `MB-076` agora tambem foram concluidos e fecharam o lote do nucleo para manutencao ativa de memoria viva, derivado de `SG-004` e `TA-003`;
- `memory-service`, `planning`, `orchestrator`, `observability`, piloto, comparadores, `evolution-lab` e verificadores de release agora tratam `memory_maintenance_*`, compaction e recall cross-session como slice baseline, auditavel e refinavel do runtime;
- `MB-077` a `MB-081` foram concluidos e fecharam o lote do nucleo para arbitragem mais declarativa de `mente -> dominio -> especialista`, derivado de `SG-005`;
- `MB-077` agora foi concluido: `mind_domain_specialist_contract_*` passou a existir em `cognitive`, `specialist`, `planning`, `synthesis` e `orchestrator`, distinguindo cadeia autoritativa, override bounded e fallback governado como contrato soberano do runtime;
- `MB-078` e `MB-079` agora foram concluidos: consumo final, fallback governado e evidencia auditavel da arbitragem `mind_domain_specialist` ja fazem parte do baseline do runtime;
- `MB-080` e `MB-081` agora tambem foram concluidos: `evolution-lab`, `evolution_from_pilot`, comparadores e verificadores de release passaram a tratar efetividade e mismatch da arbitragem declarativa como insumo formal de `refinement_vectors`, `evaluation_matrix` e leitura de release;
- `MB-082` a `MB-086` agora tambem foram concluidos e fecharam o lote do
  nucleo para identidade, missao e politica por request, derivado de `SG-006`;
- `planning`, `governance`, `orchestrator`, `observability`, piloto,
  comparadores, `evolution-lab` e verificadores de release agora tratam
  `request_identity_policy` como contrato soberano, auditavel e refinavel do
  runtime;
- `MB-087` a `MB-091` agora tambem foram concluidos e fecharam `EV-002` +
  `EV-004` como baseline comparativo controlado;
- `MB-097` a `MB-101` agora foram concluidos e fecharam o lote bounded de
  estado operacional do ecossistema em runtime, memoria, observabilidade,
  evolucao, release e documentacao;
- `MB-102` a `MB-106` foram concluidos e fecharam contrato, propagacao runtime,
  continuidade bounded, auditoria/readiness e documentacao da identidade minima
  por superficie;
- tratar a Onda 2 apenas como experimento controlado guiado pela matriz de
  readiness ja existente, sem promocao automatica de referencia externa;
- so depois desse lote: reavaliar qual vertical derivada deve abrir a proxima frente macro; `protective intelligence` permanece mapeado, mas em `deferred` ate nova decisao explicita;
- so entao: decidir se o `v3` deve abrir por essa frente, por outra vertical derivada ou por mais maturacao transversal.

Regra operacional desta fase:

- `HANDOFF.md` permanece macro e tatico;
- a fila micro executavel agora vive exclusivamente em `docs/implementation/execution-backlog.md`;
- a proxima frente tecnica deve nascer de repriorizacao explicita no backlog macro, nao ser reconstruida localmente a partir deste handoff.

Sistema oficial de planejamento desta fase:

- `HANDOFF.md` como retomada tático-operacional;
- `docs/implementation/execution-backlog.md` como fila micro soberana do corte ativo;
- `docs/implementation/unified-gap-and-absorption-backlog.md` como mapa macro do que ainda falta e base para a proxima repriorizacao;
- `docs/operations/chat-transition-template.md` como template operacional para abrir novo chat sem perder foco entre lotes;
- `docs/roadmap/programa-ate-v3.md` como direção do programa até `v3`;
- `docs/archive/implementation/v2-cycle-closure.md` como fechamento formal do primeiro corte do `v2`;
- `docs/archive/implementation/v2-alignment-cycle.md` como histórico fechado do ciclo anterior;
- `docs/archive/implementation/v2-native-memory-scope-hardening-cut.md` como ultimo recorte funcional executado do baseline nativo atual;
- `docs/archive/implementation/v2-native-memory-scope-hardening-cut-closure.md` como fechamento formal regeneravel do ultimo recorte funcional;
- `docs/archive/implementation/v2-repository-hygiene-and-tools-review-cut.md` como ultimo recorte estrutural executado;
- `docs/archive/implementation/v2-repository-hygiene-inventory.md` como inventario regeneravel da revisao estrutural ativa;
- `docs/archive/implementation/v2-repository-hygiene-doc-decisions.md` como decisao regeneravel de classificacao dos docs ativos;
- `docs/archive/implementation/v2-repository-hygiene-tool-decisions.md` como decisao regeneravel de classificacao dos entrypoints de `tools/`;
- `docs/archive/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md` como fechamento formal regeneravel da revisao estrutural mais recente;
- `docs/archive/implementation/v2-sovereign-alignment-cut.md` como histórico de transição do corte anterior;
- `docs/archive/implementation/v2-domain-consumers-and-workflows-cut-closure.md` como fechamento formal regenerável do corte anterior imediato;
- `docs/documentation/matriz-de-aderencia-mestre.md` como ponte entre visão canônica e backlog real.
- `docs/documentation/repository-map-and-consistency-audit.md` como mapa vivo de papeis, inconsistencias e candidatos a reclassificacao do repositorio.
- `docs/roadmap/programa-de-excelencia.md` como mapa completo de gaps, capacidades ausentes e direcao de maturacao para excelencia.
- `docs/architecture/technology-capability-extraction-map.md` como mapa do melhor valor extraivel de cada tecnologia externa.
- `docs/architecture/technology-absorption-order.md` como ordem oficial de traducao disciplinada dessas referencias para o JARVIS.

Leitura prioritária de aderência neste momento:

- eixo concluído na Sprint 1: `domínios`, com registry soberano sobre roteamento, maturity gate, shadow specialist sem heurística residual e fallback derivado;
- eixo concluído na Sprint 2: `memórias`, com políticas operacionais por classe para recovery, compartilhamento mediado e auditoria por classe;
- eixo concluído na Sprint 3: `mentes`, com arbitragem soberana por registry, mente primária, apoios, supressões e tensão dominante observáveis;
- eixo concluído na Sprint 4: `identidade`, com assinatura do núcleo, guardrails de governança e resposta auditável ao longo do fluxo.

Estado do ciclo rolante:

- primeiro ciclo do `pós-v1` concluído;
- primeiro ciclo do `v1.5` concluído;
- Sprint 1 do `v2` concluída;
- Sprint 2 do `v2` concluída;
- Sprint 3 do `v2` concluída;
- Sprint 4 do `v2` concluída;
- Sprint 5 do `v2` concluída;
- Sprint 6 do `v2` concluída;
- o primeiro corte do `v2` está formalmente encerrado;
- Sprint 1 do `v2-alignment-cycle` concluída;
- Sprint 2 do `v2-alignment-cycle` concluída;
- Sprint 3 do `v2-alignment-cycle` concluída;
- Sprint 4 do `v2-alignment-cycle` concluída;
- Sprint 5 do `v2-alignment-cycle` concluída;
- Sprint 6 do `v2-alignment-cycle` concluída;
- o próximo corte do `v2` está formalmente aberto;

## Decisões fechadas

Não rediscutir sem evidência forte ou mudança explícita de direção:

- o JARVIS é um sistema unificado, não um chatbot simples;
- o núcleo continua próprio e soberano na relação com o usuário;
- especialistas são subordinados ao núcleo, não competidores de identidade;
- `Python` continua como linguagem principal;
- `PostgreSQL` é o backend operacional oficial de memória;
- `sqlite` continua apenas como fallback local;
- `LangSmith` continua complementar; a trilha local persistida segue como fonte primária de auditoria;
- `LangGraph` continua como direção arquitetural forte; o subfluxo stateful de continuidade já foi absorvido parcialmente, sem transformar o runtime inteiro no runtime principal do sistema;
- referências externas passam a ser avaliadas em dois eixos: posicionamento na stack e função arquitetural por camada;
- o Documento-Mestre continua sendo o único artefato canônico de visão de produto.

Regra curta de nomenclatura técnica:

- a regra de nomes do sistema deve privilegiar nomes profissionais, limpos, robustos e duráveis;
- artefatos permanentes do sistema não devem carregar `v1`, `v2`, `poc`, `draft`, `temp` ou rótulos equivalentes no nome técnico principal;
- fase, maturidade e modo de execução devem ficar em metadata, docs vivos ou no conteúdo do artefato;
- quando um artefato transitório virar parte estável do sistema, ele deve ser renomeado para forma neutra na próxima intervenção útil.

Regra curta de promoção tecnológica nesta fase:

- nenhuma tecnologia externa atravessa direto para o núcleo;
- primeiro ela precisa responder a uma lacuna concreta do ciclo ativo;
- depois precisa ser classificada como `absorver depois`, `usar como referência` ou `rejeitar`;
- só então pode virar fluxo experimental, complemento controlado ou candidata a baseline de fase futura.

Responsabilidade prática nesta fase:

- o agente ativo conduz a análise técnica e produz a recomendação;
- a promoção só vale quando houver evidência e alinhamento com os artefatos oficiais do ciclo;
- nenhuma promoção tecnológica reabre o baseline do `v1` por conveniência.

Autonomia operacional nesta fase:

- o agente ativo pode executar sozinho sincronização de docs vivos, refactors de nomenclatura, endurecimento de contratos, testes, observabilidade, gates e coerência entre registries e runtime;
- o agente ativo pode abrir e fechar sprints dentro do corte ativo quando isso não mudar a direção macro já fechada;
- o agente ativo pode puxar sozinho o próximo item `ready` de `docs/implementation/execution-backlog.md` quando `depende_do_operador = nao`;
- o operador deve ser acionado apenas para decisões de direção, como mudança de ontologia, promoção de tecnologia externa a baseline central, abertura de nova superfície principal ou alteração da prioridade macro do programa;
- a regra prática é simples: implementação dentro da direção fechada é autonomia do Codex; mudança de direção continua reservada ao operador.

## Estado atual do repositório

Hoje o repositório contém:

- baseline integrado entre orquestração, memória, governança, conhecimento, observabilidade e operação;
- `jarvis-console` como interface textual mínima do baseline;
- `memory-service` com histórico episódico, resumo contextual, estado mínimo de missão e continuidade relacionada inicial;
- `shared/memory_registry.py` como registry formal das 11 classes de memória, já conectado ao recovery default e ao compartilhamento com especialistas;
- `shared/mind_registry.py` como registry formal das 24 mentes canônicas, com suporte preferencial inicial no `cognitive-engine`;
- `observability-service` com trilha persistida, auditoria de fluxo e espelhamento agentic complementar;
- `evolution-lab` persistindo proposals e decisões `sandbox-only`;
- `tools/validate_baseline.py`, `tools/go_live_internal_checklist.py`, `tools/run_internal_pilot.py`, `tools/compare_orchestrator_paths.py`, `tools/evolution_from_pilot.py`, `tools/archive/close_stateful_runtime_cycle.py` e `tools/archive/close_alignment_cycle.py` operacionais;
- estudo tecnológico consolidado em `docs/architecture/technology-study.md`;
- sistema documental em duas camadas ativas para programa e sprint cycle;
- auditoria documental oficial `MB-151` em
  `docs/documentation/documentation-canonicality-audit-mb151.md`;
- mapa de backlinks e sincronizacao segura `MB-152` em
  `docs/documentation/documentation-backlink-map-mb152.md`, sem limpeza fisica
  de documentos.
- archive fisico conservador `MB-153` em
  `docs/documentation/documentation-cleanup-mb153.md`, limitado a historico de
  implementacao ja mapeado.
- mapa mestre de implementacao `MB-154` em
  `docs/implementation/implementation-master-map.md`, usado para derivar
  proximos lotes sem repriorizacao cega.

### Baseline materializado

Capacidades concretas já presentes no repositório:

- `orchestrator-service` coordenando o fluxo ponta a ponta do núcleo;
- `memory-service` com persistência útil, recuperação contextual e continuidade relacionada inicial;
- `knowledge/curated/domain_registry.json` com mapa canônico de domínios separado das rotas runtime ativas do ciclo;
- `governance-service` com decisões `allow`, `allow_with_conditions`, `block` e `defer_for_validation`;
- `knowledge-service` com corpus curado local e retrieval determinístico;
- `observability-service` com trilha persistida, auditoria de requests e espelhamento agentic complementar;
- `operational-service` com produção de artefatos textuais de baixo risco;
- `evolution-lab` comparando baseline e candidata em regime `sandbox-only`;
- `jarvis-console` como primeira superfície textual real do sistema.

## O que foi feito até aqui

Principais entregas já consolidadas:

- fechamento disciplinado do `v1` com baseline operacional e console mínimo;
- validação local e `controlled` com `PostgreSQL`;
- `internal pilot` executado e convertido em evidência operacional;
- fluxo opcional de `LangGraph` aberto no orquestrador;
- Sprint 1 do `pós-v1` concluída, com modelo mínimo de continuidade entre missões relacionadas;
- Sprint 2 concluída, com ranking determinístico entre missão ativa, loops abertos e missão relacionada;
- Sprint 3 concluída, com decisão explícita entre continuar, encerrar, reformular ou retomar continuidade relacionada;
- Sprint 4 concluída, com snapshot persistente de continuidade da sessão e síntese orientada a continuidade acima da missão atual;
- Sprint 5 concluída, com auditoria explícita da continuidade, sinais comparáveis no piloto e integração desses sinais ao laboratório sandbox;
- Sprint 6 concluída, com fechamento formal do primeiro ciclo do `pós-v1` e decisão explícita de promoção para `v1.5`;
- Sprint 1 do `v1.5` concluída, com checkpoint explícito de continuidade e estado recuperável por sessão;
- Sprint 2 do `v1.5` concluída, com replay explícito, retomada governada e ponto de recuperação rastreável por sessão;
- Sprint 3 do `v1.5` concluída, com pausa `HITL` persistente, resolução manual rastreável e retomada segura acima do checkpoint governado;
- Sprint 4 do `v1.5` concluída, com subfluxo stateful de continuidade absorvido parcialmente em `LangGraph` e sinal explícito de runtime no fluxo comparativo;
- Sprint 5 do `v1.5` concluída, com evals do runtime de continuidade, cenários de conflito e retomada manual no piloto e decisão `candidate_ready_for_eval_gate` para o recorte absorvido;
- Sprint 6 do `v1.5` concluída, com fechamento formal do ciclo, classificação do backlog e decisão explícita de promoção para `v2`;
- Sprint 1 do `v2` concluída, com contratos mínimos de convocação de especialistas, fronteiras explícitas de runtime e integração mínima no núcleo;
- Sprint 2 do `v2` concluída, com seleção governada de especialistas, handoff interno observável e contenção explícita quando a convocação viola fronteiras;
- Sprint 3 do `v2` concluída, com memória relacional compartilhada mediada pelo núcleo, contexto persistido por especialista e handoff enriquecido sem escrita direta fora do núcleo;
- Sprint 4 do `v2` concluída, com registry inicial de domínios do ciclo, rota canônica `software_development -> software_change_specialist` e execução explícita em `shadow mode`;
- Sprint 5 do `v2-alignment-cycle` concluída, com gates explícitos de aderência por eixo em `internal_pilot_report`, `compare_orchestrator_paths` e `evolution_from_pilot`.
- Documento-Mestre ampliado com referências arquiteturais oficiais por função.

## O que ainda falta

Pendências principais desta fase:

- manter os docs vivos refletindo o baseline soberano já absorvido no `v2`;
- tratar o lote `pre-v3 hardening` em `docs/implementation/execution-backlog.md` como concluido, sem reabrir `MB-024` a `MB-026` como fila pendente;
- manter `docs/implementation/pre-v3-protective-intelligence-foundation-cut.md` como estudo macro preservado, mas em estado `deferred`, sem tratar esse eixo como fila ativa;
- tratar `MB-032` a `MB-036` como baseline ja fechado, sem reabrir o mesmo lote por inercia local;
- tratar `MB-037` a `MB-040` como lote fechado, sem reabrir o mesmo trabalho por inercia local;
- continuar refinando criterios de saida por `workflow_profile`, uso soberano de memoria e profundidade da cadeia `mente -> dominio -> especialista` apenas quando isso justificar um novo lote real;
- repriorizar explicitamente a proxima frente antes de abrir novo item micro `ready`.

Regra de estudo externo no `v2`:

- entra apenas o estudo que ajude diretamente contratos de especialistas, handoffs internos, memória relacional, arbitragem soberana ou gates de aderência do ciclo;
- `OpenHands` e `PydanticAI` seguem como referências mais diretamente ligadas ao corte imediato;
- `Hermes Agent`, `Graphiti`, `Zep`, `LangGraph` e `OpenAI Agents SDK` entram apenas como apoio dirigido ao problema do ciclo;
- `computer use` amplo, voz oficial, memória profunda com `pgvector` como base canônica e assistente operacional amplo continuam fora do foco imediato.

## Próximos passos imediatos

Ordem recomendada:
1. preservar `MB-102` a `MB-125` como baseline fechado de superficies minimas, objetivos persistentes, utilidade operacional e absorcao tecnologica governada;
2. preservar `MB-126` a `MB-131` como baseline fechado de experiencia/reflexao pos-tarefa governada;
3. manter voz/realtime, web rica, API publica, gateway externo, memoria temporal rica, autoexecucao longa e substrate operacional amplo fora de fase;
4. preservar `MB-023` a `MB-026` como baseline fechado e `MB-027` a `MB-031` como `deferred`, sem reabrir `protective intelligence` por impulso;
5. manter historico regeneravel em `docs/archive/implementation/` e `tools/archive/` sem reexpandir a raiz do repositorio.

Atualização desta rodada:

- `MB-052` a `MB-056` permanecem fechados como lote anterior de maturacao adaptativa do nucleo;
- `MB-057` a `MB-061` foram concluidos e fecharam o lote de intervencao adaptativa governada do nucleo;
- `adaptive_intervention_*` agora existe como contrato soberano do runtime, evidenciado em `planning`, `orchestrator`, `observability`, piloto, comparadores, `evolution-lab` e verificadores de release;
- `MB-062` ja foi concluido e abriu o novo lote de prioridade soberana por workflow, fazendo `structured_analysis`, `strategy`, `software_change`, `governance`, `decision_risk` e `operational_readiness` deixarem de compartilhar a mesma precedencia fixa entre revisao de memoria e reavaliacao especializada;
- `MB-063` agora tambem foi concluido: `observability-service`, `internal_pilot_report`, `compare_orchestrator_paths.py` e `verify_release_signal_baseline.py` passaram a publicar `adaptive_intervention_policy_status`, distinguindo `policy_aligned`, `mandatory_override` e `attention_required`;
- `MB-064` a `MB-066` agora tambem foram concluidos: `synthesis` e `response_synthesized` passaram a expor a prioridade do workflow com checkpoint/gate preservado, enquanto `evolution-lab`, `evolution_from_pilot.py` e comparadores promovem a politica de intervencao a criterio formal de refinamento;
- `MB-067` a `MB-071` tambem foram concluidos e fecharam o lote de decisao soberana de capacidades, ferramentas e handoffs bounded;
- `MB-072` a `MB-076` agora tambem foram concluidos: `memory-service`, `planning`, `orchestrator`, `observability`, piloto, comparadores, `evolution-lab` e verificadores de release passaram a tratar `memory_maintenance_*`, compaction e recall cross-session como baseline auditavel e refinavel do runtime;
- `MB-077` a `MB-081` agora tambem foram concluidos e fecharam o lote do nucleo para arbitragem mais declarativa de `mente -> dominio -> especialista`, derivado de `SG-005`;
- `MB-077` agora foi concluido: `mind_domain_specialist_contract_*` passou a existir na ultima milha de `cognitive`, `specialist`, `planning`, `synthesis` e `orchestrator`, distinguindo cadeia autoritativa, override bounded e fallback governado no runtime principal;
- `MB-078` e `MB-079` agora tambem foram concluidos: consumo final, fallback governado e evidencia auditavel da arbitragem `mind_domain_specialist` ja fazem parte do baseline;
- `MB-080` e `MB-081` agora tambem foram concluidos: `evolution-lab`, `evolution_from_pilot`, comparadores e verificadores de release passaram a tratar efetividade e mismatch da arbitragem declarativa como insumo formal de `refinement_vectors`, `evaluation_matrix` e leitura de release;
- `MB-082` a `MB-086` agora foram concluidos e fecharam o lote do nucleo para
  identidade, missao e politica por request, derivado de `SG-006`;
- `request_identity_policy` agora ja existe como contrato soberano do runtime,
  com evidencia auditavel, uso evolutivo e leitura de release integrados ao
  baseline;
- `MB-087` a `MB-091` agora tambem foram concluidos e fecharam o lote de evals
  expandidas e lane controlada da Onda 2, derivado de `EV-002` + `EV-004`;
- `observability`, piloto, comparadores, `evolution-lab`, verificadores de
  release e fechadores regeneraveis agora tratam `expanded_eval_*`,
  `surface_axis_*`, `ecosystem_state_*`, `experiment_lane_*`,
  `experiment_exit_*` e `promotion_readiness` como baseline comparativo
  controlado do nucleo;
- a rodada seguinte recuperou o gate global: `planning-engine` deixou de promover `specialist_reevaluation` a validacao humana no plano refinado, `shared/domain_registry.py` voltou a preservar `workflow_steps`, `workflow_checkpoints` e `workflow_decision_points` em rotas promovidas, e `python tools/engineering_gate.py --mode standard` agora fecha sem falhas;
- `documento_mestre_jarvis.md`, `docs/roadmap/programa-ate-v3.md` e `docs/implementation/v2-adherence-snapshot.md` agora deixam mais explicito que LLMs e runtimes agentic entram como substrato subordinado ao nucleo, que multiplas superficies expõem a mesma entidade e que o horizonte do `v3` inclui estado operacional mais rico do ecossistema;
- `protective intelligence` segue preservada em `deferred`, e a matriz de readiness da Onda 2 continua apenas como insumo controlado do proximo refinamento do nucleo.

## Riscos e bloqueios

- o `pós-v1` não deve reabrir o baseline do `v1` sem necessidade real;
- `pgvector`, memória semântica profunda, web, voz e especialistas amplos continuam fora do caminho crítico do ciclo atual;
- o fluxo opcional de `LangGraph` continua dependente do extra `.[langgraph]`, mesmo após a absorção parcial do subfluxo stateful;
- o maior risco atual não é estabilidade local; é abrir especialistas cedo demais sem contratos, memória relacional e governança suficientes.

## Arquivos relevantes

- `documento_mestre_jarvis.md`
- `README.md`
- `HANDOFF.md`
- `CHANGELOG.md`
- `docs/implementation/unified-gap-and-absorption-backlog.md`
- `docs/roadmap/programa-ate-v3.md`
- `docs/archive/implementation/v2-domain-consumers-and-workflows-cut.md`
- `docs/archive/implementation/v2-memory-gap-evidence-cut.md`
- `docs/archive/implementation/v2-memory-gap-evidence-protocol.md`
- `docs/archive/implementation/v2-memory-gap-baseline-evidence.md`
- `docs/archive/implementation/v2-memory-gap-decision.md`
- `docs/archive/implementation/v2-memory-gap-evidence-cut-closure.md`
- `docs/archive/implementation/v2-native-memory-scope-hardening-cut.md`
- `docs/documentation/matriz-de-aderencia-mestre.md`
- `docs/architecture/technology-study.md`
- `docs/architecture/turboquant-review.md`
- `docs/archive/implementation/`
- `docs/operations/v1-operational-baseline.md`
- `services/orchestrator-service/src/orchestrator_service/service.py`
- `services/memory-service/src/memory_service/service.py`
- `services/memory-service/src/memory_service/repository.py`
- `services/observability-service/src/observability_service/service.py`
- `engines/planning-engine/src/planning_engine/engine.py`
- `tools/run_internal_pilot.py`
- `tools/compare_orchestrator_paths.py`
- `tools/evolution_from_pilot.py`

## Como retomar

Leitura mínima para qualquer novo agente:

1. `HANDOFF.md`
2. `documento_mestre_jarvis.md`
3. `docs/roadmap/programa-ate-v3.md`
4. `docs/implementation/unified-gap-and-absorption-backlog.md`
5. `docs/archive/implementation/v1-5-cycle-closure.md`
6. `docs/archive/implementation/v2-cycle-closure.md`
7. `docs/archive/implementation/v2-alignment-cycle.md`
8. `docs/archive/implementation/v2-sovereign-alignment-cut.md`
9. `docs/architecture/technology-study.md`
10. `docs/architecture/turboquant-review.md`


## Visão de absorção tecnológica

Leitura de longo prazo desta fase e das próximas:

- o JARVIS deve evoluir como sistema cognitivo soberano capaz de absorver o melhor do ecossistema sem virar uma colagem de frameworks;
- a absorção tecnológica deve continuar subordinada ao núcleo, à memória canônica, à governança e à síntese própria do sistema;
- o objetivo não é terceirizar o cérebro do JARVIS, e sim incorporar valor arquitetural por função clara.

Fluxo longo de absorção tecnológica governada:

1. radar contínuo do ecossistema;
2. classificação arquitetural por eixo do sistema;
3. registro em memória evolutiva;
4. sandbox, benchmark ou fluxo experimental;
5. promoção governada por evidência.

Leitura correta por famílias de referência:

- `LangGraph`: fluxo stateful, checkpoints, replay e handoffs coordenados;
- `Hermes Agent`: runtime persistente, memória viva, continuidade operacional e skills;
- `Graphiti` e `Zep`: memória relacional, temporal e contextual;
- `DSPy / MIPROv2`, `TextGrad`, `AFlow`, `EvoAgentX`, `SEAL` e `Darwin Gödel Machine`: autoaperfeiçoamento, otimização e evolução governada.

Regra de disciplina:

- estudo externo não bloqueia a implementação principal;
- nenhuma tecnologia externa vira dependência central sem decisão arquitetural formal;
- toda absorção deve ser reversível, traduzida para os contratos do JARVIS e compatível com a soberania do núcleo.

## Política oficial de engenharia

A partir desta rodada, a referência oficial de boas práticas do repositório passa a ser:

- `docs/documentation/engineering-constitution.md`
- `AGENTS.md`
- `tools/engineering_gate.py`

Leitura correta:

- robustez, segurança, reversibilidade e auditabilidade deixam de ser só intenção e passam a ser política explícita;
- toda mudança relevante deve passar por contrato, teste, observabilidade e documentação;
- qualquer agente implementador deve seguir `AGENTS.md` e rodar o gate adequado antes de tratar a rodada como fechada.

Gate mínimo oficial:

```powershell
python tools/engineering_gate.py --mode standard
```

## Regra de linguagem

- documentação, visão e texto voltado a operador podem permanecer em português;
- contratos técnicos, eventos, payloads, status e novos ids de runtime devem convergir para inglês;
- ontologias canônicas derivadas do Documento-Mestre podem permanecer em português enquanto camada semântica;
- ids legados em português não devem ser expandidos por conveniência local.

## Atualizacao 2026-03-31

- specialist types do runtime seguem usando ids canonicos em ingles, com compatibilidade curta para labels legados em portugues;
- o corte de prova de lacuna de memoria multicamada foi formalmente encerrado;
- Sprint 2 permanece concluida com workflows compostos auditaveis no runtime;
- Sprint 3 foi concluida com benchmark governado por familia e matriz regeneravel em `docs/archive/implementation/v2-governed-benchmark-matrix.md`;
- `AutoGPT Platform`, `Mastra` e `Mem0` foram formalizadas como candidatas de `benchmark_now`;
- `LangGraph`, `OpenAI Agents SDK`, `CrewAI`, `Microsoft Agent Framework`, `OpenClaw`, `Hermes Agent`, `Manus`, `Letta / MemGPT`, `Zep` e `Graphiti` passaram a compor o `reference_envelope` do recorte;
- a Sprint 4 foi concluida com `tools/verify_active_cut_baseline.py` como verificador regeneravel do baseline do corte ativo;
- `tools/archive/close_domain_consumers_and_workflows_cut.py` passou a fechar o corte em `.jarvis_runtime/v2_domain_consumers_and_workflows_cut/`;
- a Sprint 1 do novo corte foi concluida com `docs/archive/implementation/v2-memory-gap-evidence-protocol.md` como protocolo regeneravel das hipoteses de lacuna do baseline atual;
- a Sprint 2 do novo corte foi concluida com `docs/archive/implementation/v2-memory-gap-baseline-evidence.md` como leitura local por escopo do baseline atual;
- a Sprint 3 do novo corte foi concluida com `docs/archive/implementation/v2-memory-gap-decision.md` como decisao formal de `manter_fechado`, preservando `Mem0` em `absorver_depois`;
- a Sprint 4 do recorte foi concluida com `docs/archive/implementation/v2-memory-gap-evidence-cut-closure.md` como fechamento formal do corte e recomendacao explicita do proximo recorte nativo;
- o baseline agora esta lido assim: conversa, sessao e missao permanecem suficientes; usuario e shared specialist memory sustentam lacuna parcial; organization scope continua apenas forma futura;
- o novo corte ativo passa a ser `v2-native-memory-scope-hardening-cut`, focado em endurecimento nativo de user scope e contexto recorrente de especialistas.
- a Sprint 1 do `v2-native-memory-scope-hardening-cut` foi concluida com snapshot nativo de `user scope`, recovery default desse escopo quando houver `user_id` e sinais minimos em observabilidade.
- a Sprint 2 do `v2-native-memory-scope-hardening-cut` foi concluida com contexto recorrente nativo por especialista promovido, ainda `through_core_only`, com telemetria de recorrencia no handoff e na observabilidade.
- a Sprint 3 do `v2-native-memory-scope-hardening-cut` foi concluida com no-go explicito de `organization scope`, publicado no runtime de memoria e resumido na observabilidade.
- a Sprint 2 foi concluida com `docs/archive/implementation/v2-governed-benchmark-scenario-specs.md` como artefato regeneravel de scenario specs e fronteiras sandbox;
- a Sprint 3 foi concluida com `docs/archive/implementation/v2-governed-benchmark-decisions.md` como decisao formal por tecnologia e racional curto contra o baseline do JARVIS;
- a Sprint 4 do corte anterior foi concluida com `docs/archive/implementation/v2-governed-benchmark-execution-cut-closure.md` como fechamento humano do recorte e `tools/archive/close_governed_benchmark_execution_cut.py` como fechador regeneravel;
- a Sprint 4 do `v2-native-memory-scope-hardening-cut` foi concluida com fechamento formal regeneravel em `docs/archive/implementation/v2-native-memory-scope-hardening-cut-closure.md`;
- o recorte estrutural `v2-repository-hygiene-and-tools-review-cut` foi concluido com limpeza segura da superficie ativa de `docs/` e `tools/`;
- a Sprint 1 desse corte foi concluida com inventario regeneravel em `docs/archive/implementation/v2-repository-hygiene-inventory.md`;
- a Sprint 2 desse corte foi concluida com decisao regeneravel de classificacao dos docs ativos em `docs/archive/implementation/v2-repository-hygiene-doc-decisions.md`;
- a Sprint 3 desse corte foi concluida com decisao regeneravel de classificacao dos entrypoints da raiz de `tools/` em `docs/archive/implementation/v2-repository-hygiene-tool-decisions.md`;
- a Sprint 4 desse corte foi concluida com migracao dos `archive candidates` e fechamento formal em `docs/archive/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md`;
- a proxima frente imediata passa a ser a selecao disciplinada do proximo recorte funcional, sem reabrir ruido estrutural.
- a camada de revisao profunda de repositorio para tecnologias externas foi formalizada em `docs/architecture/technology-repository-review-framework.md`, com primeira aplicacao em `docs/architecture/mem0-repository-review.md`; ela apoia decisao arquitetural, mas nao altera a prioridade funcional do backlog.
