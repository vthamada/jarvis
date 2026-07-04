# Unified Gap and Absorption Backlog

## 1. Objetivo

Este documento mapeia, em um unico backlog macro, o que ainda falta para o
JARVIS alem da fila micro corrente.

Ele existe para:

- consolidar gaps reais do sistema, traducao tecnologica, superficies,
  operacao, evolucao e pesquisa;
- ligar o que ainda falta no runtime ao que pode ou nao pode ser absorvido do
  ecossistema;
- evitar que a proxima repriorizacao nasca apenas de intuicao local;
- servir como ponte entre a direcao macro e a proxima fila micro.

Ele nao substitui:

- `documento_mestre_jarvis.md`
- `docs/roadmap/programa-ate-v3.md`
- `docs/implementation/v2-adherence-snapshot.md`
- `docs/architecture/technology-absorption-order.md`
- `docs/implementation/execution-backlog.md`

Leitura correta:

- o `execution-backlog` continua como unica fila micro ativa;
- este arquivo organiza o backlog macro do que ainda falta;
- nenhum item daqui vira `ready` automaticamente;
- toda puxada continua exigindo recorte pequeno, criterio de aceite e gate
  minimo no backlog micro.

---

## 2. Papel no sistema de planejamento

Hierarquia correta:

- `documento_mestre_jarvis.md`: visao canonica e ontologia;
- `docs/roadmap/programa-ate-v3.md`: fases e dependencias do programa;
- `docs/implementation/v2-adherence-snapshot.md`: leitura viva do baseline
  atual;
- `docs/architecture/technology-absorption-order.md`: ordem oficial de
  traducao/absorcao;
- este arquivo: mapa unificado do que ainda falta;
- `docs/implementation/execution-backlog.md`: fila micro executavel;
- `HANDOFF.md`: retomada tatico-operacional.

---

## 3. Como ler

### 3.1 Prefixos

| Prefixo | Uso correto |
| --- | --- |
| `SG` | `system gap`: lacuna real do nucleo ou do runtime |
| `TA` | `technology absorption`: traducao disciplinada de padroes externos |
| `SO` | `surface/operation`: superficies, canais e operacao ampla |
| `EV` | `evolution/benchmark`: evidencia, evals e melhoria governada |
| `DV` | `deferred vertical`: frente valida, mas fora da fila atual |
| `RH` | `research horizon`: horizonte de pesquisa, nao backlog implementavel |

### 3.2 Status macro

| Status | Uso correto |
| --- | --- |
| `candidate_for_slicing` | pode virar lote micro quando houver repriorizacao explicita |
| `active_micro_slice` | ja virou fila micro ativa, mas ainda nao foi fechado como baseline |
| `resolved_in_baseline` | ja foi absorvido em lote micro concluido e agora faz parte do baseline |
| `resolved_minimum_baseline` | ponte minima ja absorvida, mas produto/canal amplo continua fora de fase |
| `blocked_by_phase` | valido, mas ainda depende de fase ou dependencia macro |
| `deferred` | mapeado, mas explicitamente fora do foco atual |
| `research_only` | radar de pesquisa ou laboratorio, nao fila de implementacao |

### 3.3 Janela de absorcao

| Valor | Significado |
| --- | --- |
| `nao_aplicavel` | gap interno, sem dependencia direta de absorcao externa |
| `onda_1_residual` | traducao restante de referencias ja priorizadas |
| `onda_2_controlada` | complemento controlado, guiado por readiness |
| `onda_3_tardia` | produto, gateway e superficies so depois do nucleo mais maduro |
| `onda_4_pesquisa` | horizonte de pesquisa |

---

## 4. Leitura executiva do estado atual

- o baseline do `v2` ja fechou os lotes `MB-067` a `MB-081`, cobrindo decisao
  soberana de capacidades, manutencao ativa de memoria viva e arbitragem
  declarativa `mente -> dominio -> especialista`;
- a fila micro ja fechou `SG-006`, `EV-002`, `EV-004`, `EV-003` e o recorte
  bounded de `SG-002` + `TA-002` como baseline operacional auditavel;
- o proximo passo correto nao e reabrir lote encerrado nem abrir vertical nova
  por impulso;
