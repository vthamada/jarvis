# Technology Absorption Order

Execução iniciada2026-10-20: fatia de replay de contexto Hermes pin0b8dee00
reutilizada em opt-in, com comparador/executor e gate portátil. Não equivale
ao loop Hermes completo nem a promoção. Estado de verificação e resultados no
[runbook do experimento](../operations/hermes-context-comparison-2026-10-20.md).

Direção ativa revisada em 2026-10-20 por solicitação do operador. Este documento
é o norte de composição tecnológica; não é evidência de integração executada.
As seções 1–3 e 6–8 atualizadas regem a seleção. As listas das seções 4–5 são
referências por família, não uma fila que obrigue concluir toda a infraestrutura
antes de entregar produto. A fila executável continua única.

## 1. Objetivo

Este documento transforma o estudo tecnologico ampliado do JARVIS em uma
ordem oficial de traducao e absorcao disciplinada.

Ele responde:

- o que deve ser traduzido primeiro para o sistema;
- o que deve ficar como complemento futuro;
- o que deve permanecer em laboratorio ou horizonte de pesquisa.

Ele nao substitui:

- `docs/architecture/technology-study.md`
- `docs/architecture/technology-capability-extraction-map.md`
- `docs/architecture/technology-repository-review-framework.md`
- `docs/implementation/execution-backlog.md`

Leitura correta:

- este arquivo nao e permissao para importar stacks inteiras;
- ele organiza reuso de código, adaptação e tradução de padrões para o JARVIS;
- backlog micro continua vivendo em `docs/implementation/execution-backlog.md`.

---

## 2. Regra central

O JARVIS absorve tecnologias por quatro formas, sem degraus obrigatórios:

1. **padrões, primitivas e código reutilizado com origem preservada**
2. **adaptações pequenas de implementações existentes**
3. **complementos controlados**
4. **baseline de fase futura**

Regra permanente:

- o sistema seleciona o que resolve melhor uma lacuna observada no conjunto,
  não o que parece melhor isoladamente;
- reuso direto ou adaptação devem ser considerados antes de reimplementar;
  licença, acoplamento, manutenção e custo de atualização podem justificar
  implementação própria, mas a justificativa deve ser concreta e curta;
- adoção mais ampla exige demonstrar vantagem de custo total e integração,
  preservar os contratos e explicitar a decisão arquitetural; não é automática;
- nada externo assume identidade, memoria canonica, governanca final ou sintese
  soberana do nucleo.
- a ordem de absorcao e viva: o estado da arte deve ser revisado periodicamente,
  e novas tecnologias podem ser classificadas como referencia, experimento,
  complemento controlado ou traducao promovivel conforme evidencia.

### 2.1 Decisão crítica e alternativas

Mandato do operador: extrair o melhor de projetos existentes e construir um
JARVIS integrado capaz de superar referências. Recomendação de engenharia:
composição seletiva orientada a tarefas, com uma base principal por
responsabilidade. Trata-se de uma decisão de direção, ainda sem comparação
executada que demonstre ser a melhor arquitetura para todas as tarefas.

| Alternativa | Quando faz sentido | Risco ou limite | Decisão atual |
| --- | --- | --- | --- |
| Construir tudo internamente | Lacuna sem solução compatível ou diferencial necessário | Repetir trabalho e adiar utilidade | Exceção justificada por capacidade |
| Adotar um agente existente como produto principal | Prioridade exclusiva de uso imediato com poucas diferenças | Migrar autoridade e manter um fork divergente | Alternativa válida, mas muda o produto/arquitetura e exige decisão explícita |
| Composição seletiva sobre uma base coerente | Experiência própria, continuidade e várias capacidades integradas | Adaptação, compatibilidade e atualização têm custo real | Caminho recomendado para a visão do JARVIS |
| Combinar vários frameworks completos no mesmo caminho crítico | Experimento delimitado com vantagem demonstrável | Contextos, memórias e loops duplicados; latência e diagnóstico | Não adotar como padrão |

