# V1 Roadmap

## 1. Objetivo

Este documento resume o roadmap de execução do `v1` do JARVIS em nivel tatico, derivado do Documento-Mestre.

Ele complementa:

- `documento_mestre_jarvis.md`
- `docs/implementation/sprint-1-plan.md`
- `docs/implementation/first-milestone-plan.md`

---

## 2. Estrutura do roadmap

O `v1` e organizado em seis milestones:

1. `M1` - Fundacao estrutural
2. `M2` - Núcleo central funcional
3. `M3` - Memória e continuidade uteis
4. `M4` - Conhecimento e operação mínima real
5. `M5` - Governança robusta e observabilidade
6. `M6` - Consolidacao do v1 e preparacao para v2

---

## 3. Leitura correta

As milestones representam saltos estruturais de capacidade.

As sprints representam incrementos verificaveis dentro de cada milestone.

O roadmap existe para:

- reduzir acumulo caotico de features;
- manter a sequencia correta de construcao;
- impedir expansao antes da base estar estável.

---

## 4. Foco por milestone

### 4.1 M1

- fundação do repositório
- contratos e constituicao
- esqueletos dos serviços centrais

Status atual: concluida.

### 4.2 M2

- kernel do núcleo central
- interpretacao e roteamento
- cognição nuclear inicial

Status atual: substancialmente implementada, com engines iniciais e coordenacao central ativa.

### 4.3 M3

- backbone de memória
- recuperacao e gravacao uteis
- protecao e promoção básicas

Status atual: substancialmente implementada, com persistencia util e PostgreSQL validado como backend operacional do `v1`.

### 4.4 M4

- conhecimento inicial
- serviço operacional básico
- produção e execução de baixo risco

Status atual: parcialmente implementada, com retrieval local determinístico e operação textual estruturada.

### 4.5 M5

- política, risco e validação
- contencao, auditoria e protecao crítica
- observabilidade ampla do v1

Status atual: substancialmente implementada, com governança condicionada e observabilidade local benchmarkada como suficiente para o `v1`.

### 4.6 M6

- estabilidade do núcleo
- sandbox evolutivo inicial
- fechamento do v1

Status atual: em consolidacao, com benchmark dirigido implementado, `manual_variants` priorizado no `evolution-lab` e decisão final de fechamento ainda pendente.

---

## 5. Prioridade prática atual

O próximo corte de engenharia deve priorizar:

1. revisão dos derivados e do material de readiness para refletir o benchmark consolidado;
2. formalizacao de `PostgreSQL` como backend operacional recomendado do `v1`;
3. decisão de `go/no-go` para produção controlada;
4. só depois expansao de corpus, retrieval ou laboratório evolutivo.

---

## 6. Regra principal

Cada milestone só deve avancar quando:

- o núcleo anterior estiver estável o suficiente;
- os critérios mínimos de validação estiverem atendidos;
- a divida estrutural crítica estiver sob controle.
