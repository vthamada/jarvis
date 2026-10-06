# Final persistida integral -> lote TTS local

## Escopo MB225

MB225 done local; gate standard global Windows final passou. Estende MB224
sem mudar Core, memoria, governanca ou sintese. `--tts-batch` e opt-in adicional:
sem ele, o caminho single permanece limitado a600 codepoints, sem truncagem.
Nenhuma dependencia central nova; laboratorio continua complemento de saida.

## Uso e limites

Use o comando/configuracao/consentimento do
[runbook MB224](persistent-final-local-tts.md), acrescentando `--tts-batch`.
As flags `--authorized` e `--tts-authorized` continuam obrigatorias e distintas.
Nenhum modelo, arquivo humano ou dispositivo e selecionado automaticamente.
O console nao executa playback nem publica paths privados no servidor Web.

O plano contem substrings que recompõem exatamente a final canonica: ate6000
codepoints Unicode,16 partes nao vazias,600 codepoints por parte. Espacos,
acentos decompostos e CRLF sao preservados; controles/formatos perigosos sao
recusados, nao normalizados. Particao impossivel dentro dos limites e recusa,
nao resumo. Final textual permanece integral mesmo se a fala falhar.

Uma campanha usa um subprocesso e uma carga de modelo. Partes sao geradas
sequencialmente pelo SDK existente, com perfil/referencia preservados e seed
inicializada uma vez. Nao ha retry, troca de motor, nem nova chamada Core.
Nao se afirma cache unico de features da referencia: os SDKs recebem a
referencia nas chamadas existentes. Chatterbox conserva o fluxo de watermark
do SDK; nenhuma transformacao para remove-lo e introduzida.

Deadline unico inclui planejamento/preflight/geracao/montagem, ate1800s;
nao reinicia por parte. Callback fixture sincrono nao pode ser preemptado,
mas retorno tardio e recusado. Subprocesso real e supervisionado e encerrado
em timeout/cancelamento; falha de terminacao nao confirma sucesso. Limpeza e
persistencia/readback da auditoria final tambem precedem a checagem de prazo
antes de devolver sucesso. Expiracao durante auditoria registra recusa
corretiva; a candidata anterior nao autoriza playback/exposicao do artefato.

Cada parte precisa WAV PCM16 mono completo,8..96kHz e ate120s. Todas precisam
mesmo rate/formato. Agregado ate32MiB/600s: concatenacao exata dos frames PCM,
sem resampling, crossfade ou silencio acrescentado. Manifesto associa UUID,
motor, contagens e hashes ao plano; isso nao prova pronuncia de cada palavra.
Nenhuma parte isolada e declarada audio final.

## Publicacao, privacidade e rollback

Montagem valida fontes/identidade/conteudo e publica staging exclusivo;
parent revalida WAV/digest/prazo antes de publicar `sample.wav` por hardlink
sem overwrite. Filesystem sem hardlink falha fechado. Refusals tardias tentam
remover somente staging/final do inode proprio, nunca arquivo substituido por
terceiro; falha de cleanup pode deixar arquivo privado, nao confirma sucesso.
Partes/referencia/spool privados podem permanecer: nao ha promessa de limpeza
total, criptografia ou retencao segura. Use somente SDK/pesos confiaveis;
isolamento de ambiente/Python nao e sandbox de sistema operacional.

Metadata publica inclui `batch_mode`, `part_count`, `completed_parts`, status
e evidencia, sem texto/hash/path privado. `voice_quality_approved=false`.
Eventos locais existentes continuam sem conteudo; falha de auditoria impede
declarar sucesso. Codigo0 confirma turno textual, nao audio: consulte
`tts.status`/`tts.artifact_available`. Localizador temporario opt-in segue MB224.

Rollback: omitir `--tts-batch` ou todas as flags TTS. Nao ha migration ou
autoridade/API nova. MB226 acrescenta compatibilidade manual Web para agregado
ate600s/32MiB, sem autoimport; confira o
[runbook proprio](long-local-wav-web-playback.md). Nao reduzir audio original.

## Evidencia

Testes unitarios/adversariais e Core nativo com final1097 codepoints,
SQLite/restart/CLI reais e worker fixture verificam texto exato, frames em
ordem e falhas sem retry. Baterias de SDK usam stubs; supervisor usa subprocesso
simulado. Nenhum modelo/referencia humana/mic/login/store humano acionado.
Integridade estrutural nao aprova qualidade perceptiva, identidade vocal,
pronuncia integral pelo modelo nem continuidade prosodica entre partes.

Bateria consolidada732 passed/zero skips;13 testes de registry/assets e172
JS tambem passaram.39 E2E inclui expiracao durante persistencia/readback da
auditoria e falha da recusa corretiva, preservando um turno/final/texto.
Gate standard global Windows final passou; auditoria cruzada sem bloqueador.
Skips opcionais/plataforma da suite global nao sao campanha real de modelos.
