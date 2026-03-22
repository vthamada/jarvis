# HANDOFF

## Metadata

- Atualizado em: 2026-03-22
- Branch: `main`
- Commit de referência: `ac5d4d4`
- Artefato canônico do projeto: `documento_mestre_jarvis.md`
- Estado do projeto: `v1` encerrado e congelado para uso controlado; `pós-v1` aberto de forma disciplinada

## Meta atual

Abrir o `pós-v1` com foco total em `continuidade profunda entre missões`, sem reabrir o baseline do `v1`, usando estudo externo curto apenas como apoio dirigido a essa trilha.

Sistema oficial de planejamento desta fase:

- `HANDOFF.md` como retomada tático-operacional;
- `docs/roadmap/programa-ate-v3.md` como direção do programa até `v3`;
- `docs/implementation/post-v1-sprint-cycle.md` como execução oficial das próximas `6` sprints.

Estado do ciclo rolante:

- Sprint 1 concluída;
- Sprint 2 é a próxima frente ativa.

## Decisões fechadas

Não rediscutir sem evidência forte ou mudança explícita de direção:

- o JARVIS é um sistema unificado, não um chatbot simples;
- o núcleo continua próprio e soberano na relação com o usuário;
- especialistas são subordinados ao núcleo, não competidores de identidade;
- `Python` continua como linguagem principal;
- `PostgreSQL` é o backend operacional oficial de memória;
- `sqlite` continua apenas como fallback local;
- `LangSmith` continua complementar; a trilha local persistida segue como fonte primária de auditoria;
- `LangGraph` continua como direção arquitetural forte e fluxo opcional, não como runtime principal já absorvido;
- referências externas passam a ser avaliadas em dois eixos: posicionamento na stack e função arquitetural por camada;
- o Documento-Mestre continua sendo o único artefato canônico de visão de produto.

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
- `observability-service` com trilha persistida, auditoria de fluxo e espelhamento agentic complementar;
- `evolution-lab` persistindo proposals e decisões `sandbox-only`;
- `tools/validate_v1.py`, `tools/go_live_internal_checklist.py`, `tools/run_internal_pilot.py`, `tools/compare_orchestrator_paths.py` e `tools/evolution_from_pilot.py` operacionais;
- estudo tecnológico consolidado em `docs/architecture/technology-study.md`;
- sistema documental em duas camadas ativas para programa e sprint cycle.

### Baseline materializado

Capacidades concretas já presentes no repositório:

- `orchestrator-service` coordenando o fluxo ponta a ponta do núcleo;
- `memory-service` com persistência útil, recuperação contextual e continuidade relacionada inicial;
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
- Documento-Mestre ampliado com referências arquiteturais oficiais por função.

## O que ainda falta

Pendências principais desta fase:

- executar a Sprint 2 para recuperar e rankear continuidade relacionada de forma mais previsível;
- executar as Sprints 3 a 6 do ciclo rolante;
- consolidar estudo externo curto sem bloquear a implementação principal;
- decidir, ao final do ciclo, o que sobe para `v1.5` e o que fica para `v2`.

## Próximos passos imediatos

Ordem recomendada:

1. executar a Sprint 2;
2. executar a Sprint 3;
3. rodar estudo externo curto em paralelo;
4. classificar cada achado como `absorver depois`, `usar como referência` ou `rejeitar`;
5. fechar o corte entre `v1.5` e `v2` ao fim do ciclo.

## Riscos e bloqueios

- o `pós-v1` não deve reabrir o baseline do `v1` sem necessidade real;
- `pgvector`, memória semântica profunda, web, voz e especialistas amplos continuam fora do caminho crítico do ciclo atual;
- o fluxo experimental de `LangGraph` continua opcional e depende do extra `.[langgraph]`;
- o maior risco atual não é estabilidade local; é profundidade cognitiva real de continuidade entre missões.

## Arquivos relevantes

- `documento_mestre_jarvis.md`
- `README.md`
- `HANDOFF.md`
- `CHANGELOG.md`
- `docs/roadmap/programa-ate-v3.md`
- `docs/implementation/post-v1-sprint-cycle.md`
- `docs/architecture/technology-study.md`
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
4. `docs/implementation/post-v1-sprint-cycle.md`
5. `docs/architecture/technology-study.md`