- a fila micro foi reaberta em cima de `SG-003` + `SO-002`, e o lote completo
  (`MB-102` a `MB-106`) ja fechou contrato minimo de identidade por
  superficie, propagacao pelo runtime atual e persistencia bounded de
  continuidade, alem da leitura auditavel dessa continuidade em observabilidade,
  piloto, comparadores, baseline ativo, `evolution-lab`, release e docs vivos;
- a repriorizacao `EV-001` foi fechada em `MB-107` a `MB-109`, escolhendo
  `SO-003` apenas como fundacao minima de continuidade de projetos/objetivos;
- a fila micro `MB-110` a `MB-114` foi fechada e absorveu o recorte minimo de
  projetos/objetivos persistentes no runtime, memoria, replay, eventos,
  observabilidade, piloto e comparadores;
- a fila micro `MB-115` a `MB-119` foi aberta para transformar esse recorte em
  utilidade operacional para o operador; `MB-115` ja expoe estado de objetivo
  no console em modo somente leitura, `MB-116` ja permite transicoes bounded
  governadas de objetivo, `MB-117` ja leva esse estado para a sintese final,
  `MB-118` ja mede sinais de utilidade operacional e `MB-119` fechou docs e
  gates desse lote;
- a repriorizacao pos-`MB-119` foi aberta em `MB-120` e escolheu estrutura
  evolutiva + absorcao tecnologica governada como proxima frente; `MB-121` ja
  criou contrato soberano minimo para candidatos tecnologicos e bloqueia
  qualquer tentativa de tecnologia externa assumir papel de nucleo; `MB-122`
  conectou esse contrato ao `evolution-lab` como proposta `sandbox-only`;
  `MB-123` a `MB-125` fecharam observabilidade, leitura operacional no console e
  docs vivos desse recorte;
- a repriorizacao pos-`MB-125` foi aberta em `MB-126` e escolheu experiencia
  operacional + reflexao pos-tarefa governada como proxima frente; o objetivo
  e transformar missoes reais em materia-prima auditavel de evolucao, ainda sem
  autoedicao, autopromocao, scheduler autonomo ou memoria temporal relacional
  rica;
- `MB-127` a `MB-131` fecharam esse recorte: contratos, memoria evolutiva
  bounded, propostas `sandbox-only`, observabilidade, relatorio e console
  read-only agora tratam reflexao pos-tarefa como baseline governado;
- a repriorizacao pos-`MB-131` foi aberta em `MB-132` e escolheu o
  `Operator Learning Loop` como proxima frente: o foco agora e fechar o ciclo
  real `usar -> registrar -> refletir -> propor -> revisar -> medir`, fazendo
  missoes governadas gerarem experiencia, reflexao, proposta evolutiva,
  revisao humana e medicao de ganho sem autopromocao;
- `MB-133` fechou o primeiro passo tecnico desse loop: missoes/requests
  governados agora geram `experience_record` automatico no `orchestrator-service`
  e persistido pelo `memory-service`, ainda sem gerar reflexao automatica;
- `MB-134` fechou o segundo passo tecnico: cada experiencia automatica agora
  gera `post_task_reflection` bounded e persistida, sem autopromocao, sem
  mutacao de nucleo e sem influencia causal ainda;
- `MB-135` fechou a primeira influencia causal bounded: reflexoes relevantes
  agora podem influenciar planejamento e sintese quando batem por workflow,
  rota e dominio, com refs auditaveis e sem promocao automatica;
- `MB-136` criou a fila humana read-only de revisao evolutiva sobre propostas
  sandbox, com estados, blockers, testes e rollback visiveis ao operador;
- `MB-137` adicionou eval/piloto baseline vs reflection-assisted em
  observabilidade, relatorio e comparador, sem autopromocao;
- `MB-138` expos o ciclo no console por `mission-cycle`, agregando missao,
  objetivo, experiencia, reflexao, proposta evolutiva e revisao em modo
  read-only;
- `MB-139` adicionou `mission-workflow`, demonstrando execucao governada,
  experiencia/reflexao automatica, proposta sandbox e revisao humana pendente;
- `MB-140` fechou a documentacao operacional do loop em
  `docs/operations/operator-learning-loop.md`;
