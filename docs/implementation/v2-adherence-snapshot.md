# V2 Adherence Snapshot

## 1. Objetivo

Este documento registra um snapshot de aderencia entre o estado atual do repositorio,
a visao canonica do [documento_mestre_jarvis.md](d:/Users/DTI/Desktop/jarvis/documento_mestre_jarvis.md)
e a direcao operacional consolidada nos documentos vivos do projeto.

Ele existe para:

- identificar rapidamente onde o runtime ja esta coerente com a visao;
- separar gap real de deferimento correto por fase;
- orientar a escolha do proximo recorte funcional sem reabrir decisoes ja fechadas;
- manter backlog tecnico subordinado ao Documento-Mestre, e nao a conveniencias locais.

Leitura correta:

- o Documento-Mestre continua sendo a unica fonte canonica de visao;
- este arquivo e uma auditoria derivada e revisavel;
- [HANDOFF.md](d:/Users/DTI/Desktop/jarvis/HANDOFF.md) continua sendo a retomada tatico-operacional;
- [matriz-de-aderencia-mestre.md](d:/Users/DTI/Desktop/jarvis/docs/documentation/matriz-de-aderencia-mestre.md)
  continua sendo a taxonomia formal de status.

---

## 2. Fotografia atual

Estado de referencia desta revisao:

- data da fotografia: `2026-04-01`
- ultimo recorte funcional fechado: `v2-native-memory-scope-hardening-cut`
- ultimo recorte estrutural fechado: `v2-repository-hygiene-and-tools-review-cut`
- passo funcional em andamento: `domain-sovereignty-runtime-hardening`

Leitura executiva:

- nao existe hoje divergencia arquitetural grave entre o sistema e o Documento-Mestre;
- existe, sim, distancia de materializacao em alguns eixos centrais do `v2`, mas os gaps criticos diminuiram;
- dominios, especialistas promovidos e memoria guiada agora ja operam com contrato soberano ponta a ponta nas rotas promovidas do baseline atual;
- o que resta como backlog correto passa a ser maturacao declarativa adicional, nao correcao de desvio estrutural do `v2`;
- a soberania de dominios avancou mais um passo: rotas promovidas agora ja aparecem como `promoted_route_registry` soberano nos eventos do runtime, reduzindo recomputacao local no orquestrador e melhorando auditoria de elegibilidade.
- a malha dominio->especialista tambem avancou: packets guiados de memoria agora nascem da rota promovida elegivel do registry e sao validados contra o contrato canonico da rota antes da convocacao especializada.
- o contrato canonico da rota ativa passou a atravessar tambem o `planning` e a influenciar a `synthesis`, reduzindo a distancia entre memoria guiada disponivel e comportamento final do runtime.
- esse contrato agora tambem molda passos, restricoes e criterio de saida do plano, e ja aparece na leitura final como objetivo, entrega esperada, foco de leitura e workflow ativo da rota promovida.
- memoria, identidade, governanca, observabilidade e soberania do nucleo evoluiram de forma consistente;
- benchmark externo, memory gap e hardening nativo foram tratados corretamente como etapas subordinadas ao baseline,
  nao como desvio de direcao.

Em resumo:

- a visao esta preservada;
- o runtime esta coerente com a fase do programa;
- o backlog correto agora volta a ser funcional, nao estrutural.

---

## 3. Leitura por eixo

### 3.1 Nucleo central e fluxo principal

**Status:** `runtime parcial` - forte, sem divergencia material

O que esta aderente:

- o orquestrador permanece como autoridade suprema da relacao com o usuario;
- governanca, memoria, conhecimento, cognicao, especialistas, operacao e observabilidade
  continuam subordinados ao nucleo;
- LangGraph segue complementar e opcional, nao substituto do runtime principal.

Gap relevante:

- nenhum gap estrutural critico neste eixo.

Leitura:

- este eixo esta alinhado com a visao do mestre.

---

### 3.2 Identidade, missao e principios

**Status:** `runtime parcial` - consistente, com gate real

O que esta aderente:

- identidade entra no fluxo real;
- governanca ja audita coerencia de identidade;
- observabilidade ja trata alinhamento identitario como sinal de eixo.

Gap relevante:

- identidade ainda e mais forte como guardrail e trilha auditavel do que como checklist declarativo completo por request.

Leitura:

- nao ha divergencia de direcao; ha maturacao pendente.

---

### 3.3 Mentes canonicas

**Status:** `runtime parcial` - registry forte, arbitragem ainda hibrida

O que esta aderente:

- o projeto preserva a ontologia das 24 mentes;
- o registry de mentes existe e ja influencia composicao, suporte e tensao dominante;
- o eixo nao foi abandonado nem substituido por heuristica puramente solta.

Gap relevante:

- a arbitragem principal ja foi puxada para helpers soberanos do `mind_registry`, reduzindo regra espalhada no engine;
- a relacao entre mente, dominio e especialista ainda pode ficar mais explicita e menos implicita em consumidores posteriores.

