# Conversa com memoria canonica, ferramentas e prova real

## Resultado e fronteira

Continuidade autorizada F01/F02/F03, com F04/T02 em paralelo. O loop de relatorios
tem agora memoria opt-in nas duas CLIs existentes. Sem nova dependencia,
executor geral, permissao de acao ou modo Web. O Core continua admitindo,
governando, sintetizando e persistindo a final.

A prova com `gpt-6.1-sol` **nao homologou conversa util**. Operador autorizou a
mesma conta OAuth, ate seis chamadas sinteticas e renovacao somente se expirada.
Unico perfil encontrado estava expirado; uma renovacao concluiu com mesmo
vinculo, sem novo login/import de tokens. Preflight sem privilegio primeiro
recusou o lock do store; leitura autorizada com permissao adequada passou.

Uma tentativa de inferencia, zero concluidas, zero leituras de ferramenta e
nenhum segundo turno. Catalogo/selecao passaram; POST Responses recebeu
HTTP1.1/200, headers presentes e parser limpo, sem Content-Type/Content-Length,
TEchunked e encoding identity. Transporte recusou antes de aceitar corpo/SSE:
`response_media_type_missing`/`unsupported_response_encoding`; port retornou
`session_inference_failed`, loop `inference_failed`. Sem relaxar parser,
reenvio, fallback pago ou segunda renovacao. MB236 permanece blocked.
Tokens/custo nao informados; tentativa recusada nao significa zero custo.

Readback independente confirmou um turno/final canonica2635 caracteres,
ALLOW/25eventos, sem eventos de ferramenta autorizada/executada. SHA256 da final:
`8c0479b51b6abd48a82812b65696e768e902e831ca8e7b4ea79a48990d933f5c`.
SQLite/log/script retidos no diretorio de artefatos desta conversa, fora do
repositorio; memoria de producao nao usada. O script exige diretorio novo e
guarda compartilhada max_calls6, com parada na primeira falha. Nao repetir
automaticamente para consumir saldo. Primeira verificacao readonly usou nome
events.db incorreto; corrigido para observability.db sem mutar o runtime.

O fluxo oficial mantem Responses publico com OAuth, store=false/stream=true,
nao endpoints internos do ChatGPT. Verificado pela skill OpenAI Docs:
[Models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference).
Catalogo nao comprova inferencia funcional neste host.

## Historico opt-in

`ModelToolLoopConfig.include_canonical_history` e `--include-canonical-history`
em `model_tool_loop_cli` e `local_model_tool_loop_cli` ficam default off.
Opt-in autoriza egress adicional ao provider escolhido, nao autentica pessoa.
Documento de entrada segue apenas schema/query; nao pode habilitar memoria.

- Fonte: somente StoredTurn canonicos, nao context_summary/plan_summary/steps.
- Escopo: user_id igual canonical_user_ref; usuario/sessao exatos em cada linha.
- Limites: seis linhas examinadas, tres pares completos cronologicos,4000chars.
  Pares grandes/malformados excluidos inteiros, sem clipping ou consolidacao.
- Screening conhecido-sensivel da fonte inteira antes da projecao; nao e DLP
  universal/anonimato. Anexos de fonte revisada e analise de modelo ficam na
  final canonica, mas fora deste historico. Nao promete recordar literalmente
  respostas generativas anteriores.
- Historico e dados nao confiaveis, nao sistema/verdade/grant/observacao. Nova
  leitura de relatorio e citacao exata continuam obrigatorias.
- Binding/fingerprint inclui historico; fences de mutacao, config/repositorio,
  cancelamento e deadline cercam coleta/inferencia/publicacao. Coleta nao
  reinicia budget; loop recebe prazo restante.
- Evento model_tool_loop_history_selected tem somente contagens/authority none,
  sem texto, usuario, sessao, paths ou tokens no payload.

Memoria nativa permanece sem a flag. Continuidade demonstrada entre processos
CLI da mesma sessao local explicita nao e identidade Web duravel/multiusuario.
Acrescentar a flag ao comando de relatorios previamente selecionado/confirmado
mantendo session-id. Conta/modelo/paths e acknowledgement de possivel egress do
servidor local continuam escolhas do host, nunca do browser/modelo.

Proximo slice Web exige perfil/ticket/readback proprio de tool-loop; nao reusar
silenciosamente o modo generativo OAuth ou habilitar o modelo local no browser.

## Piloto local autorizado, apos o gate

