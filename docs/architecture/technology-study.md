# Technology Study

## 1. Objetivo

Este documento consolida o estudo tecnológico do JARVIS em um único artefato.

Ele existe para manter uma leitura única sobre:

- o que o `v1` realmente adotou;
- o que permanece complementar;
- o que é referência arquitetural;
- o que deve continuar em laboratório ou pós-`v1`.

Agora ele também deve ser lido em conjunto com:

- `docs/architecture/technology-capability-extraction-map.md`
- `docs/architecture/technology-absorption-order.md`
- `docs/architecture/technology-repository-review-framework.md`
- revisões profundas de repositório quando elas existirem

Em caso de conflito, `documento_mestre_jarvis.md` continua prevalecendo.

---

## 2. Classes de decisão

Cada tecnologia citada deve cair em uma destas classes:

- `adotar no v1`
- `complementar no v1`
- `laboratório`
- `inspiração arquitetural`
- `deferir para v2`
- `não adotar como núcleo`

---

## 3. Dois eixos oficiais de leitura

Desde a revisão do Documento-Mestre em 2026-03-22, este estudo opera em dois eixos simultâneos:

1. **classe de decisão / adoção**
2. **papel de referência arquitetural por função**

O primeiro eixo responde se algo entra no baseline, fica complementar, vai para laboratório ou permanece fora do núcleo.

O segundo eixo responde à pergunta normativa:

**"Que parte do JARVIS essa arquitetura ou ferramenta nos ajuda a construir melhor?"**

As funções arquiteturais oficiais são:

- orquestração de agentes;
- agente de software / desenvolvimento;
- computer use / operação do computador;
- memória persistente / estado cognitivo;
- agentes pessoais / operacionais;
- contratos, tipagem e previsibilidade.

Dentro de cada função, as referências devem ser tratadas como:

- `referência central`
- `referência secundária`
- `benchmark conceitual`

---

## 4. Critérios de estudo

Toda tecnologia deve ser avaliada por:

- aderência ao papel arquitetural do JARVIS;
- maturidade e manutenção do repositório;
- licença e risco de uso;
- persistência e isolamento;
- observabilidade e depuração;
- risco de lock-in;
- reaproveitamento parcial sem terceirizar o núcleo.

Perguntas mínimas obrigatórias durante o estudo:

1. que lacuna concreta do JARVIS esta tecnologia ajuda a resolver;
2. que parte dela pode ser reaproveitada sem terceirizar identidade, memória, governança ou síntese;
3. se ela deve entrar como baseline, complemento, laboratório ou apenas referência;
4. como validar ganho real sem quebrar o baseline atual.

### 4.1 O que esta camada não respondia sozinha

Até aqui, este estudo classificava bem:

- papel arquitetural;
- classe de decisão;
- lugar de benchmark ou inspiração.

Mas ele ainda não respondia com profundidade suficiente:

- quais primitivas de cada tecnologia realmente valem mais do que a stack inteira;
- o que pertence a workflow, memória, tool use, runtime operacional ou evolução;
- o que deve virar backlog de tradução para o JARVIS e o que deve ficar apenas como referência.

Essa lacuna passa a ser coberta por:

- `docs/architecture/technology-capability-extraction-map.md`
- revisões profundas de repositório para tecnologias que já merecem due diligence técnica real

---

## 5. Referências arquiteturais oficiais por função

| Função arquitetural | Referência central | Referência secundária | Benchmark conceitual |
| --- | --- | --- | --- |
| Orquestração de agentes | LangGraph | OpenAI Agents SDK | CrewAI, Microsoft Agent Framework, Mastra |
| Agente de software / desenvolvimento | OpenHands | OpenHands / Open Operator | OpenCode |
| Computer use / operação do computador | browser-use | Open Interpreter | Claude Computer Use |
| Memória persistente / estado cognitivo | Letta / MemGPT | Hermes Agent | Zep, Graphiti, Mem0 |
| Agentes pessoais / operacionais | OpenClaw | AutoGPT Platform | Manus |
| Contratos, tipagem e previsibilidade | PydanticAI | Qwen-Agent | smolagents |

Leitura correta:

- `referência central` é a melhor âncora para desenhar a camada;
- `referência secundária` complementa ou oferece um segundo padrão útil;
- `benchmark conceitual` ajuda a comparar soluções, sem precisar entrar no baseline ou na dependência principal.

Observação importante:

- `AutoGen` continua relevante historicamente e como referência conceitual de multiagentes, mas deixa de ocupar a primeira linha de benchmark moderno desta camada.

---

## 6. Estado de confiança atual

