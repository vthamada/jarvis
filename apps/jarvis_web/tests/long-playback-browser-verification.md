# MB226 - ensaio WebAudio de WAV longo

2026-10-05, IAB real, tab propria/servidor loopback60665. Nenhuma troca do
servidor/aba humanos existentes. Fixture criada fora do repo/OneDrive, no
diretorio de entrega autorizado, a partir do assembler Python MB225: seis
partes mono8kHz/100s, tons baixos220..320Hz, agregado600s/9.600.044bytes.
Nao foi usada gravacao humana, SDK, microfone, conta ou Core live.

## Observado

- Picker real aceitou sample.wav e UI chegou ready; play nao automatico,
  input.value vazio. Esta importacao local nao envia arquivo ao servidor.
- Clique Play passou por starting e chegou speaking_local, level0.033.
  WebAudio/analyser reais, nao stubJS; silencio/interrupcao sao amplitude,
  nao avaliacao de articulacao, fidelidade vocal ou identidade.
- Interromper voltou ready/idle; segundo Play seguido de Stop enquanto
  notice ainda "Preparando reproducao local" voltou idle/0, sem fonte tardia.
- Nova reproducao chegou speaking_local/0.033. Captura salva em JPG fora
  do repo; Remover voltou empty/controles desabilitados.
- Viewport390x844: document.clientWidth=scrollWidth375, sem overflow.
  Override restaurado. Logs warn/error vazios ao final do smoke.

Captura da entrega: mb226-playback-20261005/playback-preview.jpg na raiz de
visualizacoes desta sessao. WAV e capturas sao sinteticos, nao audios do JARVIS.

## Limites

Nao se aguardou600s ate o fim; duracao/PCM/digest e fronteiras completas
validados pelo parser real Node e assembler real Python. Lifecycle/end/late
callbacks/erro de dispositivo/BFcache cobertos por doublesJS e AppFakeDOM.
Nao prova sincronismo linguistico, desempenho universal, codec externo,
qualidade TTS, browser remoto ou dispositivo mobile nativo. Nao atribuir o
tempo da automacao do picker ao tempo de processamento de audio.

344 JS e173 Python focados/zero skips passaram. Gate standard global Windows
final passou. Tentativas anteriores/MCP: runbook long-local-wav-web-playback.
