# VoiceStudio e a voz autorizada do JARVIS

Revisão de 2026-10-17. Escopo: pesquisa de fontes primárias e leitura do
laboratório existente. Nenhuma instalação, download de pesos, inferência,
upload de gravação, chamada paga ou promoção de capability pela frente de pesquisa.
As provas coordenadas da ponte Web estão diferenciadas abaixo.
Aplicada a skill `code-verification`: suporte declarado, código implementado e
qualidade demonstrada são evidências diferentes.

## Decisão

**Já conseguimos produzir tentativas locais de clonagem zero-shot; ainda não
conseguimos afirmar que a voz de Eduardo Borgerth foi reproduzida com a
naturalidade e semelhança desejadas.** O operador preferiu a referência C do
Qwen, mas considerou o resultado insuficiente. VoiceStudio é candidato útil
para uma bancada comparativa, não uma correção de qualidade já comprovada.

Absorção proposta: `usar como referência` para curadoria/takes e `absorver depois`
para um adapter experimental de OmniVoice GGUF, condicionado a prova local.
Ele não assume memória, interpretação ou síntese soberana do JARVIS. A
autorização de uso da voz já declarada pelo operador é uma premissa operacional,
não uma verificação biométrica ou jurídica realizada pelo software.

## O que temos de fato

| Pergunta | Evidência existente | Limite |
| --- | --- | --- |
| Há material suficiente para experimentar? | O original continua presente; hash relido nesta revisão coincide com o registro anterior. A documentação registra 498,25 s. | Duração não comprova ausência de música, ruído, outros locutores ou falas úteis em todos os trechos. Não houve nova escuta. |
| Já houve modelo real? | Chatterbox PT-BR V3 e Qwen3-TTS Base 0.6B geraram WAVs locais em CUDA, documentados com hashes. | Concluir inferência não aprova identidade, pronúncia ou naturalidade. |
| Melhoramos a referência? | A/B/C e depois C1/C2/C3 foram extraídas; C2 ganhou controle x-vector-only. | Small/Turbo discordaram nos três recortes refinados. ICL permanece `draft`, não texto humano confirmado. |
| Há ambiente disponível? | Diretórios dos ambientes Qwen/Chatterbox e modelos Qwen, Chatterbox, Whisper Small/Turbo estão presentes em `.research/voice-lab`. | Presença de arquivos não confirma integridade atual, importação ou inferência nesta rodada. Hardware é o registrado: RTX3050 Laptop/4 GiB, RAM16 GiB; não foi reconsultado. |
| O Core já tem saída local? | MB224/MB225 compõem final persistida exata com TTS single/batch e preservação textual. | É laboratório/console opt-in; não equivale à fala automática do front-end nem a voz aprovada. |

Fontes locais: [laboratório](../../apps/jarvis_voice_lab/README.md),
[execuções iniciais e A/B/C](parallel-wave-local-tts-and-empirical.md),
[C1/C2/C3](parallel-wave-refined-voice-and-core-pilots.md),
[final persistida](persistent-final-local-tts.md) e
[lote integral](full-final-local-tts-batch.md).
Os diretórios privados históricos de comparação/refinamento foram localizados,
mas sua listagem interna foi recusada pelo Windows inclusive fora do sandbox.
Não se afirma nova releitura dos WAVs/manifests nem se altera ACL para contornar
isso. A referência C original pode ser recriada do WAV legível, pela janela
360–370 s já registrada, sem depender dos diretórios antigos. Não copiar referências,
transcrições privadas ou novos samples para Git/OneDrive.

## O que o VoiceStudio realmente acrescenta

Atualização da integração coordenada nesta rodada: a ponte experimental Web
agora possui captura/revisão e fala opt-in da final, descritas no
[runbook de conversa local](local-web-voice-conversation.md). ASR real de10s
concluiu em27,81s; o ensaio Qwen real excedeu300s sem parte concluída. Playback
automático/RMS foram demonstrados separadamente com tom fixture. Esses fatos
não alteram o veredito de qualidade vocal nem significam instalação do VoiceStudio.

