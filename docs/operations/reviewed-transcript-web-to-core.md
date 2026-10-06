# MB223: transcricao revisada da Web UI ao Core local

Data: 2026-10-05. MB223 done no recorte local; gate standard global Windows
passou. Nao e conclusao do JARVIS, conversa Web live ou aceite de voz real.

Continuidade MB224: o mesmo comando admite TTS local da final persistida,
somente com consentimento vocal separado e configuracao local explicita.
Nada e sintetizado pelo browser. Guia/limites:
[Final persistida -> TTS](persistent-final-local-tts.md).

## O que muda no produto

Painel separado Transcricao de arquivo - revisao local: consentimento opt-in,
picker JSON, texto editavel, prazo local120s e exportacao unica por revisao.
Nenhum upload/mic/modelo/STT/TTS ou request ao Core pelo browser. Conversa e
ensaio de voz existentes continuam fixtures explicitamente marcadas.

Importacao strict UTF8 original (sem BOM), max32768bytes, JSON sem duplicatas,
exponentoverflow, controles invalidos ou extras. Documento tem review_required
true, language Portuguese, audio_duration_seconds >0 ate900 e segments1..1000,
cada um com start_seconds/end_seconds/timestamps_estimated/text; tempos ordenados
e dentro da duracao. Candidato e join exato por newline, max4000codepoints.
Hashes usam bytes UTF8 reais, nao JSON reserializado. Textarea normaliza CR/CRLF
para exibicao, mas sem input editado o pacote preserva as quebras originais.
Edicao muda revisao; rascunho invalido fica visivel e bloqueia exportacao.

Export gera JSON somente leitura selecionavel para copiar manualmente. Sem
clipboard-write, download automatico, URL, file.name em eventos ou persistencia.
Revogacao/reset/cancel/pagehide descartam referencias e DOM; BFcache exige novo
consentimento. Leituras/crypto atrasados, revisoes obsoletas e submit repetido
nao restauram pacote. Timer1s atualiza expiracao visivel; operacoes tambem
checadas antes/depois de awaits. Nao e garantia de prazo entre hosts/suspensao.

## Fronteira: dado, nao autorizacao

Envelope jarvis-transcript-handoff-v1, oito campos exatos:
schema_version, authority=none, source_origin=unverified, document_utf8_b64
(base64 standard canonical do arquivo original), source_sha256, reviewed_text,
reviewed_sha256, review_revision int1..2147483647. Envelope max131072bytes.
Origem, speaker, modelo ASR e autenticidade WAV NAO comprovados. Hash e apenas
consistencia dos dados recebidos; revisao exportada e declaracao, nao ticket.

CLI standalone transcript-review valida opt-in/args antes de ler stdin,
bytes/schema/hashes antes de bootstrap e cria uma revisao Python NOVA. O
LocalTranscriptReview/ReviewedVoiceCorePort existente confirma hash/revisao/
deadline exatos e consome uma vez antes do handoff real ao Core. Sem retry,
downgrade ou receipt operacional. Reutilizar arquivo em OUTRA invocacao humana
explicitamente autorizada e novo turno, nao replay de autorizacao persistida.
Nao ha deduplicacao cross-process ou autenticacao do gesto humano pelo JSON.

Core persistente do console em .jarvis_runtime/console: memoria canonica,
governanca, final/eventos normais. Binding local fixo surface://local-transcript-review,
operator://local_console/user://local_operator; --session-id local ASCII ate80,
default transcript-review. Nao autentica operador. assist_only/scope vazio,
sem adapterrequest/actionreceipt/modelo/dispatch; nenhuma capability promovida.
Composicao local_observability_only nao instancia mirror/tracing externo,
mesmo com ambiente configurado. Default dos outros comandos permanece igual.

## Uso explicito

Servidor Web opt-in existente: `python -m apps.jarvis_web.serve --port 8765`.
Reiniciar instancias antigas para novo asset
allowlisted; servidor permanece GET/HEAD, CSP connect-src/form-action none.

Selecione JSON gerado pelo ASR local ou arquivo explicitamente fornecido;
revise, prepare pacote, selecione/copie manualmente e salve UTF8 se necessario.
Exemplo PowerShell7 para um arquivo deliberadamente selecionado (nao executado
sobre dados humanos nesta rodada):

```powershell
Get-Content -LiteralPath C:/JarvisPrivate/handoff.json -Raw -Encoding UTF8 | .venv/Scripts/python.exe -m apps.jarvis_console --format json transcript-review --authorized --include-content
```

Sem --authorized: zero leitura/IO/bootstrap. Stdin UTF8 ate EOF e obrigatorio;
limite de bytes nao e timeout de um produtor arbitrario que nunca encerra pipe.
Default imprime apenas metadata. --include-content mostra texto/final exatos
somente se redacao nao detectar segredo/path; caso sensivel omite conteudo
inteiro, nao altera texto/hash. Texto enviado permanece exato na memoria privada
local por consentimento. Erros fixos, sem conteudo/parserdiagnostico privado.
Erro apos Core/commit/display nao implica rollback nem autoriza retry automatico.

## Provas e limites

273 testes Python focados passaram/zero skips, incluindo CLI/DOM/Core/restart
e regressao MB221.172 testes JS passaram/zero skips, dos quais106controller
e14 handlers reais do app em DOM simulado. Node export real -> stdin Python ->
Core/SQLite persistidos/reload/final/governanca; arquivo original Unicode/CRLF/
espacos intactos. Nenhum DB humano ou modelo/rede externa usado.

IAB local real na previa temporaria65191: picker da fixture sintetica
apps/jarvis_web/tests/transcript-fixture.json, revisao1 -> export, package JSON
readonly com texto CRLF exato, descarte apagou output. Viewport390x844 (largura
util375 pelo scrollbar) sem overflow, override restaurado. Pagina final recarregada
com opt-in fechado. Screenshots inspecionadas durante teste, sem alegar teste
de ASR/microfone/voz real ou aceite de design humano. Picker teve observacao
demorada, mas handle/tab permaneceram vivos; sem restart de servidor humano.

Pendente: conversa live Web/Core com fronteira autentica, ASR/mic integrados,
fala natural aprovada, streaming e API mutante publica. No-go API intacto.
Rollback: remover painel/controller/asset/comando, nao chamar opt-in; memorias
ja registradas sao preservadas. Encerrar servidor nao apaga turnos canonicos.

Proximo MB224: fala local opt-in da final persistida, reaproveitando laboratorio
Chatterbox/Qwen sem cortar/substituir sintese final e com fallback textual claro.
