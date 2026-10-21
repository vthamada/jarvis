# Saida estruturada local e conversa com memoria

Data: 2026-10-20. Slice implementado, verificacao integrada em andamento;
qualidade de modelo real ainda nao homologada. Sem dependencia nova.

## Contrato

A CLI `apps.jarvis_console.local_model_tool_loop_cli` oferece
`--structured-tool-output`; a API `analyze_local_reports` e o provider
`ChatCompletionsInferenceProvider` oferecem `structured_tool_output=False`.
Somente bool literal do host; query, relatorio e resposta nao podem ativar ou
escolher schema. `True` com `port_factory` e recusado antes de construir o port.

O opt-in acrescenta somente `response_format` ao HTTP existente. O envelope e
fixo: `type=json_schema`, `name=jarvis_tool_loop_v1`, `strict=true` e schema
`type=object/anyOf` com alternativas completas selecionadas pela fase do Core:

- `tool_call`: call_id ASCII ate80, ferramenta fixa `read_local_report`,
  argumentos somente resource_id ASCII ate80;
- `final`: analise nao vazia ate4000 e1..3citacoes com call_id e quote ate512.

Cada objeto/argumento/citacao recusa propriedades extras. A raiz da uniao nao
tem additionalProperties=false isolado: isso proibiria todas as propriedades
no JSON Schema padrao. Valores E chaves sao tipos primitivos exatos. Factory
retorna copia nova por pedido, sem fonte/query/identidade de conta. Transporte
aceita somente esse formato opcional, nunca schema arbitrario ou native tools.
Tres variantes fechadas: somente tool_call antes da primeira observacao;
tool_call|final enquanto ainda ha leituras; somente final ao esgotar leituras.
A selecao le continuation.allowed_response_kinds e a recomendacao de progresso
do unico user message vinculado pelo host. Se kinds permite leitura/final E
suggested_next_action e a string exata read_unread_report, o opt-in solicita
somente leitura. Nos demais casos preserva kinds; nao amplia final-only nem
interpreta recomendacoes ausentes/malformadas, query ou fontes como comandos.
JSON limitado a30000chars, sem chaves duplicadas,
NaN/Infinity, overflow ou Unicode invalido. Contexto desconhecido falha antes de
HTTP, sem fallback para uniao. Query/relatorio nao escolhem a fase; JSON sozinho
nao autentica origem. Nome e variante completa fazem parte do fence.
Provider vincula bool/configuracao/payload profundamente antes e depois de I/O
e callbacks; mudar o formato revoga publicacao, sem retry ou texto parcial.

Default-off preserva payload de quatro campos e saida anterior. Somente on
acrescenta `structured_output_requested=true` e
`structured_output_schema=jarvis_tool_loop_v1` na saida CLI. Esses campos dizem
pedido do host, nao compliance do servidor, pesos locais, qualidade ou autoridade.

Nao muda `InferenceRequest`, parser do loop, governanca, memoria ou sintese.
Servidor pode ignorar o schema e gerar final prematura ou recurso nao selecionado: Core
continua exigir observacao nova, IDs frescos, escopo, citacao exata e aprovacao.
Nenhum JSONrepair, strip Markdown, warm-up, retry, native tools ou fallback.
Prazo total120s e limite3reads/4inferencias por turno permanecem intactos.
Esse opt-in prioriza leituras recomendadas para toda tarefa, nao so comparacoes:
selecionado nao significa obrigatorio e pode induzir trabalho adicional.
Ainda pode repetir recurso ou receber resposta que ignora o hint. Nao garante
cobertura de todas as fontes; nao introduz nova recusa de cobertura no Core.

## Fundamentacao externa e limites

