# HANDOFF

## Metadata

- Atualizado em: 2026-03-17
- Branch: `main`
- Commit de referencia: `b61bc42`
- Artefato canonico do projeto: `documento_mestre_jarvis.md`
- Status do projeto: Sprint 1 materializada, Sprint 2 minima consolidada e fluxo inicial `orchestrator -> governance -> memory -> operational` ativo

---

## Meta Atual

Consolidar o **primeiro fluxo funcional minimo entre servicos centrais** do JARVIS, saindo de logica local embutida para integracao explicita entre modulos centrais.

---

## Estado do Projeto

Hoje o repositorio contem:

- Documento-Mestre consolidado como artefato canonico;
- handoff operacional e changelog ativos;
- pacote inicial de documentos derivados;
- estrutura real do monorepo criada;
- arquivos-base da raiz presentes;
- camada compartilhada inicial em `shared/` com tipos, enums, estados, contratos, schemas, eventos e identidade/principios;
- `orchestrator-service` com fluxo minimo funcional para receber `InputContract`, classificar intencao, recuperar contexto, acionar governanca, despachar operacao de baixo risco, emitir eventos e registrar o turno atual;
- `governance-service` com politica minima explicita para gerar `GovernanceCheckContract` e `GovernanceDecisionContract`;
- `memory-service` com backbone minimo em memoria de processo para recuperacao contextual de sessao e registro episodico simples;
- `operational-service` com primeira camada de execucao segura e deterministica para tarefas de baixo risco.

Arquivo paralelo/historico que nao deve ser tratado como fonte principal sem decisao explicita:

- `documento_mestre_do_jarvis.md`

---

## O Que Foi Feito

- revisao estrutural relevante do Documento-Mestre;
- consolidacao e enxugamento do Documento-Mestre para reforcar seu papel canonico;
- criacao do `HANDOFF.md` em formato operacional;
- criacao do `CHANGELOG.md`;
- definicao da politica de documentos derivados;
- criacao do pacote inicial de derivados de implementacao, operacao, arquitetura e resumo executivo;
- materializacao da base real do repositorio da Sprint 1;
- criacao dos esqueletos minimos dos servicos centrais e engines centrais;
- implementacao inicial da Sprint 2 em `shared/` com contratos, tipos, schemas, eventos e identidade/principios;
- criacao de testes iniciais de regressao estrutural em `tests/unit/test_shared_layer.py`;
- implementacao do primeiro fluxo funcional do `orchestrator-service` com classificacao simples de intencao, governanca inicial, trilha de eventos e sintese basica;
- extracao da governanca minima para o `governance-service`, que agora gera a checagem e a decisao usadas pelo orquestrador;
- implementacao do `memory-service` com recuperacao contextual por sessao e registro episodico simples em memoria de processo;
- integracao do `orchestrator-service` com o `memory-service`, adicionando recuperacao e gravacao de memoria ao fluxo minimo;
- implementacao do `operational-service` com execucao segura e deterministica de operacoes de baixo risco;
- integracao do `orchestrator-service` com o `operational-service`, adicionando `operation_dispatched` e `operation_completed` ao fluxo permitido;
- ampliacao dos testes do `operational-service` e do `orchestrator-service` para cobrir despacho operacional permitido e bloqueio previo por governanca.

---

## Decisoes Fechadas

Nao rediscutir sem evidencia forte ou mudanca explicita de direcao:

- o JARVIS e um sistema unificado, nao um chatbot simples;
- o repositorio principal e `jarvis`;
- a estrategia base e monorepo modular;
- `Python` e a linguagem principal;
- `TypeScript` e linguagem secundaria para interface, web e voz quando necessario;
- `LangGraph` e a base principal de orquestracao stateful;
- `PostgreSQL + pgvector` e o backbone inicial de memoria e persistencia;
- `LangSmith` e a principal camada de observabilidade agentic;
- `OpenHands` e o principal especialista subordinado de software;
- especialistas sao subordinados ao nucleo, nao competidores de identidade;
- governanca e autoevolucao sao partes nucleares do sistema;
- o Documento-Mestre continua sendo o artefato canonico do projeto.

---