Classificação atual de confiança para o projeto:

- `alta confiança`: `LangGraph`, `OpenAI Agents SDK`, `OpenHands`, `PydanticAI`, `LangSmith`, `PostgreSQL`
- `média confiança`: `browser-use`, `Letta / MemGPT`, `Hermes Agent`, `OpenClaw`, `Qwen-Agent`, `AutoGPT Platform`, `Mastra`, `Mem0`
- `hipótese ainda aberta`: `Graphiti`, `Zep`, `Manus`, `smolagents`, `Open Interpreter`, `Microsoft Agent Framework` como benchmark mais útil do que `AutoGen`

Uso correto dessa classificação:

- `alta confiança` pode guiar desenho imediatamente;
- `média confiança` já pode orientar a camada, mas ainda pede estudo aplicado;
- `hipótese ainda aberta` não deve virar decisão estrutural sem experimento ou benchmark dirigido.

---

## 7. Matriz consolidada de adoção

| Tecnologia | Papel no JARVIS | Papel de referência | Decisão atual |
| --- | --- | --- | --- |
| LangGraph | runtime stateful e checkpoints para o orquestrador | referência central de orquestração | `complementar no v1` |
| OpenAI Agents SDK | handoffs, tools e tracing complementar | referência secundária de orquestração | `complementar no v1` |
| CrewAI | times de agentes e delegação explícita | benchmark conceitual moderno de orquestração | `inspiração arquitetural` |
| Microsoft Agent Framework | referência atual de ecossistema Microsoft para agentes | benchmark conceitual moderno de orquestração | `inspiração arquitetural` |
| AutoGen | multiagentes e conversação entre agentes | benchmark histórico de orquestração | `inspiração arquitetural` |
| PostgreSQL | backbone operacional de memória e persistência | base operacional própria | `adotar no v1` |
| pgvector | extensão vetorial do backbone relacional | complemento futuro de memória semântica | `deferir para pós-v1` |
| LangSmith | observabilidade agentic complementar | complemento de tracing e evals | `complementar no v1` |
| OpenAI Realtime / Voice | camada moderna de voz e realtime | complemento de interface e voz | `complementar no v1` |
| OpenHands | especialista subordinado de software | referência central de agente de software | `complementar no v1` |
| browser-use | operação de navegador e computer use | referência central de computer use | `laboratório` |
| Open Interpreter | shell e operação local governada | referência secundária de computer use | `laboratório` |
| Claude Computer Use | benchmark de operação do computador | benchmark conceitual de computer use | `inspiração arquitetural` |
| Letta / MemGPT | memória persistente orientada a agente | referência central de estado cognitivo | `laboratório` |
| Zep | memória contextual complementar | benchmark conceitual de memória | `laboratório` |
| Graphiti | memória temporal e relacional complementar | benchmark conceitual de memória | `laboratório` |
| LlamaIndex | ingestão e retrieval complementar | complemento de conhecimento | `laboratório` |
| Hermes Agent | runtime persistente e skills | referência secundária de estado cognitivo | `inspiração arquitetural` |
| AutoGPT Platform | agentes contínuos, blocos, triggers e automações compostas | referência secundária de agentes pessoais / operacionais | `inspiração arquitetural` |
| OpenClaw | referência de gateway, canais e operação | referência central de assistência operacional | `inspiração arquitetural` |
| Manus | referência de assistente operacional amplo | benchmark conceitual operacional | `inspiração arquitetural` |
| Mastra | workflows tipados, `HITL`, snapshots, guardrails e observabilidade | benchmark conceitual moderno de orquestração | `inspiração arquitetural` |
| Mem0 | memória multicamada com `session`, `user`, `org` e busca persistente | benchmark conceitual prático de memória | `laboratório` |
| PydanticAI | contratos estruturados e outputs previsíveis | referência central de contratos e tipagem | `laboratório` |
| Qwen-Agent | modularidade leve e estrutura de agentes | referência secundária de contratos e previsibilidade | `laboratório` |
| smolagents | ferramentas leves e composição modular | benchmark conceitual de contratos e tools | `inspiração arquitetural` |
| TextGrad | otimização textual offline | benchmark de autoaperfeiçoamento | `laboratório` |
| DSPy / MIPROv2 | otimização de programas LM | benchmark de autoaperfeiçoamento | `laboratório` |
| AFlow | otimização automatizada de workflows | benchmark de autoaperfeiçoamento | `laboratório` |
| EvoAgentX | evolução automatizada de workflows e agentes | benchmark de autoaperfeiçoamento | `laboratório` |
| SEAL | auto-adaptação persistente em nível de modelo | laboratório evolutivo mais agressivo | `deferir para v2` |
| Darwin Gödel Machine | autoaperfeiçoamento com mudança de código | laboratório evolutivo mais agressivo | `deferir para v2` |

