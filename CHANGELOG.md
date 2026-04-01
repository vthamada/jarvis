# Programa ate V3

## 2026-04-01 - Runtime sovereignty and guided memory hardening

- `domain_registry` passou a governar `canonical_domains`, `primary_canonical_domain`, `route_maturity`, `linked_specialist_type`, `specialist_mode` e `workflow_profile` no runtime.
- `cognitive-engine` deixou de sugerir especialistas governados por `intent` puro; os hints agora dependem de rotas canonicas ativas.
- `specialist-engine` passou a exigir coerencia completa entre rota, especialista, modo e memoria guiada, incluindo refs explicitas para `semantic`/`procedural` e `consumer_profile` em pacotes guiados.
- `observability-service` passou a auditar drift ja em `specialist_selection_decided`, nao apenas no evento de conclusao do especialista.
- `synthesis-engine` passou a aproveitar foco semantico e hint procedural de memoria guiada quando eles existem no runtime.
- `mind_registry` virou a fonte soberana de ranking, apoio, supressao e tensao dominante das mentes.
- `memory-service` passou a expor `semantic` e `procedural` como memoria `runtime_partial` em packets guiados por dominio quando ha evidencia persistida suficiente.

## 1. Objetivo

Este documento define o programa de implementacao do JARVIS do `pos-v1` ate `v3`.

Ele existe para orientar a evolucao do sistema sem transformar `HANDOFF.md` em backlog
macro e sem misturar direcao de medio prazo com execucao imediata.

Leitura correta:

- este documento e o contrato de direcao do programa;
- o detalhamento executável do recorte implementável atual fica em
  `docs/implementation/v2-repository-hygiene-and-tools-review-cut.md`;
- o `HANDOFF.md` continua tatico-operacional.

Fontes normativas:

- `documento_mestre_jarvis.md`
- `HANDOFF.md`
- `docs/operations/v1-operational-baseline.md`
- `docs/architecture/technology-study.md`

---

## 2. Estado de partida real

O programa parte do seguinte estado ja consolidado:

- `v1` encerrado para uso controlado, com baseline congelado;
- `orchestrator-service` operando como coordenador principal do nucleo;
- memoria persistente com `PostgreSQL` como backend operacional recomendado;
- observabilidade local persistida e auditavel, com espelhamento agentic complementar;
- `jarvis-console` como interface textual minima do baseline;
- `internal pilot` ja executado e tratado como evidencia operacional;
- `LangGraph` mantido como fluxo opcional, fora do caminho critico do `v1`.

Conclusao pratica:

- o `v1` nao deve ser reaberto;
- o trabalho novo passa a ser organizado como `pos-v1`, `v1.5`, `v2` e `v3`.

---

## 3. Eixos oficiais de evolucao

Os eixos oficiais do programa ate `v3` sao:

1. continuidade entre missoes;
2. memoria mais profunda;
3. observabilidade, evals e evidencia operacional;
4. absorcao tecnologica disciplinada;
5. superficies de uso;
6. governanca e evolucao.

Esses eixos nao avancam de forma simetrica. A ordem de prioridade e dada pela fase
corrente do programa.

---

## 4. Fases do programa

### 4.1 Pos-v1

Objetivo:

- aprofundar a continuidade entre missoes sem reabrir o baseline do `v1`.

Entra nesta fase:

- recuperacao entre missoes relacionadas;
- ranking e decisao de continuidade;
- sintese mais coerente entre missoes;
- observabilidade da continuidade;
- estudo externo curto apenas como apoio dirigido.

Fica fora desta fase:

- `LangGraph` como substrato principal do nucleo;
- especialistas amplos;
- voz e multimodalidade;
- memoria semantica profunda generalizada;
- autoevolucao promotiva.

Gate de saida:

- continuidade entre missoes demonstrada com evidencias repetiveis;
- criterios claros para separar o que sobe para `v1.5` do que fica para `v2`;
- plano rolante executado com baixa ambiguidade.

### 4.2 V1.5

Objetivo:

- consolidar o primeiro salto cognitivo acima do `v1` sem ruptura arquitetural.

Entra nesta fase:

- memoria de continuidade mais forte;
- selecao melhor entre contexto local, missao ativa e missao relacionada;
- avaliacoes operacionais mais sistematicas;
- absorcao parcial de componentes aprovados pelo estudo externo, quando houver
  consumidor real e evidencia suficiente.

Fica fora desta fase:

- migracao ampla para runtime novo;
- ecossistema completo de especialistas;
- superficies multimodais amplas;
- autonomia forte de mudanca de codigo em producao.

Gate de saida:

- continuidade profunda operando acima da missao atual;
- trilha observavel suficiente para comparar estrategias;
- decisao formal sobre que salto estrutural prepara `v2`.

### 4.3 V2

Objetivo:

- expandir o nucleo para especializacao controlada e memoria mais rica.

Entra nesta fase:

- especialistas subordinados ao nucleo;
- memoria semantica mais profunda e retrieval mais sofisticado;
- possivel absorcao mais forte de `LangGraph`, se o fluxo experimental e a evidencia justificarem;
- novas superficies de uso quando houver maturidade do nucleo.

Fica fora desta fase:

- autoevolucao forte em producao;
- mudanca livre do nucleo sem governanca reforcada;
- ampliacao de interfaces sem observabilidade suficiente.

Gate de saida:

- especialistas operando como extensao do nucleo, nao como identidades concorrentes;
- memoria e governanca sustentando maior amplitude sem perder unidade;
- operacao ampliada com rastreabilidade convincente.

### 4.4 V3

Objetivo:

- chegar a um sistema maduro, persistente e operacionalmente mais amplo.

Entra nesta fase:

- persistencia profunda;
- maturidade maior de governanca e avaliacao;
- superficies mais amplas quando justificadas;
- camadas evolutivas mais avancadas, ainda subordinadas a controle forte.

Fica fora desta fase, ate decisao formal posterior:

- autoaperfeicoamento irrestrito;
- promocao automatica de mudancas estruturais sem gates fortes;
- autonomia ampla em dominios de alto risco.

Gate de referencia:

- o sistema sustenta maturidade superior sem perder identidade unificada,
  governanca e rastreabilidade.

---

## 5. Dependencias entre trilhas

As dependencias oficiais do programa sao:

- continuidade entre missoes vem antes de memoria profunda mais ampla;
- memoria mais profunda vem antes de ampliacao cognitiva agressiva;
- observabilidade e evals acompanham qualquer salto de capacidade;
- absorcao tecnologica nao entra por moda, entra por necessidade do nucleo;
- novas superficies de uso nao lideram a arquitetura, apenas expoem um nucleo ja
  coerente;
- evolucao e governanca crescem junto, nunca isoladas.

Regra pratica:

- nenhuma tecnologia externa muda o rumo do programa por si so;
- primeiro se prova a lacuna no nucleo;
- depois se decide absorver, usar como referencia ou rejeitar.

---

## 6. Regra oficial de absorcao de estudos externos

Um estudo externo so pode atravessar para o nucleo quando responder a uma pergunta
concreta de implementacao.

Cada tecnologia estudada deve ser classificada como:

- `absorver depois`;
- `usar como referencia`;
- `rejeitar`.

Para absorver algo no nucleo, e obrigatorio demonstrar:

- problema real do JARVIS que a tecnologia resolve melhor do que o baseline atual;
- encaixe sem ruptura desnecessaria da arquitetura unificada;
- evidencia operacional ou experimental suficiente;
- delimitacao clara do que entra agora e do que fica fora.

Defaults atuais:

- `PostgreSQL`: absorvido no baseline;
- `LangSmith`: complementar;
- `LangGraph`: fluxo opcional e candidato a absorcao parcial futura;
- `Hermes Agent`, `Graphiti` e `Zep`: estudo dirigido para o `pos-v1`.

---

## 7. Marcos oficiais do programa

### Marco A - Pos-v1 executavel

- plano rolante oficial criado;
- primeira janela de `4-6` sprints definida;
- foco do ciclo travado em continuidade profunda entre missoes.

### Marco B - Continuidade profunda demonstrada

- memoria e planejamento distinguem missao ativa de continuidade relacionada;
- sintese final soa como continuidade intencional, nao mera colagem de contexto;
- observabilidade permite avaliar lacunas dessa continuidade.

### Marco C - Decisao de corte para V1.5

- backlog do primeiro ciclo classificado;
- o que sobe para `v1.5` esta fechado;
- o que fica para `v2` esta explicitamente fora do corte.

### Marco D - V1.5 consolidado

- primeira ampliacao cognitiva acima do `v1` estabilizada;
- estudos externos absorvidos ou descartados com criterio;
- baseline do `v1` preservado como referencia conhecida.

### Marco E - Preparacao de V2

- trilhas de memoria profunda, especializacao e runtime estao maduras o suficiente
  para mudanca de fase.

---

## 8. Relacao com o plano de sprint rolante

Este documento nao deve listar tarefas finas por sprint.

Ele define:

- direcao do programa;
- gates de passagem;
- o que entra e o que fica fora de cada fase;
- dependencias entre trilhas.

O documento `docs/archive/implementation/v2-domain-consumers-and-workflows-cut.md` deve derivar deste programa e
traduzir apenas o recorte curto atualmente em execução.

---

## 9. Sintese executiva

O sistema de planejamento oficial do JARVIS passa a ser:

1. `HANDOFF.md` para estado atual, retomada e foco imediato;
2. `docs/roadmap/programa-ate-v3.md` para direcao de medio e longo prazo;
3. `docs/archive/implementation/v2-domain-consumers-and-workflows-cut.md` para execução do recorte ativo.

Essa separacao existe para impedir que o `HANDOFF.md` vire roadmap macro e para evitar
que o programa ate `v3` perca precisao operacional.