- `MB-141` a `MB-145` fecharam `EV-008`: o operador agora pode aprovar,
  rejeitar, sandboxar, devolver proposta para revisao ou rollbackar proposta
  evolutiva com contrato, evidencia, testes, rollback, observabilidade e
  bloqueio explicito de autopromocao;
- a repriorizacao pos-`MB-145` abre `EV-009` como feedback de aprendizado
  revisado: decisoes humanas aprovadas ou sandboxadas podem virar guidance
  bounded, filtrado e mensuravel para planejamento/sintese, sem autopromocao;
- o proximo passo nao e abrir produto multicanal ou automacao ampla
  automaticamente; a fila atual existe para criar continuidade operacional
  governada antes de qualquer autonomia mais forte;
- voz/realtime, memoria temporal rica, produto multicanal, scheduler autonomo
  e substrate operacional amplo continuam fora de fase.

Regra pratica daqui para frente:

- primeiro puxar o que aumenta profundidade do nucleo;
- depois puxar traducao residual da Onda 1 e experimentos pequenos da Onda 2;
- deixar superficies amplas, gateway multicanal e vertical de produto para
  depois;
- manter autoevolucao forte e auto-modificacao como pesquisa.

Leitura de horizonte:

- esse backlog macro continua subordinado ao objetivo maior de construir uma
  entidade soberana, ampla e autoevolutiva;
- a contencao atual de autoevolucao forte e de superficies amplas e disciplina
  de fase, nao recuo de visao.

---

## 5. Backlog unificado do que ainda falta

### 5.1 System gaps

| ID | Gap real | Camada JARVIS | Fase alvo | Tecnologias relacionadas | Janela de absorcao | Status | Slice micro |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `SG-001` | decisao soberana de capacidades e ferramentas | nucleo executivo, governanca, dispatch | `v2 restante` | `PydanticAI`, `Mastra`, `OpenAI Agents SDK`, `Qwen-Agent` | `onda_2_controlada` | `resolved_in_baseline` | `sim` |
| `SG-002` | modelo de estado operacional do ecossistema | `orchestrator`, memoria, continuidade | `ponte v2 -> v3` | `LangGraph`, `Mastra`, `Manus` | `onda_3_tardia` | `resolved_in_baseline` | `sim` |
| `SG-003` | continuidade multissuperficie da mesma entidade | identidade, continuidade, surfaces | `ponte v2 -> v3` | `OpenClaw`, `OpenAI Agents SDK` | `onda_3_tardia` | `resolved_minimum_baseline` | `sim` |
| `SG-004` | manutencao ativa de memoria viva e memory review | `memory-service`, `memory_registry` | `v2 restante` | `Letta`, `Hermes Agent`, `Qwen-Agent` | `onda_1_residual` | `resolved_in_baseline` | `sim` |
| `SG-005` | arbitragem mais declarativa de `mente -> dominio -> especialista` nos consumidores finais | cognicao, `planning`, `synthesis`, observabilidade | `v2 restante` | `Mastra`, `PydanticAI` | `nao_aplicavel` | `resolved_in_baseline` | `sim` |
| `SG-006` | identidade, missao e politica como checklist executiva por request | identidade, nucleo executivo, governanca | `v2 restante` | `PydanticAI`, `Mastra`, `OpenAI Agents SDK` | `onda_2_controlada` | `resolved_in_baseline` | `sim` |

Notas de traducao por gap:

- `SG-001`: falta transformar a decisao de ferramenta/capacidade em contrato
  explicito do runtime, com elegibilidade, autorizacao, roteamento e
  observabilidade soberanos, sem deixar a escolha como improviso da LLM.
- `SG-002`: falta modelar de forma mais rica workflows ativos, artefatos,
  checkpoints, superficies, integracoes e pendencias como estado operacional do
  ecossistema, e nao apenas contexto de conversa ou missao.
- `SG-003`: o contrato minimo ja existe para identidade de superficie,
  propagacao, continuidade bounded e auditoria; ainda nao significa voz, web,
  API publica ou gateway multicanal amplo.
- `SG-004`: o lifecycle de memoria ja amadureceu, mas ainda falta manutencao
  ativa mais forte: consolidacao, review, compactacao, expiracao disciplinada e
  reuso governado ao longo do tempo.
