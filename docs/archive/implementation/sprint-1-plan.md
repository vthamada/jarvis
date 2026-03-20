# Sprint 1 Plan

## 1. Objetivo

Este documento transforma a **Sprint 1 — Fundação do repositório** do JARVIS em um plano técnico executável de curto prazo.

Ele deriva principalmente de:

- `documento_mestre_jarvis.md`, capítulos sobre:
  - `184. M1 — Fundação estrutural`
  - `196. Estrutura concreta inicial de diretórios e arquivos-base`
  - `206. Ordem concreta recomendada de criação dos arquivos-base`
  - `287. Fase 0 — Preparação de execução`
  - `288. Fase 1 — Fundação semântica compartilhada`

Seu objetivo não é redefinir o escopo do sistema, e sim transformar o primeiro recorte de engenharia em ações concretas.

---

## 2. Meta da Sprint 1

Ao final da Sprint 1, o repositório deve:

- existir como monorepo organizado;
- possuir estrutura inicial coerente com a arquitetura;
- conter arquivos-base mínimos para backend, documentação e testes;
- permitir que a Sprint 2 comece sem ambiguidade estrutural;
- preservar o Documento-Mestre como referência canônica.

---

## 3. Escopo da Sprint 1

Esta sprint cobre somente a base estrutural do projeto.

Inclui:

- criação da estrutura inicial de diretórios;
- criação dos arquivos-base da raiz;
- criação dos diretórios e `README.md` mínimos dos principais serviços e engines;
- preparação mínima de `docs/`, `tests/` e `tools/`;
- configuração inicial de Python e tooling de qualidade;
- convenções mínimas do repositório.

Não inclui ainda:

- implementação funcional do núcleo central;
- contratos completos em código;
- memória persistente real;
- governança funcional;
- integrações reais com ferramentas;
- frontend ou voz funcionais.

---

## 4. Entregáveis

Entregáveis mínimos da Sprint 1:

- raiz do repositório preparada;
- `pyproject.toml` inicial;
- `.editorconfig`;
- `.env.example`;
- `README.md` da raiz;
- estrutura `docs/`, `apps/`, `services/`, `engines/`, `memory/`, `knowledge/`, `governance/`, `observability/`, `evolution/`, `shared/`, `infra/`, `tests/`, `tools/`;
- `README.md` inicial nos principais serviços e engines;
- esqueleto mínimo para testes;
- convenção inicial registrada para organização do código.

Entregáveis desejáveis:

- `package.json` inicial para futuros componentes TypeScript;
- configuração mínima de lint, tipagem e testes Python;
- diretório de ADRs preparado;
- documento de comandos iniciais de bootstrap do projeto.

---

## 5. Ordem de Execução Recomendada

### 5.1 Bloco 1 — Base da raiz

Criar:

- `README.md`
- `.gitignore`
- `.editorconfig`
- `.env.example`
- `pyproject.toml`
- `package.json`

Resultado esperado:

- repositório com identidade mínima e tooling inicial definidos.

### 5.2 Bloco 2 — Estrutura de diretórios

Criar:

- `docs/`
- `apps/`
- `services/`
- `engines/`
- `memory/`
- `knowledge/`
- `governance/`
- `observability/`
- `evolution/`
- `shared/`
- `infra/`
- `tests/`
- `tools/`

Resultado esperado:

- topologia do monorepo visível e coerente com o Documento-Mestre.

### 5.3 Bloco 3 — Esqueletos dos serviços e engines centrais

Criar estrutura mínima para:

- `services/orchestrator-service/`
- `services/memory-service/`
- `services/governance-service/`
- `services/operational-service/`
- `services/knowledge-service/`
- `services/observability-service/`
- `engines/identity-engine/`
- `engines/executive-engine/`
- `engines/cognitive-engine/`
- `engines/planning-engine/`
- `engines/synthesis-engine/`

Cada um com pelo menos:

- `README.md`
- diretório `src/`
- diretório `tests/` quando fizer sentido

### 5.4 Bloco 4 — Estruturas compartilhadas

Criar estrutura mínima para:

- `shared/contracts/`
- `shared/schemas/`
- `shared/types/`
- `shared/events/`
- `shared/state/`

Resultado esperado:

- local único preparado para a fundação semântica da Sprint 2.

### 5.5 Bloco 5 — Documentação técnica mínima

Criar ou ajustar:

- `docs/architecture/`
- `docs/implementation/`
- `docs/operations/`
- `docs/executive/`
- `docs/documentation/`

Resultado esperado:

- espaço preparado para derivados sem poluir o Documento-Mestre.

---

## 6. Sequência Prática de Trabalho

Sequência curta recomendada:

1. preparar arquivos da raiz;
2. criar a árvore principal do monorepo;
3. criar esqueletos dos serviços centrais;
4. criar esqueletos dos engines centrais;
5. preparar `shared/`;
6. preparar `docs/` e `tests/`;
7. revisar coerência da estrutura com o Documento-Mestre;
8. registrar o resultado em `HANDOFF.md` e `CHANGELOG.md`.

---

## 7. Critérios de Aceite

A Sprint 1 só deve ser considerada concluída quando:

- o repositório puder ser aberto sem ambiguidade estrutural;
- a árvore principal estiver coerente com a arquitetura definida;
- os principais diretórios-base existirem;
- a raiz já expressar convenções mínimas do projeto;
- `shared/` estiver preparado para contratos, schemas, tipos e eventos;
- os serviços e engines nucleares possuírem esqueletos mínimos;
- o próximo agente conseguir iniciar a Sprint 2 sem reinventar a estrutura.

---

## 8. Riscos a Evitar

- criar mais diretórios do que o necessário neste primeiro corte;
- antecipar implementação funcional complexa dentro da Sprint 1;
- misturar documentação canônica com runbooks e planos operacionais;
- criar estruturas ad hoc fora da topologia definida;
- abrir múltiplos padrões de organização antes do primeiro padrão estar estável.

---

## 9. Como Validar a Sprint

Checagens mínimas:

- a árvore do repositório existe conforme o plano;
- a raiz contém os arquivos-base;
- os serviços e engines centrais possuem esqueletos mínimos;
- `docs/`, `tests/` e `shared/` já estão preparados;
- o `HANDOFF.md` e o `CHANGELOG.md` foram atualizados se a sprint tiver sido executada.

Comandos úteis:

```powershell
Get-ChildItem -Recurse
rg --files
```

---

## 10. Próximo Passo Após a Sprint 1

Após concluir a Sprint 1, o próximo passo natural é:

- iniciar a **Sprint 2 — Contratos e constituição**;
- começar a implementação inicial de:
  - contratos compartilhados;
  - schemas iniciais;
  - eventos internos mínimos;
  - base de identidade e princípios do sistema.

---

## 11. Síntese

A Sprint 1 não existe para “começar a programar o JARVIS” no sentido pleno.

Ela existe para:

- impedir retrabalho estrutural;
- estabilizar a topologia inicial do repositório;
- preparar a fundação semântica e técnica das próximas sprints;
- transformar o Documento-Mestre em base concreta de engenharia.
