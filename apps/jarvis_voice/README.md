# Voz: harness isolado WP-VOICE-01

## MB221: transcricao local revisada

`LocalTranscriptReview` recebe documento ASR fornecido, exige consentimento,
review/edit exatos, hash/revisao/prazo e confirmacao one-shot. Nao abre audio,
modelo ou Core. `ReviewedVoiceCorePort(..., transcript_review=review)` consome
atomicamente o request antes de Core; sem replay/downgrade para fixture. Entrada
assist_only/scope vazio, sem receipt de acao. E2E verifica memoria/final Core
reais locais; nao prova qualidade ASR/TTS, hardware ou UI. O material vocal
privado foi usado nas ondas posteriores registradas no HANDOFF; nao nesta rodada.
[Sequencia/limites MB221](../../docs/operations/parallel-wave-transport-transcript-and-job-inspection.md).

As secoes abaixo descrevem o harness fixture original, nao toda a frente atual.

Implementação local da fronteira push-to-talk: consentimento explícito e
escopado -> áudio **sintético fixture** -> transcrição final revisável ->
confirmação da revisão exata -> port do Core -> síntese final confirmada ->
fala **simulada**, com alternativa textual e interrupção.

Não há microfone, speaker, gravação, SDK, conta, token, provider de áudio,
rede, persistência própria ou dispatch de ferramenta. Os doubles fornecem
texto conhecido e bytes sintéticos. Seus testes ponta a ponta exercitam a
superfície com doubles declarados; não comprovam STT, TTS, Core ou playback
reais. A composição de um port com Core real pertence ao integrador.

## Uso local

Da raiz do repositório:

```powershell
.venv/Scripts/python.exe -m apps.jarvis_voice --consent --scenario completed
.venv/Scripts/python.exe -m apps.jarvis_voice --consent --scenario interrupted
.venv/Scripts/python.exe -m apps.jarvis_voice --consent --scenario incomplete
.venv/Scripts/python.exe -m pytest apps/jarvis_voice/tests
```

Sem `--consent`, o demonstrador recusa antes de simular captura. Consentimento
é uma decisão local explícita de interface, não uma permissão de sistema
operacional ou autorização de ferramenta. A confirmação no demonstrador é
da transcrição fixture conhecida, não de um comando ouvido de verdade.

## Contrato de composição

`VoiceHarness(identity=SurfaceIdentityContract(...), stt=..., tts=..., core=...)`
exige `surface_kind="voice"`, `surface_continuity_status="single_surface"`, scope
vazio e referências de superfície, sessão, operador e usuário presentes. Uma
cópia congelada `VoiceIdentity` evita mudanças do contrato mutável original.
Trocar a identidade/sessão cancela o turno, limpa conteúdo e revoga consentimento.
Essas referências são bindings locais, **não autenticação**. O consumidor real
deve autenticar/validar o principal no boundary apropriado.

- `consent(identity, granted=True)` libera a captura daquele binding.
- `start_capture(identity, deadline_seconds=30)` cria `CaptureTicket` de uso local.
- `finish_capture(ticket, AudioFixture(...))` recebe PCM s16le mono 16 kHz
  estritamente sintético; STT completo vai para `reviewing`, sem enviar ao Core.
- `revise_transcript(ticket, text)` retorna SHA-256 da revisão atual.
- `confirm_submission(ticket, identity=..., transcript_revision=...)` exige
  aquela revisão e envia uma única `VoiceRequest` imutável com `text`, identidade,
  request ID, deadline monotônico local e `authority="none"`.
- `core.interact(request)` retorna `FinalSynthesis` com mesmo request ID/identidade,
  `status="completed"`, `confirmed=True`, referência de síntese e texto final.
  `evidence_mode="fixture"` distingue double; `"core_local"` é reservado à
  composição que de fato recebeu a síntese soberana do Core. Esses campos não
  são prova criptográfica: o port é composição confiável, não JSON externo.
- `speak_final(ticket)` passa **somente essa síntese**, nunca transcrição ou
  resultado parcial, ao TTS. `SpeechFixture` só pode representar bytes sintéticos
  e os mesmos request/ref; `complete_playback(ticket)` marca conclusão simulada.
- `interrupt_playback()` solicita stop best-effort, invalida resultados tardios
  e preserva texto final. `cancel()`/revogação limpam conteúdo; `poll_deadline()`
  permite ao consumidor expirar o turno e parar playback simulado explicitamente.

Limites: áudio entre 2 e 640.000 bytes (até 20 segundos neste formato), sem
silêncio completo; texto de 1 a 4.000 caracteres; deadline maior que zero e até
60 segundos; até 256 eventos locais. Identidade e revision hash não concedem
grants, leases, dispatch, acesso a recursos ou aprovação de ação. Transcrições,
inclusive imperativas, são entrada de texto não confiável: interpretação,
governança, memória canônica e síntese final continuam no Core.

`snapshot()` é projeção explícita para exibição local e pode conter transcrição
ou síntese; **não deve ser enviada a telemetria**. `events()` entrega somente
nome fixo, estado e geração, sem áudio, texto, refs privadas ou exceções.

## Limitações e próximo recorte

Ports são síncronos e deadlines são verificados antes/depois das chamadas.
O harness não inicia timer, thread ou scheduler e não força encerramento de
provider bloqueado. Cancelamento descarta respostas tardias; não desfaz um
request já entregue ao Core. Um transporte real terá que impor seus próprios
timeouts/cancelamento e a UI terá que chamar `poll_deadline()` ou mecanismo
equivalente. Interrupção de fixture não prova parada de um dispositivo real.

A voz provisória é somente a fixture, sem semelhança vocal afirmada.
Eduardo Borgerth permanece requisito futuro condicionado a autorização,
licenciamento/material e provider verificados. Nenhum sample de terceiro foi
coletado, clonado ou usado, e ninguém foi contactado.

STT/TTS e hardware reais, UX de permissão do microfone, streaming, autenticação,
integração da superfície ao runtime, qualidade vocal e áudio OAuth continuam
pendentes. Desativação/rollback: deixar de compor o harness; não há dados
persistentes próprios a apagar nem nova capability promovida.