- `SG-005`: a cadeia `mente -> dominio -> especialista` ja ficou mais
  evidence-first, mas ainda pode virar criterio mais declarativo de acao,
  saida, validacao e delegacao.
- `SG-006`: o runtime agora ja materializa `request_identity_policy` como
  preflight executiva por request para missao ativa, autoridade, risco,
  reversibilidade, confirmacao e governanca; o que resta daqui em diante e uso
  evolutivo e comparativo mais amplo desses sinais, nao falta de contrato
  basico.

### 5.2 Technology absorption backlog

| ID | Traducao disciplinada ainda faltante | Fortalece | Fase alvo | Tecnologias relacionadas | Janela de absorcao | Status | Slice micro |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `TA-001` | contratos tipados de capacidade e workflow alem do plano deliberativo atual | `SG-001`, `SG-005`, `SG-006` | `v2 restante` | `PydanticAI`, `Mastra`, `Microsoft Agent Framework` | `onda_1_residual` | `resolved_in_baseline` | `sim` |
| `TA-002` | durable execution, resumabilidade e subfluxos stateful mais profundos | `SG-002` | `ponte v2 -> v3` | `LangGraph`, `Mastra` | `onda_1_residual` | `resolved_in_baseline` | `sim` |
| `TA-003` | compaction de contexto e recall cross-session 2.0 | `SG-004` | `v2 restante` | `Letta`, `Hermes Agent`, `Qwen-Agent` | `onda_1_residual` | `resolved_in_baseline` | `sim` |
| `TA-004` | memoria temporal, relacional e scoping mais rico | `SG-002`, `SG-004` | `ponte v2 -> v3` | `Graphiti`, `Zep`, `Mem0` | `onda_2_controlada` | `blocked_by_phase` | `nao` |
| `TA-005` | handoffs, tracing e session adapters por borda de fluxo | `SG-001`, `SG-003`, `SG-006`, `EV-002` | `v2 restante` | `OpenAI Agents SDK` | `onda_2_controlada` | `resolved_in_baseline` | `sim` |
| `TA-006` | substrate operacional para especialistas de software, browser e computer use | `SO-002`, `SO-003` | `ponte v2 -> v3` | `OpenHands`, `browser-use`, `Open Interpreter` | `onda_2_controlada` | `blocked_by_phase` | `nao` |
| `TA-007` | gateway multicanal, lifecycle de skills e runtime operacional local-first | `SG-003`, `SO-001`, `SO-002` | `v3` | `OpenClaw` | `onda_3_tardia` | `deferred` | `nao` |
| `TA-008` | compressao inferencial e retrieval vetorial para contexto longo e escala futura | `SG-002`, `SO-001`, `EV-004` | `ponte v2 -> v3` | `TurboQuant`, `pgvector` (futuro consumidor), `OpenAI Realtime / Voice` | `onda_2_controlada` | `blocked_by_phase` | `nao` |
| `TA-009` | contrato soberano de candidatos tecnologicos com evidencia, sandbox, rollback e promocao manual | `EV-001`, `EV-003`, `EV-004` | `v2 restante` | todas as ondas de absorcao | `onda_1_residual` | `resolved_in_baseline` | `sim` |

Notas de leitura:

- `TA-001` nao significa trocar a gramatica do JARVIS por API externa;
  significa traduzir o melhor de tipagem, validacao e snapshot para contratos
  soberanos.
- `TA-002` nao abre migracao ampla para runtime externo; significa aprofundar
  durable execution apenas onde houver consumidor canonico claro.
- `TA-003` e o principal prolongamento tecnicamente natural da Onda 1 depois do
  que ja foi absorvido em contexto vivo, recall cross-session e lifecycle
  basico.
- `TA-004` so deve subir quando o proprio JARVIS provar falta real de memoria
  temporal ou relacional mais rica.
- `TA-005` e util para bordas de fluxo, nao para terceirizar memoria canonica,
  identidade ou soberania.
- `TA-006` so faz sentido quando a camada operacional e de especialistas pedir
  substratos mais fortes sem deslocar a relacao soberana com o usuario.
- `TA-007` e referencia tardia de gateway e runtime operacional, nao base atual
  do sistema.
