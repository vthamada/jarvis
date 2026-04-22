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
| `resolved_in_baseline` | ja foi absorvido em lote micro concluido e agora faz parte do baseline |
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
- a fila micro ja fechou `SG-006`, `EV-002` e `EV-004` como baseline
  comparativo controlado, e o novo lote micro foi reaberto em cima de `EV-003`;
- o proximo passo correto nao e reabrir lote encerrado nem abrir vertical nova
  por impulso;
- a puxada atual precisa manter compile/optimize loops subordinados a traces,
  metricas, gates e bloqueios de seguranca, sem autoedicao solta do nucleo.

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
| `SG-002` | modelo de estado operacional do ecossistema | `orchestrator`, memoria, continuidade | `ponte v2 -> v3` | `LangGraph`, `Mastra`, `Manus` | `onda_3_tardia` | `candidate_for_slicing` | `sim` |
| `SG-003` | continuidade multissuperficie da mesma entidade | identidade, continuidade, surfaces | `ponte v2 -> v3` | `OpenClaw`, `OpenAI Agents SDK` | `onda_3_tardia` | `blocked_by_phase` | `nao` |
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
- `SG-003`: falta um contrato formal para chat, console, voz, web e API
  exporem a mesma entidade com continuidade compartilhada, sem bifurcar
  identidade.
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
| `TA-002` | durable execution, resumabilidade e subfluxos stateful mais profundos | `SG-002` | `ponte v2 -> v3` | `LangGraph`, `Mastra` | `onda_1_residual` | `candidate_for_slicing` | `sim` |
| `TA-003` | compaction de contexto e recall cross-session 2.0 | `SG-004` | `v2 restante` | `Letta`, `Hermes Agent`, `Qwen-Agent` | `onda_1_residual` | `resolved_in_baseline` | `sim` |
| `TA-004` | memoria temporal, relacional e scoping mais rico | `SG-002`, `SG-004` | `ponte v2 -> v3` | `Graphiti`, `Zep`, `Mem0` | `onda_2_controlada` | `blocked_by_phase` | `nao` |
| `TA-005` | handoffs, tracing e session adapters por borda de fluxo | `SG-001`, `SG-003`, `SG-006`, `EV-002` | `v2 restante` | `OpenAI Agents SDK` | `onda_2_controlada` | `resolved_in_baseline` | `sim` |
| `TA-006` | substrate operacional para especialistas de software, browser e computer use | `SO-002`, `SO-003` | `ponte v2 -> v3` | `OpenHands`, `browser-use`, `Open Interpreter` | `onda_2_controlada` | `blocked_by_phase` | `nao` |
| `TA-007` | gateway multicanal, lifecycle de skills e runtime operacional local-first | `SG-003`, `SO-001`, `SO-002` | `v3` | `OpenClaw` | `onda_3_tardia` | `deferred` | `nao` |
| `TA-008` | compressao inferencial e retrieval vetorial para contexto longo e escala futura | `SG-002`, `SO-001`, `EV-004` | `ponte v2 -> v3` | `TurboQuant`, `pgvector` (futuro consumidor), `OpenAI Realtime / Voice` | `onda_2_controlada` | `blocked_by_phase` | `nao` |

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

### 5.3 Surfaces and operation

| ID | Frente ainda faltante | Camada JARVIS | Fase alvo | Tecnologias relacionadas | Janela de absorcao | Status | Slice micro |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `SO-001` | voz e realtime como superficie subordinada | interfaces, identidade, continuidade | `v3` | `OpenClaw` como referencia tardia | `onda_3_tardia` | `deferred` | `nao` |
| `SO-002` | contrato multissuperficie entre console, web, API e futuras interfaces | gateway, identidade, runtime operacional | `ponte v2 -> v3` | `OpenAI Agents SDK`, `OpenClaw` | `onda_3_tardia` | `blocked_by_phase` | `nao` |
| `SO-003` | projetos persistentes, tarefas assincronas longas e artefatos ativos | estado operacional do ecossistema | `v3` | `Manus`, `LangGraph`, `Mastra` | `onda_3_tardia` | `deferred` | `nao` |

