# V2 Sprint Cycle

## 1. Objetivo do ciclo atual

Este documento define o ciclo rolante oficial do `v2`.

Foco único do ciclo:

- `especialização controlada subordinada ao núcleo com memória relacional mais rica`

Ele sucede o primeiro ciclo do `v1.5` e transforma o runtime stateful de continuidade
em base para convocação governada de especialistas, sem antecipar superfícies amplas
ou autonomia agressiva.

Fontes de direção:

- `HANDOFF.md`
- `docs/roadmap/programa-ate-v3.md`
- `docs/implementation/v1-5-cycle-closure.md`
- `docs/architecture/technology-study.md`

Status desta versão do ciclo:

- Sprint 1 é a próxima sprint ativa.

---

## 2. Regra de leitura

Este documento é a fonte oficial do que entra em execução agora para `v2`.

Ele não substitui:

- o Documento-Mestre como visão canônica;
- o programa até `v3` como direção macro;
- o `HANDOFF.md` como retomada operacional.

---

## 3. Sequência oficial das sprints

1. Sprint 1 - contratos e fronteiras de convocação de especialistas subordinados
2. Sprint 2 - seleção governada de especialistas e handoff interno
3. Sprint 3 - memória relacional compartilhada entre núcleo e especialistas
4. Sprint 4 - primeiro especialista subordinado em `shadow mode`
5. Sprint 5 - evals, observabilidade e governança de convocação
6. Sprint 6 - consolidação do primeiro corte do `v2`

---

## 4. Sprint 1

### Objetivo

Definir como especialistas subordinados entram no sistema sem competir com o núcleo
nem quebrar governança, memória e observabilidade.

### Entregas obrigatórias

- contratos internos mínimos para convocação de especialistas;
- fronteiras explícitas entre núcleo, especialista e tool layer;
- hints estruturados de entrada e saída para handoff interno.

### Ordem de implementação

1. contratos;
2. fronteiras de runtime;
3. integração mínima no núcleo.

### Testes obrigatórios

- contratos validados sem quebrar o fluxo atual do orquestrador;
- especialista não responde diretamente ao usuário;
- ausência de regressão no baseline do `v1` e no fechamento do `v1.5`.

### Evidência esperada

- contratos internos materializados;
- decisão explícita de quando um especialista pode ou não ser convocado.

### Definição de pronto

- o sistema consegue distinguir tecnicamente uma convocação de especialista de uma operação comum do núcleo.

### Risco de desvio arquitetural

- transformar especialistas em segunda identidade do sistema.

---

## 5. Sprint 2

### Objetivo

Executar seleção governada de especialistas e handoff interno observável.

### Entregas obrigatórias

- modelo explícito de elegibilidade de especialista;
- handoff interno governado;
- rastreabilidade do especialista escolhido e do racional da escolha.

### Ordem de implementação

1. elegibilidade;
2. handoff;
3. integração com governança e observabilidade.

### Testes obrigatórios

- cenários com e sem especialista;
- bloqueio governado quando a convocação for inadequada;
- rastreabilidade do racional de escolha.

### Evidência esperada

- trilha observável da decisão de convocação;
- coerência entre intenção, contexto e especialista escolhido.

### Definição de pronto

- outro agente consegue entender por que um especialista foi ou não chamado sem inferir a partir do texto final.

### Risco de desvio arquitetural

- handoffs opacos ou convocações por heurística solta.

---

## 6. Sprint 3

### Objetivo

Criar memória relacional compartilhada entre núcleo e especialistas.

### Entregas obrigatórias

- estrutura mínima de memória relacional;
- ligação entre continuidade da sessão e contexto especializado;
- recuperação contextual útil para handoffs repetidos.

### Ordem de implementação

1. modelo relacional mínimo;
2. persistência e recuperação;
3. integração com handoff e síntese.

### Testes obrigatórios

- relações persistidas e recuperadas entre sessões relacionadas;
- especialista recebe contexto suficiente sem duplicar memória inteira;
- ausência de regressão na continuidade do `v1.5`.

### Evidência esperada

- recuperação relacional acima do estado atual de continuidade;
- ganho perceptível no contexto dos handoffs.

### Definição de pronto

- o núcleo mantém unidade enquanto compartilha contexto relacional útil com especialistas.

### Risco de desvio arquitetural

- criar memória especializada fragmentada e sem governo do núcleo.

