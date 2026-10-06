# Laboratório TTS local opt-in

Experimento isolado: não registra capability, não entra no runtime de voz e não
substitui o Core. `authorized=True`/`--authorized` é obrigatório e registra a
afirmação de autorização do operador, não comprovação jurídica ou licença.

`run_voice_lab(...)` recebe engine (`qwen3_tts`/`chatterbox_pt_br`), caminho local
dos pesos, interpretador do ambiente separado, referência WAV, texto e workspace.
O WAV original é somente leitura. Extrai 10 s por padrão, PCM16, mono (downmix simples de
estéreo), sem alterar taxa nem tentar selecionar automaticamente a melhor fala.
Fontes: até 128 MiB/900 s, 8–96 kHz; samples: até 32 MiB/120 s. A seleção do trecho
inicial pode conter ruído/silêncio e não certifica qualidade. Cada execução cria
`jarvis-voice-lab-<uuid>-.../` no diretório temporário do sistema, fora do workspace,
sem sobrescrever runs ou o original. Pesos/SDK públicos podem ficar em `.research`,
mas referência/sample/cache ficam no TEMP para não colocá-los neste workspace
OneDrive. O laboratório não envia áudio; isso não controla backup/sync externo,
administradores ou ACL Windows. TEMP pode ser limpo automaticamente pelo sistema.

API (texto não vai ao command line):

```python
from apps.jarvis_voice_lab import run_voice_lab
result = run_voice_lab(
    engine="qwen3_tts", authorized=True, reference_path=local_wav,
    text=final_text, model_dir=local_weights, python_executable=isolated_python,
    workspace_root=workspace, device="cpu", timeout_seconds=300,
)
result.metadata()  # status, razão técnica, hash/formato; sem texto ou paths privados
result.output_path  # acesso explícito ao artefato privado, fora do metadata padrão
```

CLI: `python -m apps.jarvis_voice_lab --authorized --engine qwen3_tts
--reference <wav> --model-dir <local-dir> --python <isolated-python> --text-stdin`.
Texto é lido de stdin (até 600 caracteres), passado ao worker por JSON stdin e
nunca impresso. `--show-output-path` expõe explicitamente o caminho do sample.
Logs Python do SDK são descartados; stdout nativo vai a spool temporário próprio,
vigiado por tamanho e lido em até 4097 bytes, removido após o controle. Não há
upload, download, instalação,
playback, escuta contínua ou avaliação automática de semelhança.

Worker lazy, processo separado com env allowlist, HOME/cache próprios, offline
flags Hugging Face/Transformers, tokens/proxies/tracing não herdados e sockets
Python bloqueados. Isso é isolamento de composição, **não sandbox de OS contra
código nativo hostil**. Pesos e fonte SDK precisam ser públicos/revisados e locais.
Timeout/cancel matam e reapam o processo worker; não ativam backend remoto.
Runs incompletos permanecem no TEMP para diagnóstico, não viram samples válidos.
POSIX usa diretório0700/áudio0600; Windows herda ACL do TEMP (não há sandbox ACL).
Pesos/fontes descendentes são verificados contra links/reparse, com limite de
6.000 entries/32GiB. Isso não elimina races de processos locais do mesmo usuário.
WAVs têm frames verificados (incluindo chunks extras), output não pode ser zero;
o worker também recusa arrays vazios, não finitos ou de shape/duração inválidos.
Falhas expõem somente classe/fase allowlisted, nunca mensagem bruta do SDK.

