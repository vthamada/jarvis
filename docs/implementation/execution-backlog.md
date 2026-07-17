# Execution Backlog

## 1. Objetivo

Este documento e a fila micro soberana de execucao do corte ativo.

Ele existe para:

- transformar o backlog micro implicito em fila executavel;
- sustentar fluxo continuo de implementacao com lotes autonomos curtos;
- reduzir interrupcao humana em execucao tecnica dentro da direcao ja fechada;
- manter codigo, testes, observabilidade, docs vivas e gates na mesma disciplina operacional.

Hierarquia correta:

- `documento_mestre_jarvis.md` continua como visao canonica;
- `docs/documentation/matriz-de-aderencia-mestre.md` continua como ponte formal de aderencia;
- `docs/roadmap/programa-ate-v3.md` continua como programa macro;
- `docs/implementation/unified-gap-and-absorption-backlog.md` agora consolida o backlog macro do que ainda falta, incluindo gaps do sistema, traducao tecnologica, superficies, evolucao e pesquisa;
- `HANDOFF.md` continua como retomada tatico-operacional;
- `docs/implementation/v2-adherence-snapshot.md` continua como leitura viva do baseline;
- este arquivo e apenas a fila micro ativa do corte corrente.

Regra central:

- este backlog nao substitui a direcao macro;
- ele organiza a execucao do proximo trabalho pequeno e fechavel;
- quando a fila ficar sem item `ready`, a repriorizacao deve partir de `docs/implementation/unified-gap-and-absorption-backlog.md`;
- nenhuma mudanca de direcao entra aqui sem decisao explicita do operador.

---

## 2. Politica de fluxo

Modelo adotado:

- `Kanban` leve;
- `single source of truth` para backlog micro;
- lotes autonomos curtos;
- fechamento orientado por gate, nao por calendario.

Status validos:

| Status | Uso correto |
| --- | --- |
| `ready` | item pronto para ser puxado sem ambiguidade relevante |
| `in_progress` | item ativo da rodada atual |
| `blocked` | item valido, mas impedido por dependencia ou decisao externa |
| `done` | item fechado com gate minimo satisfeito |
| `deferred` | item reconhecido, mas fora do foco da rodada atual |

Politicas obrigatorias:

- `WIP limit`: no maximo `1` item em `in_progress`;
- ordem de puxada: impacto arquitetural, reducao de heuristica local, evidencia/gates, depois refinamentos;
- cada item precisa ser pequeno, reversivel e fechavel em uma rodada;
- toda implementacao nova relevante deve nascer com bateria de testes que cubra
  o slice local e o fluxo ponta a ponta afetado;
- docs vivas entram na fila apenas quando refletem mudanca real de runtime, gate ou baseline;
- nenhuma tarefa vaga entra em `ready`.

Politica de modelo recomendado:

- novos itens com recomendacao explicita de modelo devem, por padrao, usar apenas `gpt-5.4`, `gpt-5.3-codex` ou `gpt-5.4-mini`, salvo repriorizacao tecnica deliberada;
- `gpt-5.4` e o modelo preferencial para mudancas de alta ambiguidade arquitetural, contratos soberanos, memoria, governanca e decisoes sensiveis de nucleo;
- `gpt-5.3-codex` e o modelo preferencial para implementacao agentic pesada no repositorio, mudancas multi-arquivo, ciclos de teste/correcao e trabalho coding-first;
- `gpt-5.4-mini` e o modelo preferencial para docs, gates, sincronizacao documental, propagacoes mecanicas e tarefas de menor risco/menor custo;
- o `modo_de_raciocinio_recomendado` continua mandatorio porque o modelo sozinho nao substitui calibracao de esforco.

### Definition of Ready

Um item so entra em `ready` quando:

- tem `micro_objetivo` fechado;
- aponta comportamento, contrato, gate ou artefato especifico;
- tem `criterio_de_aceite`;
- tem `gate_minimo`;
- explicita a estrategia de validacao automatizada do slice, incluindo cobertura
  ponta a ponta do fluxo afetado ou justificativa de fase quando isso ainda nao
  for viavel;
- nao depende de decisao macro ainda aberta.

### Definition of Done

Um item so entra em `done` quando:

- implementacao principal foi concluida;
- validacao minima definida no item passou;
- a bateria de testes do comportamento novo cobre o slice local e o caminho
  ponta a ponta afetado, ou a excecao de fase ficou registrada explicitamente;
- docs vivas foram sincronizadas se a mudanca alterou estado real;
- o impacto no baseline foi registrado em uma linha curta.

---

## 3. Politica de execucao autonoma

O agente ativo pode:

- puxar sozinho qualquer item `ready` com `depende_do_operador = nao`;
- reordenar itens `ready` de mesma prioridade quando isso reduzir bloqueio tecnico sem mudar a direcao macro;
- abrir subtarefa documental derivada quando ela for necessaria para refletir mudanca real de runtime, gate ou baseline;
- fechar lote pequeno com gate minimo e sincronizacao documental correspondente.

O agente ativo nao pode sem aprovacao:

- criar nova frente macro;
- mudar ontologia de `dominios`, `memorias` ou `mentes`;
- promover tecnologia externa a baseline central;
- reabrir baseline encerrado por conveniencia local;
- trocar o papel soberano dos artefatos oficiais do projeto.

Escalar ao operador quando:

- a proxima acao muda prioridade macro;
- o item exige escolha de produto, ontologia ou superficie principal;
- houver duas solucoes tecnicas plausiveis com tradeoff arquitetural relevante;
- o bloqueio nao puder ser resolvido por exploracao local ou ajuste tecnico pequeno.

---

## 4. Fila ativa

### MB-000

- `id`: `MB-000`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: abrir backlog micro soberano dedicado e tirar a fila de execucao do estado implicito.
- `justificativa_arquitetural`: o runtime ja tem direcao macro forte, mas a execucao micro ainda estava dispersa entre `HANDOFF`, snapshot e leitura local do codigo.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: nenhuma
- `criterio_de_aceite`: existe uma fila micro ativa, com politicas explicitas, WIP limit, itens reais do baseline e hierarquia documental sem concorrencia de papeis.
- `gate_minimo`: `python tools/check_mojibake.py ...` nos docs tocados e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: backlog micro soberano aberto; `HANDOFF` e snapshot passam a apontar a fila em vez de carregar backlog implicito.

### MB-001

- `id`: `MB-001`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade`
- `workflow_profile_afetado`: `strategic_direction_workflow`, `structured_analysis_workflow`, `decision_risk_workflow`, `software_change_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: propagar `workflow_profile_status` para relatorios comparativos e artefatos de avaliacao, nao so para auditoria local.
- `justificativa_arquitetural`: hoje o runtime ja diferencia `workflow_trace_status` de `workflow_profile_status`, mas a leitura comparativa ainda nao captura essa distincao de forma soberana.
- `arquivos/servicos_principais`: `tools/compare_orchestrator_paths.py`, `tools/internal_pilot_report.py`, `services/observability-service`
- `dependencias`: nenhuma
- `criterio_de_aceite`: artefatos comparativos passam a registrar os dois status, sem confundir falha estrutural com `maturation_recommended`.
- `gate_minimo`: `pytest` direcionado dos tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `workflow_profile_status` agora atravessa `internal_pilot_report`, `compare_orchestrator_paths` e o payload serializado de comparacao, deixando de existir apenas na auditoria local.

### MB-002

- `id`: `MB-002`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade`
- `workflow_profile_afetado`: `strategic_direction_workflow`, `structured_analysis_workflow`, `decision_risk_workflow`, `software_change_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: endurecer `compare_orchestrator_paths.py` e `internal_pilot_report.py` para separar `baseline_saudavel` de `maturation_recommended` por workflow.
- `justificativa_arquitetural`: sem essa distincao, o backlog funcional continua misturando saude de baseline com maturacao recomendada.
- `arquivos/servicos_principais`: `tools/compare_orchestrator_paths.py`, `tools/internal_pilot_report.py`, `tools/evolution_from_pilot.py`
- `dependencias`: `MB-001`
- `criterio_de_aceite`: relatorios e comparacoes exibem classificacao por workflow sem rebaixar baseline saudavel a falha estrutural.
- `gate_minimo`: `pytest` direcionado dos tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `compare_orchestrator_paths` e `internal_pilot_report` agora expõem `baseline_saudavel`, `maturation_recommended` e `attention_required` como leitura explicita por workflow, sem mudar a semantica estrutural do `axis_gate_status`.

### MB-003

- `id`: `MB-003`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `memorias`
- `workflow_profile_afetado`: `strategic_direction_workflow`, `structured_analysis_workflow`, `decision_risk_workflow`, `software_change_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: consolidar `semantic` e `procedural` nos relatorios/evals como sinal causal, nao apenas presenca de contexto.
- `justificativa_arquitetural`: o runtime ja faz memoria guiada alterar plano e sintese; a evidencia comparativa ainda precisa mostrar esse efeito de forma legivel e repetivel.
- `arquivos/servicos_principais`: `tools/compare_orchestrator_paths.py`, `tools/internal_pilot_report.py`, `services/observability-service`
- `dependencias`: `MB-001`, `MB-002`
- `criterio_de_aceite`: os artefatos de comparacao distinguem memoria causal de memoria apenas anexada, sem abrir heuristica fora dos registries soberanos.
- `gate_minimo`: `pytest` direcionado dos tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `internal_pilot_report`, `compare_orchestrator_paths` e `observability-service` agora distinguem memoria causal (`causal_guidance`) de memoria apenas anexada (`attached_only`) e publicam foco semantico, hint procedural e especialistas ligados a esse efeito.

### MB-004

- `id`: `MB-004`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `mentes`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: tornar `dominant_tension` e a malha `mente -> dominio -> especialista` mais explicitos nos artefatos comparativos do baseline antes de abrir recomposicao cognitiva de runtime.
- `justificativa_arquitetural`: a cadeia ja esta menos implicita no runtime, mas ainda precisa aparecer como evidencia operacional, nao so leitura heroica de codigo.
- `arquivos/servicos_principais`: `tools/compare_orchestrator_paths.py`, `tools/internal_pilot_report.py`, `services/observability-service`
- `dependencias`: `MB-001`, `MB-002`
- `criterio_de_aceite`: os relatorios passam a mostrar tensao dominante, dominio dominante e coerencia de especialista como parte da leitura de maturacao do baseline.
- `gate_minimo`: `pytest` direcionado dos tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: os artefatos comparativos agora carregam `dominant_tension`, `primary_domain_driver` e `mind_domain_specialist_status`, tornando explicita a malha `mente -> dominio -> especialista` na leitura do baseline.

### MB-005

- `id`: `MB-005`
- `prioridade`: `P2`
- `status`: `done`
- `eixo_do_mestre`: `mentes`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: introduzir recomposicao cognitiva observavel no runtime quando houver impasse real durante a execucao.
- `justificativa_arquitetural`: isso pertence ao nucleo da excelencia, mas ainda depende de termos primeiro os relatorios e gates de baseline mais maduros.
- `arquivos/servicos_principais`: `engines/cognitive-engine`, `services/orchestrator-service`, `services/observability-service`
- `dependencias`: `MB-001`, `MB-002`, `MB-003`, `MB-004`
- `criterio_de_aceite`: o runtime emite recomposicao cognitiva rastreavel apenas quando houver evidencia de impasse e sem quebrar a soberania do nucleo.
- `gate_minimo`: `pytest` direcionado, `ruff` direcionado, `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `cognitive-engine` agora aplica recomposicao observavel em impasses reais de rota especializada, `orchestrator-service` publica esse sinal e `observability-service` passa a auditar a coerencia dessa recomposicao ao longo do fluxo.

### MB-006

- `id`: `MB-006`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade`
- `workflow_profile_afetado`: `strategic_direction_workflow`, `structured_analysis_workflow`, `decision_risk_workflow`, `software_change_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: promover `workflow_profile_status`, `memory_causality_status`, `mind_domain_specialist_status` e recomposicao cognitiva para `evolution_from_pilot` e `evolution-lab`.
- `justificativa_arquitetural`: os sinais novos ja existiam no baseline local e nos artefatos comparativos, mas ainda nao influenciavam `proposal generation` nem comparacao `sandbox-only` do laboratorio evolutivo.
- `arquivos/servicos_principais`: `tools/evolution_from_pilot.py`, `evolution/evolution-lab/src/evolution_lab/service.py`
- `dependencias`: `MB-001`, `MB-002`, `MB-003`, `MB-004`, `MB-005`
- `criterio_de_aceite`: o `evolution-lab` passa a carregar esses sinais como `source_signals`, metricas de comparacao e hints de risco, e `evolution_from_pilot` deixa de ignorar traces saudaveis que ainda estao apenas em `maturation_recommended` ou `attached_only`.
- `gate_minimo`: `pytest` direcionado do `evolution-lab`, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `evolution_from_pilot` e `evolution-lab` agora tratam maturacao de workflow, causalidade de memoria, coerencia `mente -> dominio -> especialista` e recomposicao cognitiva como sinais comparativos de refinamento, nao apenas como telemetria lateral.

### MB-007

- `id`: `MB-007`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: tornar esses sinais novos parte da evidencia regeneravel de fechamento de ciclo e de cut, e nao so do piloto comparativo.
- `justificativa_arquitetural`: sem isso, os fechadores continuam resumindo apenas scores agregados antigos e perdem a leitura mais fina que o baseline ja materializou.
- `arquivos/servicos_principais`: `tools/archive/close_alignment_cycle.py`, `tools/archive/close_sovereign_alignment_cut.py`
- `dependencias`: `MB-006`
- `criterio_de_aceite`: os fechadores passam a expor decisoes e taxas de `workflow_profile`, `memory_causality` e `mind_domain_specialist` em `payload` e `markdown` regeneravel.
- `gate_minimo`: `pytest` direcionado dos fechadores, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: os fechadores historicos do `v2` agora carregam evidencia regeneravel dos sinais novos, aproximando comparacao `sandbox`, snapshot e closure docs da mesma gramatica de maturacao.

### MB-008

- `id`: `MB-008`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `strategic_direction_workflow`, `structured_analysis_workflow`, `decision_risk_workflow`, `software_change_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: promover `workflow_profile_status`, `memory_causality_status`, `mind_domain_specialist_status` e recomposicao cognitiva a criterio formal do `release gate`.
- `justificativa_arquitetural`: os sinais novos ja existem em runtime, comparadores, `evolution-lab` e fechadores, mas o `release gate` ainda nao os trata como identidade formal do baseline soberano.
- `arquivos/servicos_principais`: `tools/engineering_gate.py`, `tools/verify_axis_artifacts.py`, `tools/verify_active_cut_baseline.py`, novo verificador dedicado de sinais de release
- `dependencias`: `MB-006`, `MB-007`
- `criterio_de_aceite`: `engineering_gate --mode release` passa a rodar uma verificacao dedicada da gramatica de sinais novos e falha se ela deixar de existir nos artefatos de release.
- `gate_minimo`: `pytest` direcionado dos verificadores/gate, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `engineering_gate --mode release` agora roda `tools/verify_release_signal_baseline.py` e trata `workflow_profile_status`, `memory_causality_status`, `mind_domain_specialist_status` e recomposicao cognitiva como gramatica formal de release.

### MB-009

- `id`: `MB-009`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade`
- `workflow_profile_afetado`: `strategic_direction_workflow`, `structured_analysis_workflow`, `decision_risk_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: ampliar os cenarios de piloto para acionar deliberadamente memoria causal e recomposicao cognitiva, nao apenas por coincidencia do baseline.
- `justificativa_arquitetural`: sem cenarios deliberados, os sinais novos podem continuar aparecendo como telemetria esporadica e enfraquecem a evidencia comparativa da fase.
- `arquivos/servicos_principais`: `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`
- `dependencias`: `MB-008`
- `criterio_de_aceite`: o piloto passa a incluir cenarios especificos para memoria `semantic/procedural` causal e para `specialist_route_impasse`, com cobertura de comparacao e relatorio.
- `gate_minimo`: `pytest` direcionado dos tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: o piloto agora inclui cenarios deliberados para memoria causal (`guided_memory_followup`) e recomposicao cognitiva por `specialist_route_impasse`, com cobertura em relatorio e comparacao.

### MB-010

- `id`: `MB-010`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: tornar os comparadores menos implicitos para os sinais novos, marcando drift real de `workflow_profile`, memoria causal, tensao dominante, dominio primario e recomposicao.
- `justificativa_arquitetural`: hoje parte desses sinais ja aparece no payload e no texto, mas ainda nao participa da deteccao formal de divergencia entre baseline e candidata.
- `arquivos/servicos_principais`: `tools/compare_orchestrator_paths.py`, `tests/unit/test_compare_orchestrator_paths.py`
- `dependencias`: `MB-009`
- `criterio_de_aceite`: a comparacao entre caminhos passa a detectar mismatch explicito dos sinais novos quando eles divergirem materialmente.
- `gate_minimo`: `pytest` direcionado do comparador, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `compare_orchestrator_paths` agora trata drift de `workflow_profile_status`, `memory_causality_status`, `dominant_tension`, `primary_domain_driver`, `mind_domain_specialist_status` e recomposicao cognitiva como divergencia formal entre baseline e candidata.

### MB-011

- `id`: `MB-011`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `mentes`
- `workflow_profile_afetado`: `strategic_direction_workflow`, `structured_analysis_workflow`, `decision_risk_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: deixar os consumidores finais do runtime mais declarativos sobre `dominant_tension`, `primary_domain_driver`, recomposicao cognitiva e guidance por `workflow_profile`.
- `justificativa_arquitetural`: o baseline ja emite esses sinais, mas parte da leitura final ainda depende de inferencia do operador a partir de payloads e rationale internos.
- `arquivos/servicos_principais`: `engines/planning-engine/src/planning_engine/engine.py`, `engines/synthesis-engine/src/synthesis_engine/engine.py`, `services/orchestrator-service/src/orchestrator_service/service.py`
- `dependencias`: `MB-009`, `MB-010`
- `criterio_de_aceite`: planejamento e sintese passam a explicitar melhor a ancora cognitiva e a tensao dominante quando a rota ativa e o workflow justificarem esse nivel de declaratividade.
- `gate_minimo`: `pytest` direcionado dos engines/servico tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `planning-engine`, `synthesis-engine` e `response_synthesized` agora tornam `dominant_tension`, `primary_domain_driver`, guidance de workflow e recomposicao cognitiva mais declarativos no comportamento final do runtime.

### MB-012

- `id`: `MB-012`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar o lote micro atual, sincronizando snapshot, handoff, changelog e backlog com o novo baseline de release.
- `justificativa_arquitetural`: sem esse fechamento, o lote vira implementacao local sem consolidacao soberana da fase.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-008`, `MB-009`, `MB-010`, `MB-011`
- `criterio_de_aceite`: o lote termina sem item `ready`, com os docs vivos refletindo o novo estado do baseline e gate minimo validado.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: backlog, handoff, snapshot e changelog voltam a convergir para um baseline sem item micro aberto, agora com gramatica de release e sinais cognitivos mais declarativos.

### MB-013

- `id`: `MB-013`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `operational_readiness_workflow`, `software_change_workflow`, `strategic_direction_workflow`
- `micro_objetivo`: endurecer `verify_active_cut_baseline.py` para cobrar cobertura minima real das rotas promovidas e dos sinais novos no piloto focado.
- `justificativa_arquitetural`: o baseline ativo ainda validava contratos de rota e benchmark, mas nao exigia evidencia minima de memoria causal, recomposicao cognitiva e cobertura por workflow profile nas rotas promovidas.
- `arquivos/servicos_principais`: `tools/verify_active_cut_baseline.py`, `tests/unit/test_verify_active_cut_baseline.py`
- `dependencias`: `MB-012`
- `criterio_de_aceite`: o verificador de baseline ativo passa a falhar se o piloto focado perder cobertura das rotas promovidas, dos workflow profiles promovidos ou dos cenarios deliberados de memoria causal e recomposicao cognitiva.
- `gate_minimo`: `pytest` direcionado do verificador, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `verify_active_cut_baseline.py` agora combina contratos estaticos do registry com evidencia minima real do piloto focado para decidir `baseline_release_ready`.

### MB-014

- `id`: `MB-014`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `operational_readiness_workflow`, `software_change_workflow`, `strategic_direction_workflow`
- `micro_objetivo`: explicitar no piloto uma malha de cobertura por rota promovida, workflow profile e sinais deliberados de memoria causal e recomposicao cognitiva.
- `justificativa_arquitetural`: sem cenarios explicitamente mapeados por rota/workflow, o baseline dependia de prompts acidentais e de inferencia local para saber se o piloto cobria o que o runtime promoveu.
- `arquivos/servicos_principais`: `tools/internal_pilot_support.py`, `tests/unit/test_internal_pilot_support.py`
- `dependencias`: `MB-013`
- `criterio_de_aceite`: os cenarios canonicos do piloto passam a declarar `expected_route`, `expected_workflow_profile` e `coverage_tags`, cobrindo todas as rotas promovidas e os sinais deliberados do baseline.
- `gate_minimo`: `pytest` direcionado do piloto, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `default_pilot_scenarios()` agora mapeia cobertura explicita para as seis rotas promovidas e para os sinais de `memory_causality` e `cognitive_recomposition`.

### MB-015

- `id`: `MB-015`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: tornar o artefato de baseline ativo mais legivel sobre cobertura de piloto, workflow profiles promovidos e sinais de maturacao exigidos para release.
- `justificativa_arquitetural`: endurecer o gate sem melhorar a leitura do payload e do markdown manteria a cobertura escondida em logica interna e tornaria a manutencao futura mais opaca.
- `arquivos/servicos_principais`: `tools/verify_active_cut_baseline.py`, `tests/unit/test_verify_active_cut_baseline.py`
- `dependencias`: `MB-013`, `MB-014`
- `criterio_de_aceite`: o payload, o texto e o markdown do baseline ativo passam a expor cobertura de piloto, match de workflow e readiness dos sinais deliberados.
- `gate_minimo`: `pytest` direcionado do verificador, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: o baseline ativo agora publica cobertura de piloto e readiness de sinais deliberados em vez de resumir apenas contratos de rota e benchmark.

### MB-016

- `id`: `MB-016`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar o lote micro de endurecimento do baseline ativo, sincronizando backlog, handoff, snapshot e changelog.
- `justificativa_arquitetural`: sem esse fechamento, a nova cobertura por rota/workflow e sinais deliberados ficaria como implementacao local sem consolidacao documental da fase.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-013`, `MB-014`, `MB-015`
- `criterio_de_aceite`: o lote termina sem item `ready`, com docs vivos refletindo a nova cobertura do baseline ativo e gate minimo validado.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: backlog, handoff, snapshot e changelog voltam a convergir para um baseline ativo que combina contratos promovidos com cobertura deliberada de piloto.

### MB-017

- `id`: `MB-017`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `operational_readiness_workflow`, `software_change_workflow`, `strategic_direction_workflow`
- `micro_objetivo`: promover a cobertura deliberada do piloto para o fechador regeneravel do `v2-domain-consumers-and-workflows-cut`.
- `justificativa_arquitetural`: o gate e o baseline ativo ja conheciam a nova cobertura, mas o fechamento regeneravel do corte ainda resumia apenas contratos e benchmark governance, perdendo a leitura minima por rota e workflow.
- `arquivos/servicos_principais`: `tools/archive/close_domain_consumers_and_workflows_cut.py`, `tests/unit/test_close_domain_consumers_and_workflows_cut.py`
- `dependencias`: `MB-016`
- `criterio_de_aceite`: o fechador passa a expor coverage de piloto, match de workflow e readiness dos sinais deliberados no payload e no markdown.
- `gate_minimo`: `pytest` direcionado do fechador, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: o fechamento regeneravel do corte agora carrega cobertura deliberada de piloto como parte da evidencia minima do `baseline_release_ready`.

### MB-018

- `id`: `MB-018`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: atualizar a leitura executiva para refletir que o baseline do corte combina contratos promovidos com cobertura deliberada do piloto.
- `justificativa_arquitetural`: sem leitura executiva coerente, a nova evidencia continua presa ao verificador tecnico e ao fechador regeneravel, em vez de orientar a narrativa oficial do estado atual.
- `arquivos/servicos_principais`: `docs/executive/master-summary.md`, `docs/archive/implementation/v2-domain-consumers-and-workflows-cut-closure.md`
- `dependencias`: `MB-017`
- `criterio_de_aceite`: os documentos executivos e de fechamento passam a mencionar explicitamente cobertura das rotas promovidas, dos workflow profiles e dos sinais deliberados do piloto.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: a leitura executiva oficial do corte deixa de tratar a cobertura deliberada do piloto como detalhe técnico implícito.

### MB-019

- `id`: `MB-019`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar o lote micro de promovacao da cobertura deliberada para fechamento e leitura executiva.
- `justificativa_arquitetural`: sem o fechamento formal da rodada, o baseline ganha nova leitura regeneravel sem consolidacao no backlog, handoff, snapshot e changelog.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-017`, `MB-018`
- `criterio_de_aceite`: o lote termina sem item `ready`, com docs vivos refletindo o novo estado do corte e gate minimo validado.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: backlog, handoff, snapshot e changelog voltam a convergir para um baseline que agora tambem projeta a cobertura deliberada do piloto na leitura executiva.

### MB-020

- `id`: `MB-020`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `mentes`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `operational_readiness_workflow`, `software_change_workflow`, `strategic_direction_workflow`
- `micro_objetivo`: transformar `dominant_tension` e alinhamento `mente -> dominio -> especialista` em cobertura deliberada do baseline ativo, e nao apenas sinal incidental do piloto.
- `justificativa_arquitetural`: o runtime e os comparadores ja expunham esses sinais, mas o verificador do baseline ainda nao exigia evidencia minima de que eles continuavam materializados nas rotas promovidas.
- `arquivos/servicos_principais`: `tools/verify_active_cut_baseline.py`, `tools/internal_pilot_support.py`, `tests/unit/test_verify_active_cut_baseline.py`, `tests/unit/test_internal_pilot_support.py`
- `dependencias`: `MB-019`
- `criterio_de_aceite`: o baseline ativo passa a falhar se o piloto focado perder o cenario deliberado de `dominant_tension` ou de alinhamento `mind_domain_specialist`, e os cenarios canonicos declaram essa cobertura via `coverage_tags`.
- `gate_minimo`: `pytest` direcionado dos verificadores/piloto, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `verify_active_cut_baseline.py` agora exige cobertura deliberada de `dominant_tension` e `mind_domain_specialist`, e os cenarios canonicos do piloto passaram a declarar esses sinais de forma explicita.

### MB-021

- `id`: `MB-021`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: promover esses dois sinais novos para o fechador regeneravel e para a leitura executiva do corte.
- `justificativa_arquitetural`: sem isso, o baseline ativo endurece, mas a narrativa regeneravel do corte e a leitura executiva continuam atrasadas em relacao ao que o gate realmente passou a exigir.
- `arquivos/servicos_principais`: `tools/archive/close_domain_consumers_and_workflows_cut.py`, `tests/unit/test_close_domain_consumers_and_workflows_cut.py`, `docs/archive/implementation/v2-domain-consumers-and-workflows-cut-closure.md`, `docs/executive/master-summary.md`
- `dependencias`: `MB-020`
- `criterio_de_aceite`: o fechador e os docs executivos passam a mencionar readiness deliberado de `dominant_tension` e `mind_domain_specialist` como parte da evidencia formal do corte.
- `gate_minimo`: `pytest` direcionado do fechador, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: o fechamento regeneravel do corte e a leitura executiva passam a refletir que o baseline deliberadamente cobre tensao cognitiva e alinhamento `mente -> dominio -> especialista`.

### MB-022

- `id`: `MB-022`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar o lote micro final de robustez do `v2`, sincronizando backlog, handoff, snapshot e changelog.
- `justificativa_arquitetural`: sem fechamento formal, a ultima pendencia real de robustez do `v2` continuaria como implementacao local sem consolidacao soberana do baseline.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-020`, `MB-021`
- `criterio_de_aceite`: o lote termina sem item `ready`, com docs vivos refletindo que `workflow_profile`, memoria causal, recomposicao cognitiva, `dominant_tension` e alinhamento `mente -> dominio -> especialista` agora fazem parte da leitura formal de robustez do `v2`.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode release`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: backlog, handoff, snapshot e changelog convergem para um `v2` sem pendencia tecnica material de robustez dentro do baseline atual.

### MB-023

- `id`: `MB-023`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `governanca`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: formalizar a fase de continuidade/HITL/replay como subfluxo nativo do caminho padrao, alinhando seu fechamento ao caminho opcional de `LangGraph`.
- `justificativa_arquitetural`: a continuidade ja era stateful, mas permanecia espalhada como logica inline no `handle_input`, enquanto apenas o caminho `LangGraph` publicava um fechamento explicito de subfluxo.
- `arquivos/servicos_principais`: `services/orchestrator-service/src/orchestrator_service/service.py`, `services/orchestrator-service/src/orchestrator_service/langgraph_flow.py`, `services/orchestrator-service/tests/test_orchestrator_service.py`, `services/orchestrator-service/tests/test_langgraph_flow.py`
- `dependencias`: `MB-022`
- `criterio_de_aceite`: o caminho padrao passa a encapsular a continuidade em uma fase nativa com evento `continuity_subflow_completed`, e o caminho `LangGraph` reutiliza o mesmo payload soberano de fechamento.
- `gate_minimo`: `pytest` direcionado do `orchestrator-service`, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: a continuidade agora fecha como subfluxo explicito tambem no runtime padrao, com o mesmo tipo de evidencia estrutural ja existente no caminho `LangGraph`.

### MB-024

- `id`: `MB-024`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `governanca`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `operational_readiness_workflow`, `software_change_workflow`, `strategic_direction_workflow`
- `micro_objetivo`: explicitar o lifecycle do subfluxo de especialistas no runtime padrao, com fases observaveis coerentes entre planejamento, governanca, execucao e retorno ao nucleo.
- `justificativa_arquitetural`: o orquestrador ainda concentra demais a malha de handoff especializado, o que dificulta escalar especialistas e missões longas sem carregar `service.py` com logica transversal.
- `arquivos/servicos_principais`: `services/orchestrator-service/src/orchestrator_service/service.py`, `engines/specialist-engine`, `services/observability-service`, testes do `orchestrator-service`
- `dependencias`: `MB-023`
- `criterio_de_aceite`: o caminho padrao passa a emitir um fechamento soberano do subfluxo de especialistas e a distinguir claramente fases de selecao, governanca, execucao e refinamento.
- `gate_minimo`: `pytest` direcionado do `orchestrator-service` e `observability-service`, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: o runtime agora fecha o subfluxo de especialistas com payload soberano e observabilidade dedicada, distinguindo selecao, governanca, execucao, refinamento e `runtime_mode` entre o caminho nativo e o caminho `LangGraph`.

### MB-025

- `id`: `MB-025`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `memorias`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: introduzir um contrato minimo de `mission_runtime_state` para preparar missões assincronas e continuidade longa sem reabrir a ontologia do sistema.
- `justificativa_arquitetural`: a missao ja existe como contexto e continuidade, mas ainda nao aparece como estado operacional explicito e auditavel o suficiente para a fase pre-`v3`.
- `arquivos/servicos_principais`: `services/memory-service`, `shared/contracts`, `services/orchestrator-service`, verificadores do baseline ativo
- `dependencias`: `MB-024`
- `criterio_de_aceite`: o runtime passa a expor um estado minimo de missao ativa/relacionada e readiness para retomada longa sem depender de recomposicao textual de hints.
- `gate_minimo`: `pytest` direcionado, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: o runtime agora declara `mission_runtime_state` para requests com missao ativa, related mission e readiness de retomada, deixando a continuidade longa menos dependente de recomposicao textual de hints.

### MB-026

- `id`: `MB-026`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `operational_readiness_workflow`, `software_change_workflow`, `strategic_direction_workflow`
- `micro_objetivo`: consolidar leitura agregada de hardening pre-`v3` por workflow e por subfluxo, para que continuidade, especialistas e missao longa passem a ser lidos como readiness arquitetural e nao apenas telemetria dispersa.
- `justificativa_arquitetural`: sem essa agregacao, os novos estados formais entram no runtime, mas continuam aparecendo de forma muito localizada para guiar benchmark, fechamento e decisao de transicao para `v3`.
- `arquivos/servicos_principais`: `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`, `tools/verify_active_cut_baseline.py`, `docs/executive/master-summary.md`
- `dependencias`: `MB-025`
- `criterio_de_aceite`: comparadores, baseline ativo e leitura executiva passam a enxergar subfluxos stateful e readiness de missao longa como sinais agregados do lote pre-`v3`.
- `gate_minimo`: `pytest` direcionado dos tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: comparadores, baseline ativo, fechamento regeneravel e leitura executiva agora tratam `specialist_subflow` e `mission_runtime_state` como sinais agregados de hardening arquitetural pre-`v3`, e nao apenas telemetria localizada.

### MB-027

- `id`: `MB-027`
- `prioridade`: `P0`
- `status`: `deferred`
- `eixo_do_mestre`: `governanca`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: introduzir os contratos canonicos minimos de `protective intelligence` para caso, evidencia, cadeia de custodia, achado, hipotese e sinal de risco.
- `justificativa_arquitetural`: o eixo continua valido, mas foi rebaixado porque o programa ainda precisa fechar maturacao do nucleo cognitivo antes de abrir uma vertical nova por contratos e servicos dedicados.
- `arquivos/servicos_principais`: `shared/contracts/__init__.py`, `docs/implementation/pre-v3-protective-intelligence-foundation-cut.md`, `docs/architecture/protective-intelligence-architecture.md`
- `dependencias`: nenhuma
- `criterio_de_aceite`: o repositorio passa a expor contratos compartilhados claros para `case_record`, `evidence_item`, `evidence_chain_entry`, `finding`, `hypothesis` e `risk_signal`, todos subordinados ao nucleo e sem semantica ofensiva.
- `gate_minimo`: `pytest` direcionado de contratos, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `deferred` por repriorizacao macro; sem implementacao iniciada.

### MB-028

- `id`: `MB-028`
- `prioridade`: `P0`
- `status`: `deferred`
- `eixo_do_mestre`: `memorias`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: criar o `evidence-ledger-service` minimo para registrar artefatos com hash, proveniencia e cadeia de custodia.
- `justificativa_arquitetural`: evidencia nao deve ser tratada como memoria mutavel comum, mas o eixo inteiro foi rebaixado ate que metacognicao, memoria causal e lifecycle nativos avancem mais no nucleo.
- `arquivos/servicos_principais`: `services/evidence-ledger-service`, `shared/contracts/__init__.py`, `services/observability-service`
- `dependencias`: `MB-027`
- `criterio_de_aceite`: o sistema consegue registrar evidencias com integridade minima, trilha de custodia e leitura auditavel, ainda sem abrir automacao ofensiva nem toolchain ampla.
- `gate_minimo`: `pytest` direcionado do novo servico, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `deferred` por repriorizacao macro; sem implementacao iniciada.

### MB-029

- `id`: `MB-029`
- `prioridade`: `P1`
- `status`: `deferred`
- `eixo_do_mestre`: `governanca`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: criar o `case-service` minimo com timeline, entidades e vinculo entre caso, evidencia, hipoteses e achados.
- `justificativa_arquitetural`: sem caso formal, o eixo perde capacidade de continuidade investigativa, mas essa fundacao so deve voltar para a fila ativa depois que o nucleo cognitivo fechar as prioridades de maturacao ainda abertas.
- `arquivos/servicos_principais`: `services/case-service`, `shared/contracts/__init__.py`, `services/orchestrator-service`
- `dependencias`: `MB-027`, `MB-028`
- `criterio_de_aceite`: o sistema consegue abrir um caso, anexar evidencias registradas, manter timeline basica e associar entidades/achados sem sair do nucleo.
- `gate_minimo`: `pytest` direcionado do novo servico, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `deferred` por repriorizacao macro; sem implementacao iniciada.

### MB-030

- `id`: `MB-030`
- `prioridade`: `P1`
- `status`: `deferred`
- `eixo_do_mestre`: `observabilidade`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: criar o `risk-signal-service` minimo para consolidar sinais, prioridade e proxima acao defensiva recomendada por caso.
- `justificativa_arquitetural`: o eixo so ganha valor operacional quando os artefatos investigativos conseguem se transformar em leitura de risco e recomendacao auditavel, mas a prioridade atual voltou ao nucleo e ao seu amadurecimento causal.
- `arquivos/servicos_principais`: `services/risk-signal-service`, `services/case-service`, `services/observability-service`
- `dependencias`: `MB-029`
- `criterio_de_aceite`: o sistema consolida sinais de risco por caso, preserva proveniencia e publica recomendacoes defensivas sem automatizar resposta critica.
- `gate_minimo`: `pytest` direcionado do novo servico, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `deferred` por repriorizacao macro; sem implementacao iniciada.

### MB-031

- `id`: `MB-031`
- `prioridade`: `P1`
- `status`: `deferred`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: introduzir governanca, observabilidade e gate minimo para a fundacao de `protective intelligence`, fechando o primeiro lote do eixo sem reabrir o baseline do `v2`.
- `justificativa_arquitetural`: uma frente nova nao deve nascer sem guardrails explicitos, mas esse fechamento fica diferido ate que o nucleo cognitivo volte a ser o foco ativo da fila micro.
- `arquivos/servicos_principais`: `services/governance-service`, `services/observability-service`, `tools/engineering_gate.py`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`
- `dependencias`: `MB-028`, `MB-029`, `MB-030`
- `criterio_de_aceite`: o eixo ganha sinais minimos de observabilidade, politicas de governanca coerentes e gate suficiente para ser tratado como frente funcional real, ainda defensiva e `advisory_only`.
- `gate_minimo`: `pytest` direcionado, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `deferred` por repriorizacao macro; sem implementacao iniciada.