---

## 7. Sprint 4

### Objetivo

Ligar o primeiro especialista subordinado em `shadow mode`, sem torná-lo superfície soberana.

### Entregas obrigatórias

- primeiro especialista convocável em regime controlado;
- resposta final ainda consolidada pelo núcleo;
- caminho de comparação entre fluxo com e sem especialista.

### Ordem de implementação

1. especialista inicial;
2. shadow mode;
3. comparação controlada.

### Testes obrigatórios

- especialista opera como extensão do núcleo;
- sombra comparativa sem regressão do caminho principal;
- saída estruturada compatível com síntese final do núcleo.

### Evidência esperada

- cenários em que o especialista agrega valor real;
- cenários em que o núcleo corretamente não o convoca.

### Definição de pronto

- o primeiro especialista existe como capacidade útil e subordinada, não como agente paralelo.

### Risco de desvio arquitetural

- ampliar especialistas cedo demais sem ganho mensurável.

---

## 8. Sprint 5

### Objetivo

Transformar convocação de especialistas em comportamento avaliável, comparável e governável.

### Entregas obrigatórias

- evals da convocação;
- observabilidade de handoff e retorno;
- critérios explícitos para manter, ajustar ou recuar.

### Ordem de implementação

1. métricas;
2. trilha observável;
3. integração com `evolution-lab`.

### Testes obrigatórios

- comparação entre núcleo puro e fluxo com especialista;
- anomalias e sinais ausentes detectáveis;
- proposals sandbox-only derivadas dos achados.

### Evidência esperada

- decisão baseada em evidência sobre utilidade do especialista;
- sinais suficientes para promoção ou contenção.

### Definição de pronto

- a convocação de especialistas pode ser julgada por evidência, não por impressão subjetiva.

### Risco de desvio arquitetural

- tratar benchmark ou framework externo como validação automática do desenho.

---

## 9. Sprint 6

### Objetivo

Consolidar o primeiro corte do `v2` e decidir o que segue para o ciclo seguinte.

### Entregas obrigatórias

- fechamento do ciclo com backlog classificado;
- decisão formal do que permanece no corte do `v2`;
- explicitação do que continua fora do foco imediato.

---

## 10. Definição de pronto do ciclo

O primeiro ciclo do `v2` será considerado pronto quando:

- especialistas subordinados operarem sem quebrar a unidade do núcleo;
- houver memória relacional mínima útil acima da continuidade do `v1.5`;
- a convocação de especialistas estiver observável, comparável e governada;
- o sistema tiver dado o primeiro salto real rumo à especialização controlada sem ampliar superfícies prematuramente.

---

## 11. Estudos externos autorizados neste ciclo

Os estudos externos continuam subordinados ao ciclo ativo.

Eles entram apenas quando ajudam diretamente o objetivo de `v2`:

- contratos de especialistas;
- handoffs internos;
- memória relacional e contexto compartilhado;
- convocação governada e observável.

Perguntas permitidas agora:

- `OpenHands`: ajuda a modelar o primeiro especialista técnico subordinado sem terceirizar o núcleo?
- `PydanticAI`: melhora contratos, outputs estruturados e previsibilidade de handoff sem substituir contratos canônicos?
- `Hermes Agent`: oferece referência útil de runtime persistente e estado compartilhado para especialistas?
- `Graphiti`: oferece modelo útil de memória relacional e timeline sem exigir absorção ampla imediata?
- `Zep`: oferece ideia reutilizável para memória temporal e recuperação contextual no recorte do `v2`?
- `LangGraph`: justifica absorção mais forte em handoffs internos além do subfluxo de continuidade já consolidado?
- `OpenAI Agents SDK`: ensina algo útil sobre handoffs e tracing interno sem transformar o JARVIS em colagem de agentes?

Regra:

- estudo não bloqueia sprint;
- estudo não redefine a prioridade do ciclo;
- estudo entra para responder uma lacuna concreta de especialistas, memória ou handoff;
- conclusão de estudo deve cair em uma destas classes:
  - `absorver depois`
  - `usar como referência`
  - `rejeitar`

Fica explicitamente fora do foco deste ciclo:

- `computer use` amplo;
- voz como superfície oficial;
- memória profunda com `pgvector` como base obrigatória;
- assistente operacional amplo;
- autoaperfeiçoamento promotivo.