- `TA-008` so sobe quando houver pressao real de `KV cache`, `long-context`,
  `voice/realtime` ou retrieval vetorial alem do que o baseline atual pede;
  ate la, `TurboQuant` fica como referencia forte de infraestrutura, nao como
  frente micro.
- `TA-009` e a ponte operacional para absorcao continua do estado da arte:
  primeiro classifica candidatos como referencia, experimento, complemento ou
  traducao promovivel; promocao continua manual, com evidencia, testes e
  rollback.

### 5.3 Surfaces and operation

| ID | Frente ainda faltante | Camada JARVIS | Fase alvo | Tecnologias relacionadas | Janela de absorcao | Status | Slice micro |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `SO-001` | voz e realtime como superficie subordinada | interfaces, identidade, continuidade | `v3` | `OpenClaw` como referencia tardia | `onda_3_tardia` | `deferred` | `nao` |
| `SO-002` | contrato multissuperficie entre console, web, API e futuras interfaces | gateway, identidade, runtime operacional | `ponte v2 -> v3` | `OpenAI Agents SDK`, `OpenClaw` | `onda_3_tardia` | `resolved_minimum_baseline` | `sim` |
| `SO-003` | projetos persistentes, tarefas assincronas longas e artefatos ativos | estado operacional do ecossistema | `v3` | `Manus`, `LangGraph`, `Mastra` | `onda_3_tardia` | `resolved_minimum_baseline` | `sim` |

Notas de leitura:

- nenhuma dessas frentes deve liderar a arquitetura antes de o nucleo abrir a
  fase correta;
- quando essas frentes subirem, devem expor a mesma entidade soberana, nao
  runtimes paralelos.

### 5.4 Evolution and benchmark

| ID | Frente ainda faltante | Camada JARVIS | Fase alvo | Tecnologias relacionadas | Janela de absorcao | Status | Slice micro |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `EV-001` | repriorizacao explicita do proximo lote micro a partir deste mapa unificado | governanca de execucao | `agora` | `nenhuma` | `nao_aplicavel` | `resolved_in_baseline` | `sim` |
| `EV-002` | expandir evals e sinais para capacidade, superficie e estado do ecossistema | `observability`, `evolution-lab`, gates | `v2 restante` | `DSPy`, `OpenAI Agents SDK`, `Mastra` | `onda_2_controlada` | `resolved_in_baseline` | `sim` |
| `EV-003` | compile e optimize loops governados para prompts, planos e workflows | `evolution-lab` | `v2 restante` | `DSPy/MIPROv2`, `TextGrad`, `AFlow`, `EvoAgentX` | `onda_1_residual` | `resolved_in_baseline` | `sim` |
| `EV-004` | lane controlada de experimentos da Onda 2 com criterio de entrada e saida | comparadores, laboratorio, gates | `v2 restante` | `OpenAI Agents SDK`, `Qwen-Agent`, `Graphiti`, `Mem0`, `OpenHands`, `browser-use` | `onda_2_controlada` | `resolved_in_baseline` | `sim` |
| `EV-005` | loop de absorcao tecnologica governada como candidato persistido, observado e operavel | contratos, `evolution-lab`, observabilidade, console | `v2 restante` | todas as ondas, com prioridade para Onda 1 residual e Onda 2 controlada | `onda_1_residual` | `resolved_in_baseline` | `sim` |
| `EV-006` | experiencia operacional e reflexao pos-tarefa como materia-prima governada de evolucao | contratos, memoria evolutiva, `evolution-lab`, observabilidade, console | `v2 restante` | padroes de self-evolving agents e continual learning traduzidos sem self-modification | `onda_1_residual` | `resolved_in_baseline` | `sim` |
| `EV-007` | Operator Learning Loop como ciclo real de uso humano e aprendizado governado | `orchestrator`, memoria evolutiva, `evolution-lab`, console, evals | `v2 restante` | padroes de lifelong learning e reflection-assisted agents traduzidos como fluxo auditavel | `onda_1_residual` | `resolved_in_baseline` | `sim` |
| `EV-008` | controles humanos de revisao evolutiva para fechar propostas pendentes | `evolution-lab`, console, observabilidade, docs | `v2 restante` | padroes de human-in-the-loop governance e release gates traduzidos como decisao auditavel | `onda_1_residual` | `resolved_in_baseline` | `sim` |
| `EV-009` | feedback de aprendizado revisado influenciando decisoes futuras de forma bounded | contratos, `orchestrator`, planning, synthesis, observabilidade, console | `v2 restante` | padroes de learning feedback loops e human-reviewed memory traduzidos como guidance auditavel | `onda_1_residual` | `resolved_in_baseline` | `sim` |

