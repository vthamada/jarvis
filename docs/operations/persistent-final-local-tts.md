# Sintese persistida -> TTS local explicito

## Escopo MB224

MB225 acrescenta modo batch opt-in para finais longas, sem alterar o single
documentado aqui. Veja [lote integral e seus limites](full-final-local-tts-batch.md).

MB224 done no recorte local, gate standard global Windows passou. Este fluxo
estende `transcript-review` do
MB223: documento/transcricao revisados -> Core persistente -> final canonica ->
laboratorio local Chatterbox ou Qwen. O laboratorio e complemento de saida;
nao interpreta pedidos, nao substitui o Core nem adquire autoridade de ferramenta.

Nenhum modelo, referencia humana ou dispositivo de audio foi acionado pela
implementacao/testes. Evidencia sintetica e marcada `fixture`; nao prova qualidade
vocal, autenticidade do falante, inferencia real ou aceite perceptual.

## Uso explicito

O caminho sem flags TTS permanece textual. Para uma nova interacao, forneca por
stdin o envelope MB223 e autorize o turno e a fala separadamente. Exemplo
PowerShell 7, com caminhos **ilustrativos** (nao arquivos distribuidos):

```powershell
Get-Content -LiteralPath C:/JarvisPrivate/handoff.json -Raw -Encoding UTF8 |
  .venv/Scripts/python.exe -m apps.jarvis_console --format json transcript-review `
    --authorized --include-content --tts-authorized `
    --tts-engine qwen3_tts `
    --tts-reference C:/JarvisPrivate/reference.wav `
    --tts-model-dir C:/JarvisPrivate/qwen-model `
    --tts-python C:/JarvisPrivate/qwen-venv/Scripts/python.exe `
    --tts-show-output-path
```

O operador deve ter direito/consentimento para usar a referencia. Nada seleciona
automaticamente a gravacao humana, baixa pesos, autentica conta ou usa chaves.
Modelos/SDKs devem estar preparados localmente. Para Chatterbox use
`chatterbox_pt_br` e, quando exigido pelo SDK preparado,
`--tts-sdk-source-dir` com raiz local explicita. `--tts-device cpu` e padrao;
`cuda:0` exige selecao explicita. Nenhum playback automatico.

Use apenas executaveis, SDKs e pesos confiaveis. Ambiente de subprocesso
separado nao e sandbox de sistema operacional: este recorte nao prova que
codigo arbitrario de um SDK selecionado e incapaz de acessar o host ou a rede.
O adapter nao baixa dependencias nem garante essa seguranca por validar paths.

Opcoes de qualidade existentes: `--tts-voice-profile baseline`,
`chatterbox_conversational`, `qwen_icl` ou `qwen_icl_draft`,
`--tts-reference-start`, `--tts-reference-duration`, `--tts-seed`.
`qwen_icl` exige `--tts-reference-transcript` exata da janela e
`--tts-transcript-confirmed`. O perfil draft exige transcricao nao confirmada
e continua experimento, nao voz aprovada. Transcricao de referencia em argv
pode ser visivel no historico do shell e na lista de processos: nao passe
segredos e nao use esta opcao quando essa exposicao for inadequada.

Todas as opcoes TTS sao recusadas sem `--tts-authorized`; esta autorizacao nao
substitui `--authorized`. JSON importado nao pode selecionar arquivos/modelos.
Consulte tambem [o fluxo textual](reviewed-transcript-web-to-core.md).

## Fronteiras e falhas

- Configuracao/consentimento sao validados sem IO antes de ler stdin. Envelope
  valido precede preflight readonly dos paths, WAV, pesos e janela; nenhum
  bootstrap Core ocorre para configuracao/fonte invalida.
- Paths devem ser locais, absolutos, sem travessia, redirecionamento, dispositivo
  ou rede. Referencia e SDK/pesos nao sao abertos para escrita pelo adapter.
- Apenas a final exata vinculada ao request, resposta, memoria e eventos locais
  pode chegar ao laboratorio. O pedido revisado nao vira texto de TTS.
- Falha/timeout/cancelamento de TTS nao desfaz turno ja persistido, nao reenvia
  Core e nao tenta outro motor. A final textual permanece canonica.
- O modo single tem limite600 codepoints por final. Acima dele a fala e
  recusada, sem abreviacao/truncagem. O modo `--tts-batch` MB225 usa limites
  separados; nao confundir integridade estrutural com qualidade vocal aprovada.
- Audio declarado como sucesso deve existir, ser WAV mono valido e concordar
  com duracao/rate/digest e binding do resultado. Parcial nao e sucesso.

`--include-content` permite mostrar texto/final somente se o redator aceitar;
conteudo sensivel e omitido integralmente. Fallback disponivel significa que
o texto esta preservado, nao que sua exibicao privada foi autorizada.

Codigo de saida0 confirma o handoff textual concluido, nao a existencia de
audio: inspecione `tts.status` e `tts.artifact_available`. Falha vocal preserva
esse sucesso textual; erro previo ao Core continua recusado pelo console.

## Onde fica o audio

O laboratorio cria uma pasta propria no diretorio temporario do sistema.
Metadata normal nao mostra paths nem digests. `--tts-show-output-path` solicita
um **localizador relativo seguro**, nao suspende a redacao de paths privados.
Quando disponivel, `tts.output_location` contem `base=system_temporary_directory`
e `relative_path=jarvis-voice-lab-<run>-<suffix>/sample.wav`.

Para resolver o localizador no mesmo computador/processo de configuracao:

```powershell
# Use o relative_path retornado pela sua propria execucao, sem inventar run/suffix.
Join-Path ([System.IO.Path]::GetTempPath()) 'jarvis-voice-lab-<run>-<suffix>/sample.wav'
```

Diretorios temporarios podem ser removidos pelo sistema; este fluxo nao exporta
automaticamente para Downloads, nao publica arquivo no servidor Web e nao toca
clipboard. Artefatos de laboratorio podem conter audio, referencia preparada e
metadados/textos de trabalho: trate a pasta inteira como privada. Nao afirmar
retencao segura, limpeza automatica ou criptografia que o laboratorio nao oferece.

## Observabilidade, validacao e rollback

Os eventos `local_final_tts_requested` e `local_final_tts_finished` sao locais
e sem texto/path/hash; eventos existentes de
governanca, sintese e memoria continuam soberanos. Falha de auditoria impede
promover audio a sucesso. Os stores de Core humanos nao sao usados pelos testes.

542 testes focados passaram/zero skips: baterias unitarias adversariais,
parser/CLI, Core real com SQLite/restart e laboratorio injetado. Gate `standard`
global Windows passou.93 testes do adapter,154 de opcoes e57 E2E novos;
238 regressoes relacionadas completam a bateria focada. Nenhum skip nela;
o gate global tem skips opcionais/plataforma, nao e campanha real de modelos.
O caminho com final curta usa test double explicito de sintese, nao modelo real;
Core nativo sem esse double tambem precisa provar preservacao da final longa.

Rollback: nao fornecer flags TTS. O fluxo MB223, final e memoria persistente
continuam funcionando. Nao e necessaria migration, promocao de capability,
API mutante publica, alteracao de auth ou troca do cerebro do sistema.
