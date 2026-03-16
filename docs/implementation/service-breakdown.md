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
- classificar intencao;
- coordenar fluxo entre memoria, cognicao, governanca e operacao;
- produzir sintese final.

### 3.2 memory-service

Responsavel por:

- recuperar contexto util;
- registrar episodios;
- proteger memoria critica;
- sustentar continuidade de sessao e missao.

### 3.3 governance-service

Responsavel por:

- classificar risco;
- permitir, condicionar ou bloquear acao;
- proteger memoria critica;
- registrar decisao e auditoria.

### 3.4 operational-service

Responsavel por:

- executar tasks autorizadas;
- orquestrar adaptadores;
- produzir artefatos;
- devolver resultado estruturado ao nucleo.

### 3.5 knowledge-service

Responsavel por:

- registrar dominios;
- indexar conhecimento;
- realizar retrieval;
- apoiar profundidade semantica do nucleo.

### 3.6 observability-service

Responsavel por:

- logs estruturados;
- traces;
- metricas;
- correlacao entre fluxo, decisao, memoria e operacao.

---

## 4. Ordem sugerida de maturacao

Ordem pratica:

1. `orchestrator-service`
2. `memory-service`
3. `governance-service`
4. `operational-service`
5. `knowledge-service`
6. `observability-service`

---

## 5. Regra de implementacao

Nenhum servico deve nascer como centro soberano do sistema alem do nucleo de orquestracao.

Todos os demais devem:

- expor contratos claros;
- operar com rastreabilidade;
- permanecer substituiveis em nivel razoavel.