Uma base coerente não significa perpetuar o código atual. Se absorver uma
implementação maior for mais simples e seguro do que manter a nossa, registrar
essa alternativa e o custo de migração. Investimento passado não é critério de
aprovação. A soberania é exercida por contratos e controle dos efeitos, não
pela autoria de cada linha nem pela centralização física de todos os processos.

A ambição de superioridade se traduz em melhores resultados nas tarefas do
usuário. Não pressupõe vencer todos os agentes, modelos e benchmarks ao mesmo
tempo. O modelo, o hardware, o contexto e os limites também afetam o resultado;
um timeout local isolado não identifica um defeito exclusivo do harness.

### 2.2 Regra prática de incorporação

Para cada lacuna prioritária, usar o item e o runbook existentes, sem criar um
registro paralelo de estados:

1. Fixar tarefa, baseline, critério de sucesso e limites antes do experimento.
2. Indicar o componente candidato, repositório, commit, arquivos, licença e
   dependências transitivas relevantes; preservar atribuições ao reutilizar.
3. Escolher reuso, adaptação ou implementação própria, justificando custo de
   manutenção/atualização, compatibilidade e menor superfície necessária.
4. Integrar uma fatia ponta a ponta em sandbox, com uma autoridade por função;
   nenhum segundo store vira memória canônica nem um loop externo autoriza I/O.
5. Executar testes funcionais e negativos, medir qualidade/latência/consumo e
   esforço de integração, registrar falhas e comparar com o baseline elegível.
6. Registrar decisão, limites e rollback. Promoção continua manual, pelos
   contratos e registries existentes, incluindo `shared/technology_absorption.py`;
   nenhuma regra de runtime é relaxada por este texto.

O registro mínimo é: lacuna/tarefa -> origem e versão -> opção escolhida ->
mudança e testes -> comandos/artefatos/resultados -> decisão e rollback.
Referência, experimento, integração validada e ganho comparativo são evidências
distintas. Um estudo pode terminar em rejeição ou decisão de não integrar.

### 2.3 Evidência atual e próxima prova

- O [piloto de conversa](../operations/structured-local-conversation-2026-10-20.md)
  fechou uma comparação real de duas fontes; o segundo turno expirou e o
  controle sem histórico não executou. Memória útil real segue não comprovada.
- A [campanha existente](../operations/harness-mission-campaign.md) tem 25
  missões sintéticas públicas e runner/grader, não comparação válida já
  concluída contra Hermes nem prova de generalização ou tarefas privadas reais.
- As avaliações de [ai-memory](../implementation/ai-memory-assessment-2026-10-20.md)
  e [Harness2](../implementation/harness2-assessment-2026-10-20.md) são estudos;
  não equivalem a capacidades integradas ou ganho de autoevolução.

Primeiro experimento iniciado: uma fatia reaproveitada do Hermes no fluxo
modelo -> Core -> leitura de relatórios -> observação -> continuação -> síntese.
O commit foi fixado em0b8dee00; o acoplamento do loop completo motivou extrair
replay de contexto, não importar o runtime. A arquitetura publicada sozinha
não demonstrava essa extração; código e proveniência foram inspecionados. Não instalar
Hermes globalmente, importar credenciais ou ativar suas ferramentas por padrão.

Comparar o baseline JARVIS com a candidata adaptada sob o mesmo modelo, fontes,
capabilities, hardware e orçamento de inferências/tempo. Contabilizar chamadas
auxiliares, retries, compactação e estado de residência; diferenças inevitáveis
devem ser declaradas. Cada lado usa seu protocolo interno documentado: não
forçar o Hermes inalterado ao JSON proprietário do JARVIS nem atribuir ao
Hermes original um resultado obtido apenas pela nossa candidata adaptada.

O recorte de aceite tem três cenários: comparação de duas fontes; segundo
turno com correção, restart e controle sem histórico; chamada proibida sem
efeito externo. A recusa é exigida no cenário proibido, mas não conta como
conclusão útil dos cenários permitidos. Conferir resposta final, memória,
eventos e ausência de efeitos indevidos. Essa prova pequena fecha viabilidade,
não superioridade estatística. Se houver sinal útil, ampliar na campanha
existente com repetições, tarefas novas e revisão humana; o split público
dev/probe não é holdout secreto. Limiares de ganho e regressão devem ser fixados
antes dessa ampliação, com todos os resultados incluídos.

