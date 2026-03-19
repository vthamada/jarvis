# Service Breakdown

## 1. Objetivo

Este documento organiza a decomposicao inicial dos principais servicos do JARVIS para orientar implementacao.

Ele nao redefine a arquitetura. Ele a traduz para um mapa tecnico mais executavel.

---

## 2. Servicos centrais do primeiro corte

Os servicos centrais do primeiro corte sao:

- `orchestrator-service`
- `memory-service`
- `governance-service`
- `operational-service`
- `knowledge-service`
- `observability-service`

---

## 3. Funcao resumida por servico

### 3.1 orchestrator-service

Responsavel por:

- receber entradas normalizadas;
- coordenar fluxo entre memoria, cognicao, governanca, conhecimento, observabilidade e operacao;
- produzir sintese final.

### 3.2 memory-service

Responsavel por:

- recuperar contexto util;
- registrar episodios;
- persistir continuidade de sessao;
- manter estado minimo de missao;
- proteger memoria critica;
- sustentar continuidade de sessao e missao.

### 3.3 governance-service

Responsavel por:

- classificar risco;
- permitir, condicionar, bloquear ou adiar acao;
- proteger memoria critica;
- registrar decisao e auditoria.

### 3.4 operational-service

Responsavel por:

- executar tasks autorizadas;
- produzir artefatos textuais;
- devolver resultado estruturado ao nucleo.

### 3.5 knowledge-service

Responsavel por:

- registrar dominios;
- manter corpus local inicial;
- realizar retrieval deterministico;
- apoiar profundidade semantica do nucleo.

### 3.6 observability-service

Responsavel por:

- logs estruturados;
- persistencia da trilha de eventos;
- correlacao entre fluxo, decisao, memoria e operacao;
- exportacao de trace view;
- espelhamento agentic opcional.

---

## 4. Ordem sugerida de maturacao

Ordem pratica historica:

1. `orchestrator-service`
2. `memory-service`
3. `governance-service`
4. `operational-service`
5. `knowledge-service`
6. `observability-service`

Leitura pratica atual:

- `orchestrator-service`: baseline integrado ativo
- `memory-service`: persistencia util ativa, com `PostgreSQL` validado como backend operacional do `v1` e `sqlite` mantido como fallback local
- `governance-service`: baseline robusto inicial ativo
- `operational-service`: operacao de baixo risco ativa
- `knowledge-service`: retrieval inicial ativo, com ranking ponderado ja absorvido ao baseline
- `observability-service`: ingestao, consulta, exportacao de trace view e espelhamento agentic inicial ativos para o `v1`

---

## 5. Regra de implementacao

Nenhum servico deve nascer como centro soberano do sistema alem do nucleo de orquestracao.

Todos os demais devem:

- expor contratos claros;
- operar com rastreabilidade;
- permanecer substituiveis em nivel razoavel.
