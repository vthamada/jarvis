# Master Summary

## 1. Objetivo

Este documento resume o projeto JARVIS para leitura executiva, preservando alinhamento com o Documento-Mestre sem reproduzi-lo integralmente.

---

## 2. O que é o JARVIS

O JARVIS é definido como um sistema cognitivo unificado, multidomínio, metacognitivo, operacional e governado.

Na prática, ele não deve ser tratado como:

- chatbot simples;
- automação isolada;
- coleção desconexa de tools;
- agente único de tarefa estreita.

Ele deve ser tratado como:

- uma entidade cognitiva única;
- um sistema com memória útil;
- um núcleo que pensa, planeja e age;
- uma plataforma governada de operação e evolução.

---

## 3. Objetivo do projeto

O objetivo central é construir uma base correta para um sistema capaz de:

- ampliar capacidade intelectual e operacional do usuário;
- sustentar memória, continuidade e missão;
- agir com autonomia graduada e governada;
- evoluir sem perder identidade.

---

## 4. Estratégia macro

O projeto está organizado em quatro fases:

- `v1` - baseline unificado e utilizável
- `pós-v1` - continuidade profunda entre missões
- `v1.5` - primeiro salto cognitivo acima do baseline
- `v2` e `v3` - especialização, memória mais profunda e maturidade ampliada

Estratégia explícita:

- construir o núcleo primeiro;
- evitar fragmentação prematura;
- usar tecnologia reaproveitada onde faz sentido;
- manter identidade, memória, governança e síntese como partes próprias do sistema.

---

## 5. Stack e referências

Stack base do baseline atual:

- `Python` como linguagem principal;
- `TypeScript` para interfaces e componentes web/voz quando necessário;
- `PostgreSQL` como backend operacional oficial de memória;
- `LangSmith` como observabilidade agentic complementar;
- `OpenHands` como referência principal para especialista subordinado de software.

Leitura arquitetural oficial de referências externas:

- `LangGraph` orienta orquestração stateful;
- `OpenAI Agents SDK` complementa handoffs, tools e voice flows;
- `OpenHands` orienta o especialista de software;
- `browser-use`, `Open Interpreter` e `Claude Computer Use` orientam computer use;
- `Letta / MemGPT`, `Hermes`, `Zep` e `Graphiti` orientam memória persistente e estado cognitivo;
- `OpenClaw` e `Manus` orientam a camada de assistência operacional;
- `PydanticAI`, `Qwen-Agent` e `smolagents` orientam contratos, tipagem e previsibilidade.

Regra executiva:

- referências externas orientam a construção do JARVIS;
- elas não substituem o núcleo nem transformam o projeto em colagem de frameworks.

---

## 6. Estado atual

Hoje o projeto já não está em consolidação inicial.

O repositório possui:

- baseline integrado entre orquestração, memória, governança, conhecimento, observabilidade e operação;
- `jarvis-console` como interface textual mínima;
- `PostgreSQL` validado como backend operacional oficial;
- `internal pilot` executado;
- `evolution-lab` ativo em `sandbox-only`;
- ciclos formais de `pós-v1` e `v1.5` já executados, com `v2` aberto como frente ativa.

Leitura curta do momento:

- o `v1` está encerrado e congelado para uso controlado;
- o primeiro ciclo do `pós-v1` foi encerrado;
- o primeiro ciclo do `v1.5` foi encerrado formalmente;
- o programa subiu para `v2`;
- a frente ativa agora é `especialização controlada subordinada ao núcleo com memória relacional mais rica`;
- Sprint 1 do `v2` foi concluída;
- Sprint 2 do `v2` foi concluída;
- Sprint 3 do `v2` foi concluída com memória relacional compartilhada mediada pelo núcleo e contexto persistido por especialista;
- Sprint 4 do `v2` foi concluída com registry inicial de domínios e primeiro especialista subordinado em `shadow mode`;
- Sprint 5 do `v2` foi concluída com evals de aderência do recorte de especialistas;
- Sprint 6 do `v2` foi concluída com fechamento formal do primeiro corte do ciclo;
- o ultimo recorte funcional concluido do programa agora e `docs/archive/implementation/v2-native-memory-scope-hardening-cut.md`, fechado para endurecer o baseline nativo antes de qualquer reabertura externa;
- o ultimo recorte estrutural concluido do programa agora e `docs/implementation/v2-repository-hygiene-and-tools-review-cut.md`, fechado para reduzir a superficie ativa do repositorio;
- a Sprint 1 desse recorte foi concluida com inventario regeneravel da superficie estrutural do repositorio;
- a Sprint 2 desse recorte foi concluida com decisao regeneravel de classificacao dos docs ativos de `docs/implementation`;
- a Sprint 3 desse recorte foi concluida com decisao regeneravel de classificacao dos entrypoints da raiz de `tools/`;
- a Sprint 4 desse recorte foi concluida com migracao dos `archive candidates` e fechamento formal do recorte;
- a auditoria completa do Documento-Mestre continua orientando o backlog por eixo canônico;
- o fechamento formal do corte soberano segue regenerável por `tools/archive/close_sovereign_alignment_cut.py` em `docs/archive/implementation/v2-sovereign-alignment-cut-closure.md`;
- o fechamento formal do corte de consumers/workflows segue regenerável por `tools/archive/close_domain_consumers_and_workflows_cut.py` em `docs/archive/implementation/v2-domain-consumers-and-workflows-cut-closure.md`.
- o plano regenerável do corte ativo segue emitido por `tools/archive/render_governed_benchmark_execution_plan.py` em `docs/archive/implementation/v2-governed-benchmark-execution-plan.md`.
- o lote `pre-v3 hardening` tambem ja foi concluido no backlog micro, deixando continuidade stateful nativa, `specialist_subflow` e `mission_runtime_state` como baseline observado e comparavel.
- o proximo passo do programa deixou de ser correção estrutural do `v2` e passou a ser decidir a fronteira arquitetural suficiente para abertura do `v3`.
- o baseline ativo do corte agora tambem combina contratos promovidos do registry com cobertura deliberada do piloto, exigindo as seis rotas promovidas, seus `workflow_profiles` e sinais minimos de memoria causal e recomposicao cognitiva antes de manter `baseline_release_ready`.
- essa cobertura deliberada agora tambem exige `dominant_tension` e alinhamento `mente -> dominio -> especialista` como parte explicita da leitura de robustez do `v2`, em vez de deixar esses sinais apenas nos comparadores tecnicos.
---

## 7. Risco principal

O principal risco atual não é falta de visão. É excesso de escopo.

O risco estrutural complementar é outro:

- implementar com eficiência local, mas sem fechar lacunas explícitas do Documento-Mestre em `mentes`, `domínios` e `memórias`.

Leitura executiva atual desse risco:

- o risco principal deixou de ser descompasso estrutural do `v2` e passou a ser abrir nova frente macro antes de aproveitar o baseline já endurecido;
- `domínios`, `memórias` e `mentes` ainda admitem maturação adicional, mas já não configuram pendência técnica material de robustez no baseline atual;
- o próximo erro a evitar é misturar expansão funcional nova com baseline ainda não consolidado documentalmente.

O projeto deve evitar:

- reabrir o baseline do `v1` sem necessidade real;
- tentar absorver tecnologia externa antes de provar a lacuna no núcleo;
- expandir superfícies antes de consolidar especialistas subordinados e memória relacional.

---

## 8. Próximo passo recomendado

O próximo passo executivo mais racional é:

- usar `docs/implementation/v2-native-memory-scope-hardening-cut-closure.md` como fechamento formal mais recente do eixo de memoria nativa;
- usar `docs/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md` como fechamento estrutural mais recente;
- selecionar agora o proximo recorte funcional com base em `docs/implementation/v2-adherence-snapshot.md`, sem reabrir ruido estrutural;
- usar o fechamento regeneravel do `v2-domain-consumers-and-workflows-cut` como leitura executiva minima de cobertura por rota, workflow e sinais deliberados antes de qualquer benchmark novo;
- manter `Mastra` e `AutoGPT Platform` apenas como referencia e `Mem0` como candidata condicional de reabertura futura;
- manter fora do proximo recorte voz oficial, `computer use` amplo, `pgvector` como base canonica e assistente operacional amplo.
