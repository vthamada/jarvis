# Modelo local via Core e ciclo de vida ASR

## Escopo da continuidade de 18/10

Tres pacotes paralelos, com arquivos disjuntos e um unico executor de testes:
supervisao ASR Windows, decoder HTTP chunked e composicao CLI do modelo local.
Os testes usaram servidores scripted, sem inferencia de pesos reais,
download de modelos, microfone, conta/OAuth, upload de voz, commit ou push.
Ollama foi instalado posteriormente por pedido explicito; ver registro abaixo.
MB236 e a configuracao privada de voz nao mudam. A Web nao ganhou seletor de LLM.

## Voz: confirmar o worker antes do cleanup

A ponte Web habilita `confirm_worker_exit=True` no Windows. Antes de importar
SDKs, o worker ASR publica um rendezvous privado ligado a run/nonce; o supervisor
so confirma ACK apos validar e reter o handle do processo real (PID, PPID,
imagem e creationtime), incluindo a topologia launcher de venv -> Python base.
Nao ha varredura de processos, kill por nome, permissao nova ou sleep de cleanup.
Selecionado executavel e home de pyvenv.cfg recusam UNC/device/relativos antes
de lstat/stat; o arquivo de configuracao local nao autoriza acesso a rede.

Cancelamento/prazo so libera a captura depois de o kernel confirmar a saida do
worker proprio. Falha de terminate nao prova saida: somente um novo wait no mesmo
handle atestado pode confirma-la. Se continuar vivo ou o wait falhar, a fronteira
permanece incerta. O worker sem ACK nao pode importar o SDK.

`WorkerExitUnconfirmed` tem mensagem fixa `local_asr_worker_exit_unconfirmed` e
`artifacts_retained=True`. Nesse caso a ponte preserva captura/runtime privados,
nao tenta rmtree e propaga falha para a quarentena de voz ja existente. A conversa
textual segue disponivel; reinicio explicito da instancia e necessario para
novo uso de voz. Retencao nao significa apagamento seguro nem coleta automatica.

Em sucesso ou erro com saida confirmada, o wrapper remove apenas seu diretorio
privado, verificando identidade e ausencia de redirecionamento antes da remocao.
Mudanca da fronteira/erro de cleanup tambem recusa a publicacao do rascunho com
mensagem fixa e quarentena; nao expor paths ao browser. Se rmtree falhar depois
de apagar parte dos arquivos, a retencao pode ser parcial: nao prometer todos
preservados nem todos apagados. No caso de worker incerto nao se inicia cleanup.
A verificacao nao e uma
sandbox de SO contra um invasor local da mesma conta.

O opt-in do laboratorio continua defaultoff; Linux segue o caminho anterior.
`quality`/beam5 permanece padrao. O resultado segue rascunho revisavel, sem
autossubmit, identidade de falante, Core ou alteracao da voz original. TTS ainda
nao usa este novo handshake; nao extrapolar esta prova para seu ciclo de vida.

## HTTP: chunked completo, nao streaming

O transporte local aceita JSON com Content-Length ou um unico
`Transfer-Encoding: chunked` em HTTP/1.1. Recusa CL+TE, codings combinados,
duplicatas, extensoes/trailers, framing incompleto, overflow e bytes extras.
Limites: 4096 chunks, linha de tamanho de ate 8 digitos hex, overhead wire de
ate 64KiB alem do teto decoded ja configurado; limites de cabecalho/corpo e
deadline total continuam independentes. Framing fragmentado nao reinicia prazo.

Mesmo depois de `0\r\n\r\n`, exige fechamento do peer dentro do prazo: nenhuma
prosa parcial ou SSE e publicada. `Connection: close`, endereco HTTP numerico
loopback, rota exata `/v1/chat/completions`, sem DNS/proxy/auth/redirect/retry.
Isso remove uma incompatibilidade de framing; nao prova compatibilidade de
todos os modelos, parametros ou versoes Ollama/LM Studio/llama.cpp.

## CLI local explicita

Documento stdin UTF-8/EOF:

```json
{"schema_version":"jarvis-local-model-tool-loop-v1","query":"Compare documentation and observability pilot reports."}
```

Exemplo de formato, nao executar com placeholders:

Executar a partir da raiz deste checkout, como as CLIs existentes; o catalogo
curado nativo e relativo ao diretorio de trabalho. O runtime canonico padrao
permanece em `.jarvis_runtime/console`, nao no servidor de modelo.

```powershell
.venv/Scripts/python.exe -m apps.jarvis_console.local_model_tool_loop_cli --authorized --confirm-input --confirm-reports --acknowledge-upstream-egress --session-id local-reports --model SELECTED_MODEL --endpoint http://127.0.0.1:11434/v1/chat/completions --report "documentation=C:/PRIVATE/selected-report.txt" --include-content
```

