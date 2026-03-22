# Technology Study

## 1. Objetivo

Este documento consolida o estudo tecnológico do JARVIS em um único artefato.

Ele existe para manter uma leitura única sobre:

- o que o `v1` realmente adotou;
- o que permanece complementar;
- o que é referência arquitetural;
- o que deve continuar em laboratório ou pós-`v1`.

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

---

## 5. Referências arquiteturais oficiais por função

| Função arquitetural | Referência central | Referência secundária | Benchmark conceitual |
| --- | --- | --- | --- |
| Orquestração de agentes | LangGraph | OpenAI Agents SDK | CrewAI, Microsoft Agent Framework |
| Agente de software / desenvolvimento | OpenHands | OpenHands / Open Operator | OpenCode |
| Computer use / operação do computador | browser-use | Open Interpreter | Claude Computer Use |
| Memória persistente / estado cognitivo | Letta / MemGPT | Hermes Agent | Zep, Graphiti |
| Agentes pessoais / operacionais | OpenClaw | nenhuma obrigatória nesta fase | Manus |
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
- `média confiança`: `browser-use`, `Letta / MemGPT`, `Hermes Agent`, `OpenClaw`, `Qwen-Agent`
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
| OpenClaw | referência de gateway, canais e operação | referência central de assistência operacional | `inspiração arquitetural` |
| Manus | referência de assistente operacional amplo | benchmark conceitual operacional | `inspiração arquitetural` |
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
- continua como POC opcional no repositório atual.

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