Notas de leitura:

- `EV-001` e o primeiro passo operacional, nao uma frente tecnica longa.
- `EV-002` impede que capacidades novas entrem sem leitura causal suficiente.
- `EV-003` deve continuar governado por datasets, traces e metricas, sem
  autoedicao solta de producao.
- `EV-004` existe para impedir que a Onda 2 vire hype ou backlog disperso.
- `EV-005` impede que a absorcao tecnologica viva apenas em docs: candidatos
  devem ter contrato, laboratorio, evidencia, observabilidade e leitura humana
  antes de qualquer promocao.
- `EV-006` e o proximo passo da estrutura evolutiva: registrar experiencia,
  refletir sobre outcome/falhas, propor melhorias sandbox-only e expor tudo ao
  operador antes de qualquer mudanca no runtime.
- `EV-007` fecha o ciclo operacional em torno do humano: usar, registrar,
  refletir, propor, revisar e medir. Ele nao abre voz, realtime, UI rica,
  scheduler autonomo, browser/computer use amplo ou autoevolucao profunda.
- `EV-008` transformou revisao pendente em decisao humana auditavel, mantendo
  promocao automatica e mutacao de nucleo bloqueadas.
- `EV-009` e o proximo passo correto apos a decisao humana: aplicar somente
  aprendizados revisados, relevantes e bounded como guidance, medir impacto e
  continuar bloqueando qualquer promocao sem release gate.
- `MB-147` formalizou o contrato desse guidance, `MB-148` conectou sua
  influencia runtime em memoria, planning e synthesis, e `MB-149`/`MB-150`
  fecharam medicao comparativa e leitura operacional; `EV-009` agora faz parte
  do baseline resolvido, sem autopromocao.
- `MB-151` foi fechado como auditoria documental governada oficial: ele
  transformou a repriorizacao pos-`MB-150` em inventario, classificacao,
  clusters, riscos e recomendacao de proximo recorte, sem executar limpeza
  documental ampla nem abrir nova funcionalidade.
- `MB-152` foi fechado no backlog micro: o mapa de backlinks dos 73 documentos
  auditados foi criado em
  `docs/documentation/documentation-backlink-map-mb152.md`, documentos ativos
  defasados foram sincronizados de forma limitada e nenhum movimento, delete,
  rename ou merge sensivel foi executado.
- `MB-153` foi fechado como archive fisico conservador: seis documentos
  historicos de implementacao foram movidos para
  `docs/archive/implementation/`, backlinks literais foram reescritos, nenhum
  documento foi deletado e nenhum merge destrutivo foi executado.
- `MB-154` foi fechado como `Implementation Master Map`: a visao de
  implementacao agora esta decomposta por trilhas de capacidade, status,
  dependencias, fases e proximos slices em
  `docs/implementation/implementation-master-map.md`.
- `MB-155` foi fechado como baseline minimo de dashboard textual do operador:
  o console agora agrega missao, objetivo, work items, checkpoints, artefatos,
  experiencia/reflexao, fila evolutiva e aprendizado revisado em modo read-only.
- `MB-156` foi fechado como ciclo governado minimo de work items: o operador
  pode criar, consultar, pausar, bloquear, concluir e redefinir proxima acao de
  work item por console, com governanca, memoria canonica e eventos auditaveis.
- `MB-157` foi fechado como lifecycle minimo de artefatos vivos: o operador
  pode registrar, consultar, ativar, arquivar, substituir e rollbackar refs de
  artefato bounded sem mutacao fisica de arquivos.
- `MB-158` foi fechado como metricas compactas de utilidade operacional:
  observabilidade e dashboard agora expoem status, score e sinais de utilidade
  do operador sem promover aprendizado ou release automaticamente.
