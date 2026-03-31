# V2 Domain Consumers and Workflows Cut

## 1. Objetivo

Este documento abre o proximo recorte de execucao do `v2` apos o fechamento do
`v2-sovereign-alignment-cut`.

Ele existe para:

- transformar o baseline soberano ja fechado em consumidores canonicos de dominio;
- consolidar workflows operacionais compostos acima do nucleo soberano;
- manter `guided`, `domain_specialist_completed` e axis gates como baseline fixo;
- estudar tecnologias externas apenas em sandbox governado.

---

## 2. Leitura correta deste corte

O alinhamento soberano por eixo nao esta mais em aberto.

O que este corte assume como baseline obrigatorio:

- `shared/domain_registry.py` ja governa refs canonicas e roteamento runtime;
- `shared/memory_registry.py` e `shared/mind_registry.py` ja participam do runtime auditavel;
- `guided` ja e o caminho principal das rotas promovidas;
- `domain_specialist_completed` ja e o evento canonico de conclusao guiada;
- `tools/engineering_gate.py --mode release` ja exige artefatos minimos por eixo.

O que este corte passa a fazer acima desse baseline:

- promover consumidores canonicos de dominio com handoff mais rico;
- compor workflows operacionais sem bypassar governanca, memoria canonica ou sintese final;
- manter estudos externos como benchmark dirigido, sem promocao direta ao nucleo.

---

## 3. Escopo do corte

### Sprint 1. Domain consumers

Status atual:

- concluida.

Objetivo:

- consolidar consumidores canonicos acima do `guided` atual para as rotas ja promovidas.

Entrega realizada:

- rotas promovidas agora carregam `consumer_profile`, `consumer_objective`, `expected_deliverables` e `telemetry_focus`;
- `memory-service` persiste esse pacote como parte do `domain_guided_memory_packet`;
- `specialist-engine` passou a compor handoff e `expected_outputs` a partir do consumidor canonico;
- `orchestrator-service` e `observability-service` passaram a exigir essa telemetria no caminho `guided`.

### Sprint 2. Operational workflows

Status atual:

- concluida.

Objetivo:

- criar camada inicial de workflows compostos acima do nucleo soberano.

Entrega realizada:

- workflows auditaveis para planejamento, readiness e execucao assistida;
- composicao orientada por estado, sem transformar tool runners em cerebro real do sistema;
- governanca explicita em pontos de decisao e promocao;
- `workflow_trace_status` e `workflow_domain_route` passaram a fazer parte do baseline observavel.

### Sprint 3. Governed benchmarks

Status atual:

- concluida.

Objetivo:

- comparar referencias externas apenas como benchmark governado.

Entrega realizada:

- criada a matriz regeneravel `docs/implementation/v2-governed-benchmark-matrix.md` via `tools/render_governed_benchmark_matrix.py`;
- o recorte passou a declarar todas as tecnologias que podem entrar nesta fase por familia de capacidade, nao apenas `AutoGPT Platform`, `Mastra` e `Mem0`;
- `AutoGPT Platform`, `Mastra` e `Mem0` foram fixadas como candidatas de `benchmark_now`;
- `LangGraph`, `OpenAI Agents SDK`, `CrewAI`, `Microsoft Agent Framework`, `OpenClaw`, `Hermes Agent`, `Manus`, `Letta / MemGPT`, `Zep` e `Graphiti` passaram a compor o `reference_envelope` deste corte;
- a regra de sprint ficou explicita: benchmark governado nao promove tecnologia ao nucleo por si so.

### Sprint 4. Release-grade baseline

Status atual:

- concluida.

Objetivo:

- endurecer o baseline do `v2` para novos recortes sem reabrir o alinhamento soberano.

Entregas esperadas:

- axis gates preservados como criterio de promocao;
- artefatos regeneraveis coerentes com docs vivas;
- verificacao `release-grade` executavel para rotas, consumidores, workflows e benchmark governance;
- fechamento formal do corte com backlog classificado para o proximo recorte e artefato regeneravel em `.jarvis_runtime/v2_domain_consumers_and_workflows_cut/`.

---

## 4. O que nao entra agora

- voz oficial como superficie principal;
- `computer use` amplo;
- `pgvector` como fundacao canonica obrigatoria;
- promocao agressiva de tecnologia externa ao nucleo;
- expansao ampla de especialistas sem consumidor canonico correspondente.

---

## 5. Definicao de pronto deste corte

Este corte deve ser considerado pronto quando:

- existir pelo menos um consumidor canonico mais rico por rota promovida relevante;
- a camada inicial de workflows operacionais estiver observavel e governada;
- benchmarks externos tiverem decisao registrada sem promocao oportunista;
- `tools/engineering_gate.py --mode release` continuar passando sem excecoes especiais;
- `HANDOFF.md`, `README.md` e `docs/executive/master-summary.md` refletirem o mesmo estado real.

---

## 6. Documento de apoio obrigatorio

Ler em conjunto com:

- `docs/implementation/v2-sovereign-alignment-cut-closure.md`
- `docs/archive/implementation/v2-sovereign-alignment-cut.md`
- `docs/implementation/v2-governed-benchmark-matrix.md`
- `docs/implementation/v2-domain-consumers-and-workflows-cut-closure.md`
- `docs/architecture/technology-study.md`
- `docs/documentation/matriz-de-aderencia-mestre.md`

Atualizacao da Sprint 2:

- camada inicial aberta com `workflow_profile`, `workflow_steps`, `workflow_composed` e `workflow_completed`;
- o dispatch operacional agora tambem carrega `workflow_state`, `workflow_governance_mode` e `workflow_decision_points`;
- o runtime passou a emitir `workflow_governance_declared`, `workflow_decisions` e `workflow_completed_steps` como trilha auditavel minima;
- a composicao do workflow agora prioriza a rota de dominio ativa com definicao canonica propria, em vez de depender apenas do `task_type`;
- `strategy`, `operational_readiness`, `software_development`, `documentation`, `decision_risk` e outras rotas relevantes agora podem definir perfil, checkpoints e pontos de decisao proprios;
- `observability-service` agora diferencia `workflow_trace_status` entre `healthy`, `incomplete`, `attention_required` e `not_applicable`;
- o artefato operacional agora reflete o workflow ativo, sua rota de origem, seus checkpoints e seus pontos de decisao governados.

Atualizacao da Sprint 3:

- o corte agora possui uma matriz regeneravel de benchmark governado por familia em `docs/implementation/v2-governed-benchmark-matrix.md`;
- `AutoGPT Platform`, `Mastra` e `Mem0` ficaram marcadas como `benchmark_now` sem promocao direta;
- `LangGraph`, `OpenAI Agents SDK`, `CrewAI`, `Microsoft Agent Framework`, `OpenClaw`, `Hermes Agent`, `Manus`, `Letta / MemGPT`, `Zep` e `Graphiti` ficaram formalizadas como envelope comparativo desta fase;
- a tecnologia so pode subir no futuro como `usar como referencia`, `absorver depois` ou `rejeitar`, nunca por entusiasmo local com framework.


Atualizacao da Sprint 4:

- `tools/verify_active_cut_baseline.py` agora gera artefatos regeneraveis do baseline ativo em `.jarvis_runtime/v2_domain_consumers_and_workflows_cut/`;
- `tools/engineering_gate.py --mode release` passou a exigir essa verificacao antes da validacao final do baseline;
- `tools/close_domain_consumers_and_workflows_cut.py` passou a consolidar o fechamento do corte em artefatos regeneraveis;
- a sprint foi concluida com backlog classificado para um proximo recorte proprio de execucao sandbox dos benchmarks governados.
