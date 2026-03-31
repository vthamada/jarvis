# V2 Governed Benchmark Execution Cut

## 1. Objetivo

Este documento abre o recorte de execucao sandbox que sucede o fechamento do
`v2-domain-consumers-and-workflows-cut`.

Ele existe para:

- executar benchmarks pequenos e governados das tecnologias marcadas como `benchmark_now`;
- comparar ganho real contra o baseline soberano ja fechado;
- produzir decisao disciplinada por tecnologia: `usar como referencia`, `absorver depois` ou `rejeitar`;
- impedir promocao oportunista de framework para o nucleo.

---

## 2. Leitura correta deste corte

O que este corte assume como baseline obrigatorio:

- `docs/archive/implementation/v2-domain-consumers-and-workflows-cut-closure.md` ja fechou consumidores, workflows e benchmark governance como baseline `release-grade`;
- `tools/verify_active_cut_baseline.py` e `tools/archive/close_domain_consumers_and_workflows_cut.py` ja existem como verificadores regeneraveis do corte anterior;
- `docs/archive/implementation/v2-governed-benchmark-matrix.md` ja define o envelope completo e fixa `Mastra`, `AutoGPT Platform` e `Mem0` como `benchmark_now`;
- nenhuma tecnologia externa entra no nucleo por benchmark isolado.

O que este corte passa a fazer acima desse baseline:

- transformar `benchmark_now` em execucao sandbox por familia de capacidade;
- registrar artefatos minimos de execucao, leitura comparativa e decisao por tecnologia;
- manter `reference_envelope` apenas como contraste, sem reabrir o baseline local.

---

## 3. Escopo do corte

### Sprint 1. Benchmark execution plan

Status atual:

- concluida.

Objetivo:

- transformar `benchmark_now` em perfis de execucao sandbox claros e regeneraveis.

Entrega realizada:

- criado dataset versionado em `tools/benchmarks/datasets/v2_governed_benchmark_execution_profiles.json`;
- criado renderizador `tools/archive/render_governed_benchmark_execution_plan.py`;
- criado artefato regeneravel `docs/archive/implementation/v2-governed-benchmark-execution-plan.md` com superficies baseline, perguntas de avaliacao, artefatos esperados e bloqueios de absorcao por tecnologia.

### Sprint 2. Scenario specs and sandbox notes

Status atual:

- concluida.

Objetivo:

- definir cenario minimo de execucao para cada tecnologia `benchmark_now` sem criar dependencia central nova.

Entregas esperadas:

- especificacao de cenario por `Mastra`, `AutoGPT Platform` e `Mem0`;
- checklist minimo de evidencia e fronteiras sandbox por tecnologia;
- artefato regeneravel em `docs/archive/implementation/v2-governed-benchmark-scenario-specs.md`.

Entrega realizada:

- criado dataset versionado em `tools/benchmarks/datasets/v2_governed_benchmark_scenarios.json`;
- criado renderizador `tools/archive/render_governed_benchmark_scenario_specs.py`;
- criado artefato regeneravel `docs/archive/implementation/v2-governed-benchmark-scenario-specs.md` com scenario id, objetivo, sinais de sucesso/falha, evidencia minima e fronteiras sandbox por tecnologia.

### Sprint 3. Per-technology decision closure

Status atual:

- concluida.

Objetivo:

- decidir por tecnologia entre `usar como referencia`, `absorver depois` ou `rejeitar`.

Entregas esperadas:

- decisao formal por tecnologia;
- racional curto e comparavel contra o baseline atual;
- atualizacao de `technology-study.md`, `HANDOFF.md` e do proprio corte.

Entrega realizada:

- criado dataset versionado em `tools/benchmarks/datasets/v2_governed_benchmark_decisions.json`;
- criado renderizador `tools/archive/render_governed_benchmark_decisions.py`;
- criado artefato regeneravel `docs/archive/implementation/v2-governed-benchmark-decisions.md` com decisao final, racional curto, sinais de reabertura e superficies recomendadas por tecnologia;
- `Mastra` e `AutoGPT Platform` foram classificados como `usar como referencia`, enquanto `Mem0` ficou classificada como `absorver depois`.

### Sprint 4. Cut closure

Status atual:

- concluida.

Objetivo:

- fechar o recorte sem deixar benchmark solto ou conclusao implicita.

Entregas esperadas:

- fechamento formal do corte com backlog classificado;
- artefato regeneravel de encerramento;
- definicao clara do que sobe para recorte futuro e do que continua apenas como referencia.

Entrega realizada:

- criado `tools/archive/close_governed_benchmark_execution_cut.py` como fechador regeneravel do recorte;
- criado artefato formal `docs/archive/implementation/v2-governed-benchmark-execution-cut-closure.md`;
- o recorte encerrou com `Mastra` e `AutoGPT Platform` mantidas como referencia e `Mem0` como unica candidata de reabertura futura condicionada.
- `tools/engineering_gate.py --mode release` permanece como gate oficial do fechamento do recorte.

---

## 4. Tecnologias dentro do recorte imediato

Entram agora como `benchmark_now`:

- `Mastra`
- `AutoGPT Platform`
- `Mem0`

Ficam apenas como `reference_envelope` nesta fase:

- `LangGraph`
- `OpenAI Agents SDK`
- `CrewAI`
- `Microsoft Agent Framework`
- `OpenClaw`
- `Hermes Agent`
- `Manus`
- `Letta / MemGPT`
- `Zep`
- `Graphiti`

---

## 5. Definicao de pronto deste corte

Este corte deve ser considerado pronto quando:

- cada tecnologia `benchmark_now` tiver perfil de execucao, scenario spec e decisao formal registrada;
- `docs/archive/implementation/v2-governed-benchmark-execution-cut-closure.md` existir como fechamento humano do recorte;
- `tools/archive/close_governed_benchmark_execution_cut.py` passar no gate de release como fechamento do corte atual;
- `HANDOFF.md`, `README.md`, `docs/executive/master-summary.md` e `docs/architecture/technology-study.md` refletirem o mesmo estado real.

---

## 6. Documento de apoio obrigatorio

Ler em conjunto com:

- `docs/archive/implementation/v2-domain-consumers-and-workflows-cut-closure.md`
- `docs/archive/implementation/v2-governed-benchmark-matrix.md`
- `docs/archive/implementation/v2-governed-benchmark-execution-plan.md`
- `docs/archive/implementation/v2-governed-benchmark-scenario-specs.md`
- `docs/archive/implementation/v2-governed-benchmark-decisions.md`
- `docs/archive/implementation/v2-governed-benchmark-execution-cut-closure.md`
- `docs/architecture/technology-study.md`
- `docs/documentation/matriz-de-aderencia-mestre.md`
