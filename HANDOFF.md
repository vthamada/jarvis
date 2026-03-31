# HANDOFF

## Metadata

- Atualizado em: 2026-03-31
- Branch: `main`
- Commit de referência: `e165a5c`
- Artefato canônico do projeto: `documento_mestre_jarvis.md`
- Estado do projeto: `v1` encerrado e congelado para uso controlado; primeiro ciclo do `pós-v1` encerrado; primeiro ciclo do `v1.5` encerrado; primeiro corte do `v2` encerrado; `v2-alignment-cycle` encerrado; próximo corte do `v2` aberto

## Atualização do próximo corte do v2

A primeira implementação do próximo corte do `v2` já foi aberta.

Leitura operacional correta desta rodada:

- as rotas `software_development`, `analysis`, `governance`, `operational_readiness`, `strategy` e `decision_risk` já operam em modo `guided`, ainda subordinadas ao núcleo;
- `specialist-engine` agora aceita rotas canônicas de especialista acima de `shadow`, desde que continuem `through_core_only` e `advisory_only`, e passou a validar se o vínculo domínio->especialista realmente bate com o registry soberano;
- `memory-service` já gera `domain_guided_memory_packet` de forma genérica para rotas promovidas do registry;
- `orchestrator-service` passou a emitir `domain_specialist_completed`, além dos sinais legados de `shadow` quando eles existirem;
- `observability-service` passou a auditar alinhamento de domínio por convocação canônica de especialista, não apenas por `shadow mode`.

## Meta atual

Abrir o próximo corte do `v2` sobre um runtime já alinhado aos eixos do Documento-Mestre, mantendo aderência por eixo como gate fixo de promoção e evitando ampliar superfícies cedo demais.

Sistema oficial de planejamento desta fase:

- `HANDOFF.md` como retomada tático-operacional;
- `docs/roadmap/programa-ate-v3.md` como direção do programa até `v3`;
- `docs/archive/implementation/v2-cycle-closure.md` como fechamento formal do primeiro corte do `v2`;
- `docs/archive/implementation/v2-alignment-cycle.md` como histórico fechado do ciclo anterior;
- `docs/archive/implementation/v2-native-memory-scope-hardening-cut.md` como ultimo recorte funcional executado do baseline nativo atual;
- `docs/implementation/v2-native-memory-scope-hardening-cut-closure.md` como fechamento formal regeneravel do ultimo recorte funcional;
- `docs/implementation/v2-repository-hygiene-and-tools-review-cut.md` como ultimo recorte estrutural executado;
- `docs/implementation/v2-repository-hygiene-inventory.md` como inventario regeneravel da revisao estrutural ativa;
- `docs/implementation/v2-repository-hygiene-doc-decisions.md` como decisao regeneravel de classificacao dos docs ativos;
- `docs/implementation/v2-repository-hygiene-tool-decisions.md` como decisao regeneravel de classificacao dos entrypoints de `tools/`;
- `docs/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md` como fechamento formal regeneravel da revisao estrutural mais recente;
- `docs/archive/implementation/v2-sovereign-alignment-cut.md` como histórico de transição do corte anterior;
- `docs/archive/implementation/v2-domain-consumers-and-workflows-cut-closure.md` como fechamento formal regenerável do corte anterior imediato;
- `docs/documentation/matriz-de-aderencia-mestre.md` como ponte entre visão canônica e backlog real.

Leitura prioritária de aderência neste momento:

- eixo concluído na Sprint 1: `domínios`, com registry soberano sobre roteamento, maturity gate, shadow specialist sem heurística residual e fallback derivado;
- eixo concluído na Sprint 2: `memórias`, com políticas operacionais por classe para recovery, compartilhamento mediado e auditoria por classe;
- eixo concluído na Sprint 3: `mentes`, com arbitragem soberana por registry, mente primária, apoios, supressões e tensão dominante observáveis;
- eixo concluído na Sprint 4: `identidade`, com assinatura do núcleo, guardrails de governança e resposta auditável ao longo do fluxo.