O [Ollama documenta response_format](https://docs.ollama.com/capabilities/structured-outputs)
para a API compativel; cloud nao suporta esse recurso nessa documentacao.
No [pin52f16812](https://github.com/ollama/ollama/blob/52f168120e8cb38a367653353f84feedefede706/openai/openai.go),
o adapter repassa json_schema.schema ao formato nativo; strict nao e garantia
independente equivalente ao servico OpenAI.
O [llama.cpp f174553e](https://github.com/ggml-org/llama.cpp/blob/f174553e1621c6a22a64e7bfcbb58d3a5c49e6fb/common/json-schema.cpp)
traduz anyOf/oneOf para uniao antes de ler propriedades da raiz. Cada branch
deve conter seu contrato completo. Os kinds distintos tornam nossas branches
disjuntas; isso nao prova suporte generico a exclusividade oneOf.
Inspecao desses pins nao atesta a versao/build instalado nem a aderencia do Qwen.
A variante textual de invalid_model_message do piloto anterior nao foi retida;
este slice nao e apresentado como correcao causal dessa variante desconhecida.

## Evidencia e campanha

RED API/CLI antes de producao:7failed por kw/flag ausentes; um ensaio restrito
anterior teve6erros de setup no temporario, nao RED de produto. RED provider
interrompido em2failed por argumento ausente. Primeira verificacao integrada:
56passed/1failed; oraculo de memoria sobre-especificava type explicito junto de
enum unitario. Ajustado ao contrato enum-only ja acordado, sem relaxar parser.
Revisao independente encontrou chave str-subclass que comparava como strict mas
serializava outro texto;2REDs confirmaram. Guard de tamanho/chave str exata
corrigido. Isso e fence do seam Python confiavel, nao alegacao de exploit remoto.
Regressao integrada fresca:350 passed/84,14s, zero falhas/errors/skips; Ruff
global e diff check aprovados. XML structured-tool-regression-20261020-01.xml
nos artefatos privados. Sao testes offline/scripted, nao inferencias reais.

Prova E2E parametrizada off/on usa CLI/TCP/Core/SQLite/restart reais e servidor
scripted calculado somente pelo payload recebido. Duas interacoes, snapshots
identicos, fontes atualizadas e controle sem historia; verifica formato no fio
sem usar factory de producao como oraculo. Nao comprova inteligencia/qualidade.
Negativos HTTP mantem final prematura, kind invalido, ferramenta e recurso fora
do escopo recusados apos1pedido/zero reads, sem repair/retry e com final nativa.

Standard Windows da primeira versao, com uniao em todas as fases:11649 passed/
124 skipped, zero falhas/errors,11773 coletados/2158,217s de pytest. Encoding,
docs e Ruff aprovados;20 hashes Python e inventario ficaram identicos no gate.
XML/log structured-standard-20261020-01 nos artefatos privados. Esse standard
antecede a correcao por fase, nao e aceite global do codigo atual.

Piloto estruturado autorizado max9 executado uma vez:1tentativa/1resposta,
42858ms primeiro byte/EOF,414 input/102 output tokens. Core recusou
observation_required antes de ferramentas: final prematura, zero reads/analise
aceita. Final nativa2635chars conferida exatamente apos restart/export; raw do
modelo nao retido. Parou sem retry; segundo turno/controle nao executados.
As8chamadas nao usadas nao sao reutilizadas. Nao demonstra aderencia integral
ao schema nem compara causalmente latencia com outra campanha.

Falha motivou schema por fase, nao relaxamento do Core. RED E2E1failed e RED
unitario4failed reproduziram uniao ampla na fase inicial. Regressao fresca da
correcao:396 passed/58,93s, zero falhas/errors/skips; Ruff/diff aprovados. Inclui
90 testes unitarios do opt-in e E2E com tres reads e final-only no quarto pedido.
Standard integral dessa versao phase-bound aprovado:11695 passed/124 skipped,
zero falhas/errors,11819 coletados/1939,314s de pytest; encoding/docs/Ruff OK,
20 hashes Python e inventario identicos durante suite. XML/log
structured-phase-standard-20261020-01 nos artefatos privados. Docker daemon
indisponivel na checagem, sem reinicio/reset/build. Verificacao Windows foreground.

Piloto phase-bound:2tentativas/2respostas, primeiro byte18766/21953ms. Core
completed com1read documentation e final3370chars, readback/export exatos. A
analise inclui label, mas diz que precisa consultar observability e nao consulta.
Auditoria separada interrompeu por fresh_report_observation_mismatch; protocolo
aceito nao significa tarefa cumprida. Sem segunda interacao/controle/retry.
Novo ensaio explicito consultboth/once/3sentencas tambem parou no mesmo criterio:
2tentativas/2respostas,1read/final3208chars, primeiro byte5734/19703ms. Palavra
alterada, sessao/label/diretorio novos, sem correcao causal alegada. Cache/carga
nao controlados; esses tempos nao permitem comparacao causal de desempenho.

Essa evidencia motivou o estreitamento por recomendacao de leitura acima, sem
novas regras Core. RED2failed/14passed unit e1failed E2E antes do fix;16 testes
novos passaram depois. Inclui servidor que ignora hint e mantem completed
nativo apos1read: auditoria deve distinguir cobertura incompleta de protocolo.
Regressao integrada atual:376 passed/146,20s, zero falhas/errors/skips em oito
arquivos provider/transporte/CLI/memoria/negativos. Ruff/diff aprovados. XML
read-priority-regression-20261020-01 nos artefatos privados. Standard integral
atual aprovado:11712 passed/124 skipped, zero falhas/errors,11836 coletados/
2527,353s de pytest; encoding/docs/Ruff aprovados.20 hashes Python e inventario
identicos durante gate. XML/log read-priority-standard-20261020-01 preservados.

Operador ampliou autorizacao de chamadas Qwen locais sinteticas, sem teto
global. Cada novo ensaio teve teto voluntario10 para tres bracos (min3cada; uma
chamada extra compartilhada, max4por turno), preservando limite do guard, sem
warmup, repair, retry, OAuth/API paga ou uso de cotas anteriores. Parar na
primeira falha continua obrigatorio por ensaio; novos ensaios sao explicitos.
Diretorio/session/label novos; fontes sinteticas proprias, reader fresco por
braco, snapshot de dois bancos, contador global/reserva de tres chamadas por
braco. Default do novo runner e preflight inerte: executado,0calls e nenhum
diretorio de campanha criado. Runner por progresso executado depois do gate:
3tentativas/2respostas, duas fontes distintas observadas; primeiro byte98250ms
consumiu o prazo, terceira inferencia timed_out/timeout. Core failed/inference_failed;
final nativa2635chars exata no restart/export. Parou, sem segundo turno/controle.
O diagnostico nao separa carga/prefill/geracao: causa dos98s nao demonstrada.

Outro ensaio foi explicitamente anunciado com condicao inicial diferente:
GET/api/ps declarou modelo residente, size3534917467/size_vram2344636907 e
context4096. Sem inferencia de aquecimento; metadado nao atesta pesos nem causa
de latencia. Primeiro turno completou3calls,2reads/citacoes distintas e final
3719chars exata. Analise relaciona o gap de trace em ambas as fontes e identifica
o label como preferencia da query, nao fato das fontes. Primeiro byte6296/7390/
40046ms; nao e conversa fluida nem comparacao causal de performance.

Snapshots canonicos iguais de dois bancos gerados e fontes revisadas. Segundo
turno transportou1par de historico, releu ambas as fontes novas, mas a6a chamada
estourou o prazo restante92953ms. Provider timed_out/timeout; Core
failed/inference_failed, final3711chars exata apos restart/export. Nenhuma
analise de segundo turno aceita; controle nao executado. Runner parou na falha.

Total da rodada:14tentativas/12respostas completas em5ensaios (1+2+2+3+6).
Uma comparacao util de duas fontes fechada; memoria real ainda nao comprovada.
Todos os ensaios e saldos preservados, sem reuso, warmup artificial, repair,
retry automatico, OAuth/API paga ou aumento do prazo. Uso de historico no
payload nao equivale a resposta util com memoria. Proximos recortes: diagnostico
da latencia e saida concisa com orcamento explicito; nao atribuir timeout a
verbosidade, carga ou truncamento sem evidencia. Nenhuma nova inferencia em curso.
Memoria do segundo turno refere preferencia
na query anterior, nao memoria literal do anexo generativo excluido do historico.

## Rollback e estado

Sincronizacao documental final validada por quick (encoding/docs/Ruff) e256
testes frescos de inventario/contratos MCP/stdio/guardrails em52,72s, zero falhas.
XML structured-final-docs-20261020-01 preservado. Sem novos edits Python.

Omitir a flag/usar False restaura geracao anterior sem apagar stores. Sem
migracao, install/download, conta, commit ou push. MB236 e estados macro iguais.
Implementacao opt-in verificada pelo standard; aceite de conversa com memoria
real continua aberto. MB236/F01/F02 nao promovidos por esse ensaio.
