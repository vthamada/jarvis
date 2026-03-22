# Post-v1 Sprint Cycle

## 1. Objetivo do ciclo atual

Este documento define o ciclo rolante oficial das proximas `6` sprints do JARVIS no
inicio do `pos-v1`.

Foco unico do ciclo:

- `continuidade profunda entre missoes`

Ele traduz o programa em execucao concreta e deve ser revisado ao fim deste ciclo. A
proxima versao deve substituir esta e, quando fizer sentido, a versao anterior deve ser
preservada em `docs/archive/implementation/`.

Fontes de direcao:

- `HANDOFF.md`
- `docs/roadmap/programa-ate-v3.md`
- `docs/architecture/technology-study.md`

Status desta versao do ciclo:

- Sprint 1 concluida;
- Sprint 2 concluida;
- Sprint 3 concluida;
- Sprint 4 concluida;
- Sprint 5 passa a ser a proxima sprint ativa.

---

## 2. Regra de leitura

Este documento e a fonte oficial do que entra em execucao agora.

Ele nao substitui:

- o Documento-Mestre como visao canonica;
- o programa ate `v3` como direcao macro;
- o `HANDOFF.md` como retomada operacional.

Ele existe para deixar fechados:

- objetivo de cada sprint;
- ordem de implementacao;
- dependencias;
- testes obrigatorios;
- evidencia esperada;
- definicao de pronto.

---

## 3. Sequencia oficial das sprints

1. Sprint 1 - modelo de continuidade entre missoes e contratos internos
2. Sprint 2 - recuperacao e ranking de continuidade relacionada
3. Sprint 3 - decisao de continuidade no planejamento e na orquestracao
4. Sprint 4 - sintese e memoria de continuidade
5. Sprint 5 - observabilidade e evals da continuidade
6. Sprint 6 - consolidacao e decisao do corte para `v1.5`

---

## 4. Sprint 1

Status:

- concluida

### Objetivo

Definir como o sistema representa continuidade acima da missao atual sem quebrar o
baseline do `v1`.

### Entregas obrigatorias

- modelo interno de continuidade entre missoes relacionadas;
- contratos internos ou tipos compartilhados minimos para representar:
  - relacao entre missao atual e missao relacionada;
  - recomendacao de continuidade;
  - sinais minimos de prioridade e confianca;
- delimitacao clara entre:
  - contexto da sessao atual;
  - estado da missao ativa;
  - continuidade relacionada acima da missao atual.

### Ordem de implementacao

1. tipos e estrutura interna de continuidade;
2. criterio inicial de relacionamento entre missoes;
3. leitura desses sinais no orquestrador e no planejamento.

### Dependencias e bloqueios

- nao reabrir contratos publicos do `v1` sem necessidade real;
- nao introduzir retrieval semantico amplo nesta sprint;
- nao depender de tecnologia externa para fechar o modelo.

### Testes obrigatorios

- representacao consistente do vinculo entre missoes;
- ausencia de regressao no fluxo normal do `v1`;
- conflito entre missao ativa e continuidade relacionada tratado sem colapsar o fluxo.

### Evidencia esperada

- exemplo reproduzivel de duas missoes relacionadas;
- decisao clara sobre qual sinal deve prevalecer.

### Definicao de pronto

- o sistema ja consegue diferenciar continuidade local de continuidade relacionada;
- o restante do ciclo pode evoluir sem ambiguidade conceitual.

### Risco de desvio arquitetural

- transformar continuidade em mais um canal de contexto indistinto.

Resultado registrado nesta rodada:

- modelo explicito de continuidade relacionada adicionado ao nucleo;
- memoria passou a recuperar candidatas de missao relacionada dentro da mesma sessao;
- orquestrador e planejamento passaram a receber esse sinal sem breaking change na API publica do `v1`;
- o plano deliberativo agora explicita a fonte da continuidade (`active_mission`, `related_mission` ou `fresh_request`).

---

## 5. Sprint 2

Status:

- concluida

### Objetivo

Recuperar e rankear continuidade relacionada de forma previsivel.

### Entregas obrigatorias

- estrategia de recuperacao entre missoes relacionadas;
- ranking deterministico inicial para continuidade;
- criterio de desempate entre missao ativa, loop aberto e missao relacionada.