O operador escolhe modelo/endpoint e ate tres arquivos absolutos. Nao se le um
arquivo de query implicitamente: fornecer o documento acima por stdin. Flags
nao autenticam operador. Consentimentos de query e relatorios sao separados;
o acknowledgement adicional reconhece que um servidor em loopback pode enviar
o texto a cloud. Loopback NAO comprova pesos locais ou privacidade do servidor.
Nao ha descoberta, inicializacao/download de modelos, credenciais SIWC ficticias,
chaves herdadas, fallback de provider ou permissao operacional nova.

CLI local e CLI SIWC compartilham somente o fluxo canonico: admissao Core ->
modelo -> proposta limitada de leitura -> governanca/recurso -> resultado ->
continuacao -> sintese final -> readback exato de memoria/evento. Selecao de
endpoint/schema/provider permanece na composicao host, nunca stdin/modelo.
SIWC mantem assinatura, validacao de conta e whitelist anteriores.

`status=recorded` significa persistencia conferida, nao tarefa util concluida.
`model_tool_loop_status=completed` valida protocolo/citacao, nao veracidade ou
qualidade do raciocinio. `evidence_mode=live` significa sockets reais: mesmo
um servidor scripted recebe essa classificacao. `real_model_verified` e
`local_weights_verified` sao sempre false nesta CLI. Saida padrao e metadata;
`--include-content` projeta a final canonica integral, sujeita a redacao.
Query/final continuam na memoria canonica, e `input_received` ja registra query;
telemetria nova do loop/sintese nao duplica query, relatorios, prosa ou paths.
Filtros de padroes conhecidos nao sao DLP universal.

## Verificacao desta rodada

Primeira coleta integrada parou por basenames duplicados unit/integration;
nenhum caso daquela coleta rodou. Integracao chunked foi renomeada para
`test_local_chat_chunked_flow.py`; a CLI tambem usa basename exclusivo.
Unidade inicial chunked:59 passaram; foi GREEN da implementacao, nao prova RED.
Primeira bateria voz/HTTP:270 passaram e1 falhou no Windows linger/venv ao
confirmar saida apos parar launcher. Havia uma janela exited -> terminate sem
reconsulta; tratamento conservador e tres casos deterministas foram adicionados.
A falha e consistente com essa janela, mas nao captura sua causa exata no SO.

Bateria fresca apos o tratamento da corrida:53 passed/7.51s, incluindo os
quatro casos Windows base/venv e retencao/cleanup do wrapper. Antes da revisao
lexical adicional; nao somar como testes exclusivos. A rodada de CLI/regressao
seguinte terminou11 failed/711 passed/2 skipped/468.38s. Diagnostico isolado
confirmou AttributeError: o wrapper consultava `evidence_mode` publico que o
provider nao expoe. Corrigido somente no wrapper: binding default usa a constante
host ja passada ao constructor; factory injetada continua obrigada a declarar
`injected_transport`, nunca `live`.

O oracle de prosa do teste novo tambem precisava ler o literal JSON do anexo,
pois underscores/dois-pontos sao escapados pela sintese soberana. Agora exige
analise/citacao/resource decodificados exatos, alem de final==StoredTurn. Nao ha
normalizacao nova no runtime. Um subprocess DEFER excedeu o watchdog de teste
30s; startup/SQLite sao separados do budget de inferencia. Watchdog de processo
do teste passou a120s, sem mudar os30s default ou0.3s do caso de prazo do modelo.
O Windows reportou~838MiB livres durante a rodada; isso nao atribui causalidade
a um processo especifico nem autoriza encerrar programas alheios.

Nova rodada fresca interrompida por `-x`:87 passed/1 failed/58.90s; unidades
default BLOCK/DEFER passaram, mas subprocess ainda recusava. Trace isolado
confirmou FileNotFoundError do corpus curado relativo ao cwd temporario do
teste, antes do HTTP (zero requests). A fixture deve selecionar corpus/registry
publicos por caminhos absolutos, mantendo cwd e SQLite isolados; nao se remove
KnowledgeService, governanca ou readback para passar o teste.

Validacao fresca integrada:475 passed/142.46s/zero falhas ou skips. Inclui CLI
local+SIWC legado, lifecycle/Windows real/captura, perfil/decoding/transcricao
legados e chunked/HTTP/Core. Quick gate e git diff --check passaram. Snapshot de
138 arquivos de codigo/testes/configuracao congelado antes do gate standard;
resultado standard ainda pendente. Testes Windows
usam stdlib/handles reais, Python base/venv e lock em captura sintetica, sem ML.
Testes HTTP/CLI usam sockets/Core/SQLite/restart reais e respostas scripted,
nao prova de modelo local instalado ou de conversa fluida. Nao homologam Linux.

Primeiro standard desta continuidade parou em Ruff antes do pytest: uma linha
de101 caracteres no novo codigo embedded da fixture excedia o limite100.
Correcao somente de quebra de linha, sem alterar contrato ou oracle. Manifesto
de fontes foi recapturado para o standard seguinte, preservando log anterior.
Esse standard passou verificacoes estaticas e foi interrompido intencionalmente
em~25% do pytest para priorizar a instalacao pedida pelo operador, com RAM baixa.
Processos conhecidos do gate/pytest foram confirmados encerrados; log retido.
Nao ha veredito completo nem aprovacao standard desta continuidade.