### MB-032

- `id`: `MB-032`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `mentes`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`
- `micro_objetivo`: transformar metacognicao de sinal declarativo em criterio causal de deliberacao no runtime final, fazendo `primary_mind`, `dominant_tension` e `primary_domain_driver` influenciarem explicitamente criterio de saida, proxima acao e contencao quando houver conflito real.
- `justificativa_arquitetural`: o `programa-de-excelencia` ainda aponta metacognicao real como prioridade alta do nucleo; abrir uma vertical nova antes disso alonga o gap central em vez de fecha-lo.
- `arquivos/servicos_principais`: `engines/cognitive-engine`, `engines/planning-engine`, `engines/synthesis-engine`, `services/observability-service`
- `dependencias`: nenhuma
- `criterio_de_aceite`: quando houver ancora cognitiva ativa, plano, sintese e auditoria conseguem explicitar se ela alterou `success_criteria`, `smallest_safe_next_action` ou recomendacao de contencao, sem criar heuristica nova fora dos registries.
- `gate_minimo`: `pytest` direcionado dos engines/servicos tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `planning`, `synthesis`, `response_synthesized` e `observability` agora carregam `metacognitive_guidance_*` e distinguem quando a ancora cognitiva alterou criterio de saida, proxima acao segura e recomendacao de contencao.

### MB-033

- `id`: `MB-033`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `memorias`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: aprofundar o uso causal de `semantic` e `procedural` por `workflow_profile` e por fonte de continuidade, distinguindo melhor reasoning final, packet de especialista e recovery de missao.
- `justificativa_arquitetural`: memoria causal ja entrou no runtime, mas ainda e um dos maiores gaps remanescentes do nucleo; ela precisa amadurecer antes de abrir uma vertical nova com servicos dedicados.
- `arquivos/servicos_principais`: `shared/memory_registry.py`, `services/memory-service/src/memory_service/service.py`, `engines/planning-engine`, `engines/synthesis-engine`, `services/observability-service`
- `dependencias`: `MB-032`
- `criterio_de_aceite`: o runtime final passa a diferenciar, por workflow e por fonte de continuidade, quando `semantic` e `procedural` alteraram framing, continuidade e proxima acao, sem bypass de governanca nem regressao para hints apenas anexados.
- `gate_minimo`: `pytest` direcionado dos servicos/engines tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `memory_registry`, `memory-service`, `planning`, `synthesis` e `observability` agora distinguem fonte, efeitos, lifecycle e revisao de `semantic`/`procedural` por `workflow_profile` e por fonte de continuidade, separando reasoning final, packet de especialista e recovery de missao.

### MB-034

- `id`: `MB-034`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `memorias`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: iniciar lifecycle nativo de memoria com consolidacao, promocao, envelhecimento e revisao de artefatos `semantic` e `procedural`, sem dependencia externa nova.
- `justificativa_arquitetural`: o `programa-de-excelencia` ainda identifica lifecycle de memoria como gap central; sem isso, o sistema lembra e usa contexto, mas aprende pouco como ecossistema vivo.
- `arquivos/servicos_principais`: `shared/memory_registry.py`, `services/memory-service/src/memory_service/service.py`, `services/memory-service/src/memory_service/repository.py`, `services/observability-service`
- `dependencias`: `MB-033`
- `criterio_de_aceite`: o baseline passa a distinguir pelo menos estados nativos de consolidacao, retencao e envelhecimento para memoria util do runtime, com politica soberana e observabilidade correspondente.
- `gate_minimo`: `pytest` direcionado do `memory-service`, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `memory_registry` e `memory-service` agora tratam consolidacao, promocao, retencao e revisao de `semantic`/`procedural` como sinais soberanos de lifecycle, propagados para planning, synthesis, packets guiados e observabilidade.

### MB-035

- `id`: `MB-035`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `mentes`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: tornar a relacao `mente -> dominio -> especialista` evidencia primaria do runtime e do piloto, reduzindo inferencia posterior a partir de rationale textual.
- `justificativa_arquitetural`: a cadeia ja esta menos implicita, mas ainda nao e evidence-first em todos os consumidores posteriores; esse e um gap de profundidade cognitiva, nao de nova vertical.
- `arquivos/servicos_principais`: `services/orchestrator-service`, `services/observability-service`, `engines/specialist-engine`, `tools/compare_orchestrator_paths.py`, `tools/internal_pilot_report.py`
- `dependencias`: `MB-032`
- `criterio_de_aceite`: runtime, piloto e comparadores passam a explicar esse encadeamento com payload e leitura dedicados, sem depender de parse manual do `rationale`.
- `gate_minimo`: `pytest` direcionado dos servicos/tools tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `orchestrator`, `observability`, piloto e comparadores agora carregam `mind_domain_specialist_chain_*`, `primary_mind` e `primary_route` como evidencia primaria do runtime, reduzindo inferencia posterior a partir de rationale textual.

### MB-036

- `id`: `MB-036`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: promover metacognicao causal, lifecycle de memoria e coerencia `mente -> dominio -> especialista` a sinais formais de evolucao, comparacao sandbox e readiness de release.
- `justificativa_arquitetural`: sem esse fechamento, os proximos avancos do nucleo ficam locais demais e nao se tornam capacidade autoevolutiva governada do ecossistema.
- `arquivos/servicos_principais`: `tools/evolution_from_pilot.py`, `evolution/evolution-lab/src/evolution_lab/service.py`, `tools/compare_orchestrator_paths.py`, `tools/verify_release_signal_baseline.py`
- `dependencias`: `MB-033`, `MB-034`, `MB-035`
- `criterio_de_aceite`: comparadores, laboratorio e verificadores de release passam a tratar esses tres eixos como sinais formais de maturacao do nucleo antes da abertura de nova vertical.
- `gate_minimo`: `pytest` direcionado dos tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `evolution_from_pilot`, `evolution-lab`, `compare_orchestrator_paths`, `internal_pilot_report` e `verify_release_signal_baseline` agora promovem metacognicao causal, lifecycle de memoria e coerencia `mente -> dominio -> especialista` a sinais formais de evolucao governada e readiness de release.

### MB-037

- `id`: `MB-037`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: transformar metacognicao causal, lifecycle de memoria e coerencia `mente -> dominio -> especialista` em vetores priorizados de refinamento por workflow, para que o loop evolutivo passe a sugerir o proximo ganho do nucleo em vez de apenas relatar estado.
- `justificativa_arquitetural`: os sinais novos ja viraram baseline de runtime e release; o passo correto agora e faze-los orientar evolucao governada de forma mais acionavel, sem abrir nova vertical.
- `arquivos/servicos_principais`: `evolution/evolution-lab/src/evolution_lab/service.py`, `tools/evolution_from_pilot.py`, `tools/compare_orchestrator_paths.py`, `tools/internal_pilot_report.py`
- `dependencias`: `MB-036`
- `criterio_de_aceite`: comparadores, laboratorio e relatorios passam a expor `refinement_vectors` ou leitura equivalente por workflow, separando baseline saudavel de melhoria priorizada sem rebaixar maturacao a falha estrutural.
- `gate_minimo`: `pytest` direcionado dos tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `evolution-lab`, `evolution_from_pilot`, `compare_orchestrator_paths` e `internal_pilot_report` agora publicam `refinement_vectors` por workflow e deixam o loop evolutivo sugerir o proximo ganho do nucleo em vez de apenas relatar estado.

### MB-038

- `id`: `MB-038`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `mentes`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: fazer tensao dominante e discordancia entre mentes virarem restricao, checkpoint de validacao ou passo extra do plano quando o workflow exigir profundidade cognitiva maior.
- `justificativa_arquitetural`: a ancora metacognitiva ja e causal, mas a composicao entre mentes ainda precisa sair do nivel declarativo e ganhar efeito deliberativo mais profundo no plano e na sintese.
- `arquivos/servicos_principais`: `engines/cognitive-engine`, `engines/planning-engine`, `engines/synthesis-engine`, `services/observability-service`
- `dependencias`: `MB-037`
- `criterio_de_aceite`: quando houver tensao ou discordancia relevante, o runtime passa a explicitar restricao, validacao adicional ou checkpoint governado sem espalhar heuristica fora dos registries.
- `gate_minimo`: `pytest` direcionado dos engines/servicos tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `planning`, `synthesis`, `orchestrator` e `observability` agora tratam discordancia entre mentes como restricao, checkpoint governado e leitura auditavel do runtime quando o workflow pede maior profundidade cognitiva.

### MB-039

- `id`: `MB-039`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `memorias`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: introduzir telemetria de corpus e pressao de retencao por classe de memoria, tornando consolidacao, promocao, retencao e envelhecimento parte observavel do sistema vivo, e nao apenas decisao local por request.
- `justificativa_arquitetural`: o lifecycle nativo ja existe como sinal; o proximo ganho e fazer o sistema enxergar a saude do proprio corpus com disciplina, antes de qualquer expansao de storage ou dependencia externa.
- `arquivos/servicos_principais`: `shared/memory_registry.py`, `services/memory-service/src/memory_service/service.py`, `services/memory-service/src/memory_service/repository.py`, `services/observability-service/src/observability_service/service.py`
- `dependencias`: `MB-038`
- `criterio_de_aceite`: o baseline passa a publicar resumo coerente de consolidacao, retencao, envelhecimento e revisao por classe, com leitura suficiente para orientar maturacao e evitar crescimento sem criterio.
- `gate_minimo`: `pytest` direcionado do `memory-service` e `observability-service`, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: o baseline agora publica `memory_corpus_status`, `memory_retention_pressure` e resumo de corpus por classe, tornando lifecycle, revisao e pressao de retencao parte observavel do sistema vivo.

### MB-040

- `id`: `MB-040`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: formalizar uma matriz de evals por eixo e por workflow usando os sinais do nucleo como criterio de maturacao, para que excelencia deixe de ser so leitura estrategica e vire gate operacional mais fino.
- `justificativa_arquitetural`: o `programa-de-excelencia` ainda aponta falta de framework formal de evals por eixo e workflow; isso deve nascer sobre o baseline soberano ja endurecido, nao sobre uma vertical nova.
- `arquivos/servicos_principais`: `tools/compare_orchestrator_paths.py`, `tools/verify_active_cut_baseline.py`, `tools/verify_release_signal_baseline.py`, `docs/roadmap/programa-de-excelencia.md`
- `dependencias`: `MB-037`, `MB-038`, `MB-039`
- `criterio_de_aceite`: comparadores e verificadores passam a distinguir de forma mais formal baseline saudavel, maturacao recomendada e vetor prioritario de refinamento por eixo/workflow.
- `gate_minimo`: `pytest` direcionado dos tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: comparadores e verificadores agora expõem matriz formal por workflow/eixo, distinguem baseline saudavel de maturacao recomendada e carregam vetores priorizados de refinamento como criterio operacional.

### MB-041

- `id`: `MB-041`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: abrir a traducao disciplinada da Onda 1 de absorcao, formalizando um recorte implementavel de contratos tipados e validacao soberana inspirado em `PydanticAI` e `Mastra`, sem trocar a gramatica canonica do JARVIS.
- `justificativa_arquitetural`: depois do fechamento de `MB-037` a `MB-040`, o proximo passo correto nao e abrir nova vertical, e sim transformar o estudo tecnologico em backlog de traducao do que mais fortalece o nucleo.
- `arquivos/servicos_principais`: `shared/contracts/__init__.py`, `engines/planning-engine`, `engines/synthesis-engine`, `services/orchestrator-service`, `services/observability-service`
- `dependencias`: nenhuma
- `criterio_de_aceite`: existe ao menos um primeiro recorte de validacao tipada e retry/validator semantics aplicado ao runtime, com observabilidade suficiente para distinguir falha de contrato, falha de output e saida coerente.
- `gate_minimo`: `pytest` direcionado dos engines/servicos tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `planning-engine` agora valida e repara o contrato deliberativo contra schema canonico, `synthesis-engine` passou a validar/recompor output minimo, e `orchestrator`/`observability` distinguem `contract_validation_status` e `output_validation_status` no runtime.

### MB-042

- `id`: `MB-042`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `memorias`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: traduzir padroes de contexto vivo, compressao disciplinada e recall cross-session inspirados em `Letta`, `Hermes Agent` e `Qwen-Agent`, sem substituir o `memory_registry`.
- `justificativa_arquitetural`: o `programa-de-excelencia` ainda aponta gestao de contexto e memoria causal como lacuna canonica forte; essa traducao e mais util agora do que abrir runtime operacional amplo.
- `arquivos/servicos_principais`: `shared/memory_registry.py`, `services/memory-service`, `services/orchestrator-service`, `engines/planning-engine`, `engines/synthesis-engine`
- `dependencias`: nenhuma
- `criterio_de_aceite`: o baseline ganha politica soberana de compactacao/recall e consegue distinguir melhor memoria viva de contexto descartavel sem inflar a janela de contexto.
- `gate_minimo`: `pytest` direcionado de `memory-service`/engines tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `memory_registry`, `memory-service`, `orchestrator`, `planning` e `synthesis` agora tratam contexto vivo compactado e recall cross-session como politica soberana do baseline, distinguindo memoria viva de contexto descartavel sem reabrir historico bruto.

### MB-043

- `id`: `MB-043`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `memorias`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: materializar lifecycle de memoria mais vivo, com manutencao, consolidacao e distincao entre memoria fixada, operacional e arquivavel, inspirado em `Letta / MemGPT`.
- `justificativa_arquitetural`: a camada de memoria do JARVIS ja e forte, mas ainda pode crescer muito em manutencao ativa antes de qualquer absorcao mais ampla de stack externa.
- `arquivos/servicos_principais`: `shared/memory_registry.py`, `services/memory-service/src/memory_service/service.py`, `services/memory-service/src/memory_service/repository.py`, `services/observability-service`
- `dependencias`: `MB-042`
- `criterio_de_aceite`: o sistema passa a manter sinais e politicas mais explicitas de consolidacao, fixacao, arquivamento e revisao de memoria util sem quebrar a ontologia canonica.
- `gate_minimo`: `pytest` direcionado do `memory-service`, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `memory_registry`, `memory-service`, `repository`, `planning`, `orchestrator` e `observability` agora distinguem estados operacionais, fixados e arquivaveis da memoria guiada, com sinais explicitos de consolidacao, fixacao e arquivamento no runtime e no corpus.

### MB-044

- `id`: `MB-044`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `continuidade`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: aprofundar durable execution, resumabilidade e checkpoints de workflow inspirados em `LangGraph` e `Mastra`, sem transformar o runtime inteiro no runtime principal dessas stacks.
- `justificativa_arquitetural`: o baseline ja usa subfluxos e sinais stateful, mas a proxima profundidade real de continuidade longa ainda depende de checkpointing e retomada mais ricos.
- `arquivos/servicos_principais`: `services/orchestrator-service`, `services/orchestrator-service/src/orchestrator_service/langgraph_flow.py`, `shared/contracts/__init__.py`, `services/observability-service`
- `dependencias`: `MB-041`, `MB-042`
- `criterio_de_aceite`: o runtime ganha checkpointing/resume mais rico em workflows longos, com trace observavel e sem terceirizar governanca ou ontologia ao grafo.
- `gate_minimo`: `pytest` direcionado do `orchestrator-service`, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `orchestrator-service`, `langgraph_flow`, `operational-service`, `observability-service` e contratos compartilhados agora carregam `workflow_checkpoint_state`, `workflow_resume_status`, `workflow_resume_point` e `workflow_pending_checkpoints` como sinais soberanos de durable execution e retomada governada.

### MB-045

- `id`: `MB-045`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `memorias`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: abrir o primeiro lifecycle soberano de artefatos procedurais reutilizaveis, inspirado em `Hermes Agent` e `OpenClaw`, sem confundir isso com promocao de especialista ou tool use irrestrito.
- `justificativa_arquitetural`: memoria procedural ainda e classe de memoria; o passo seguinte e avaliar quando ela deve virar artefato reutilizavel e governado pelo nucleo.
- `arquivos/servicos_principais`: `shared/memory_registry.py`, `services/memory-service`, `evolution/evolution-lab`, `services/observability-service`
- `dependencias`: `MB-042`, `MB-043`
- `criterio_de_aceite`: existe ao menos um fluxo experimental controlado em que know-how procedural vira artefato rastreavel, versionavel e reutilizavel, ainda `through_core_only`.
- `gate_minimo`: `pytest` direcionado dos servicos/tools tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `memory_registry`, `memory-service`, `repository`, `planning`, `synthesis` e `orchestrator` agora distinguem `procedural_artifact_status`, refs, versao e resumo como artefato reutilizavel `through_core_only`, sem confundir isso com promocao de especialista ou tool use irrestrito.

### MB-046

- `id`: `MB-046`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `evolucao`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: traduzir `compile/eval loops` inspirados em `DSPy / MIPROv2` e `TextGrad` para o `evolution-lab`, tornando proposals de refinamento mais metric-driven e menos manuais.
- `justificativa_arquitetural`: o baseline ja tem `refinement_vectors`; o passo seguinte e deixar o laboratorio propor, priorizar e comparar variantes com algoritmo de refinamento mais forte.
- `arquivos/servicos_principais`: `evolution/evolution-lab/src/evolution_lab/service.py`, `tools/evolution_from_pilot.py`, `tools/compare_orchestrator_paths.py`, `tools/verify_release_signal_baseline.py`
- `dependencias`: `MB-041`, `MB-043`, `MB-045`
- `criterio_de_aceite`: o laboratorio passa a registrar propostas com metricas, candidatos, criterio de selecao e comparacao mais explicitamente inspirados em compile loops, sem automatizar promocao de mudanca.
- `gate_minimo`: `pytest` direcionado dos tools/servicos tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `impacto_no_baseline`: `evolution-lab`, `compare_orchestrator_paths`, `evolution_from_pilot`, `internal_pilot_report` e `verify_release_signal_baseline.py` agora registram `candidate_refs`, `refinement_vectors`, `evaluation_matrix`, `selection_criteria` e `metric_deltas`, fechando a Onda 1 como traducao governada de compile/eval loops.

### MB-047

- `id`: `MB-047`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `fluxo_principal`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: transformar `workflow_profile` em criterio real de saida, completude e qualidade da ultima milha do runtime, evitando linguagem generica quando a rota ja conhece foco, checkpoint e gate de entrega.
- `justificativa_arquitetural`: o contrato de workflow ja atravessa o runtime, mas ainda ha espaco para fazer criterio de fechamento e completude final depender menos de framing generico e mais do contrato soberano da rota.
- `arquivos/servicos_principais`: `shared/domain_registry.py`, `engines/planning-engine`, `engines/synthesis-engine`, `services/orchestrator-service`, `services/observability-service`
- `dependencias`: `MB-044`
- `criterio_de_aceite`: `planning`, `synthesis`, `orchestrator` e `observability` passam a distinguir criterios de saida e completude por `workflow_profile`, com sinais auditaveis que separam output coerente, output parcial e output desalinhado por rota.
- `gate_minimo`: `pytest` direcionado dos engines/servicos tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: `synthesis`, `orchestrator` e `observability` agora distinguem output coerente, parcial e desalinhado por `workflow_profile`, e esse contrato passou a pesar no fechamento formal do fluxo.

### MB-048

- `id`: `MB-048`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `memorias`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: tornar `semantic` e `procedural` mais causais no runtime final, fazendo framing, prioridade, profundidade e recomendacao final responderem melhor a continuidade util por workflow e por fonte de memoria.
- `justificativa_arquitetural`: depois de distinguir memoria viva, lifecycle e artefatos procedurais, o proximo ganho real e fazer essas classes pesarem mais na direcao do raciocinio, e nao apenas na ancoragem contextual.
- `arquivos/servicos_principais`: `shared/memory_registry.py`, `services/memory-service`, `engines/planning-engine`, `engines/synthesis-engine`, `services/orchestrator-service`
- `dependencias`: `MB-047`
- `criterio_de_aceite`: o runtime final passa a distinguir melhor quando `semantic` e `procedural` alteraram framing, prioridade, profundidade e recomendacao final por `workflow_profile`, sem bypass de governanca nem regressao para hints apenas anexados.
- `gate_minimo`: `pytest` direcionado de `memory-service`/engines tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: `memory_registry`, `planning`, `synthesis` e os comparadores agora distinguem efeito de memoria por workflow e por fonte de continuidade, fazendo `semantic` e `procedural` pesarem em prioridade, profundidade e recomendacao final do runtime.

### MB-049

- `id`: `MB-049`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `cognicao`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: tornar a cadeia `mente -> dominio -> especialista` ainda mais evidence-first nos consumidores finais, reduzindo o que ainda fica implicito entre selecao, sintese, comparacao e release signals.
- `justificativa_arquitetural`: a cadeia ja existe como sinal primario, mas ainda pode pesar mais na decisao final e nos criterios de coerencia do ecossistema sem virar heuristica espalhada.
- `arquivos/servicos_principais`: `engines/cognitive-engine`, `engines/planning-engine`, `engines/synthesis-engine`, `services/orchestrator-service`, `services/observability-service`, `tools/compare_orchestrator_paths.py`
- `dependencias`: `MB-047`, `MB-048`
- `criterio_de_aceite`: a cadeia `mente -> dominio -> especialista` passa a influenciar mais explicitamente selecao, sintese, comparacao e readiness de release, com menos dependencia de parse posterior de rationale.
- `gate_minimo`: `pytest` direcionado dos engines/servicos/tools tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: `orchestrator`, `synthesis`, `compare_orchestrator_paths` e `evolution-lab` agora tratam a cadeia `mente -> dominio -> especialista` como evidencia primaria mais rica, incluindo planned hints, alinhamento parcial e coerencia do encadeamento no runtime final.

### MB-050

- `id`: `MB-050`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: separar formalmente `baseline_saudavel` de `maturation_recommended` em observabilidade, comparadores, piloto e gates, para que maturacao futura nao seja confundida com regressao estrutural.
- `justificativa_arquitetural`: o projeto ja distinguiu parte dessa leitura, mas falta torná-la mais formal e uniforme para evitar drift de interpretacao entre runtime, comparacao e release.
- `arquivos/servicos_principais`: `services/observability-service`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`, `tools/verify_release_signal_baseline.py`, `tools/verify_active_cut_baseline.py`
- `dependencias`: `MB-047`, `MB-048`, `MB-049`
- `criterio_de_aceite`: `baseline_saudavel`, `maturation_recommended` e `attention_required` passam a ter semantica mais consistente entre auditoria, piloto, comparadores e gates, sem alterar o contrato do usuario final por conveniencia local.
- `gate_minimo`: `pytest` direcionado dos tools/servicos tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `impacto_no_baseline`: `workflow_output_status` agora entra formalmente em piloto, comparadores, `evolution-lab` e verificadores de release como separacao explicita entre `baseline_saudavel`, `maturation_recommended` e `attention_required`.

### MB-051

- `id`: `MB-051`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `evolucao`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fazer o `evolution-lab` usar os sinais refinados do nucleo para priorizar melhor quais refinamentos merecem experimento real por workflow, preparando o proximo salto de autoevolucao governada.
- `justificativa_arquitetural`: depois de fechar compile/eval loops da Onda 1, o proximo ganho nao e abrir nova vertical, e sim fazer o laboratorio priorizar melhor o que deve virar experimento candidato.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `tools/evolution_from_pilot.py`, `tools/compare_orchestrator_paths.py`, `tools/verify_release_signal_baseline.py`
- `dependencias`: `MB-048`, `MB-049`, `MB-050`
- `criterio_de_aceite`: o laboratorio passa a priorizar melhor candidatos por workflow com base em sinais mais causais do nucleo, sem automatizar promocao de mudanca nem abrir frente macro nova.
- `gate_minimo`: `pytest` direcionado dos tools/servicos tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: `evolution_from_pilot`, `evolution-lab` e `verify_release_signal_baseline.py` agora usam sinais mais causais do nucleo para priorizar experimentos por workflow, sem automatizar promocao nem abrir nova frente macro.

### MB-052

- `id`: `MB-052`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `mentes`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: tornar a metacognicao mais adaptativa no meio do fluxo, fazendo recomposicao e mudanca de estrategia cognitiva reagirem a impasses reais de plano, workflow e output sem esperar apenas o fechamento final.
- `justificativa_arquitetural`: o baseline agora ja audita `workflow_output_status`, discordancia entre mentes e recomposicao cognitiva; o proximo ganho real e fazer esses sinais alterarem o proprio caminho do runtime durante a execucao.
- `arquivos/servicos_principais`: `engines/cognitive-engine`, `engines/planning-engine`, `services/orchestrator-service`, `services/observability-service`
- `dependencias`: `MB-047`, `MB-049`
- `criterio_de_aceite`: o runtime passa a emitir recomposicao ou mudanca de estrategia cognitiva mid-flow quando houver impasse real de plano/output, com `reason`, `trigger` e impacto rastreavel em passos, checkpoints ou criterios de saida, sem bypass de governanca nem de soberania de dominio.
- `gate_minimo`: `pytest` direcionado dos engines/servicos tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: `planning-engine`, `synthesis-engine`, `orchestrator-service` e `observability-service` agora tornam a mudanca de estrategia cognitiva mid-flow parte observavel do baseline quando a revisao especializada preserva um impasse governado.

### MB-053