Estado do ciclo rolante:

- primeiro ciclo do `pós-v1` concluído;
- primeiro ciclo do `v1.5` concluído;
- Sprint 1 do `v2` concluída;
- Sprint 2 do `v2` concluída;
- Sprint 3 do `v2` concluída;
- Sprint 4 do `v2` concluída;
- Sprint 5 do `v2` concluída;
- Sprint 6 do `v2` concluída;
- o primeiro corte do `v2` está formalmente encerrado;
- Sprint 1 do `v2-alignment-cycle` concluída;
- Sprint 2 do `v2-alignment-cycle` concluída;
- Sprint 3 do `v2-alignment-cycle` concluída;
- Sprint 4 do `v2-alignment-cycle` concluída;
- Sprint 5 do `v2-alignment-cycle` concluída;
- Sprint 6 do `v2-alignment-cycle` concluída;
- o próximo corte do `v2` está formalmente aberto;

## Decisões fechadas

Não rediscutir sem evidência forte ou mudança explícita de direção:

- o JARVIS é um sistema unificado, não um chatbot simples;
- o núcleo continua próprio e soberano na relação com o usuário;
- especialistas são subordinados ao núcleo, não competidores de identidade;
- `Python` continua como linguagem principal;
- `PostgreSQL` é o backend operacional oficial de memória;
- `sqlite` continua apenas como fallback local;
- `LangSmith` continua complementar; a trilha local persistida segue como fonte primária de auditoria;
- `LangGraph` continua como direção arquitetural forte; o subfluxo stateful de continuidade já foi absorvido parcialmente, sem transformar o runtime inteiro no runtime principal do sistema;
- referências externas passam a ser avaliadas em dois eixos: posicionamento na stack e função arquitetural por camada;
- o Documento-Mestre continua sendo o único artefato canônico de visão de produto.

Regra curta de nomenclatura técnica:

- a regra de nomes do sistema deve privilegiar nomes profissionais, limpos, robustos e duráveis;
- artefatos permanentes do sistema não devem carregar `v1`, `v2`, `poc`, `draft`, `temp` ou rótulos equivalentes no nome técnico principal;
- fase, maturidade e modo de execução devem ficar em metadata, docs vivos ou no conteúdo do artefato;
- quando um artefato transitório virar parte estável do sistema, ele deve ser renomeado para forma neutra na próxima intervenção útil.

Regra curta de promoção tecnológica nesta fase:

- nenhuma tecnologia externa atravessa direto para o núcleo;
- primeiro ela precisa responder a uma lacuna concreta do ciclo ativo;
- depois precisa ser classificada como `absorver depois`, `usar como referência` ou `rejeitar`;
- só então pode virar fluxo experimental, complemento controlado ou candidata a baseline de fase futura.

Responsabilidade prática nesta fase:

- o agente ativo conduz a análise técnica e produz a recomendação;
- a promoção só vale quando houver evidência e alinhamento com os artefatos oficiais do ciclo;
- nenhuma promoção tecnológica reabre o baseline do `v1` por conveniência.

Autonomia operacional nesta fase:

- o agente ativo pode executar sozinho sincronização de docs vivos, refactors de nomenclatura, endurecimento de contratos, testes, observabilidade, gates e coerência entre registries e runtime;
- o agente ativo pode abrir e fechar sprints dentro do corte ativo quando isso não mudar a direção macro já fechada;
- o operador deve ser acionado apenas para decisões de direção, como mudança de ontologia, promoção de tecnologia externa a baseline central, abertura de nova superfície principal ou alteração da prioridade macro do programa;
- a regra prática é simples: implementação dentro da direção fechada é autonomia do Codex; mudança de direção continua reservada ao operador.

## Estado atual do repositório

Hoje o repositório contém:

- baseline integrado entre orquestração, memória, governança, conhecimento, observabilidade e operação;
- `jarvis-console` como interface textual mínima do baseline;
- `memory-service` com histórico episódico, resumo contextual, estado mínimo de missão e continuidade relacionada inicial;
- `shared/memory_registry.py` como registry formal das 11 classes de memória, já conectado ao recovery default e ao compartilhamento com especialistas;
- `shared/mind_registry.py` como registry formal das 24 mentes canônicas, com suporte preferencial inicial no `cognitive-engine`;
- `observability-service` com trilha persistida, auditoria de fluxo e espelhamento agentic complementar;
- `evolution-lab` persistindo proposals e decisões `sandbox-only`;
- `tools/validate_baseline.py`, `tools/go_live_internal_checklist.py`, `tools/run_internal_pilot.py`, `tools/compare_orchestrator_paths.py`, `tools/evolution_from_pilot.py`, `tools/archive/close_stateful_runtime_cycle.py` e `tools/archive/close_alignment_cycle.py` operacionais;
- estudo tecnológico consolidado em `docs/architecture/technology-study.md`;
- sistema documental em duas camadas ativas para programa e sprint cycle.

### Baseline materializado

Capacidades concretas já presentes no repositório:

- `orchestrator-service` coordenando o fluxo ponta a ponta do núcleo;
- `memory-service` com persistência útil, recuperação contextual e continuidade relacionada inicial;
- `knowledge/curated/domain_registry.json` com mapa canônico de domínios separado das rotas runtime ativas do ciclo;
- `governance-service` com decisões `allow`, `allow_with_conditions`, `block` e `defer_for_validation`;
- `knowledge-service` com corpus curado local e retrieval determinístico;
- `observability-service` com trilha persistida, auditoria de requests e espelhamento agentic complementar;
- `operational-service` com produção de artefatos textuais de baixo risco;
- `evolution-lab` comparando baseline e candidata em regime `sandbox-only`;
- `jarvis-console` como primeira superfície textual real do sistema.

## O que foi feito até aqui

Principais entregas já consolidadas:

- fechamento disciplinado do `v1` com baseline operacional e console mínimo;
- validação local e `controlled` com `PostgreSQL`;
- `internal pilot` executado e convertido em evidência operacional;
- fluxo opcional de `LangGraph` aberto no orquestrador;
- Sprint 1 do `pós-v1` concluída, com modelo mínimo de continuidade entre missões relacionadas;
- Sprint 2 concluída, com ranking determinístico entre missão ativa, loops abertos e missão relacionada;
- Sprint 3 concluída, com decisão explícita entre continuar, encerrar, reformular ou retomar continuidade relacionada;
- Sprint 4 concluída, com snapshot persistente de continuidade da sessão e síntese orientada a continuidade acima da missão atual;
- Sprint 5 concluída, com auditoria explícita da continuidade, sinais comparáveis no piloto e integração desses sinais ao laboratório sandbox;
- Sprint 6 concluída, com fechamento formal do primeiro ciclo do `pós-v1` e decisão explícita de promoção para `v1.5`;
- Sprint 1 do `v1.5` concluída, com checkpoint explícito de continuidade e estado recuperável por sessão;
- Sprint 2 do `v1.5` concluída, com replay explícito, retomada governada e ponto de recuperação rastreável por sessão;
- Sprint 3 do `v1.5` concluída, com pausa `HITL` persistente, resolução manual rastreável e retomada segura acima do checkpoint governado;
- Sprint 4 do `v1.5` concluída, com subfluxo stateful de continuidade absorvido parcialmente em `LangGraph` e sinal explícito de runtime no fluxo comparativo;
- Sprint 5 do `v1.5` concluída, com evals do runtime de continuidade, cenários de conflito e retomada manual no piloto e decisão `candidate_ready_for_eval_gate` para o recorte absorvido;
- Sprint 6 do `v1.5` concluída, com fechamento formal do ciclo, classificação do backlog e decisão explícita de promoção para `v2`;
- Sprint 1 do `v2` concluída, com contratos mínimos de convocação de especialistas, fronteiras explícitas de runtime e integração mínima no núcleo;
- Sprint 2 do `v2` concluída, com seleção governada de especialistas, handoff interno observável e contenção explícita quando a convocação viola fronteiras;
- Sprint 3 do `v2` concluída, com memória relacional compartilhada mediada pelo núcleo, contexto persistido por especialista e handoff enriquecido sem escrita direta fora do núcleo;
- Sprint 4 do `v2` concluída, com registry inicial de domínios do ciclo, rota canônica `software_development -> software_change_specialist` e execução explícita em `shadow mode`;
- Sprint 5 do `v2-alignment-cycle` concluída, com gates explícitos de aderência por eixo em `internal_pilot_report`, `compare_orchestrator_paths` e `evolution_from_pilot`.
- Documento-Mestre ampliado com referências arquiteturais oficiais por função.