---

## 8. Leitura aplicada das tecnologias mais importantes

### 8.1 LangGraph

O que interessa ao JARVIS:

- durable execution;
- checkpoints;
- replay;
- `human-in-the-loop`;
- subgraphs para partes do fluxo.

O que não deve ser terceirizado:

- identidade do JARVIS;
- contratos canônicos;
- governança;
- política de memória;
- arbitragem cognitiva como decisão de produto.

Decisão atual:

- aprovado como próximo salto estrutural do núcleo;
- mantido fora do caminho crítico do `v1`;
- continua como fluxo opcional no repositório atual.

### 8.2 PostgreSQL + pgvector

Leitura atual:

- `PostgreSQL` já foi validado e entrou como backend operacional oficial;
- `pgvector` continua aprovado arquiteturalmente, mas ainda não tem consumidor canônico suficiente para virar parte obrigatória do baseline.

Decisão atual:

- `PostgreSQL`: `adotar no v1`
- `pgvector`: `deferir para pós-v1`

### 8.3 LangSmith

Leitura atual:

- a trilha local persistida continua sendo a fonte primária;
- `LangSmith` agrega valor como espelhamento, dashboards, experiments e evals;
- não deve se tornar a única fonte de auditoria.

Decisão atual:

- `complementar no v1`

### 8.4 CrewAI, AutoGen e Microsoft Agent Framework

Leitura atual:

- `CrewAI` merece mais peso como benchmark moderno de orquestração colaborativa;
- `AutoGen` continua relevante, mas com peso mais histórico e menos central na leitura atual;
- `Microsoft Agent Framework` entra como benchmark conceitual mais atual no ecossistema Microsoft, mas ainda como hipótese aberta para o JARVIS.

Regra:

- nenhuma dessas opções substitui `LangGraph` como referência central de orquestração do JARVIS.

### 8.5 PydanticAI

Leitura atual:

- a referência ficou forte o bastante para orientar contratos, tipagem, outputs estruturados e fluxos previsíveis;
- ainda não deve redefinir os contratos canônicos do JARVIS, mas já justifica papel central na camada de previsibilidade.

### 8.6 AutoGPT Platform, Mastra e Mem0

Leitura atual:

- `AutoGPT Platform` merece atenção como referência de agentes contínuos, workflows por blocos, triggers, webhooks e automações compostas;
- `Mastra` merece atenção como benchmark moderno de workflows tipados, `suspend/resume`, `human-in-the-loop`, snapshots, guardrails e observabilidade;
- `Mem0` merece atenção como benchmark prático de memória multicamada, com separação entre contexto de conversa, sessão, usuário e organização.

O que interessa ao JARVIS:

- do `AutoGPT Platform`: blocos reutilizáveis, automações acionadas por eventos e execução contínua governada;
- do `Mastra`: padrões de workflow tipado, pausa e retomada, steps reutilizáveis, snapshots e observabilidade de execução;
- do `Mem0`: organização de memória em camadas operacionais e formas de recuperar contexto persistente sem inflar o prompt bruto.

O que não deve ser terceirizado:

- o núcleo soberano do JARVIS;
- a ontologia de `domínios`, `memórias` e `mentes`;
- a governança final;
- a memória canônica já modelada nos registries do sistema.

Decisão atual:

- `AutoGPT Platform`: `inspiração arquitetural`
- `Mastra`: `inspiração arquitetural`
- `Mem0`: `laboratório`

---

## 9. Fluxo de incorporação no sistema

Este documento não serve apenas para listar tecnologias. Ele também define o caminho correto pelo qual uma tecnologia pode atravessar para o sistema.

O fluxo oficial é:

1. identificar uma lacuna concreta do núcleo ou de uma sprint ativa;
2. classificar a tecnologia pelos dois eixos oficiais:
   - classe de decisão / adoção;
   - papel de referência arquitetural por função;
3. produzir leitura aplicada:
   - o que interessa ao JARVIS;
   - o que não deve ser terceirizado;
   - qual o limite de uso;
4. decidir uma das três saídas:
   - `absorver depois`
   - `usar como referência`
   - `rejeitar`
5. se houver potencial de absorção, validar por fluxo experimental, complemento isolado ou benchmark dirigido;
6. só então promover a tecnologia para o baseline de uma fase futura.

Regra central:

- nenhuma tecnologia entra no núcleo por prestígio, hype ou completude estrutural;
- primeiro se prova a lacuna;
- depois se mede o ganho;
- só então se absorve parte do que realmente melhora o JARVIS.

### 9.1 Formas corretas de incorporação

Uma tecnologia pode entrar no sistema de quatro formas:

1. **como referência arquitetural**
   - orienta desenho de uma camada, mas não vira dependência operacional;
2. **como complemento controlado**
   - entra em adaptador, fluxo experimental ou parte delimitada do sistema sem redefinir o baseline;
3. **como laboratório**
   - permanece fora do caminho crítico e serve para benchmark, comparação ou experimentação;
4. **como baseline de fase futura**
   - só após evidência suficiente, consumidor real e delimitação clara do que sobe.

### 9.2 Exemplos atuais do projeto

- `PostgreSQL`: já atravessou o fluxo e foi absorvido no baseline do `v1`.
- `LangSmith`: entrou como complemento controlado, mantendo a trilha local como fonte primária.
- `LangGraph`: está em fluxo opcional e segue como candidato a absorção parcial futura.
- `pgvector`: foi aprovado arquiteturalmente, mas continua deferido até existir consumidor semântico canônico.
- `Hermes Agent`, `Graphiti`, `Zep`, `AutoGPT Platform`, `Mastra` e `Mem0`: seguem como estudo dirigido, sem promoção automática.

### 9.3 Relação com o programa e com as sprints

Este documento responde:

- o que a tecnologia é para o JARVIS;
- que papel arquitetural ela cumpre;
- qual seu estado de adoção.

Quem responde quando ela pode atravessar para o sistema é:

- `docs/roadmap/programa-ate-v3.md` para a regra de absorção no programa;
- `docs/archive/implementation/v2-domain-consumers-and-workflows-cut.md` para o uso da tecnologia no recorte ativo;
- `HANDOFF.md` para a decisão operacional em vigor.

---

### 9.4 Visão do ecossistema JARVIS

A visão de longo prazo do JARVIS não é apenas usar tecnologias boas.

Ela é construir um sistema soberano capaz de analisar continuamente o estado da arte e absorver o que realmente melhora sua cognição, sua operação e sua evolução sem perder identidade própria.

Leitura correta:

- o JARVIS deve reaproveitar o melhor do ecossistema quando isso acelerar a construção do sistema;
- esse reaproveitamento precisa acontecer por função arquitetural clara;
- nenhuma tecnologia externa pode assumir identidade, memória canônica, governança final ou síntese soberana do sistema.

### 9.5 Fluxo longo de absorção tecnológica

Fluxo disciplinado esperado no longo prazo:

1. radar contínuo do ecossistema;
2. classificação por função arquitetural;
3. registro em memória evolutiva;
4. experimento em sandbox, benchmark ou fluxo isolado;
5. promoção governada por evidência.

Regras permanentes:

- absorver por problema, e não por hype;
- traduzir valor para a gramática do JARVIS, e não terceirizar o núcleo;
- manter toda absorção reversível, auditável e compatível com os registries soberanos do sistema.

### 9.6 Leitura correta por famílias de referência

As famílias de estudo devem ser lidas assim:

- `LangGraph`: referência principal para fluxo stateful, checkpoints, replay e handoffs coordenados;
- `Hermes Agent`: referência de runtime persistente, memória viva, continuidade operacional e skills;
- `Graphiti` e `Zep`: referências para memória relacional, temporal e contextual;
- `AutoGPT Platform`: referência de automações compostas, blocos e agentes contínuos;
- `Mastra`: referência de workflows tipados, `HITL`, snapshots e guardrails;
- `Mem0`: referência de memória multicamada operacional;
- `DSPy / MIPROv2`, `TextGrad`, `AFlow`, `EvoAgentX`, `SEAL` e `Darwin Gödel Machine`: eixo de autoaperfeiçoamento, otimização e evolução governada.

Regra importante:

- `Hermes Agent` não é a referência principal do eixo de autoaperfeiçoamento;
- ele pertence antes ao eixo de runtime persistente, memória viva e skills.

## 10. Governança do processo de análise tecnológica

Para evitar ambiguidade, o processo oficial de análise e incorporação tecnológica do JARVIS passa a obedecer à seguinte distribuição de responsabilidade.

### 10.1 Quem conduz a análise

O estudo técnico é conduzido pelo agente de implementação ativo do ciclo corrente.

Isso significa:

- o agente não escolhe tecnologia por iniciativa solta;
- o agente parte da lacuna concreta do núcleo, da sprint ou do programa;
- o agente produz a análise aplicada e registra a recomendação nos artefatos já existentes;
- o agente pode implementar fluxo experimental, adaptador isolado ou benchmark quando houver justificativa clara.

