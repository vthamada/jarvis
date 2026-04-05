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

---

## 5. Regras de manutencao da fila

- o proximo item puxado deve ser o primeiro `ready` de maior prioridade sem dependencia aberta;
- nenhum item novo entra em `ready` sem `criterio_de_aceite` e `gate_minimo`;
- quando um item for fechado, registrar em uma linha o impacto no baseline e sincronizar `HANDOFF.md`, snapshot e `CHANGELOG.md` se o estado real mudou;
- `HANDOFF.md` nao deve voltar a carregar a fila micro;
- este documento e a unica fila micro ativa do corte corrente.

Estado atual da fila:

- nao ha item `ready`, `in_progress` ou `blocked` neste momento;
- `MB-008` a `MB-012` foram concluidos e fecharam o lote atual;
- a fila volta a aguardar nova priorizacao macro ou novo lote micro soberano;
- o baseline atual ja trata sinais de release, memoria causal, recomposicao cognitiva e malha `mente -> dominio -> especialista` como parte da sua leitura formal de maturacao.