- `MB-159` foi fechado como raciocinio minimo de objetivos de horizonte longo:
  estrategia read-only deriva de estado de missao, work items, artefatos,
  checkpoints, anchors de memoria e proxima acao auditavel, sem scheduler
  autonomo.
- `MB-160` foi fechado como repriorizacao pos-`MB-159` a partir do
  `implementation-master-map`, abrindo uma fila maior `MB-161` a `MB-174`;
  `MB-161` foi fechado como anchors de evidencia de memoria semantica;
  `MB-162` foi fechado como candidatos bounded de playbook procedural;
  `MB-163` e o unico item tecnico `ready` e `MB-164` a `MB-174` permanecem
  bloqueados por dependencia/ordem.

### 5.5 Deferred verticals already mapped

| ID | Frente mapeada | Papel correto | Fase alvo | Status |
| --- | --- | --- | --- | --- |
| `DV-001` | `protective intelligence foundation` | vertical valida, mas fora da fila ativa enquanto o nucleo ainda extrai profundidade do baseline atual | `ponte v2 -> v3` | `deferred` |

Regra:

- `DV-001` so deve reabrir quando houver repriorizacao macro explicita e
  consumidor soberano claro;
- ele nao disputa a proxima rodada micro por inercia.

### 5.6 Research horizon

| ID | Horizonte | Papel correto | Fase alvo | Tecnologias relacionadas | Janela de absorcao | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `RH-001` | autoevolucao forte, self-modification governada e adaptacao persistente do nucleo | horizonte estrutural oficial do sistema, mantido em pesquisa e laboratorio ate maturidade suficiente | `pos-v3` | `SEAL`, `Darwin Godel Machine` | `onda_4_pesquisa` | `research_only` |
| `RH-002` | agent platform ampla, multicanal rica e autonomia de produto | referencia de longo prazo, nao fila atual | `v3+` | `Manus`, `OpenClaw`, `AutoGPT Platform` | `onda_3_tardia` | `research_only` |

---

## 6. Ordem recomendada para derivar a proxima fila micro

Quando o `execution-backlog` estiver sem item `ready`, a puxada correta passa a
ser:

1. consultar `docs/implementation/implementation-master-map.md` para escolher
   uma capacidade e sua dependencia correta;
2. confirmar se a capacidade deriva de `SG`, `TA`, `SO`, `EV`, `DV` ou `RH`
   sem violar fase;
3. conectar esse item a um ou dois `TA` somente quando houver padrao externo
   necessario;
4. abrir um lote micro curto, reversivel e auditavel em
   `docs/implementation/execution-backlog.md`;
5. manter `SO`, `DV` e `RH` fora da fila micro, salvo mudanca explicita de
   fase.

Ordem recomendada hoje:

1. tratar `MB-110` a `MB-159` como baseline fechado de objetivos persistentes,
   utilidade operacional, absorcao tecnologica governada, aprendizado revisado,
   higiene documental e horizonte longo minimo.
2. executar `MB-163` como proximo item tecnico da fila maior pos-`MB-160`.
3. manter `SO-001`, `TA-004`, `TA-006` e verticais `deferred` fora da fila ate
   haver decisao explicita de fase.

Leitura correta:

- `SG-001`, `SG-004`, `SG-005`, `SG-006`, `TA-001`, `TA-003`, `TA-005`,
  `EV-002` e `EV-004` ja foram traduzidos em lotes micro concluidos e agora
  pertencem ao baseline, nao a proxima puxada;
- `EV-003` ja foi corretamente fatiado e concluido no backlog micro como o
  lote `MB-092` a `MB-096`, passando a fazer parte do baseline evolutivo
  governado;
- `SG-002` + `TA-002` ja foram fatiados e concluidos no lote `MB-097` a
  `MB-101`, criando estado operacional bounded, auditavel e regeneravel do
  ecossistema;
- `SG-003` + `SO-002` agora foram repriorizados e concluidos como lote micro
  `MB-102` a `MB-106`; o baseline materializou contrato minimo, propagacao,
  persistencia bounded, auditoria/readiness e fechamento documental da
  continuidade da mesma entidade;
- `EV-001` foi fechado como fila micro `MB-107` a `MB-109`, escolhendo
  `SO-003` como recorte minimo de continuidade de projetos/objetivos;