Leitura:

- a visao foi respeitada, mas a materializacao ainda esta incompleta.

---

### 3.4 Dominios canonicos e rotas de runtime

**Status:** `runtime parcial` - principal gap funcional restante

O que esta aderente:

- o sistema ja possui registry canonico de dominios;
- a separacao entre ontologia canonica e rotas operacionais de runtime esta estabelecida;
- existem rotas promovidas, contratos de consumo por dominio, workflows e vinculos com especialistas;
- o `knowledge-service` agora da precedencia explicita a mencoes declaradas de rota runtime
  e dominio canonico do registry, com matching normalizado sem depender de acento.

Gap relevante:

- o `domain_registry` agora governa tambem o contrato soberano da rota primaria em `planning`, `memory`, `specialist`, `orchestrator` e observabilidade;
- `primary_route`, `primary_canonical_domain`, `consumer_objective`, `expected_deliverables`, `telemetry_focus` e `workflow_profile` ja atravessam o runtime sem recomposicao heuristica relevante fora do registry;
- o que sobra neste eixo e amadurecimento adicional de gates por `workflow_profile` e eventual expansao futura para novas rotas, nao correcao de baseline.

Leitura:

- este continua sendo o eixo mais importante para o proximo recorte funcional,
  mas o primeiro endurecimento ja entrou no baseline.

---

### 3.5 Memorias canonicas

**Status:** `runtime parcial` - avancou bastante, sem divergencia de visao

O que esta aderente:

- o sistema mantem a ideia de memoria estratificada e soberana;
- user scope nativo foi endurecido;
- recorrencia soberana de especialistas promovidos foi implementada ainda `through_core_only`;
- organization scope ficou corretamente bloqueado sem consumidor canonico soberano;
- benchmark e evidencia local evitaram reabrir absorcao externa por conveniencia.

Gap relevante:

- `semantic` e `procedural` agora entram como `runtime_partial` em packets guiados por dominio quando existe evidencia persistida e compatibilidade canonica;
- a politica que libera essas classes saiu de decisao espalhada no servi?o e passou a viver mais explicitamente no `memory_registry`;
- `planning` e `synthesis` ja usam esse apoio sem bypassar governanca, enquanto especialistas continuam presos ao contrato elegivel da rota promovida;
- a camada multicamada nativa ainda pode crescer antes de qualquer absorcao futura, mas isso ja e maturacao incremental, nao correcao urgente.

Leitura:

- este eixo esta consistente com a visao e com a fase atual.

---

### 3.6 Governanca, seguranca e autonomia

**Status:** `runtime parcial` - forte

O que esta aderente:

- o sistema preserva governanca como camada real, nao decorativa;
- decisoes de risco, bloqueio, deferimento e condicoes continuam no fluxo principal;
- a evolucao externa e os benchmarks continuam subordinados ao baseline soberano.

Gap relevante:

- ainda existe espaco para formalizar melhor governanca de memoria e politicas declarativas mais completas.

Leitura:

- sem divergencia material neste eixo.

---

### 3.7 Especialistas subordinados

**Status:** `runtime parcial` - malha promovida fechada, expansao futura pendente

O que esta aderente:

- especialistas continuam subordinados ao nucleo;
- nao existe concessao de identidade propria a especialistas;
- handoffs continuam `through_core_only` e `advisory_only` quando aplicavel;
- memoria compartilhada e recorrencia foram mantidas como mediacao do nucleo.

Gap relevante:

- hints, selecao, handoff e conclusao de especialistas promovidos agora dependem de rota canonica ativa, `linked_specialist_type`, `specialist_mode`, memoria guiada coerente e alinhamento com `primary_route` e `primary_canonical_domain`;
- a observabilidade passou a usar esses sinais diretamente para marcar `attention_required` quando houver drift;
- o que resta neste eixo e ampliar a mesma disciplina para expansoes futuras e formalizar melhor evolucoes alem do nivel promovido atual.

Leitura:

- o eixo esta na direcao certa, mas ainda nao atingiu a forma plena do mestre.

---

### 3.8 Observabilidade e evidencia

**Status:** `runtime parcial` - solido

O que esta aderente:

- o projeto ja opera com trilha auditavel, comparadores, baseline verification e engineering gate;
- decisoes de benchmark, closure de cuts e baseline release-grade ja entram como evidencia regeneravel.

Gap relevante:

- ainda cabe reduzir carga documental sem perder auditabilidade;
- parte dos sinais pode ficar mais consolidada por eixo ao longo dos proximos cortes.

Leitura:

- eixo consistente com a visao.

---

### 3.9 Evolucao, benchmark e absorcao externa

**Status:** `deferido por fase` - correto

O que esta aderente:

- benchmark governado foi usado como filtro de decisao, nao como atalho de arquitetura;
- `Mastra` e `AutoGPT Platform` ficaram como referencia;
- `Mem0` ficou em `absorver_depois` e depois foi mantido fechado por evidencia local insuficiente;
- nada externo assumiu o papel de cerebro do sistema.

