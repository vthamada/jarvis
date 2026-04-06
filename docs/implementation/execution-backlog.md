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

---

## 5. Regras de manutencao da fila

- o proximo item puxado deve ser o primeiro `ready` de maior prioridade sem dependencia aberta;
- nenhum item novo entra em `ready` sem `criterio_de_aceite` e `gate_minimo`;
- quando um item for fechado, registrar em uma linha o impacto no baseline e sincronizar `HANDOFF.md`, snapshot e `CHANGELOG.md` se o estado real mudou;
- `HANDOFF.md` nao deve voltar a carregar a fila micro;
- este documento e a unica fila micro ativa do corte corrente.

Estado atual da fila:

- o lote `pre-v3 hardening` foi concluido;
- `MB-023` a `MB-026` foram executados sem reabrir a robustez ja fechada do `v2`;
- nao ha item `ready`, `in_progress` ou `blocked` na fila micro neste momento;
- o baseline atual continua sem pendencia tecnica material de robustez do `v2`, e o proximo passo agora depende de decisao sobre a fronteira arquitetural do `v3`.