### Ordem de implementacao

1. recuperacao;
2. ranking;
3. integracao controlada no `memory-service` e no orquestrador.

### Dependencias e bloqueios

- depende do modelo interno fechado na Sprint 1;
- ainda nao introduzir `pgvector` como parte obrigatoria;
- manter `PostgreSQL` e fallback local sem bifurcar comportamento funcional.

### Testes obrigatorios

- recuperacao entre instancias;
- ranking estavel em casos concorrentes;
- regressao de missao simples do `v1`.

### Evidencia esperada

- caso com tres candidatas de continuidade e escolha previsivel da melhor.

### Definicao de pronto

- a recuperacao relacionada passou a ser reprodutivel e auditavel.

### Risco de desvio arquitetural

- recuperar contexto demais e diluir a intencao da missao atual.

Resultado registrado nesta rodada:

- `memory-service` passou a recuperar candidatas relacionadas com ordenacao deterministica;
- o ranking de continuidade agora diferencia missao ativa, loops abertos e missao relacionada;
- `planning-engine` e `orchestrator-service` passaram a receber recomendacao explicita de continuidade a partir da memoria.

---

## 6. Sprint 3

Status:

- concluida

### Objetivo

Fazer planejamento e orquestracao decidirem explicitamente entre continuar, encerrar,
reformular ou retomar contexto relacionado.

### Entregas obrigatorias

- decisao de continuidade no `planning-engine`;
- ajuste do `orchestrator-service` para carregar sinais de continuidade relacionada;
- governanca aplicada quando a retomada implicar mudanca sensivel de direcao.

### Ordem de implementacao

1. criterio de decisao no planejamento;
2. integracao no orquestrador;
3. endurecimento de governanca quando necessario.

### Dependencias e bloqueios

- depende da recuperacao e do ranking da Sprint 2;
- nao transformar o orquestrador em heuristica espalhada;
- nao introduzir runtime novo como dependencia desta decisao.

### Testes obrigatorios

- continuar a missao correta;
- encerrar loop explicitamente;
- reformular quando houver conflito real;
- retomar contexto relacionado sem parecer deriva arbitraria.

### Evidencia esperada

- trilha audivel de decisao por `request_id` mostrando por que o sistema escolheu um dos
  quatro caminhos.

### Definicao de pronto

- a decisao de continuidade deixa de ser implicita e vira comportamento observavel.

### Risco de desvio arquitetural

- esconder a decisao em sintese final sem lastro no planejamento.

Resultado registrado nesta rodada:

- `planning-engine` passou a decidir explicitamente entre `continuar`, `encerrar`, `reformular` e `retomar`;
- o plano deliberativo agora carrega `continuity_reason` e a decisao de continuidade deixa rastro legivel;
- `orchestrator-service` passou a emitir `continuity_decided` por `request_id`;
- `governance-service` endureceu a leitura de retomada relacionada quando ainda ha loop critico aberto;
- `synthesis-engine` passou a refletir a decisao de continuidade tambem no caminho governado.

---

## 7. Sprint 4

Status:

- concluida

### Objetivo

Fazer memoria e sintese soarem como continuidade intencional de uma entidade unica.

### Entregas obrigatorias

- memoria de continuidade acima da missao atual;
- resumo reutilizavel orientado a continuidade;
- sintese final com tom de continuacao, encerramento ou reformulacao coerente.

### Ordem de implementacao

1. persistencia de sinais de continuidade;
2. reutilizacao desses sinais;
3. ajuste da sintese final.

### Dependencias e bloqueios

- depende da decisao explicita de continuidade da Sprint 3;
- nao expor pipeline interno na resposta final;
- nao mascarar erro de recuperacao com texto convincente.

### Testes obrigatorios

- continuidade percebida entre missoes relacionadas;
- encerramento coerente;
- reformulacao coerente;
- ausencia de regressao em sessoes simples.

### Evidencia esperada

- comparacao antes/depois da resposta sintetizada para o mesmo conjunto de cenarios.

### Definicao de pronto

- a resposta final transmite continuidade real, nao apenas contexto reaproveitado.

### Risco de desvio arquitetural

- melhorar o tom sem melhorar o raciocinio que sustenta o tom.

Resultado registrado nesta rodada:

- `memory-service` passou a persistir continuidade da sessao acima da missao atual;
- a recuperacao agora reaproveita um resumo reutilizavel orientado a continuidade;
- `synthesis-engine` passou a emitir uma linha de continuidade ativa coerente com o estado do nucleo;
- `orchestrator-service` passou a injetar esses sinais na sintese sem expor pipeline interno.

---

## 8. Sprint 5

### Objetivo

Tornar a continuidade profunda observavel, comparavel e auditavel.

### Entregas obrigatorias

- eventos e sinais minimos para trilha de continuidade;
- visao de anomalias ou falhas de continuidade;
- evals ou benchmark dirigidos para os cenarios do ciclo;
- insumos para `internal pilot report` e `evolution-lab`.

### Ordem de implementacao

1. ampliar trilha observavel;
2. definir cenarios de avaliacao;
3. integrar analise de falhas e sinais ao laboratorio sandbox.

### Dependencias e bloqueios

- depende do comportamento funcional real das Sprints 1 a 4;
- nao usar observabilidade apenas como log passivo;
- nao mudar o baseline do `v1` por causa de eval isolada.

### Testes obrigatorios

- eventos de continuidade presentes na trilha;
- relatorio de piloto identifica lacunas dessa trilha;
- benchmark/eval diferencia comportamento forte de comportamento fraco.

### Evidencia esperada

- relatorio mostrando casos saudaveis, ambiguos e problematicos.

### Definicao de pronto

- a equipe consegue medir continuidade, nao apenas descreve-la.

### Risco de desvio arquitetural

- auditar muito pouco ou auditar sem perguntas concretas.

---

## 9. Sprint 6

### Objetivo

Consolidar o primeiro ciclo e decidir formalmente o corte entre `v1.5` e `v2`.

### Entregas obrigatorias

- fechamento do ciclo com backlog classificado;
- decisao formal do que sobe para `v1.5`;
- explicito do que fica fora e segue para `v2`;
- revisao do proprio plano rolante para o proximo ciclo.

### Ordem de implementacao

1. consolidar evidencia funcional e operacional;
2. classificar achados e backlog;
3. reescrever o plano rolante seguinte.

### Dependencias e bloqueios

- depende da evidencia produzida nas sprints anteriores;
- nao antecipar `v2` sem criterio;
- nao deixar descoberta tecnologica substituir decisao de produto e arquitetura.

### Testes obrigatorios

- bateria final dos cenarios do ciclo;
- ausencia de regressao sobre o baseline do `v1`;
- criterio claro de subida para `v1.5`.

### Evidencia esperada

- documento de fechamento do ciclo com decisao de corte;
- proxima versao do plano rolante pronta.

### Definicao de pronto

- outro agente consegue iniciar o ciclo seguinte sem reinterpretar a estrategia.

### Risco de desvio arquitetural

- empurrar decisoes de corte para frente e manter o `pos-v1` indefinido.

---

## 10. Estudos externos autorizados neste ciclo

Os estudos externos seguem paralelos e subordinados a este ciclo.

Perguntas permitidas agora:

- `LangGraph`: melhora checkpoint, replay ou HITL da trilha de continuidade?
- `Hermes Agent`: ensina algo util sobre runtime persistente e continuidade?
- `Graphiti`: oferece modelo util de memoria de relacoes e timeline?
- `Zep`: oferece ideia reutilizavel para memoria temporal e recuperacao de contexto?

Regra:

- estudo nao bloqueia sprint;
- estudo nao redefine prioridade do ciclo;
- conclusao de estudo deve cair em uma destas classes:
  - `absorver depois`
  - `usar como referencia`
  - `rejeitar`

---

## 11. Definicao de pronto do ciclo inteiro

O primeiro ciclo do `pos-v1` sera considerado pronto quando:

- continuidade profunda entre missoes estiver funcional e observavel;
- a diferenca entre missao ativa e missao relacionada estiver clara no nucleo;
- planejamento decidir explicitamente entre continuar, encerrar, reformular ou retomar;
- a sintese final soar como entidade unica entre missoes relacionadas;
- os estudos externos tiverem resposta objetiva para a trilha principal;
- houver decisao formal sobre o que sobe para `v1.5` e o que fica para `v2`.
