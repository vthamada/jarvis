# Repository Map And Consistency Audit

## 1. Objetivo

Este documento cruza a superficie viva de `docs/`, `tools/` e das demais pastas do repositorio
para responder quatro perguntas:

- quais artefatos sao ativos e devem orientar o baseline atual;
- quais artefatos sao historicos e nao devem voltar a ser tratados como fonte ativa;
- quais diretorios sao gerados/local-only e nao sao fonte de verdade;
- quais inconsistencias ou candidatos a reclassificacao ainda existem.

## 2. Estado de referencia

- data da revisao: `2026-04-02`
- branch de referencia: `main`
- commit de referencia do baseline lido: `5852749`
- docs vivos centrais: `HANDOFF.md`, `CHANGELOG.md`, `README.md`, `docs/executive/master-summary.md`, `docs/implementation/v2-adherence-snapshot.md`, `docs/documentation/matriz-de-aderencia-mestre.md`

## 3. Mapa de `docs/`

### 3.1 Superficie ativa

| Caminho | Papel atual | Status |
| --- | --- | --- |
| `docs/documentation/engineering-constitution.md` | guardrail minimo de engenharia | ativo |
| `docs/documentation/matriz-de-aderencia-mestre.md` | ponte entre Documento-Mestre e backlog real | ativo |
| `docs/documentation/repository-map-and-consistency-audit.md` | mapa do repositorio e auditoria de consistencia | ativo |
| `docs/implementation/v2-adherence-snapshot.md` | snapshot funcional mais importante do baseline atual | ativo |
| `docs/implementation/v2-native-memory-scope-hardening-cut-closure.md` | fechamento formal funcional mais recente | ativo |
| `docs/implementation/v2-repository-hygiene-and-tools-review-cut.md` | ultimo recorte estrutural executado | ativo |
| `docs/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md` | fechamento formal do ultimo recorte estrutural | ativo |
| `docs/implementation/v2-repository-hygiene-inventory.md` | inventario regeneravel da revisao estrutural | ativo |
| `docs/implementation/v2-repository-hygiene-doc-decisions.md` | classificacao regeneravel dos docs de implementacao | ativo |
| `docs/implementation/v2-repository-hygiene-tool-decisions.md` | classificacao regeneravel dos entrypoints de `tools/` | ativo |
| `docs/operations/release-and-change-management.md` | operacao e mudanca controlada | ativo |
| `docs/operations/incident-response.md` | resposta a incidentes | ativo |
| `docs/operations/v1-operational-baseline.md` | baseline operacional minimo ainda referenciado | ativo |
| `docs/roadmap/programa-ate-v3.md` | direcao macro do programa | ativo |
| `docs/executive/master-summary.md` | leitura executiva sintetica | ativo |
| `docs/architecture/technology-study.md` | radar de tecnologias e regra de absorcao | ativo |
| `docs/architecture/evolution-lab.md` | framing do laboratorio evolutivo | ativo |
| `docs/architecture/technology-repository-review-framework.md` | criterio de revisao externa de repositorios | ativo |
| `docs/architecture/mem0-repository-review.md` | estudo arquitural de memoria externa | ativo como referencia, nao como backlog |
| `docs/adr/adr-001-absorcao-parcial-de-langgraph-no-nucleo.md` | ADR vigente | ativo |
| `docs/future/architecture/*` | visao futura, explicitamente nao baseline | ativo como visao |

### 3.2 Superficie historica

| Caminho | Papel atual | Status |
| --- | --- | --- |
| `docs/archive/implementation/*` | historico fechado de ciclos e cuts anteriores | historico |
| `docs/archive/operations/internal-pilot-plan.md` | historico de piloto | historico |
| `docs/archive/documentation/estrutura_de_documentos_derivados.md` | historico de reorganizacao documental | historico |
| `docs/archive/documentation/auditoria-primaria-documento-mestre.md` | auditoria historica do mestre usada na fase de saneamento documental | historico |
| `docs/archive/executive/v1-scope-summary.md` | historico de escopo do `v1` | historico |

Regra operacional:

- artefatos em `docs/archive/` podem ser citados como lastro historico;
- artefatos em `docs/archive/` nao devem ser reabertos como documento ativo por inercia.

## 4. Mapa das outras pastas

### 4.1 Runtime, contratos e servicos

| Caminho | Papel atual | Status |
| --- | --- | --- |
| `shared/` | contratos, registries, eventos, schemas e tipos soberanos | ativo |
| `engines/` | cognicao, identidade, planejamento, especialistas e sintese | ativo |
| `services/` | orquestracao, memoria, governanca, conhecimento, observabilidade e operacao | ativo |
| `knowledge/curated/` | corpus e registry de dominios | ativo |
| `evolution/` | laboratorio evolutivo sandbox | ativo controlado |
| `tests/` | cobertura compartilhada e validacao de baseline | ativo |

### 4.2 Superficie de tooling