- `id`: `MB-053`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `memorias`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: transformar lifecycle de memoria em sistema vivo operacional, fazendo promocao, consolidacao, fixacao, revisao e arquivamento alterarem de forma controlada recovery, packet guiado e corpus util do runtime.
- `justificativa_arquitetural`: o baseline ja publica telemetria de `retention_pressure`, consolidacao, fixacao e arquivamento, mas ainda falta fazer esse lifecycle alterar comportamento real de recuperacao e manutencao do corpus.
- `arquivos/servicos_principais`: `shared/memory_registry.py`, `services/memory-service/src/memory_service/service.py`, `services/memory-service/src/memory_service/repository.py`, `services/observability-service`
- `dependencias`: `MB-052`
- `criterio_de_aceite`: o runtime passa a aplicar regras soberanas de promocao, consolidacao, revisao e arquivamento no proprio fluxo de memoria, sem inflar o corpus nem quebrar as classes canonicas do sistema.
- `gate_minimo`: `pytest` direcionado de `memory-service`/`observability-service`, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: `memory_registry`, `memory-service`, `repository` e `observability-service` agora fazem lifecycle de memoria alterar recovery, packet guiado, reuso recorrente e auditoria de drift quando memoria arquivavel tenta voltar ao especialista sem revisao.

### MB-054

- `id`: `MB-054`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `memorias`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: fazer memoria util influenciar mais explicitamente rota, hint especializado e ranking de continuidade, em vez de pesar quase so em framing e recomendacao final.
- `justificativa_arquitetural`: depois de fortalecer a causalidade de `semantic` e `procedural` no plano e na sintese, o proximo passo e fazer historico util alterar selecao de caminho do runtime.
- `arquivos/servicos_principais`: `engines/cognitive-engine`, `engines/planning-engine`, `engines/specialist-engine`, `services/orchestrator-service`, `services/memory-service`
- `dependencias`: `MB-052`, `MB-053`
- `criterio_de_aceite`: rota, especialista, profundidade e ranking de continuidade passam a responder melhor a memoria relevante do usuario/missao, sem reintroduzir heuristica espalhada fora dos registries soberanos.
- `gate_minimo`: `pytest` direcionado dos engines/servicos tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: `cognitive-engine`, `orchestrator-service`, `planning-engine` e comparadores agora fazem memoria relevante influenciar rota prioritaria, hints especializados, ranking de continuidade e leitura causal do caminho do runtime, sem reintroduzir heuristica espalhada fora dos registries soberanos.

### MB-055

- `id`: `MB-055`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `mentes`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: aprofundar a composicao de mentes por workflow e dominio, fazendo historico de composicoes, tensao dominante e discordancia entre mentes alterarem apoio, validacao e fechamento do fluxo de forma mais causal.
- `justificativa_arquitetural`: a composicao cognitiva atual ja e visivel e util, mas ainda e mais declarativa do que deliberativa no meio e no fim do fluxo.
- `arquivos/servicos_principais`: `shared/mind_registry.py`, `engines/cognitive-engine`, `engines/planning-engine`, `services/observability-service`, `tools/compare_orchestrator_paths.py`, `tools/verify_release_signal_baseline.py`
- `dependencias`: `MB-052`, `MB-054`
- `criterio_de_aceite`: composicao de mentes passa a influenciar mais explicitamente apoio, validacao, criterios de saida e readiness de release por workflow, com menos dependencia de parse posterior de `rationale`.
- `gate_minimo`: `pytest` direcionado dos engines/servicos/tools tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: `planning-engine`, `synthesis-engine`, `observability-service`, `compare_orchestrator_paths.py` e `verify_release_signal_baseline.py` agora tratam discordancia, checkpoint de validacao entre mentes e cadeia `mente -> dominio -> especialista` como sinais causais mais explicitos de saida, maturacao e release.

### MB-056

- `id`: `MB-056`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `evolucao`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: formalizar readiness da Onda 2 de absorcao como matriz de experimento controlado, usando os sinais causais do nucleo para indicar quais referencias externas merecem traducao pequena no proximo ciclo sem abrir nova vertical nem promover stack por impulso.
- `justificativa_arquitetural`: a Onda 1 foi absorvida com disciplina; o proximo passo nao e importar mais tecnologia, e sim criar criterio formal para decidir onde a Onda 2 realmente agrega ao nucleo.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `tools/evolution_from_pilot.py`, `tools/compare_orchestrator_paths.py`, `docs/architecture/technology-absorption-order.md`
- `dependencias`: `MB-053`, `MB-054`, `MB-055`
- `criterio_de_aceite`: o laboratorio e os comparadores passam a publicar uma matriz de readiness para experimentos da Onda 2, subordinada aos sinais do nucleo e sem automatizar promocao de tecnologia externa.
- `gate_minimo`: `pytest` direcionado dos tools/servicos tocados, `ruff` direcionado, `python tools/check_mojibake.py docs/architecture docs/implementation` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: `evolution-lab`, `compare_orchestrator_paths.py` e `docs/architecture/technology-absorption-order.md` agora publicam uma matriz de readiness da Onda 2 subordinada aos sinais causais do nucleo, mantendo a proxima absorcao externa como experimento controlado em vez de frente macro nova.

### MB-057

- `id`: `MB-057`
- `prioridade`: `P0`
- `status`: `completed`
- `eixo_do_mestre`: `fluxo_principal`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: transformar os sinais causais ja materializados no baseline em um contrato soberano de intervencao adaptativa governada, antes da sintese final e sem abrir nova vertical do sistema.
- `justificativa_arquitetural`: o runtime ja produz `workflow_output_status`, `mind_disagreement_status`, `mind_validation_checkpoint_status`, `memory_retention_pressure`, `workflow_resume_status` e sinais correlatos, mas o proximo ganho real do nucleo e fazer esses slices escolherem checkpoints e contencoes bounded em vez de ficarem apenas como evidencia posterior.
- `arquivos/servicos_principais`: `shared/domain_registry.py`, `engines/planning-engine`, `services/orchestrator-service`, `services/observability-service`
- `dependencias`: `MB-052`, `MB-053`, `MB-055`
- `criterio_de_aceite`: `planning` e `orchestrator` passam a carregar um slice explicito de `adaptive_intervention_*`, derivado apenas de sinais soberanos e guidance do `workflow_profile`, distinguindo pelo menos checkpoint de clarificacao, checkpoint de revisao de memoria, reavaliacao especializada e contencao segura sem heuristica espalhada fora dos registries do nucleo.
- `gate_minimo`: `pytest` direcionado dos engines/servicos tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: o runtime passa a tratar intervencao adaptativa como contrato soberano e auditavel do fluxo, usando sinais ja existentes do nucleo para decidir o proximo movimento seguro antes do fechamento final.

### MB-058

- `id`: `MB-058`
- `prioridade`: `P0`
- `status`: `completed`
- `eixo_do_mestre`: `governanca`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: fazer `planning`, `orchestrator`, memoria e revisao especializada aplicarem esse contrato como politica governada de proximo passo, evitando tanto overreaction quanto silencio quando os sinais pedirem intervencao.
- `justificativa_arquitetural`: depois de formalizar o contrato, o ganho seguinte e fazer o runtime reagir de forma pequena, reversivel e explicavel quando houver impasse, pressao de memoria, checkpoint de validacao ou perda de completude por workflow.
- `arquivos/servicos_principais`: `engines/planning-engine`, `engines/specialist-engine`, `services/orchestrator-service`, `services/memory-service`, `services/governance-service`
- `dependencias`: `MB-057`
- `criterio_de_aceite`: o runtime passa a escolher uma unica intervencao governada por request quando os sinais justificarem isso, registrando `reason`, `trigger`, `selected_action` e `expected_effect` sem bypassar governanca, sem abrir especialistas fora da rota elegivel e sem transformar contencao em fallback generico.
- `gate_minimo`: `pytest` direcionado dos engines/servicos tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: `planning`, `orchestrator`, memoria e governanca passam a responder ao estado causal do runtime com checkpoints e contencoes bounded, em vez de apenas relatar o problema no fim do fluxo.

### MB-059

- `id`: `MB-059`
- `prioridade`: `P1`
- `status`: `completed`
- `eixo_do_mestre`: `observabilidade`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: tornar essas intervencoes parte da evidencia formal do baseline, com cenarios deliberados, comparacao de caminhos e leitura auditavel do que foi util, excessivo ou insuficiente por workflow.
- `justificativa_arquitetural`: sem observabilidade propria, a intervencao adaptativa correria o risco de virar heuristica opaca; o baseline precisa mostrar quando houve intervencao, por que ela aconteceu e se ela melhorou o fechamento do fluxo.
- `arquivos/servicos_principais`: `services/observability-service`, `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`, `tools/verify_active_cut_baseline.py`
- `dependencias`: `MB-058`
- `criterio_de_aceite`: piloto, comparadores e auditoria passam a cobrir cenarios deliberados de intervencao adaptativa e a expor pelo menos `adaptive_intervention_status`, `adaptive_intervention_reason` e `adaptive_intervention_effectiveness`, distinguindo resposta coerente de intervencao desnecessaria ou insuficiente.
- `gate_minimo`: `pytest` direcionado dos tools/servicos tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: a intervencao adaptativa deixa de ser apenas comportamento interno e passa a existir como sinal auditavel e comparavel do baseline por workflow.

### MB-060

- `id`: `MB-060`
- `prioridade`: `P1`
- `status`: `completed`
- `eixo_do_mestre`: `evolucao`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fazer `refinement_vectors`, `evaluation_matrix` e verificadores de release usarem a efetividade das intervencoes adaptativas como insumo de priorizacao do proximo refinamento do nucleo, sem automatizar promocao de mudanca.
- `justificativa_arquitetural`: o laboratorio ja sabe ler sinais causais do runtime; o proximo ganho e usar o resultado das intervencoes governadas para separar melhor o que merece experimento, o que pede hardening e o que continua apenas como maturacao recomendada.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `tools/evolution_from_pilot.py`, `tools/compare_orchestrator_paths.py`, `tools/verify_release_signal_baseline.py`
- `dependencias`: `MB-059`
- `criterio_de_aceite`: `evolution-lab`, comparadores e verificadores passam a registrar `adaptive_intervention_effectiveness` e seu peso em `refinement_vectors`/`evaluation_matrix`, priorizando refinamentos por workflow sem transformar o laboratorio em promotor automatico de baseline.
- `gate_minimo`: `pytest` direcionado dos tools/servicos tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: o loop evolutivo passa a tratar a efetividade das intervencoes adaptativas como insumo formal de priorizacao do proximo ganho causal do nucleo.

### MB-061

- `id`: `MB-061`
- `prioridade`: `P1`
- `status`: `completed`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar o lote de intervencao adaptativa governada do nucleo, sincronizando backlog, handoff, snapshot, changelog e gate com o novo estado real do baseline.
- `justificativa_arquitetural`: esse lote altera criterio de comportamento do runtime e a leitura comparativa do baseline; o fechamento precisa consolidar o contrato novo sem deixar docs vivos em drift nem reabrir a fila por inercia.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-057`, `MB-058`, `MB-059`, `MB-060`
- `criterio_de_aceite`: o lote termina com docs vivos refletindo a intervencao adaptativa governada como baseline do nucleo, `CHANGELOG.md` sincronizado e gate minimo validado, deixando o proximo passo macro explicitamente ancorado nos novos sinais do runtime.
- `gate_minimo`: `python tools/check_mojibake.py docs/implementation docs/operations HANDOFF.md CHANGELOG.md` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `impacto_no_baseline`: o lote fecha com memoria operacional, backlog micro, snapshot e changelog coerentes com a nova gramatica de intervencao adaptativa governada do nucleo.

### MB-062

- `id`: `MB-062`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `fluxo_principal`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: fazer a escolha entre `memory_review_checkpoint` e `specialist_reevaluation` respeitar prioridade soberana por `workflow_profile`, em vez de depender de ordem fixa do engine.
- `justificativa_arquitetural`: o contrato de intervencao adaptativa ja existia, mas a selecao entre revisao de memoria e reavaliacao especializada ainda era quase generica; o proximo ganho real e deixar o workflow ativo governar essa precedencia sem reabrir heuristica local espalhada.
- `arquivos/servicos_principais`: `shared/domain_registry.py`, `engines/planning-engine/src/planning_engine/engine.py`, `engines/planning-engine/tests/test_planning_engine.py`
- `dependencias`: `MB-057`, `MB-058`
- `criterio_de_aceite`: quando houver sinais concorrentes de memoria e discordancia cognitiva, o `planning-engine` passa a selecionar a intervencao de acordo com a prioridade soberana do `workflow_profile`; clarificacao e contencao segura continuam tendo precedencia absoluta.
- `gate_minimo`: `pytest` direcionado do `planning-engine`, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: o runtime agora deixa a prioridade entre revisao de memoria e reavaliacao especializada ser governada pelo registry soberano de workflow, reduzindo genericidade residual na intervencao adaptativa.

### MB-063

- `id`: `MB-063`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: auditar e comparar se a intervencao adaptativa escolhida bate com a prioridade soberana do `workflow_profile`, distinguindo match correto de override por salvaguarda obrigatoria.
- `justificativa_arquitetural`: depois de mover a prioridade para o registry, o baseline precisa evidenciar quando a escolha seguiu a politica do workflow e quando foi corretamente sobreposta por clarificacao ou contencao segura.
- `arquivos/servicos_principais`: `services/observability-service`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`, `tools/verify_release_signal_baseline.py`
- `dependencias`: `MB-062`
- `criterio_de_aceite`: auditoria, comparadores e leitura de release passam a expor pelo menos um sinal de `adaptive_intervention_policy_status`, diferenciando `policy_aligned`, `mandatory_override` e `attention_required`.
- `gate_minimo`: `pytest` direcionado dos services/tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: a prioridade soberana de intervencao deixa de existir apenas no `planning` e passa a virar evidencia auditavel do baseline por workflow.

### MB-064

- `id`: `MB-064`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `sintese`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: tornar a leitura final do runtime mais explicita sobre por que a prioridade do workflow escolheu uma intervencao e qual checkpoint ativo ela preservou.
- `justificativa_arquitetural`: sem essa camada, a politica de prioridade fica correta internamente, mas ainda exige parse heroico de rationale para entender o efeito da escolha no fechamento do fluxo.
- `arquivos/servicos_principais`: `engines/synthesis-engine`, `services/orchestrator-service`
- `dependencias`: `MB-063`
- `criterio_de_aceite`: `response_synthesized` e a resposta final passam a refletir, de forma bounded, o motivo do workflow para a intervencao selecionada e o checkpoint/gate preservado por ela.
- `gate_minimo`: `pytest` direcionado dos engines/servicos afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `impacto_no_baseline`: a ultima milha do runtime agora explicita a prioridade soberana da intervencao por workflow, inclusive com checkpoint e gate preservados em `synthesis` e `response_synthesized`.

### MB-065

- `id`: `MB-065`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `evolucao`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fazer `refinement_vectors` e a `evaluation_matrix` usarem mismatch ou inefetividade da politica de intervencao por workflow como insumo de refinamento do nucleo.
- `justificativa_arquitetural`: depois de auditar a politica, o loop evolutivo precisa saber quais workflows ainda escolhem a intervencao certa, mas fecham mal, e quais ainda pedem ajuste na propria prioridade soberana.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `tools/evolution_from_pilot.py`, `tools/compare_orchestrator_paths.py`
- `dependencias`: `MB-063`, `MB-064`
- `criterio_de_aceite`: mismatch ou efetividade insuficiente da politica de intervencao passam a influenciar `refinement_vectors` por workflow sem promover mudanca automaticamente.
- `gate_minimo`: `pytest` direcionado dos tools/servicos afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: mismatch ou fechamento insuficiente da politica de intervencao agora entram em `refinement_vectors`, `evaluation_matrix` e propostas sandbox como criterio evolutivo por workflow.

### MB-066

- `id`: `MB-066`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar o lote de prioridade soberana de intervencao por workflow com docs vivos, changelog e gate sincronizados.
- `justificativa_arquitetural`: esse lote muda a leitura do baseline e da propria evidencia comparativa; o fechamento precisa consolidar a nova gramatica sem deixar a fila ou os docs em drift.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-063`, `MB-064`, `MB-065`
- `criterio_de_aceite`: o lote termina com docs vivos coerentes com a nova prioridade soberana por workflow, `CHANGELOG.md` sincronizado e gate minimo validado.
- `gate_minimo`: `python tools/check_mojibake.py docs/implementation docs/operations HANDOFF.md CHANGELOG.md` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `impacto_no_baseline`: o lote fecha com sintese, comparadores, loop evolutivo e docs vivos sincronizados em torno da prioridade soberana de intervencao por workflow.

### MB-067

- `id`: `MB-067`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `fluxo_principal`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: formalizar um contrato soberano de decisao de capacidades e ferramentas por request, derivado do estado executivo do runtime e nao de improviso local da LLM.
- `justificativa_arquitetural`: depois de fechar a politica soberana de intervencao adaptativa por workflow, o proximo ganho real do nucleo e tornar explicita a decisao sobre capacidade, ferramenta, handoff e dispatch elegivel, sem deixar essa camada como parse implicito do plano ou da resposta.
- `arquivos/servicos_principais`: `shared/contracts/__init__.py`, `shared/schemas/__init__.py`, `shared/domain_registry.py`, `engines/planning-engine`, `services/orchestrator-service`
- `dependencias`: `MB-062`, `MB-063`, `MB-064`
- `criterio_de_aceite`: `planning` e `orchestrator` passam a carregar um slice explicito de `capability_decision_*`, distinguindo pelo menos objetivo, elegibilidade, autorizacao, modo de execucao e fallback governado, sem bypassar registry, governanca ou memoria canonica.
- `gate_minimo`: `pytest` direcionado dos engines/servicos tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: a escolha de capacidade/ferramenta deixa de ser detalhe implicito do runtime e passa a existir como contrato soberano, pequeno e auditavel do fluxo principal.

### MB-068

- `id`: `MB-068`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `governanca`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: fazer `planning`, `orchestrator`, dispatch e governanca aplicarem esse contrato como politica soberana de elegibilidade, autorizacao e handoff bounded de capacidades.
- `justificativa_arquitetural`: depois de formalizar o contrato, o passo seguinte e impedir que selecao de capacidade, uso de ferramenta ou handoff de borda virem decisao espalhada entre prompt, heuristica residual e adapters locais.
- `arquivos/servicos_principais`: `engines/planning-engine`, `services/orchestrator-service`, `services/governance-service`, `operation_dispatch`
- `dependencias`: `MB-067`
- `criterio_de_aceite`: o runtime passa a escolher capacidade e handoff elegiveis por request com `reason`, `authorization_status`, `selected_mode` e `expected_effect`, sem abrir caminho paralelo fora do contrato soberano nem promover stack externa a cerebro do sistema.
- `gate_minimo`: `pytest` direcionado dos engines/servicos tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: capacidade e handoff de borda passam a responder a elegibilidade e autorizacao soberanas, em vez de depender de improviso residual do fluxo.

### MB-069

- `id`: `MB-069`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: tornar a decisao soberana de capacidade e ferramenta parte da evidencia auditavel do baseline, incluindo tracing, handoff e adaptadores de sessao nas bordas do fluxo.
- `justificativa_arquitetural`: sem evidencia propria, essa camada correria o risco de virar opaca; o baseline precisa mostrar quando uma capacidade foi elegivel, autorizada, acionada, negada ou corretamente contida por workflow.
- `arquivos/servicos_principais`: `services/observability-service`, `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`, `tools/verify_release_signal_baseline.py`
- `dependencias`: `MB-068`
- `criterio_de_aceite`: auditoria, piloto e comparadores passam a expor pelo menos `capability_decision_status`, `capability_authorization_status`, `handoff_adapter_status` e `capability_effectiveness`, distinguindo uso coerente, uso excessivo, negacao correta e bypass indevido.
- `gate_minimo`: `pytest` direcionado dos services/tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: a decisao de capacidade/ferramenta deixa de ser telemetria lateral e passa a existir como evidencia formal e comparavel do runtime.

### MB-070

- `id`: `MB-070`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `evolucao`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fazer `refinement_vectors`, `evaluation_matrix` e verificadores de release usarem efetividade e drift da politica soberana de capacidades como insumo do proximo refinamento do nucleo.
- `justificativa_arquitetural`: depois de tornar a decisao observavel, o loop evolutivo precisa separar melhor quando o problema esta na elegibilidade da capacidade, na autorizacao, no tracing/handoff de borda ou no proprio desenho do workflow.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `tools/evolution_from_pilot.py`, `tools/compare_orchestrator_paths.py`, `tools/verify_release_signal_baseline.py`
- `dependencias`: `MB-069`
- `criterio_de_aceite`: `evolution-lab`, comparadores e verificadores passam a registrar mismatch, inefetividade ou overreach da politica de capacidades em `refinement_vectors` e `evaluation_matrix`, sem automatizar promocao de mudanca ou stack externa.
- `gate_minimo`: `pytest` direcionado dos tools/servicos tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: a politica soberana de capacidades passa a influenciar de forma formal a priorizacao do proximo ganho causal do nucleo.

### MB-071

- `id`: `MB-071`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar o lote de decisao soberana de capacidades com docs vivos, changelog e gate sincronizados ao novo estado real do baseline.
- `justificativa_arquitetural`: esse lote muda a leitura do fluxo principal, da governanca de ferramentas e da evidencia comparativa; o fechamento precisa consolidar o contrato novo sem deixar backlog, handoff e snapshot em drift.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-067`, `MB-068`, `MB-069`, `MB-070`
- `criterio_de_aceite`: o lote termina com docs vivos refletindo a decisao soberana de capacidades como baseline do nucleo, `CHANGELOG.md` sincronizado e gate minimo validado.
- `gate_minimo`: `python tools/check_mojibake.py docs/implementation docs/operations HANDOFF.md CHANGELOG.md` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `impacto_no_baseline`: o lote fecha com backlog, handoff, snapshot e changelog coerentes com a nova gramatica soberana de capacidade, ferramenta e handoff bounded.

### MB-072

- `id`: `MB-072`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `fluxo_principal`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: formalizar manutencao ativa de memoria viva por request, com contrato explicito para `memory_review`, compaction e recall cross-session governado.
- `justificativa_arquitetural`: depois de fechar a gramatica soberana de capacidades, o proximo ganho causal do nucleo e endurecer o lifecycle vivo da memoria para que review, compactacao e recall deixem de ser heuristica residual e passem a responder ao estado real do runtime.
- `arquivos/servicos_principais`: `memory-service`, `shared/memory_registry`, `engines/planning-engine`, `services/orchestrator-service`
- `dependencias`: `MB-063`, `MB-064`, `MB-065`, `MB-066`
- `criterio_de_aceite`: `memory-service`, `planning` e `orchestrator` passam a carregar um slice explicito de manutencao ativa de memoria, distinguindo pelo menos review necessario, compactacao aplicavel, recall cross-session e fallback contido, sem inflar janela, reabrir historico bruto ou bypassar memoria canonica.
- `gate_minimo`: `pytest` direcionado dos services/engines tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: review, compactacao e recall cross-session deixam de ser efeito lateral da memoria e passam a existir como contrato vivo e auditavel do fluxo principal.

### MB-073

- `id`: `MB-073`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `governanca`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: fazer recovery, packet guiado e reuse de memoria cross-session aplicarem essa manutencao viva como politica soberana do runtime.
- `justificativa_arquitetural`: depois de formalizar o contrato de manutencao ativa, o passo seguinte e impedir que review de memoria, compaction e recall cross-session virem comportamento espalhado entre adapters, heuristicas locais e resumo contextual ad hoc.
- `arquivos/servicos_principais`: `memory-service`, `shared/memory_registry`, `services/orchestrator-service`, `services/knowledge-service`
- `dependencias`: `MB-072`
- `criterio_de_aceite`: recovery, memoria guiada e reuse cross-session passam a responder a `memory_review`, compaction e recall soberanos por request, com efeito observavel em framing, continuidade, foco de especialista e proxima acao, sem quebrar escopo canonico.
- `gate_minimo`: `pytest` direcionado dos services tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: memoria viva deixa de ser apenas registro e passa a dirigir reuse e continuidade de forma mais governada, compacta e causal.

### MB-074

- `id`: `MB-074`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: tornar manutencao ativa de memoria viva parte da evidencia auditavel do baseline em tracing, piloto e comparadores.
- `justificativa_arquitetural`: sem evidencia propria, review de memoria, compaction e recall cross-session 2.0 podem parecer melhoria sem prova; o baseline precisa mostrar quando memoria viva foi acionada, ficou estavel, entrou em pressao ou foi corretamente contida.
- `arquivos/servicos_principais`: `services/observability-service`, `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`
- `dependencias`: `MB-073`
- `criterio_de_aceite`: auditoria, piloto e comparadores passam a expor pelo menos `memory_review_status`, sinais de compaction, estado de recall cross-session e pressao de retencao ao longo do fluxo, distinguindo uso causal, uso superficial e drift de memoria viva.
- `gate_minimo`: `pytest` direcionado dos services/tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: a manutencao ativa de memoria deixa de ser telemetria lateral e passa a existir como evidencia formal e comparavel do runtime.

### MB-075

- `id`: `MB-075`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `evolucao`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fazer `refinement_vectors`, `evaluation_matrix` e leitura de release usarem efetividade e drift da memoria viva como insumo do proximo refinamento do nucleo.
- `justificativa_arquitetural`: depois de tornar memoria viva observavel, o loop evolutivo precisa separar melhor quando o problema esta em review, compactacao, reuse cross-session ou no proprio workflow que consome memoria.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `tools/evolution_from_pilot.py`, `tools/compare_orchestrator_paths.py`, `tools/verify_release_signal_baseline.py`
- `dependencias`: `MB-074`
- `criterio_de_aceite`: `evolution-lab`, comparadores e verificadores passam a registrar mismatch, pressao ou inefetividade de memoria viva em `refinement_vectors` e `evaluation_matrix`, sem automatizar promocao de mudanca ou dependencia externa.
- `gate_minimo`: `pytest` direcionado dos tools/servicos tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: memoria viva passa a influenciar de forma formal a priorizacao do proximo ganho causal do nucleo.

### MB-076

- `id`: `MB-076`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar o lote de memoria viva ativa com docs vivos, changelog e gate sincronizados ao novo estado real do baseline.
- `justificativa_arquitetural`: esse lote muda a leitura do recovery, do reuse cross-session e da compactacao do contexto; o fechamento precisa consolidar o contrato novo sem deixar backlog, handoff e snapshot em drift.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-072`, `MB-073`, `MB-074`, `MB-075`
- `criterio_de_aceite`: o lote termina com docs vivos refletindo memoria viva ativa como baseline do nucleo, `CHANGELOG.md` sincronizado e gate minimo validado.
- `gate_minimo`: `python tools/check_mojibake.py docs/implementation docs/operations HANDOFF.md CHANGELOG.md` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `impacto_no_baseline`: o lote fecha com backlog, handoff, snapshot e changelog coerentes com a nova gramatica soberana de review, compaction e recall cross-session.

### MB-077

- `id`: `MB-077`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `fluxo_principal`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: formalizar arbitragem mais declarativa de `mente -> dominio -> especialista` nos consumidores finais, com contrato explicito para cadeia autoritativa, override bounded e fallback governado.
- `justificativa_arquitetural`: depois de fechar capacidade soberana e manutencao ativa de memoria, o proximo ganho causal do nucleo e remover a arbitragem residual implicita na ultima milha de `planning`, `synthesis` e consumo final do runtime.
- `arquivos/servicos_principais`: `cognitive-engine`, `specialist-engine`, `engines/planning-engine`, `engines/synthesis-engine`, `services/orchestrator-service`
- `dependencias`: `MB-071`, `MB-076`
- `criterio_de_aceite`: `planning`, `synthesis`, `cognitive`, `specialist` e `orchestrator` passam a carregar um slice explicito de arbitragem `mind_domain_specialist`, distinguindo cadeia soberana, override permitido, degradacao bounded e fallback final, sem reintroduzir heuristica local nem quebrar governanca ou memoria canonica.
- `gate_minimo`: `pytest` direcionado dos services/engines tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: `cognitive`, `specialist`, `planning`, `synthesis` e `orchestrator` agora carregam `mind_domain_specialist_contract_*`, distinguindo cadeia autoritativa, override bounded e fallback governado como slice explicito do runtime.

### MB-078

- `id`: `MB-078`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `governanca`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: fazer consumidores finais, dispatch e framing aplicarem a arbitragem declarativa `mente -> dominio -> especialista` como politica soberana do runtime.
- `justificativa_arquitetural`: depois de formalizar o contrato, o passo seguinte e impedir que a cadeia autoritativa de mente, dominio e especialista se fragmente entre adapters, framing final e leituras locais do consumidor.
- `arquivos/servicos_principais`: `cognitive-engine`, `specialist-engine`, `engines/synthesis-engine`, `services/orchestrator-service`, `shared/domain_registry`
- `dependencias`: nenhuma
- `criterio_de_aceite`: consumidores finais e fluxo de dispatch passam a responder ao contrato de arbitragem `mind_domain_specialist`, com efeito observavel em selecao, framing, continuidade e fallback final, sem bypassar rota promovida ou especialista canonico.
- `gate_minimo`: `pytest` direcionado dos services/engines tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: `specialist-engine`, `operation_dispatch`, `operational-service`, `response_synthesized` e `workflow_*` agora aplicam `mind_domain_specialist` como politica soberana de selecao, consumo final, framing e fallback, priorizando o especialista canonico da rota ativa quando ele existe e contendo a ultima milha no nucleo quando o contrato pede fallback governado.

### MB-079

- `id`: `MB-079`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: tornar a arbitragem declarativa `mente -> dominio -> especialista` parte da evidencia auditavel do baseline em tracing, piloto e comparadores.
- `justificativa_arquitetural`: sem evidencia propria, a ultima milha da arbitragem pode parecer alinhada sem prova; o baseline precisa mostrar quando a cadeia ficou autoritativa, parcial, degradada ou em drift no consumidor final.
- `arquivos/servicos_principais`: `services/observability-service`, `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`
- `dependencias`: `MB-078`
- `criterio_de_aceite`: auditoria, piloto e comparadores passam a expor pelo menos `mind_domain_specialist_status`, efetividade da arbitragem final e mismatch entre cadeia autoritativa, framing e especialista efetivamente consumido ao longo do fluxo.
- `gate_minimo`: `pytest` direcionado dos services/tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: `observability`, piloto e comparadores agora expõem `mind_domain_specialist_effectiveness` e `mind_domain_specialist_mismatch_flags`, tornando a efetividade da arbitragem final e seus drifts parte formal e comparavel do baseline.

### MB-080

- `id`: `MB-080`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `evolucao`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fazer `refinement_vectors`, `evaluation_matrix` e leitura de release usarem efetividade e drift da arbitragem declarativa como insumo do proximo refinamento do nucleo.
- `justificativa_arquitetural`: depois de tornar a arbitragem observavel, o loop evolutivo precisa separar melhor quando o problema esta na mente dominante, na rota de dominio, no especialista consumido ou no framing final.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `tools/evolution_from_pilot.py`, `tools/compare_orchestrator_paths.py`, `tools/verify_release_signal_baseline.py`
- `dependencias`: `MB-079`
- `criterio_de_aceite`: `evolution-lab`, comparadores e verificadores passam a registrar mismatch, degradacao ou inefetividade da arbitragem declarativa em `refinement_vectors` e `evaluation_matrix`, sem automatizar promocao de mudanca ou dependencia externa.
- `gate_minimo`: `pytest` direcionado dos tools/servicos tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: a arbitragem `mente -> dominio -> especialista` passa a influenciar de forma formal a priorizacao do proximo ganho causal do nucleo.

### MB-081

- `id`: `MB-081`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar o lote de arbitragem declarativa com docs vivos, changelog e gate sincronizados ao novo estado real do baseline.
- `justificativa_arquitetural`: esse lote muda a leitura final do encadeamento `mente -> dominio -> especialista`; o fechamento precisa consolidar o contrato novo sem deixar backlog, handoff e snapshot em drift.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-077`, `MB-078`, `MB-079`, `MB-080`
- `criterio_de_aceite`: o lote termina com docs vivos refletindo arbitragem declarativa como baseline do nucleo, `CHANGELOG.md` sincronizado e gate minimo validado.
- `gate_minimo`: `python tools/check_mojibake.py docs/implementation docs/operations HANDOFF.md CHANGELOG.md` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `impacto_no_baseline`: o lote fecha com backlog, handoff, snapshot e changelog coerentes com a nova gramatica soberana da arbitragem `mente -> dominio -> especialista`.