O motor padrão declarado é OmniVoice, com condicionamento por gravação e
transcrição. O projeto recomenda recorte curto e limpo; referências longas podem
ser reduzidas a outra janela. Portanto, para comparar, usar explicitamente o
mesmo WAV recortado e o texto exato desse recorte, sem aceitar seleção automática
como prova de melhor voz. O original de oito minutos não deve ser fornecido
integralmente ao caminho de clonagem.
[Catálogo e política de referência](https://github.com/debpalash/VoiceStudio/blob/main/docs/engines/README.md),
[OmniVoice](https://github.com/debpalash/VoiceStudio/blob/main/docs/engines/omnivoice.md).

| Rota | Aplicação ao host registrado |
| --- | --- |
| OmniVoice PyTorch | O guia recomenda pelo menos cerca de 6 GB de VRAM dedicada. A RTX de 4 GiB pode paginar/ficar lenta; CPU é alternativa a medir, não conversa em tempo real demonstrada. |
| OmniVoice GGUF | Existe adapter com executável Windows, pesos/codec pinados e saída WAV; candidato legítimo para 4 GiB. O probe classifica 4.000 MiB ou mais como `mid-vram`, selecionando Q8_0; Q4_K_M é opção menor. Isso não mede memória livre ou o pico total real. |
| Qwen/Chatterbox via MLX-Audio | Apple Silicon, não Windows. O Qwen curado é VoiceDesign; nessa rota somente CSM é habilitado para clonagem. Não substitui nossos Qwen Base/Chatterbox PT-BR. |

Fontes: [probe real](https://github.com/debpalash/VoiceStudio/blob/main/backend/engines/omnivoice_gguf/hardware_probe.py#L47),
[adapter GGUF](https://github.com/debpalash/VoiceStudio/blob/main/backend/engines/omnivoice_gguf/backend.py#L335),
[guia GGUF](https://github.com/debpalash/VoiceStudio/blob/main/docs/engines/omnivoice-gguf.md),
[MLX](https://github.com/debpalash/VoiceStudio/blob/main/docs/engines/mlx-audio.md).

Não assumir aceleração NVIDIA pelo nome GGUF: o build Windows inspecionado não
habilita `GGML_CUDA` explicitamente. `--help` no preflight não executa inferência.
O CLI pinado exige transcrição com `--ref-wav`; usar texto correspondente,
mesmo que a interface diga que é opcional. Os números publicados de footprint
não provam pico RAM/VRAM nem latência deste host.
[Build Windows](https://github.com/debpalash/VoiceStudio/blob/main/scripts/build-omnivoice-tts.sh#L139),
[CLI pinado](https://github.com/ServeurpersoCom/omnivoice.cpp/blob/886fc079838ca7400cb2b42b36e2a65aa1daabe8/tools/omnivoice-tts.cpp#L54).

O ganho de produto mais seguro é revisar waveform/recorte/transcrição, comparar
takes e localizar clipping/silêncios. Exportar em 24/32 bits ou aumentar passos
não garante semelhança; as verificações de sinal do projeto não são notas de
naturalidade. Sua prova Windows com RTX4090 não valida nossa RTX3050/4 GiB.
[Qualidade e limites da evidência upstream](https://github.com/debpalash/VoiceStudio/blob/main/docs/audio-quality.md).

## Próximo A/B isolado, antes de escolher voz padrão

1. Ouvir C/C2 e escolher um recorte de 5–15 s com um locutor, frase completa e
   sem efeitos perceptíveis. Confirmar manualmente a transcrição exata; manter
   recorte, texto e original privados e imutáveis. ASR pode sugerir, nunca marcar
   `transcript_confirmed` sozinho.
2. Rodada inicial sem motor novo: Qwen Base0.6B `qwen_icl` confirmado versus
   x-vector-only com o mesmo recorte, roteiro e seed42. Assim isolamos o efeito
   do alinhamento. Comparar também Chatterbox PT-BR `chatterbox_conversational`,
   sem remover watermark. Não chamar sementes iguais de aleatoriedade equivalente
   entre motores diferentes.
3. Após aprovação explícita da preparação de software/pesos e avaliação dos
   termos, adicionar OmniVoice GGUF Q8_0 ao mesmo roteiro; Q4_K_M apenas como
   condição separada. Ambiente/cache próprios fora do repositório sincronizado,
   inferência offline, um motor por vez e nenhum fallback remoto silencioso.
4. Usar pelo menos três roteiros: saudação curta; instrução com pergunta e
   pausas; leitura com números, siglas e nomes em PT-BR. Ouvir takes sem o nome
   do motor, em ordem alternada, avaliando separadamente semelhança, naturalidade,
   pronúncia, omissões/repetições e estabilidade entre frases.
5. Registrar tempo até primeiro áudio, tempo total/RTF, pico RAM/VRAM, device e
   fallback real, versões, recorte e seed. Repetir a condição vencedora antes de
   promovê-la. WAV válido/ASR parecido não substituem aceite humano da voz.

Não há latência TTS comparável registrada nos relatórios locais lidos: durações
de 8–10 s são do WAV gerado, não do processamento. O tempo histórico de 84,2 s
para transcrever 498,25 s com Whisper Small também não qualifica a latência de
uma conversa com captura, revisão, Core, TTS e reprodução.

Aceite conversacional adicional: áudio deve vir somente da final canônica
vinculada ao turno, sem reenvio ao modelo, resumo oculto, partes descartadas ou
fala do pedido no lugar da resposta. Cancelamento precisa interromper playback
e geração; erro conserva texto. A esfera deve medir o áudio efetivamente
reproduzido, não um cronômetro decorativo. Qualificar essa integração é separado
de aprovar a identidade vocal.

## Licenças e fronteiras

O app declara AGPL-3.0-only; pesos, tokenizer, gravação e direitos da pessoa têm
termos separados. O card upstream inspecionado identifica pesos OmniVoice como
CC-BY-NC, e o ADR GGUF retirou a aprovação comercial anterior. Quantização não
concede novos direitos. Antes de copiar código/incorporar binários ou distribuir
uma versão comercial, revisar os artefatos e uso concretos; isto não é parecer
jurídico nem autorização comercial.
[Aviso do aplicativo](https://github.com/debpalash/VoiceStudio/blob/main/LICENSE-NOTICE.md),
[card versionado dos pesos](https://huggingface.co/k2-fsa/OmniVoice/blob/c5fdb5ccb189668d56333f77ba2629f4cd7535f4/README.md),
[correção do ADR](https://github.com/debpalash/VoiceStudio/blob/main/docs/adr/SPIKE-01-gguf.md#L4).

Veredito: **viabilidade técnica parcial; qualidade inconclusiva; nenhuma nova
voz aprovada**. O próximo ganho provável é referência/transcrição confirmadas e
A/B controlado, não instalar outra interface esperando melhora automática.
Esta revisão documental não executou testes/gate; a coordenação executa o gate
integrado da rodada antes do fechamento. Rollback: não instalar/invocar o
candidato externo; os motores e a final textual atuais permanecem inalterados.
