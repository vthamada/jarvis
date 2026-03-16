# Estrutura de Documentos Derivados

## 1. Objetivo

Este documento define como o projeto `jarvis` deve extrair documentação derivada a partir do **Documento-Mestre do JARVIS**, preservando o mestre como artefato canônico e evitando duplicidade estrutural descontrolada.

Seu objetivo é responder:

- o que deve permanecer no Documento-Mestre;
- o que pode ou deve virar documento derivado;
- como manter coerência entre artefato canônico, documentos operacionais e documentação técnica auxiliar.

---

## 2. Princípio geral

O **Documento-Mestre** continua sendo a referência canônica de:

- identidade do sistema;
- missão, natureza e princípios;
- arquitetura conceitual, lógica e técnica;
- contratos canônicos;
- governança;
- posicionamento oficial de tecnologias;
- roadmap macro;
- critérios de maturidade e transição.

Documentos derivados existem para aprofundar, operacionalizar ou segmentar partes do sistema sem inflar excessivamente o documento principal.

---

## 3. Regra de precedência

Em caso de conflito:

1. o **Documento-Mestre** prevalece;
2. um **ADR formal** pode alterar o Documento-Mestre quando a mudança for explicitamente promovida;
3. documentos derivados não devem contradizer o Documento-Mestre sem revisão formal.

---

## 4. O que deve permanecer no Documento-Mestre

Devem permanecer no Documento-Mestre:

- definições constitucionais do sistema;
- taxonomias centrais;
- arquitetura oficial;
- decisões estruturais;
- políticas de governança e autonomia;
- critérios formais de validação e maturidade;
- visão e recorte oficial de `v1`, `v2` e `v3`;
- contratos e schemas canônicos em nível normativo.

---

## 5. O que deve virar documento derivado

Devem preferencialmente virar documentos derivados:

- planos operacionais detalhados;
- planos de sprint;
- runbooks;
- playbooks de incidentes;
- checklists de readiness e go-live;
- políticas detalhadas de release;
- planos de benchmark e datasets;
- documentação de implementação por serviço;
- documentação de ownership e operação de equipe;
- documentação de interface e integração em nível tático.

---

## 6. Classes recomendadas de derivados

### 6.1 Derivados operacionais

Função:

- orientar operação real, incidentes, readiness, produção controlada e mudanças.

Exemplos:

- `docs/operations/v1-production-controlled.md`
- `docs/operations/release-and-change-management.md`
- `docs/operations/incident-response.md`
- `docs/operations/go-live-readiness.md`

### 6.2 Derivados de implementação

Função:

- transformar arquitetura em plano executável de engenharia.

Exemplos:

- `docs/implementation/sprint-1-plan.md`
- `docs/implementation/service-breakdown.md`
- `docs/implementation/first-milestone-plan.md`

### 6.3 Derivados arquiteturais especializados

Função:

- aprofundar uma parte específica sem expandir demais o Documento-Mestre.

Exemplos:

- `docs/architecture/voice-runtime.md`
- `docs/architecture/specialists-v2.md`
- `docs/architecture/evolution-lab.md`

### 6.4 Derivados executivos

Função:

- resumir o sistema para públicos específicos.

Exemplos:

- `docs/executive/master-summary.md`
- `docs/executive/v1-scope-summary.md`

---

## 7. Regra de extração

Um tema deve ser extraído do Documento-Mestre quando pelo menos uma destas condições for verdadeira:

- o detalhamento virou majoritariamente operacional;
- o tema muda com frequência maior do que a arquitetura central;
- o conteúdo passou a repetir o que já existe no mestre;
- o bloco interessa mais à execução diária do que à definição do sistema;
- a leitura do Documento-Mestre está sendo prejudicada pelo crescimento do tema.

---

## 8. Regra de sincronização

Ao criar ou atualizar um derivado:

- registrar claramente de qual seção do Documento-Mestre ele deriva;
- não redefinir conceitos constitucionais por conta própria;
- apontar para o Documento-Mestre quando o assunto for normativo;
- atualizar `HANDOFF.md` se a mudança afetar continuidade operacional;
- registrar no `CHANGELOG.md` quando a mudança for relevante.

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
```

---

## 10. Próximos derivados mais naturais

Os primeiros documentos derivados mais naturais, no estado atual do projeto, são:

1. `docs/implementation/sprint-1-plan.md`
2. `docs/operations/v1-production-controlled.md`
3. `docs/operations/release-and-change-management.md`
4. `docs/operations/incident-response.md`
5. `docs/operations/go-live-readiness.md`
6. `docs/executive/master-summary.md`

---

## 11. Síntese

O Documento-Mestre deve permanecer como **constituição do sistema**.

Os documentos derivados devem funcionar como:

- extensões operacionais;
- aprofundamentos especializados;
- resumos segmentados;
- instrumentos de execução e continuidade.

Essa separação existe para reduzir duplicidade, preservar clareza e manter rastreabilidade entre visão, arquitetura e execução.