### Verificacao anterior a publicacao solicitada

Em18/10 o operador autorizou commit/push e merge das implementacoes pendentes.
Inventario167 arquivos,138 de codigo/testes/config; base250b128 e branch
codex/publish-harness-voice-local-2026-10-18. Nenhum arquivo ignorado forcado,
audio/modelo/perfil privado publicado ou chamada de modelo/OAuth realizada.
Busca de padroes comuns de segredos e marcadores de conflito sem ocorrencias;
isso nao constitui garantia universal de DLP. Diffcheck aprovado.

Primeiro standard desta publicacao observou F na posicao430, interrompido
antes do traceback/JUnit final. A coleta oficial11404 localizou
`test_real_crash_after_core_commit_reconciles_receipt_without_another_core_call[True]`.
As duas variantes passaram isoladas:2 passed/30.81s. Bateria Web isolada:
65 passed/29.29s, incluindo o runner Node. Esses resultados nao substituem
o standard completo nem provam a causa da falha inicial.

Novo standard com identificacao por teste e fail-fast passou encoding/docs/Ruff
e ambas as variantes de crash no fluxo integrado. A sessao do executor
desapareceu em~5%, sem veredito; consulta posterior confirmou ausencia dos
processos gate/pytest. Sem nova tentativa local cega, modificacao de runtime,
timeout relaxado ou teste omitido para contornar a falha. Validacao Windows
completa continua parcial; CI Linux do PR e a execucao duravel do mesmo gate
standard exigida antes do merge. Esta secao registra o estado pre-publicacao;
os checks do PR sao a fonte do resultado remoto posterior.

## Proximo aceite e rollback

O operador informou inicialmente nao ter servidor local. Recomendacao inicial
(inferencia operacional, nao benchmark): Ollama nativo Windows, que documenta
suporte NVIDIA sem exigir Docker. Nao selecionou pesos. A autorizacao posterior
para instalar o runtime foi executada conforme registro abaixo.
[Windows oficial](https://docs.ollama.com/windows).

Proposta futura: bind127.0.0.1, `OLLAMA_NO_CLOUD=1`, um modelo e uma requisicao
por vez. Sao controles documentados do servidor; desativar cloud exige reinicio
e conferencia do log, nao bloqueia todo egress de downloads/updates. Escolha de
modelo/licenca/quantizacao/contexto continua separada da instalacao do runtime.
[Configuracao oficial](https://docs.ollama.com/faq).

Instalacao explicita concluida: Ollama0.40.5 via winget/scope user/source winget,
pacote
Ollama.Ollama e installer GitHub oficial; SHA256 conferido pelo winget:
ea0b50685d382bc0af164abdbf9b41bd89abb98de14fc51e4890a7176757a519.
Binario em C:\Users\vtham\AppData\Local\Programs\Ollama\ollama.exe.
Antes: nenhuma instalacao encontrada,23,2GiB livres; GPU consultada RTX3050
Laptop4096MiB/driver572.70, sem mudar driver. Duas configuracoes de usuario
antes ausentes foram persistidas: OLLAMA_HOST=127.0.0.1:11434 e OLLAMA_NO_CLOUD=1.
App/servidor iniciados pelo instalador. Listener conferido somente127.0.0.1;
CLI e GET/api/version confirmaram0.40.5; GET/api/tags e GET/api/ps confirmaram
zero modelos instalados e zero carregados. Cloud disabled true observado no
log de startup, sem expor log completo. GETs sem proxy/redirect e com prazo;
nenhuma inferencia, login, renovacao de conta ou download de pesos.
Isso prepara o host, nao conecta automaticamente JARVIS/Web ou prova geracao.
PATH do usuario conferido; terminais abertos antes da instalacao podem precisar
ser reabertos. Restavam20,0GiB no disco depois. Os138 hashes de codigo/testes/
configuracao permaneceram identicos ao manifesto final, sem arquivos removidos;
standard segue interrompido/pendente, nao aprovado por esse hash.
Quick gate e diffcheck pos-registro passaram; nao substituem standard.

Outra consulta de recurso durante o gate encontrou~388MiB de RAM livre em
~16GiB totais. Processo pytest continuava presente com atividade de CPU/IO
acumulada. Isso nao identifica um programa culpado nem mede latencia do modelo;
nao encerrar programas alheios ou iniciar ML em paralelo para compensar.

Antes de nova campanha ASR, obter gate e prova do encerramento acima. Depois,
comparar latencia real com mesmo audio/configuracao, uma condicao por vez.
Residencia de modelos, ASR mais rapido, TTS de baixa latencia, endpointing,
resposta oral apropriada pelo Core e prova fisica do microfone continuam
pendentes. Nenhuma melhoria perceptiva da voz foi avaliada nesta rodada.

Rollback: omitir voz na composicao Web e usar texto; nao usar a nova CLI local.
Nao desativar o guard Web para contornar falha de encerramento. Laboratorio
legado permanece opt-in separado. Nao ha migracao nem reescrita de memoria.
