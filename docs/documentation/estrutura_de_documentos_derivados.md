# Estrutura de Documentos Derivados

## 1. Objetivo

Este documento define como o projeto `jarvis` deve extrair documentacao derivada a partir do **Documento-Mestre do JARVIS**, preservando o mestre como artefato canonico e evitando duplicidade estrutural descontrolada.

Seu objetivo e responder:

- o que deve permanecer no Documento-Mestre;
- o que pode ou deve virar documento derivado;
- como manter coerencia entre artefato canonico, documentos operacionais e documentacao tecnica auxiliar.

---

## 2. Principio geral

O **Documento-Mestre** continua sendo a referencia canonica de:

- identidade do sistema;
- missao, natureza e principios;
- arquitetura conceitual, logica e tecnica;
- contratos canonicos;
- governanca;
- posicionamento oficial de tecnologias;
- referencias arquiteturais oficiais por funcao;
- roadmap macro;
- criterios de maturidade e transicao.

Documentos derivados existem para aprofundar, operacionalizar ou segmentar partes do sistema sem inflar excessivamente o documento principal.

---

## 3. Regra de precedencia

Em caso de conflito:

1. o **Documento-Mestre** prevalece;
2. um **ADR formal** pode alterar o Documento-Mestre quando a mudanca for explicitamente promovida;
3. documentos derivados nao devem contradizer o Documento-Mestre sem revisao formal.

---

## 4. O que deve permanecer no Documento-Mestre

Devem permanecer no Documento-Mestre:

- definicoes constitucionais do sistema;
- taxonomias centrais;
- arquitetura oficial;
- decisoes estruturais;
- politicas de governanca e autonomia;
- regras oficiais de uso de referencias externas por funcao arquitetural;
- criterios formais de validacao e maturidade;
- visao e recorte oficial de `v1`, `v2` e `v3`;
- contratos e schemas canonicos em nivel normativo.

---

## 5. O que deve virar documento derivado

Devem preferencialmente virar documentos derivados:

- planos operacionais detalhados;
- planos de sprint;
- runbooks;
- playbooks de incidentes;
- checklists de readiness e go-live;
- politicas detalhadas de release;
- planos de benchmark e datasets;
- documentacao de implementacao por servico;
- documentacao de ownership e operacao de equipe;
- documentacao de interface e integracao em nivel tatico.

---

## 6. Classes recomendadas de derivados

### 6.1 Derivados operacionais

Funcao:

- orientar operacao real, incidentes, readiness, producao controlada e mudancas.

Exemplos:

- `docs/roadmap/programa-ate-v3.md`
- `docs/operations/v1-operational-baseline.md`
- `docs/operations/release-and-change-management.md`
- `docs/operations/incident-response.md`

### 6.2 Derivados de implementacao

Funcao:

- transformar arquitetura em plano executavel de engenharia.

Exemplos:

- `docs/implementation/post-v1-cycle-closure.md`
- `docs/implementation/v1-5-sprint-cycle.md`
- `docs/implementation/post-v1-sprint-cycle.md`
- `docs/implementation/implementation-strategy.md`
- `docs/implementation/service-breakdown.md`
- `docs/archive/implementation/sprint-1-plan.md`
- `docs/archive/implementation/first-milestone-plan.md`

### 6.3 Derivados arquiteturais especializados

Funcao:

- aprofundar uma parte especifica sem expandir demais o Documento-Mestre.

Exemplos:

- `docs/architecture/evolution-lab.md`
- `docs/future/architecture/voice-runtime.md`
- `docs/future/architecture/specialists-v2.md`

### 6.4 Derivados executivos

Funcao:

- resumir o sistema para publicos especificos.

Exemplos:

- `docs/executive/master-summary.md`
- `docs/executive/v1-scope-summary.md`

---

## 7. Regra de extracao

Um tema deve ser extraido do Documento-Mestre quando pelo menos uma destas condicoes for verdadeira:

- o detalhamento virou majoritariamente operacional;
- o tema muda com frequencia maior do que a arquitetura central;
- o conteudo passou a repetir o que ja existe no mestre;
- o bloco interessa mais a execucao diaria do que a definicao do sistema;
- a leitura do Documento-Mestre esta sendo prejudicada pelo crescimento do tema.

---

## 8. Regra de sincronizacao

Ao criar ou atualizar um derivado:

- registrar claramente de qual secao do Documento-Mestre ele deriva;
- nao redefinir conceitos constitucionais por conta propria;
- apontar para o Documento-Mestre quando o assunto for normativo;
- atualizar `HANDOFF.md` se a mudanca afetar continuidade operacional;
- registrar no `CHANGELOG.md` quando a mudanca for relevante.

---

## 9. Estrutura inicial recomendada

Estrutura sugerida:

```text
docs/
  architecture/
  implementation/
  operations/
  executive/
  documentation/
  archive/
  future/
```

---

## 10. Derivados ativos mais importantes

Os derivados ativos mais importantes, no estado atual do projeto, sao:

1. `docs/operations/v1-operational-baseline.md`
2. `docs/roadmap/programa-ate-v3.md`
3. `docs/implementation/post-v1-sprint-cycle.md`
4. `docs/implementation/post-v1-cycle-closure.md`
5. `docs/implementation/v1-5-sprint-cycle.md`
6. `docs/operations/release-and-change-management.md`
7. `docs/operations/incident-response.md`
8. `docs/implementation/implementation-strategy.md`
9. `docs/implementation/service-breakdown.md`
10. `docs/executive/master-summary.md`

Documentos historicos ou de futuro devem preferencialmente sair do caminho principal:

- historicos em `docs/archive/`
- temas pos-`v1` em `docs/future/`

---

## 11. Sintese

O Documento-Mestre deve permanecer como **constituicao do sistema**.

Os documentos derivados devem funcionar como:

- extensoes operacionais;
- aprofundamentos especializados;
- resumos segmentados;
- instrumentos de execucao e continuidade.

Essa separacao existe para reduzir duplicidade, preservar clareza e manter rastreabilidade entre visao, arquitetura e execucao.