## O Que Ainda Falta

Pendencias principais agora:

- instalar as dependencias locais de desenvolvimento, especialmente `pytest` e `ruff`;
- validar a Sprint 1, a Sprint 2 e a cadeia `orchestrator -> governance -> memory -> operational` com o bootstrap real do ambiente virtual;
- decidir se a proxima integracao central sera observabilidade propriamente dita ou persistencia minima real da memoria;
- sair de memoria apenas em processo para um backbone persistente quando entrar a proxima fase;
- decidir formalmente o destino de `documento_mestre_do_jarvis.md`.

---

## Proximos Passos Imediatos

Ordem recomendada:

1. criar e ativar `.venv`;
2. instalar `.[dev]`;
3. rodar `pytest` e `ruff check .`;
4. escolher a proxima integracao central: observabilidade ou persistencia minima de memoria;
5. manter o `orchestrator-service` como coordenador, evitando recolocar politica, armazenamento ou execucao estrutural dentro dele.

---

## Riscos / Bloqueios

- o ambiente local atual ainda nao tem `pytest` instalado, entao a validacao completa nao foi executada;
- a memoria atual ainda e apenas de processo e nao persistente entre reinicios;
- a classificacao de intencao ainda permanece no `orchestrator-service` como heuristica simples;
- o `operational-service` atual e deliberadamente limitado a tarefas seguras e deterministicas, ainda sem adaptadores reais.

---

## Arquivos Relevantes

- `documento_mestre_jarvis.md`
- `HANDOFF.md`
- `CHANGELOG.md`
- `shared/types/__init__.py`
- `shared/contracts/__init__.py`
- `shared/schemas/__init__.py`
- `shared/events/__init__.py`
- `shared/state/__init__.py`
- `services/orchestrator-service/src/orchestrator_service/service.py`
- `services/orchestrator-service/tests/test_orchestrator_service.py`
- `services/governance-service/src/governance_service/service.py`
- `services/governance-service/tests/test_governance_service.py`
- `services/memory-service/src/memory_service/service.py`
- `services/memory-service/tests/test_memory_service.py`
- `services/operational-service/src/operational_service/service.py`
- `services/operational-service/tests/test_operational_service.py`
- `tests/unit/test_shared_layer.py`
- `docs/implementation/service-breakdown.md`
- `docs/implementation/implementation-strategy.md`

---

## Como Validar / Retomar

Leitura minima para qualquer novo agente:

1. `HANDOFF.md`
2. `documento_mestre_jarvis.md`
3. `services/memory-service/src/memory_service/service.py`
4. `services/governance-service/src/governance_service/service.py`
5. `services/operational-service/src/operational_service/service.py`
6. `services/orchestrator-service/src/orchestrator_service/service.py`

Checagens rapidas recomendadas:

- confirmar que `shared/` contem a camada canonica minima;
- validar que o `memory-service` recupera contexto e grava turnos na mesma sessao;
- validar que o `governance-service` produz checagem e decisao canonicas;
- validar que o `operational-service` executa apenas tarefas seguras e deterministicas;
- validar que o `orchestrator-service` consome memoria, governanca e operacao e emite a trilha correta de eventos;
- instalar dependencias locais e executar `pytest`.

Comandos uteis:

```powershell
rg --files
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
pytest
ruff check .
```

---

## Regra Para o Proximo Agente

- tratar `documento_mestre_jarvis.md` como artefato canonico;
- usar `HANDOFF.md` como documento operacional de estado;
- atualizar `CHANGELOG.md` sempre que houver mudanca relevante;
- priorizar agora integracao funcional entre servicos centrais;
- reutilizar `shared/` em vez de redefinir contratos localmente nos servicos.

---

## Criterio de Encerramento Deste Handoff

Este handoff continua util enquanto o projeto estiver saindo da fundacao estrutural e entrando nos primeiros fluxos funcionais.

Ele deve ser reavaliado quando:

- a validacao local com `pytest` e `ruff` estiver estabelecida;
- a proxima integracao central alem de memoria, governanca e operacao estiver ativa;
- o foco principal do trabalho deixar de ser fundacao e passar a ser iteracao funcional continua.
