# V1 Roadmap

## 1. Objetivo

Este documento resume o roadmap de execucao do `v1` do JARVIS em nivel tatico, derivado do Documento-Mestre.

Ele complementa:

- `documento_mestre_jarvis.md`
- `docs/implementation/sprint-1-plan.md`
- `docs/implementation/first-milestone-plan.md`

---

## 2. Estrutura do roadmap

O `v1` e organizado em seis milestones:

1. `M1` - Fundacao estrutural
2. `M2` - Nucleo central funcional
3. `M3` - Memoria e continuidade uteis
4. `M4` - Conhecimento e operacao minima real
5. `M5` - Governanca robusta e observabilidade
6. `M6` - Consolidacao do v1 e preparacao para v2

---

## 3. Leitura correta

As milestones representam saltos estruturais de capacidade.

As sprints representam incrementos verificaveis dentro de cada milestone.

O roadmap existe para:

- reduzir acumulo caotico de features;
- manter a sequencia correta de construcao;
- impedir expansao antes da base estar estavel.

---

## 4. Foco por milestone

### 4.1 M1

- fundacao do repositorio
- contratos e constituicao
- esqueletos dos servicos centrais

Status atual: concluida.

### 4.2 M2

- kernel do nucleo central
- interpretacao e roteamento
- cognicao nuclear inicial

Status atual: substancialmente implementada, com engines iniciais e coordenacao central ativa.

### 4.3 M3

- backbone de memoria
- recuperacao e gravacao uteis
- protecao e promocao basicas

Status atual: substancialmente implementada, com persistencia util e PostgreSQL validado como backend operacional do `v1`.

### 4.4 M4

- conhecimento inicial
- servico operacional basico
- producao e execucao de baixo risco

Status atual: parcialmente implementada, com retrieval local deterministico e operacao textual estruturada.

### 4.5 M5

- politica, risco e validacao
- contencao, auditoria e protecao critica
- observabilidade ampla do v1

Status atual: substancialmente implementada, com governanca condicionada e observabilidade local benchmarkada como suficiente para o `v1`.

### 4.6 M6

- estabilidade do nucleo
- sandbox evolutivo inicial
- fechamento do v1

Status atual: em consolidacao, com benchmark dirigido implementado, `manual_variants` priorizado no `evolution-lab` e decisao final de fechamento ainda pendente.

---

## 5. Prioridade pratica atual

O proximo corte de engenharia deve priorizar:

1. revisao dos derivados e do material de readiness para refletir o benchmark consolidado;
2. formalizacao de `PostgreSQL` como backend operacional recomendado do `v1`;
3. decisao de `go/no-go` para producao controlada;
4. so depois expansao de corpus, retrieval ou laboratorio evolutivo.

---

## 6. Regra principal

Cada milestone so deve avancar quando:

- o nucleo anterior estiver estavel o suficiente;
- os criterios minimos de validacao estiverem atendidos;
- a divida estrutural critica estiver sob controle.
