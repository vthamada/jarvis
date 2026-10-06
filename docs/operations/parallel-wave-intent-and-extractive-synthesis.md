# Rodada 2026-10-04 - intent readonly e sintese extrativa

Operador pediu prosseguir. Tres workers desenvolveram Executive/negacao,
testes adversariais + Core e auditoria de inferencia. Coordenador integrou
port opcional em Synthesis e ponto comum native/LangGraph. Nenhuma dependencia,
shared contract novo, transporte HTTP, conta, base humana ou efeito em arquivo
humano. Sem commit/push; MB218 in_progress/MB219 blocked e Linux deferred.

## O que mudou

Executive usa familias de palavras normalizadas, em vez de substrings arbitrarias.
`runtime`, `planetarium` e `dropbox` nao acionam run/plan/drop. Draft textual nao
e operacao; planning explicitamente readonly nao solicita despacho. Negacao e
local e restritiva: positivo posterior, dupla/indireta negacao, quote/code/source,
controles e oversized pedem esclarecimento. Marcadores highrisk sao preservados
mesmo negados/citados ou alem da janela de routing. Nao e entendimento semantico
geral nem autorizacao. Detalhes: `docs/security/intent-readonly-boundary.md`.

SynthesisEngine aceita composicao opt-in `inference_port` + `inference_model`;
por padrao permanece desligado. Provider id/evidence mode esperados sao vinculados
explicitamente pela composicao (default fixture); apenas fixture/injected_transport
sao aceitos neste slice. Uma declaracao `live` nao e prova e e recusada. O port
recebe somente entrada corrente, referencia SHA-256 e instrucao de selecao de
trechos. Nao consulta memoria paralela, corpus do avaliador ou ferramentas.

O envelope permitido contem somente `citations`, com `source_ref/start/end/quote`.
Synthesis verifica schema, chaves duplicadas, identidade, fonte, offsets inteiros,
quote exata, sobreposicao e budgets. Nao aceita texto livre, efeito/grant ou
outros campos. Model request binding e limites sao snapshots locais; mutacao do
request nao amplia permissao. Erros, outputs late/invalidos e cancellation da
API local descartam candidato inteiro, sem ecoar exception/output livre.

Elegibilidade exige Governance exatamente allow, analise, native output/workflow
coerentes, sem operacao/adapter/clarificacao/confirmacao humana pendente e objetivo
nao contido. `allow_with_conditions` nao vira allow. Sintese nativa permanece
intacta; trechos verificados sao acrescentados como entrada nao confiavel, com
Markdown/HTML/URL/ANSI/bidi escapados. Fidelidade a entrada NAO comprova verdade.
Um falso claim na fonte permanece citado, nunca recibo/evento de execucao.

Native e nos opcionais usam `_compose_response` comum e response_synthesized
inclui apenas status/code/evidence-mode/count deste caminho. Observabilidade
existente da entrada permanece inalterada; este slice nao promete redacao global
de todos os eventos preexistentes. Memoria grava o final exato de Synthesis.

## Exemplo de composicao confiavel

```python
from synthesis_engine.engine import SynthesisEngine

# Port explicito com dados publicos/fixture; nao habilitado por input.metadata.
core.synthesis_engine = SynthesisEngine(
    inference_port=fixture_port,
    inference_model="fixture-model",
    inference_provider_id="fixture",
    inference_evidence_mode="fixture",
)
```

Nenhum comando/UI habilita isso automaticamente. Nao enviar dados a transporte
externo sem autorizacao e fronteiras de produto proprias. Limites: entrada atual
ate16k caracteres (tambem budget do InferenceMessage), candidato8k,1-4 quotes
nao sobrepostas de ate400 caracteres. Deadline2s revalida retorno, mas Python
sincrono arbitrario nao pode ser interrompido por esse consumer; cooperacao do
port/transporte e obrigatoria. A API de cancellation e local; nao afirmamos
cancelamento integrado a superficies do usuario.

## Evidencia desta rodada

259 testes focados passaram:100 Executive/adversarial/Core,27 Synthesis,
49 adversariais extrativos,8 fluxo extrativo,75 harness existente.
Fixtures Core usam SQLite TEMP e entrada sintetica. Caminho positivo declara
bounded_core_action explicitamente na fixture (nao eleva autonomia real do
operador); allow/sem operation e verificacao de final canonico foram comprovados.
Assist_only contido/defaultoff fazem zero chamadas. Os opcionais usam scheduler
fixture identificado: prova dos nos/composicao, nao LangGraph instalado/controlado.

Corpus/grader operator_tasks ficaram intactos. Antes:5 finais/121 eventos,
3 needs_decision (3 allow_with_conditions/2 defer entre os cinco turnos).
Depois:5 finais/136 eventos,3 needs_decision (1 allow_with_conditions/4 defer).
Digest do corpus preservado:
`c70a17581da807f404e92b518dd3393a8b618a5ee20d694f07ac394e5261ed46`.
Menos ambiguidade lexical nao implica mais autonomia ou tarefa util; agora a
capability/autonomy ladder continua contendo o fluxo por motivos proprios.
Nenhum ganho de produto, relato JSON/CSV ou continuidade util e promovido.
Gate standard agregado final Windows passou com codigo congelado apos review;
3344 testes coletados, nao3344 passes. Skips nao substituem provas controladas.
Documentacao de estado: HANDOFF.

## Proxima prioridade e rollback

Proximos slices devem entregar produtos estruturados com validacao independente
de fatos/calculos/citacoes/correcoes, sem oracle do grader nem resposta paralela.
Modelo/transport real, OAuth, recall semantico e interfaces live continuam abertos.
A avaliacao inicial esta em `inference-synthesis-integration-assessment.md`.

Rollback de inferencia: compor SynthesisEngine sem port, sem migration/dados a
desfazer. Guard lexical pode ser revertido por hunks revisados, preservando o
restante pendente e repetindo gate. Nao apagar memoria, enfraquecer Governance
ou desabilitar subject guard para recuperar compatibilidade aparente.