Operador autorizou baixar `qwen3:4b-instruct` e ate seis chamadas locais com os
mesmos dois relatorios sinteticos, sem API paga ou mudar preferencia OAuth.
Ollama observado0.40.6, loopback127.0.0.1:11434, nenhum modelo antes do download.
Pull concluiu com verificacao de SHA e manifest;2497293803 bytes, digest exato:
`0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`.
Referencias primarias: [modelo](https://ollama.com/library/qwen3:4b-instruct),
[compatibilidade HTTP](https://docs.ollama.com/api/openai-compatibility).

Apos o standard aprovado, composicao real pelo helper compartilhado da CLI:
LocalChatHttpTransport/ChatCompletionsInferenceProvider, selecao fixa do host,
guarda global de seis chamadas e Core/Governance/reader/final/memoria existentes.
Nao usou o factory injetado de testes como evidencia live nem alterou o runtime.
Nao e prova da UI ou de uso literal da CLI publica neste piloto real.

Quatro chamadas ao modelo concluidas; observacoes enviadas cresceram0/1/2/3.
Tres leituras governadas reais, ordem documentacao/observabilidade/documentacao,
confirmada por hashes dos arquivos e eventos. Quarta proposta recusada com
`reused_call_id`, antes de executar outra leitura; nenhuma analise generativa
aceita. Proposta bruta nao retida: nao inferir o identificador ou recurso da
quarta proposta. Mesmo ID novo nao permitiria quarta ferramenta: limite tres.
Port/HTTP funcionaram; nao foi falha de autenticacao/transporte.

Script parou nessa recusa, sem retry, segundo turno ou uso das duas chamadas
restantes. Guarda de provider indica stopped=false porque nao houve erro no
provider; isso nao significa que o script prosseguiu. Contadores informados:
1188 input_tokens/130 output_tokens, custo nao informado. Nao e benchmark de
qualidade nem aceite de memoria real: todos os prompts eram do primeiro turno.

Readback SQLite independente:1turno/final nativa2635 chars,40eventos,4 model_requested,
finish step4/tool_calls3/observations3/refused/reused_call_id; final entregue
igual ao export e mesmo SHA da final nativa OAuth acima. Artefatos privados
conversation-local-model-pilot.log e conversation-local-real-20261018-01/core
retidos fora do repositorio. Processo concluiu exit0 por encerramento controlado,
nao por aceite funcional. Modelo observado com contexto4096 e offload parcial;
nao afirmar100%GPU. `ollama stop` confirmou zero modelos carregados; pesos
permanecem instalados. Nenhum outro servico/modelo foi encerrado.

Revisao independente nao encontrou defeito bloqueante comprovado neste diff.
Hipotese para proximo slice controlado: instrucoes atuais nao explicitam budget
restante/acoes seguintes permitidas/finalizacao obrigatoria ao esgotar leituras.
Nao atribuir causalidade sem experimento, trocar modelo ou aumentar limites para
esconder a falha. Manter Core/grants/fingerprints/citacoes/deadline e comparar
comportamento; novos consumos reais exigem escopo autorizado proprio.

## Avaliacao independente

Adapter de missoes separa brief literal de binding/fontes. Fontes integrais
entram na seam reviewed existente, bundle512/brief2048; sem truncamento ou
subconjunto. Nao resolve envelopebinding do grader nem briefs que por si exigem
clarificacao. Nenhuma missao promovida. Detalhes: mission-routing-reviewed-sources.md.

## Evidencia e gate

RED comprovado: config/flags inexistentes; fontes/binding contaminavam content.
Duas tentativas iniciais de teste tiveram setup/oraculo incorretos (query fora
do slice e literal escapado), corrigidos antes do RED do parametro ausente.
Coleta anterior colidiu basename unit/integration, renomeado. Primeiro lote
teve98passed/2erros setup por IDs Windows enormes; IDs curtos mantiveram tamanhos.

Bateria focada fresca128passed/zero falhas/skips em131,97s; warning de cache
inacessivel, desativado explicitamente depois. Cobre isolamento, sensivel,
limites, mutacao, cancel/deadline, SQLite/restart, CLI e review. Fixture contextual
distingue resposta com/sem historico, nao inteligencia real. Prova CLI/socket
em dois subprocessos passou. Regresso ampliado fresco389passed/127,60s/zero
skips; primeira rodada restrita teve381passed/8falhas HTTP sem requests.
Tres casos diagnosticos passaram com permissao de sockets, sem mudar codigo;
mesmo lote completo depois passou389. Limitacao de ambiente, nao corretivo de
runtime. Quick/diffcheck passaram. Standard global Windows exit0:11514 casos,
11390 passed/124 skipped/zero falhas/errors,2171,756s;14 hashes Python inalterados
durante o gate. XML conversation-standard-01.xml e log de mesmo prefixo retidos
nos artefatos desta conversa. Skips nao homologam outros ambientes; CI Linux
anterior ao diff nao substitui aceite Linux destas mudancas.

Sincronizacao documental posterior ao standard atualizou inventario/HANDOFF/
mapas sem alterar Python. Primeira verificacao do inventario recusou nove refs
na F01 (limite oito):2failed/86errors/6passed, fixture invalida compartilhada.
Substituida referencia de codigo por runbook consolidado, sem mudar validador,
testes ou estados de prontidao. Reexecucao fresca:94passed/51,12s. Comparacao
estruturada dos14 hashes Python com o freeze do standard confirmou igualdade.
Quick final (encoding, guardrails documentais e Ruff) e git diff --check
tambem passaram apos essa sincronizacao. Nenhum codigo foi alterado apos
o standard; a verificacao94 cobre o inventario documental atualizado.

Rollback: desligar flag/config. Sem migrar schemas/InputContract/stores/grants
ou apagar memoria humana. Sem commit/push ou promocao macro.