No teste de memória, o segundo pedido não deve repetir o fato/preferência a
recordar, nem escondê-lo nas novas fontes. O controle difere apenas pela
ausência do histórico e não deve inventar essa informação. Transportar um par
canônico até o modelo sem resposta útil não satisfaz o aceite de memória.

Na primeira comparação inválida por transporte, contrato ou recurso, classificar
a causa antes de acrescentar candidatos ou alterar prompts sucessivamente.
Se o reuso exigir importar outro cérebro ou infraestrutura desproporcional,
registrar a rejeição e tentar uma primitiva menor. O próximo recorte e sua
sequência ficam no [backlog micro](../implementation/execution-backlog.md).

### 2.4 Referências e alcance da recomendação

Fontes primárias consultadas em 2026-10-20:

- [Arquitetura do Hermes](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture):
  documenta separação entre loop, contexto, providers, ferramentas e estado.
  É evidência de desenho publicado, não prova local de extração ou desempenho.
- [Building effective agents, Anthropic](https://www.anthropic.com/engineering/building-effective-agents):
  recomenda complexidade proporcional ao ganho, atenção ao custo/latência e
  compreensão das abstrações. Não afirma que nossa composição específica vencerá.

A escolha por composição seletiva é inferência de engenharia aplicada à visão
e às restrições locais, não uma conclusão experimental desses projetos. As
fontes são vivas; qualquer código incorporado exige pin próprio no experimento.

---

## 3. Criterio de ordenacao

Uma tecnologia sobe na ordem quando combina:

- forte aderencia ao gap atual do JARVIS;
- traducao pequena e reversivel;
- ganho observável de utilidade, robustez ou profundidade no fluxo completo;
- baixo risco de terceirizacao do nucleo.

Uma tecnologia desce na ordem quando:

- não atende uma tarefa prioritária ou um risco concreto do fluxo atual;
- exige importar plataforma demais para colher valor pequeno;
- pressupoe uma fase que o JARVIS ainda nao abriu;
- traz mais superficie do que necessidade real.
- parece novidade relevante, mas ainda nao mostrou ganho claro acima do baseline
  ou das referencias ja classificadas.

---

## 4. Ordem oficial de absorcao

### 4.1 Onda 1: traducao imediata para o nucleo

Estas sao as referencias cujo valor ja conversa diretamente com os gaps centrais
do baseline atual.

#### 1. `PydanticAI`

O que absorver:

- contratos estruturados;
- validadores de output;
- retries e falhas controladas;
- tipagem de outputs por etapa.

Onde encaixa:

- `shared/contracts`
- `planning-engine`
- `synthesis-engine`
- outputs de especialistas

O que nao absorver:

- a API inteira como substituta da gramatica do JARVIS.

#### 2. `Letta / MemGPT`

O que absorver:

- memoria viva com manutencao;
- distincao entre memoria fixada e memoria arquivada;
- ciclos de limpeza, consolidacao e review;
- memoria como sistema vivo, nao apenas store.

Onde encaixa:

- `memory-service`
- `memory_registry`
- lifecycle nativo de memoria

O que nao absorver:

- ontologia de memoria deles no lugar das 11 classes canonicas.

#### 3. `Hermes Agent`

O que absorver:

- skills como memoria procedural reutilizavel;
- busca cross-session;
- compressao disciplinada de contexto;
- subagentes isolados para pesquisa e execucao paralela.

Onde encaixa:

- `memory-service`
- `evolution-lab`
- futuras camadas de runtime operacional

O que nao absorver:

- o runtime inteiro do Hermes como cerebro do sistema.

#### 4. `LangGraph`

O que absorver:

- durable execution;
- resumabilidade;
- subgraphs stateful;
- replay e interrupts governados.

Onde encaixa:

- `orchestrator-service`
- continuidade longa
- workflows stateful

O que nao absorver:

- selecao cognitiva, dominio ou governanca como responsabilidade do grafo.

#### 5. `Mastra`

O que absorver:

- semantica forte de workflow tipado;
- snapshots;
- `suspend/resume`;
- taxonomia de evals e leitura de runtime.

Onde encaixa:

- `planning-engine`
- `orchestrator-service`
- `observability-service`
- gramaticas de workflow

O que nao absorver:

- stack inteira de agentes/workflows como baseline JS do sistema.

#### 6. `DSPy / MIPROv2`

O que absorver:

- compile loops;
- optimization by metric;
- surrogate-guided refinement;
- programa LM como objeto de evolucao governada.

Onde encaixa:

- `evolution-lab`
- comparadores
- proposal generation

O que nao absorver:

- uma DSL externa como forma principal de descrever o runtime do JARVIS.

### 4.2 Onda 2: complementos controlados

Estas tecnologias ja sao importantes, mas devem entrar depois que a Onda 1
estiver mais bem traduzida.

Estado atual:

- a Onda 2 agora ja possui matriz formal de readiness em `compare_orchestrator_paths.py` e no `evolution-lab`, subordinada aos sinais causais do nucleo;
- isso nao ativa automaticamente nenhum item da Onda 2: a matriz serve para filtrar candidatos a experimento controlado, nao para abrir frente macro nem promover stack externa por impulso.

#### 7. `OpenAI Agents SDK`

Absorver:

- semantica de handoff;
- spans/tracing;
- adapters de session;
- guardrails por borda do fluxo.

#### 8. `Qwen-Agent`

Absorver:

- context compaction;
- parser fallback de tool calls;
- MCP patterns;
- benchmark de planning com documentos e retrieval.

#### 9. `Graphiti / Zep`

Absorver:

- memoria relacional e temporal;
- facts/summaries;
- point-in-time recall;
- camada futura de graph memory.

#### 10. `Mem0`

Absorver:

- ownership e scoping;
- write lifecycle;
- separacao mais rica entre `user`, `session`, `agent`, `org`, `project`.

Leitura correta:

- o melhor valor aqui e modelagem de escopo, nao substituicao da fundacao de
  memoria.

#### 11. `OpenHands`

Absorver:

- substrate de coding;
- isolamento por sandbox;
- especialista de software mais forte.

#### 12. `browser-use`

Absorver:

- browser operator dedicado;
- browser profiles persistentes;
- superfice de navegacao autenticada e repetivel.

#### 13. `Open Interpreter`

Absorver:

- substrate local de execucao;
- computer primitives de alto nivel;
- multi-language execution governada.

#### 14. `AutoGPT Platform`

Absorver:

- blocos reutilizaveis;
- triggers e webhooks;
- automacoes compostas.

#### 15. `TurboQuant`

Absorver:

- compressao de `KV cache` para `long-context` e `realtime` futuros;
- compressao vetorial para retrieval semantico em escala;
- benchmark de `bitwidth x recall x latencia x memoria`.

Leitura correta:

- so faz sentido quando houver pressao real de memoria de inferencia ou
  retrieval vetorial alem do que o baseline atual pede;
- nao entra como resposta para memoria canonica, governanca ou gaps atuais do
  nucleo.

### 4.3 Onda 3: referencias de produto e operacao tardia

Estas tecnologias valem como referencia forte, mas so fazem sentido depois de o
nucleo estar mais maduro.

#### 16. `OpenClaw`

Absorver:

- gateway multicanal;
- lifecycle de skills;
- runtime operacional local-first.

#### 17. `Manus`

Absorver:

- projects persistentes;
- tarefas assincronas de longa duracao;
- superficie mais ampla de agent platform.

### 4.4 Onda 4: horizonte de pesquisa

Estas referencias devem ficar fora do backlog implementavel atual.

#### 18. `TextGrad`

Valor:

- refinement loops textuais locais no laboratorio evolutivo.

#### 19. `AFlow`

Valor:

- busca sobre workflows via arvore/MCTS.

#### 20. `EvoAgentX`

Valor:

- encadear gerar, avaliar e evoluir workflows.

#### 21. `SEAL`

Valor:

- horizonte de adaptacao persistente.

#### 22. `Darwin Godel Machine`

Valor:

- horizonte de auto-modificacao empiricamente validada.

Regra:

- `TextGrad`, `AFlow` e `EvoAgentX` podem orientar `evolution-lab`;
- `SEAL` e `Darwin Godel Machine` permanecem pesquisa, nao backlog da fase.

---

## 5. Leitura sintetica por camada do JARVIS

### 5.1 Mais urgente agora

- contratos e validacao: `PydanticAI`
- memoria viva e lifecycle: `Letta / MemGPT`
- memoria procedural e recall cross-session: `Hermes Agent`
- durable execution e workflows stateful: `LangGraph`
- semantica de workflow e snapshots: `Mastra`
- evolucao por metrica: `DSPy / MIPROv2`

### 5.2 Depois disso

- handoff/tracing/session adapters: `OpenAI Agents SDK`
- context management e MCP patterns: `Qwen-Agent`
- memoria temporal/graph: `Graphiti`, `Zep`
- ownership/scoping: `Mem0`
- compressao inferencial e vector retrieval: `TurboQuant`
- coding specialist substrate: `OpenHands`
- browser/computer substrate: `browser-use`, `Open Interpreter`
- automacoes compostas: `AutoGPT Platform`

### 5.3 Mais tarde

- gateway e canais: `OpenClaw`
- product surface ampla e projetos async: `Manus`

### 5.4 Horizonte

- `TextGrad`
- `AFlow`
- `EvoAgentX`
- `SEAL`
- `Darwin Godel Machine`

---

## 6. Traducao para backlog

A prioridade começa pela tarefa útil e pela lacuna demonstrada. As ondas acima
são um mapa de referências, não uma obrigação de abrir itens para cada projeto.
A direção de 2026-10-20 substitui a leitura de que todas as fundações precisam
estar completas antes de uma experiência de produto ser entregue.

O mapa vira backlog assim:

- **Onda 1** oferece candidatos ao backlog micro; só entram em `ready` após
  Definition of Ready e escolha da tarefa, sem abertura automática por projeto;
- **Onda 2** gera itens `blocked` ou `deferred`, dependendo da maturidade do
  baseline;
- a abertura de qualquer item da Onda 2 deve usar tambem a matriz formal de
  readiness publicada por comparadores e `evolution-lab`;
- **Onda 3** fica mapeada, mas nao entra como fila ativa;
- **Onda 4** entra no radar do `evolution-lab` e em estudos/papers, nao em
  backlog implementavel.

Regra pratica:

- backlog de absorção inclui **reuso efetivo, adaptação e tradução disciplinada**;
- cada item deve dizer qual comportamento melhora, o componente/código
  candidato e a camada do JARVIS, com aceite ponta a ponta;
- nenhum item deve ser escrito como "adotar tecnologia X".

---

## 7. Relacao com os docs vivos

Leitura conjunta recomendada:

- `docs/architecture/technology-study.md` para papel e classe de decisao
- `docs/architecture/technology-capability-extraction-map.md` para o que vale
  extrair
- `docs/architecture/turboquant-review.md` e outros reviews especificos quando
  a tecnologia candidata nao for uma stack completa, e sim uma primitive
  algoritmica ou infraestrutural
- `docs/architecture/hermes-agent-repository-review.md` e outros reviews
  profundos para tecnologias candidatas
- `docs/implementation/execution-backlog.md` para o lote micro executavel
- `HANDOFF.md` para a leitura tatica da rodada

---

## 8. Conclusao

A direção é entregar tarefas úteis completas usando a combinação mais simples
de componentes que satisfaça a visão e os contratos do JARVIS. Reuso de código
é uma ferramenta concreta; construir internamente exige motivo, assim como
importar uma dependência. Aumentar o número de tecnologias não é objetivo.

O próximo investimento prioritário é conversa útil com ferramentas e memória,
com uma fatia reaproveitada comparada ao baseline. Voz, Web, browser, code e
integrações avançam por jornadas verificáveis, sem depender de completar todas
as famílias deste catálogo. Autoevolução só demonstra valor quando melhora
resultados em comparação controlada e permite rollback; esta direção não
autoriza automodificação do núcleo ou promoção automática.