## O que ainda falta

Pendências principais desta fase:

- sincronizar os docs vivos para refletir um único corte ativo;
- tornar o registry de domínios a fonte soberana de roteamento e refs canônicas;
- explicitar consumo de memória por classe nas rotas guiadas;
- convergir `mind_registry` com domínios canônicos e promover os gates por eixo a regra contínua de engenharia.

Regra de estudo externo no `v2`:

- entra apenas o estudo que ajude diretamente contratos de especialistas, handoffs internos, memória relacional, arbitragem soberana ou gates de aderência do ciclo;
- `OpenHands` e `PydanticAI` seguem como referências mais diretamente ligadas ao corte imediato;
- `Hermes Agent`, `Graphiti`, `Zep`, `LangGraph` e `OpenAI Agents SDK` entram apenas como apoio dirigido ao problema do ciclo;
- `computer use` amplo, voz oficial, memória profunda com `pgvector` como base canônica e assistente operacional amplo continuam fora do foco imediato.

## Próximos passos imediatos

Ordem recomendada:
1. usar `docs/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md` como fechamento estrutural mais recente;
2. selecionar o proximo recorte funcional a partir de `docs/implementation/v2-adherence-snapshot.md` e do backlog vivo;
3. preservar `axis gates`, baseline release-grade e a superficie ativa enxuta como regra continua;
4. manter historico regeneravel em `docs/archive/implementation/` e `tools/archive/` sem reexpandir a raiz do repositorio;
5. manter qualquer delete definitivo dependente de nova checagem formal de referencias.

## Riscos e bloqueios

- o `pós-v1` não deve reabrir o baseline do `v1` sem necessidade real;
- `pgvector`, memória semântica profunda, web, voz e especialistas amplos continuam fora do caminho crítico do ciclo atual;
- o fluxo opcional de `LangGraph` continua dependente do extra `.[langgraph]`, mesmo após a absorção parcial do subfluxo stateful;
- o maior risco atual não é estabilidade local; é abrir especialistas cedo demais sem contratos, memória relacional e governança suficientes.

## Arquivos relevantes

- `documento_mestre_jarvis.md`
- `README.md`
- `HANDOFF.md`
- `CHANGELOG.md`
- `docs/roadmap/programa-ate-v3.md`
- `docs/archive/implementation/v2-domain-consumers-and-workflows-cut.md`
- `docs/archive/implementation/v2-memory-gap-evidence-cut.md`
- `docs/archive/implementation/v2-memory-gap-evidence-protocol.md`
- `docs/archive/implementation/v2-memory-gap-baseline-evidence.md`
- `docs/archive/implementation/v2-memory-gap-decision.md`
- `docs/archive/implementation/v2-memory-gap-evidence-cut-closure.md`
- `docs/archive/implementation/v2-native-memory-scope-hardening-cut.md`
- `docs/documentation/matriz-de-aderencia-mestre.md`
- `docs/architecture/technology-study.md`
- `docs/archive/implementation/`
- `docs/operations/v1-operational-baseline.md`
- `services/orchestrator-service/src/orchestrator_service/service.py`
- `services/memory-service/src/memory_service/service.py`
- `services/memory-service/src/memory_service/repository.py`
- `services/observability-service/src/observability_service/service.py`
- `engines/planning-engine/src/planning_engine/engine.py`
- `tools/run_internal_pilot.py`
- `tools/compare_orchestrator_paths.py`
- `tools/evolution_from_pilot.py`

