# Implementation Strategy

## 1. Objetivo

Este documento resume a estratégia prática de implementação do `v1` do JARVIS em formato de execução de engenharia.

Ele deriva principalmente do capítulo `286. Estratégia detalhada de implementação do v1 passo a passo`.

---

## 2. Princípios

A implementação do `v1` deve obedecer a:

- fundação antes de feature;
- contrato antes de integração complexa;
- identidade antes de automação ampla;
- governança antes de autonomia expandida;
- observabilidade desde o início;
- incrementos úteis e testáveis;
- estado persistente onde isso for estruturalmente importante.

---

## 3. Sequência geral

Sequência recomendada:

1. alinhar baseline tecnico e documental;
2. consolidar persistencia de memoria e continuidade;
3. estruturar observabilidade minima do fluxo;
4. fortalecer engines, conhecimento e operacao util;
5. endurecer governanca para o `v1`;
6. preparar consolidacao do `v1` e sandbox evolutivo inicial.

---

## 4. Leitura prática das fases

### 4.1 Fase 0

Preparar o repositório e o ambiente.

### 4.2 Fase 1

Criar a base semântica compartilhada.

### 4.3 Fase 2

Fazer o nucleo central responder de forma coerente.

### 4.4 Fase 3

Adicionar memória útil e continuidade.

### 4.5 Fase 4

Ativar governança mínima robusta.

### 4.6 Fase 5

Adicionar operação real de baixo risco.

### 4.7 Fase 6

Aprofundar conhecimento e domínios prioritários.

### 4.8 Fase 7

Fortalecer observabilidade e estabilidade operacional.

### 4.9 Fase 8

Preparar o sandbox evolutivo inicial.

---

## 5. Estado pratico atual

O repositorio ja concluiu a fundacao estrutural e o primeiro fluxo funcional minimo.

Hoje o baseline implementado cobre:

- `orchestrator-service` como coordenador do fluxo;
- `memory-service` com persistencia local de sessao e missao;
- `governance-service` com decisao simples e condicionada;
- `knowledge-service` com retrieval deterministico local e corpus curado externo ao codigo;
- `operational-service` com artefatos textuais de baixo risco;
- `observability-service` com trilha de eventos persistida;
- `evolution-lab` com comparacao sandbox-only entre baseline e candidata;
- `engines/` dedicadas para identidade, executivo, planejamento, cognicao e sintese.

Leitura de milestone:

- `M1` concluida
- `M2` parcialmente concluida
- `M3` substancialmente implementada
- `M4` parcialmente implementada
- `M5` parcialmente implementada
- `M6` iniciada no baseline local

---

## 6. Proxima sequencia de engenharia

Sequencia recomendada a partir do estado atual:

1. padronizar ambiente de dev com `pip install -e .[dev]`;
2. confirmar `pytest -q` e `ruff check .` em ambiente limpo;
3. elevar a persistencia de memoria para `PostgreSQL` operacional;
4. ampliar corpus e retrieval do `knowledge-service`;
5. fortalecer benchmark, readiness e qualidade do `evolution-lab`.

---

## 7. Regra de execução

Nao implementar modulos isolados apenas por completude estrutural.

Implementar ciclos integrados de capacidade, em que cada etapa:

- produz valor verificável;
- deixa base reaproveitável para a próxima;
- reduz risco de retrabalho.
