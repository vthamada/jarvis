# Matriz de Aderência do Documento-Mestre

## 1. Objetivo

Este documento registra a auditoria completa do **Documento-Mestre do JARVIS**
contra a implementação atual do repositório.

Ele existe para responder, de forma rastreável:

- o que o mestre define como visão canônica;
- o que já está implementado no código;
- o que existe apenas como tipagem, contrato ou documentação;
- o que foi corretamente deferido por fase;
- o que já entrou em descompasso com a visão;
- qual lacuna deve orientar o backlog real.

Escopo desta auditoria:

- identidade, missão, princípios e filosofia;
- núcleo central, fluxo principal e papel do orquestrador;
- mentes;
- domínios;
- memórias;
- governança, segurança e autonomia;
- especialistas subordinados;
- tool layer e operação computacional;
- observabilidade, validação e evals;
- evolução e autoaperfeiçoamento;
- voz, realtime e superfícies;
- contratos, schemas e tipos;
- implementação, operação, release e incidentes.

---

## 2. Como ler a auditoria

### 2.1 Taxonomia fixa de status

Estados possíveis de aderência:

- `runtime maduro`: já opera de forma consistente com a visão canônica;
- `runtime parcial`: já opera de verdade, mas ainda abaixo da visão plena do mestre;
- `tipado/documentado`: já possui contrato, enum, schema ou regra formal, mas ainda sem runtime equivalente;
- `canônico apenas`: existe no mestre, mas sem materialização relevante no repositório;
- `deferido por fase`: ainda não entrou na implementação por escolha arquitetural explícita da fase;
- `contradição real`: o estado atual do repositório contradiz a direção canônica.

### 2.2 Classes finais de priorização

Ao final da auditoria, cada eixo deve cair em uma destas classes:

- `corrigir agora`: há descompasso relevante com o mestre ou gargalo operacional direto;
- `manter deferido`: a lacuna existe, mas está corretamente fora do corte da fase;
- `apenas preservar como visão`: faz parte da constituição do sistema, mas ainda não deve virar backlog imediato.

### 2.3 Regra de evidência

Cada eixo auditado deve registrar:

- capítulos de referência no Documento-Mestre;
- evidência principal no código ou nos documentos ativos;
- lacuna dominante;
- risco de desvio;
- próximo passo obrigatório;
- fase ou sprint em que o eixo deve ser atacado.

---

## 3. Blocos auditados do Documento-Mestre

Ordem usada nesta auditoria:

1. identidade, missão, princípios e filosofia;
2. núcleo central, fluxo principal e papel do orquestrador;
3. mentes;
4. domínios;
5. memórias;
6. governança, segurança e autonomia;
7. especialistas subordinados;
8. tool layer e operação computacional;
9. observabilidade, validação e evals;
10. evolução e autoaperfeiçoamento;
11. voz, realtime e superfícies;
12. contratos, schemas e tipos;
13. implementação, operação, release e incidentes.

---

## 4. Matriz executiva por eixo

