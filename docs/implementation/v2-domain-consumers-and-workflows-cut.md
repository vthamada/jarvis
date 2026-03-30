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

Entregas esperadas:

- contratos mais ricos de consumo por dominio;
- handoffs mais especificos por rota promovida;
- telemetria que diferencie contribuicao guiada, consumo efetivo e queda para fallback.

### Sprint 2. Operational workflows

Objetivo:

- criar camada inicial de workflows compostos acima do nucleo soberano.

Entregas esperadas:

- workflows auditaveis para planejamento, readiness e execucao assistida;
- composicao orientada por estado, sem transformar tool runners em cerebro real do sistema;
- governanca explicita em pontos de decisao e promocao.

### Sprint 3. Governed benchmarks

Objetivo:

- comparar referencias externas apenas como benchmark governado.

Entregas esperadas:

- recortes pequenos para `AutoGPT Platform`, `Mastra` e `Mem0`;
- criterio claro de `usar como referencia`, `absorver depois` ou `rejeitar`;
- nenhum impacto direto no baseline central sem evidencia.

### Sprint 4. Release-grade baseline

Objetivo:

- endurecer o baseline do `v2` para novos recortes sem reabrir o alinhamento soberano.

Entregas esperadas:

- axis gates preservados como criterio de promocao;
- artefatos regeneraveis coerentes com docs vivas;
- fechamento do corte com backlog classificado para o proximo recorte.

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
- `docs/architecture/technology-study.md`
- `docs/documentation/matriz-de-aderencia-mestre.md`

Atualizacao da Sprint 2:

- camada inicial aberta com `workflow_profile`, `workflow_steps`, `workflow_composed` e `workflow_completed`;
- o dispatch operacional passa a carregar um workflow composto auditavel sem criar um runtime paralelo;
- o artefato operacional agora reflete o workflow ativo e seus checkpoints.
