# Smoke de browser: esfera de particulas

Data2026-10-04, IAB real, servidor loopback proprio com porta efemera; nenhuma
reinicializacao do servidor humano8765. Imagem do operador usada como referencia
visual, nao como dependência. Sem browser engine remoto, upload ou microfone.

## Fluxos observados

- Canvas desenhado com particulas ciano, silhueta ondulada e nucleo; screenshot
  de entrega exportado fora do repo/OneDrive. Console sem warnings/errors finais.
- Picker selecionou fixture WAV PCM16 mono16kHz/12s gerada localmente, sem nome/
  conteudo no metadata do app. Nenhuma reproducao automatica apos selecao.
- Clique Reproduzir abriu AudioContext real; DOM mostrou speaking_local e nivel
  visual0.011 num frame amostrado, nao zero. Isso confirma caminho RMS real,
  nao e avaliacao de TTS, voz do dublador ou fala do Core.
- Interromper voltou idle/0 e habilitou reproducao novamente. Remover descartou
  selecao/retornou empty, controle play desabilitado.
- Pausar/Retomar alternou aria-pressed e texto do botao. Preferencia reduced-
  motion e lifecycle/late callbacks cobertos por doubles JS, nao alterando SO.
- Viewport390x844: clientWidth/scrollWidth ambos375 (scrollbar15), sem overflow
  horizontal; esfera/controles responsivos. Override restaurado antes da entrega.
- Primeiro picker usando fixture TEMP inacessivel retornou erro generico.
  Copia explicita da mesma fixture para diretorio de entrega acessivel passou.
  Nao houve ampliacao de permissao/ACL ou fallback que abrisse arquivos humanos.

## Limites

Audio sintetico de ensaio e API WebAudio reais; Core/STT/TTS live nao envolvidos.
Nao foi usado o WAV privado do dublador. Nao prova fidelidade, sincronismo
fono-visemico, perceptual performance/FPS ou acesso em outro browser/hardware.
Oscilacao speaking_fixture continua sintetica e rotulada. Nenhum dado canônico
ou grant foi criado. Servidor efemero pode ser encerrado; entrega nao e deploy.

52 JS e36 Python Web passaram; standard global Windows passou. Rerun Web apos
formatacao final complementa gate; sem release/capability promovida.