### MB-082

- `id`: `MB-082`
- `prioridade`: `P0`
- `status`: `completed`
- `eixo_do_mestre`: `identidade`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: formalizar identidade, missao ativa e politica executiva por request como contrato soberano do runtime.
- `justificativa_arquitetural`: depois de fechar capacidade soberana, memoria viva e arbitragem declarativa, o proximo ganho causal do nucleo e explicitar a preflight executiva que ancora quem o JARVIS e em cada request, qual missao esta ativa, qual autoridade esta em jogo e que limites politicos devem moldar o fluxo.
- `arquivos/servicos_principais`: `engines/planning-engine`, `services/governance-service`, `services/orchestrator-service`, `shared/contracts`, `shared/schemas`
- `dependencias`: `MB-071`, `MB-081`
- `criterio_de_aceite`: `planning`, `governance` e `orchestrator` passam a carregar um slice explicito de `request_identity_policy`, distinguindo pelo menos missao ativa, postura executiva, autoridade, risco, reversibilidade e necessidade de confirmacao, sem expor internals na resposta final nem reintroduzir heuristica local espalhada.
- `gate_minimo`: `pytest` direcionado dos services/engines tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: identidade, missao e politica deixam de ser apenas pressuposto editorial e passam a existir como contrato auditavel do runtime por request.

### MB-083

- `id`: `MB-083`
- `prioridade`: `P0`
- `status`: `completed`
- `eixo_do_mestre`: `governanca`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: fazer planejamento, governanca e dispatch aplicarem o contrato `request_identity_policy` como politica soberana do runtime.
- `justificativa_arquitetural`: depois de formalizar o contrato, o passo seguinte e impedir que missao, identidade, confirmacao e limites de acao permaneçam distribuidos entre adapters, rationale textual e leitura implicita do fluxo.
- `arquivos/servicos_principais`: `engines/planning-engine`, `services/governance-service`, `services/orchestrator-service`, `services/operational-service`
- `dependencias`: `MB-082`
- `criterio_de_aceite`: o runtime passa a responder ao contrato `request_identity_policy` em composicao de plano, checkpoint de governanca, despacho e ultima milha operacional, com efeito observavel em contencao, prioridade de acao e confirmacao exigida, sem bypassar memoria canonica ou politica de capacidade.
- `gate_minimo`: `pytest` direcionado dos services/engines tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: missao ativa, autoridade e politica executiva passam a moldar o fluxo principal como criterio soberano, nao apenas como contexto implicito.

### MB-084

- `id`: `MB-084`
- `prioridade`: `P1`
- `status`: `completed`
- `eixo_do_mestre`: `observabilidade`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: tornar `request_identity_policy` parte da evidencia auditavel do baseline em tracing, piloto e comparadores.
- `justificativa_arquitetural`: sem evidencia propria, o checklist executivo por request pode parecer alinhado sem prova; o baseline precisa mostrar quando a missao foi materializada, quando a politica executiva foi aplicada corretamente e quando houve drift entre intencao, risco e acao.
- `arquivos/servicos_principais`: `services/observability-service`, `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`
- `dependencias`: `MB-083`
- `criterio_de_aceite`: auditoria, piloto e comparadores passam a expor pelo menos `request_identity_status`, `mission_policy_status` e mismatch entre missao ativa, autoridade, confirmacao exigida e comportamento final do fluxo.
- `gate_minimo`: `pytest` direcionado dos services/tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: identidade e politica executiva deixam de ser somente leitura conceitual e passam a existir como evidencia comparavel do runtime.

### MB-085

- `id`: `MB-085`
- `prioridade`: `P1`
- `status`: `completed`
- `eixo_do_mestre`: `evolucao`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fazer `refinement_vectors`, `evaluation_matrix` e leitura de release usarem drift e efetividade de `request_identity_policy` como insumo do proximo refinamento do nucleo.
- `justificativa_arquitetural`: depois de tornar o checklist executivo observavel, o loop evolutivo precisa separar melhor quando o problema esta em missao ativa mal materializada, politica executiva frouxa, confirmacao insuficiente ou contencao excessiva.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `tools/evolution_from_pilot.py`, `tools/compare_orchestrator_paths.py`, `tools/verify_release_signal_baseline.py`
- `dependencias`: `MB-084`
- `criterio_de_aceite`: `evolution-lab`, comparadores e verificadores passam a registrar mismatch, inefetividade ou excesso de contencao de `request_identity_policy` em `refinement_vectors` e `evaluation_matrix`, sem automatizar promocao de mudanca ou abrir autoedicao do nucleo.
- `gate_minimo`: `pytest` direcionado dos tools/servicos tocados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: identidade, missao e politica executiva passam a influenciar formalmente a priorizacao do proximo ganho causal do nucleo.

### MB-086

- `id`: `MB-086`
- `prioridade`: `P1`
- `status`: `completed`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar o lote de `request_identity_policy` com docs vivos, changelog e gate sincronizados ao novo estado real do baseline.
- `justificativa_arquitetural`: esse lote muda a leitura de identidade, missao e politica por request; o fechamento precisa consolidar o contrato novo sem deixar backlog, handoff, snapshot e changelog em drift.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-082`, `MB-083`, `MB-084`, `MB-085`
- `criterio_de_aceite`: o lote termina com docs vivos refletindo `request_identity_policy` como baseline do nucleo, `CHANGELOG.md` sincronizado e gate minimo validado.
- `gate_minimo`: `python tools/check_mojibake.py docs/implementation docs/operations HANDOFF.md CHANGELOG.md` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `impacto_no_baseline`: o lote fecha com backlog, handoff, snapshot e changelog coerentes com a nova gramatica soberana de identidade, missao e politica por request.

### MB-087

- `id`: `MB-087`
- `prioridade`: `P0`
- `status`: `completed`
- `eixo_do_mestre`: `evolucao`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: formalizar a gramatica soberana de `expanded_eval_scope` e `controlled_wave2_experiment` para capacidade, superficie e estado operacional do ecossistema, sem promover stack externa nem abrir superficie nova por inercia.
- `justificativa_arquitetural`: depois de consolidar contratos causais do nucleo, o proximo risco deixa de ser falta de sinal local e passa a ser falta de leitura comparavel para novas capacidades e experimentos controlados; o baseline precisa saber o que esta avaliando, por que um experimento pode entrar e quando ele deve sair sem virar promocao automatica.
- `arquivos/servicos_principais`: `tools/compare_orchestrator_paths.py`, `evolution/evolution-lab`, `tools/verify_release_signal_baseline.py`, `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`
- `dependencias`: `MB-086`
- `criterio_de_aceite`: comparadores, laboratorio e verificadores passam a compartilhar uma gramatica explicita para `expanded_eval_scope`, `wave2_candidate_class`, `experiment_entry_status`, `experiment_exit_status` e `promotion_readiness`, distinguindo capacidade, superficie e estado operacional sem reabrir heuristica solta.
- `gate_minimo`: `pytest` direcionado dos tools/servicos afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: o runtime passa a ter uma malha comparativa formal para dizer o que ainda e refinamento do nucleo e o que ja e experimento controlado de Onda 2.

### MB-088

- `id`: `MB-088`
- `prioridade`: `P0`
- `status`: `completed`
- `eixo_do_mestre`: `observabilidade`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: expandir tracing, piloto e comparadores para exporem cobertura e drift por `capability_surface_axis`, `ecosystem_state_axis` e `experiment_lane_status`.
- `justificativa_arquitetural`: `EV-002` so faz sentido se a observabilidade passar a separar claramente o que hoje e baseline do nucleo, o que e area de avaliacao expandida e o que ainda esta fora de escopo por fase; sem esse recorte, a leitura de experimentos continua misturada com telemetria geral.
- `arquivos/servicos_principais`: `services/observability-service`, `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`
- `dependencias`: `MB-087`
- `criterio_de_aceite`: auditoria, piloto e comparadores passam a publicar pelo menos `expanded_eval_status`, `surface_axis_status`, `ecosystem_state_status` e `experiment_lane_status`, deixando explicito quando um fluxo esta fora da lane controlada, quando esta apto a entrar nela e quando ainda nao tem cobertura suficiente.
- `gate_minimo`: `pytest` direcionado dos services/tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: capacidade, superficie e estado operacional deixam de ser leitura lateral e viram evidencia auditavel do baseline comparativo.

### MB-089

- `id`: `MB-089`
- `prioridade`: `P1`
- `status`: `completed`
- `eixo_do_mestre`: `evolucao`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: materializar a lane controlada da Onda 2 em `evolution-lab` e comparadores, com criterio formal de entrada, permanencia e saida para referencias candidatas.
- `justificativa_arquitetural`: `EV-004` existe para impedir hype e dispersao; o laboratorio precisa distinguir experimento elegivel, experimento em observacao, experimento reprovado e experimento ainda imaturo sem deixar isso virar promocao silenciosa de tecnologia externa.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `tools/evolution_from_pilot.py`, `tools/compare_orchestrator_paths.py`
- `dependencias`: `MB-088`
- `criterio_de_aceite`: o laboratorio e os comparadores passam a emitir `experiment_lane_decision`, `entry_criteria_refs`, `exit_criteria_refs`, `promotion_blockers` e recomendacao bounded por candidato, mantendo a Onda 2 subordinada aos sinais do nucleo.
- `gate_minimo`: `pytest` direcionado dos services/tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: a Onda 2 deixa de ser so matriz passiva de readiness e passa a ter lane controlada, sem perder a soberania do nucleo.

### MB-090

- `id`: `MB-090`
- `prioridade`: `P1`
- `status`: `completed`
- `eixo_do_mestre`: `gates/release`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: ligar a nova gramatica de eval expandida e experimentos controlados aos verificadores de release e aos fechadores regeneraveis do corte.
- `justificativa_arquitetural`: sem leitura de gate, a lane controlada continua sendo so artefato de laboratorio; o baseline precisa conseguir afirmar quando um experimento esta pronto para continuar como experimento, quando deve ser congelado e quando ainda nao pode contaminar a leitura de release.
- `arquivos/servicos_principais`: `tools/verify_release_signal_baseline.py`, `tools/verify_active_cut_baseline.py`, `tools/close_alignment_cycle.py`, `tools/close_sovereign_alignment_cut.py`
- `dependencias`: `MB-089`
- `criterio_de_aceite`: verificadores e fechadores passam a registrar `expanded_eval_readiness`, `experiment_release_status`, `promotion_blockers` e `wave2_lane_health` sem transformar release em mecanismo de promocao automatica.
- `gate_minimo`: `pytest` direcionado dos tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `impacto_no_baseline`: release e closure docs passam a distinguir maturacao do nucleo de experimento controlado de tecnologia externa.

### MB-091

- `id`: `MB-091`
- `prioridade`: `P1`
- `status`: `completed`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar o lote de evals expandidas e lane controlada da Onda 2 com docs vivos, changelog e gate sincronizados ao novo estado real do baseline.
- `justificativa_arquitetural`: esse lote muda a leitura do que e baseline soberano, o que e experimento controlado e o que continua fora de fase; o fechamento precisa consolidar essa fronteira sem deixar backlog, handoff, snapshot e changelog em drift.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-087`, `MB-088`, `MB-089`, `MB-090`
- `criterio_de_aceite`: o lote termina com docs vivos refletindo `EV-002` e `EV-004` como baseline comparativo controlado, `CHANGELOG.md` sincronizado e gate minimo validado.
- `gate_minimo`: `python tools/check_mojibake.py docs/implementation docs/operations HANDOFF.md CHANGELOG.md` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `impacto_no_baseline`: o lote fecha com a fronteira entre baseline soberano e experimento controlado formalizada nos docs vivos.

### MB-092

- `id`: `MB-092`
- `prioridade`: `P0`
- `status`: `concluido`
- `eixo_do_mestre`: `evolucao`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: formalizar a gramatica soberana de compile/optimize loops governados para prompts, planos e workflows, sem abrir autoedicao solta nem promocao automatica de mudanca.
- `justificativa_arquitetural`: depois de fechar evals expandidas e a lane controlada da Onda 2, o proximo ganho causal do baseline e transformar sinais comparativos e vetores de refinamento em contratos claros de oportunidade de otimizacao, bloqueio de seguranca e escopo elegivel, evitando que `EV-003` vire heuristica espalhada no laboratorio.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `tools/evolution_from_pilot.py`, `tools/compare_orchestrator_paths.py`, `shared/contracts`, `shared/schemas`
- `dependencias`: `MB-091`
- `criterio_de_aceite`: `evolution-lab`, comparadores e artefatos de piloto passam a compartilhar um slice explicito para `optimization_scope`, `optimization_target_kind`, `optimization_candidate_status`, `optimization_safety_status` e `optimization_blockers`, distinguindo prompt, plano e workflow como alvos governados de refinamento sem autorizar mudanca automatica de producao.
- `gate_minimo`: `pytest` direcionado dos services/tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: o sistema passa a ter contrato soberano para dizer o que e oportunidade real de compile/optimize loop e o que ainda e ruido comparativo.

### MB-093

- `id`: `MB-093`
- `prioridade`: `P0`
- `status`: `concluido`
- `eixo_do_mestre`: `evolucao`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: materializar `EV-003` em `evolution-lab` e `evolution_from_pilot`, fazendo traces, `evaluation_matrix` e `refinement_vectors` emitirem propostas bounded de otimizacao para prompts, planos e workflows.
- `justificativa_arquitetural`: depois de formalizar o contrato, o loop evolutivo precisa deixar de apenas apontar drift e passar a produzir candidatos governados de refinamento, com alvo, justificativa, criterio de seguranca e evidencias minimas por workflow.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `tools/evolution_from_pilot.py`, `tools/internal_pilot_support.py`
- `dependencias`: `MB-092`
- `criterio_de_aceite`: `evolution-lab` e `evolution_from_pilot` passam a emitir pelo menos propostas bounded por `prompt`, `plan` e `workflow`, com criterio de elegibilidade, blockers, refs de evidencia e recomendacao de acao sem autoaplicar mudanca no runtime.
- `gate_minimo`: `pytest` direcionado dos services/tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: o laboratorio deixa de ser apenas leitor de diferencas e passa a produzir candidatos governados de refinamento do nucleo.

### MB-094

- `id`: `MB-094`
- `prioridade`: `P1`
- `status`: `concluido`
- `eixo_do_mestre`: `observabilidade`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: tornar oportunidades, blockers e seguranca de otimizacao parte explicita da evidencia auditavel em comparadores, relatorios e baseline ativo.
- `justificativa_arquitetural`: sem observabilidade propria, compile/optimize loops ficam opacos e parecem autoaperfeicoamento sem prova; o baseline precisa mostrar onde ha oportunidade real, onde a seguranca bloqueia acao e onde o sinal ainda e insuficiente.
- `arquivos/servicos_principais`: `tools/compare_orchestrator_paths.py`, `tools/internal_pilot_report.py`, `tools/verify_active_cut_baseline.py`, `services/observability-service`
- `dependencias`: `MB-093`
- `criterio_de_aceite`: comparadores, relatorios e auditoria passam a expor pelo menos `optimization_candidate_status`, `optimization_safety_status`, `optimization_target_kind` e `optimization_blockers`, deixando explicito quando o runtime esta pronto para refinar, quando deve apenas observar e quando precisa congelar.
- `gate_minimo`: `pytest` direcionado dos services/tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: oportunidades de refinamento passam a ser evidencia comparavel e auditavel, e nao apenas leitura interna do laboratorio.

### MB-095

- `id`: `MB-095`
- `prioridade`: `P1`
- `status`: `concluido`
- `eixo_do_mestre`: `gates/release`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: ligar a nova gramatica de compile/optimize loops governados aos verificadores de release e aos fechadores regeneraveis do corte.
- `justificativa_arquitetural`: `EV-003` precisa influenciar leitura de baseline sem virar mecanismo de promocao automatica; release e closure docs devem distinguir candidato de otimizacao, risco de seguranca e recomendacao de congelamento.
- `arquivos/servicos_principais`: `tools/verify_release_signal_baseline.py`, `tools/verify_active_cut_baseline.py`, `tools/archive/close_alignment_cycle.py`, `tools/archive/close_sovereign_alignment_cut.py`
- `dependencias`: `MB-094`
- `criterio_de_aceite`: verificadores e fechadores passam a registrar `optimization_readiness`, `optimization_release_status`, `optimization_blockers` e `optimization_safety_status`, sem transformar gates em aplicadores automaticos de refinamento.
- `gate_minimo`: `pytest` direcionado dos tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: release e closure docs passam a distinguir drift, oportunidade governada de refinamento e bloqueio de seguranca no loop evolutivo.

### MB-096

- `id`: `MB-096`
- `prioridade`: `P1`
- `status`: `concluido`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar o lote de compile/optimize loops governados com docs vivos, changelog e gate sincronizados ao novo estado real do baseline.
- `justificativa_arquitetural`: esse lote muda a leitura do que o sistema ja consegue sugerir como refinamento governado do nucleo; o fechamento precisa consolidar essa fronteira sem deixar backlog, handoff, snapshot e changelog em drift.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-092`, `MB-093`, `MB-094`, `MB-095`
- `criterio_de_aceite`: o lote termina com docs vivos refletindo `EV-003` como baseline evolutivo governado, `CHANGELOG.md` sincronizado e gate minimo validado.
- `gate_minimo`: `python tools/check_mojibake.py docs/implementation docs/operations HANDOFF.md CHANGELOG.md` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4-mini`
- `impacto_no_baseline`: o lote fecha com a gramatica de compile/optimize loops governados materializada e documentada como parte do baseline evolutivo.

### MB-097

- `id`: `MB-097`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `estado_operacional`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: formalizar um contrato soberano minimo de estado operacional do ecossistema, distinguindo workflows ativos, artefatos vivos, checkpoints abertos, pendencias e superfícies associadas sem rebaixar isso a contexto textual solto.
- `justificativa_arquitetural`: depois de fechar o baseline evolutivo do `v2 restante`, o proximo ganho causal real e dar ao runtime uma nocao mais explicita do estado operacional que ele esta coordenando; sem isso, o JARVIS continua forte em request-response, mas fraco em continuidade operacional mais ampla.
- `arquivos/servicos_principais`: `services/orchestrator-service`, `services/operational-service`, `shared/contracts`, `shared/schemas`, `shared/events`
- `dependencias`: `MB-096`
- `criterio_de_aceite`: `orchestrator`, `operational-service` e contratos compartilhados passam a carregar pelo menos `ecosystem_state_status`, `active_work_items`, `active_artifact_refs`, `open_checkpoint_refs` e `surface_presence`, distinguindo ausencia de estado, estado parcial util e estado operacional coerente.
- `gate_minimo`: `pytest` direcionado dos services/tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: `OperationDispatchContract`, `OperationResultContract`, `orchestrator-service`, `operational-service` e eventos internos agora carregam `ecosystem_state_status`, `active_work_items`, `active_artifact_refs`, `open_checkpoint_refs` e `surface_presence` como gramatica minima de estado operacional do ecossistema.

### MB-098

- `id`: `MB-098`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `continuidade`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: aplicar o contrato de estado operacional do ecossistema em continuidade, memoria canonica e lifecycle de workflows ativos, sem abrir ainda memoria temporal/relacional rica.
- `justificativa_arquitetural`: o contrato de estado so gera valor se afetar recovery, missao ativa, artefatos em curso e resumabilidade bounded; esse passo traduz `SG-002` em comportamento real sem saltar para `TA-004`.
- `arquivos/servicos_principais`: `services/memory-service`, `shared/memory_registry.py`, `services/orchestrator-service`, `services/operational-service`
- `dependencias`: `MB-097`
- `criterio_de_aceite`: recovery, continuidade e workflow lifecycle passam a reconhecer work items e artefatos ativos do ecossistema como estado soberano, com retomada bounded e sem inventar memória temporal fora de fase.
- `gate_minimo`: `pytest` direcionado dos services/tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: continuidade deixa de depender apenas de missão e histórico conversacional e passa a enxergar estado operacional ativo do ecossistema.

### MB-099

- `id`: `MB-099`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: tornar o estado operacional do ecossistema auditavel em observabilidade, piloto, comparadores e baseline ativo.
- `justificativa_arquitetural`: sem evidência formal, `SG-002` vira apenas payload novo no runtime; o baseline precisa mostrar quando há ecossistema ativo coerente, quando ele está parcial e quando o sistema ainda não sustenta continuidade operacional.
- `arquivos/servicos_principais`: `services/observability-service`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`, `tools/verify_active_cut_baseline.py`
- `dependencias`: `MB-098`
- `criterio_de_aceite`: comparadores, relatorios e baseline passam a expor `ecosystem_state_status`, cobertura de `active_work_items`, `active_artifact_refs`, `open_checkpoint_refs` e `surface_presence`, distinguindo `not_applicable`, `partial_operational_state` e `operational_state_attached`.
- `gate_minimo`: `pytest` direcionado dos services/tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: `observability-service`, piloto, comparadores e baseline ativo agora expõem `operational_ecosystem_state_status`, `active_work_items`, `active_artifact_refs`, `open_checkpoint_refs` e `surface_presence` sem confundir esse slice com a eval expandida da Onda 2.

### MB-100

- `id`: `MB-100`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `gates/release`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: ligar o novo estado operacional do ecossistema aos verificadores de release, `evolution-lab` e fechadores regeneraveis, sem transformar isso em promoção automática de v3.
- `justificativa_arquitetural`: a ponte `v2 -> v3` precisa aparecer como readiness governada, não como mudança de fase implícita; os gates devem mostrar se o runtime já sustenta ecossistema operacional bounded ou se ainda precisa congelar.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `tools/evolution_from_pilot.py`, `tools/verify_release_signal_baseline.py`, `tools/archive/close_alignment_cycle.py`, `tools/archive/close_sovereign_alignment_cut.py`
- `dependencias`: `MB-099`
- `criterio_de_aceite`: gates, laboratório e fechadores passam a registrar `ecosystem_state_status` e readiness de estado operacional sem confundir esse slice com abertura automática de multissuperfície ou autonomia ampla.
- `gate_minimo`: `pytest` direcionado dos tools afetados, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: `evolution-lab`, `evolution_from_pilot`, verificador de release e fechadores regeneráveis agora registram readiness do estado operacional do ecossistema como evidência governada, sem promover multissuperfície ou autonomia ampla automaticamente.

### MB-101

- `id`: `MB-101`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar o lote de estado operacional do ecossistema com docs vivos, changelog e gate sincronizados ao novo estado real do baseline.
- `justificativa_arquitetural`: abrir a ponte `v2 -> v3` sem sincronizar backlog, snapshot e handoff gera drift semântico; o fechamento precisa explicitar que `SG-002` foi aberto como recorte bounded e que `SG-003`/`SO-002` continuam dependentes desse baseline.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-097`, `MB-098`, `MB-099`, `MB-100`
- `criterio_de_aceite`: o lote termina com docs vivos refletindo a abertura controlada da ponte `v2 -> v3`, `CHANGELOG.md` sincronizado e gate minimo validado.
- `gate_minimo`: `python tools/check_mojibake.py docs/implementation docs/operations HANDOFF.md CHANGELOG.md` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4-mini`
- `impacto_no_baseline`: o lote `MB-097` a `MB-101` fica fechado como ponte bounded de `SG-002` + `TA-002`; a repriorizacao macro seguinte abriu `SG-003`/`SO-002` apenas como contrato minimo em `MB-102` a `MB-106`.

### MB-102

- `id`: `MB-102`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `identidade/superficies`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: formalizar um contrato soberano minimo de identidade e continuidade por superficie para console, API, web futura, voz futura e operadores humanos, sem criar gateways externos nem nova UI ampla.
- `justificativa_arquitetural`: `SG-003` so deve abrir depois do estado operacional bounded existir; agora o proximo risco e a mesma entidade parecer diferente em cada canal. O primeiro passo precisa ser contrato, nao interface nova.
- `arquivos/servicos_principais`: `shared/contracts`, `shared/schemas`, `shared/events`, `apps/jarvis_console`
- `dependencias`: `MB-101`
- `criterio_de_aceite`: contratos compartilhados passam a carregar pelo menos `surface_id`, `surface_kind`, `surface_session_id`, `surface_capability_scope`, `operator_identity_ref`, `canonical_user_ref` e `surface_continuity_status`, distinguindo `single_surface`, `linked_surface` e `surface_identity_conflict`.
- `gate_minimo`: `pytest` direcionado de `shared`, `apps/jarvis_console` e `services/orchestrator-service`, `ruff` direcionado e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: `SurfaceIdentityContract`, `InputContract`, `OperationDispatchContract`, `OperationResultContract`, schemas, eventos e console agora carregam identidade minima de superficie (`surface_*`, operador e usuario canonico), sem promover voz, web rica, API publica ou gateway externo.

### MB-103

- `id`: `MB-103`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `orquestracao/superficies`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: aplicar o contrato de superficie no console atual, no input recebido e no `orchestrator-service`, fazendo a superficie ativa acompanhar request, dispatch, workflow e resposta final.
- `justificativa_arquitetural`: o contrato de superficie so vira comportamento real quando o runtime consegue responder "de qual superficie veio, qual identidade canonica representa e qual continuidade ela pode compartilhar" sem heuristica local.
- `arquivos/servicos_principais`: `apps/jarvis_console`, `services/orchestrator-service`, `engines/planning-engine`, `engines/synthesis-engine`, `shared/events`
- `dependencias`: `MB-102`
- `criterio_de_aceite`: eventos `input_received`, `workflow_composed`, `operation_dispatched`, `response_synthesized` e `memory_recorded` carregam o mesmo slice `surface_*`, preservando `through_core_only`, sem duplicar identidade entre console e futuras superficies.
- `gate_minimo`: `pytest` direcionado de `apps/jarvis_console`, `services/orchestrator-service`, `engines/planning-engine`, `engines/synthesis-engine` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: `surface_*` agora acompanha console, `input_received`, `workflow_composed`, `operation_dispatched`, `response_synthesized`, `memory_recorded`, planning context e synthesis input no runtime atual, preservando `through_core_only`.

### MB-104

- `id`: `MB-104`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `memoria/continuidade`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: persistir e recuperar continuidade de superficie em `memory-service`, `session_continuity`, checkpoints e replay, sem abrir memoria temporal rica nem grafo relacional amplo.
- `justificativa_arquitetural`: multissuperficie segura depende de continuidade compartilhada, mas a fase atual ainda deve manter memoria bounded. O escopo e vincular superficies a sessao/missao canonica, nao reconstruir historico total.
- `arquivos/servicos_principais`: `services/memory-service`, `shared/memory_registry.py`, `services/orchestrator-service`
- `dependencias`: `MB-103`
- `criterio_de_aceite`: continuidade e replay passam a registrar superficies vinculadas, superficie ativa, ultima superficie conhecida e conflito de identidade de superficie, com recovery bounded e sem expor estado de uma superficie a outra sem identidade canonica coerente.
- `gate_minimo`: `pytest` direcionado de `services/memory-service`, `services/orchestrator-service`, `shared/memory_registry.py` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: `memory-service`, `session_continuity`, `continuity_checkpoint`, `continuity_replay`, `mission_state` e `mission_runtime_state` agora persistem e recuperam superficies vinculadas, superficie ativa, ultima superficie conhecida e flags de conflito de identidade.

### MB-105

- `id`: `MB-105`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade/gates`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: tornar continuidade de superficie auditavel em observabilidade, piloto, comparadores, baseline ativo, `evolution-lab` e verificadores de release.
- `justificativa_arquitetural`: sem evidencia formal, multissuperficie vira risco de identidade duplicada. Os gates precisam mostrar quando uma superficie esta isolada, vinculada ou em conflito antes de qualquer expansao de UI/canal.
- `arquivos/servicos_principais`: `services/observability-service`, `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`, `tools/verify_active_cut_baseline.py`, `evolution/evolution-lab`, `tools/evolution_from_pilot.py`, `tools/verify_release_signal_baseline.py`
- `dependencias`: `MB-104`
- `criterio_de_aceite`: auditoria, relatorios, comparadores e release passam a expor `surface_continuity_status`, `linked_surface_count`, `surface_identity_conflict_flags` e readiness de multissuperficie sem transformar isso em promocao automatica de voz, web ou API publica.
- `gate_minimo`: `pytest` direcionado dos services/tools afetados, `python tools/verify_release_signal_baseline.py` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: a ponte multissuperficie ganha leitura comparavel e gateada antes de virar interface ampla.

### MB-106

- `id`: `MB-106`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar o lote de continuidade multissuperficie minima com docs vivos, changelog, snapshot e backlog macro sincronizados ao novo estado real.
- `justificativa_arquitetural`: `SO-002` nao pode ficar ambiguo entre contrato de identidade e abertura ampla de produto; o fechamento precisa explicitar que o lote abriu apenas a camada soberana minima de superficies.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-102`, `MB-103`, `MB-104`, `MB-105`
- `criterio_de_aceite`: docs vivos refletem `SG-003` + `SO-002` como contrato minimo de continuidade multissuperficie, mantendo `SO-001`, `SO-003`, `TA-004`, `TA-006` e verticais `deferred` fora de fase ate nova decisao explicita.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4-mini`
- `impacto_no_baseline`: o lote termina com a identidade multissuperficie minima registrada como ponte governada para `v3`, sem contaminar a fila com interfaces amplas; a fila micro volta a ficar sem item `ready` ate nova repriorizacao explicita.

### MB-107

