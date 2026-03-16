# HANDOFF

## Metadata

- Atualizado em: 2026-03-16
- Branch: `main`
- Commit de referencia: `335c3f6`
- Artefato canonico do projeto: `documento_mestre_jarvis.md`
- Status do projeto: Sprint 1 materializada e Sprint 2 iniciada com base semantica compartilhada minima

---

## Meta Atual

Consolidar a **Sprint 2 - Contratos e constituicao** sem abrir escopo prematuro de integracao funcional ampla.

---

## Estado do Projeto

Hoje o repositorio contem:

- Documento-Mestre consolidado como artefato canonico;
- handoff operacional e changelog ativos;
- pacote inicial de documentos derivados;
- estrutura real do monorepo criada;
- arquivos-base da raiz presentes;
- esqueletos minimos dos servicos centrais e engines centrais ja presentes no codigo;
- camada compartilhada inicial em `shared/` com:
  - tipos e enums canonicos;
  - estados iniciais;
  - contratos canonicos prioritarios;
  - schemas declarativos iniciais;
  - eventos internos iniciais;
  - base de identidade, missao e principios.

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
- preparacao de `shared/contracts`, `shared/schemas`, `shared/types`, `shared/events` e `shared/state`;
- implementacao inicial da Sprint 2 em `shared/` com contratos, tipos, schemas, eventos e identidade/principios;
- criacao de testes iniciais de regressao estrutural em `tests/unit/test_shared_layer.py`.

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
- validar a Sprint 1 e a Sprint 2 com o bootstrap real do ambiente virtual;
- expandir a camada compartilhada com validacao mais forte e, se fizer sentido, centralizacao futura em biblioteca especifica;
- iniciar o esqueleto funcional do `orchestrator-service` usando os contratos canonicos de `shared/`;
- decidir formalmente o destino de `documento_mestre_do_jarvis.md`.

---

## Proximos Passos Imediatos

Ordem recomendada:

1. criar e ativar `.venv`;
2. instalar `.[dev]`;
3. rodar `pytest` e `ruff check .`;
4. ligar o `orchestrator-service` aos contratos e eventos canonicos iniciais;
5. depois disso iniciar o primeiro fluxo funcional minimo entre entrada, governanca e sintese basica.

---

## Riscos / Bloqueios

- o ambiente local atual ainda nao tem `pytest` instalado, entao a validacao completa nao foi executada;
- a camada de voz em `shared/schemas` esta apenas com placeholders canonicos, porque os campos formais ainda nao foram fechados em codigo;
- existe risco de voltar a expandir documentacao mais rapido do que codigo;
- `documento_mestre_do_jarvis.md` continua como fonte paralela potencialmente ambigua.

---

## Arquivos Relevantes

- `documento_mestre_jarvis.md`
- `HANDOFF.md`
- `CHANGELOG.md`
- `README.md`
- `pyproject.toml`
- `package.json`
- `shared/types/__init__.py`
- `shared/contracts/__init__.py`
- `shared/schemas/__init__.py`
- `shared/events/__init__.py`
- `shared/state/__init__.py`
- `tests/unit/test_shared_layer.py`
- `services/orchestrator-service/src/orchestrator_service/service.py`
- `docs/implementation/sprint-1-plan.md`
- `docs/implementation/service-breakdown.md`
- `docs/implementation/implementation-strategy.md`

---

## Como Validar / Retomar

Leitura minima para qualquer novo agente:

1. `HANDOFF.md`
2. `documento_mestre_jarvis.md`
3. `shared/types/__init__.py`
4. `shared/contracts/__init__.py`
5. `shared/schemas/__init__.py`

Checagens rapidas recomendadas:

- confirmar que a arvore principal do monorepo existe;
- validar que `shared/` contem tipos, contratos, schemas, eventos e identidade canonicos;
- confirmar que os servicos e engines centrais continuam com esqueletos minimos;
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
- priorizar agora codigo integrador, nao novos documentos;
- reutilizar `shared/` em vez de redefinir contratos localmente nos servicos.

---

## Criterio de Encerramento Deste Handoff

Este handoff continua util enquanto o projeto estiver saindo da fundacao estrutural e entrando nos primeiros fluxos funcionais.

Ele deve ser reavaliado quando:

- a validacao local com `pytest` e `ruff` estiver estabelecida;
- o `orchestrator-service` passar a executar um fluxo minimo real com contratos compartilhados;
- o foco principal do trabalho deixar de ser fundacao e passar a ser iteracao funcional continua.
