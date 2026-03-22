# Service Breakdown

## 1. Objetivo

Este documento organiza a decomposição dos principais serviços do JARVIS para orientar implementação e leitura técnica.

Ele não redefine a arquitetura. Ele a traduz para um mapa técnico executável e coerente com o estado atual do repositório.

---

## 2. Serviços centrais ativos

Os serviços centrais do baseline atual são:

- `orchestrator-service`
- `memory-service`
- `governance-service`
- `operational-service`
- `knowledge-service`
- `observability-service`

---

## 3. Função resumida por serviço

### 3.1 `orchestrator-service`

Responsável por:

- receber entradas normalizadas;
- coordenar fluxo entre memória, cognição, governança, conhecimento, observabilidade e operação;
- decidir continuidade, incluindo missão ativa e missão relacionada;
- produzir a síntese final.

### 3.2 `memory-service`

Responsável por:

- recuperar contexto útil;
- registrar episódios;
- persistir continuidade de sessão;
- manter estado mínimo de missão;
- sustentar continuidade relacionada acima da missão atual;
- proteger memória crítica.

### 3.3 `governance-service`

Responsável por:

- classificar risco;
- permitir, condicionar, bloquear ou adiar ação;
- proteger memória crítica;
- registrar decisão e auditoria.

### 3.4 `operational-service`

Responsável por:

- executar tarefas autorizadas;
- produzir artefatos textuais;
- devolver resultado estruturado ao núcleo.

### 3.5 `knowledge-service`

Responsável por:

- registrar domínios;
- manter corpus curado local;
- realizar retrieval determinístico;
- apoiar profundidade semântica do núcleo sem reabrir o baseline do `v1`.

### 3.6 `observability-service`

Responsável por:

- persistir a trilha de eventos;
- correlacionar request, sessão, missão e operação;
- auditar fluxo recente;
- exportar trace view;
- espelhar traces para camada agentic complementar quando configurado.

---

## 4. Leitura prática do baseline

Estado funcional atual:

- `orchestrator-service`: baseline integrado ativo
- `memory-service`: persistência útil ativa, com `PostgreSQL` como backend operacional oficial e `sqlite` como fallback local
- `governance-service`: baseline robusto inicial ativo
- `operational-service`: operação de baixo risco ativa
- `knowledge-service`: retrieval inicial ativo, com ranking ponderado absorvido ao baseline
- `observability-service`: ingestão, consulta, auditoria e espelhamento agentic complementar ativos

---

## 5. Relação com o pós-v1

No ciclo atual do `pós-v1`, os serviços mais sensíveis são:

1. `memory-service`
2. `orchestrator-service`
3. `planning-engine`
4. `observability-service`

Motivo:

- a trilha ativa do ciclo é `continuidade profunda entre missões`;
- essa trilha exige recuperação, ranking, decisão e evidência, não expansão ampla de superfície.

---

## 6. Regra de implementação

Nenhum serviço deve nascer como centro soberano do sistema além do núcleo de orquestração.

Todos os demais devem:

- expor contratos claros;
- operar com rastreabilidade;
- permanecer substituíveis em nível razoável;
- servir ao núcleo central, não competir com ele.