### 10.2 Quem decide a classificação final

A decisão arquitetural final continua subordinada ao mantenedor do projeto e ao estado oficial dos artefatos canônicos.

Na prática:

- o agente propõe;
- os documentos registram;
- a decisão vigente passa a valer quando refletida em `HANDOFF.md`, no programa, no sprint cycle e, quando necessário, no Documento-Mestre.

### 10.3 Quem pode promover uma tecnologia

Nenhuma tecnologia é promovida diretamente de estudo para baseline.

A promoção só pode ocorrer quando existirem simultaneamente:

- lacuna concreta do sistema;
- recomendação técnica explícita;
- evidência produzida por experimento, fluxo experimental ou benchmark;
- decisão coerente com `HANDOFF.md` e com a fase atual do programa.

---

## 11. Como o agente deve fazer a análise

O agente deve seguir sempre a mesma sequência disciplinada.

### 11.1 Etapa 1 — Partir da lacuna do sistema

O ponto de partida não é a ferramenta. O ponto de partida é a lacuna.

Exemplos:

- "`LangGraph` melhora checkpoint, replay ou `human-in-the-loop` do orquestrador?"
- "`Graphiti` melhora a recuperação entre missões relacionadas?"
- "`PydanticAI` melhora a previsibilidade de contratos e outputs?"
- "`AutoGPT Platform` melhora a futura camada de automação contínua e workflows acionados por eventos?"
- "`Mastra` melhora pause/resume, steps tipados ou trilhas de observabilidade do fluxo?"
- "`Mem0` melhora a modelagem multicamada entre conversa, sessão, usuário e organização?"

Se a lacuna não estiver clara, o estudo ainda não deve começar.

### 11.2 Etapa 2 — Formular a pergunta de implementação

Toda análise deve produzir uma pergunta objetiva no formato:

**"Esta tecnologia melhora qual parte do JARVIS, em relação a quê, e sob quais limites?"**

Essa pergunta precisa conter:

- a camada afetada;
- o problema atual;
- o limite do experimento;
- o critério de sucesso.

### 11.3 Etapa 3 — Fazer leitura aplicada, não leitura genérica

O agente deve extrair da tecnologia apenas o que é relevante para o JARVIS.

A análise mínima deve responder:

1. que parte do sistema isso ajuda a construir melhor;
2. o que pode ser reaproveitado;
3. o que não pode ser terceirizado;
4. qual o risco de acoplamento;
5. qual a menor forma segura de testar valor real.

### 11.4 Etapa 4 — Classificar a saída

Ao fim da análise, a tecnologia deve cair em uma destas saídas:

- `absorver depois`
- `usar como referência`
- `rejeitar`

Leitura correta:

- `absorver depois`: há valor real, mas a fase atual ainda não justifica incorporar;
- `usar como referência`: a tecnologia ajuda a orientar desenho, mas não deve virar dependência;
- `rejeitar`: não resolve a lacuna com ganho suficiente ou traz custo/desvio excessivo.

---

## 12. Como o agente deve fazer a incorporação

Se a análise for positiva, a incorporação deve ser sempre parcial, controlada e reversível.

### 12.1 Regra central

O agente não "adota a ferramenta".

O agente:

- isola o recorte útil;
- protege o baseline atual;
- mede o ganho;
- promove só o que melhora o sistema sem deformar a arquitetura.

### 12.2 Formas válidas de incorporação

As formas corretas de entrada são:

1. **Fluxo experimental opcional**
   - usada quando o objetivo é comparar comportamento sem reabrir o baseline;
2. **complemento controlado**
   - usada quando a tecnologia entra em adaptador, observabilidade, tooling ou subfluxo delimitado;
3. **benchmark/laboratório**
   - usada quando o valor ainda está em comparação, não em absorção;
4. **promoção para baseline de fase futura**
   - usada apenas quando a evidência já é forte e o encaixe arquitetural está claro.

### 12.3 O que o agente deve preservar durante a incorporação

Mesmo em fluxo experimental ou complemento, o agente deve preservar:

- identidade do JARVIS;
- contratos canônicos;
- política de memória;
- governança;
- síntese final;
- rastreabilidade;
- rollback simples.

### 12.4 Regra de recorte mínimo

A incorporação deve começar pelo menor recorte útil possível.

Exemplos:

- `LangGraph` entra primeiro em checkpoint, replay ou HITL, não em refactor total do núcleo;
- `Graphiti` ou `Zep` entram primeiro em experimento de continuidade relacionada, não na memória inteira;
- `PydanticAI` entra primeiro em contratos ou outputs delimitados, não substituindo toda a camada canônica;
- `AutoGPT Platform` entra primeiro como benchmark de blocos, workflows e agentes contínuos, não como runtime soberano;
- `Mastra` entra primeiro como benchmark de `suspend/resume`, snapshots e guardrails, não como substituto direto do orquestrador;
- `Mem0` entra primeiro em experimento delimitado de memória multicamada, não como memória canônica total;
- `browser-use` entra primeiro como laboratório governado, não como operação ampla soberana.

---

## 13. Evidência obrigatória antes de promover tecnologia

Antes de qualquer promoção de status, o agente precisa produzir evidência suficiente.

### 13.1 Evidência mínima aceita

Pelo menos um destes formatos deve existir:

- fluxo experimental executável;
- benchmark comparativo;
- avaliação dirigida por cenário;
- evidência operacional reaproveitável no piloto;
- teste ou trilha observável que prove ganho real.

### 13.2 O que a evidência precisa demonstrar

A evidência precisa demonstrar, no mínimo:

- que havia uma lacuna real;
- que a tecnologia melhorou essa lacuna;
- que o ganho supera o custo de acoplamento;
- que a incorporação não quebrou o baseline atual;
- que existe limite claro do que entra e do que continua fora.

### 13.3 O que não conta como evidência suficiente

Não contam como promoção válida:

- entusiasmo com framework;
- maturidade pública isolada;
- benchmark genérico sem cenário do JARVIS;
- opinião sem teste;
- ganho cosmético sem melhora estrutural.

---

## 14. Estados possíveis de uma tecnologia dentro do JARVIS

Para evitar ambiguidade, toda tecnologia deve estar em um destes estados:

1. **somente referência**
   - influencia desenho, mas não entra no runtime;
2. **laboratório**
   - está em benchmark, comparação ou estudo aplicado;
3. **Fluxo experimental opcional**
   - existe implementação isolada para comparação;
4. **complemento controlado**
   - já entrou em parte delimitada do sistema;
5. **baseline da fase**
   - faz parte do núcleo oficial daquela fase.

### 14.1 Exemplos atuais do projeto

- `PostgreSQL`: baseline do `v1`;
- `LangSmith`: complemento controlado;
- `LangGraph`: fluxo opcional e candidato a absorção parcial futura;
- `pgvector`: aprovado arquiteturalmente, mas ainda fora do baseline;
- `Hermes Agent`, `Graphiti`, `Zep`, `AutoGPT Platform`, `Mastra` e `Mem0`: estudo dirigido e laboratório;
- `OpenClaw`: referência arquitetural;
- `SEAL`: deferido para fase futura, sem entrada no núcleo atual.

---

## 15. Regras de bloqueio

Uma tecnologia não deve atravessar para o sistema se ocorrer qualquer uma destas condições:

- a lacuna do sistema não está clara;
- a tecnologia resolve um problema que ainda não é prioritário no programa;
- a incorporação exige terceirizar identidade, memória, governança ou síntese;
- o ganho não foi demonstrado em cenário do JARVIS;
- a fase atual do programa explicitamente mantém essa tecnologia fora do corte;
- o baseline precisaria ser reaberto sem necessidade real.

---

## 16. Leitura executiva do processo

O processo correto, resumido, é:

1. localizar a lacuna do núcleo;
2. formular a pergunta de implementação;
3. analisar a tecnologia pelos dois eixos oficiais;
4. decidir `absorver depois`, `usar como referência` ou `rejeitar`;
5. se fizer sentido, criar fluxo experimental, complemento isolado ou benchmark;
6. produzir evidência;
7. só então promover a tecnologia para o baseline de uma fase futura.

Em uma frase:

**o agente analisa por problema e incorpora por recorte, nunca por entusiasmo com framework.**


## 17. Foco de estudo no ciclo atual

Trilha atual: `continuidade profunda entre missões` no pós-`v1`, seguida do alinhamento soberano de `domínios`, `memórias` e `mentes` no `v2-sovereign-alignment-cut`.

Ordem oficial de estudo externo neste momento:

1. `LangGraph`
2. `Hermes Agent`
3. `Graphiti`
4. `Zep`

Tecnologias que passam a merecer atenção complementar, mas fora do corte imediato:

- `AutoGPT Platform`, para camada futura de blocos, workflows acionados por eventos e agentes contínuos;
- `Mastra`, para benchmark de workflows tipados, `suspend/resume`, snapshots, guardrails e observabilidade;
- `Mem0`, para benchmark de memória multicamada com separação entre conversa, sessão, usuário e organização.

