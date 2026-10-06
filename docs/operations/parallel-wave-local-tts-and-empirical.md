# Quarta onda: TTS local, Web, MCP e avaliacao empirica

Data: 2026-10-02. Desenvolvimento opt-in, nenhuma capability promovida.
MB218 permanece in_progress; MB219 blocked. Docker/Linux deferred pelo operador.

## Entregas e limites

- `apps/jarvis_voice_lab`: laboratorio Chatterbox PT-BR V3 e Qwen3-TTS Base 0.6B.
  SDKs separados do Core, texto via stdin, referencia WAV readonly, consentimento
  explicitamente declarado. Isso nao verifica biometricamente dono ou autorizacao.
  Pesos publicos/revisoes/hashes em `tools/download_voice_lab_models.py`.
  Referencias/amostras privadas ficam no TEMP local, nao no workspace OneDrive.
  SDKs/pesos publicos em `.research/voice-lab`, ignorados pelo Git. O checker de
  encoding exclui esse runtime externo, sem excluir documentacao canonica.
- `apps/jarvis_web`: consentimento, transcricao fixture revisavel, envio exato,
  final textual e playback/interrupcao simulados. Sem microfone/STT/TTS/Core live.
  Novo asset `/voice-controller.mjs`; servidor antigo 8765 precisa reinicio manual.
  Skill AwesomeDESIGN.md orientou estados, foco e integracao visual sem rebrand.
- `apps/jarvis_mcp`: subprocess proprio stdio JSON-RPC real com servidor fixture
  readonly, initialize/list/call, schema/binding/limites/cancelamento. Nao conecta
  servidores pessoais, nao autentica e nao concede autoridade ao conteudo externo.
- `evolution/empirical_runner`: dois ports executados, corpus congelado, scorer
  independente, repeats e holdout transparentes. Piloto `empirical_pilot` chama
  dois Core reais da mesma revisao em runtimes SQLite temporarios separados.
  Prova de pipeline, nao ganho de inteligencia nem evolucao/autopromocao ativa.

## Reproduzir sem modelo real

```powershell
.venv/Scripts/python.exe -m apps.jarvis_console.empirical_pilot
.venv/Scripts/python.exe -m pytest apps/jarvis_mcp/tests evolution/empirical_runner/tests tests/integration/test_empirical_core_pipeline.py
node --test apps/jarvis_web/tests/*.test.mjs
.venv/Scripts/python.exe tools/engineering_gate.py --mode standard
```

Piloto empirico observado: 12/12 medicoes, 6 turnos canonicos consultados e 155
eventos por braco, governanca defer_for_validation, nenhum dispatch. Score exato
0/6 nos dois bracos; respostas finais nao foram alteradas para melhorar score.
Corpus pequeno de contrato nao e benchmark de inteligencia do JARVIS.

## Preparacao e inferencia privada

Downloads sao exclusivamente entrada de software/pesos publicos, nunca upload
de WAV/texto. Nao usar demos Gradio hospedados, URLs de referencia ou HF tokens.
Downloader sem `--download` faz somente dry-run. Com opt-in verifica integridade
e so publica arquivos completos sem sobrescrever resultados existentes.

```powershell
.venv/Scripts/python.exe tools/download_voice_lab_models.py --engine qwen3_tts --download
.venv/Scripts/python.exe tools/download_voice_lab_models.py --engine chatterbox_pt_br --download
.venv/Scripts/python.exe tools/download_voice_lab_models.py --engine chatterbox_pt_br_source --download
```

Qwen usa `Qwen/Qwen3-TTS-12Hz-0.6B-Base`, revisao 5d83992436eae1d760afd27aff78a71d676296fc,
SDK qwen-tts 0.1.1. Modo x_vector_only sem transcricao da referencia pode reduzir
fidelidade; nao alegar identidade vocal comprovada. Chatter usa pesos PT-BR
b3952f18bc2eaa72b9bd7c17d2c4653bcad4770d e loader oficial do demo
9e515821e826e207cd617a0fdd0223899ed108ea: nao substituir pelo loader PyPI generico.
Watermark Chatter preservado. Ambiente experimental Torch 2.6.0+cu124 separado;
demo oficial lista 2.8.0, portanto compatibilidade exige evidencia local.