- `SO-003` agora tem baseline minimo concluido em `MB-110` a `MB-114`,
  limitado a contratos, propagacao runtime, persistencia bounded,
  auditoria/readiness e fechamento documental;
- `EV-005` agora tem baseline concluido em `MB-120` a `MB-125`, limitado a
  contrato soberano, `evolution-lab`, observabilidade, relatorio, comparador e
  console read-only de candidatos tecnologicos;
- `EV-006` foi concluido em `MB-126` a `MB-131`, com escopo estrito de
  experiencia/reflexao pos-tarefa e sem self-modification forte;
- `EV-007` foi fatiado em `MB-132` a `MB-140`; `MB-133` ja automatizou
  `experience_record` no fluxo real, `MB-134` ja automatizou
  `post_task_reflection` bounded, `MB-135` ja adicionou influencia governada em
  planejamento/sintese, `MB-136` ja criou a fila humana read-only de revisao
  evolutiva, `MB-137` ja adicionou eval/piloto baseline vs reflection-assisted,
  `MB-138` ja expos o ciclo no console e `MB-139` ja adicionou workflow pratico
  ponta a ponta; `MB-140` ja fechou a documentacao operacional, sem novo item
  tecnico `ready` automatico;
- `TA-004`, `TA-006` e `DV-001` continuam relevantes, mas ainda fora da fila
  sem mudanca explicita de fase;
- `EV-008` foi fechado como lote `MB-141` a `MB-145`; nao ha novo item tecnico
  `ready` sem repriorizacao explicita;
- `EV-009` foi fechado como lote `MB-146` a `MB-150`; nao ha novo item tecnico
  `ready` sem repriorizacao explicita;
- `MB-151` foi fechado como auditoria/repriorizacao documental, nao como lote
  tecnico de implementacao funcional;
- `MB-152` foi fechado como mapa de backlinks e sincronizacao segura de
  documentos ativos defasados;
- `MB-153` foi fechado como primeiro archive fisico conservador de documentos
  historicos de implementacao;
- `MB-154` foi fechado como mapa mestre completo de implementacao;
- `MB-155` foi fechado como dashboard textual minimo do operador, movendo
  `OP-006` para `minimum_baseline`;
- `MB-156` foi fechado como ciclo governado minimo de work items, movendo
  `OP-004` para `minimum_baseline`;
- `MB-157` foi fechado como lifecycle minimo de artefatos vivos, movendo
  `OP-005` e `ACT-004` para `minimum_baseline`;
- `MB-158` foi fechado como metricas compactas de utilidade operacional, movendo
  `OBS-005` para `minimum_baseline`;
- `MB-159` foi fechado como raciocinio minimo de objetivos de horizonte longo,
  movendo `COG-010` para um baseline minimo operacional;
- `MB-160` abriu a fila maior `MB-161` a `MB-174`, priorizando memoria causal,
  autonomia runtime, promocao governada, cockpit, feedback, dominios/evals,
  proveniencia e readiness; `MB-161` e `MB-162` foram fechados e `MB-163` e o
  unico item `ready`;
- `RH-*` permanece fora do backlog implementavel.

---

## 7. Regras de manutencao

- nenhum item daqui deve ser reescrito como "adotar tecnologia X";
- toda absorcao continua subordinada a identidade, memoria canonica,
  governanca, continuidade e sintese final do JARVIS;
- quando um item deste backlog virar lote micro, registrar o fatiamento
  correspondente no `execution-backlog`;
- quando uma fase mudar, revisar `fase_alvo`, `status` e `janela de absorcao`
  antes de abrir outra fila.

---

## 8. Referencias

- [documento_mestre_jarvis.md](../../documento_mestre_jarvis.md)
- [programa-ate-v3.md](../roadmap/programa-ate-v3.md)
- [v2-adherence-snapshot.md](./v2-adherence-snapshot.md)
- [execution-backlog.md](./execution-backlog.md)
- [technology-absorption-order.md](../architecture/technology-absorption-order.md)
- [technology-capability-extraction-map.md](../architecture/technology-capability-extraction-map.md)
- [technology-study.md](../architecture/technology-study.md)
- [HANDOFF.md](../../HANDOFF.md)
