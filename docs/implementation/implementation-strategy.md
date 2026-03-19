# Implementation Strategy

## 1. Objetivo

Este documento resume a estrategia pratica de implementacao do `v1` do JARVIS em formato de execucao de engenharia.

Ele deriva principalmente do capitulo `286. Estrategia detalhada de implementacao do v1 passo a passo`.

---

## 2. Principios

A implementacao do `v1` deve obedecer a:

- fundacao antes de feature;
- contrato antes de integracao complexa;
- identidade antes de automacao ampla;
- governanca antes de autonomia expandida;
- observabilidade desde o inicio;
- incrementos uteis e testaveis;
- estado persistente onde isso for estruturalmente importante.

---

## 3. Sequencia geral

Sequencia recomendada para o `v1`:

1. alinhar baseline tecnico e documental;
2. consolidar memoria persistente e continuidade;
3. estruturar observabilidade minima do fluxo;
4. fortalecer engines, conhecimento e operacao util;
5. endurecer governanca para o `v1`;
6. consolidar benchmark, readiness e decisao de fechamento para producao controlada.

---

## 4. Leitura pratica das fases

### 4.1 Fase 0

Preparar o repositorio e o ambiente.

### 4.2 Fase 1

Criar a base semantica compartilhada.

### 4.3 Fase 2

Fazer o nucleo central responder de forma coerente.

### 4.4 Fase 3

Adicionar memoria util e continuidade.

### 4.5 Fase 4

Ativar governanca minima robusta.

### 4.6 Fase 5

Adicionar operacao real de baixo risco.

### 4.7 Fase 6

Aprofundar conhecimento e dominios prioritarios.

### 4.8 Fase 7

Fortalecer observabilidade e estabilidade operacional.

### 4.9 Fase 8

Preparar o sandbox evolutivo inicial.

---

## 5. Estado pratico atual

O repositorio ja saiu da fundacao estrutural e possui um baseline integrado do `v1` validado por benchmark dirigido.

Hoje o baseline implementado cobre:

- `orchestrator-service` como coordenador do fluxo;
- `memory-service` com persistencia util, `sqlite` como fallback local e `PostgreSQL` validado como backend operacional do `v1` local;
- `governance-service` com decisao simples, condicionada, bloqueada e adiada para validacao;
- `knowledge-service` com retrieval deterministico local, corpus curado externo ao codigo e ranking ponderado ja absorvido ao baseline;
- `operational-service` com artefatos textuais de baixo risco;
- `observability-service` com trilha de eventos persistida e validada para o `v1`;
- `evolution-lab` com comparacao sandbox-only entre baseline e candidata, priorizando `manual_variants`;
- `engines/` dedicadas para identidade, executivo, planejamento, cognicao e sintese.

Leitura de milestone:

- `M1` concluida
- `M2` substancialmente implementada
- `M3` substancialmente implementada e validada com PostgreSQL
- `M4` parcialmente implementada
- `M5` substancialmente implementada
- `M6` em consolidacao final

---

## 6. Proxima sequencia de engenharia

Sequencia recomendada a partir do estado atual:

1. revisar os documentos derivados e o material de readiness para refletir o baseline benchmarkado;
2. tratar `PostgreSQL` como caminho operacional recomendado do `v1`, mantendo `sqlite` como fallback local;
3. decidir formalmente se o baseline atual ja permite fechar o `v1` para producao controlada;
4. so depois reabrir expansao de corpus, retrieval mais forte ou evolucao mais sofisticada.

---

## 7. Regra de execucao

Nao implementar modulos isolados apenas por completude estrutural.

Implementar ciclos integrados de capacidade, em que cada etapa:

- produz valor verificavel;
- deixa base reaproveitavel para a proxima;
- reduz risco de retrabalho.