Inferencia offline via cache local, sem credenciais herdadas e com guarda Python
de rede. Isso nao e sandbox de SO contra extensao nativa maliciosa. Windows ACL
segue conta do operador; TEMP nao garante sigilo contra outro processo dessa conta,
backup configurado ou administrador. Artefatos temporarios podem expirar; copiar
somente mediante decisao do operador para destino privado fora de sincronizacao.

GPU observada RTX3050 Laptop 4GiB e RAM16GiB. Rodar motores sequencialmente,
medir fallback CPU explicitamente, nao mascarar OOM como sucesso GPU. Amostra
bench TTS nao representa conversa/JARVIS live nem clonagem validada por escuta.

## Estado de validacao

Pesos dos dois motores e fonte PT-BR baixados com hashes verificados. Duas
inferencias reais concluiram sequencialmente em `cuda:0`, sem fallback remoto,
com o mesmo texto de qualificacao e os 10 s iniciais do WAV autorizado. WAVs
mono PCM16 a 24 kHz, frames completos e hashes relidos pelo coordenador:

| Motor | Evidencia | Duracao audio | SHA256 |
| --- | --- | --- | --- |
| Chatterbox PT-BR V3 | model_real | 5.12 s | 3e38f51835a6e6c309d2961dffbdde9b3ee79faafbf40266f1532a4f9d566e53 |
| Qwen3-TTS Base 0.6B | model_real | 5.68 s | 763efee719066e56ef1c647d6b154008573fd28b5872dab722a1bd015fe02dff |

Duracao e do audio, nao latencia nem avaliacao perceptual. Nao houve escuta/
comparacao humana de fidelidade nessa validacao inicial. Posteriormente o operador
ouviu e rejeitou as primeiras amostras como roboticas; qualidade nao aprovada.
Chatter preserve watermark; Qwen x-vector-only.
Pip check passou nos dois ambientes; import Qwen avisou ausencia de executavel
SoX/FlashAttention, mas SDPA/inferencia local concluiram. Nao instalar esses
extras nem reivindicar aceleracao FlashAttention.

Ligacao conversa Core -> TTS ainda nao esta fechada fisicamente: final padrao
observado excede o limite de 600 caracteres do piloto; recusa, nao trunca nem
fala input em lugar da sintese soberana. Proximo slice: sintese vocal concisa
subordinada ao Core ou segmentacao integral governada, com testes proprios.
Gate standard global final passou no Windows: encoding/document guardrails/Ruff/
pytest. Bateria focada: 241 Python passed, 1 skip de symlink indisponivel Windows,
42 JS passed. Primeira coleta global ocorreu durante alteracao do mock de stdout
e falhou; mock final passou local e gate repetido depois da estabilizacao passou.
Nenhum skip comprova Linux/hardware; nao houve gate release ou promocao.

`python -m apps.jarvis_console.local_tts_pilot` compoe final canonicamente
persistido/eventos/governanca com laboratorio opt-in. Texto vem de stdin, caminho
privado somente com `--show-output-path`; mesmo conjunto de argumentos do lab.
Core default real observado recusou final3227, 23 eventos, allow_with_conditions,
sem TTS/dispatch. Caminho positivo dos testes usa sintese curta e worker
explicitamente fixture; nao confundir com Core default falando audio real.
Rollback: nao invocar pilotos. Nenhuma alteracao de registry central ou dependencia
central nova; ambientes experimentais privados nao entram em pacote/release.

## Revisao vocal e ASR local (rodada seguinte)

