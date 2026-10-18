# Conversa Web por voz local — integração experimental

Continuação de18/10: diagnóstico de fases, reuso opt-in de condicionamento e
ASR experimental estão em validação separada. Ver
[evidências e limites atuais](voice-latency-diagnostics-2026-10-18.md) e
[estudo de fluidez](fluid-conversation-options-2026-10-18.md). Os números abaixo
são da revisão de17/10; não qualificam as mudanças posteriores.

Rodada de 2026-10-17. Ponte experimental integrada; gate standard Windows aprovado
exit0:10704 passed/121 skipped/zero falhas/errors,25 hashes preservados.
Aceite funcional permanece parcial: TTS real falhou e microfone físico não foi
acionado. Não declarar conversa utilizável ou fluida a partir do gate de código.
O recorte não promove naturalidade da clonagem, autenticação por voz, escuta
contínua, operação duplex ou autoridade para ações.

## Fluxo e consentimentos

1. O host inicia a Web com `--authorized --enable-voice --voice-profile` e um
   arquivo **absoluto, privado e explicitamente selecionado**. Sem essas opções,
   a voz continua desativada e `Permissions-Policy` proíbe microfone.
2. Parear a sessão local continua obrigatório. Clicar em **Preparar voz local**
   consulta apenas a configuração pública: não carrega pesos, não abre microfone
   e não autoriza fala automática.
3. Clicar no microfone solicita a permissão normal do navegador. Captura mono
   PCM16, até30s/6MiB, sem retorno do microfone aos alto-falantes. Ao terminar,
   **Transcrever gravação** envia o WAV somente ao mesmo servidor loopback.
4. Whisper local produz rascunho em um campo separado. Revisar e clicar em
   **Usar no pedido · sem enviar** copia o texto ao compositor. **Enviar ao Core**
   continua uma ação explícita; consentimento generativo continua separado.
5. Marcar **Falar automaticamente as próximas respostas finais do Core** arma
   áudio por gesto explícito e vale somente para novos turnos desta página.
   Não narra histórico, recuperação de ticket, final bloqueada ou resposta de
   outra sessão. A configuração é apagada em desconexão, pagehide/BFCache e troca
   de sessão. A transcrição não é enviada automaticamente ao Core.
6. A fala usa só o ticket de uma final `allow` já validada/persistida. O servidor
   obtém a final exata; o browser não pode escolher texto, modelo ou referência.
   Usa o lote local existente, sem resumo, truncagem, descarte de partes ou
   fallback. A esfera lê RMS do `AnalyserNode` que alimenta a reprodução real.

A captura usa `ScriptProcessorNode` como caminho de compatibilidade, atualmente
obsoleto no padrão WebAudio; não foi qualificada em todos os navegadores.
Migração para AudioWorklet e medição de latência são trabalho separado, sem
afrouxar a CSP para anunciar suporte não demonstrado.

Não usamos `SpeechRecognition` cloud nem `speechSynthesis` do sistema como
fallback. A captura usa o caminho de compatibilidade `ScriptProcessorNode`
(API depreciada), com saída zerada e limite de amostras/tempo. AudioWorklet é
uma evolução separada; não afirmar suporte universal ou validação em hardware
que não foi exercitado.

## Configuração do host

O arquivo JSON usa `schema_version=jarvis-local-voice-profile-v1`, `asr` e `tts`.
Cada seção pode ser nula, mas não ambas. Exemplo **ilustrativo**; todos os paths
devem apontar a arquivos locais já preparados e confiáveis:

```json
{
  "schema_version": "jarvis-local-voice-profile-v1",
  "asr": {
    "model_dir": "C:/JarvisPrivate/models/whisper-small",
    "python_executable": "C:/JarvisPrivate/voice-env/Scripts/python.exe",
    "device": "cpu",
    "timeout_seconds": 180
  },
  "tts": {
    "engine": "qwen3_tts",
    "reference_path": "C:/JarvisPrivate/voice/reference.wav",
    "model_dir": "C:/JarvisPrivate/models/qwen-base",
    "python_executable": "C:/JarvisPrivate/voice-env/Scripts/python.exe",
    "device": "cpu",
    "timeout_seconds": 300,
    "voice_profile": "baseline",
    "reference_start_seconds": 0,
    "reference_duration_seconds": 10,
    "transcript_confirmed": false,
    "seed": 42
  }
}
```

