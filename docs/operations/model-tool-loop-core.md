# Loop modelo/Core/ferramenta de relatorios locais

Atualizacao2026-10-18: historico canonico opt-in nas CLIs, mesmo sujeito/sessao,
sem anexos nao confiaveis. Prova gpt-6.1-sol apos refresh expirado da mesma conta
parou HTTP200/Content-Typeausente, sem tools/retry/modelo homologado ou Web.
Evidencias/gate: canonical-history-conversation-pilot-2026-10-18.md.

Data: 2026-10-16. Recorte opt-in nativo F01/F03; nao e fechamento macro,
homologacao de modelo real, executor geral ou retomada duravel de jobs.

## Entrega

O Core agora suporta a sequencia:

`modelo -> proposta -> governanca Core -> leitura -> observacao -> modelo -> sintese`

O modelo usa o port de inferencia existente. Pode solicitar `read_local_report`
e selecionar somente IDs de ate tres arquivos UTF-8 fornecidos pelo host.
As propostas sao JSON estrito no texto da resposta; este recorte nao adiciona
o protocolo nativo de function calling de um provider nem um registro geral.
Cada arquivo tem limite de 8192 bytes; no maximo tres chamadas de ferramenta e
quatro inferencias, dentro de um unico prazo de ate 120 segundos. Cada rodada
tem request ID ligado ao binding, passo e digest das observacoes atuais.

O default continua sem loop. A composicao nativa explicitamente seleciona
`ModelToolLoopConfig`; a Web/API, voz, MCP e caminho LangGraph nao sao ativados.
LangGraph com essa configuracao recusa antes do fluxo; nao finge paridade.
Nao ha nova dependencia central ou framework externo no papel de cerebro.

## Autoridade, dados e sintese

- So entra analysis naturalmente ALLOW/core_guidance_only, sem operacao,
  especialista, adapter, validacao/confirmacao pendente ou fonte revisada extra.
- BLOCK/DEFER nao chamam modelo, catalogo nem leitor. CLI default tambem nao
  abre o perfil de conta antes da primeira inferencia permitida pelo Core.
- O JSON do modelo tem schema fechado: tool_call com call_id/tool e somente
  arguments.resource_id; ou final com analysis/citations. Chaves duplicadas,
  campos de grants/actions, caminhos, ferramentas desconhecidas e refs inventadas
  sao recusados antes da leitura. Nao ha retry automatico.
- GovernanceService.assess_model_tool_call reavalia o pedido e produz check
  nativo model_tool_call/read_local_report para o recurso e fingerprint exatos.
  Condicoes nao viram ALLOW implicitamente. O Core revalida autorizacao e
  consume o fingerprint antes do adapter; trocas de contexto/plano/configuracao
  ou resultado de rodada anterior sao recusadas.
- O reader nao faz stat/open/read no construtor. O primeiro read autorizado
  fixa identidade/hash observados; isso nao e selecao previa de conteudo. Reads
  seguintes recusam drift. So arquivos regulares/single-link, sem symlink,
  reparse, FIFO/device ou caminhos livres; backend de handles POSIX/Windows
  existente e reutilizado sem chamar preflight/escrita. Arquivo mantem snapshot
  completo; ancestrais usam identidade/modo/atributos, nao timestamps de siblings.
- O provider recebe apenas query atual, IDs selecionados e observacoes aceitas.
  Nao recebe paths, historico, identidade humana, plano, grants ou credenciais.
  Os filtros sensiveis de padroes conhecidos recusam query, report e candidato;
  nao sao DLP universal nem prova de ausencia de PII/segredos em texto livre.
- O modelo precisa ter ao menos uma observacao e uma citacao literal dela.
  Citacao exata prova origem, nao verdade ou cumprimento integral da tarefa.
- A resposta nativa permanece soberana. A analise/citacoes entram como anexo
  JSON-literal escapado com o marcador GENERATIVE_ANALYSIS_MARKER existente,
  declaradas unverified, nunca fatos/grants/confirmacoes. Planejamento remove
  esse anexo do recall, preservando bytes do final na memoria canonica.
