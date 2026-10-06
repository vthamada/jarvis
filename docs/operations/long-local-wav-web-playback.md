# WAV integral -> ensaio manual Web

## Escopo MB226

Implementacao concluida no recorte local; gate standard global Windows passou. Complementa
[MB225](full-final-local-tts-batch.md) no picker/player Web existente. Audio
selecionado manualmente nao comprova origem, autenticidade, final do Core ou
qualidade vocal. Conversa Web continua fixture; nao ha ponte HTTP ao Core.

## Uso

Inicie o servidor estatico allowlisted existente, em loopback:

```powershell
.venv/Scripts/python.exe -u -m apps.jarvis_web.serve --port 8765
```

Abra o endereco local, expanda **Esfera + audio local**, selecione o seu
`sample.wav` e clique **Reproduzir ensaio**. Selecionar nao toca audio nem
cria AudioContext. Somente arquivos locais escolhidos pelo operador chegam
ao browser, sem upload, microfone, URL, cookies ou armazenamento persistente.
Para localizar um resultado MB225, use seu localizador temporario opt-in;
o servidor nao publica arquivos de laboratorio e nao busca essa pasta.

WAV completo RIFF/PCM16, mono ou stereo,8..96kHz, ate32MiB e600s. Limites
independentes:600s em rate alto pode exceder32MiB e sera recusado. `fmt`
de16bytes antes de `data`, tamanhos/align/byte-rate coerentes, no maximo64
chunks; duplicatas, truncagem, sobras e formatos comprimidos recusados.
Tamanho real vem do DataView nativo, nao propriedade adulterada do buffer.
Metadata/textos de chunks desconhecidos nao aparecem na UI ou telemetria.

## Preparacao, interrupcao e privacidade

Conversao PCM->Float32 avanca em blocos de16384 frames, com macrotarefas
entre blocos e checks de generation/context/seleção antes de iniciar a fonte.
**Interromper** funciona durante preparacao e reproducao; preserva a selecao
para novo clique explicito. Reproducoes concorrentes/callbacks obsoletos nao
reiniciam som. **Remover**, reset e pagehide descartam referencias/fecham
contexto; BFcache requer nova selecao. Pagina oculta interrompe sem auto-resume.

Picker limpa seu valor antes de leitura, permitindo reselecionar o mesmo
File sem reter nome. Cancelar picker sem arquivo preserva selecao atual.
Erros de dispositivos/getters/callbacks sao codigos fixos sem texto/path;
observadores reentrantes nao criam novo play/select. Cleanup de nodos e
contexto e best-effort; nao se promete apagamento seguro de RAM.

Memoria limitada pelo arquivo: ate32MiB PCM +ate64MiB AudioBufferFloat32,
alem de copias/overhead internos do browser. Nao e streaming/download ou
promessa de baixa latencia para qualquer hardware. RMS mede amplitude real,
nao palavras ou consciencia; esfera respeita reduced-motion/pausa manual.

## Evidencia e rollback

344 testes JS/zero skips e173 Python focados/zero skips passaram. Python
assembler MB225 real -> parser Node real prova PCM/digest exatos em126s e600s;
SDK/TTS/Core nao sao simulados para afirmar fala real nessa prova: simplesmente
nao sao invocados. Tonal sintetico nao aprova qualidade/identidade de voz.

Browser IAB real selecionou fixture de seis partes100s (9.600.044bytes), sem
autoplay; reproducao exibiu speaking_local e RMS0.033. Cancelamento durante
preparacao voltou idle/0. Mobile390x844: clientWidth=scrollWidth375, sem
overflow horizontal; override restaurado. Logs sem warn/error no smoke.
Nao foi reproduzido WAV humano/modelo. Gate standard global Windows final passou.

Primeiro gate global terminou com uma falha no teste MCP
`test_missing_canonical_evidence_is_refused[events]` (nao no player). Alvo
isolado passou; ensaio independente com setup simulado3.1s reproduziu retorno
`report_entry_cancelled_or_expired` antes de Core/consulta de eventos. Latencia
e a hipotese suportada, nao houve instrumentacao do tempo da falha original.
Teste de evidencia agora usa budget10s (maximo ja permitido pelo produto),
com contador garantindo consulta ao alvo; testes de prazo permanecem separados
e runtime MCP intacto. Bateria MCP inteira56 passed, tambem apos collection
global5355 (56 selecionados/5299 deselected). Segunda execucao global acusou
outra F perto desse trecho e foi interrompida, nao usada como evidencia de
sucesso; seu traceback nao foi capturado. Terceira execucao standard completa,
com PYTEST_ADDOPTS='--maxfail=1 --tb=short', passou (exit0/all checks passed).
Essa opcao nao seleciona/exclui testes; somente para cedo se houver falha.
Nenhuma flexibilizacao de governanca/evidencia ou mudanca de runtime MCP.

Rollback: nao selecionar/reproduzir audio ou desativar controles locais;
Core, memoria e arquivo original permanecem intactos. Encerrar servidor com
Ctrl+C. Nenhuma conta/API/grant/dependencia nova ativada por este recorte.
