# Avaliacao da integracao de inferencia com sintese soberana

## Escopo da avaliacao

Esta nota registra a avaliacao local de 2026-10-04. Nao e prova de modelo
real, autorizacao para rede, autenticacao, promocao de capability ou fechamento
de MB218/MB219. A implementacao e seus resultados devem ser consultados no
handoff da rodada; esta nota distingue recomendacoes da capacidade comprovada.

O menor recorte recomendavel e inferencia opt-in para selecionar trechos
extrativos da entrada atual. O modelo produz dados candidatos; Synthesis
verifica cada trecho e compoe a resposta. Nao se aceita resposta livre do
modelo como substituta da sintese, de Governance ou da memoria canonica.

## Interfaces existentes e pontos de composicao

- `shared/model_inference.py`: `ModelInferencePort.infer(request,
  cancellation=None) -> InferenceResult`. Request/result sao limitados, mas
  uma implementacao arbitraria do port ainda precisa de validacao na fronteira.
- `services/inference-service/src/inference_service/providers.py`:
  `FakeInferenceProvider` e `ResponsesPlanInferenceProvider(transport, ...)`.
  O segundo exige transporte injetado; nao fornece HTTP ou credenciais. O
  timeout depende de cooperacao do transporte durante operacoes bloqueantes.
- `engines/synthesis-engine/src/synthesis_engine/engine.py`:
  `SynthesisEngine.compose_result(synthesis_input) -> SynthesisResult` e o
  ponto soberano para selecao, validacao e composicao do candidato.
- `services/orchestrator-service/src/orchestrator_service/service.py`:
  `_compose_response(...) -> SynthesisResult` e o ponto comum para entregar
  a entrada corrente a Synthesis, sem introduzir recuperacao paralela.
- `services/orchestrator-service/src/orchestrator_service/langgraph_flow.py`:
  `_synthesize_response(state)` chama o mesmo `_compose_response`. A entrada
  e a projecao segura da observabilidade precisam ser equivalentes nos dois
  modos; a persistencia continua a consumir a resposta soberana exata.

O novo contexto pode ser opcional e limitado, derivado pelo Orchestrator do
`InputContract.content`. A referencia deve identificar os bytes da fonte
atual; nao e identificacao de usuario, autenticacao ou autoridade. Nao deve
ser criada outra memoria, nem consultar historico/cross-session para este
slice. Campos de input nao podem habilitar o port ou conceder autorizacao.

## Por que o validador atual nao basta para prosa livre

`SynthesisEngine._validate_output` verifica a presenca das tres clausulas
minimas por substring. `_validate_workflow_output` compara clausulas esperadas
de workflow. Essas verificacoes nao demonstram verdade factual, atendimento
da tarefa, ausencia de alucinacao ou legitimidade de um efeito declarado.

Uma resposta maliciosa pode conter as clausulas corretas e afirmar uma compra
ou execucao inexistente. Portanto, reutilizar somente esses validadores para
aceitar texto livre nao preservaria a fronteira desejada.

Trechos extrativos permitem uma garantia menor e verificavel: a sequencia de
caracteres ocorreu na fonte indicada. Isso nao demonstra que a fonte seja
verdadeira, atual ou autorizativa. O renderer deve rotular explicitamente os
trechos como entrada nao confiavel, nao como fatos confirmados ou recibos.

## Recorte implementavel sem transporte externo

1. Port desabilitado por padrao e configurado apenas por composicao confiavel.
2. Elegibilidade antes da chamada: Governance exatamente `allow`, sintese e
   workflow nativos coerentes, sem operacao, adapter request, clarificacao,
   confirmacao pendente ou estado contido. Falha preserva o resultado nativo.
3. Request limitado contendo apenas a fonte corrente e instrucao para um
   envelope JSON de citacoes, sem ferramentas ou memoria paralela.
4. Envelope estrito: apenas `citations`, cada item contendo `source_ref`,
   `start`, `end`, `quote`. Sem campos adicionais, chaves duplicadas, floats,
   booleanos como offsets, NaN/Infinity, refs desconhecidas ou spans invalidos.
5. Para cada item, validar `source[start:end] == quote`, limites de quantidade,
   tamanho por trecho, tamanho total e ausencia de duplicatas. O modelo nao
   define goal, governance, plano, grants, efeitos ou sintese final.
6. Synthesis acrescenta somente trechos verificados com rotulo nativo e escape
   de markup, controles, ANSI, bidi e quebras. Uma citacao de um falso claim de
   execucao permanece dado citado; nao muda eventos operacionais ou autoridade.