## Como retomar

Leitura mínima para qualquer novo agente:

1. `HANDOFF.md`
2. `documento_mestre_jarvis.md`
3. `docs/roadmap/programa-ate-v3.md`
4. `docs/archive/implementation/v1-5-cycle-closure.md`
5. `docs/archive/implementation/v2-cycle-closure.md`
6. `docs/archive/implementation/v2-alignment-cycle.md`
7. `docs/archive/implementation/v2-sovereign-alignment-cut.md`
8. `docs/architecture/technology-study.md`


## Visão de absorção tecnológica

Leitura de longo prazo desta fase e das próximas:

- o JARVIS deve evoluir como sistema cognitivo soberano capaz de absorver o melhor do ecossistema sem virar uma colagem de frameworks;
- a absorção tecnológica deve continuar subordinada ao núcleo, à memória canônica, à governança e à síntese própria do sistema;
- o objetivo não é terceirizar o cérebro do JARVIS, e sim incorporar valor arquitetural por função clara.

Fluxo longo de absorção tecnológica governada:

1. radar contínuo do ecossistema;
2. classificação arquitetural por eixo do sistema;
3. registro em memória evolutiva;
4. sandbox, benchmark ou fluxo experimental;
5. promoção governada por evidência.

Leitura correta por famílias de referência:

- `LangGraph`: fluxo stateful, checkpoints, replay e handoffs coordenados;
- `Hermes Agent`: runtime persistente, memória viva, continuidade operacional e skills;
- `Graphiti` e `Zep`: memória relacional, temporal e contextual;
- `DSPy / MIPROv2`, `TextGrad`, `AFlow`, `EvoAgentX`, `SEAL` e `Darwin Gödel Machine`: autoaperfeiçoamento, otimização e evolução governada.

Regra de disciplina:

- estudo externo não bloqueia a implementação principal;
- nenhuma tecnologia externa vira dependência central sem decisão arquitetural formal;
- toda absorção deve ser reversível, traduzida para os contratos do JARVIS e compatível com a soberania do núcleo.

## Política oficial de engenharia

A partir desta rodada, a referência oficial de boas práticas do repositório passa a ser:

- `docs/documentation/engineering-constitution.md`
- `AGENTS.md`
- `tools/engineering_gate.py`

Leitura correta:

- robustez, segurança, reversibilidade e auditabilidade deixam de ser só intenção e passam a ser política explícita;
- toda mudança relevante deve passar por contrato, teste, observabilidade e documentação;
- qualquer agente implementador deve seguir `AGENTS.md` e rodar o gate adequado antes de tratar a rodada como fechada.

Gate mínimo oficial:

```powershell
python tools/engineering_gate.py --mode standard
```

## Regra de linguagem

- documentação, visão e texto voltado a operador podem permanecer em português;
- contratos técnicos, eventos, payloads, status e novos ids de runtime devem convergir para inglês;
- ontologias canônicas derivadas do Documento-Mestre podem permanecer em português enquanto camada semântica;
- ids legados em português não devem ser expandidos por conveniência local.

## Atualizacao 2026-03-31