Chatterbox aceita o motor existente `chatterbox_pt_br` e `sdk_source_dir` local.
Perfis ICL exigem as confirmações reais do laboratório: ASR não pode confirmar
transcrição humana. Não selecionar uma voz humana sem direitos/consentimento.
Configuração privada da prova ficou ignorada em `.research`; contém localizadores,
não cópia da gravação ou credenciais. Não adicionar ao Git. Não há download de
pesos, instalação, autenticação ou descoberta automática de contas.

```powershell
.venv/Scripts/python.exe -u -m apps.jarvis_api --authorized --port 0 `
  --enable-voice --voice-profile C:/JarvisPrivate/web-voice-profile.json
```

ASR e TTS são subprocessos offline do laboratório já existente, com ambiente
separado/sem tokens herdados. Isso não é sandbox de sistema operacional para
SDKs arbitrários. Modelos locais disputam VRAM: um worker de voz por servidor,
sem executar ASR e TTS simultaneamente nessa instância. Não iniciar duas
instâncias com modelos reais na mesma GPU para contornar esse limite.

## Contratos, falhas e retenção

- Rotas `/api/voice/config`, `/transcriptions`, `/speech`, `/cancel`, `/jobs/{id}`
  e `/audio/{id}` sob prefixo `/api/voice`. Origin, Host, cliente, sessão,
  CSRF e fence de entrega são os existentes. Sem CORS, URL de arquivo ou path
  fornecido pelo browser. JSON mantém32KiB; apenas captura tem limite6MiB.
- Microfone `(self)` somente com ASR configurado; câmera/geolocalização negadas.
  CSP permanece igual, inclusive `media-src 'none'`; WAV toca por WebAudio em
  memória, não por elemento de mídia remoto. Assets novos entram na allowlist.
- Captura/transcrições temporárias da ponte Web ficam sob um diretório próprio,
  fora do workspace, removido ao finalizar o wrapper. Falhas de filesystem/processo
  podem impedir cleanup; não prometer apagamento seguro. O laboratório TTS mantém
  seus artefatos privados temporários, como antes; paths não são publicados na Web.
- Até32 jobs retidos, até900s de elegibilidade; expiração é checada em acesso e
  antes de publicar, e jobs vencidos são retirados ao abrir novos jobs. Não é
  limpeza proativa/segura de RAM. Fechar/revogar limpa os payloads em memória.
  Áudio limitado a32MiB/600s, final até6000 codepoints,16 partes de até600.
- O ticket de análise continua120s. A fala captura a final validada antes disso;
  sua geração até300s não renova a análise nem cria outro turno. A entrega exige
  sessão atual. Snapshot textual imutável é o vínculo do job de áudio.
- Só uma tentativa TTS por ticket retido, inclusive falha/cancelamento. Sem
  retry, troca de motor ou API paga. Resultado tardio não reabre áudio. Cancelar
  voz não cancela/desfaz Core ou memória. Ocultar página interrompe captura e
  reprodução; cancelamento de worker conhecido é solicitado separadamente.
- Falha no worker real deixa voz em indisponibilidade até reinício da instância,
  para não iniciar outro processo após cleanup incerto. A conversa textual segue.
- `web_voice_requested` e `web_voice_finished` são persistidos/readback no
  observability local, vinculados a ticket/sessão, com kind/status/evidence/authority,
  sem texto/path/gravação. Auditoria falha impede sucesso de áudio. Recusa durante
  auditoria pode produzir um evento corretivo de falha, sem publicar candidata.
- ASR é pré-processamento para revisão, não entrada no Core, identificação de
  locutor ou novo registro canônico. Status fixo não é um receipt de ferramenta.

## Evidência e limites atuais

Continuidade18/10: a ponte agora exige confirmacao de saida do worker ASR real
no Windows antes do cleanup. Saida incerta preserva captura/runtime, usa erro
fixo e a quarentena existente; nao presume apagamento. Isso nao altera TTS,
decoding default, revisao ou envio ao Core. Validacao desta continuidade esta
no [runbook lifecycle/CLI local](local-model-cli-and-asr-lifecycle-2026-10-18.md);
os gates/provas abaixo permanecem historicos, nao seu aceite.

Testes novos começaram com11 falhas reais de binding/fixture/cancelamento,
corrigidas sem retirar os oráculos. Primeira tentativa sandbox teve erros de
temporários e foi interrompida; a primeira saída host tinha IDs enormes de
parâmetros, corrigidos para nomes limitados, sem alterar dados/casos.
Serviço135, perfil95 e regressão HTTP/Core/Web256 passaram; JavaScript1282 passou.
São contagens de baterias sobrepostas, não somar como casos independentes.
Primeiro standard terminou exit1:10689 aprovações/121 skips/cinco falhas de
compatibilidade no startup: o cleanup
exigia `voice_service` em servidores mínimos legados. A extensão passou a ser
opcional, sem alterar testes antigos;58 casos legados e10 novos de startup
passaram juntos (68), incluindo voz/default desligado e ordem de encerramento
voz -> autenticação -> Core -> socket. Bateria integrada pós-correção422 passou
em26,79s; não somar aos68, pois se sobrepõem. Standard final aprovado exit0:
10704 passagens/121 skips/zero falhas/errors;25 hashes congelados preservados.
HTTP compõe Core nativo e SQLite, mas seu motor de voz é fixture explícita.
Browser reconheceu perfil Whisper/Qwen real sem erros; preparar não abriu mic.
Prova única real no browser: Core nativo concluiu a mesma pergunta sintética, mas
Qwen Base0.6B/CUDA, referência C original360–370s/x-vector baseline, não concluiu
o áudio dentro de300s. Cliente mostrou `voice_timeout`, cancelou sem retry/fallback
e preservou a final. No diretório criado por esse ensaio havia só referência e
spool vazio, nenhuma parte WAV concluída; não se afirma que o gargalo exato da
carga/geração foi isolado. Não houve reprodução automática real nessa tentativa.
GPU consultada depois: RTX3050 Laptop4096MiB, ocupação/uso reportados0; consulta
da árvore do servidor não encontrou filhos diretos. Isso não prova ausência de
qualquer processo órfão fora dessa árvore nem autoriza matar processos alheios.
Probe separado, **sem pesos/referência/inferência**, confirmou Python3.12.6,
PyTorch em4,81s e SDK Qwen em13,53s (total14,66s), com guard offline e ambiente
sem tokens. O aviso genérico de flash-attn ausente não demonstra a causa da
lentidão; não foi instalado nada. Não chamar esse fluxo de conversa em tempo real
nem dar aceite perceptivo.

ASR real separado concluiu uma única transcrição do recorte autorizado360–370s:
Whisper Small/CUDA,10s de áudio,160 caracteres de rascunho,27,81s totais incluindo
preflight/preparação/worker/limpeza. Esse tempo não é um benchmark steady-state.
Saída não confirmada, sem identificação de falante ou envio ao Core; áudio/drafts
sob diretórios temporários próprios foram encerrados pelo wrapper sem erro.
Prova valida o motor/arquivo, não o dispositivo físico nem toda a conversa por
microfone. Nenhuma segunda tentativa TTS real; mic físico não acionado pelo agente.

QA visual no IAB, por CUA (plugin Browser standalone não disponível): página
pareada -> Preparar voz local -> controles ASR/TTS disponíveis; preparar não
capturou áudio nem gerou fala. Checkbox de fala automática foi ligado/desligado
sem pergunta. Revisão expande, permanece separada do compositor e sem envio.
Desktop1280x900 e mobile390x844: conteúdo presente, sem overlay/erro de console
ou overflow horizontal (1265/1265 e375/375 CSSpx, com scrollbar). Evidências
de tela ficam na pasta de artefatos da sessão, fora do Git.

Prova adicional do wiring no browser usou **Core/SQLite reais com tom sintético
fixture**, não Qwen/voz humana: parear -> preparar -> marcar fala automática ->
preencher comparação pública -> Enviar -> playback automático. Esfera observada
em `speaking_local`, nível0 no silêncio e0,517 no tom; Parar voz retornou
`idle`/0. Consultar o mesmo ticket manteve repouso e não gerou outro áudio;
stdout registrou uma única síntese fixture. Console sem warn/error. Servidor
fixture encerrado, sem modelos/microfone/conta. Isso comprova a ligação de
reprodução/amplitude, **não** o sucesso do TTS real que falhou acima.

Próximo recorte útil: instrumentar tempos separados de carga, condicionamento,
geração da primeira parte e lote completo, preservando a final integral. Só
depois escolher redução de latência/residência/streaming por evidência; não
aumentar timeout ou reduzir/truncar silenciosamente a final para parecer fluido.
Prova de microfone físico, desempenho conversacional e aceite vocal continuam
pendentes, apesar do gate de código aprovado. Recorte funcional segue
`in_progress` no backlog, sem promoção macro.

Relatórios paralelos: [provedores](provider-options-2026-10-17.md) e
[VoiceStudio/clonagem](voicestudio-cloning-assessment-2026-10-17.md).
Não houve novas integrações de provedores, instalação de VoiceStudio ou upload
da voz nesta rodada. Rollback: omitir opções de voz e manter modo textual/WAV
manual; sem migração de banco ou ampliação de autoridade do Core.
