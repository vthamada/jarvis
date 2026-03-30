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

### 4.1 O que nao deve motivar reescrita integral do mestre

O Documento-Mestre nao deve ser reescrito do zero apenas porque:

- ficou extenso;
- exige leitura mais lenta do que os documentos de sprint;
- o backlog atual esta mais granular do que a sua formulacao;
- parte da implementacao ainda materializa apenas recortes funcionais do mapa completo.

A extensao do mestre e aceitavel enquanto ele continuar cumprindo o papel de constituicao
do sistema.

### 4.2 Quando mexer no mestre vale a pena

Alteracoes no Documento-Mestre valem a pena quando houver:

- contradicao com o estado real e oficial do repositorio;
- ambiguidade normativa que esteja gerando desvio recorrente de implementacao;
- ausencia de regra canonica necessaria para guiar novas fases;
- necessidade de reorganizar navegacao, indice, marcacao ou separacao entre
  visao permanente e direcao de fase.

### 4.3 O que deve ser reorganizado, sem reescrever a visao

Quando o mestre precisar de refatoracao, a prioridade deve ser:

- melhorar navegacao e indexacao;
- marcar melhor o que e permanente, o que e direcao arquitetural e o que e
  recorte de fase;
- reduzir repeticao de conteudo operacional que deveria viver em derivados;
- apontar com mais clareza para ADRs, ciclos, servicos e artefatos ativos;
- preservar a ontologia do sistema, o mapa de mentes, dominios e memorias e
  as decisoes canonicamente fechadas.

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

### 5.1 O que deve virar ponte entre visao e implementacao

Nao basta ter o Documento-Mestre e os ciclos de sprint. O projeto tambem
precisa de artefatos de traducao entre visao canonica e execucao real.

Devem existir, de forma explicita, mecanismos para responder:

- o que do mestre ja esta materializado;
- o que esta apenas tipado ou conceitual;
- o que esta implementado parcialmente;
- qual lacuna do mestre cada sprint fecha;
- qual parte ainda esta fora do foco do ciclo atual.

Essa ponte de execucao deve preferencialmente assumir estas formas:

- matriz de aderencia `Documento-Mestre x Implementacao`;
- registries canonicos de mentes, dominios e memorias com estado de maturidade;
- regra de cobertura por sprint indicando qual lacuna do mestre esta sendo tratada;
- criterios de promocao entre `conceitual`, `tipado`, `runtime parcial` e
  `runtime maduro`.

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

- `docs/archive/implementation/post-v1-cycle-closure.md`
- `docs/archive/implementation/v1-5-cycle-closure.md`
- `docs/archive/implementation/v2-sprint-cycle.md`
- `docs/archive/implementation/v1-5-sprint-cycle.md`
- `docs/archive/implementation/post-v1-sprint-cycle.md`
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
- `docs/archive/executive/v1-scope-summary.md`

### 6.5 Derivados de aderencia e traducao

Funcao:

- ligar o Documento-Mestre ao backlog real;
- reduzir descompasso entre visao canonica e implementacao incremental;
- tornar auditavel o que ja foi absorvido e o que ainda esta em lacuna.

Exemplos de conteudo adequado:

- matriz de aderencia por mentes, dominios e memorias;
- registries de maturidade por eixo canonico;
- quadro de correspondencia entre capitulo do mestre, servico e sprint alvo.

Artefato ativo nesta classe:

- `docs/documentation/matriz-de-aderencia-mestre.md`

Regra atual desta classe:

- a matriz de aderência não deve cobrir apenas `mentes`, `domínios` e `memórias`;
- ela deve funcionar como auditoria completa dos blocos canônicos do mestre;
- o backlog ativo deve se recalibrar a partir dessa auditoria, e não apenas da sprint em andamento.

---

## 7. Regra de extracao

Um tema deve ser extraido do Documento-Mestre quando pelo menos uma destas condicoes for verdadeira:

- o detalhamento virou majoritariamente operacional;
- o tema muda com frequencia maior do que a arquitetura central;
- o conteudo passou a repetir o que ja existe no mestre;
- o bloco interessa mais a execucao diaria do que a definicao do sistema;
- a leitura do Documento-Mestre esta sendo prejudicada pelo crescimento do tema.

### 7.1 Regra de nao-desvio

Sempre que a implementacao avancar em recortes muito pragmaticos, e necessario
perguntar:

- qual lacuna canonica do mestre esta sendo fechada;
- qual eixo esta ficando para tras;
- se o ciclo esta favorecendo runtime e entrega local, mas negligenciando
  mentes, dominios ou memorias previstas na visao oficial.

Se essas perguntas nao puderem ser respondidas com clareza, o problema nao e
o tamanho do mestre. O problema e ausencia de ponte entre visao e execucao.

---

## 8. Regra de sincronizacao

Ao criar ou atualizar um derivado:

- registrar claramente de qual secao do Documento-Mestre ele deriva;
- nao redefinir conceitos constitucionais por conta propria;
- apontar para o Documento-Mestre quando o assunto for normativo;
- atualizar `HANDOFF.md` se a mudanca afetar continuidade operacional;
- registrar no `CHANGELOG.md` quando a mudanca for relevante.

### 8.1 Regra de alinhamento do backlog com o mestre

Ao abrir ou atualizar um ciclo de sprint, deve ficar explicito:

- qual trecho do Documento-Mestre o ciclo aproxima;
- qual parte ainda permanece somente conceitual;
- qual eixo do mestre nao esta sendo coberto no ciclo atual;
- se o backlog esta puxando mais runtime local do que aderencia arquitetural.

Essa regra existe para evitar que o projeto fique eficiente demais em resolver
o curto prazo e fraco demais em materializar a visao canonica.

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
3. `docs/archive/implementation/post-v1-sprint-cycle.md`
4. `docs/archive/implementation/post-v1-cycle-closure.md`
5. `docs/archive/implementation/v1-5-cycle-closure.md`
6. `docs/archive/implementation/v2-sprint-cycle.md`
7. `docs/operations/release-and-change-management.md`
8. `docs/operations/incident-response.md`
9. `docs/implementation/implementation-strategy.md`
10. `docs/implementation/service-breakdown.md`
11. `docs/executive/master-summary.md`
12. `docs/documentation/matriz-de-aderencia-mestre.md`

Documentos historicos ou de futuro devem preferencialmente sair do caminho principal:

- historicos em `docs/archive/`
- temas pos-`v1` em `docs/future/`

---

## 11. Sintese

O Documento-Mestre deve permanecer como **constituicao do sistema**.

Os documentos derivados devem funcionar como:

- extensoes operacionais;
- aprofundamentos especializados;
- pontes de traducao entre visao e implementacao;
- resumos segmentados;
- instrumentos de execucao e continuidade.

Essa separacao existe para reduzir duplicidade, preservar clareza e manter rastreabilidade entre visao, arquitetura e execucao.