7. Exceptions, timeout, cancelamento, output malformed ou identity mismatch
   deixam a sintese nativa intacta. Nao tentar reparar prosa livre nem publicar
   output parcial. Revalidar `InferenceResult` mesmo quando o port retorna uma
   instancia do tipo esperado.
8. Observabilidade com status/reason enums e contagens limitadas. Nao registrar
   prompt, texto do candidato, quote, tokens de consulta ou exception livre.
   `provider_id`/`evidence_mode` auto-declarados nao provam uma chamada real.

## Evidencia de elegibilidade no Core atual

Foi executado um diagnostico local com `_isolated_core`, stores temporarios,
observabilidade somente local e entrada publica sintetica. Nenhum modelo,
conta ou base humana foi acessado. A entrada usada foi:

> Analise os fatos: A revisao acontece na quinta-feira. O responsavel e Ana.

- Com `requested_autonomy_level=max_autonomy_level=assist_only`: intent
  `analysis`, Governance `defer_for_validation`, containment
  `defer_capability_above_autonomy_limit`, capability
  `core_with_specialist_handoff`, confirmacao `not_required`, sem operacao.
- Com ambos os niveis explicitamente `bounded_core_action` na fixture:
  intent `analysis`, Governance `allow`, capability
  `core_with_specialist_handoff`, request confirmation `bounded_autonomy`,
  sem operacao. Isso torna possivel testar o caminho positivo real sem mudar
  politica ou reinterpretar uma decisao condicional como permissao plena.
- Entradas `general_assistance` no segundo nivel resultaram em
  `allow_with_conditions`; nao devem passar pelo novo caminho estrito.

Esta fixture nao autoriza elevar a autonomia do usuario em runtime. E somente
composicao declarada de teste; nao e evidencia de uma resposta util gerada por
modelo nem de capacidade operacional externa.

## O harness continua sendo uma leitura honesta

`evals/operator_tasks/core_pilot.py` retorna `needs_decision` para qualquer
decisao diferente de `allow` e busca a resposta final exata na memoria canonica.
Isso deve continuar intacto; nao usar expected facts, oracle do grader ou
resposta paralela para melhorar a pontuacao.

Corrigir intent/negacao, por si so, nao garante permissao: a ladder pode manter
confirmacao explicita ou a capability pode exceder `assist_only`.
`shared/autonomy_ladder.py:evaluate_autonomy_action` retorna
`require_confirmation` para evidencia ausente quando o contrato exige
confirmacao. `GovernanceService.make_decision` preserva isso como
`allow_with_conditions`/`prepare_exact_action_confirmation`. Outra decisao
possivel e defer por capability acima do limite. Sao fronteiras distintas da
classificacao lexical inicial.

Mesmo com `allow`, a sintese nativa atual e framing de objetivo/julgamento/
recomendacao, nao o envelope JSON de relatorio, CSV revisavel ou retomada
corrigida exigido pelo corpus. A selecao de citacoes e um incremento de
evidencia, nao resolve calculo, produto estruturado, correcao ou recall por si.

## Bateria minima para implementacao

- Default off e inelegibilidade fazem zero chamadas ao port.
- Fixture valida passa por Synthesis e persiste exatamente sua resposta final
  no Core real; caminho native e opcional LangGraph tem a mesma fronteira.
- Governance condicional/bloqueada/defer, confirmacao, clarificacao e adapter
  impedem o port; nenhum grant, dispatch ou efeito novo e emitido.
- Port adversarial retorna request/model trocados, result de tipo errado,
  status inconsistente, texto grande, exception e output parcial: fallback
  nativo exato e telemetria redigida.
- JSON duplicado/extra, offsets bool/negativos/fora do limite, quote falsa,
  fonte desconhecida, excesso de trechos e caracteres de controle sao testados.
- Texto de entrada com falsa execucao e instrucao de bypass so pode aparecer
  como citacao explicitamente nao confiavel, nunca como efeito ou autorizacao.
- O corpus/grader continua imutavel e nao recebe novas respostas fabricadas.
- Gate adequado, handoff e documentacao operacional acompanham o estado real.

Promocao futura de respostas livres/estruturadas exigira validadores de produto
e evidencia proporcionais, transporte explicitamente autorizado e prova do
fluxo real. Este recorte nao deve ser vendido como conversa livre resolvida.