- specialist types do runtime seguem usando ids canonicos em ingles, com compatibilidade curta para labels legados em portugues;
- o corte de prova de lacuna de memoria multicamada foi formalmente encerrado;
- Sprint 2 permanece concluida com workflows compostos auditaveis no runtime;
- Sprint 3 foi concluida com benchmark governado por familia e matriz regeneravel em `docs/archive/implementation/v2-governed-benchmark-matrix.md`;
- `AutoGPT Platform`, `Mastra` e `Mem0` foram formalizadas como candidatas de `benchmark_now`;
- `LangGraph`, `OpenAI Agents SDK`, `CrewAI`, `Microsoft Agent Framework`, `OpenClaw`, `Hermes Agent`, `Manus`, `Letta / MemGPT`, `Zep` e `Graphiti` passaram a compor o `reference_envelope` do recorte;
- a Sprint 4 foi concluida com `tools/verify_active_cut_baseline.py` como verificador regeneravel do baseline do corte ativo;
- `tools/archive/close_domain_consumers_and_workflows_cut.py` passou a fechar o corte em `.jarvis_runtime/v2_domain_consumers_and_workflows_cut/`;
- a Sprint 1 do novo corte foi concluida com `docs/archive/implementation/v2-memory-gap-evidence-protocol.md` como protocolo regeneravel das hipoteses de lacuna do baseline atual;
- a Sprint 2 do novo corte foi concluida com `docs/archive/implementation/v2-memory-gap-baseline-evidence.md` como leitura local por escopo do baseline atual;
- a Sprint 3 do novo corte foi concluida com `docs/archive/implementation/v2-memory-gap-decision.md` como decisao formal de `manter_fechado`, preservando `Mem0` em `absorver_depois`;
- a Sprint 4 do recorte foi concluida com `docs/archive/implementation/v2-memory-gap-evidence-cut-closure.md` como fechamento formal do corte e recomendacao explicita do proximo recorte nativo;
- o baseline agora esta lido assim: conversa, sessao e missao permanecem suficientes; usuario e shared specialist memory sustentam lacuna parcial; organization scope continua apenas forma futura;
- o novo corte ativo passa a ser `v2-native-memory-scope-hardening-cut`, focado em endurecimento nativo de user scope e contexto recorrente de especialistas.
- a Sprint 1 do `v2-native-memory-scope-hardening-cut` foi concluida com snapshot nativo de `user scope`, recovery default desse escopo quando houver `user_id` e sinais minimos em observabilidade.
- a Sprint 2 do `v2-native-memory-scope-hardening-cut` foi concluida com contexto recorrente nativo por especialista promovido, ainda `through_core_only`, com telemetria de recorrencia no handoff e na observabilidade.
- a Sprint 3 do `v2-native-memory-scope-hardening-cut` foi concluida com no-go explicito de `organization scope`, publicado no runtime de memoria e resumido na observabilidade.
- a Sprint 2 foi concluida com `docs/archive/implementation/v2-governed-benchmark-scenario-specs.md` como artefato regeneravel de scenario specs e fronteiras sandbox;
- a Sprint 3 foi concluida com `docs/archive/implementation/v2-governed-benchmark-decisions.md` como decisao formal por tecnologia e racional curto contra o baseline do JARVIS;
- a Sprint 4 do corte anterior foi concluida com `docs/archive/implementation/v2-governed-benchmark-execution-cut-closure.md` como fechamento humano do recorte e `tools/archive/close_governed_benchmark_execution_cut.py` como fechador regeneravel;
- a Sprint 4 do `v2-native-memory-scope-hardening-cut` foi concluida com fechamento formal regeneravel em `docs/implementation/v2-native-memory-scope-hardening-cut-closure.md`;
- o recorte estrutural `v2-repository-hygiene-and-tools-review-cut` foi concluido com limpeza segura da superficie ativa de `docs/` e `tools/`;
- a Sprint 1 desse corte foi concluida com inventario regeneravel em `docs/implementation/v2-repository-hygiene-inventory.md`;
- a Sprint 2 desse corte foi concluida com decisao regeneravel de classificacao dos docs ativos em `docs/implementation/v2-repository-hygiene-doc-decisions.md`;
- a Sprint 3 desse corte foi concluida com decisao regeneravel de classificacao dos entrypoints da raiz de `tools/` em `docs/implementation/v2-repository-hygiene-tool-decisions.md`;
- a Sprint 4 desse corte foi concluida com migracao dos `archive candidates` e fechamento formal em `docs/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md`;
- a proxima frente imediata passa a ser a selecao disciplinada do proximo recorte funcional, sem reabrir ruido estrutural.
- a camada de revisao profunda de repositorio para tecnologias externas foi formalizada em `docs/architecture/technology-repository-review-framework.md`, com primeira aplicacao em `docs/architecture/mem0-repository-review.md`; ela apoia decisao arquitetural, mas nao altera a prioridade funcional do backlog.