| Caminho | Papel atual | Status |
| --- | --- | --- |
| `tools/engineering_gate.py` | gate padrao e de release | ativo |
| `tools/verify_document_guardrails.py` | guardrail de docs criticos | ativo |
| `tools/verify_axis_artifacts.py` | verificacao dos artefatos minimos por eixo | ativo |
| `tools/verify_active_cut_baseline.py` | baseline do recorte ativo | ativo |
| `tools/validate_baseline.py` | validacao de baseline do sistema | ativo |
| `tools/run_internal_pilot.py` | piloto interno | ativo |
| `tools/compare_orchestrator_paths.py` | comparacao de caminhos do runtime | ativo |
| `tools/internal_pilot_report.py` | consolidacao do piloto | ativo |
| `tools/evolution_from_pilot.py` | proposals a partir de comparacao | ativo |
| `tools/go_live_internal_checklist.py` | checklist de go-live | ativo |
| `tools/close_native_memory_scope_hardening_cut.py` | fechamento regeneravel do ultimo recorte funcional | ativo |
| `tools/close_repository_hygiene_and_tools_review_cut.py` | fechamento regeneravel do ultimo recorte estrutural | ativo |
| `tools/render_repository_hygiene_*.py` | renderizadores regeneraveis do recorte estrutural | ativo |
| `tools/archive/*` | fechadores e renderizadores historicos | historico |

Leitura correta:

- `tools/close_native_memory_scope_hardening_cut.py` e `tools/close_repository_hygiene_and_tools_review_cut.py` ainda nao sao obsoletos; eles continuam referenciados por docs vivos, inventarios e gates;
- `tools/archive/` concentra fechadores de ciclos que ja nao comandam o baseline atual.

### 4.3 Diretorios gerados ou locais

| Caminho | Papel atual | Status |
| --- | --- | --- |
| `.jarvis_runtime/` | artefatos regenerados de execucao local | gerado |
| `.pytest_tmp/` | apoio local de teste | gerado |
| `.ruff_cache/` | cache local de lint | gerado |
| `.test_runtime/` | artefatos locais de teste | gerado |
| `pytest-cache-files-*` | residuos locais de cache | gerado |
| `__pycache__/` | cache Python | gerado |
| `jarvis.egg-info/` | metadata local de instalacao | gerado |
| `.venv/` | ambiente local | local-only |
| `.claude/` | configuracao local do operador | local-only |

Regra operacional:

- nenhum desses diretorios e fonte de verdade do projeto;
- mudancas neles so devem ser versionadas se houver decisao explicita do operador.

## 5. Inconsistencias encontradas

### 5.1 Corrigidas nesta rodada

1. `HANDOFF.md` estava com `commit de referencia` defasado (`bdf569b`) e foi alinhado ao baseline lido (`5852749`).
2. `docs/implementation/v2-adherence-snapshot.md` ainda usava links absolutos antigos (`d:/Users/DTI/Desktop/jarvis/...`) e foi normalizado para caminhos relativos portaveis.
3. `docs/architecture/mem0-repository-review.md` tambem carregava links absolutos antigos para `memory-service` e `memory_registry`, agora normalizados.
4. `cognitive-engine` e `specialist-engine` agora consomem explicitamente contratos de rota (`domain_specialist_routes`) antes do fallback local, reduzindo drift entre roteamento resolvido e convocacao de especialista.
5. `auditoria_documento_mestre_jarvis.md` deixou a raiz do repositorio, foi arquivado como `docs/archive/documentation/auditoria-primaria-documento-mestre.md` e teve seus links normalizados.

### 5.2 Acompanhar, mas sem urgencia critica

1. `README.md` e `docs/executive/master-summary.md` ainda carregam bastante historico de ciclos anteriores no mesmo corpo do estado atual; nao ha contradicao grave, mas a superficie continua mais narrativa do que estritamente operacional.
2. `docs/implementation/implementation-strategy.md` e `docs/implementation/service-breakdown.md` nao apareceram como pontos de conflito, mas tambem nao sao hoje os docs mais citados pelo baseline; vale revisar periodicamente se continuam ativos ou se devem virar referencia historica.

## 6. Decisoes praticas

1. Tratar `docs/implementation/v2-adherence-snapshot.md` como fotografia funcional oficial do baseline atual.
2. Tratar `HANDOFF.md` como retomada tatico-operacional e `CHANGELOG.md` como trilha historica minima.
3. Manter `docs/archive/implementation/` e `tools/archive/` como historico fechado, sem reativacao casual.
4. Usar `shared/`, `engines/`, `services/` e `knowledge/curated/` como eixo tecnico soberano do runtime.
5. Tratar diretorios gerados e locais como ruido operacional, nao como fonte de verdade.

## 7. Proximas verificacoes recomendadas

1. Revisar periodicamente se `README.md` e `docs/executive/master-summary.md` ainda estao proporcionais ao baseline atual.
2. Reavaliar o papel de `docs/implementation/implementation-strategy.md` e `docs/implementation/service-breakdown.md` sempre que o baseline funcional mudar de forma material.
3. Reexecutar este mapa sempre que um novo recorte funcional ou estrutural for aberto.
