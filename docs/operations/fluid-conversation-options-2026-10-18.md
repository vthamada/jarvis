# Conversa fluida: caminhos e evidência necessária

Estudo de 2026-10-18, a partir do código local e de fontes primárias consultadas
nesta data. Escopo desta frente: leitura e proposta; nenhum modelo, teste,
servidor, instalação, download, conta ou upload foi executado. Não promove
capability. As provas de 17/10 abaixo são históricas e não foram reexecutadas.
Aplicadas `code-verification` e sua matriz para separar suporte declarado de
desempenho comprovado; `OpenAI Docs` somente para a referência Realtime.

## Decisão prática

O problema não se resolve apenas trocando o motor de voz. Hoje há três barreiras
independentes: tempo até reconhecer o pedido, geração/reprodução de áudio e
forma/conteúdo da resposta soberana. A prévia anterior usava Core nativo sem LLM
generativo habilitado; sua final de comparação tinha 2635 caracteres. Uma voz
perfeita não transforma esse caminho em conversação geral nem torna uma final
longa uma boa fala curta.

Prioridade: diagnosticar as fases do TTS antes de servidor residente ou
streaming; reutilizar condicionamento somente com compatibilidade demonstrada;
em paralelo, qualificar endpointing e ASR rápidos preservando revisão. Só depois
projetar modo hands-free, fala incremental e barge-in completo. Não aumentar
timeout nem cortar/resumir a final no browser para simular fluidez.

## Linha de base local e cadeia de latências

| Etapa atual | Evidência por leitura ou prova anterior | Consequência |
| --- | --- | --- |
| Captura | `microphone-capture.mjs`: gesto explícito, PCM16 mono, `ScriptProcessorNode`, máximo30s; encerra por botão/limite. | Não há detector de fim de fala; limite não significa envio automático. API de captura obsoleta não é streaming ASR. |
| ASR | `transcribe.py` cria processo por pedido. `asr_worker.py` importa PyTorch/Transformers, carrega modelo/processador, reamostra16kHz, usa janelas20s e beam5. | Carga é paga novamente por turno; a saída chega após transcrição completa, não como parcial ao vivo. |
| Revisão | `live-conversation-voice.mjs` termina em `onTranscript`; módulo não tem autoridade para submeter ao Core. | Há espera humana legítima entre rascunho e Enviar, separada de tempo computacional. |
| Core | Final textual validada/persistida precede fala. Generativo é opt-in separado. | Primeiro texto visível hoje é a final, não tokens arbitrários de um LLM. |
| TTS | `voice_profile.py` força lote integral; `lab_batch.py` lança um processo; `worker.py` carrega um modelo por lote, gera partes exatas em sequência e usa referência em cada chamada. | Não carrega um modelo por parte, mas recarrega por turno; condicionamento repetido por parte é candidato concreto de desperdício. |
| Entrega | Lote só é aceito completo e montado atomicamente. Serviço só publica WAV completo; browser faz polling500ms e baixa WAV antes de tocar. | Mesmo primeira parte rápida não reduz a primeira fala atual. Polling pode acrescentar espera, mas não explica300s. |
| Reprodução | Esfera usa RMS do caminho WebAudio real; tom fixture comprovou wiring. | Movimento não prova qualidade vocal, TTS real ou conversa física. |

Fonte local: [runbook Web](local-web-voice-conversation.md),
[avaliação de clonagem](voicestudio-cloning-assessment-2026-10-17.md),
[opções de provedores](provider-options-2026-10-17.md),
[worker ASR](../../apps/jarvis_voice_lab/asr_worker.py),
[worker TTS](../../apps/jarvis_voice_lab/worker.py),
[lote](../../apps/jarvis_voice_lab/lab_batch.py),
[serviço de voz](../../apps/jarvis_api/voice_service.py) e
[síntese soberana](../../engines/synthesis-engine/src/synthesis_engine/engine.py).

