# Service Breakdown

## 1. Objetivo

Este documento organiza a decomposicao inicial dos principais serviços do JARVIS para orientar implementacao.

Ele não redefine a arquitetura. Ele a traduz para um mapa técnico mais executável.

---

## 2. Serviços centrais do primeiro corte

Os serviços centrais do primeiro corte sóo:

- `orchestrator-service`
- `memory-service`
- `governance-service`
- `operational-service`
- `knowledge-service`
- `observability-service`

---

## 3. Função resumida por serviço

### 3.1 orchestrator-service

Responsavel por:

- receber entradas normalizadas;
- coordenar fluxo entre memória, cognição, governança, conhecimento, observabilidade e operação;
- produzir síntese final.

### 3.2 memory-service

Responsavel por:

- recuperar contexto util;
- registrar episodios;
- persistir continuidade de sessão;
- manter estado mínimo de missão;
- proteger memória crítica;
- sustentar continuidade de sessão e missão.

### 3.3 governance-service

Responsavel por:

- classificar risco;
- permitir, condicionar, bloquear ou adiar ação;
- proteger memória crítica;
- registrar decisão e auditoria.

### 3.4 operational-service

Responsavel por:

- executar tasks autorizadas;
- produzir artefatos textuais;
- devolver resultado estruturado ao núcleo.

### 3.5 knowledge-service

Responsavel por:

- registrar dominios;
- manter corpus local inicial;
- realizar retrieval determinístico;
- apoiar profundidade semântica do núcleo.

### 3.6 observability-service

Responsavel por:

- logs estruturados;
- persistencia da trilha de eventos;
- correlação entre fluxo, decisão, memória e operação;
- exportacao de trace view;
- espelhamento agentic opcional.

---

## 4. Ordem sugerida de maturacao

Ordem prática historica:

1. `orchestrator-service`
2. `memory-service`
3. `governance-service`
4. `operational-service`
5. `knowledge-service`
6. `observability-service`

Leitura prática atual:

- `orchestrator-service`: baseline integrado ativo
- `memory-service`: persistencia util ativa, com `PostgreSQL` validado como backend operacional do `v1` e `sqlite` mantido como fallback local
- `governance-service`: baseline robusto inicial ativo
- `operational-service`: operação de baixo risco ativa
- `knowledge-service`: retrieval inicial ativo, com ranking ponderado já absorvido ao baseline
- `observability-service`: ingestao, consulta, exportacao de trace view e espelhamento agentic inicial ativos para o `v1`

---

## 5. Regra de implementacao

Nenhum serviço deve nascer como centro soberano do sistema alem do núcleo de orquestracao.

Todos os demais devem:

- expor contratos claros;
- operar com rastreabilidade;
- permanecer substituiveis em nivel razoavel.