Notas de leitura:

- nenhuma dessas frentes deve liderar a arquitetura antes de o nucleo abrir a
  fase correta;
- quando essas frentes subirem, devem expor a mesma entidade soberana, nao
  runtimes paralelos.

### 5.4 Evolution and benchmark

| ID | Frente ainda faltante | Camada JARVIS | Fase alvo | Tecnologias relacionadas | Janela de absorcao | Status | Slice micro |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `EV-001` | repriorizacao explicita do proximo lote micro a partir deste mapa unificado | governanca de execucao | `agora` | `nenhuma` | `nao_aplicavel` | `candidate_for_slicing` | `sim` |
| `EV-002` | expandir evals e sinais para capacidade, superficie e estado do ecossistema | `observability`, `evolution-lab`, gates | `v2 restante` | `DSPy`, `OpenAI Agents SDK`, `Mastra` | `onda_2_controlada` | `resolved_in_baseline` | `sim` |
| `EV-003` | compile e optimize loops governados para prompts, planos e workflows | `evolution-lab` | `v2 restante` | `DSPy/MIPROv2`, `TextGrad`, `AFlow`, `EvoAgentX` | `onda_1_residual` | `resolved_in_baseline` | `sim` |
| `EV-004` | lane controlada de experimentos da Onda 2 com criterio de entrada e saida | comparadores, laboratorio, gates | `v2 restante` | `OpenAI Agents SDK`, `Qwen-Agent`, `Graphiti`, `Mem0`, `OpenHands`, `browser-use` | `onda_2_controlada` | `resolved_in_baseline` | `sim` |

Notas de leitura:

- `EV-001` e o primeiro passo operacional, nao uma frente tecnica longa.
- `EV-002` impede que capacidades novas entrem sem leitura causal suficiente.
- `EV-003` deve continuar governado por datasets, traces e metricas, sem
  autoedicao solta de producao.
- `EV-004` existe para impedir que a Onda 2 vire hype ou backlog disperso.

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

1. escolher um `SG` ou `EV` em `candidate_for_slicing` que aumente profundidade
   do nucleo;
2. conectar esse item a um ou dois `TA` que traduzam apenas o padrao externo
   necessario;
3. abrir um lote micro curto, reversivel e auditavel em
   `docs/implementation/execution-backlog.md`;
4. manter `SO`, `DV` e `RH` fora da fila micro, salvo mudanca explicita de
   fase.

Ordem recomendada hoje:

1. `SG-002` + `TA-002`
2. `SG-003` + `SO-002`

Leitura correta:

- `SG-001`, `SG-004`, `SG-005`, `SG-006`, `TA-001`, `TA-003`, `TA-005`,
  `EV-002` e `EV-004` ja foram traduzidos em lotes micro concluidos e agora
  pertencem ao baseline, nao a proxima puxada;
- `EV-003` ja foi corretamente fatiado e concluido no backlog micro como o
  lote `MB-092` a `MB-096`, passando a fazer parte do baseline evolutivo
  governado;
- a repriorizacao explicita seguinte pode abrir a ponte `v2 -> v3` em cima de
  `SG-002` + `TA-002`, desde que o recorte continue pequeno, reversivel e
  auditavel, sem puxar ainda memoria temporal rica, multissuperficie ou
  substrate operacional amplo;
- `SG-002`, `SG-003`, `TA-002`, `TA-004`, `SO-*` e `DV-001` ja sao
  relevantes, mas ainda nao sao a melhor puxada do `v2` atual;
- depois de abrir `SG-002` + `TA-002`, `SG-003` e `SO-002` passam a depender
  da existencia de um estado operacional do ecossistema minimamente soberano;
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
