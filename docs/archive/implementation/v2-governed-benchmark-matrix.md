# V2 Governed Benchmark Matrix

- corte: `v2-domain-consumers-and-workflows-cut`
- sprint: `sprint-3-governed-benchmarks`
- decisao: `complete_sprint_3_governed_benchmarks`

## Regras do benchmark governado

- regra central: nenhuma tecnologia externa entra no nucleo por benchmark isolado
- regra do corte ativo: benchmark_now significa comparar recorte governado sem promocao direta
- regra do envelope comparativo: reference_envelope significa tecnologia util para contraste, nao para entrada imediata

## Candidatas em benchmark agora

- `Mastra`
- `AutoGPT Platform`
- `Mem0`

## Quando `absorver_depois` pode subir

- a lacuna do JARVIS precisa estar comprovada no corte ativo, sem workaround excessivo no baseline
- o benchmark ou experimento precisa mostrar ganho real contra o baseline atual
- o ganho precisa vir sem romper domain_registry, memory_registry, mind_registry, governanca final ou sintese soberana
- a absorcao precisa caber no menor recorte util e reversivel
- HANDOFF.md e o documento do corte precisam passar a tratar a tecnologia como candidata de absorcao da fase

## Familias

### Workflow orchestration and typed execution

- lacuna do JARVIS: expandir workflows compostos acima do nucleo soberano sem terceirizar o orquestrador
- objetivo do benchmark: comparar runtime tipado, pause/resume, guardrails e observabilidade executavel
- distribuicao: benchmark_now=`1`, reference_envelope=`4`, defer_outside_cut=`0`

- `LangGraph`
  disposition: `reference_envelope`; expected_outcome: `absorver_depois`
  why_it_matters: ja sustenta durable execution, replay e HITL como referencia principal do runtime stateful
  benchmark_scope: nao rebenchmarkar neste corte; manter como baseline comparativo e referencia soberana
  promotion_blocker: o valor dele ja esta tratado fora desta sprint e nao depende do benchmark atual
- `OpenAI Agents SDK`
  disposition: `reference_envelope`; expected_outcome: `usar_como_referencia`
  why_it_matters: ajuda a comparar handoffs, tools e tracing sem virar o cerebro do sistema
  benchmark_scope: comparacao conceitual de contratos e tracing, sem adaptador novo no baseline
  promotion_blocker: o corte atual nao pede troca da camada principal de orquestracao
- `Mastra`
  disposition: `benchmark_now`; expected_outcome: `usar_como_referencia`
  why_it_matters: oferece workflows tipados, suspend/resume, HITL, snapshots e observabilidade de execucao
  benchmark_scope: avaliar pause/resume, steps reutilizaveis e trilha observavel contra o workflow baseline do JARVIS
  promotion_blocker: nao pode substituir o orchestrator nem redefinir contratos canonicos
- `CrewAI`
  disposition: `reference_envelope`; expected_outcome: `usar_como_referencia`
  why_it_matters: serve como comparativo de delegacao e composicao colaborativa
  benchmark_scope: comparacao conceitual de delegacao e papel de supervisor, sem entrada no runtime
  promotion_blocker: o recorte nao esta abrindo times de agentes como baseline
- `Microsoft Agent Framework`
  disposition: `reference_envelope`; expected_outcome: `usar_como_referencia`
  why_it_matters: ajuda a comparar o ecossistema moderno de workflows e integracoes Microsoft
  benchmark_scope: apenas envelope comparativo para padroes de orchestracao e governanca
  promotion_blocker: hipotese ainda aberta e fora do nucleo atual

### Continuous operational agents and automation blocks

- lacuna do JARVIS: estudar automacoes continuas, blocos reutilizaveis e execucao acionada por eventos sem romper a soberania do nucleo
- objetivo do benchmark: comparar blocos, triggers, webhooks e agentes persistentes como camada futura acima do runtime
- distribuicao: benchmark_now=`1`, reference_envelope=`3`, defer_outside_cut=`0`