| Eixo | Capítulos canônicos no mestre | Estado atual | Classe final | Evidência principal | Lacuna dominante | Próximo passo | Fase/sprint alvo |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `identidade, missão, princípios e filosofia` | `2` a `8`, `26`, `231` | `runtime parcial` | `corrigir agora` | `orchestrator-service`, `planning-engine`, `synthesis-engine`, `governance-service` | a identidade está presente, mas ainda não é auditada como eixo próprio de aderência | transformar princípios identitários em critérios auditáveis de runtime e síntese | `v2`, com revisão transversal em todas as sprints |
| `núcleo central e fluxo principal` | `9`, `27` a `30`, `35` a `38`, `49` | `runtime parcial` | `corrigir agora` | `orchestrator-service`, `planning-engine`, `cognitive-engine`, `langgraph_flow` | o fluxo central existe, mas a leitura do mestre ainda não governa explicitamente todos os recortes do backlog | manter o núcleo como eixo de cobrança e revisar cada sprint pela ótica do fluxo principal | `v2` contínuo |
| `mentes` | `10`, `19`, `21`, `38`, `50` | `runtime parcial` | `corrigir agora` | `shared/mind_registry.py`, `engines/cognitive-engine`, `planning-engine` | o registry canônico existe, mas a arbitragem e a composição ainda não governam o runtime com profundidade suficiente | promover o registry de mentes para fonte soberana de composição, suporte preferencial e maturidade operacional | `v2`, após consolidação de `domínios` e `memórias` |
| `domínios` | `11`, `12`, `13`, `22`, `39`, `52`, `232` | `runtime parcial` | `corrigir agora` | `knowledge-service`, `knowledge/curated/v1_corpus.json`, `knowledge/curated/domain_registry.json`, `cognitive-engine`, `specialist-engine` | o mapa canônico já está no registry, mas o runtime ainda opera por subset e heurística local em parte do roteamento | tornar o registry a fonte soberana de roteamento, corpus ativo e shadow specialists por domínio | `v2`, Sprints 5 e 6 |
| `memórias` | `14`, `23`, `40`, `51`, `83`, `232` | `runtime parcial` | `corrigir agora` | `shared/types`, `shared/memory_registry.py`, `memory-service`, `governance-service`, `orchestrator-service`, `specialist-engine` | as 11 classes já têm registry formal, mas poucas operam como políticas distintas de leitura, compartilhamento e promoção | transformar o registry de memórias em política operacional por classe e ampliar o runtime além de continuidade, missão e relacional | `v2`, Sprint 4 em diante |
| `governança, segurança e autonomia` | `24`, `42`, `54`, `230` | `runtime parcial` | `corrigir agora` | `governance-service`, `observability-service`, `shared/contracts` | a governança é forte no recorte atual, mas ainda não cobre toda a amplitude formal do mestre | expandir a auditoria por tipo de decisão e por nível de autonomia | `v2`, transversal |
| `especialistas subordinados` | `64`, `76.4`, `254` a `263` | `runtime parcial` | `corrigir agora` | `specialist-engine`, `governance-service`, `orchestrator-service`, `shared/contracts` | há handoff e fronteira, mas ainda não há especialistas realmente orientados por domínio com memória compartilhada mais rica | consolidar memória relacional e amarrar especialista a domínio e contratos canônicos | `v2`, Sprints 3 e 4 |
| `tool layer e operação computacional` | `15`, `41`, `53`, `65` | `runtime parcial` | `manter deferido` | `operational-service`, `tools/`, artefatos textuais do baseline | o mestre descreve uma camada operacional mais ampla do que o recorte atual implementa | manter a operação textual segura e só expandir quando o `v2` pedir | `v2` tardio ou `v3` |
| `observabilidade, validação e evals` | `44`, `55`, `66`, `233`, `301` a `311`, `329` a `342` | `runtime parcial` | `corrigir agora` | `observability-service`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`, `evolution-lab` | os sinais de aderência por eixo já existem, mas ainda falta usá-los para fechar o primeiro corte do `v2` | usar `domain_alignment_status`, `memory_alignment_status` e `specialist_sovereignty_status` para decidir manutenção, ajuste ou contenção do recorte atual | `v2`, Sprint 6 |
| `evolução e autoaperfeiçoamento` | `16`, `25`, `43`, `56`, `67`, `313` a `327` | `runtime parcial` | `manter deferido` | `evolution-lab`, `tools/evolution_from_pilot.py`, proposals sandbox-only | existe laboratório e governança, mas não a camada evolutiva plena descrita pelo mestre | preservar o sandbox e só promover quando houver maturidade de baseline maior | `v2` tardio e `v3` |
| `voz, realtime e superfícies` | `68`, `76.1`, `126` a `128`, `253` | `deferido por fase` | `manter deferido` | documentação e referência arquitetural; ausência de runtime oficial | a visão está clara, mas o corte atual do projeto ainda não autoriza materialização | manter fora do backlog imediato e preservar a direção canônica | `v3` ou fase específica futura |
| `contratos, schemas e tipos` | `238` a `273` | `runtime parcial` | `corrigir agora` | `shared/contracts`, `shared/types`, serviços centrais | vários contratos canônicos já existem, mas a cobertura ainda é desigual entre eixos e especialistas | fechar registries e alinhar novos contratos à matriz de aderência | `v2`, transversal |
| `implementação, operação, release e incidentes` | `286` a `350` | `runtime parcial` | `corrigir agora` | `docs/implementation`, `docs/operations`, `tools/close_stateful_runtime_cycle.py`, `tools/validate_baseline.py` | a operação está madura para o baseline, mas o mestre ainda não é usado como régua contínua de cada ciclo | recalibrar o `v2` para declarar eixo, lacuna e não-cobertura por sprint | `v2`, imediato |

Leitura objetiva:

- o eixo mais distante do mestre continua sendo `domínios`, agora com mapa canônico completo já materializado no registry;
- `memórias` é o eixo com maior impacto operacional imediato, porque o registry já existe mas ainda não governa o runtime por classe;
- `mentes` está melhor encaminhado, com registry canônico ativo, mas ainda implícito demais na arbitragem;
- `voz` e parte da `tool layer` não são falhas; são deferimentos corretos de fase;
- o maior gargalo transversal segue sendo a falta de registries canônicos e de backlog explicitamente guiado pelo mestre.

---

## 5. Auditoria detalhada por eixo

## 5.1 Identidade, missão, princípios e filosofia

### Definição canônica

O mestre define o JARVIS como um sistema unificado, com identidade própria,
pluralidade interna, memória útil, governança forte e evolução sem perda de
coerência.

### Evidência atual

- `orchestrator-service` continua sendo a única superfície final de resposta;
- `planning-engine`, `cognitive-engine` e `synthesis-engine` preservam o núcleo como
  consolidado da resposta;
- `governance-service` protege memória crítica, risco e autonomia;
- `HANDOFF.md`, `README.md` e os ciclos ativos preservam o núcleo como soberano.

### Julgamento

| Subárea | Estado | Observação |
| --- | --- | --- |
| identidade unificada | `runtime parcial` | o sistema já protege a unidade percebida |
| princípios nucleares | `tipado/documentado` | aparecem com força em docs e decisões, mas ainda sem checklist explícito por eixo |
| filosofia arquitetural | `tipado/documentado` | o repositório segue a filosofia geral, mas sem auditoria formal contínua |

Classe final:

- `corrigir agora`

Risco de desvio:

- continuar implementando bem o curto prazo sem verificar se a identidade ainda está sendo preservada como critério de aceitação.

Próximo passo obrigatório:

- transformar princípios identitários e filosóficos em perguntas fixas de revisão do backlog e da síntese.

## 5.2 Núcleo central, fluxo principal e papel do orquestrador

### Definição canônica

O mestre descreve um núcleo central forte, com classificador, roteador,
planejador, coordenador e arbitragem, sempre acima de especialistas e tools.

### Evidência atual

- `orchestrator-service` coordena o fluxo ponta a ponta;
- `planning-engine`, `cognitive-engine`, `synthesis-engine` e `governance-service`
  operam em torno do núcleo;
- `langgraph_flow` já absorve recorte stateful sem substituir o runtime inteiro.

### Julgamento

| Subárea | Estado | Observação |
| --- | --- | --- |
| fluxo central do núcleo | `runtime parcial` | já existe de forma robusta para baseline, continuidade e especialistas |
| papel soberano do orquestrador | `runtime parcial` | está preservado, inclusive com `LangGraph` subordinado |
| metacontrole pleno do fluxo | `runtime parcial` | a coordenação existe, mas ainda mais operacional do que metacognitiva |

Classe final:

- `corrigir agora`

Risco de desvio:

- abrir especialistas e runtimes auxiliares sem revisar o papel soberano do núcleo em cada nova sprint.

Próximo passo obrigatório:

- manter toda sprint do `v2` explicitamente subordinada ao fluxo central do núcleo.

## 5.3 Mentes

### Definição canônica

O mestre define 24 mentes oficiais, com 12 mentes nucleares ativas no recorte do
`v1`, e prevê composição, arbitragem e combinações preferenciais entre elas.

### Evidência atual

- `shared/mind_registry.py` registra as 24 mentes canônicas e marca as 12 mentes nucleares ativas;
- `engines/cognitive-engine` materializa as 12 mentes nucleares e já consulta o registry para suporte preferencial;
- `planning-engine` e `synthesis-engine` consomem efeitos desse recorte;
- já existe seleção de mente primária, apoios e tensão dominante.

### Julgamento

| Subárea | Estado | Observação |
| --- | --- | --- |
| mapa completo de 24 mentes | `tipado/documentado` | já existe registry canônico em `shared/mind_registry.py` |
| núcleo de 12 mentes | `runtime parcial` | já opera de forma útil |
| composição e arbitragem entre mentes | `runtime parcial` | já há suporte preferencial inicial, mas a arbitragem ainda é rasa e pouco soberana |
| maturidade por mente | `tipado/documentado` | o registry já carrega status formal por mente |

Classe final:

- `corrigir agora`

Risco de desvio:

- tratar mentes como lista local do `v1`, em vez de eixo cognitivo progressivo do sistema.

Próximo passo obrigatório:

- promover o registry de mentes para fonte soberana da composição, da arbitragem e da maturidade operacional.

## 5.4 Domínios

### Definição canônica

O mestre define 30 domínios principais, além de domínios operacionais e meta,
como mapa oficial de conhecimento do sistema.

### Evidência atual

- `knowledge/curated/domain_registry.json` já espelha o mapa canônico com domínios principais, operacionais e meta;
- `knowledge-service` separa o mapa canônico das rotas runtime ativas do ciclo;
- o corpus atual ainda cobre apenas subconjunto pragmático;
- o `cognitive-engine` já usa fallback canônico e prioriza hints vindos do registry.

### Julgamento

| Subárea | Estado | Observação |
| --- | --- | --- |
| mapa oficial de 30 domínios | `tipado/documentado` | o mapa canônico completo já existe no registry |
| domínios ativos no runtime | `runtime parcial` | as rotas ativas ainda cobrem subset útil do ciclo |
| roteamento pela taxonomia oficial | `runtime parcial` | o registry já influencia hints e rotas, mas ainda não governa todo o runtime |
| maturidade por domínio | `tipado/documentado` | activation stage, maturity e scope já existem no registry |

Classe final:

- `corrigir agora`

Risco de desvio:

- o sistema continuar operando por utilidade local e não por mapa cognitivo rastreável.

Próximo passo obrigatório:

- tornar o registry soberano para roteamento, corpus ativo, especialistas em shadow mode e comparação do `v2`.

## 5.5 Memórias

### Definição canônica

O mestre define 11 classes principais de memória, com promoção, arquivamento,
relação com identidade, domínios, autoevolução e contexto operacional.

### Evidência atual

- `MemoryClass` já tipa as 11 classes;
- `shared/memory_registry.py` registra as 11 classes com status, defaults de recuperação e elegibilidade para compartilhamento;
- `memory-service` opera contextual, episódica, missão, checkpoint, replay, pausa e
  continuidade relacionada;
- `memory-service` passou a persistir contexto relacional compartilhado por especialista,
  mediado pelo núcleo e recuperável por missão, com refs canônicas por classe e por domínio;
- `governance-service` protege memória crítica;
- `specialist-engine` e `orchestrator-service` já consomem esse contexto no handoff do `v2`.

### Julgamento

| Subárea | Estado | Observação |
| --- | --- | --- |
| taxonomia das 11 memórias | `tipado/documentado` | enum e registry canônicos já existem |
| memória contextual, episódica e de missão | `runtime parcial` | opera no baseline e no `v1.5` |
| memória relacional | `runtime parcial` | já opera como contexto compartilhado mediado pelo núcleo no `v2` |
| memória de domínio, evolutiva e semântica rica | `tipado/documentado` | já têm registry formal, mas ainda sem política runtime plena |
| promoção e arquivamento formais | `canônico apenas` | ainda não operam como sistema vivo |

Classe final:

- `corrigir agora`

Risco de desvio:

- continuar chamando de memória expandida o que ainda é sobretudo continuidade contextual aprimorada.

Próximo passo obrigatório:

- promover o registry de memórias para política runtime por classe e ampliar leitura, compartilhamento e promoção além do recorte atual.

## 5.6 Governança, segurança e autonomia

### Definição canônica

O mestre exige classificação de risco, níveis de autonomia, regimes de permissão,
supervisão de ação, memória e evolução, além de auditoria e contenção.

### Evidência atual

- `governance-service` já decide `allow`, `allow_with_conditions`, `block` e
  `defer_for_validation`;
- o sistema já suporta checkpoints contidos, pausas governadas e retomada manual;
- `observability-service` registra rastreabilidade útil.

### Julgamento

| Subárea | Estado | Observação |
| --- | --- | --- |
| governança de operação | `runtime parcial` | bem materializada no recorte atual |
| governança de memória | `runtime parcial` | forte para memória crítica e continuidade |
| governança evolutiva | `runtime parcial` | existe no sandbox, ainda não plena |
| modelo completo de autonomia | `tipado/documentado` | a visão do mestre é maior do que o uso atual |

Classe final:

- `corrigir agora`

Risco de desvio:

- a governança ficar forte só nos fluxos mais recentes e não virar modelo geral por eixo.

Próximo passo obrigatório:

- indexar decisões de governança também por eixo do mestre e por tipo de autonomia.

## 5.7 Especialistas subordinados

### Definição canônica

O mestre prevê especialistas subordinados ao núcleo, sem identidade própria,
ligados a memória, governança e evolução, preferencialmente por domínio.

### Evidência atual

- `shared/contracts` já expõe contratos mínimos;
- `specialist-engine` já separa seleção, composição e handoff;
- `governance-service` e `orchestrator-service` já governam convocações.

### Julgamento

| Subárea | Estado | Observação |
| --- | --- | --- |
| fronteira entre núcleo e especialista | `runtime parcial` | já existe com clareza |
| handoff governado e observável | `runtime parcial` | Sprint 1 e Sprint 2 do `v2` fecharam o recorte estrutural |
| especialistas por domínio | `canônico apenas` | ainda não materializados |
| memória compartilhada rica com especialistas | `canônico apenas` | eixo aberto na Sprint 3 |

Classe final:

- `corrigir agora`

Risco de desvio:

- abrir `shadow mode` antes de amarrar especialistas a domínio e memória relacional de verdade.

Próximo passo obrigatório:

- condicionar a evolução dos especialistas ao avanço de `memórias` e `domínios`.

## 5.8 Tool layer e operação computacional

### Definição canônica

O mestre descreve uma camada ampla de percepção, produção, execução, intervenção,
supervisão de ação e ferramentas.

### Evidência atual

- `operational-service` produz artefatos textuais de baixo risco;
- o projeto possui tooling de validação, piloto, comparação e fechamento de ciclo;
- não há ainda computer use amplo nem tool layer multimodal madura.

### Julgamento

| Subárea | Estado | Observação |
| --- | --- | --- |
| operação textual segura | `runtime parcial` | já existe e é útil |
| tool layer ampla | `deferido por fase` | ainda fora do corte |
| computer use forte | `deferido por fase` | continua referenciado, não implementado |

Classe final:

- `manter deferido`

Risco de desvio:

- tratar ausência de tool layer ampla como falha imediata, quando ela é deferimento explícito de fase.

Próximo passo obrigatório:

- manter a contenção do escopo operacional até que especialistas e memórias amadureçam.

## 5.9 Observabilidade, validação e evals

### Definição canônica

O mestre exige rastreabilidade, telemetria, validação em camadas, benchmarks e
critérios formais de qualidade.

### Evidência atual

- `observability-service` grava trilha local, auditoria de fluxo e anomalias;
- `tools/internal_pilot_report.py` e `tools/compare_orchestrator_paths.py`
  geram evidência operacional;
- `evolution-lab` já compara baseline e candidata em sandbox.

### Julgamento

| Subárea | Estado | Observação |
| --- | --- | --- |
| rastreabilidade operacional | `runtime parcial` | forte para baseline, continuidade e especialistas |
| evals comparativas | `runtime parcial` | existem para alguns fluxos críticos |
| benchmarks por eixo canônico | `tipado/documentado` | o mestre pede cobertura mais ampla do que a hoje materializada |
| validação por camada do sistema | `runtime parcial` | forte em ciclos recentes, ainda não indexada por todos os eixos |

Classe final:

- `corrigir agora`

Risco de desvio:

- continuar medindo o que foi recentemente implementado sem medir o que o mestre define como obrigatório.

Próximo passo obrigatório:

- ligar observabilidade e evals aos eixos auditados, especialmente `domínios`, `memórias` e `mentes`.

## 5.10 Evolução e autoaperfeiçoamento

### Definição canônica

O mestre prevê autoevolução governada, comparativa, com memória evolutiva,
promoção controlada, rollback e sandbox.

### Evidência atual

- `evolution-lab` já opera proposals e decisões `sandbox-only`;
- `tools/evolution_from_pilot.py` converte sinais em proposals;
- há comparação entre baseline e candidata.

### Julgamento

| Subárea | Estado | Observação |
| --- | --- | --- |
| sandbox evolutivo | `runtime parcial` | existe e já é útil |
| promoção governada | `runtime parcial` | existe em nível de laboratório |
| camada evolutiva plena | `deferido por fase` | o mestre projeta algo mais amplo do que o backlog atual |

Classe final:

- `manter deferido`

Risco de desvio:

- puxar autoevolução mais agressiva antes de consolidar aderência do núcleo ao mestre.

Próximo passo obrigatório:

- manter a evolução como apoio comparativo e não como prioridade principal do `v2`.

## 5.11 Voz, realtime e superfícies

### Definição canônica

O mestre descreve camada de voz, sessão realtime, identidade vocal, barge-in,
latência e ferramentas em modo voz.

### Evidência atual

- a camada está detalhada no mestre e em documentos derivados;
- o repositório ainda opera com `jarvis-console` como superfície mínima real;
- não há runtime oficial de voz ativo.

### Julgamento

| Subárea | Estado | Observação |
| --- | --- | --- |
| console mínimo | `runtime parcial` | superfície textual real já existe |
| voz/realtime oficiais | `deferido por fase` | fora do backlog imediato |
| multimodalidade | `deferido por fase` | preservada como visão futura |

Classe final:

- `manter deferido`

Risco de desvio:

- confundir ausência de implementação com falha arquitetural, quando a decisão de fase é explícita.

Próximo passo obrigatório:

- manter apenas documentação e não abrir implementação de voz neste corte.

## 5.12 Contratos, schemas e tipos

### Definição canônica

O mestre prevê contratos formais do sistema, enums canônicos, estados e regras de
versionamento.

### Evidência atual

- `shared/contracts` e `shared/types` já materializam parte relevante dos contratos;
- o `v2` já abriu contratos de continuidade e de especialistas;
- serviços centrais já consomem esse material compartilhado.

### Julgamento

| Subárea | Estado | Observação |
| --- | --- | --- |
| enums e tipos comuns | `runtime parcial` | já orientam o sistema |
| contratos canônicos iniciais | `runtime parcial` | boa parte já foi absorvida |
| cobertura uniforme por eixo | `tipado/documentado` | ainda desigual entre núcleos e recortes futuros |

Classe final:

- `corrigir agora`

Risco de desvio:

- os contratos seguirem evoluindo por necessidade local sem fechar o mapa canônico por eixo.

Próximo passo obrigatório:

- amarrar novos contratos e registries diretamente à matriz de aderência.

## 5.13 Implementação, operação, release e incidentes

### Definição canônica

O mestre define estratégia de implementação faseada, validação, readiness,
releases, incidentes e transição entre versões.

### Evidência atual

- o `v1`, o `pós-v1` e o `v1.5` já tiveram ciclos formais de fechamento;
- há ferramentas de checklist, piloto, comparação e fechamento de ciclo;
- `HANDOFF.md`, `README.md`, `programa-ate-v3.md` e os sprint cycles materializam a
  governança operacional.

### Julgamento

| Subárea | Estado | Observação |
| --- | --- | --- |
| estratégia de ciclo e transição | `runtime parcial` | já existe de forma concreta |
| readiness e operação controlada | `runtime parcial` | forte para baseline |
| uso do mestre como régua de cada sprint | `tipado/documentado` | ainda incompleto até esta auditoria |

Classe final:

- `corrigir agora`

Risco de desvio:

- o backlog continuar guiado só pelo ciclo local e não pela cobertura canônica.

Próximo passo obrigatório:

- recalibrar o `v2` para declarar eixo, lacuna e não-cobertura em cada sprint.

---

## 6. Gargalos principais identificados

O gargalo atual não é falta de visão no Documento-Mestre.

Os gargalos reais são:

1. ausência de registries canônicos de `mentes`, `domínios` e `memórias`;
2. ausência de backlog explicitamente indexado pelos eixos do mestre;
3. cobertura ainda parcial de princípios identitários, composição de mentes e
   taxonomia de domínios;
4. tendência do projeto a resolver bem o curto prazo sem fechar lacunas canônicas
   explicitamente.

Em uma frase:

- o mestre já diz o que o sistema deve ser;
- o repositório já resolve problemas reais;
- o que faltava era uma auditoria que transformasse o mestre em cobrança rastreável.

### 6.1 Ordem de correção do descompasso

Ordem recomendada para reaproximar implementação e mestre:

1. `domínios`
2. `memórias`
3. `mentes`
4. `especialistas subordinados`
5. `observabilidade, validação e evals`

Justificativa:

- `domínios` é hoje o maior descompasso estrutural;
- `memórias` é o eixo com maior impacto direto na Sprint 3 do `v2`;
- `mentes` já possuem recorte funcional, mas ainda sem registry e sem ecologia explícita;
- especialistas só devem amadurecer depois de `domínios` e `memórias`;
- observabilidade precisa medir a aderência aos eixos, não apenas aos fluxos recentes.

---

## 7. Recalibração obrigatória do v2

A partir desta auditoria, o `v2` deve ser lido assim:

- Sprint 3 fechou o primeiro avanço prioritário do eixo `memórias`, com contexto compartilhado mediado pelo núcleo;
- Sprint 4 abriu o registry inicial de `domínios` e ligou o primeiro especialista em `shadow mode` com vínculo explícito a domínio e memória compartilhada;
- Sprint 5 fechou a medição explícita de aderência do recorte de especialistas aos eixos do mestre, não apenas performance local;
- Sprint 6 deve fechar o primeiro corte do `v2` dizendo explicitamente o que ficou:
  - `corrigido agora`;
  - `mantido deferido`;
  - `preservado apenas como visão`.

Regra prática:

- nenhuma sprint do `v2` deve avançar sem declarar:
  1. eixo principal do mestre;
  2. lacuna dominante atacada;
  3. critério de avanço alterado ao final da sprint;
  4. eixos que continuam fora de cobertura.

---

## 8. Regra de uso desta matriz

Esta matriz deve ser atualizada quando acontecer uma destas situações:

- um eixo novo do mestre passar a ser coberto formalmente;
- um eixo mudar de `canônico apenas` para `tipado/documentado`;
- um eixo mudar de `tipado/documentado` para `runtime parcial`;
- um eixo atingir `runtime maduro`;
- uma sprint do `v2` ou fase futura alterar a classe final de priorização;
- um deferimento de fase virar contradição real ou vice-versa.

Ela não substitui:

- o Documento-Mestre;
- o `HANDOFF.md`;
- o sprint cycle ativo;
- os documentos de operação.

Ela existe para impedir que o repositório avance sem rastreabilidade de aderência.

### 8.1 Leitura obrigatória por sprint

Cada sprint ativa deve responder explicitamente:

1. qual eixo principal da matriz está sendo movimentado;
2. qual lacuna dominante daquele eixo está sendo atacada;
3. qual critério de avanço muda ao final da sprint;
4. o que continua fora de cobertura, mesmo após a entrega.

### 8.2 Aplicação imediata ao ciclo atual

Aplicação imediata ao `v2`:

- Sprint 3 deve ser lida como avanço prioritário do eixo `memórias`;
- o maior eixo crítico do ciclo inteiro continua sendo `domínios`;
- `mentes` não devem ser expandidas por quantidade antes de ganharem registry e regras de composição;
- `voz`, `realtime`, `computer use` amplo e memória profunda com `pgvector` seguem como `deferido por fase`;
- qualquer estudo externo só faz sentido se reduzir lacuna de `domínios`, `memórias`, `mentes` ou `especialistas` de forma comprovável.