Leitura operacional:

- o estudo é paralelo curto e dirigido;
- nenhuma dessas tecnologias entra automaticamente no núcleo;
- o foco imediato continua sendo fortalecer os eixos soberanos do próprio JARVIS antes de qualquer absorção mais ampla.

## 17. Nota de linguagem tecnica

- runtime ids novos devem convergir para ingles;
- labels legados em portugues podem permanecer apenas como compatibilidade curta ou camada semantica;
- isso agora tambem vale para specialist types e futuros workflow ids do runtime.


## 18. Governed benchmark envelope of the active v2 cut

O corte ativo `v2-domain-consumers-and-workflows-cut` passou a tratar benchmark como artefato governado, e nao como pesquisa solta.

Artefato regeneravel desta sprint:

- `docs/archive/implementation/v2-governed-benchmark-matrix.md`
- `tools/archive/render_governed_benchmark_matrix.py`
- `tools/benchmarks/datasets/v2_governed_benchmark_candidates.json`

### 18.1 Familias que podem entrar neste recorte

As tecnologias elegiveis para este recorte sao lidas por familia de capacidade:

- `workflow_orchestration`: `LangGraph`, `OpenAI Agents SDK`, `Mastra`, `CrewAI`, `Microsoft Agent Framework`;
- `continuous_operational_agents`: `AutoGPT Platform`, `OpenClaw`, `Hermes Agent`, `Manus`;
- `multilayer_memory`: `Mem0`, `Letta / MemGPT`, `Zep`, `Graphiti`.

### 18.2 Candidatas em benchmark agora

Nesta sprint, apenas tres tecnologias entram como `benchmark_now`:

- `AutoGPT Platform`
- `Mastra`
- `Mem0`

Leitura correta:

- `AutoGPT Platform` entra para comparar blocos, triggers, webhooks e automacoes compostas;
- `Mastra` entra para comparar workflows tipados, `suspend/resume`, snapshots, guardrails e observabilidade;
- `Mem0` entra para comparar memoria multicamada por escopo, sem reabrir a memoria canonica do JARVIS.

### 18.3 Tecnologias no envelope comparativo

Estas tecnologias podem entrar na leitura deste recorte, mas ficam em `reference_envelope`:

- `LangGraph`
- `OpenAI Agents SDK`
- `CrewAI`
- `Microsoft Agent Framework`
- `OpenClaw`
- `Hermes Agent`
- `Manus`
- `Letta / MemGPT`
- `Zep`
- `Graphiti`

Regra:

- elas entram para contraste arquitetural e delimitacao de escopo;
- elas nao entram como benchmark principal desta sprint;
- nenhuma delas sobe para o nucleo por comparacao conceitual isolada.

### 18.4 Decisao correta dentro deste recorte

A Sprint 3 do corte ativo encerra com a seguinte politica:

- `benchmark_now` nao implica promocao;
- `reference_envelope` nao implica absorcao;
- a saida continua restrita a `usar como referencia`, `absorver depois` ou `rejeitar`;
- qualquer experimento futuro precisa preservar `domain_registry`, `memory_registry`, `mind_registry`, governanca final e sintese soberana.

Decisao formal desta sprint:

- `Mastra`: `usar como referencia`;
- `AutoGPT Platform`: `usar como referencia`;
- `Mem0`: `absorver depois`.

Leitura apos o fechamento deste corte:

- `Mastra` permanece como referencia forte de workflow e nao deve subir por conveniencia local;
- `AutoGPT Platform` permanece como referencia de camada operacional futura e nao como nucleo;
- `Mem0` fica como unica candidata de reabertura futura, condicionada a lacuna real do baseline de memoria.

### 18.5 Quando `absorver depois` vira candidata a absorcao

Uma tecnologia marcada como `absorver depois` so deve mudar de status quando todos estes sinais aparecerem ao mesmo tempo:

- a lacuna do JARVIS estiver comprovada no corte ativo, e o baseline atual estiver exigindo workaround demais;
- o benchmark, experimento ou fluxo isolado demonstrar ganho real contra o baseline atual;
- o ganho vier sem romper `domain_registry`, `memory_registry`, `mind_registry`, governanca final ou sintese soberana;
- a incorporacao couber no menor recorte util e reversivel, sem refactor total do nucleo;
- `HANDOFF.md` e o documento do corte ativo passarem a tratar a tecnologia como candidata de absorcao da fase.

Leitura correta:

- `absorver depois` ainda nao e permissao de adotar;
- ele apenas registra que a tecnologia ja parece promissora o bastante para uma futura janela de entrada;
- a entrada continua subordinada a recorte, evidencia e coerencia com o baseline do sistema.

### 18.6 Fontes oficiais consultadas nesta rodada

- `AutoGPT Platform`: `https://docs.agpt.co/platform/agent-blocks/`
- `Mastra`: `https://mastra.ai/en/docs/workflows/suspend-and-resume`
- `Mem0`: `https://docs.mem0.ai/api-reference/memory/add-memories`
- `Letta`: `https://docs.letta.com/guides/ade/core-memory`
- `Zep`: `https://help.getzep.com/docs`


### 18.7 Proximo recorte correto

- o recorte ativo de memoria deve primeiro provar a lacuna do baseline atual;
- `Mem0` nao sobe por conveniencia local nem por analogia com produtos externos;
- a reabertura de absorcao so fica correta se o proprio JARVIS provar onde sua modelagem atual deixa de ser suficiente.

Leitura apos a Sprint 2 do recorte de memoria:

- conversa, sessao e missao continuam suficientes no baseline atual;
- `user scope` ficou lido como tipado e rastreado, mas ainda nao runtime-rich;
- `specialist_shared_memory` ficou lido como handoff forte, mas nao como prova de um escopo mais forte por agente;
- `organization scope` continua apenas forma futura e ainda nao vira lacuna comprovada;
- por isso, `Mem0` continua em `absorver depois` e nao em reabertura imediata.

Leitura apos a Sprint 3 do recorte de memoria:

- a decisao formal correta neste momento e `manter_fechado`;
- `Mem0` continua candidata condicional e nao sobe para recorte proprio de absorcao nesta fase;
- qualquer futura reabertura depende primeiro de consumidor canonico, custo estrutural comprovado ou nova evidencia local acima do baseline atual.

Leitura apos o fechamento do memory gap evidence cut:

- o proximo passo correto nao e abrir absorcao externa;
- o proximo passo correto e endurecer nativamente `user scope` e `specialist_shared_memory`;
- `Mem0` continua candidata condicional e so reabre se o baseline endurecido ainda provar insuficiencia.


### 18.8 Camada de revisao profunda de repositorio

A partir desta rodada, o estudo tecnologico passa a distinguir duas camadas:

- triagem arquitetural e benchmark governado
- revisao profunda de repositorio para candidatas serias

Essa segunda camada agora foi formalizada em:

- `docs/architecture/technology-repository-review-framework.md`

Primeira aplicacao registrada:

- `docs/architecture/mem0-repository-review.md`

Leitura correta:

- a revisao profunda nao promove tecnologia ao nucleo;
- ela serve para verificar se uma tecnologia continua fazendo sentido quando saimos das docs e olhamos o repositorio real;
- o primeiro caso aplicado reforcou `Mem0` como `absorver depois`, mas apenas por absorcao estreita, tardia e reversivel.

### 18.9 Mapa expandido de potencial tecnologico

A leitura correta do ecossistema, depois do aprofundamento desta revisao, e:

- `LangGraph`, `Mastra`, `OpenAI Agents SDK` e `Microsoft Agent Framework`
  concentram mais valor em durable execution, handoffs, guardrails, checkpoints
  e contratos de workflow do que em identidade do sistema;
- `Letta`, `Zep`, `Graphiti`, `Mem0`, `Hermes Agent` e `OpenClaw`
  concentram mais valor em memoria, continuidade, recall, skills e runtime
  persistente do que em governanca soberana;
- `OpenHands`, `browser-use`, `Open Interpreter` e `Claude Computer Use`
  concentram mais valor em substrate operacional e computer use do que em
  arquitetura cognitiva;
- `PydanticAI`, `Qwen-Agent` e `smolagents` concentram mais valor em contratos,
  validacao, MCP, tool use e simplicidade de composicao do que em estrutura de
  sistema;
- `DSPy / MIPROv2`, `TextGrad`, `AFlow`, `EvoAgentX`, `SEAL` e `Darwin Godel
  Machine` concentram mais valor em algoritmos de refinamento e evolucao
  governada do que em produto final.

Regra nova de leitura:

- o principal ganho para o JARVIS nao vem de "adotar uma tecnologia";
- vem de traduzir o melhor padrao de cada familia para a camada correta do
  sistema.

Artefatos que agora devem ser lidos em conjunto:

- `docs/architecture/technology-capability-extraction-map.md`
- `docs/architecture/technology-absorption-order.md`
- `docs/architecture/mem0-repository-review.md`
- `docs/architecture/hermes-agent-repository-review.md`