Prova anterior: Whisper Small/CUDA concluiu10s de gravação em27,81s totais,
incluindo preparação/worker/cleanup. Não é latência steady-state nem prova de
microfone. Qwen Base0.6B/CUDA excedeu300s; nenhuma parte concluída foi localizada.
Importação isolada levou14,66s no total, sem carregar pesos. Esses fatos não
isolam carga, condicionamento, tokenização, geração ou salvamento como causa.
Ausência de flash-attn, VRAM4GiB e final extensa são hipóteses/contexto, não causa
comprovada do timeout. O resultado é falha funcional, não benchmark concluído.

## O que cada tecnologia pode realmente mudar

### Qwen3-TTS: cache do prompt antes de streaming

A API Base aceita `create_voice_clone_prompt` e posterior `voice_clone_prompt`;
sem isso, `generate_voice_clone(ref_audio=...)` constrói o prompt. Podemos
reaproveitá-lo **dentro do mesmo lote**, com mesmo modelo/referência/perfil,
evitando extração repetida. Não presumir ganho percentual ou equivalência de
WAV sem teste. Não persistir embedding sensível por conveniência.
[API e caminho efetivo](https://github.com/QwenLM/Qwen3-TTS/blob/main/qwen_tts/inference/qwen3_tts_model.py).

O README descreve arquitetura streaming, mas a docstring da API Python diz que
`non_streaming_mode=false` simula entrada textual streaming, sem habilitar
geração incremental real. Nosso worker recebe listas de WAVs completos. Logo
mudar essa flag não implementa streaming. A mesma API exige texto de referência
no modo ICL; ASR não pode confirmar esse texto por conta própria.
[Contrato Python](https://github.com/QwenLM/Qwen3-TTS/blob/main/qwen_tts/inference/qwen3_tts_model.py),
[visão do modelo](https://github.com/QwenLM/Qwen3-TTS).

vLLM-Omni já documenta Qwen com PCM incremental, voz pré-computada e WebSocket;
PCM depende da configuração `async_chunk`, e entrada WebSocket por padrão pode
esperar `input.done`. Isso é outro runtime, não recurso já disponível no nosso
SDK. Considerá-lo em host Linux/GPU com margem, não impor serving complexo a
Windows/4GiB antes de medir o caminho existente.
[Streaming Qwen no runtime oficial](https://docs.vllm.ai/projects/vllm-omni/en/latest/user_guide/examples/online_serving/text_to_speech/).

### Chatterbox: separar PT-BR atual, Turbo e Flash

O worker JARVIS usa um SDK/fine-tune PT-BR local específico (`t3_pt_br`,
`s3gen_v3`), não necessariamente a API upstream atual. Upstream multilingual
possui `prepare_conditionals` e reutiliza `conds` se a referência não é passada
novamente. É uma referência para otimização, condicionada à assinatura e aos
pesos locais; manter o watermark do caminho normal.
[Código multilingual](https://github.com/resemble-ai/chatterbox/blob/master/src/chatterbox/mtl_tts.py).

Chatterbox-Turbo e Nano são listados como inglês, não substitutos PT-BR
qualificados. Multilingual V3 e pacotes de idioma são caminhos distintos.
[Família e linguagens](https://github.com/resemble-ai/chatterbox).

Existe também **Chatterbox-Flash**, projeto da Resemble com trabalho de difusão
em blocos/streaming. Não confundir com Turbo, nem com forks HTTP que apenas
fragmentam um WAV pronto. O pacote declara tokenizer inglês preservado; seu
exemplo público retorna WAV completo. Não há nesta revisão demonstração de
clonagem PT-BR, streaming integrado ou execução Windows/4GiB do nosso material.
Classificação: referência, não próxima migração.
[Projeto Flash](https://github.com/resemble-ai/chatterbox-flash),
[artigo dos autores](https://arxiv.org/abs/2605.30748).

### ASR: faster-whisper/CTranslate2 como experimento comparável

faster-whisper oferece CTranslate2 com `float16` ou `int8_float16` em CUDA e
`int8` em CPU. `segments` é generator: a inferência só começa ao iterar; medir
apenas o retorno da função produziria um tempo falso. GPU depende das versões
corretas de CUDA/cuDNN. Conversão/download de pesos é preparação nova, não apenas
trocar o path Transformers atual. Batch grande melhora throughput, não
necessariamente latência de um interlocutor e pode consumir mais memória.
[Uso e requisitos](https://github.com/SYSTRAN/faster-whisper).

Consultar tipos realmente suportados e registrar tipo efetivo; CTranslate2
pode converter para outra precisão conforme hardware/backend.
[Quantização e fallback de precisão](https://opennmt.net/CTranslate2/quantization.html).

Primeiro comparar o Small já conhecido: Transformers/CUDA versus CTranslate2
CPU-int8 e CUDA-int8_float16. Variar runtime/device antes de variar tamanho
facilita atribuir o ganho. Tiny/Base multilíngues são candidatos depois, não
`.en`. Turbo não é sinônimo de menor: upstream lista809M parâmetros e memória
estimada maior que Small. Esses números são dos autores, não limites/benchmarks
do nosso wrapper ou garantia de caber junto com TTS/LLM.
[Modelos Whisper](https://github.com/openai/whisper#available-models-and-languages).

CPU-int8 pode liberar GPU para TTS, mas16GiB de RAM e CPU também são recursos
compartilhados. Comparar beam5 e beam1 como condições separadas; rapidez que
perde negações, nomes ou números não é progresso. Whisper não fornece por si o
protocolo de captura contínua/endpointing do JARVIS.

### Silero VAD: terminar o turno, não autorizar ações

Silero fornece probabilidades de fala e estado por chunks; há PyTorch/ONNX,
8/16kHz e exemplo browser. `VADIterator` possui silêncio mínimo e padding. Isso
permite endpointing local sem chamar um LLM, mas não detecta consentimento,
identidade, destinatário ou se o pensamento terminou.
[Projeto](https://github.com/snakers4/silero-vad),
[iterator e parâmetros](https://github.com/snakers4/silero-vad/blob/master/src/silero_vad/utils_vad.py).

Usar como referência/experimento. Modelo/ONNX/browser e AudioWorklet requerem
assets locais pinados, limites e revisão específica de CSP; não abrir CDN,
`blob:` ou permissões amplas como atalho. Padding, silêncio e histerese devem
ser testados em PT-BR com pausas, ventilador e retorno dos alto-falantes. Começar
com botão de falar ou half-duplex; VAD sem controle de eco pode ouvir o próprio
JARVIS. Headset é uma condição de teste separada, não solução universal.

### VoiceStudio/OmniVoice GGUF: candidato de memória, não prova de fluidez

O guia GGUF oferece execução externa quantizada, incluindo Q8_0/Q4_K_M para
memória menor e clonagem. O processo é criado por geração; não elimina cold
start automaticamente. O checkout usa placeholders; binário real e pesos são
preparação explícita. Footprint publicado não mede pico/latência deste host.
[Guia do motor](https://github.com/debpalash/VoiceStudio/blob/main/docs/engines/omnivoice-gguf.md).

O build Windows consultado chama CMake sem habilitar CUDA explicitamente.
Não inferir aceleração NVIDIA do nome GGUF. Licenças/direitos dos componentes
continuam separados e exigem revisão antes da preparação/distribuição.
Classificação: absorver depois do diagnóstico e A/B dos motores presentes.
[Build](https://github.com/debpalash/VoiceStudio/blob/main/scripts/build-omnivoice-tts.sh),
[avaliação local de direitos/artefatos](voicestudio-cloning-assessment-2026-10-17.md).

### Realtime cloud: referência de interação, não cérebro alternativo

A documentação oficial OpenAI separa VAD de criação/interrupção automática de
resposta; eventos de fala podem existir sem resposta automática. Essa separação
é útil ao desenho do JARVIS. Speech-to-speech autônomo em cloud, porém, não pode
falar antes da final soberana e depois fingir que passou pelo Core. Qualquer
experimento futuro exigiria contrato próprio de transporte/egress/conta/teto,
sem reaproveitar OAuth como autorização implícita nem enviar a voz privada.
[VAD](https://developers.openai.com/api/docs/guides/realtime-vad),
[controle de eventos](https://developers.openai.com/api/reference/resources/realtime/client-events).

Não se usou serviço remoto nem se afirma acesso pela assinatura ChatGPT. A
avaliação acima é arquitetural: a alternativa mais simples de preservar
soberania continua ASR → Core → TTS, não um segundo agente paralelo que conversa
e executa ações fora dele. OmniVoice, OmniRoute e Qwen-Omni são projetos/camadas
distintos; nomes parecidos não indicam integração nem compatibilidade.

## Medir uma conversa, não só um WAV

Usar correlação opaca entre eventos, relógio monotônico local e durações sem
texto, paths ou voz no trace público. Não subtrair diretamente timestamps do
browser e do processo Python, que têm origens de relógio diferentes.

| Métrica proposta | Fronteiras observáveis |
| --- | --- |
| `endpoint_delay_ms` | Última fala rotulada do usuário → encerramento de captura. Separar botão humano de VAD. |
| `asr_ready_ms` | WAV finalizado → rascunho disponível no browser; detalhar upload/import/load/resample/decode/return. |
| `review_wait_ms` | Rascunho disponível → Enviar explícito. Não misturar esse tempo com inferência. |
| `core_first_text_ms` | Enviar → primeiro texto canônico disponibilizado; hoje é a final completa. Não contar placeholder como texto do Core. |
| `tts_first_part_ms` | Solicitação TTS → primeira parte PCM/WAV válida no worker. Hoje é diagnóstico privado, não áudio já entregue. |
| `first_audible_audio_ms` | Fim da fala do usuário → primeira amostra de fala efetivamente tocada. Separar espera de revisão e não contar tom/ack fixture. |
| `turn_complete_ms` | Fim da fala → final textual disponível, geração concluída e reprodução concluída, com marcos separados. |
| `barge_in_stop_ms` | Interrupção explícita/fala aceita → áudio em zero e geração encerrada confirmada; medir os dois tempos. |

Registrar também duração do áudio, RTF de geração, texto/partes em contagens,
falhas/timeouts, CPU/RAM/VRAM pico, device/precisão efetivos, revisão corretiva,
erros de nomes/números/negações, omissões/repetições e aceite humano separado
para naturalidade e semelhança. Manifesto privado pode conter hashes de roteiro
e referência; embedding/gravação/transcrição não devem ir ao log operacional.

Separar condições:

- **Cold process/model:** processo novo, importação e carga incluídas, pesos já
  preparados offline. Registrar cache de disco do sistema como desconhecido ou
  previamente aquecido, sem fingir que é disco frio.
- **Warm model:** mesmo processo/modelo e prompt realmente reutilizados,
  warmup declarado à parte. Hoje não existe entre turnos Web; não publicar uma
  segunda chamada por processo novo como benchmark warm-resident.
- **Isolado versus composto:** ASR, TTS e LLM primeiro individualmente; depois
  mesma sequência do produto, com política de recursos. Uma GPU4GiB não é
  evidência de que os três caibam residentes/simultâneos.

Corpus mínimo:20 falas PT-BR curtas, com referência humana, incluindo saudação,
pergunta, correção, negação, nomes/números, pausa interna, silêncio/ruído e
interrupção. TTS: roteiro curto, médio e a final canônica integral atual; mesma
referência/seed/configuração por comparação. Medir repetição suficiente para
variância; com20 casos, p95 é uma estimativa inicial, não SLO robusto.

Como meta de produto inicial a negociar, buscar resposta audível em poucos
segundos para pedidos curtos; isso não é capacidade atual nem SLA aprovado.
Na primeira rodada, o aceite útil é localizar a fase lenta e obter geração
curta concluída com texto integral, depois comparar mediana/tail e qualidade.

## Três slices pequenos, em ordem

1. **Diagnóstico do TTS sem mudar o resultado.** Instrumentar marcos
   limitados de import/carga/condicionamento/parte/salvamento/cleanup, sem alterar
   a entrega atômica. Capturar a última fase confirmada mesmo no timeout. Depois
   medir uma frase curta antes da final longa, uma condição por vez. Testes de
   ordem, limite, cancelamento, privacidade e falha/timeout preservando a última
   fase sem reportar sucesso parcial. Rollback: desativar diagnóstico, manter
   a mesma geração/entrega anterior.

2. **Condicionamento Qwen uma vez por lote.** Se a assinatura instalada
   suportar `create_voice_clone_prompt`/`voice_clone_prompt`, reutilizar dentro
   daquele processo e perfil. Sem residência entre sessões nem cache em disco.
   API incompatível deve falhar claramente, não trocar motor silenciosamente.
   Fixture independente deve verificar uma criação para várias partes, mesmos
   substrings/hashes, seed/perfil/idioma, cancelamento e nenhum agregado parcial.
   Prova real compara condição anterior/nova no mesmo roteiro; não prometer WAV
   bit-idêntico só porque texto/seed coincidem. Rollback: retornar à chamada
   explícita anterior do SDK, sem migrar dados ou permissões.

3. **Bancada ASR com contrato de revisão preservado.** Benchmark offline do motor
   atual e candidato CTranslate2 antes de instalar/integrar dependência central.
   Mesmo WAV/idioma/beam5, medição incluindo consumo do generator, device/precisão
   efetivos e texto humano de referência; tiny/beam1 são comparações separadas.
   O artefato continua rascunho, sem envio ao Core. Testes de saída inválida,
   negação/números, timeout/cancelamento e isolamento de perfil; rollback é
   selecionar o motor anterior. Um harness de benchmark não promove o adapter
   novo nem implica instalação autorizada de pesos/dependências.

## Evoluções posteriores, não embutidas nos slices pequenos

Endpointing local opt-in pode parar/transcrever automaticamente após silêncio,
mas rascunho continua revisão não confirmada. Consentimento de sessão é
específico para escuta/segmentação local, revogável e apagado ao ocultar,
desconectar ou expirar sessão. Testes de silêncio/ruído/pausas/limites,
permissão tardia, feedback do alto-falante e nenhum Enviar implícito. Prova
física exige operador; não gravar o ambiente silenciosamente. Rollback:
botão push-to-talk e stop/transcrever manuais já existentes.

Core precisa produzir resposta apropriada ao modo conversacional, validada e
persistida, não relatório longo lido por inteiro por acidente. Uma projeção
oral curta futura deve ser artefato explícito do Core, com vínculo à final e
testes de conteúdo/autoridade, nunca resumo oculto pelo browser/TTS. Sem novo
contrato, manter a final integral atual. Streaming posterior pode entregar
partes ordenadas dessa final já aceita, com manifesto/digest, backpressure,
cancelamento e estado parcial explícito; tocar parte não torna lote completo
nem permite rollback do que o usuário já ouviu. Não falar tokens de raciocínio
provisório antes de governança/síntese final.

Modo hands-free exige decisão adicional: permissão para capturar, permissão
para submeter ASR sem revisão e consentimento generativo são três escopos
diferentes. Negação/correção/baixa confiança não podem autorizar ações externas.
Não expandir um checkbox de fala automática para dar essas permissões.

Barge-in começa com interrupção de reprodução/worker e fence contra callbacks
tardios. A nova fala cria outro turno pelas mesmas regras. Não apagar/repetir
uma ação já executada, desfazer final persistida, reescrever memória canônica ou
executar novamente um ticket para retomar áudio. No futuro, progresso de fala
ouvido pode ser metadado de apresentação vinculado à final, não uma segunda
memória factual. O caminho atual já separa cancelar voz de cancelar Core;
preservar essa fronteira.

## Veredito e fronteira de promoção

Especificação de conversa fluida: **não atendida nas provas históricas**.
Viabilidade das otimizações: **parcial por código/documentação**; latência,
qualidade PT-BR, microfone e convivência de recursos precisam de medição.
Qwen conditioning e diagnóstico são as mudanças menores com justificativa
direta. Residency/streaming/Realtime e troca de motor não são pré-requisitos
para corrigir a primeira falha nem foram habilitados por este estudo.

Código upstream em branch móvel deve ser pinado/revisto antes de experimento.
Nenhum número dos autores foi promovido a benchmark JARVIS. Nenhuma revisão
perceptiva da voz humana foi realizada nesta frente. Não houve workloads nem
gate por este agente; o coordenador é o executor único dos testes e da rodada
integrada, com HANDOFF/backlog sincronizados por ele.