- `id`: `MB-107`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `governanca/backlog`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: selecionar explicitamente o proximo candidato macro depois do fechamento `MB-102` a `MB-106`, usando `unified-gap-and-absorption-backlog.md` como fonte soberana e sem abrir superficie ampla por inercia.
- `justificativa_arquitetural`: depois de um lote de ponte `v2 -> v3`, o risco principal e confundir maturidade minima de contrato com autorizacao para produto/canal amplo. A proxima fila tecnica precisa nascer de uma decisao pequena, registrada e reversivel.
- `arquivos/servicos_principais`: `docs/implementation/unified-gap-and-absorption-backlog.md`, `docs/implementation/execution-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-106`
- `criterio_de_aceite`: o backlog macro registra a decisao de abrir `SO-003` apenas como recorte minimo de projetos/objetivos persistentes, a fila micro explicita qual frente sera convertida em lote tecnico seguinte, e as exclusoes de fase (`SO-001`, `TA-004`, `TA-006`, `DV-*`, `RH-*`) permanecem visiveis.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4-mini`
- `impacto_no_baseline`: registra `SO-003` como proxima frente tecnica em recorte minimo de continuidade de projetos, objetivos, work items, checkpoints e artefatos vivos, sem abrir autonomia ampla.

### MB-108

- `id`: `MB-108`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `governanca/backlog`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: transformar a decisao de `MB-107` em um lote tecnico curto, com itens reais, arquivos principais, criterios de aceite, gates e apenas um item `ready`.
- `justificativa_arquitetural`: a repriorizacao so protege o nucleo se virar backlog executavel com contratos claros. Este item impede que a decisao macro fique solta ou que uma frente grande entre sem fatiamento.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-107`
- `criterio_de_aceite`: existe um novo lote tecnico numerado apos `MB-109`, com WIP `ready` unico, dependencias claras, modelos recomendados, modos de raciocinio, gates minimos e escopo limitado ao candidato escolhido em `MB-107`.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4-mini`
- `impacto_no_baseline`: converte `SO-003` em lote micro `MB-110` a `MB-114`, com `MB-110` como unico item `ready`.

### MB-109

- `id`: `MB-109`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar documentalmente a fila de repriorizacao `MB-107` a `MB-109`, deixando o lote tecnico seguinte pronto para implementacao e o historico vivo sincronizado.
- `justificativa_arquitetural`: cada troca de fila precisa preservar continuidade operacional para que o proximo agente saiba onde o sistema esta e por que frentes fora de fase continuam bloqueadas.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-107`, `MB-108`
- `criterio_de_aceite`: docs vivos registram a decisao, o lote tecnico aberto, o primeiro item `ready`, as exclusoes de fase e o gate executado; `EV-001` deixa de ser pendencia macro solta.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4-mini`
- `impacto_no_baseline`: fecha a repriorizacao `EV-001`; a fila volta a carregar um proximo passo tecnico claro em `MB-110` sem expandir superficie, memoria temporal rica ou substrate operacional amplo antes de fase.

### MB-110

- `id`: `MB-110`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `projetos/objetivos`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: formalizar contrato soberano minimo para projetos, objetivos persistentes, work items, checkpoints e artefatos vivos, sem abrir execucao autonoma longa nem produto multicanal amplo.
- `justificativa_arquitetural`: depois de estado operacional e continuidade por superficie, a maior lacuna de utilidade para operador humano e o JARVIS manter objetivos vivos, saber o que esta em andamento e apontar o proximo passo sem depender de memoria solta de chat.
- `arquivos/servicos_principais`: `shared/contracts`, `shared/schemas`, `shared/events`, `services/orchestrator-service`, `services/operational-service`
- `dependencias`: `MB-109`
- `criterio_de_aceite`: contratos compartilhados passam a representar `project_ref`, `objective_ref`, `work_item_refs`, `checkpoint_refs`, `artifact_refs`, `objective_status` e `next_action_ref` como slice minimo governado, com estados bounded como `active`, `paused`, `blocked`, `completed` e `requires_operator_decision`.
- `gate_minimo`: `pytest` direcionado de `shared`, `services/orchestrator-service`, `services/operational-service` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: `SO-003` agora tem contrato minimo em `shared/contracts`, `shared/schemas` e `shared/events`, incluindo `objective_state_declared`.
- `evidencia_de_fechamento`: coberto por `tests/unit/test_shared_layer.py`, `services/orchestrator-service/tests/test_orchestrator_service.py`, `services/operational-service/tests/test_operational_service.py`.

### MB-111

- `id`: `MB-111`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `orquestracao/projetos`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: propagar o contrato de projeto/objetivo pelo runtime atual, conectando input, workflow, dispatch, operacao, sintese e eventos sem criar scheduler autonomo.
- `justificativa_arquitetural`: o contrato so melhora utilidade se aparecer no caminho operacional real; ele precisa acompanhar request, plano, decisao e resposta final como contexto governado, nao como metadata documental.
- `arquivos/servicos_principais`: `services/orchestrator-service`, `engines/planning-engine`, `engines/synthesis-engine`, `services/operational-service`, `shared/events`
- `dependencias`: `MB-110`
- `criterio_de_aceite`: eventos centrais e contratos de runtime carregam o mesmo slice `project/objective/work_item/checkpoint/artifact`, preservando `through_core_only`, sem agendamento autonomo, sem bypass de governanca e sem transformar artefatos em tarefas autoexecutaveis.
- `gate_minimo`: `pytest` direcionado de `services/orchestrator-service`, `engines/planning-engine`, `engines/synthesis-engine`, `services/operational-service` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: projetos e objetivos atravessam input, planning, dispatch, operational result, synthesis input e eventos centrais sem scheduler autonomo.
- `evidencia_de_fechamento`: `workflow_composed`, `objective_state_declared`, `operation_dispatched`, `operation_completed`, `workflow_completed`, `response_synthesized` e `memory_recorded` carregam o slice de continuidade.

### MB-112

- `id`: `MB-112`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `memoria/projetos`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: persistir e recuperar continuidade bounded de projetos/objetivos em memoria, checkpoints e replay, sem abrir memoria temporal rica, grafo relacional amplo ou agente de tarefas longas.
- `justificativa_arquitetural`: a utilidade para o operador depende de retomada confiavel. O sistema precisa saber quais objetivos e work items estao ativos, bloqueados ou pausados antes de tentar automacao mais forte.
- `arquivos/servicos_principais`: `services/memory-service`, `shared/memory_registry.py`, `services/orchestrator-service`
- `dependencias`: `MB-111`
- `criterio_de_aceite`: `memory-service`, continuidade, checkpoint e replay registram objetivos ativos, work items, artefatos, checkpoints e proxima acao bounded, com recovery seguro e sem misturar projetos sem identidade canonica coerente.
- `gate_minimo`: `pytest` direcionado de `services/memory-service`, `services/orchestrator-service`, `shared/memory_registry.py` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: `memory-service` persiste e recupera projeto, objetivo, work items, checkpoints, artefatos, status e proxima acao em continuidade de sessao, estado de missao, checkpoint e replay.
- `evidencia_de_fechamento`: `services/memory-service/tests/test_memory_service.py::test_memory_service_recovers_bounded_ecosystem_state_for_continuity`.

### MB-113

- `id`: `MB-113`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade/gates`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: tornar projetos/objetivos auditaveis em observabilidade, piloto, comparadores, baseline ativo, `evolution-lab` e release.
- `justificativa_arquitetural`: sem evidencia comparavel, objetivos persistentes viram promessa invisivel. Os gates precisam mostrar cobertura, bloqueios, retomada e proxima acao antes de qualquer autonomia mais ampla.
- `arquivos/servicos_principais`: `services/observability-service`, `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`, `tools/verify_active_cut_baseline.py`, `evolution/evolution-lab`, `tools/evolution_from_pilot.py`, `tools/verify_release_signal_baseline.py`
- `dependencias`: `MB-112`
- `criterio_de_aceite`: auditoria, relatorios, comparadores e release expoem `objective_continuity_status`, `active_work_item_count`, `open_checkpoint_count`, `artifact_continuity_status`, `next_action_status` e blockers sem promover autoexecucao.
- `gate_minimo`: `pytest` direcionado dos services/tools afetados, `python tools/verify_release_signal_baseline.py` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: continuidade de projetos ganha leitura auditavel por `objective_continuity_status`, contagens de work items/checkpoints, estado de artefato e prontidao de proxima acao.
- `evidencia_de_fechamento`: `services/observability-service/tests/test_observability_service.py::test_observability_service_audits_project_objective_continuity_signals`, `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`.

### MB-114

- `id`: `MB-114`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar o lote minimo de projetos/objetivos persistentes com docs vivos, changelog, snapshot e backlog macro sincronizados ao novo estado real.
- `justificativa_arquitetural`: `SO-003` precisa permanecer contido como fundacao de continuidade de objetivos; o fechamento deve explicitar que tarefas longas, automacao ampla, browser/computer use e produto multicanal continuam fora de fase.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-110`, `MB-111`, `MB-112`, `MB-113`
- `criterio_de_aceite`: docs vivos refletem `SO-003` como contrato minimo de continuidade de projetos/objetivos, mantendo `SO-001`, `TA-004`, `TA-006`, `DV-*` e `RH-*` fora de fase ate nova decisao explicita.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4-mini`
- `impacto_no_baseline`: o lote fecha projetos/objetivos persistentes como ponte governada para utilidade operacional, sem abrir autonomia ampla.
- `evidencia_de_fechamento`: backlog, handoff, snapshot, changelog e backlog macro sincronizados nesta rodada.

---

### MB-115

- `id`: `MB-115`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `operacao/objetivos`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: expor no console o estado persistido de um objetivo/projeto por `mission_id`, incluindo projeto, objetivo, status, work items, checkpoints, artefatos e proxima acao.
- `justificativa_arquitetural`: depois de `MB-110` a `MB-114`, a informacao ja existe no runtime, mas ainda precisava aparecer para o operador humano sem depender de leitura interna de banco ou logs.
- `arquivos/servicos_principais`: `apps/jarvis_console`, `services/memory-service`
- `dependencias`: `MB-114`
- `criterio_de_aceite`: `jarvis-console objectives --mission-id ...` mostra o estado de objetivo persistido sem executar acao, sem escrever memoria e sem bypassar o nucleo.
- `gate_minimo`: `pytest apps/jarvis_console/tests/test_console.py` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4-mini`
- `impacto_no_baseline`: o operador passa a conseguir consultar o estado operacional minimo de projetos/objetivos pelo console.
- `evidencia_de_fechamento`: `apps/jarvis_console/tests/test_console.py::test_console_objectives_shows_persisted_project_objective_state`.

### MB-116

- `id`: `MB-116`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `operacao/objetivos`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `strategic_direction_workflow`, `software_change_workflow`
- `micro_objetivo`: adicionar comandos operacionais bounded para retomar, pausar, bloquear, concluir e redefinir proxima acao de um objetivo, sempre passando por governanca e persistencia canonica.
- `justificativa_arquitetural`: consultar objetivos melhora visibilidade, mas o operador precisa conseguir conduzir o estado sem editar banco, docs ou memoria manualmente.
- `arquivos/servicos_principais`: `apps/jarvis_console`, `services/orchestrator-service`, `services/memory-service`, `services/governance-service`
- `dependencias`: `MB-115`
- `criterio_de_aceite`: comandos de transicao de objetivo exigem `mission_id`, registram evento auditavel, preservam `through_core_only`, recusam transicao insegura e atualizam memoria de forma reversivel.
- `gate_minimo`: `pytest apps/jarvis_console/tests services/memory-service/tests services/orchestrator-service/tests/test_orchestrator_service.py` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: objetivos deixam de ser apenas consultaveis e passam a ser conduzidos pelo operador com trilha governada.
- `evidencia_de_fechamento`: `apps/jarvis_console/tests/test_console.py::test_console_objective_pause_updates_state_through_governed_core`, `apps/jarvis_console/tests/test_console.py::test_console_objective_blocks_unsafe_terminal_resume`.

### MB-117

- `id`: `MB-117`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `sintese/operacao`
- `workflow_profile_afetado`: `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`, `strategic_direction_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: fazer a sintese final expor, quando houver objetivo ativo, estado atual, proxima acao, decisao pendente e artefato relevante em linguagem operacional.
- `justificativa_arquitetural`: o operador nao deve precisar abrir debug ou comando separado para entender o que mudou em uma rodada quando o objetivo ativo foi afetado.
- `arquivos/servicos_principais`: `engines/synthesis-engine`, `services/orchestrator-service`, `apps/jarvis_console`
- `dependencias`: `MB-116`
- `criterio_de_aceite`: respostas finais com objetivo ativo incluem resumo operacional bounded sem vazar detalhes internos de especialistas nem promover autoexecucao.
- `gate_minimo`: `pytest engines/synthesis-engine/tests services/orchestrator-service/tests apps/jarvis_console/tests` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: a utilidade de projetos/objetivos passa a aparecer no fluxo normal da conversa.
- `evidencia_de_fechamento`: `engines/synthesis-engine/tests/test_synthesis_engine.py::test_synthesis_engine_surfaces_bounded_objective_state`, `apps/jarvis_console/tests/test_console.py::test_console_ask_surfaces_active_objective_state_in_final_synthesis`.

### MB-118

- `id`: `MB-118`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade/utilidade`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: auditar utilidade operacional de objetivos: objetivo consultado, retomado, pausado, bloqueado, concluido, sem proxima acao ou sem artefato associado.
- `justificativa_arquitetural`: a evolucao futura precisa saber se a camada de objetivos esta ajudando o operador, nao apenas se tecnicamente existe.
- `arquivos/servicos_principais`: `services/observability-service`, `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`
- `dependencias`: `MB-117`
- `criterio_de_aceite`: auditoria e relatorios expoem sinais de utilidade de objetivos sem transformar sucesso local em promocao automatica de autonomia.
- `gate_minimo`: `pytest services/observability-service/tests tests/unit apps/jarvis_console/tests` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: o sistema passa a medir se a camada operacional humana realmente reduz friccao.
- `evidencia_de_fechamento`: `services/observability-service/tests/test_observability_service.py::test_observability_service_audits_objective_operational_utility_signals`, `tests/unit/test_internal_pilot_report.py::test_internal_pilot_report_renders_text`, `tests/unit/test_compare_orchestrator_paths.py::test_compare_results_flags_objective_utility_mismatch_fields`.

### MB-119

- `id`: `MB-119`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar o lote de utilidade operacional de objetivos com docs vivos, changelog, snapshot, handoff e gates sincronizados.
- `justificativa_arquitetural`: a camada de objetivos deve permanecer contida como assistencia operacional governada, sem virar scheduler autonomo ou produto multicanal por inercia.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `docs/implementation/v2-adherence-snapshot.md`, `HANDOFF.md`, `CHANGELOG.md`
- `dependencias`: `MB-115`, `MB-116`, `MB-117`, `MB-118`
- `criterio_de_aceite`: docs vivos refletem o novo estado utilizavel para operador e deixam claro que autoexecucao longa, voz, web, API publica e browser/computer use continuam fora de fase.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4-mini`
- `impacto_no_baseline`: fecha a primeira camada realmente consultavel de objetivos/projetos para operador humano.
- `evidencia_de_fechamento`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`.

### MB-120

- `id`: `MB-120`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `evolucao/absorcao_tecnologica`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: abrir a repriorizacao explicita pos-`MB-119` escolhendo estrutura evolutiva e absorcao tecnologica governada como proxima frente, sem abrir scheduler autonomo, voz, web, API publica ou browser/computer use amplo.
- `justificativa_arquitetural`: a camada de objetivos ficou utilizavel para o operador, mas a visao de sistema autoevolutivo exige agora uma gramatica mais forte para candidatos tecnologicos, experimentos e promocao manual baseada em evidencia.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `docs/architecture/documento_evolutivo_jarvis.md`, `HANDOFF.md`
- `dependencias`: `MB-119`
- `criterio_de_aceite`: a fila micro registra a decisao da frente, explicita limites de fase e abre um lote pequeno com contratos, laboratorio, observabilidade e fechamento documental.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: a proxima rodada passa a mirar o loop evolutivo e a absorcao tecnologica governada, nao novas superficies ou autonomia ampla.
- `evidencia_de_fechamento`: fila `MB-120` a `MB-124` aberta com `MB-122` como proximo item `ready`.

### MB-121

- `id`: `MB-121`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `evolucao/absorcao_tecnologica`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `software_change_workflow`, `governance_boundary_workflow`
- `micro_objetivo`: criar contrato e gramatica minima para candidato de absorcao tecnologica, incluindo classe de absorcao, hipotese, evidencias, testes, rollback, papel subordinado e bloqueadores de soberania.
- `justificativa_arquitetural`: o sistema precisa absorver estado da arte continuamente, mas nenhuma tecnologia externa pode virar cerebro real por atalho; o primeiro passo e tornar cada candidato classificavel e auditavel.
- `arquivos/servicos_principais`: `shared/contracts`, `shared/schemas`, `shared/technology_absorption.py`, `tests/unit`
- `dependencias`: `MB-120`
- `criterio_de_aceite`: candidatos podem ser classificados como referencia, experimento, complemento controlado ou traducao promovivel; tentativa de assumir papel de nucleo e bloqueada; promocao so chega a revisao manual com evidencia, testes e rollback.
- `gate_minimo`: `pytest tests/unit/test_technology_absorption.py tests/unit/test_shared_layer.py` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: absorcao tecnologica deixa de ser apenas leitura documental e passa a ter contrato soberano minimo no codigo.
- `evidencia_de_fechamento`: `tests/unit/test_technology_absorption.py` e `tests/unit/test_shared_layer.py::test_technology_absorption_candidate_contract_is_subordinate_by_default`.

### MB-122

- `id`: `MB-122`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `evolucao/absorcao_tecnologica`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `software_change_workflow`, `governance_boundary_workflow`
- `micro_objetivo`: fazer o `evolution-lab` registrar candidatos tecnologicos usando a nova gramatica, preservando `sandbox-only`, promocao manual e rollback obrigatorio.
- `justificativa_arquitetural`: o contrato isolado e necessario, mas o loop evolutivo so passa a usar isso quando o laboratorio conseguir transformar tecnologia observada em candidato persistido e comparavel.
- `arquivos/servicos_principais`: `evolution/evolution-lab/src/evolution_lab/service.py`, `evolution/evolution-lab/tests/test_evolution_lab_service.py`
- `dependencias`: `MB-121`
- `criterio_de_aceite`: o laboratorio cria proposta de absorcao tecnologica com `strategy_context` contendo readiness, blockers, classe de absorcao e restricoes de promocao, sem promover automaticamente.
- `gate_minimo`: `pytest evolution/evolution-lab/tests/test_evolution_lab_service.py tests/unit/test_technology_absorption.py` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: `evolution-lab` agora registra candidato tecnologico como proposta `sandbox-only`, com readiness, blockers, matriz e politica de promocao manual.
- `evidencia_de_fechamento`: `evolution/evolution-lab/tests/test_evolution_lab_service.py::test_evolution_lab_registers_governed_technology_absorption_candidate`, `evolution/evolution-lab/tests/test_evolution_lab_service.py::test_evolution_lab_blocks_technology_candidate_that_requests_core_role`.

### MB-123

- `id`: `MB-123`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade/evolucao`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `software_change_workflow`, `governance_boundary_workflow`
- `micro_objetivo`: expor sinais de absorcao tecnologica em observabilidade, piloto interno, relatorio e comparador, distinguindo referencia, candidato em sandbox, bloqueio por soberania e revisao manual.
- `justificativa_arquitetural`: candidatos tecnologicos sem telemetria viram backlog especulativo; o operador precisa ver se a absorcao esta segura, util e ainda subordinada ao nucleo.
- `arquivos/servicos_principais`: `services/observability-service`, `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`
- `dependencias`: `MB-122`
- `criterio_de_aceite`: relatorios e comparacoes carregam readiness de absorcao sem confundir experimento controlado com promocao.
- `gate_minimo`: `pytest services/observability-service/tests tests/unit` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: observabilidade, piloto interno, relatorio e comparador agora carregam sinais de absorcao tecnologica, incluindo readiness, decisao, blockers, candidatos e exigencia de revisao manual.
- `evidencia_de_fechamento`: `services/observability-service/tests/test_observability_service.py::test_observability_service_audits_technology_absorption_signals`, `tests/unit/test_internal_pilot_report.py::test_internal_pilot_report_renders_text`, `tests/unit/test_compare_orchestrator_paths.py::test_compare_results_flags_technology_absorption_mismatch_fields`.

### MB-124

