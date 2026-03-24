# HANDOFF

## Metadata

- Atualizado em: 2026-03-23
- Branch: `main`
- Commit de referência: `5ec3744`
- Artefato canônico do projeto: `documento_mestre_jarvis.md`
- Estado do projeto: `v1` encerrado e congelado para uso controlado; primeiro ciclo do `pós-v1` encerrado; primeiro ciclo do `v1.5` encerrado; primeiro corte do `v2` encerrado; ciclo de alinhamento do `v2` aberto

## Meta atual

Fechar o primeiro corte do `v2` e abrir o ciclo de alinhamento do runtime ao Documento-Mestre, com foco em `domínios`, `memórias`, `mentes`, identidade auditável e gates por eixo.

Sistema oficial de planejamento desta fase:

- `HANDOFF.md` como retomada tático-operacional;
- `docs/roadmap/programa-ate-v3.md` como direção do programa até `v3`;
- `docs/implementation/v2-cycle-closure.md` como fechamento formal do primeiro corte do `v2`;
- `docs/implementation/v2-alignment-cycle.md` como execução oficial do próximo ciclo;
- `docs/documentation/matriz-de-aderencia-mestre.md` como ponte entre visão canônica e backlog real.

Leitura prioritária de aderência neste momento:

- eixo crítico mais distante do mestre: `domínios`, porque o mapa canônico já existe no registry, mas ainda não governa todo o runtime;
- eixo operacional mais urgente do ciclo: `memórias`, porque o registry formal já existe, mas ainda não virou política completa por classe;
- eixo estrutural seguinte: `mentes`, agora com registry canônico aberto, mas ainda pouco soberano na arbitragem.

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
- Sprint 1 do `v2-alignment-cycle` é a próxima frente ativa.

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

- a regra de nomes do sistema deve privilegiar nomes profissionais, limpos,
  robustos e duráveis;
- artefatos permanentes do sistema não devem carregar `v1`, `v2`, `poc`,
  `draft`, `temp` ou rótulos equivalentes no nome técnico principal;
- fase, maturidade e modo de execução devem ficar em metadata, docs vivos ou
  no conteúdo do artefato;
- quando um artefato transitório virar parte estável do sistema, ele deve ser
  renomeado para forma neutra na próxima intervenção útil.

Regra curta de promoção tecnológica nesta fase:

- nenhuma tecnologia externa atravessa direto para o núcleo;
- primeiro ela precisa responder a uma lacuna concreta do ciclo ativo;
- depois precisa ser classificada como `absorver depois`, `usar como referência` ou `rejeitar`;
- só então pode virar fluxo experimental, complemento controlado ou candidata a baseline de fase futura.

Responsabilidade prática nesta fase:

- o agente ativo conduz a análise técnica e produz a recomendação;
- a promoção só vale quando houver evidência e alinhamento com os artefatos oficiais do ciclo;
- nenhuma promoção tecnológica reabre o baseline do `v1` por conveniência.

## Estado atual do repositório

Hoje o repositório contém:

- baseline integrado entre orquestração, memória, governança, conhecimento, observabilidade e operação;
- `jarvis-console` como interface textual mínima do baseline;
- `memory-service` com histórico episódico, resumo contextual, estado mínimo de missão e continuidade relacionada inicial;
- `shared/memory_registry.py` como registry formal das 11 classes de memória, já conectado ao recovery default e ao compartilhamento com especialistas;
- `shared/mind_registry.py` como registry formal das 24 mentes canônicas, com suporte preferencial inicial no `cognitive-engine`;
- `observability-service` com trilha persistida, auditoria de fluxo e espelhamento agentic complementar;
- `evolution-lab` persistindo proposals e decisões `sandbox-only`;
- `tools/validate_baseline.py`, `tools/go_live_internal_checklist.py`, `tools/run_internal_pilot.py`, `tools/compare_orchestrator_paths.py`, `tools/evolution_from_pilot.py` e `tools/close_stateful_runtime_cycle.py` operacionais;
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
- Sprint 4 do `v2` concluída, com registry inicial de domínios do ciclo, rota canônica `software_development -> especialista_software_subordinado` e execução explícita em `shadow mode`;
- Documento-Mestre ampliado com referências arquiteturais oficiais por função.

## O que ainda falta

Pendências principais desta fase:

- executar a Sprint 1 do `v2-alignment-cycle`;
- transformar o registry de `domínios` em fonte soberana de roteamento do runtime;
- promover o registry de `memórias` para política operacional por classe;
- tornar a arbitragem entre `mentes` menos implícita e mais soberana;
- preservar a mediação do núcleo como única política de escrita da memória compartilhada;
- usar os sinais de aderência recém-abertos como critério explícito de promoção, ajuste ou contenção;
- consolidar estudo externo curto sem bloquear a implementação principal.

Regra de estudo externo no `v2`:

- entra apenas o estudo que ajude diretamente contratos de especialistas, handoffs internos, memória relacional ou convocação governada;
- `OpenHands` e `PydanticAI` são as referências mais diretamente ligadas ao corte imediato;
- `Hermes Agent`, `Graphiti`, `Zep`, `LangGraph` e `OpenAI Agents SDK` entram apenas como apoio dirigido ao problema do ciclo;
- `computer use` amplo, voz oficial, memória profunda com `pgvector` como base canônica e assistente operacional amplo continuam fora do foco imediato.

## Próximos passos imediatos

Ordem recomendada:

1. executar a Sprint 1 do `v2-alignment-cycle`;
2. tornar `domain_registry.json` a fonte primária de roteamento e ativação;
3. usar `domain_alignment_status`, `memory_alignment_status` e `specialist_sovereignty_status` como gates da próxima rodada;
4. usar a matriz para priorizar `domínios`, `memórias` e `mentes` nessa ordem;
5. rodar estudo externo curto em paralelo;
6. classificar cada achado como `absorver depois`, `usar como referência` ou `rejeitar`;

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
- `docs/implementation/post-v1-cycle-closure.md`
- `docs/implementation/v1-5-cycle-closure.md`
- `docs/implementation/v2-cycle-closure.md`
- `docs/implementation/v2-alignment-cycle.md`
- `docs/architecture/technology-study.md`
- `docs/documentation/matriz-de-aderencia-mestre.md`
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
4. `docs/implementation/v1-5-cycle-closure.md`
5. `docs/implementation/v2-cycle-closure.md`
6. `docs/implementation/v2-alignment-cycle.md`
7. `docs/architecture/technology-study.md`