- `AutoGPT Platform`
  disposition: `benchmark_now`; expected_outcome: `usar_como_referencia`
  why_it_matters: organiza workflows por blocos reutilizaveis e automacoes acionadas por eventos
  benchmark_scope: avaliar blocos, triggers, webhooks e composicao de automacoes como camada futura de skills e workflows
  promotion_blocker: nao pode assumir identidade, memoria canonica ou governanca final
- `OpenClaw`
  disposition: `reference_envelope`; expected_outcome: `usar_como_referencia`
  why_it_matters: continua util para comparar gateways, canais e assistencia operacional
  benchmark_scope: comparacao de superficie operacional e canais, sem entrada no recorte de workflows
  promotion_blocker: o foco desta sprint e benchmark de workflows, nao superficie multi-canal
- `Hermes Agent`
  disposition: `reference_envelope`; expected_outcome: `absorver_depois`
  why_it_matters: permanece forte como referencia de runtime persistente, skills e continuidade viva
  benchmark_scope: comparacao de runtime persistente e skills, sem abrir migracao do nucleo agora
  promotion_blocker: o corte atual ainda nao esta promovendo runtime persistente novo
- `Manus`
  disposition: `reference_envelope`; expected_outcome: `usar_como_referencia`
  why_it_matters: funciona como benchmark conceitual de assistencia operacional ampla
  benchmark_scope: comparacao conceitual de amplitude operacional, sem adaptador tecnico direto
  promotion_blocker: baixa traducao direta para contratos soberanos do JARVIS nesta fase

### Multilayer memory and context scoping

- lacuna do JARVIS: comparar memoria multicamada entre conversa, sessao, usuario, organizacao e memoria compartilhada por agente
- objetivo do benchmark: avaliar particionamento, recuperacao e escopo sem substituir a memoria canonica do sistema
- distribuicao: benchmark_now=`1`, reference_envelope=`3`, defer_outside_cut=`0`

- `Mem0`
  disposition: `benchmark_now`; expected_outcome: `absorver_depois`
  why_it_matters: oferece memoria multicamada e escopo por user, agent, app e session
  benchmark_scope: comparar modelagem multicamada e isolamento por escopo contra o pacote atual do memory-service
  promotion_blocker: nao pode substituir os registries soberanos nem a memoria canonica nesta fase
- `Letta / MemGPT`
  disposition: `reference_envelope`; expected_outcome: `usar_como_referencia`
  why_it_matters: continua forte como referencia de blocos de memoria, memoria editavel e hierarquia de contexto
  benchmark_scope: comparar blocos persistentes, memoria editavel e memoria compartilhada entre agentes
  promotion_blocker: o recorte atual quer comparar camadas, nao migrar para um agente com memoria propria
- `Zep`
  disposition: `reference_envelope`; expected_outcome: `usar_como_referencia`
  why_it_matters: ajuda a comparar sessoes, users, facts temporais e graph-backed recall
  benchmark_scope: comparacao de memoria por user e session com knowledge graph temporal
  promotion_blocker: a memoria canonica do JARVIS ainda nao pede graph memory como baseline
- `Graphiti`
  disposition: `reference_envelope`; expected_outcome: `usar_como_referencia`
  why_it_matters: serve como comparativo de memoria temporal e relacional que pode complementar continuidade
  benchmark_scope: comparacao conceitual de grafo temporal e trilha relacional entre missoes
  promotion_blocker: falta consumidor canonico de graph memory neste recorte

## Racional

a sprint 3 fecha o envelope de benchmark governado do corte ativo. AutoGPT Platform, Mastra e Mem0 entram como benchmarks pequenos e controlados; LangGraph, OpenAI Agents SDK, CrewAI, Microsoft Agent Framework, OpenClaw, Hermes Agent, Manus, Letta/MemGPT, Zep e Graphiti ficam no envelope comparativo, sem promocao oportunista.