Leitura:

- este eixo esta alinhado com a visao e com a sua direcao explicita para o projeto.

---

### 3.10 Voz, realtime e superficies amplas

**Status:** `deferido por fase` - correto

Leitura:

- continuam parte da visao, mas fora do caminho critico do `v2`.

---

## 4. Tabela consolidada

| Eixo | Status | Leitura atual | Prioridade |
|---|---|---|---|
| Nucleo / Orquestrador | runtime parcial | forte, sem gap material | baixa |
| Identidade | runtime parcial | operacional e auditavel | baixa |
| Mentes | runtime parcial | arbitragem ainda hibrida | media |
| Dominios | runtime parcial | contrato soberano ja atravessa o runtime promovido | media |
| Memorias | runtime parcial | eixo fortalecido e coerente | media |
| Governanca | runtime parcial | solida | baixa |
| Especialistas | runtime parcial | malha promovida fechada e auditavel | media |
| Observabilidade | runtime parcial | forte | baixa |
| Evolucao / Benchmark | deferido por fase | corretamente subordinado | nao aplicavel |
| Voz / Realtime | deferido por fase | corretamente adiado | nao aplicavel |

---

## 5. Proxima sequencia correta de implementacao

Com base no estado atual do repositorio, a sequencia mais coerente deixou de ser correcao estrutural do `v2` e passou a ser maturacao disciplinada do baseline:

### Passo 1 - consolidar o fechamento operacional do `v2`

Foco:

- manter `HANDOFF.md`, `CHANGELOG.md` e este snapshot como leitura viva do baseline;
- tratar dominios, especialistas promovidos e memoria guiada como eixos funcionalmente fechados no `v2` atual.

### Passo 2 - aprofundar criterios por `workflow_profile`

Foco:

- tornar criterios de saida e leitura final ainda mais especificos por rota promovida;
- fazer isso sem espalhar heuristica fora de `domain_registry`, `memory_registry` e `mind_registry`.

### Passo 3 - amadurecer memoria semantica e procedural

Foco:

- ampliar utilidade de `semantic` e `procedural` como apoio soberano de continuidade e framing;
- manter `organization_scope` fechado e evitar qualquer bypass de governanca.

### Passo 4 - deixar a relacao mente -> dominio -> especialista ainda mais explicita

Foco:

- reduzir consumo implicito dessa relacao em consumidores posteriores;
- tratar isso como maturacao cognitiva futura, nao como lacuna critica do baseline.

---

## 6. O que nao deve ser reaberto sem evidencia forte

- JARVIS como sistema unificado, nao chatbot simples;
- soberania do nucleo na relacao com o usuario;
- especialistas subordinados, nao identidades paralelas;
- governanca, memoria canonica e sintese final nao externalizadas;
- benchmark externo como apoio ou filtro, nao como substituto do nucleo;
- organization scope bloqueado sem consumidor canonico soberano;
- `Mem0` sem promocao automatica;
- voz, realtime e superficies amplas fora do caminho critico do `v2`.

---

## 7. Conclusao

A leitura correta hoje e:

- o repositorio nao esta divergindo da visao do Documento-Mestre;
- tambem nao esta divergindo da sua direcao macro ja formalizada nos artefatos do projeto;
- o que existe e um conjunto de gaps de materializacao normais para a fase do `v2`.

A divergencia relevante, neste momento, nao e mais de fechamento funcional do `v2`.
O que resta e maturacao adicional em tres pontos:

- criterios mais especificos por `workflow_profile` no runtime final;
- uso mais rico de memoria `semantic` e `procedural` sem perder soberania;
- relacao mente -> dominio -> especialista ainda mais explicita em consumidores posteriores.

Esse e o backlog certo a partir daqui, mas ele ja nao caracteriza desvio material do `v2`.

---

## 8. Referencias

- [documento_mestre_jarvis.md](d:/Users/DTI/Desktop/jarvis/documento_mestre_jarvis.md)
- [HANDOFF.md](d:/Users/DTI/Desktop/jarvis/HANDOFF.md)
- [matriz-de-aderencia-mestre.md](d:/Users/DTI/Desktop/jarvis/docs/documentation/matriz-de-aderencia-mestre.md)
- [v2-native-memory-scope-hardening-cut-closure.md](d:/Users/DTI/Desktop/jarvis/docs/implementation/v2-native-memory-scope-hardening-cut-closure.md)
- [v2-repository-hygiene-and-tools-review-cut.md](d:/Users/DTI/Desktop/jarvis/docs/implementation/v2-repository-hygiene-and-tools-review-cut.md)
- [v2-repository-hygiene-and-tools-review-cut-closure.md](d:/Users/DTI/Desktop/jarvis/docs/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md)
- [programa-ate-v3.md](d:/Users/DTI/Desktop/jarvis/docs/roadmap/programa-ate-v3.md)
- [technology-study.md](d:/Users/DTI/Desktop/jarvis/docs/architecture/technology-study.md)