- `id`: `MB-124`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `operacao/evolucao`
- `workflow_profile_afetado`: `operational_readiness_workflow`
- `micro_objetivo`: expor no console leitura read-only dos candidatos tecnologicos recentes, seus bloqueadores, evidencias e proxima decisao humana.
- `justificativa_arquitetural`: a absorcao tecnologica precisa ser operavel pelo humano, nao apenas escondida no laboratorio.
- `arquivos/servicos_principais`: `apps/jarvis_console`, `evolution/evolution-lab`, `tests`
- `dependencias`: `MB-122`, `MB-123`
- `criterio_de_aceite`: operador consegue consultar candidatos sem promover, alterar ou executar experimento automaticamente.
- `gate_minimo`: `pytest apps/jarvis_console/tests evolution/evolution-lab/tests tests/unit` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4-mini`
- `impacto_no_baseline`: o operador passa a consultar candidatos tecnologicos recentes pelo console em modo read-only, sem promocao, execucao ou alteracao de estado.
- `evidencia_de_fechamento`: `apps/jarvis_console/tests/test_console.py::test_console_technology_candidates_shows_recent_absorption_candidate`.

### MB-125

- `id`: `MB-125`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar documentalmente o lote de absorcao tecnologica governada com changelog, handoff, snapshot, backlog macro e gates sincronizados.
- `justificativa_arquitetural`: a camada evolutiva deve permanecer governada e auditable; docs vivas precisam deixar claro o que foi aberto e o que continuou fora de fase.
- `arquivos/servicos_principais`: `CHANGELOG.md`, `HANDOFF.md`, `docs/implementation/*`, `docs/architecture/*`
- `dependencias`: `MB-122`, `MB-123`, `MB-124`
- `criterio_de_aceite`: documentos registram contrato, laboratorio, observabilidade e superficie read-only, mantendo autoedicao, autopromocao, pesos de modelo e autonomia ampla fora de fase.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4-mini`
- `impacto_no_baseline`: o lote `MB-120` a `MB-125` fecha a primeira camada operacional de absorcao tecnologica governada.
- `evidencia_de_fechamento`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`.

### MB-126

- `id`: `MB-126`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `evolucao/experiencia`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: abrir a repriorizacao explicita pos-`MB-125`, escolhendo experiencia operacional e reflexao pos-tarefa governada como proxima frente micro.
- `justificativa_arquitetural`: depois de objetivos persistentes e absorcao tecnologica governada, o proximo passo evolutivo correto e fazer o JARVIS aprender com missoes reais de forma auditavel, sem autoedicao, autopromocao ou autonomia ampla.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `docs/architecture/documento_evolutivo_jarvis.md`, `HANDOFF.md`
- `dependencias`: `MB-125`
- `criterio_de_aceite`: fila micro registra a frente escolhida, explicita que `TA-004`, `TA-006`, voz, web, API publica, scheduler autonomo e self-modification continuam fora de fase, e abre um lote curto com contrato, persistencia, proposta evolutiva, observabilidade e fechamento documental.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: a proxima rodada passa a mirar experiencia/reflexao pos-tarefa como materia-prima governada de autoevolucao, em vez de abrir nova superficie ou automacao ampla.
- `evidencia_de_fechamento`: fila `MB-126` a `MB-131` aberta com `MB-127` como proximo item `ready`.

### MB-127

- `id`: `MB-127`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `evolucao/experiencia`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `strategic_direction_workflow`, `software_change_workflow`, `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`
- `micro_objetivo`: criar contratos compartilhados para `experience_record` e `post_task_reflection`, registrando missao, objetivo, workflow, sinais usados, resultado, falhas, decisoes, aprendizado candidato e recomendacao de proxima acao.
- `justificativa_arquitetural`: autoevolucao governada precisa de materia-prima estruturada; sem um contrato de experiencia, o laboratorio so ve sinais soltos e nao consegue distinguir aprendizado real de telemetria dispersa.
- `arquivos/servicos_principais`: `shared/contracts`, `shared/schemas`, `shared/events`, `tests/unit`
- `dependencias`: `MB-126`
- `criterio_de_aceite`: contratos validam experiencia/reflexao sem permitir mutacao automatica do nucleo, exigem origem, outcome, evidence refs, falhas, recomendacao bounded, rollback quando houver proposta de mudanca e status manual para promocao.
- `gate_minimo`: `pytest tests/unit/test_experience_reflection.py tests/unit/test_shared_layer.py` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: experiencia operacional passa a ter contrato soberano minimo para virar insumo evolutivo auditavel.
- `evidencia_de_fechamento`: `tests/unit/test_experience_reflection.py::test_experience_reflection_contracts_are_manual_review_only`, `tests/unit/test_shared_layer.py::test_experience_reflection_contracts_are_shared_schemas`.

### MB-128

- `id`: `MB-128`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `memoria/evolucao`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `strategic_direction_workflow`, `software_change_workflow`
- `micro_objetivo`: persistir e recuperar registros de experiencia/reflexao como memoria evolutiva bounded, associada a missao, objetivo, superficie e workflow sem abrir memoria temporal relacional rica.
- `justificativa_arquitetural`: o sistema precisa reusar aprendizados de missoes anteriores, mas isso deve entrar primeiro como registro bounded e canonico, nao como grafo temporal amplo ou memoria externa dominante.
- `arquivos/servicos_principais`: `services/memory-service`, `shared/memory_registry.py`, `tests`
- `dependencias`: `MB-127`
- `criterio_de_aceite`: memory-service grava e recupera experiencias por `mission_id`, `objective_ref`, workflow e tags de evidencia; recuperacao e read-only para consumidores; dados inseguros ou sem origem ficam fora do corpus reutilizavel.
- `gate_minimo`: `pytest services/memory-service/tests tests/unit/test_experience_reflection.py` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: reflexoes deixam de ser efemeras e passam a compor memoria evolutiva governada.
- `evidencia_de_fechamento`: `tests/unit/test_experience_reflection.py::test_memory_service_persists_bounded_experience_reflection`, `tests/unit/test_experience_reflection.py::test_memory_service_blocks_experience_reflection_without_evidence_or_manual_review`.

### MB-129

- `id`: `MB-129`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `evolucao/laboratorio`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `strategic_direction_workflow`, `software_change_workflow`, `governance_boundary_workflow`
- `micro_objetivo`: fazer o `evolution-lab` transformar reflexoes pos-tarefa em propostas evolutivas `sandbox-only`, classificando melhoria de memoria, workflow, skill, policy, rota ou teste.
- `justificativa_arquitetural`: experiencia so vira evolucao quando gera proposta comparavel, testavel e reversivel; o laboratorio deve continuar sandbox-only e nunca aplicar mudanca sozinho.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `tests`
- `dependencias`: `MB-127`, `MB-128`
- `criterio_de_aceite`: laboratorio cria proposta com tipo, justificativa, evidence refs, risco, teste minimo, rollback e status de revisao manual; propostas que pedem autoedicao, promocao automatica ou bypass do nucleo sao bloqueadas.
- `gate_minimo`: `pytest evolution/evolution-lab/tests tests/unit/test_experience_reflection.py` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: reflexao pos-tarefa passa a alimentar o loop evolutivo com propostas governadas e testaveis.
- `evidencia_de_fechamento`: `evolution/evolution-lab/tests/test_evolution_lab_service.py::test_evolution_lab_creates_sandbox_proposal_from_post_task_reflection`, `evolution/evolution-lab/tests/test_evolution_lab_service.py::test_evolution_lab_blocks_reflection_that_requests_autopromotion`.

### MB-130

- `id`: `MB-130`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade/evolucao`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `strategic_direction_workflow`, `software_change_workflow`, `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`
- `micro_objetivo`: expor sinais de experiencia/reflexao em observabilidade, piloto interno, relatorio, comparador e console read-only.
- `justificativa_arquitetural`: o operador precisa enxergar se o sistema esta aprendendo com missoes reais e se os aprendizados continuam subordinados a evidencia, testes e revisao humana.
- `arquivos/servicos_principais`: `services/observability-service`, `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`, `apps/jarvis_console`
- `dependencias`: `MB-128`, `MB-129`
- `criterio_de_aceite`: relatorios mostram registros recentes, qualidade da reflexao, outcome, falhas recorrentes, propostas geradas e bloqueios; console permite consulta read-only sem promover nem executar mudanca.
- `gate_minimo`: `pytest services/observability-service/tests tests/unit apps/jarvis_console/tests` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: aprendizado operacional fica visivel e comparavel antes de qualquer promocao.
- `evidencia_de_fechamento`: `services/observability-service/tests/test_observability_service.py::test_observability_service_audits_experience_reflection_signals`, `apps/jarvis_console/tests/test_console.py::test_console_experience_reflections_shows_recent_records`.

### MB-131

- `id`: `MB-131`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar documentalmente o lote de experiencia/reflexao pos-tarefa com changelog, handoff, snapshot, backlog macro e gates sincronizados.
- `justificativa_arquitetural`: a camada de aprendizado operacional deve permanecer governada, auditavel e separada de self-modification forte.
- `arquivos/servicos_principais`: `CHANGELOG.md`, `HANDOFF.md`, `docs/implementation/*`, `docs/architecture/*`
- `dependencias`: `MB-127`, `MB-128`, `MB-129`, `MB-130`
- `criterio_de_aceite`: documentos registram o baseline de experiencia/reflexao, limites de fase e proximas frentes candidatas, mantendo voz, web, API publica, `TA-004`, `TA-006`, autopromocao e alteracao de pesos fora de fase.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4-mini`
- `impacto_no_baseline`: fecha a primeira camada de experiencia operacional como insumo governado de autoevolucao.
- `evidencia_de_fechamento`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`.

### MB-132

- `id`: `MB-132`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `operacao/evolucao`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `strategic_direction_workflow`, `software_change_workflow`, `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`
- `micro_objetivo`: abrir a repriorizacao explicita pos-`MB-131`, escolhendo o marco `Operator Learning Loop` como proxima frente micro.
- `justificativa_arquitetural`: o baseline ja possui contratos, memoria evolutiva, laboratorio, observabilidade e console read-only para experiencia/reflexao, mas ainda falta fechar o ciclo real `usar -> registrar -> refletir -> propor -> revisar -> medir` em fluxo governado de operador.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `docs/implementation/v2-adherence-snapshot.md`, `HANDOFF.md`, `CHANGELOG.md`
- `dependencias`: `MB-131`
- `criterio_de_aceite`: fila micro registra objetivos, nao objetivos, criterios de sucesso, limites de fase e lote pequeno `MB-133` a `MB-140`, sem abrir voz, realtime, UI rica, browser/computer use amplo, scheduler autonomo, autopromocao, alteracao de pesos, novas verticais ou produto multicanal.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: a proxima rodada passa a mirar uso operacional humano com aprendizado governado, nao nova infraestrutura solta.
- `evidencia_de_fechamento`: lote `MB-132` a `MB-140` aberto com `MB-133` como proximo item `ready`; `.venv\Scripts\python.exe tools\check_mojibake.py .`, `.venv\Scripts\python.exe -m pytest tests\unit\test_experience_reflection.py` e `.venv\Scripts\python.exe tools\engineering_gate.py --mode standard`.

### MB-133

- `id`: `MB-133`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `operacao/memoria/evolucao`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `strategic_direction_workflow`, `software_change_workflow`, `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`
- `micro_objetivo`: gerar automaticamente um `experience_record` ao final de uma missao/request real governado no fluxo normal do `orchestrator-service`.
- `justificativa_arquitetural`: experiencia nao pode depender de registro manual se o sistema deve aprender com uso real; o fechamento do fluxo ja possui plano, rota, workflow, governanca, especialistas, operacao, sintese e memoria gravada.
- `arquivos/servicos_principais`: `services/orchestrator-service`, `services/memory-service`, `shared/contracts`, `shared/schemas`, `shared/events`, `tests`
- `dependencias`: `MB-132`
- `criterio_de_aceite`: todo fluxo governado elegivel grava `ExperienceRecordContract` com `mission_id`, `user_intent`, rota/workflow, `primary_mind`, `primary_domain_driver`, especialista usado, resumo de plano, resumo de execucao, outcome, erros, ferramentas/sinais usados, checkpoints e feedback quando existir, preservando `human_review_required`, sem autopromocao e sem mutacao do nucleo.
- `gate_minimo`: `pytest services/orchestrator-service/tests services/memory-service/tests tests/unit/test_experience_reflection.py` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: missoes reais passam a produzir materia-prima evolutiva automaticamente.
- `evidencia_de_fechamento`: `services/orchestrator-service/tests/test_orchestrator_service.py::test_orchestrator_service_handles_unitary_deliberative_planning`, `tests/unit/test_experience_reflection.py::test_memory_service_persists_experience_before_reflection`, `apps/jarvis_console/tests/test_console.py::test_console_experience_reflections_shows_pending_reflection`.

### MB-134

- `id`: `MB-134`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `evolucao/reflexao`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `strategic_direction_workflow`, `software_change_workflow`, `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`
- `micro_objetivo`: gerar automaticamente `post_task_reflection` bounded a partir de experiencias relevantes do fluxo real.
- `justificativa_arquitetural`: reflexao pos-tarefa deve ser o primeiro mecanismo de aprendizado governado, mas nao pode promover mudanca, editar core ou alterar pesos.
- `arquivos/servicos_principais`: `services/orchestrator-service`, `services/memory-service`, `evolution/evolution-lab`, `tests`
- `dependencias`: `MB-133`
- `criterio_de_aceite`: cada experiencia elegivel gera `PostTaskReflectionContract` estruturado, com evidencia, recomendacao bounded, testes sugeridos, rollback quando aplicavel, blockers e status de revisao humana; registros sem evidencia ficam bloqueados.
- `gate_minimo`: `pytest services/orchestrator-service/tests services/memory-service/tests evolution/evolution-lab/tests tests/unit/test_experience_reflection.py` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: o ciclo deixa de apenas registrar uso e passa a refletir sobre outcome/falhas de forma auditavel.
- `evidencia_de_fechamento`: `services/orchestrator-service/tests/test_orchestrator_service.py::test_orchestrator_service_handles_unitary_deliberative_planning`, `tests/unit/test_experience_reflection.py`, `services/memory-service/tests`, `evolution/evolution-lab/tests`.

### MB-135

- `id`: `MB-135`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `planejamento/sintese/evolucao`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `strategic_direction_workflow`, `software_change_workflow`, `structured_analysis_workflow`, `decision_risk_workflow`, `governance_boundary_workflow`
- `micro_objetivo`: permitir que reflexoes anteriores influenciem planejamento e sintese de forma governada, filtrada e auditavel.
- `justificativa_arquitetural`: aprendizado so vira utilidade quando melhora decisoes futuras, mas reflexoes nao podem ser injetadas indiscriminadamente nem substituir memoria canonica.
- `arquivos/servicos_principais`: `services/memory-service`, `services/orchestrator-service`, `engines/planning-engine`, `engines/synthesis-engine`, `services/observability-service`, `tests`
- `dependencias`: `MB-134`
- `criterio_de_aceite`: o runtime busca apenas reflexoes relevantes por rota, dominio e workflow, registra `reflection_influence_status`, evidencia quais reflexoes foram usadas e preserva fallback quando nao houver match seguro.
- `gate_minimo`: `pytest services/orchestrator-service/tests engines/planning-engine/tests engines/synthesis-engine/tests services/observability-service/tests tests/unit` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: reflexoes passam de arquivo consultavel para apoio causal bounded ao fluxo.
- `evidencia_de_fechamento`: `services/orchestrator-service/tests/test_orchestrator_service.py::test_orchestrator_service_applies_relevant_post_task_reflection`, `engines/planning-engine/tests/test_planning_engine.py::test_planning_engine_applies_bounded_reflection_influence`, `engines/synthesis-engine/tests/test_synthesis_engine.py::test_synthesis_engine_surfaces_reflection_influence`.

### MB-136

- `id`: `MB-136`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `governanca/evolucao`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: criar fila humana de revisao evolutiva para propostas geradas por reflexao.
- `justificativa_arquitetural`: proposta evolutiva sem fila humana explicita fica escondida no laboratorio; revisao humana e gate sao fronteiras de soberania.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `apps/jarvis_console`, `shared/contracts`, `tests`
- `dependencias`: `MB-134`
- `criterio_de_aceite`: propostas entram em estados `observed`, `candidate`, `needs_review`, `approved`, `rejected`, `sandboxed`, `promoted` ou `rolled_back`; nenhuma proposta de risco passa de revisao sem decisao humana/gate.
- `gate_minimo`: `pytest evolution/evolution-lab/tests apps/jarvis_console/tests tests/unit` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: evolucao derivada de reflexao fica operavel por humano, nao apenas persistida.
- `evidencia_de_fechamento`: `evolution/evolution-lab/tests/test_evolution_lab_service.py::test_evolution_lab_creates_sandbox_proposal_from_post_task_reflection`, `apps/jarvis_console/tests/test_console.py::test_console_evolution_review_queue_shows_human_review_items`, `tests/unit/test_shared_layer.py::test_experience_reflection_contracts_are_shared_schemas`.

### MB-137

- `id`: `MB-137`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `evals/evolucao`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `strategic_direction_workflow`, `software_change_workflow`
- `micro_objetivo`: criar eval/piloto que compara comportamento baseline versus reflection-assisted.
- `justificativa_arquitetural`: reflexao so deve amadurecer quando houver evidencia de ganho em planejamento, sintese ou decisao.
- `arquivos/servicos_principais`: `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`, `services/observability-service`, `tests`
- `dependencias`: `MB-135`
- `criterio_de_aceite`: piloto registra cenarios com e sem reflexao relevante, mede diferenca de plano/sintese/decisao e documenta limitacoes sem tratar melhoria local como autopromocao.
- `gate_minimo`: `pytest tests/unit services/observability-service/tests` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: o loop passa a medir se aprendizado melhora comportamento futuro.
- `evidencia_de_fechamento`: `services/observability-service/tests/test_observability_service.py::test_observability_service_audits_reflection_influence_signals`, `tests/unit/test_internal_pilot_report.py::test_internal_pilot_report_renders_text`, `tests/unit/test_compare_orchestrator_paths.py::test_compare_results_flags_reflection_assisted_mismatch_fields`.

### MB-138

- `id`: `MB-138`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `operacao/console`
- `workflow_profile_afetado`: `operational_readiness_workflow`
- `micro_objetivo`: melhorar o console textual para mostrar o ciclo de missao, experiencia, reflexao, proposta evolutiva e status de revisao.
- `justificativa_arquitetural`: o operador precisa enxergar o ciclo completo sem abrir banco, debug ou logs internos.
- `arquivos/servicos_principais`: `apps/jarvis_console`, `services/memory-service`, `evolution/evolution-lab`, `tests`
- `dependencias`: `MB-136`, `MB-137`
- `criterio_de_aceite`: console mostra missao, objetivo, rota, plano, checkpoints, memoria usada, especialista usado, experiencia, reflexao, proposta evolutiva, status de revisao e proximos passos, em modo seguro e sanitizado.
- `gate_minimo`: `pytest apps/jarvis_console/tests services/memory-service/tests evolution/evolution-lab/tests` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: o aprendizado operacional vira visivel e utilizavel pelo operador humano.
- `evidencia_de_fechamento`: `apps/jarvis_console/tests/test_console.py::test_console_mission_cycle_shows_operator_learning_loop`.

### MB-139

- `id`: `MB-139`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `operacao/workflow`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `strategic_direction_workflow`, `software_change_workflow`
- `micro_objetivo`: criar workflow pratico ponta a ponta de missao: iniciar missao, entender objetivo, planejar, executar/simular, registrar experiencia, refletir, propor aprendizado, revisar e encerrar.
- `justificativa_arquitetural`: o sistema precisa demonstrar utilidade operacional real antes de abrir superficies mais ricas ou autonomia ampla.
- `arquivos/servicos_principais`: `apps/jarvis_console`, `services/orchestrator-service`, `services/memory-service`, `evolution/evolution-lab`, `tests`
- `dependencias`: `MB-138`
- `criterio_de_aceite`: um cenario governado real ou simulado demonstra o ciclo completo sem autopromocao, sem scheduler autonomo e com evidencia recuperavel no console.
- `gate_minimo`: `pytest apps/jarvis_console/tests services/orchestrator-service/tests tests/unit` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: o JARVIS passa de infraestrutura de aprendizado para loop operacional demonstravel.
- `evidencia_de_fechamento`: `apps/jarvis_console/tests/test_console.py::test_console_mission_workflow_runs_governed_loop_end_to_end`.

### MB-140

- `id`: `MB-140`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `docs/gates`
- `workflow_profile_afetado`: `nao_aplicavel`
- `micro_objetivo`: fechar documentalmente o baseline do `Operator Learning Loop` com docs operacionais de uso humano real.
- `justificativa_arquitetural`: o operador precisa saber como iniciar missao, revisar reflexao, revisar proposta evolutiva, interpretar relatorio e fechar ciclo.
- `arquivos/servicos_principais`: `docs/operations`, `docs/implementation/*`, `docs/architecture/*`, `HANDOFF.md`, `CHANGELOG.md`
- `dependencias`: `MB-139`
- `criterio_de_aceite`: documentacao operacional, backlog, snapshot, handoff e changelog registram o ciclo completo, evidencias, limites conhecidos e proximo item `ready` recomendado.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4-mini`
- `impacto_no_baseline`: fecha a primeira camada utilizavel de aprendizado humano-governado do sistema.
- `evidencia_de_fechamento`: `docs/operations/operator-learning-loop.md`, `HANDOFF.md`, `CHANGELOG.md`, `v2-adherence-snapshot.md` e backlog macro sincronizados apos demonstracao ponta a ponta.

---

Estado apos `MB-140`: o baseline do `Operator Learning Loop` esta fechado.
A nova fila tecnica abre o recorte `Human Evolution Review Controls`: transformar
propostas evolutivas pendentes em decisoes humanas auditaveis, sem autopromocao
e sem mutacao autonoma do nucleo.

### MB-141

- `id`: `MB-141`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `governanca/evolucao`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: abrir a repriorizacao explicita pos-`MB-140`, escolhendo controles humanos de revisao evolutiva como proximo recorte.
- `justificativa_arquitetural`: o loop operacional ja gera experiencia, reflexao e proposta, mas ainda termina com revisao pendente. O proximo gargalo de utilidade e permitir que o operador decida, registre evidencia e mantenha rollback sem abrir autopromocao.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-140`
- `criterio_de_aceite`: existe novo lote micro `MB-141` a `MB-145`, com limites de fase explicitos e foco em decisao humana auditavel sobre propostas evolutivas.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4-mini`
- `impacto_no_baseline`: inicia o fechamento da lacuna entre proposta evolutiva pendente e decisao humana governada.
- `evidencia_de_fechamento`: backlog micro, backlog macro, handoff, snapshot e changelog sincronizados.

### MB-142

- `id`: `MB-142`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `contratos/evolucao`
- `workflow_profile_afetado`: `governance_boundary_workflow`
- `micro_objetivo`: formalizar contrato compartilhado de decisao humana sobre proposta evolutiva.
- `justificativa_arquitetural`: aprovar, rejeitar, sandboxar ou devolver proposta para revisao precisa virar contrato estavel, nao metadata solta no laboratorio.
- `arquivos/servicos_principais`: `shared/contracts`, `shared/schemas`, `shared/events`, `tests/unit`
- `dependencias`: `MB-141`
- `criterio_de_aceite`: existe contrato tipado para `evolution_review_decision`, com `proposal_id`, `review_status`, `decision`, `operator_ref`, `evidence_refs`, `proposed_tests`, `rollback_plan_ref`, `risk_acceptance`, `timestamp` e bloqueio explicito de promocao automatica.
- `gate_minimo`: `pytest tests/unit/test_shared_layer.py` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: decisoes humanas de evolucao passam a ter contrato soberano e auditavel.
- `evidencia_de_fechamento`: teste compartilhado cobrindo schema, evento e defaults seguros.

### MB-143

- `id`: `MB-143`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `evolution-lab/governanca`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `software_change_workflow`
- `micro_objetivo`: implementar transicoes humanas no `evolution-lab` para propostas em fila.
- `justificativa_arquitetural`: a fila read-only prova existencia de propostas, mas o operador ainda nao consegue fechar o ciclo de revisao sem editar armazenamento ou docs manualmente.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `shared/contracts`, `tests`
- `dependencias`: `MB-142`
- `criterio_de_aceite`: `evolution-lab` aceita decisoes `approve`, `reject`, `sandbox`, `needs_review` e `rollback`, persiste historico de decisao, exige evidencia/testes/rollback quando houver risco e bloqueia `promoted` sem gate humano explicito.
- `gate_minimo`: `pytest evolution/evolution-lab/tests tests/unit` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: propostas deixam de ser apenas pendentes e passam a ter ciclo humano reversivel.
- `evidencia_de_fechamento`: testes do `evolution-lab` cobrindo approve/reject/sandbox/rollback e bloqueio de promocao sem gate.

### MB-144

- `id`: `MB-144`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `operacao/console`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: expor no console comandos seguros para revisar propostas evolutivas.
- `justificativa_arquitetural`: o operador precisa fechar a revisao pelo mesmo canal textual em que enxerga missao, reflexao e fila, sem acesso direto ao banco.
- `arquivos/servicos_principais`: `apps/jarvis_console`, `evolution/evolution-lab`, `tests`
- `dependencias`: `MB-143`
- `criterio_de_aceite`: console possui comando `evolution-review --proposal-id ... --action approve|reject|sandbox|needs-review|rollback`, exige evidencia quando aplicavel, mostra status final, blockers, rollback e `automatic_promotion=False`.
- `gate_minimo`: `pytest apps/jarvis_console/tests evolution/evolution-lab/tests` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: o operador passa a revisar aprendizado pelo console sem promover mudanca sozinho.
- `evidencia_de_fechamento`: teste de console aprovando/rejeitando proposta em modo governado e auditavel.

### MB-145

- `id`: `MB-145`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade/docs`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: auditar e documentar o fechamento humano de revisao evolutiva.
- `justificativa_arquitetural`: decisoes humanas so fortalecem o sistema se virarem evidencia comparavel em observabilidade, piloto, relatorios e docs operacionais.
- `arquivos/servicos_principais`: `services/observability-service`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`, `docs/operations`, `HANDOFF.md`, `CHANGELOG.md`
- `dependencias`: `MB-144`
- `criterio_de_aceite`: eventos e relatorios mostram decisao humana de revisao, proposta afetada, evidencia, rollback, status final e limites; docs explicam como aprovar/rejeitar/sandboxar sem autopromocao.
- `gate_minimo`: `pytest services/observability-service/tests tests/unit apps/jarvis_console/tests` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: fecha o ciclo `propor -> revisar` com evidencia humana auditavel.
- `evidencia_de_fechamento`: observabilidade, relatorios, docs e handoff sincronizados com o novo estado real.

Estado apos `MB-145`: o lote `Human Evolution Review Controls` esta fechado.
Nao ha novo item tecnico `ready`; o proximo lote deve nascer de repriorizacao
explicita baseada em uso humano real do ciclo `usar -> registrar -> refletir ->
propor -> revisar -> medir`.

## 4.23 Repriorizacao pos-MB-145: Reviewed Learning Feedback Loop

O lote `MB-146` a `MB-150` abre o recorte `Reviewed Learning Feedback Loop`.
Objetivo: fazer decisoes humanas revisadas voltarem ao runtime como orientacao
bounded, filtrada, observavel e mensuravel, sem autopromocao, sem mutacao de
nucleo e sem transformar aprovacao humana em deploy automatico.

### MB-146

- `id`: `MB-146`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `evolucao/medicao`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: abrir a repriorizacao explicita pos-`MB-145`, escolhendo feedback de aprendizado revisado como proximo recorte.
- `justificativa_arquitetural`: o sistema ja registra experiencia, reflexao, proposta e decisao humana. O gargalo agora e medir se aprendizados revisados melhoram decisoes futuras sem liberar autopromocao.
- `arquivos/servicos_principais`: `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `HANDOFF.md`, `docs/implementation/v2-adherence-snapshot.md`, `CHANGELOG.md`
- `dependencias`: `MB-145`
- `criterio_de_aceite`: existe novo lote micro `MB-146` a `MB-150`, com limites de fase explicitos e foco em influencia governada de aprendizado revisado.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4-mini`
- `impacto_no_baseline`: inicia a ponte entre revisao humana e melhoria mensuravel do runtime.
- `evidencia_de_fechamento`: backlog micro, backlog macro, handoff, snapshot e changelog sincronizados.

### MB-147

- `id`: `MB-147`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `contratos/evolucao`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `software_change_workflow`
- `micro_objetivo`: formalizar contrato de `reviewed_learning_guidance` derivado de decisoes humanas aprovadas ou sandboxadas.
- `justificativa_arquitetural`: decisoes humanas nao devem entrar no planejamento como texto solto; precisam virar guidance tipado, filtravel e com limites de uso.
- `arquivos/servicos_principais`: `shared/contracts`, `shared/schemas`, `shared/events`, `evolution/evolution-lab`, `tests/unit`
- `dependencias`: `MB-146`
- `criterio_de_aceite`: existe contrato tipado com `guidance_id`, `source_review_decision_id`, `evolution_proposal_id`, `review_status`, `route`, `workflow_profile`, `domain`, `guidance_summary`, `allowed_usage`, `evidence_refs`, `rollback_plan_ref`, `expires_at` opcional e flags `automatic_promotion_allowed=false`, `core_mutation_allowed=false`.
- `gate_minimo`: `pytest tests/unit/test_shared_layer.py evolution/evolution-lab/tests` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: aprendizado revisado passa a ter forma canonica antes de influenciar qualquer decisao.
- `evidencia_de_fechamento`: testes de contrato, schema, evento e derivacao no `evolution-lab`.

### MB-148

- `id`: `MB-148`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `runtime/planning/synthesis`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: permitir que `reviewed_learning_guidance` influencie planejamento e sintese de forma filtrada, auditavel e bounded.
- `justificativa_arquitetural`: a utilidade do loop depende de o sistema aprender com revisoes humanas, mas somente quando rota, workflow e dominio forem relevantes e sem substituir governanca ou memoria canonica.
- `arquivos/servicos_principais`: `services/orchestrator-service`, `engines/planning-engine`, `engines/synthesis-engine`, `services/memory-service`, `tests`
- `dependencias`: `MB-147`
- `criterio_de_aceite`: planning/synthesis recebem guidance revisado apenas quando relevante por rota/workflow/dominio, registram `reviewed_learning_influence_status`, refs usadas, motivo de aplicacao ou bloqueio, e nunca promovem mudanca automaticamente.
- `gate_minimo`: `pytest services/orchestrator-service/tests engines/planning-engine/tests engines/synthesis-engine/tests services/memory-service/tests` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: decisoes revisadas passam a influenciar comportamento futuro sob governanca e telemetria.
- `evidencia_de_fechamento`: `reviewed_learning_guidance` agora atravessa memoria, orquestracao, planning e synthesis com filtros por rota/workflow/dominio, refs auditaveis, bloqueio de escopo e testes de guidance relevante/irrelevante; validado por `pytest tests/unit/test_experience_reflection.py engines/planning-engine/tests/test_planning_engine.py engines/synthesis-engine/tests/test_synthesis_engine.py services/orchestrator-service/tests/test_orchestrator_service.py -q`.

### MB-149

- `id`: `MB-149`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade/evals`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: medir baseline versus execucao assistida por aprendizado revisado.
- `justificativa_arquitetural`: uma revisao humana so deve virar aprendizado confiavel se houver evidencia comparativa de melhora ou ausencia de regressao.
- `arquivos/servicos_principais`: `services/observability-service`, `tools/internal_pilot_support.py`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`, `tests`
- `dependencias`: `MB-148`
- `criterio_de_aceite`: relatorios e comparadores exibem `reviewed_learning_influence_status`, refs, taxa de uso, divergencias entre baseline e assisted, regressions/blockers e conclusao `no_promotion_without_release_gate`.
- `gate_minimo`: `pytest services/observability-service/tests tests/unit/test_internal_pilot_report.py tests/unit/test_compare_orchestrator_paths.py` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: o ciclo `revisar -> medir` passa a ter evidencia operacional comparavel.
- `evidencia_de_fechamento`: observabilidade, piloto interno, relatorio e comparador agora carregam `reviewed_learning_influence_status`, refs, motivo, taxa assisted/baseline e conclusao `no_promotion_without_release_gate`; validado por `pytest services/observability-service/tests/test_observability_service.py tests/unit/test_internal_pilot_report.py tests/unit/test_compare_orchestrator_paths.py -q`.

### MB-150

- `id`: `MB-150`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `operacao/docs`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: expor ao operador a influencia de aprendizado revisado e documentar como interpretar resultados.
- `justificativa_arquitetural`: o operador precisa ver quando um aprendizado revisado foi usado, por que foi usado, quais evidencias sustentam isso e qual proximo passo seguro.
- `arquivos/servicos_principais`: `apps/jarvis_console`, `docs/operations/operator-learning-loop.md`, `HANDOFF.md`, `CHANGELOG.md`, `tests`
- `dependencias`: `MB-149`
- `criterio_de_aceite`: console mostra guidance revisado usado, refs, status de influencia, medicao baseline vs assisted, limites de promocao e proximo passo humano; docs explicam o fluxo `revisar -> influenciar -> medir`.
- `gate_minimo`: `pytest apps/jarvis_console/tests tests/unit` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: fecha a leitura operacional do feedback de aprendizado revisado sem abrir autoevolucao profunda.
- `evidencia_de_fechamento`: `mission-cycle` e `mission-workflow` agora mostram influencia de aprendizado revisado, refs, motivo, medicao assisted/baseline e limite de release; `docs/operations/operator-learning-loop.md`, handoff, snapshot e changelog foram sincronizados.

Estado apos `MB-150`: o lote `Reviewed Learning Feedback Loop` esta fechado.
Nao ha novo item tecnico implementavel sem repriorizacao explicita a partir do
backlog macro.

## 4.24 Repriorizacao pos-MB-150: Auditoria documental governada

Este lote fecha a primeira decisao curta apos o ciclo `usar -> registrar ->
refletir -> propor -> revisar -> influenciar -> medir`: antes de abrir nova
funcionalidade, o repositorio precisa estabilizar a camada documental ativa,
identificar documentos canonicos, operacionais, historicos e defasados, e
preparar uma segunda passada segura com mapa de backlinks.

### MB-151

- `id`: `MB-151`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `governanca/documentacao`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: oficializar a auditoria documental governada pos-`MB-150`, sem executar limpeza ampla, e definir o proximo recorte seguro.
- `justificativa_arquitetural`: o repositorio acumulou documentos canonicos, operacionais, historicos e defasados; antes de mover, mesclar, arquivar ou remover qualquer arquivo, a governanca exige inventario, classificacao, clusters, riscos e decisao humana onde houver sensibilidade.
- `arquivos/servicos_principais`: `docs/documentation/documentation-canonicality-audit-mb151.md`, `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `docs/implementation/v2-adherence-snapshot.md`, `HANDOFF.md`, `CHANGELOG.md`
- `dependencias`: `MB-150`
- `criterio_de_aceite`: auditoria salva como documento oficial; backlog registra `MB-151` como fechado; nenhum arquivo foi movido, deletado, renomeado ou mesclado; documentos locais ficam consistentes com a auditoria; `MB-152` foi aberto como proximo recorte naquele momento.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: transforma a auditoria documental em evidencia oficial, preservando soberania do Documento-Mestre e evitando limpeza documental sem mapa de referencias.
- `evidencia_de_fechamento`: `docs/documentation/documentation-canonicality-audit-mb151.md` registra 73 documentos revisados, canonicos ativos, operacionais ativos, implementacao ativa, documentos defasados, candidatos a merge/archive, ausencia de candidato seguro a remocao, documentos com decisao humana, clusters, riscos e `MB-152` como proximo recorte.

### MB-152

- `id`: `MB-152`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `governanca/documentacao`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: gerar mapa de backlinks e sincronizar somente documentos ativos defasados, sem mover, deletar ou mesclar documentos nesta rodada.
- `justificativa_arquitetural`: a auditoria `MB-151` identificou documentos ativos defasados e historicos fora de archive, mas tambem registrou risco de quebrar referencias e perder rastreabilidade; a segunda passada segura precisa mapear backlinks antes de qualquer reorganizacao fisica.
- `arquivos/servicos_principais`: `docs/documentation/documentation-canonicality-audit-mb151.md`, `docs/documentation/repository-map-and-consistency-audit.md`, `README.md`, `docs/operations/chat-transition-template.md`, `docs/operations/release-and-change-management.md`, `docs/operations/incident-response.md`, `docs/executive/master-summary.md`, `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `docs/implementation/v2-adherence-snapshot.md`, `HANDOFF.md`, `CHANGELOG.md`
- `dependencias`: `MB-151`
- `criterio_de_aceite`: existe mapa de backlinks para documentos auditados; apenas documentos ativos defasados sao sincronizados; nenhum arquivo e movido, deletado ou mesclado; documentos historicos sao marcados apenas quando seguro; documentos sensiveis permanecem separados; um plano posterior explicita moves/archive; gate padrao passa.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: reduz risco documental antes de qualquer limpeza, mantendo rastreabilidade e evitando contradicao com o Documento-Mestre.
- `fora_de_escopo`: deletar documentos; mover documentos para archive; mesclar documentos canonicos; alterar Documento-Mestre; alterar arquitetura; abrir funcionalidade; voz/realtime/browser/computer use/SecurityOS.
- `evidencia_de_fechamento`: `docs/documentation/documentation-backlink-map-mb152.md` registra backlinks dos 73 documentos auditados, identifica documentos de alto acoplamento, preserva documentos sensiveis, sincroniza apenas docs ativos defasados e explicita plano posterior para moves/archive sem executar limpeza fisica.

### MB-153

- `id`: `MB-153`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `governanca/documentacao`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: executar o primeiro archive fisico conservador de documentos historicos de implementacao, reescrevendo backlinks e preservando rastreabilidade.
- `justificativa_arquitetural`: depois de `MB-151` e `MB-152`, alguns documentos historicos de implementacao ja tinham classificacao, backlink map e baixo risco suficiente para sair da superficie ativa sem perda de historico; delecao e merge destrutivo continuavam sem base segura.
- `arquivos/servicos_principais`: `docs/documentation/documentation-cleanup-mb153.md`, `docs/archive/implementation/*`, `README.md`, `HANDOFF.md`, `CHANGELOG.md`, `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `docs/implementation/v2-adherence-snapshot.md`
- `dependencias`: `MB-152`
- `criterio_de_aceite`: apenas archive candidates historicos e nao sensiveis sao movidos; backlinks literais sao reescritos; nenhum documento e deletado; nenhum merge destrutivo e executado; documentos referenciados pelo Documento-Mestre permanecem no lugar; gate padrao passa.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: reduz a superficie ativa de implementacao sem quebrar referencias nem perder historico, mantendo docs sensiveis e canonicos intactos.
- `fora_de_escopo`: deletar documentos; mover docs referenciados pelo Documento-Mestre; mesclar documentos canonicos; alterar arquitetura; abrir funcionalidade.
- `evidencia_de_fechamento`: `docs/documentation/documentation-cleanup-mb153.md` lista seis moves para `docs/archive/implementation/`, registra ausencia de delecao, ausencia de merge destrutivo e validacao de backlinks antigos.

### MB-154

- `id`: `MB-154`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `governanca/planejamento`, `arquitetura/evolucao`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: criar um mapa mestre de implementacao que decompoe a visao do JARVIS em capacidades, status, dependencias, fases e proximos slices, evitando repriorizacao cega a cada lote.
- `justificativa_arquitetural`: o backlog micro executa cortes pequenos com seguranca, mas a visao do JARVIS exige uma decomposicao completa de produto/capacidades para enxergar o caminho total sem transformar cada decisao em nova descoberta local.
- `arquivos/servicos_principais`: `docs/implementation/implementation-master-map.md`, `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `docs/implementation/v2-adherence-snapshot.md`, `HANDOFF.md`, `CHANGELOG.md`
- `dependencias`: `MB-153`
- `criterio_de_aceite`: existe documento ativo acima da fila micro com trilhas de capacidade, status, dependencias, fases, gaps de maior valor, regra de derivacao de MBs e sugestao de proximo lote; o documento nao substitui Documento-Mestre nem `execution-backlog`; gate padrao passa.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: o planejamento deixa de depender apenas de repriorizacao incremental e passa a ter um mapa completo de implementacao orientado por capacidades.
- `fora_de_escopo`: implementar funcionalidade nova; abrir voz/realtime/browser/computer use; alterar Documento-Mestre; alterar arquitetura runtime; promover capacidades deferred.
- `evidencia_de_fechamento`: `docs/implementation/implementation-master-map.md` registra tracks `OP`, `COG`, `MEM`, `EVL`, `ACT`, `SPC`, `KNW`, `OBS`, `GOV`, `SFC` e `DOC`, identifica gaps de maior valor e recomenda o lote `MB-155` a `MB-159` como proximo candidato, sem coloca-lo automaticamente em `ready`.

## 4.25 Lote pos-MB-154: Operator Product Utility Baseline

Este lote deriva explicitamente de
`docs/implementation/implementation-master-map.md` e prioriza utilidade diaria
do operador antes de abrir capacidades especulativas.

Escopo permitido:

- dashboard textual do operador;
- ciclo governado de work items;
- lifecycle minimo de artefatos;
- metricas de utilidade operacional;
- raciocinio de objetivos de horizonte longo.

Fora de escopo:

- voz/realtime;
- UI rica;
- browser/computer use amplo;
- scheduler autonomo;
- integracoes externas amplas;
- SecurityOS/protective intelligence vertical;
- autopromocao evolutiva;
- self-modification ou alteracao de pesos.

### MB-155

- `id`: `MB-155`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `superficies/operador`, `observabilidade`, `continuidade`
- `map_ids`: `OP-006`, `SFC-003`, `OBS-005`
- `workflow_profile_afetado`: `operational_readiness_workflow`
- `micro_objetivo`: criar baseline minimo de dashboard textual do operador para consultar missao, objetivo, proximas acoes, experiencia/reflexao, fila evolutiva e sinais de aprendizado revisado em uma unica leitura.
- `justificativa_arquitetural`: o sistema ja registra, reflete, revisa, influencia e mede, mas o operador ainda precisa de uma tela textual unica para entender o estado diario sem navegar comandos separados.
- `arquivos/servicos_principais`: `apps/jarvis_console/cli.py`, `apps/jarvis_console/tests/test_console.py`, `docs/implementation/implementation-master-map.md`, `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `docs/implementation/v2-adherence-snapshot.md`, `HANDOFF.md`, `CHANGELOG.md`
- `dependencias`: `MB-154`
- `criterio_de_aceite`: existe comando read-only `operator-dashboard` que agrega estado de missao/objetivo, work items, checkpoints, artefatos, ultima experiencia/reflexao, propostas em revisao, aprendizado revisado e proximo passo do operador; nao escreve memoria, nao promove proposta e nao cria fonte paralela de estado.
- `gate_minimo`: `pytest apps/jarvis_console/tests/test_console.py` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: o operador passa a ter um painel CLI minimo para iniciar o dia ou retomar missao com leitura consolidada do ciclo governado.
- `fora_de_escopo`: criar UI rica; listar todas as missoes sem indice canonico; alterar contratos compartilhados; criar scheduler; criar nova persistencia; promover aprendizado automaticamente.
- `evidencia_de_fechamento`: `apps/jarvis_console operator-dashboard` renderiza dashboard read-only para escopo de missao ou global; testes cobrem missao com experiencia/reflexao/proposta pendente e estado global vazio.

### MB-156

- `id`: `MB-156`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `continuidade/objetivos`, `governanca`, `operacao`
- `map_ids`: `OP-004`, `COG-010`, `GOV-007`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `decision_risk_workflow`
- `micro_objetivo`: tornar work items objetos operacionais governados no console, com criacao, atualizacao de status e fechamento passando por governanca e memoria canonica.
- `justificativa_arquitetural`: work items ja existem como refs em `MissionStateContract`, mas ainda nao sao conduzidos como objetos operacionais de primeira classe pelo operador.
- `arquivos/servicos_principais`: `shared/contracts`, `shared/schemas`, `shared/events`, `services/memory-service`, `services/orchestrator-service`, `apps/jarvis_console`, `tests`
- `dependencias`: `MB-155`
- `criterio_de_aceite`: o operador consegue criar, consultar, pausar/bloquear/concluir e redefinir proxima acao de work item por comando governado; eventos auditaveis e estado de missao refletem a mudanca; transicoes inseguras sao bloqueadas.
- `gate_minimo`: testes unitarios/direcionados do console, memoria/orquestrador afetados e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: work items deixam de ser apenas refs passivos e passam a ter ciclo operacional minimo governado por console, governanca, memoria canonica e eventos auditaveis.
- `fora_de_escopo`: scheduler autonomo; atribuicao automatica de tarefas; integracoes externas; UI rica; mover work items para armazenamento paralelo fora da memoria canonica.
- `evidencia_de_fechamento`: `work-item` cria, pausa, bloqueia, conclui e redefine proxima acao de work item via `orchestrator-service`; `work-items` consulta o estado; `MemoryService.transition_work_item_state()` atualiza `MissionStateContract`; `work_item_state_changed` e `mission_updated` registram a transicao.

### MB-157

- `id`: `MB-157`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `artefatos`, `memoria`, `operacao`
- `map_ids`: `OP-005`, `ACT-004`, `MEM-006`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: criar registry minimo de lifecycle de artefatos vivos com refs, versoes, status, missao proprietaria, objetivo relacionado e metadados de substituicao/rollback.
- `justificativa_arquitetural`: artefatos ja aparecem no estado operacional, mas ainda faltam identidade duravel e lifecycle governado para uso diario.
- `arquivos/servicos_principais`: `shared/contracts`, `services/memory-service`, `services/operational-service`, `apps/jarvis_console`, `tests`
- `dependencias`: `MB-156`
- `criterio_de_aceite`: artefatos podem ser registrados, consultados e vinculados a missao/objetivo/work item sem quebrar governanca nem criar escrita fora do core.
- `gate_minimo`: testes direcionados de contratos/memoria/console e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: artefatos vivos passam a ter lifecycle minimo governado por console, governanca, memoria canonica e eventos auditaveis, sem file adapter nem mutacao fisica de arquivos.
- `fora_de_escopo`: ler, mover, deletar ou editar arquivos reais; versionamento rico; registry externo; lifecycle multicanal; promocao automatica.
- `evidencia_de_fechamento`: `artifact` registra, ativa, arquiva, substitui e rollbacka refs de artefato bounded; `artifacts` consulta estado read-only; `ArtifactLifecycleStateContract` e `artifact_lifecycle_state_changed` registram a transicao; `MemoryService.transition_artifact_lifecycle_state()` atualiza `MissionStateContract`.

### MB-158

- `id`: `MB-158`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade`, `produto_operador`, `evolucao`
- `map_ids`: `OBS-005`, `OBS-009`, `EVL-005`
- `workflow_profile_afetado`: `operational_readiness_workflow`
- `micro_objetivo`: medir utilidade operacional do JARVIS para o operador a partir de missoes retomadas, work items fechados, memoria reutilizada, repeticao reduzida e impacto de aprendizado revisado.
- `justificativa_arquitetural`: o sistema precisa medir valor diario real, nao apenas saude de infraestrutura.
- `arquivos/servicos_principais`: `services/observability-service`, `tools/internal_pilot_report.py`, `tools/compare_orchestrator_paths.py`, `apps/jarvis_console`, `tests`
- `dependencias`: `MB-156`, `MB-157`
- `criterio_de_aceite`: relatorios e dashboard expoem metricas compactas de utilidade, com limitacoes claras e sem tratar ganho local como promocao automatica.
- `gate_minimo`: testes direcionados de observabilidade/relatorios/console e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: observabilidade e dashboard passam a expor `operator_usefulness_status`, `operator_usefulness_score` e `operator_usefulness_signals`, medindo valor operacional sem tratar sinal local como promocao automatica.
- `evidencia_de_fechamento`: `FlowAudit` calcula sinais compactos de utilidade a partir de objetivo consultado, work items, artefatos, proxima acao, memoria causal, experiencia/reflexao e aprendizado revisado; `operator-dashboard` exibe esses campos.

### MB-159

- `id`: `MB-159`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `planejamento`, `memoria`, `continuidade`
- `map_ids`: `COG-010`, `MEM-005`, `MEM-006`
- `workflow_profile_afetado`: `strategic_direction_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: adicionar raciocinio minimo de objetivo de horizonte longo com estrategia, marcos, riscos, anchors de memoria e evolucao da proxima acao entre sessoes.
- `justificativa_arquitetural`: a visao do JARVIS exige ajudar em objetivos persistentes, mas isso deve nascer sobre work items, artefatos e metricas, nao como planejamento abstrato solto.
- `arquivos/servicos_principais`: `engines/planning-engine`, `services/memory-service`, `services/orchestrator-service`, `engines/synthesis-engine`, `apps/jarvis_console`, `tests`
- `dependencias`: `MB-156`, `MB-157`, `MB-158`
- `criterio_de_aceite`: planejamento/sintese conseguem mostrar estrategia de horizonte longo ligada a memoria e estado operacional, com proximas acoes auditaveis e sem scheduler autonomo.
- `gate_minimo`: testes direcionados de planning/memoria/orquestracao/sintese/console e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: o sistema passa a derivar uma estrategia minima de horizonte longo a partir de `MissionStateContract`, work items, artefatos, checkpoints, anchors de memoria e proxima acao auditavel, sem scheduler autonomo.
- `evidencia_de_fechamento`: `LongHorizonGoalStrategyContract`, `LONG_HORIZON_GOAL_STRATEGY_SCHEMA`, evento `long_horizon_goal_strategy_declared`, `MemoryService.build_long_horizon_goal_strategy()`, `OrchestratorService.inspect_long_horizon_goal_strategy()`, comando `goal-strategy` e sintese final mostram a leitura read-only de estrategia de horizonte longo.

## 4.26 Lote pos-MB-159: Core Usefulness Expansion Queue

Este lote deriva explicitamente de
`docs/implementation/implementation-master-map.md` depois do fechamento de
`MB-159`. A fila e maior para dar visao de caminho, mas preserva `WIP limit = 1`:
apenas `MB-161` entra como `ready`; os demais ficam `blocked` por ordem e
dependencia.

Tese da repriorizacao:

- o gargalo atual nao e criar mais infraestrutura solta;
- o proximo valor esta em tornar memoria, governanca, evolucao, cockpit,
  dominios e qualidade mais causais e utilizaveis pelo operador;
- capacidades deferred continuam fora da fase.

Escopo permitido:

- influencia semantica/procedural de memoria com evidencias;
- auditoria de memoria usada e nao usada;
- autonomia como contrato runtime governado;
- checklist e gate de promocao sandbox-to-release;
- cockpit textual do operador;
- feedback explicito do operador;
- onboarding de dominios e evals por dominio;
- proveniencia/freshness de conhecimento;
- dashboard de regressao/readiness.

Fora de escopo:

- voz/realtime;
- UI rica;
- browser/computer use amplo;
- scheduler autonomo;
- file adapter amplo;
- API publica/web;
- SecurityOS/protective intelligence vertical;
- integracoes externas amplas;
- auto-promocao evolutiva;
- self-modification ou alteracao de pesos.

### MB-160

- `id`: `MB-160`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `governanca/planejamento`, `documentacao`, `execucao`
- `map_ids`: `DOC-002`, `DOC-003`, `DOC-004`, `DOC-007`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: repriorizar a fila pos-`MB-159` a partir do mapa mestre, criando uma fila maior de implementacao sem abrir capacidades fora de fase.
- `justificativa_arquitetural`: o `implementation-master-map` agora permite enxergar o caminho completo; a fila micro precisa capturar um horizonte maior sem abandonar WIP controlado.
- `arquivos/servicos_principais`: `docs/implementation/implementation-master-map.md`, `docs/implementation/execution-backlog.md`, `docs/implementation/unified-gap-and-absorption-backlog.md`, `docs/implementation/v2-adherence-snapshot.md`, `HANDOFF.md`, `CHANGELOG.md`
- `dependencias`: `MB-159`
- `criterio_de_aceite`: existe fila `MB-160` a `MB-174`, derivada dos gaps de maior valor, com status, dependencias, criterios de aceite, gates e apenas um item tecnico `ready`.
- `gate_minimo`: `python tools/check_mojibake.py .` e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: o projeto passa de repriorizacao lote-a-lote para uma fila maior, rastreavel e ainda executavel com WIP 1.
- `fora_de_escopo`: implementar funcionalidade; alterar Documento-Mestre; abrir voz/realtime/browser/computer use; promover capabilities deferred.
- `evidencia_de_fechamento`: este lote registra `MB-161` como unico item tecnico `ready` e `MB-162` a `MB-174` como `blocked` por dependencia/ordem.

### MB-161

- `id`: `MB-161`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `memoria`, `planejamento`, `sintese`, `observabilidade`
- `map_ids`: `MEM-005`, `COG-007`, `OBS-005`
- `workflow_profile_afetado`: `strategic_direction_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: tornar a influencia de memoria semantica mais causal, com anchors de evidencia, motivos de relevancia e motivos auditaveis de nao uso.
- `justificativa_arquitetural`: memoria ja aparece no runtime, mas ainda precisa explicar de forma mais forte por que influenciou ou nao influenciou plano/sintese.
- `arquivos/servicos_principais`: `services/memory-service`, `engines/planning-engine`, `engines/synthesis-engine`, `services/orchestrator-service`, `services/observability-service`, `apps/jarvis_console`, `tests`
- `dependencias`: `MB-160`
- `criterio_de_aceite`: planning/synthesis recebem e exibem anchors semanticos relevantes, refs de evidencia e razoes de uso/nao uso; observabilidade registra o sinal; testes cobrem memoria, planning/synthesis e console/dashboard afetado.
- `gate_minimo`: testes direcionados de memoria/planning/synthesis/observabilidade/console e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: memoria semantica agora carrega refs de ancora, refs de evidencia e motivo auditavel de uso ou nao uso em planning, synthesis, eventos, observabilidade e console/dashboard.
- `evidencia_de_fechamento`: `pytest tests/unit/test_shared_layer.py engines/planning-engine/tests/test_planning_engine.py engines/synthesis-engine/tests/test_synthesis_engine.py services/orchestrator-service/tests/test_orchestrator_service.py services/observability-service/tests/test_observability_service.py apps/jarvis_console/tests/test_console.py` passou com 160 testes.

### MB-162

- `id`: `MB-162`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `memoria`, `artefatos`, `evolucao`
- `map_ids`: `MEM-006`, `ACT-004`, `EVL-007`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `software_change_workflow`
- `micro_objetivo`: criar baseline de memoria procedural/playbooks derivados de procedimentos repetidos, artefatos e reflexoes revisadas, sem promocao automatica.
- `justificativa_arquitetural`: o JARVIS precisa reaproveitar modos de trabalho, nao apenas fatos semanticos, mas isso deve nascer como candidato governado.
- `arquivos/servicos_principais`: `services/memory-service`, `evolution/evolution-lab`, `services/orchestrator-service`, `apps/jarvis_console`, `tests`
- `dependencias`: `MB-161`
- `criterio_de_aceite`: procedimentos recorrentes podem ser registrados como candidatos bounded com evidencia, rollback e revisao humana; nenhum playbook vira regra ativa sem gate.
- `gate_minimo`: testes direcionados de memoria/evolution-lab/console e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: memoria procedural agora possui candidato de playbook bounded persistente, com passos limitados, evidencias, artefatos/reflexoes fonte, testes propostos, rollback, revisao humana e bloqueio de autopromocao/core mutation; evolution-lab transforma o candidato em proposta sandbox-only e console mostra a fila read-only.
- `evidencia_de_fechamento`: `pytest tests/unit/test_shared_layer.py services/memory-service/tests/test_memory_service.py evolution/evolution-lab/tests/test_evolution_lab_service.py apps/jarvis_console/tests/test_console.py` passou com 98 testes.

### MB-163

- `id`: `MB-163`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `memoria`, `observabilidade`, `produto_operador`
- `map_ids`: `MEM-005`, `MEM-006`, `OP-006`, `OBS-005`
- `workflow_profile_afetado`: `operational_readiness_workflow`
- `micro_objetivo`: expor ao operador quais memorias e procedimentos influenciaram a missao, por que foram selecionados e quais foram ignorados.
- `justificativa_arquitetural`: memoria causal so e confiavel se o operador conseguir auditar uso, nao uso e relevancia.
- `arquivos/servicos_principais`: `services/observability-service`, `services/memory-service`, `apps/jarvis_console`, `tests`
- `dependencias`: `MB-161`, `MB-162`
- `criterio_de_aceite`: console/dashboard mostra memoria usada, memoria ignorada, razoes e evidencias sem escrever memoria nem alterar decisao final.
- `gate_minimo`: testes direcionados de observabilidade/console e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: `observability-service` agora consolida `memory_influence_used_refs`, `memory_influence_ignored_refs`, `memory_influence_reasons` e `memory_influence_evidence_refs`; `jarvis-console operator-dashboard` mostra esses sinais em modo read-only, sem escrever memoria ou alterar decisao final.
- `evidencia_de_fechamento`: `pytest services/observability-service/tests/test_observability_service.py apps/jarvis_console/tests/test_console.py` passou com 78 testes.

### MB-164

- `id`: `MB-164`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `governanca`, `soberania`, `politica_runtime`
- `map_ids`: `GOV-007`, `COG-001`, `ACT-002`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `decision_risk_workflow`
- `micro_objetivo`: formalizar `autonomy_ladder` como contrato compartilhado runtime, com niveis, limites, confirmacoes humanas e capacidade maxima permitida por request/missao.
- `justificativa_arquitetural`: autonomia nao pode permanecer apenas como texto; o runtime precisa carregar explicitamente o nivel permitido.
- `arquivos/servicos_principais`: `shared/contracts`, `shared/schemas`, `shared/events`, `services/governance-service`, `services/orchestrator-service`, `tests`
- `dependencias`: `MB-163`
- `criterio_de_aceite`: existe contrato/schema/evento de autonomia; requests e missoes podem declarar nivel permitido; nenhum nivel concede autopromocao ou bypass de governanca.
- `gate_minimo`: testes direcionados de shared/governance/orchestrator e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: `AutonomyLadderContract`, schema e evento `autonomy_ladder_declared` formalizam niveis runtime de autonomia; `InputContract`, plano, governanca, dispatch e eventos agora carregam requested/max/effective level, status de downgrade, confirmacao humana, acoes permitidas/bloqueadas e bloqueio explicito de autopromocao/core mutation.
- `evidencia_de_fechamento`: `pytest tests/unit/test_shared_layer.py services/governance-service/tests/test_governance_service.py services/orchestrator-service/tests/test_orchestrator_service.py` passou com 61 testes.

### MB-165

- `id`: `MB-165`
- `prioridade`: `P0`
- `status`: `done`
- `eixo_do_mestre`: `governanca`, `operacao`, `ferramentas`
- `map_ids`: `GOV-007`, `GOV-005`, `ACT-002`, `ACT-003`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: aplicar a autonomia permitida em governanca, dispatch operacional e console, bloqueando acoes acima do nivel autorizado.
- `justificativa_arquitetural`: contrato de autonomia so tem valor se afetar autorizacao real de capacidade e operacao.
- `arquivos/servicos_principais`: `services/governance-service`, `services/orchestrator-service`, `services/operational-service`, `apps/jarvis_console`, `tests`
- `dependencias`: `MB-164`
- `criterio_de_aceite`: decisoes e eventos mostram nivel de autonomia, limite aplicado, motivo de allow/block/defer e acao exigida do operador.
- `gate_minimo`: testes direcionados de governanca/orquestracao/operacional/console e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: governanca agora bloqueia claims proibidos de autonomia e defere capability acima de `max_autonomy_capability_mode`; `operational-service` falha dispatch acima do limite sem gerar artefato; `observability-service` e `jarvis-console operator-dashboard` mostram nivel efetivo, status do ladder, limite aplicado, confirmacao humana e acoes bloqueadas.
- `evidencia_de_fechamento`: `pytest services/governance-service/tests/test_governance_service.py services/orchestrator-service/tests/test_orchestrator_service.py services/operational-service/tests/test_operational_service.py services/observability-service/tests/test_observability_service.py apps/jarvis_console/tests/test_console.py` passou com 130 testes.

### MB-166

- `id`: `MB-166`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `evolucao`, `release`, `governanca`
- `map_ids`: `EVL-006`, `GOV-009`, `DOC-010`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: definir checklist executavel de promocao sandbox-to-release para aprendizados revisados e candidatos evolutivos.
- `justificativa_arquitetural`: o sistema ja cria propostas e guidance, mas precisa de caminho explicito, testavel e reversivel para promocao futura.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `tools`, `docs/operations`, `shared/contracts`, `tests`
- `dependencias`: `MB-165`
- `criterio_de_aceite`: checklist inclui evidencia, testes, rollback, gate, escopo e aprovacao humana; propostas continuam sem promocao automatica.
- `gate_minimo`: testes direcionados de evolution-lab/tools e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: `SandboxToReleaseChecklistContract` e schema canonico agora formalizam escopo, revisao humana, evidencias, testes, rollback, gates obrigatorios e blockers; `evolution-lab` constroi o checklist a partir da proposta/revisao, rejeita revisao de outra proposta e preserva `automatic_promotion_allowed=false` e `core_mutation_allowed=false`.
- `evidencia_de_fechamento`: `pytest tests/unit/test_shared_layer.py evolution/evolution-lab/tests/test_evolution_lab_service.py` passou com 33 testes; `python tools/engineering_gate.py --mode standard` passou integralmente; `docs/operations/release-and-change-management.md` registra que `ready_for_release_review` nao constitui permissao de promocao.

### MB-167

- `id`: `MB-167`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `evolucao`, `release`, `observabilidade`
- `map_ids`: `EVL-006`, `GOV-009`, `OBS-004`
- `workflow_profile_afetado`: `governance_boundary_workflow`
- `micro_objetivo`: tornar o checklist de promocao verificavel por runtime/tools, com eventos observaveis e conclusao explicita de release.
- `justificativa_arquitetural`: promocao governada precisa produzir evidencia auditavel, nao depender de leitura manual solta.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `services/observability-service`, `tools/verify_release_signal_baseline.py`, `tools/engineering_gate.py`, `tests`
- `dependencias`: `MB-166`
- `criterio_de_aceite`: release/promotion check retorna status, blockers, evidencias e decisao; falhas bloqueiam promocao.
- `gate_minimo`: testes direcionados de evolution/observability/tools e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: `PromotionGateDecisionContract` e schema canonico separam checklist, verificacao de release e autorizacao humana; `evolution-lab` valida gates intrinsecos a partir da evidencia real, aceita somente gates externos conhecidos, produz blockers/missing gates e payload `promotion_gate_evaluated`; `observability-service` consolida a decisao e `verify_release_signal_baseline.py` verifica cenarios pass/block.
- `evidencia_de_fechamento`: `pytest tests/unit/test_shared_layer.py evolution/evolution-lab/tests/test_evolution_lab_service.py services/observability-service/tests/test_observability_service.py tests/unit/test_verify_release_signal_baseline.py` passou com 82 testes; `python tools/verify_release_signal_baseline.py` concluiu com grammar coerente; `python tools/engineering_gate.py --mode standard` passou integralmente.

### MB-168

- `id`: `MB-168`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `superficies/operador`, `continuidade`, `governanca`
- `map_ids`: `SFC-003`, `OP-003`, `OP-006`, `OP-010`
- `workflow_profile_afetado`: `operational_readiness_workflow`
- `micro_objetivo`: expandir cockpit textual do operador para objetivos, work items, artefatos, revisoes, autonomia, memorias usadas e proximas decisoes em uma visao consolidada.
- `justificativa_arquitetural`: o operador precisa de um cockpit pratico antes de qualquer UI rica ou superficie nova.
- `arquivos/servicos_principais`: `apps/jarvis_console`, `services/orchestrator-service`, `services/observability-service`, `services/memory-service`, `tests`
- `dependencias`: `MB-163`, `MB-165`, `MB-167`
- `criterio_de_aceite`: comando de cockpit mostra estado consolidado read-only, limites, decisoes pendentes e proximo passo; nao escreve memoria nem executa tarefa.
- `gate_minimo`: testes direcionados de console/orchestrator/observability e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: `operator-dashboard` agora consolida status/contagens de objetivo, work items, checkpoints e artefatos; detalhes da revisao; memoria e autonomia; evidencia/status/blockers do promotion gate; e uma fila ordenada de decisoes humanas com `cockpit_status`, `pending_decisions`, `next_operator_decision` e `next_operator_step`, mantendo a superficie read-only.
- `evidencia_de_fechamento`: `pytest apps/jarvis_console/tests/test_console.py apps/jarvis_console/tests/test_console_end_to_end.py` passou com 38 testes; cobertura inclui missao real, estado global vazio e consolidacao de revisao, promotion gate e confirmacao de autonomia; `python tools/engineering_gate.py --mode standard` passou integralmente.

### MB-169

- `id`: `MB-169`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `sintese`, `produto_operador`, `continuidade`
- `map_ids`: `OP-008`, `OBS-005`, `COG-010`
- `workflow_profile_afetado`: `strategic_direction_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: gerar relatorio humano compacto de progresso de missao/projeto a partir de estado canonico, experiencia/reflexao, artefatos e estrategia de horizonte longo.
- `justificativa_arquitetural`: utilidade diaria exige resumo legivel de andamento, riscos e proximas acoes, nao apenas eventos brutos.
- `arquivos/servicos_principais`: `engines/synthesis-engine`, `services/orchestrator-service`, `apps/jarvis_console`, `services/observability-service`, `tests`
- `dependencias`: `MB-168`
- `criterio_de_aceite`: relatorio mostra progresso, pendencias, riscos, artefatos, memoria influente, aprendizados e proxima acao auditavel.
- `gate_minimo`: testes direcionados de synthesis/orchestrator/console e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: `MissionProgressReportContract` e schema canonico formalizam relatorio derivado/read-only; `synthesis-engine` compoe texto humano com progresso, pendencias, riscos, memoria, aprendizado, estrategia e proxima acao; `orchestrator-service` coleta somente estado canonico e emite `mission_progress_report_generated`; observabilidade audita os sinais e `jarvis-console progress-report` expoe o resultado.
- `evidencia_de_fechamento`: `pytest tests/unit/test_shared_layer.py engines/synthesis-engine/tests/test_synthesis_engine.py services/orchestrator-service/tests/test_orchestrator_service.py services/observability-service/tests/test_observability_service.py apps/jarvis_console/tests/test_console.py apps/jarvis_console/tests/test_console_end_to_end.py` passou com 156 testes; `python tools/engineering_gate.py --mode standard` passou integralmente.

### MB-170

- `id`: `MB-170`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `experiencia`, `feedback`, `evolucao`
- `map_ids`: `OP-007`, `MEM-003`, `EVL-002`, `OBS-009`
- `workflow_profile_afetado`: `operational_readiness_workflow`
- `micro_objetivo`: capturar feedback explicito do operador apos missoes e injeta-lo em experiencia/reflexao bounded.
- `justificativa_arquitetural`: aprendizado sem feedback humano explicito fica dependente demais de inferencia operacional.
- `arquivos/servicos_principais`: `apps/jarvis_console`, `services/memory-service`, `evolution/evolution-lab`, `services/orchestrator-service`, `tests`
- `dependencias`: `MB-169`
- `criterio_de_aceite`: operador consegue registrar feedback estruturado; experiencia/reflexao carrega o sinal; proposta evolutiva continua em revisao humana.
- `gate_minimo`: testes direcionados de console/memory/evolution/orchestrator e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: `OperatorFeedbackContract`, schema e evento `operator_feedback_recorded` formalizam feedback explicito bounded; governanca valida experiencia/reflexao, rating, refs e limites; memoria canonica anexa resumo, evidencias e sinais; `evolution-lab` cria proposta `operator_feedback_improvement` sandbox-only; observabilidade audita o sinal e `jarvis-console mission-feedback` fecha o caminho humano sem autopromocao.
- `evidencia_de_fechamento`: 181 testes focados passaram em shared, experience/reflection, governance, evolution, orchestrator, observability e console; `python tools/engineering_gate.py --mode standard` passou integralmente apos sincronizacao documental.

### MB-171

- `id`: `MB-171`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `dominios`, `especialistas`, `conhecimento`, `evals`
- `map_ids`: `SPC-006`, `KNW-007`, `OBS-006`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `domain_onboarding_workflow`
- `micro_objetivo`: criar protocolo minimo de onboarding de dominio com criterios, registro, knowledge pack, rota, especialista, testes e evals.
- `justificativa_arquitetural`: novos dominios nao podem entrar como conteudo solto; precisam de contrato, teste e rota governada.
- `arquivos/servicos_principais`: `shared/domain_registry.py`, `shared/specialist_registry.py`, `knowledge-service`, `docs/architecture`, `tests`
- `dependencias`: `MB-170`
- `criterio_de_aceite`: existe protocolo e baseline de validacao para novo dominio sem promover especialista profundo automaticamente.
- `gate_minimo`: testes direcionados de registry/knowledge e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `high`
- `modelo_recomendado`: `gpt-5.4`
- `impacto_no_baseline`: novos dominios agora possuem contratos tipados de candidato, knowledge pack versionado e assessment sem mutacao, com rota, workflow, testes, eval, rollback, especialista bounded e revisao humana obrigatoria antes de qualquer alteracao dos registries ativos.
- `evidencia_de_fechamento`: manifest baseline reproduzivel avaliado pelo `knowledge-service`, registries ativos preservados e testes direcionados cobrindo sucesso, colisao, dominio desconhecido, ausencia de controles e tentativa de ativacao/promocao; gate padrao aprovado.

### MB-172

- `id`: `MB-172`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `evals`, `dominios`, `qualidade`
- `map_ids`: `OBS-006`, `SPC-006`, `KNW-004`
- `workflow_profile_afetado`: `domain_onboarding_workflow`
- `micro_objetivo`: criar baseline de eval pack por dominio/rota promovida, reutilizavel para validar respostas, memoria e especialista.
- `justificativa_arquitetural`: dominios so devem escalar se houver medicao minima de qualidade e regressao.
- `arquivos/servicos_principais`: `tools`, `tests`, `shared/domain_registry.py`, `services/observability-service`, `docs/operations`
- `dependencias`: `MB-171`
- `criterio_de_aceite`: existe padrao de eval pack e pelo menos um pacote baseline exercitando rota/dominio sem depender de rede externa.
- `gate_minimo`: testes direcionados de tools/observability e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: o sistema agora possui contrato e runner offline reutilizavel de eval por dominio/rota promovida, cobrindo decisao, rota, refs canonicas, workflow, especialista, resposta, memoria causal, eventos e trace sem transformar resultado verde em autorizacao de promocao.
- `evidencia_de_fechamento`: `domain_analysis_eval_pack_v1.json` executou dois casos consecutivos pelo Core real com `pass_rate=1.0`; o follow-up comprovou `causal_guidance`, o comando operacional gerou artefatos locais e o gate padrao foi aprovado.

### MB-173

- `id`: `MB-173`
- `prioridade`: `P2`
- `status`: `done`
- `eixo_do_mestre`: `conhecimento`, `sintese`, `governanca`
- `map_ids`: `KNW-003`, `KNW-004`, `KNW-008`
- `workflow_profile_afetado`: `research_synthesis_workflow`, `strategic_direction_workflow`
- `micro_objetivo`: fortalecer proveniencia, freshness e conflito/incerteza em respostas baseadas em conhecimento.
- `justificativa_arquitetural`: um assistente de dominios amplos precisa indicar de onde vem a informacao, validade temporal e conflitos.
- `arquivos/servicos_principais`: `services/knowledge-service`, `engines/synthesis-engine`, `services/governance-service`, `tests`
- `dependencias`: `MB-172`
- `criterio_de_aceite`: respostas com conhecimento carregam source refs, freshness status e incertezas quando aplicavel; ausencia de fonte fica visivel.
- `gate_minimo`: testes direcionados de knowledge/synthesis/governance e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: respostas baseadas em conhecimento agora carregam evidencia estruturada por fonte, freshness derivada do timestamp da request, conflito/incerteza e qualificacao governada de uso ate a sintese e os eventos, sem mutar a permissao principal nem atribuir confianca implicita a fonte sem metadata.
- `evidencia_de_fechamento`: testes direcionados cobrem corpus interno vigente, proveniencia ausente, janela expirada, conflito declarado, politica governada e propagacao ponta a ponta; `docs/architecture/knowledge-provenance-and-freshness.md` registra semantica, limites e operacao.

### MB-174

- `id`: `MB-174`
- `prioridade`: `P2`
- `status`: `done`
- `eixo_do_mestre`: `observabilidade`, `qualidade`, `documentacao`
- `map_ids`: `OBS-007`, `OBS-008`, `DOC-010`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `governance_boundary_workflow`
- `micro_objetivo`: consolidar dashboard de regressao/readiness por capacidade, incluindo sinais de testes, gates, docs stale e status drift.
- `justificativa_arquitetural`: uma fila maior exige leitura de saude acumulada para evitar regressao silenciosa.
- `arquivos/servicos_principais`: `tools`, `services/observability-service`, `docs/implementation`, `apps/jarvis_console`, `tests`
- `dependencias`: `MB-173`
- `criterio_de_aceite`: existe relatorio/CLI compacto de readiness por capacidade e drift documental/status, com gate padrao passando.
- `gate_minimo`: testes direcionados de tools/observability/console e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: existe dashboard read-only de readiness por capacidade, gate/testes, documentos e fila; o agregador distingue baseline, candidato e deferred, detecta status drift, preserva historico JSON e nunca autoriza release autonomo.
- `evidencia_de_fechamento`: `tools/readiness_dashboard.py`, `jarvis-console readiness-dashboard`, contratos/schemas e agregacao no `observability-service` possuem testes de parsing, score, drift, blockers, historico e console; `docs/operations/regression-readiness-dashboard.md` registra uso e limites.

### MB-175

- `id`: `MB-175`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `evolucao`, `memoria procedural`, `controle de programa`
- `map_ids`: `EVL-007`, `MEM-003`, `MEM-006`, `EVL-008`, `OBS-009`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `research_synthesis_workflow`
- `micro_objetivo`: repriorizar o pos-`MB-174` para evolucao governada de skills e workflows a partir de padroes recorrentes reais.
- `justificativa_arquitetural`: experiencia/reflexao, playbooks, review, sandbox e promotion gate ja existem; o maior elo faltante e transformar recorrencia observada em candidata reutilizavel sem ativacao autonoma.
- `arquivos/servicos_principais`: `docs/implementation`, `HANDOFF.md`, `CHANGELOG.md`
- `dependencias`: `MB-174`
- `criterio_de_aceite`: existe fila ordenada `MB-176` a `MB-189`, com WIP 1, criterios de aceite, gates e limites de fase; somente `MB-176` fica ready.
- `gate_minimo`: `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: a proxima fase aprofunda a autoevolucao operacional por evidencia, skills e workflows governados, mantendo adapters amplos, superficies e self-modification fora da fila.
- `evidencia_de_fechamento`: fila `MB-176` a `MB-189` derivada do mapa mestre e do warning ativo `EVL-007` no dashboard, com `MB-176` como unico item tecnico ready.

### MB-176

- `id`: `MB-176`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `evolucao`, `experiencia`, `observabilidade`
- `map_ids`: `EVL-007`, `MEM-003`, `OBS-009`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `research_synthesis_workflow`
- `micro_objetivo`: gerar relatorio bounded de padroes recorrentes a partir de experiencias, reflexoes e feedbacks com escopo compativel.
- `justificativa_arquitetural`: skill candidata exige recorrencia e evidencia antes de qualquer mineracao ou registry.
- `arquivos/servicos_principais`: `shared/contracts`, `services/memory-service`, `services/observability-service`, `tests`
- `dependencias`: `MB-175`
- `criterio_de_aceite`: duas ou mais experiencias compativeis podem formar pattern evidence com workflow, rota, dominio, outcome, evidencias, confidence bounded e bloqueio explicito de criacao/promocao automatica de skill.
- `gate_minimo`: testes direcionados de memory/observability/shared e `python tools/engineering_gate.py --mode standard`
- `depende_do_operador`: `nao`
- `modo_de_raciocinio_recomendado`: `medium`
- `modelo_recomendado`: `gpt-5.3-codex`
- `impacto_no_baseline`: experiencias, reflexoes e feedbacks canonicos agora podem ser agregados por workflow, rota e dominio em pattern evidence read-only, com threshold, confidence bounded, conflitos e blockers explicitos.
- `evidencia_de_fechamento`: contratos/schemas `RecurringPatternEvidenceContract` e `RecurringPatternReportContract`, agregador deterministico compartilhado, builders em memoria/observabilidade e testes de recorrencia valida, insuficiencia, conflito e correcao ponta a ponta; nenhuma skill e criada ou promovida.

### MB-177

- `id`: `MB-177`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `evolucao`, `skills`, `memoria procedural`
- `map_ids`: `EVL-007`, `MEM-006`, `GOV-004`
- `workflow_profile_afetado`: `operational_readiness_workflow`
- `micro_objetivo`: formalizar contrato e registry persistente de skill candidata, versionada e inativa.
- `justificativa_arquitetural`: separar candidata de playbook, skill formal e skill ativa evita promocao implicita.
- `arquivos/servicos_principais`: `shared/contracts`, `services/memory-service`, `evolution/evolution-lab`, `tests`
- `dependencias`: `MB-176`
- `criterio_de_aceite`: skill candidata possui inputs, outputs, dominio, especialista, tools permitidas, risco, versao, evidencias, failure modes, rollback e status humano; ativacao automatica e mutacao do Core ficam falsas.
- `gate_minimo`: testes direcionados de memory/evolution/shared e gate padrao
- `impacto_no_baseline`: existe registry canonico SQLite/PostgreSQL para skill candidata versionada, bounded, inativa, consultavel e imutavel por versao, sem consumo runtime.
- `evidencia_de_fechamento`: `SkillCandidateContract`/schema, `StoredSkillCandidate`, tabela/index/filtros e enforcement no `memory-service`; testes comprovam persistencia, idempotencia, contencao de claims inseguros, colisao de versao e imutabilidade.

### MB-178

- `id`: `MB-178`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `evolucao`, `skills`
- `map_ids`: `EVL-007`, `MEM-003`, `MEM-006`
- `workflow_profile_afetado`: `operational_readiness_workflow`, `research_synthesis_workflow`
- `micro_objetivo`: implementar Skill Miner bounded que converte pattern evidence elegivel em skill candidata.
- `justificativa_arquitetural`: mineracao deve ser deterministica, auditavel e incapaz de ativar skill.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `services/memory-service`, `tests`
- `dependencias`: `MB-177`
- `criterio_de_aceite`: threshold de recorrencia, outcomes, conflitos e evidencias controla geracao; insuficiencia produz blocker visivel, nunca candidata otimista.
- `gate_minimo`: testes direcionados de evolution/memory e gate padrao
- `impacto_no_baseline`: o `evolution-lab` possui miner deterministico que converte somente pattern evidence elegivel e spec bounded em candidata inativa idempotente; qualquer falha retorna resultado bloqueado sem candidata.
- `evidencia_de_fechamento`: `SkillMiningRequestContract`/`SkillMiningResultContract`, eligibility gate por threshold/outcome/confidence/refs/conflitos/risco/tools e testes elegivel, insuficiente, conflitante, inseguro e miner-to-registry ponta a ponta.

### MB-179

- `id`: `MB-179`
- `prioridade`: `P1`
- `status`: `done`
- `eixo_do_mestre`: `evolucao`, `governanca`, `evals`
- `map_ids`: `EVL-007`, `EVL-005`, `EVL-006`, `GOV-009`
- `workflow_profile_afetado`: `governance_boundary_workflow`, `operational_readiness_workflow`
- `micro_objetivo`: conectar skill candidata a review humano, eval sandbox e promotion checklist sem ativacao runtime.
- `justificativa_arquitetural`: candidato reutilizavel precisa de prova e decisao humana antes de consumo.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `services/governance-service`, `services/observability-service`, `tests`
- `dependencias`: `MB-178`
- `criterio_de_aceite`: review/eval/checklist carregam skill/version/evidencias/testes/rollback; resultado verde permanece pendente de promocao humana separada.
- `gate_minimo`: testes direcionados de evolution/governance/observability e gate padrao
- `impacto_no_baseline`: skill candidata inativa agora percorre proposta persistida, review humano, eval sandbox derivado, checklist e promotion gate com identidade/versao causal, sem ativacao runtime.
- `evidencia_de_fechamento`: `SkillSandboxCaseResultContract`/`SkillSandboxEvalContract`, proposta skill-aware, review metadata, gate intrinseco `skill_sandbox_eval` e testes ponta a ponta pass/block preservam `promotion_authorized=false`.

### MB-180

- `id`: `MB-180`
- `prioridade`: `P1`
- `status`: `completed`
- `eixo_do_mestre`: `operador`, `skills`, `observabilidade`
- `map_ids`: `EVL-007`, `OP-010`, `SFC-004`
- `workflow_profile_afetado`: `operational_readiness_workflow`
- `micro_objetivo`: expor pattern evidence, skill candidata, eval, review e blockers no console read-only.
- `justificativa_arquitetural`: o operador precisa compreender e revisar a evolucao proposta.
- `arquivos/servicos_principais`: `apps/jarvis_console`, `services/observability-service`, `tests`, `docs/operations`
- `dependencias`: `MB-179`
- `criterio_de_aceite`: console mostra origem, recorrencia, escopo, risco, versao, testes, rollback e status sem executar/promover skill.
- `gate_minimo`: testes de console/observability, E2E afetado e gate padrao
- `impacto_no_baseline`: `skill-evolution` correlaciona pattern, candidata inativa, proposta, review e sandbox em leitura sanitizada, sem escrita, ativacao ou promocao.
- `evidencia_de_fechamento`: contratos `SkillEvolutionOperator*`, projection no observability, console com filtros bounded, runbook e E2E real preservam `runtime_activation_allowed=false` e `promotion_authorized=false`.

### MB-181

- `id`: `MB-181`
- `prioridade`: `P2`
- `status`: `ready`
- `eixo_do_mestre`: `workflows`, `evolucao`
- `map_ids`: `COG-006`, `EVL-008`, `DOC-004`
- `workflow_profile_afetado`: todos os workflows promovidos do registry
- `micro_objetivo`: formalizar versao e lifecycle de workflow_profile sem alterar registry ativo.
- `justificativa_arquitetural`: comparar workflows exige identidade/versionamento antes de gerar variantes.
- `arquivos/servicos_principais`: `shared/contracts`, `shared/domain_registry.py`, `evolution/evolution-lab`, `tests`
- `dependencias`: `MB-180`
- `criterio_de_aceite`: versoes baseline/candidate possuem passos, checkpoints, decisions, evidencias e rollback; registry ativo permanece imutavel.
- `gate_minimo`: testes de shared/evolution/domain registry e gate padrao

### MB-182

- `id`: `MB-182`
- `prioridade`: `P2`
- `status`: `blocked`
- `eixo_do_mestre`: `workflows`, `evolucao`, `memoria`
- `map_ids`: `EVL-008`, `COG-006`, `COG-007`
- `workflow_profile_afetado`: workflows promovidos com pattern evidence elegivel
- `micro_objetivo`: gerar variante candidata de workflow a partir de evidencia revisada.
- `justificativa_arquitetural`: reflexao isolada nao pode reescrever workflow; somente pattern evidence revisada pode propor variante.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `services/memory-service`, `tests`
- `dependencias`: `MB-181`
- `criterio_de_aceite`: candidata explicita delta de passos/checkpoints/criteria, evidencia, risco e rollback, sem escrita no registry ativo.
- `gate_minimo`: testes de evolution/memory e gate padrao

### MB-183

- `id`: `MB-183`
- `prioridade`: `P2`
- `status`: `blocked`
- `eixo_do_mestre`: `evals`, `workflows`, `observabilidade`
- `map_ids`: `EVL-005`, `EVL-008`, `OBS-009`
- `workflow_profile_afetado`: workflow candidato sob avaliacao
- `micro_objetivo`: comparar baseline vs workflow candidate em cenarios offline equivalentes.
- `justificativa_arquitetural`: workflow so pode avancar com ganho mensuravel e ausencia de regressao.
- `arquivos/servicos_principais`: `tools`, `services/observability-service`, `evolution/evolution-lab`, `tests`
- `dependencias`: `MB-182`
- `criterio_de_aceite`: eval mede sucesso, contrato, retrabalho, checkpoints, memoria e regressao; resultado nao autoriza promocao.
- `gate_minimo`: testes de tools/observability/evolution e gate padrao

### MB-184

- `id`: `MB-184`
- `prioridade`: `P2`
- `status`: `blocked`
- `eixo_do_mestre`: `governanca`, `workflows`, `rollback`
- `map_ids`: `EVL-006`, `EVL-008`, `GOV-009`
- `workflow_profile_afetado`: workflow candidato aprovado em eval
- `micro_objetivo`: integrar workflow candidate ao promotion gate e rollback manual.
- `justificativa_arquitetural`: promocao de workflow deve reutilizar gates existentes e preservar decisao humana separada.
- `arquivos/servicos_principais`: `evolution/evolution-lab`, `services/governance-service`, `tools`, `tests`
- `dependencias`: `MB-183`
- `criterio_de_aceite`: checklist exige review, eval, release gate e rollback; nenhuma promocao ocorre automaticamente.
- `gate_minimo`: testes de evolution/governance/release e gate padrao

### MB-185

- `id`: `MB-185`
- `prioridade`: `P2`
- `status`: `blocked`
- `eixo_do_mestre`: `roteamento`, `evolucao`, `observabilidade`
- `map_ids`: `COG-003`, `COG-007`, `EVL-008`, `OBS-009`
- `workflow_profile_afetado`: rotas promovidas
- `micro_objetivo`: produzir evidencia de adaptacao de routing sem mutar rota ativa.
- `justificativa_arquitetural`: acerto de rota/especialista deve ser medido antes de qualquer ajuste.
- `arquivos/servicos_principais`: `services/observability-service`, `evolution/evolution-lab`, `tools`, `tests`
- `dependencias`: `MB-184`
- `criterio_de_aceite`: relatorio compara rota esperada/observada, outcome, memoria e especialista e gera somente candidata revisavel.
- `gate_minimo`: testes de observability/evolution/tools e gate padrao

### MB-186

- `id`: `MB-186`
- `prioridade`: `P2`
- `status`: `blocked`
- `eixo_do_mestre`: `memoria semantica`, `memoria procedural`, `planejamento`
- `map_ids`: `MEM-005`, `MEM-006`, `COG-007`, `GOV-004`
- `workflow_profile_afetado`: workflows promovidos
- `micro_objetivo`: endurecer politica causal de influencia semantica/procedural com prioridade, conflito e non-use auditavel.
- `justificativa_arquitetural`: skills/workflows revisados precisam coexistir com memoria sem influencia indiscriminada.
- `arquivos/servicos_principais`: `services/memory-service`, `engines/planning-engine`, `services/governance-service`, `tests`
- `dependencias`: `MB-185`
- `criterio_de_aceite`: politica seleciona ou ignora memoria por escopo/evidencia/conflito e registra razao na decisao e sintese.
- `gate_minimo`: testes de memory/planning/governance/orchestrator e gate padrao

### MB-187

- `id`: `MB-187`
- `prioridade`: `P2`
- `status`: `blocked`
- `eixo_do_mestre`: `memoria`, `operador`, `governanca`
- `map_ids`: `MEM-007`, `MEM-008`, `MEM-009`, `GOV-004`
- `workflow_profile_afetado`: `memory_lifecycle_workflow`
- `micro_objetivo`: consolidar fila humana de revisao, consolidacao e expiracao de memoria.
- `justificativa_arquitetural`: memoria evolutiva crescente exige manutencao humana verificavel, nao scheduler autonomo.
- `arquivos/servicos_principais`: `services/memory-service`, `services/governance-service`, `apps/jarvis_console`, `tests`
- `dependencias`: `MB-186`
- `criterio_de_aceite`: operador revisa candidatos de consolidacao/arquivo/expiracao com evidencias e rollback; nenhuma manutencao critica e autonoma.
- `gate_minimo`: testes de memory/governance/console e gate padrao

### MB-188

- `id`: `MB-188`
- `prioridade`: `P2`
- `status`: `blocked`
- `eixo_do_mestre`: `observabilidade`, `evolucao`, `utilidade`
- `map_ids`: `OBS-005`, `OBS-009`, `EVL-005`, `EVL-008`
- `workflow_profile_afetado`: workflows com evidencia longitudinal
- `micro_objetivo`: medir ao longo do tempo se skills, workflows e memoria revisados melhoram missoes futuras.
- `justificativa_arquitetural`: autoevolucao util exige ganho sustentado, nao apenas eval pontual.
- `arquivos/servicos_principais`: `services/observability-service`, `tools`, `apps/jarvis_console`, `tests`
- `dependencias`: `MB-187`
- `criterio_de_aceite`: relatorio longitudinal mede sucesso, retrabalho, feedback, regressao e rollback por versao, sem converter score em promocao.
- `gate_minimo`: testes de observability/tools/console e gate padrao

### MB-189

- `id`: `MB-189`
- `prioridade`: `P2`
- `status`: `blocked`
- `eixo_do_mestre`: `qualidade`, `documentacao`, `readiness`
- `map_ids`: `OBS-007`, `OBS-008`, `DOC-010`
- `workflow_profile_afetado`: `operational_readiness_workflow`
- `micro_objetivo`: fechar o slice de evolucao de skills/workflows com readiness, regressao e docs sincronizados.
- `justificativa_arquitetural`: a fase precisa terminar com evidencia acumulada e proxima decisao explicita.
- `arquivos/servicos_principais`: `tools`, `docs/implementation`, `HANDOFF.md`, `CHANGELOG.md`, `tests`
- `dependencias`: `MB-188`
- `criterio_de_aceite`: dashboard registra capacidades/status sem drift, gate padrao passa e nenhuma promocao/autonomia fora de escopo foi aberta.
- `gate_minimo`: dashboard com gate padrao e document guardrails

## 5. Regras de manutencao da fila

- o proximo item puxado deve ser o primeiro `ready` de maior prioridade sem dependencia aberta;
- nenhum item novo entra em `ready` sem `criterio_de_aceite` e `gate_minimo`;
- quando um item for fechado, registrar em uma linha o impacto no baseline e sincronizar `HANDOFF.md`, snapshot e `CHANGELOG.md` se o estado real mudou;
- `HANDOFF.md` nao deve voltar a carregar a fila micro;
- este documento e a unica fila micro ativa do corte corrente.

Estado atual da fila:

- o lote `pre-v3 hardening` foi concluido e preservado como baseline fechado;
- `protective intelligence foundation` permanece mapeada, mas foi reclassificada para `deferred`;
- `MB-027` a `MB-031` nao devem ser puxados sem repriorizacao macro explicita do operador;
- `MB-032` a `MB-036` foram concluidos e fecharam o lote atual de maturacao do nucleo cognitivo;
- `MB-037` a `MB-040` foram concluidos e fecharam o lote de autoevolucao governada, composicao de mentes mais profunda, telemetria viva de memoria e evals formais por eixo/workflow;
- `docs/architecture/technology-absorption-order.md` agora formaliza a ordem oficial de traducao disciplinada das referencias externas para o JARVIS;
- `MB-041` a `MB-046` foram concluidos e fecharam o lote de absorcao disciplinada da Onda 1;
- `MB-047` a `MB-051` formaram o lote de maturacao causal final do nucleo e ja foram concluidos;
- `MB-052` a `MB-056` foram concluidos e fecharam o lote atual de maturacao adaptativa do nucleo;
- `MB-052` tornou a metacognicao adaptativa mid-flow observavel por `plan_refined`, `response_synthesized` e auditoria local;
- `MB-053` transformou lifecycle de memoria em comportamento operacional vivo para recovery, packet guiado e reuso recorrente de especialista;
- `MB-054` fez memoria relevante influenciar de forma mais causal rota, hints especializados e ranking de continuidade;
- `MB-055` aprofundou a composicao de mentes como sinal causal do runtime e dos gates de release;
- `MB-056` formalizou a matriz de readiness da Onda 2 como experimento controlado subordinado aos sinais do nucleo;
- `MB-057` a `MB-061` foram concluidos e fecharam o lote de intervencao adaptativa governada do nucleo;
- `MB-057` e `MB-058` agora tratam `adaptive_intervention_*` como contrato soberano do runtime em `planning`, `orchestrator`, dispatch e fluxo opcional de `LangGraph`, sem transformar a intervencao em fallback generico;
- `MB-059` e `MB-060` agora tornam a efetividade dessas intervencoes parte do baseline auditavel em `observability`, piloto, comparadores, `evolution-lab`, `evolution_from_pilot` e verificadores de release;
- `MB-061` fecha o lote com docs vivos e gate sincronizados, deixando a fila micro novamente sem item `ready` ate nova repriorizacao explicita do nucleo;
- `MB-062` inaugurou o lote seguinte e ja foi concluido: a prioridade entre `memory_review_checkpoint` e `specialist_reevaluation` agora respeita guidance soberano por `workflow_profile`;
- `MB-063` tambem foi concluido: `observability-service`, piloto, comparadores e leitura de release agora expõem `adaptive_intervention_policy_status`, distinguindo `policy_aligned`, `mandatory_override` e `attention_required` como evidencia auditavel por workflow;
- `MB-064` a `MB-066` agora tambem foram concluidos: a sintese final e `response_synthesized` explicam a prioridade do workflow e o checkpoint/gate preservado, enquanto `evolution-lab`, `evolution_from_pilot.py` e `compare_orchestrator_paths.py` passaram a tratar a politica de intervencao como insumo formal de refinamento;
- `docs/implementation/unified-gap-and-absorption-backlog.md` agora consolida o que ainda falta no sistema, integrando gaps do nucleo, traducao tecnologica, superficies, evolucao e pesquisa em um unico mapa macro para a proxima repriorizacao;
- `MB-067` a `MB-071` foram concluidos e fecharam o lote do nucleo para decisao soberana de capacidades, ferramentas e handoffs bounded, derivado de `SG-001`, `TA-001` e `TA-005`;
- `planning`, `orchestrator`, `governance`, `observability`, piloto, comparadores e `evolution-lab` agora carregam `capability_decision_*`, `capability_effectiveness` e `handoff_adapter_status` como baseline auditavel do runtime;
- `MB-072` a `MB-076` foram concluidos e fecharam o lote do nucleo para manutencao ativa de memoria viva, derivado de `SG-004` e `TA-003`;
- `memory-service`, `planning`, `orchestrator`, `observability`, piloto, comparadores, `evolution-lab` e verificadores de release agora tratam `memory_maintenance_*`, compaction e recall cross-session como slice soberano, auditavel e refinavel do runtime;
- `MB-077` a `MB-081` foram concluidos e fecharam o lote do nucleo para arbitragem mais declarativa de `mente -> dominio -> especialista`, derivado de `SG-005`;
- `MB-077` agora foi concluido: `mind_domain_specialist_contract_*` passou a existir como contrato vivo em `cognitive`, `specialist`, `planning`, `synthesis` e `orchestrator`, distinguindo cadeia autoritativa, override bounded e fallback governado;
- `MB-078` agora foi concluido: selecao, dispatch, artefato operacional e sintese final passaram a obedecer o contrato `mind_domain_specialist` como politica soberana de consumo final e fallback;
- `MB-079` agora tambem foi concluido: `observability-service`, piloto e comparadores passaram a expor `mind_domain_specialist_effectiveness` e `mind_domain_specialist_mismatch_flags` como evidencia formal da arbitragem final;
- `MB-080` e `MB-081` agora tambem foram concluidos: `evolution-lab`, `evolution_from_pilot`, comparadores e verificadores de release passaram a tratar efetividade e mismatch da arbitragem declarativa como insumo formal de `refinement_vectors`, `evaluation_matrix` e leitura de release;
- `MB-082` a `MB-086` foram concluidos e fecharam o lote do nucleo para identidade, missao e politica por request, derivado de `SG-006`;
- `planning`, `governance`, `orchestrator`, `observability`, piloto, comparadores, `evolution-lab` e verificadores de release agora tratam `request_identity_policy` como slice soberano, auditavel e refinavel do runtime;
- `MB-087` a `MB-091` foram concluidos e fecharam o lote de evals expandidas e lane controlada da Onda 2, derivado de `EV-002` + `EV-004`;
- `observability`, piloto, comparadores, `evolution-lab`, verificadores de release e fechadores regeneraveis agora tratam `expanded_eval_*`, `surface_axis_*`, `ecosystem_state_*`, `experiment_lane_*`, `experiment_exit_*` e `promotion_readiness` como baseline comparativo controlado;
- `MB-092` a `MB-096` foram concluidos e fecharam o lote de compile/optimize loops governados, derivado de `EV-003`;
- `shared/optimization_state.py`, `evolution-lab`, comparadores, relatorios, verificadores de baseline/release e fechadores regeneraveis agora tratam `optimization_*` como slice soberano do baseline evolutivo;
- `MB-097` agora foi concluido: `OperationDispatchContract`, `OperationResultContract`, `orchestrator-service`, `operational-service` e eventos internos passaram a carregar estado operacional minimo do ecossistema;
- `MB-098` agora tambem foi concluido: `memory-service`, `shared/memory_registry.py`, `orchestrator-service` e a malha de continuidade passaram a persistir e retomar `ecosystem_state_*` como estado bounded de missao, checkpoint e replay;
- `MB-099` a `MB-101` foram concluidos e fecharam a leitura auditavel, evolutiva, regeneravel e documental desse estado operacional, ainda sem abrir multissuperficie ampla ou substrate operacional fora de fase;
- `MB-102` agora foi concluido: contratos compartilhados, schemas, eventos e `apps/jarvis_console` passaram a carregar identidade minima de superficie, operador e usuario canonico como base soberana para continuidade multissuperficie;
- `MB-103` agora tambem foi concluido: `surface_*` acompanha console, eventos centrais do orquestrador, dispatch, contexto de planning e synthesis input, preservando `through_core_only`;
- `MB-104` agora tambem foi concluido: memoria, session continuity, checkpoints, replay e mission runtime state persistem e recuperam continuidade bounded de superficie;
- `MB-105` agora tambem foi concluido: observabilidade, piloto, comparadores, baseline ativo, `evolution-lab` e verificadores de release expoem `surface_continuity_status`, `linked_surface_count`, `surface_identity_conflict_flags` e readiness multissuperficie sem promover nova UI, voz, web ou API publica;
- `MB-106` agora tambem foi concluido: docs vivos, changelog, snapshot e backlog macro registram `SG-003` + `SO-002` como ponte minima de continuidade multissuperficie, sem abrir produto multicanal amplo;
- `MB-107` a `MB-109` agora foram concluidos como repriorizacao explicita baseada em `EV-001`, registrando `SO-003` como proxima frente tecnica apenas em recorte minimo;
- `MB-110` a `MB-114` foram concluidos como lote de continuidade minima de projetos/objetivos persistentes;
- `MB-115` agora foi concluido: o console expoe o estado persistido de objetivos/projetos por `mission_id`, sem executar acao ou escrever memoria;
- `MB-116` agora foi concluido: o console aplica transicoes bounded de objetivo por governanca, memoria canonica e evento auditavel;
- `MB-117` agora foi concluido: a sintese final expoe estado operacional bounded de objetivo ativo, proxima acao, decisao pendente e artefato relevante quando houver esse contexto;
- `MB-118` agora foi concluido: observabilidade, piloto interno, relatorio e comparador expoem sinais de utilidade operacional de objetivos;
- `MB-119` agora foi concluido: docs vivos registram o fechamento da primeira camada utilizavel de objetivos/projetos para operador humano;
- `MB-120` agora foi concluido: a repriorizacao pos-`MB-119` escolheu estrutura evolutiva e absorcao tecnologica governada como proxima frente, sem abrir novas superficies ou autonomia ampla;
- `MB-121` agora foi concluido: candidatos tecnologicos passam a ter contrato soberano minimo e gramatica de readiness que bloqueia violacao da soberania do nucleo e exige evidencia, testes e rollback para revisao manual;
- `MB-122` agora foi concluido: o `evolution-lab` registra candidatos tecnologicos como propostas `sandbox-only`, com readiness, blockers e politica explicita contra promocao automatica;
- `MB-123` agora foi concluido: observabilidade, piloto interno, relatorio e comparador expoem sinais de absorcao tecnologica governada;
- `MB-124` agora foi concluido: o console expoe candidatos tecnologicos recentes em modo read-only;
- `MB-125` agora foi concluido: docs vivos registram o fechamento da primeira camada operacional de absorcao tecnologica governada;
- `MB-126` agora foi concluido: a repriorizacao pos-`MB-125` escolheu experiencia operacional e reflexao pos-tarefa governada como proxima frente, sem abrir novas superficies, automacao ampla ou self-modification;
- `MB-127` agora foi concluido: contratos compartilhados de `experience_record` e `post_task_reflection` materializam experiencia operacional como materia-prima soberana para autoevolucao governada;
- `MB-128` agora foi concluido: `memory-service` persiste e recupera experiencias/reflexoes como memoria evolutiva bounded, sem abrir memoria temporal relacional rica;
- `MB-129` agora foi concluido: `evolution-lab` transforma reflexoes pos-tarefa em propostas `post_task_reflection_improvement` `sandbox-only`, bloqueando autopromocao e mutacao do nucleo;
- `MB-130` agora foi concluido: observabilidade, relatorio e console read-only expoem sinais e registros de experiencia/reflexao pos-tarefa;
- `MB-131` agora foi concluido: docs vivos registram o fechamento da primeira camada de experiencia/reflexao pos-tarefa governada;
- `MB-132` a `MB-140` foram concluidos como baseline do `Operator Learning Loop`;
- `MB-141` a `MB-145` foram concluidos como controles humanos de revisao evolutiva;
- `MB-146` abriu o lote `Reviewed Learning Feedback Loop`;
- `MB-147` formalizou o contrato de `reviewed_learning_guidance` e sua derivacao no `evolution-lab`;
- `MB-148` conectou `reviewed_learning_guidance` ao runtime de memoria, planejamento e sintese com filtros de escopo;
- `MB-149` fechou medicao baseline vs reviewed-learning-assisted em observabilidade, piloto, relatorio e comparador;
- `MB-150` fechou a leitura operacional no console e na documentacao;
- `MB-151` foi concluido como auditoria documental governada oficial, sem mover, deletar, renomear, mesclar ou remover arquivos;
- `MB-152` foi concluido como mapa de backlinks e sincronizacao segura de documentos ativos defasados, sem mover, deletar, renomear ou mesclar documentos;
- `MB-153` foi concluido como primeiro archive fisico conservador: seis documentos historicos de implementacao foram movidos para `docs/archive/implementation/`, backlinks literais foram reescritos e nenhum documento foi deletado ou mesclado destrutivamente;
- `MB-154` foi concluido como `Implementation Master Map`, consolidando tudo que precisa ser implementado em trilhas, capacidades, status, dependencias, fases e proximos candidatos;
- `MB-155` foi concluido como baseline minimo de dashboard textual do operador por `operator-dashboard`;
- `MB-156` foi concluido como ciclo governado minimo de work items por console, governanca, memoria canonica e eventos auditaveis;
- `MB-157` foi concluido como lifecycle minimo de artefatos vivos por console, governanca, memoria canonica e eventos auditaveis;
- `MB-158` foi concluido como metricas compactas de utilidade operacional em observabilidade e dashboard;
- `MB-159` foi concluido como raciocinio minimo de objetivos de horizonte longo, fechando o lote `MB-155` a `MB-159`;
- `MB-160` foi concluido como repriorizacao pos-`MB-159` a partir de `docs/implementation/implementation-master-map.md`, abrindo a fila maior `MB-161` a `MB-174`;
- `MB-161` foi concluido como anchors de evidencia para memoria semantica em planning/synthesis/observabilidade/console;
- `MB-162` foi concluido como baseline governado de candidatos de playbook procedural;
- `MB-163` foi concluido como superficie auditavel de influencia de memoria em observabilidade e dashboard textual;
- `MB-164` foi concluido como contrato runtime compartilhado de `autonomy_ladder`, sem enforcement amplo ainda;
- `MB-165` foi concluido como enforcement minimo de `autonomy_ladder` em governanca, dispatch operacional, observabilidade e console;
- `MB-166` foi concluido como checklist sandbox-to-release executavel, auditavel e incapaz de autorizar promocao autonoma;
- `MB-167` foi concluido como enforcement runtime/tooling observavel do promotion gate, sem autorizacao autonoma de promocao;
- `MB-168` foi concluido como cockpit textual consolidado e read-only para estado, limites e decisoes do operador;
- `MB-169` foi concluido como relatorio humano compacto derivado do estado canonico, sem escrita ou execucao autonoma;
- `MB-170` foi concluido como feedback explicito governado do operador, persistido em experiencia/reflexao e convertido em proposta sandbox sob revisao humana;
- `MB-171` foi concluido como protocolo governado de onboarding de dominios, sem ativar rota ou promover especialista;
- `MB-172` foi concluido como primeiro eval pack offline reutilizavel por dominio/rota, com agregacao observavel e promocao manual-only;
- `MB-173` foi concluido como baseline de proveniencia, freshness e conflito/incerteza de conhecimento;
- `MB-174` foi concluido como dashboard integrado de regressao/readiness, fechando a fila `MB-161` a `MB-174`; nao ha item tecnico `ready` ate nova repriorizacao explicita pelo mapa mestre;
- `MB-175` foi concluido como repriorizacao pos-`MB-174`, abrindo a fila governada de skill/workflow evolution `MB-176` a `MB-189`;
- `MB-176` a `MB-180` foram concluidos como cadeia de pattern evidence, registry, miner, review/sandbox e superficie read-only; `MB-181` e o unico item tecnico `ready` e `MB-182` a `MB-189` permanecem `blocked` por dependencia/ordem;
- `SO-001`, `TA-004`, `TA-006` e verticais `deferred` continuam fora da fila sem mudanca explicita de fase;
- `protective intelligence foundation` continua `deferred` e a matriz da Onda 2 segue como insumo, nao como gatilho automatico para abrir nova vertical.