Qwen usa `Qwen3TTSModel.from_pretrained` apenas com caminho local,
`local_files_only=True`, `trust_remote_code=False`, SDPA, float32 CPU/bfloat16 CUDA
e `generate_voice_clone(language="Portuguese", x_vector_only_mode=True)`.
Este modo não requer transcrição da referência e pode limitar fidelidade.
[API oficial](https://github.com/QwenLM/Qwen3-TTS).

Chatter PT-BR V3 requer o fork oficial do demo, explicitamente selecionado por
`sdk_source_dir`/`--sdk-source-dir`, contendo `chatterbox/src/chatterbox/tts.py`.
O loader `ChatterboxTTS.from_local` usa `t3_pt_br.safetensors`, `s3gen_v3.pt` e
companion assets locais; `generate(language_id="pt")` preserva o watermark padrão.
Não há fallback para multilíngue PyPI, cujo loader/config pode ser incompatível.
[Card oficial](https://huggingface.co/ResembleAI/Chatterbox-Multilingual-pt-br),
[fonte do demo pinada](https://huggingface.co/spaces/ResembleAI/Chatterbox-Multilingual-TTS-pt-br/blob/9e515821e826e207cd617a0fdd0223899ed108ea/chatterbox/src/chatterbox/tts.py).

`evidence_mode="fixture"` exige fixture_worker explicitamente injetado. Seus
samples não são clonagem/modelo real. Testes mocked de subprocess validam contratos,
não comprovam inferência. Instalação/pesos e execução real são coordenação externa
ao módulo. Nenhum sample confirma identidade vocal, qualidade ou produção pronta.

## Perfis experimentais e transcrição local

O operador rejeitou as primeiras amostras como robóticas. Não confundir inferência
concluída com qualidade aceita. `--reference-start` e `--reference-duration`
selecionam explicitamente uma janela de 3–15 s; `--seed` permite repetir o ensaio.
Não há seleção automática da melhor fala, remoção de música ou avaliação vocal.

`--voice-profile chatterbox_conversational` usa exaggeration=0.35, cfg_weight=0.3
e temperature=0.75, preservando watermark. São parâmetros experimentais, não uma
garantia de naturalidade. `baseline` mantém os defaults anteriores.

`--voice-profile qwen_icl` exige `--reference-transcript-file` UTF-8 revisado e
`--transcript-confirmed`; passa ref_text e x_vector_only_mode=False. A janela deve
caber integralmente no WAV. Não há truncamento silencioso ou confirmação de ASR.
O texto de referência vai somente por stdin privado, não para metadata/logs.

Para comparação explicitamente experimental solicitada pelo operador,
`--voice-profile qwen_icl_draft` aceita texto ASR **não revisado**, sem
`--transcript-confirmed`. Usa ref_text/ICL, mas expõe voice_profile,
reference_transcript_reviewed=False e review_required=True no resultado.
Não equivale a `qwen_icl`, não aceita confirmação nesse perfil e não promove
qualidade. Os dois modos ICL exigem que a janela caiba integralmente no WAV.
Esse ensaio permite avaliar a hipótese, não confiar no texto reconhecido.

`python -m apps.jarvis_voice_lab.transcribe --authorized --source <wav>
--model-dir <whisper-small-local> --python <isolated-python>` gera TXT/JSON no TEMP,
sem upload, identificação de falantes ou integração com Core. O downloader público
oferece `whisper_small` e `whisper_turbo` em revisões fixas e verifica hashes; o worker usa somente
pesos locais em safetensors e o mesmo bloqueio de sockets/env allowlist.

ASR processa janelas independentes de 20 s, com marcações aproximadas da janela,
não alinhamento palavra a palavra. Cortes e silêncio podem causar erros, omissões
ou alucinações; `review_required=True` sempre. Transcrição automática nunca fornece
`transcript_confirmed` para Qwen. Artefatos contêm conteúdo privado e podem expirar.
Testes de orquestração usam doubles, não atestam precisão do modelo.

## Referências próximas de uma amostra preferida

`reference_selection.suggest_reference_windows(source, anchor_seconds=360)`
sugere até três janelas de 3–15 s próximas da referência C. Busca limitada a
blocos de 20 ms, prioriza bordas com energia baixa e evita referências com menos
de metade dos blocos acima de -35 dBFS. Não é VAD, detector de música, avaliação
de semelhança ou garantia de frase completa; cada resultado exige escuta humana.
Não altera nem grava o original. `prepare_reference(..., exact_window=True)`
extrai explicitamente a janela escolhida para um arquivo novo fora do workspace.

Comparar ASR Small/Turbo deve usar exatamente o mesmo recorte. Concordância dos
rascunhos não os torna corretos nem confirma transcrição para ICL. Turbo está
fixado em `41f01f3fe87f28c78e2fbf8b568835947dd65ed9` (pesos públicos OpenAI),
sem download durante inferência. Executar ASR e TTS sequencialmente nesta GPU.
Uma nova comparação de referências mantém modelo Qwen Base 0.6B, frase e seed
constantes; mudar também o modelo impediria atribuir o resultado ao material.