Controles experimentais no lab: referencia start/duration (3–15s), seed,
Chatter conversational (.35 exaggeration/.3 cfg/.75 temperature) e Qwen ICL
com transcricao exata revisada/confirmada obrigatoria. Janela ICL nao trunca.
Nova amostra Chatter real CUDA 5.32s/24kHz mono PCM16, SHA256
414d769aaaeccebda4795754999b1b0180f3b763cfcb98c87cfaff0b541da48f,
ainda nao avaliada pelo operador. Nao promover como solucao da voz robotica.

WAV original de 498.25s processado localmente por Whisper-small, revisao publica
973afd24965f72e36ca33b3055d56a652f456b4d. Pesos e tokenizer hash verificados,
SDK no ambiente Qwen separado; nenhum upload ou hardware de audio aberto.
Primeiro passe teve repeticoes artificiais e marcas longas; nao aceito como
referencia ICL. Reprocessamento independente a cada 20s reduz propagacao de
contexto; timestamps localizam janelas, nao palavras. Reexecucao real concluiu
em 84.2s: 25 janelas cobrem 0–498.25s. Repeticoes longas anteriores ausentes,
mas rascunho ainda apresenta palavras/frases incorretas; nao ha precisao atestada.
Pode errar/omitir/alucinar.
TXT/JSON privados no TEMP, review_required=True; nunca identifica locutor nem
autoriza automaticamente clonagem. Gate standard global Windows desta rodada
passou; 140 testes focados passaram e 1 skip Windows. Sem release/promocao.

## Comparacao solicitada de referencias

Rodada exploratoria: A=44–54s, B=220–230s, C=360–370s do original, mesma frase
de qualificacao mais longa e seed42. Selecao por rascunho, nao avaliacao auditiva.
Executar ASR sobre cada janela exata, Chatter conversational e Qwen ICL draft,
sequencialmente em CUDA. Nao misturar referencia/ASR de janelas diferentes.

qwen_icl_draft e opt-in separado, aceita somente transcript_confirmed=False;
metadata inclui reference_transcript_reviewed=False/review_required=True.
Isso nao enfraquece qwen_icl confirmado nem transforma ASR em texto conferido.
Original somente leitura, referências/amostras/manifest privado no TEMP; sem
upload, playback automatico, nova capability ou integracao soberana promovida.
Seis inferencias reais concluiram em CUDA, mono PCM16/24kHz. Mesmo texto:
"Bom dia, senhor. Ja organizei suas prioridades. Podemos comecar pela tarefa
mais importante, ou revisar os detalhes primeiro. O que prefere?" (acentos
presentes no input real; texto completo no manifest privado).

| Referencia | Chatter duracao / SHA256 | Qwen draft duracao / SHA256 |
| --- | --- | --- |
| A | 13.16s / 32aaf61af6ad1ca31ba76cd5cde1c722bffd31b2cbd32448e2b63267e419b38a | 8.00s / 461a99c13e25df34bbcf4613feca50a894af59dccabafc60e4bce6d6d4da3f3e |
| B | 9.76s / 41e6e6cc13a98bac96b1de295f00017733b00749acac2b9686d08803f5c5e498 | 8.88s / 88634b029597d639f89bf9765ffadd533dbf981bb49b15586c95dd2e6eca7e46 |
| C | 10.44s / 5ccee46ef680c2e73e7b5ae71cefc0a0c8626725238282a3649a5df593cea5a6 | 8.32s / 20b553d43bcfe15b18464f66620177293257bb04b2032e4d81b28ec83d66c3f4 |

Duracoes nao atestam ritmo natural, completude da fala ou qualidade; sem avaliacao
auditiva pelo agente. Qwen segue rascunho ICL, nao confirmado. Copias de entrega
em Codex visualizations fora de Git/OneDrive, hashes comparados ao manifest de
origem, sem modificar original ou remover watermark. Artefatos dependem do host;
TEMP/visualizations nao sao armazenamento permanente garantido.
149 testes focados passaram/1 skip Windows; gate standard global Windows passou.
Qualidade so pode ser julgada pela escuta; nenhuma promocao/release/commit/push.
