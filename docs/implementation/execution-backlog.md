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
- `HANDOFF.md` continua como retomada tatico-operacional;
- `docs/implementation/v2-adherence-snapshot.md` continua como leitura viva do baseline;
- este arquivo e apenas a fila micro ativa do corte corrente.

Regra central:

- este backlog nao substitui a direcao macro;
- ele organiza a execucao do proximo trabalho pequeno e fechavel;
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
- docs vivas entram na fila apenas quando refletem mudanca real de runtime, gate ou baseline;
- nenhuma tarefa vaga entra em `ready`.

### Definition of Ready

Um item so entra em `ready` quando:

- tem `micro_objetivo` fechado;
- aponta comportamento, contrato, gate ou artefato especifico;
- tem `criterio_de_aceite`;
- tem `gate_minimo`;
- nao depende de decisao macro ainda aberta.

### Definition of Done

Um item so entra em `done` quando:

- implementacao principal foi concluida;
- validacao minima definida no item passou;
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

---

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
- a fila micro volta a ficar sem item `ready` ate nova repriorizacao explicita do operador;
- a abertura ou repriorizacao do proximo lote continua sendo rodada `extra high`, sem reativar `protective intelligence` nem reabrir itens ja concluidos por inercia local.