- Falha, cancelamento, prazo, proposta invalida ou drift descartam prosa e
  observacoes parciais do outcome e preservam o final nativo. Nao ha escrita de
  memoria pelo modelo ou uso de texto de ferramenta como permissao.

## Uso explicito

A CLI exige consentimento separado para query e relatorios inteiros. Os IDs
e caminhos vem do operador, nao do documento stdin ou do modelo.

```json
{"schema_version":"jarvis-model-tool-loop-v1","query":"Compare documentation and observability pilot reports."}
```

```powershell
python -m apps.jarvis_console.model_tool_loop_cli --authorized --confirm-input --confirm-reports --session-id reports-local --model SELECTED_MODEL --credential-dir ABSOLUTE_PRIVATE_DIRECTORY --profile-ref profile-EXACT_64_HEX --report documentation=ABSOLUTE_REPORT_PATH --report observability=OTHER_ABSOLUTE_REPORT_PATH --include-content
```

Fornecer o documento por stdin UTF-8/EOF e substituir todos placeholders. Nao
executamos esse exemplo com conta humana. A autorizacao antiga de uma unica
pergunta OAuth NAO cobre as ate quatro inferencias deste loop. Nova campanha
real exige consentimento especifico e resolver o bloqueio MB236; login/refresh,
busca de tokens, fallback de provider e relaxamento de Content-Type nao existem
nesta CLI. Um perfil escolhido e carregado apenas no primeiro infer permitido.
Em caminhos com espacos, colocar o argumento inteiro ID=caminho entre aspas.

Saida default contem somente metadados. `status=recorded` significa final e
evento sintetizado conferidos no armazenamento canonico, nao tarefa concluida.
`model_tool_loop_status=completed` significa protocolo/citacoes estruturalmente
aceitos. `--include-content` continua sujeito a redacao de padroes conhecidos.
Flags locais nao autenticam operador. O profile/reader temporario nao fica
ativado na instancia Core apos a chamada.

## Observabilidade e persistencia

Eventos novos model_tool_loop_* contem status/code/contagens/digests, nunca
query, corpo de relatorio, prosa do modelo ou paths. Os checks de ferramenta
possuem subject/action e IDs/fingerprint correlacionados. Hashes nao anonimizam.
response_synthesized acrescenta cinco campos model_tool_loop_* de resultado.
Finais e eventos existentes permanecem pela memoria/observabilidade canonicas.

Nao ha receipt duravel antes da leitura, scheduler, reconciliacao apos crash,
garantia exactly-once entre processos ou ferramenta com efeito de escrita.
O consume de fingerprint e local ao turno. Retomada duravel com efeito incerto
e a proxima prioridade, nao capacidade entregue por este slice.

Timeout e cancelamento sao cooperativos. Provider/callback/OS bloqueado nao e
preemptado; guards verificam antes/depois e descartam resultado tardio. O reader
tambem recebe deadline real; lock/read do SO nao se tornam watchdog de processo.
O carregamento lazy da conta desconta seu tempo do budget da rodada; se ele
consumir o prazo ou ocorrer cancelamento, nao inicia a inferencia seguinte.
A sintese revalida contexto, cancelamento e prazo original antes e depois de
renderizar o anexo. O evento model_tool_loop_finished descreve o protocolo;
somente response_synthesized informa o resultado efetivamente publicado.

## Validacao e limites da evidencia

Os testes novos usam Core, SQLite, arquivos e restart reais, com modelo
sintetico/port injetado. Cobrem duas leituras, continuacao/final, governanca por
call/recurso, BLOCK/DEFER, schema/bindings, replay de resultado antigo, limites,
cancelamento/drift, dados sensiveis/injecao, citacoes e projecao de Planning.
CLI tem consentimento, conta lazy, metadados, readback e restauracao de escopo.
Isso nao comprova raciocinio, qualidade ou utilidade de um modelo externo.

Uma recusa no primeiro lote mostrou a necessidade de nao tratar mtime de
ancestral como troca do arquivo. Repro deterministico com timestamp do pai
falhou na comparacao anterior; a correcao e a contraprova de inode diferente
passaram sem alterar o adapter global. A causa exata da recusa inicial nao foi
capturada. Newline de fixture Windows foi corrigido nos testes, mantendo CRLF
real do arquivo. Nao houve normalizacao de conteudo no reader.

O primeiro comando pytest sem basetemp explicito falhou em 47 setups na
criacao do temporario do sandbox. O lote de regressao no sandbox teve 8 falhas de
TLS antes de qualquer request ao servidor: probe loopback retornou 10013.
Os 10 casos TLS sinteticos executados no host permitido passaram. Nao houve
relaxamento de certificado, parser ou rede externa para resolver esses casos.

O primeiro gate foi interrompido deliberadamente durante pytest, sem veredito
final, para corrigir o budget lazy e a fronteira final de publicacao. Os seis
casos E2E de cancelamento/prazo/drift antes da sintese e durante renderizacao,
e os casos lazy com clock controlado, fazem parte da nova validacao abaixo.

Validacao integrada fresca dos cinco arquivos de teste: 287 passed, 3 skipped,
zero falhas em 126.76s. Os skips de filesystem/plataforma nao validam outro
ambiente. O caso lazy setup35s/budget30s falhou com o comportamento anterior
substituido somente em memoria (retornava completed); a implementacao corrigida
passou na bateria integrada. Nenhuma conta real foi carregada nessa prova.

O primeiro gate completo terminou exit 1: 13 failed, 9959 passed, 121 skipped
em 1650.84s. As 13 falhas eram AttributeError no novo campo opcional da sintese
em entradas legadas (nove casos adversariais e quatro de fonte revisada).
O acesso foi corrigido para getattr/default None, preservando o caminho legado
sem editar esses testes ou relaxar os controles. Regressao ampliada fresca:
428 passed, 3 skipped, zero falhas em 59.76s. O gate anterior continua registrado
como falha, nao foi promovido a aprovado. O XML foi gerado em nome incorreto no workspace
porque o parser da variavel PYTEST_ADDOPTS remove barras Windows sem quotes.
Os dois relatorios gerados foram movidos para a pasta de evidencia, sem perda;
o novo comando usa barras portaveis e a prova de gravacao foi conferida.

Gate standard reexecutado: exit 0, 9972 passed, 121 skipped, zero failed/errors
em 801.27s. XML confere 10093 casos; os 12 hashes de runtime/testes congelados
permanecem identicos. Entre os gates completos mudou somente o acesso opcional
na sintese; os dois arquivos de testes legados nao foram editados. Os skips
nao homologam outra plataforma, modelo ou conta. Nao houve commit/push/merge.

Evidencias locais desta rodada ficam em
`C:\Users\vtham\.codex\visualizations\2026\08\11\019ff2ec-5e21-75a2-a819-f8cf4aa2b4e0\model-tool-loop-gate-20261016`:
`frozen-inputs-final.json`, `standard-final.log` e `standard-final.xml`
(primeiro gate completo). A reexecucao usa sufixo `recheck` e preserva estes.
Resultado aprovado: `standard-recheck.log`, `standard-recheck.xml`,
`frozen-inputs-recheck.json` e `verified-inputs-recheck.json`.

```powershell
python -m pytest tests/unit/test_model_tool_loop.py tests/unit/test_local_report_reader.py tests/unit/test_model_tool_loop_policy.py tests/unit/test_model_tool_loop_cli.py tests/integration/test_model_tool_loop_core.py -q
python tools/engineering_gate.py --mode standard
```

## Rollback

Continuidade local18/10: a CLI SIWC mantem selecao/assinatura/whitelist e
compartilha apenas o fluxo canonico com uma composicao HTTP local independente.
Novo schema/consentimentos/acknowledgement de egress sao explicitos; veja
[CLI local e lifecycle ASR](local-model-cli-and-asr-lifecycle-2026-10-18.md).
`live` de HTTP significa socket, nao prova de modelo/pesos locais. Nao depende
de desbloquear MB236 nem amplia a autorizacao OAuth anterior.

Remover ModelToolLoopConfig da composicao (default None) desativa o loop.
Nao ha migracao nem memoria paralela. Finais historicas continuam preservadas;
o marcador ja usado pela projecao de Planning permanece compativel.
