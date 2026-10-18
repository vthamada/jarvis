# Voz: diagnóstico de latência e adapter local — 2026-10-18

Recorte de código verificado. Não é aceite de conversa fluida, voz clonada ou modelo local
real. Mesmo WIP1 funcional; MB236 e estados macro não alterados.

## Implementações e fronteiras

- Diagnóstico TTS opt-in `run_voice_lab_batch(..., diagnostics=True)`: sidecar
  privado de fases, até80 eventos/32KiB, sem texto/voz/paths/tokens. Não muda
  request JSON, stdout, resultado público, deadline, cancelamento ou áudio integral.
  Gravação binária/exclusiva, sem seguir redirecionamentos. Leitor estrito vincula
  run/engine/device/partes, sequência e relógio monotônico. Diagnóstico não é
  evidência de áudio válido. Desligado por padrão.
- ASR `decoding_profile`: `quality` continua beam5/default; `conversation` escolhe
  beam1 explicitamente no perfil privado do host ou CLI de transcrição. Não há
  precisão prometida, troca de motor, escuta contínua, envio automático ao Core ou
  confirmação humana fabricada. Perfis antigos e configuração pública Web intactos.
- Qwen `reuse_voice_prompt=True`: cria um condicionamento em RAM por lote,
  reutilizado nas partes exatas; `False` preserva o caminho anterior. API/assinatura
  incompatível recusa, sem fallback nem cache em disco. A fase privada opcional
  `reference_conditioning` separa esse custo de `generate`. Ainda não é residência
  entre turnos, streaming ou opção habilitada na fala automática Web.
- Adapter textual `ChatCompletionsInferenceProvider` e `LocalChatHttpTransport`:
  HTTP somente loopback numérico selecionado pelo host, endpoint fixo
  `/v1/chat/completions`, nonstream/n=1, resposta textual completa, limites/prazo/
  cancelamento/binding e falha sem conteúdo. Sem DNS, proxy, auth, redirects,
  retries ou ferramentas executadas pelo provedor. Exige Content-Length e peer
  close. `live` indica I/O de socket, não modelo real nem ausência de egress do
  daemon upstream. Nenhum modelo foi instalado/descoberto/ativado.

O adapter ainda não está selecionável pela Web/CLI de produto: essas composições
continuam SIWC/`responses_plan`. A prova de integração usa HTTP real e motor
scripted fixture atravessando Core/ferramenta readonly/síntese/SQLite. Não se
deve anunciar Ollama, LM Studio, OpenRouter, Groq ou OmniRoute conectados.
Consulta somente ao PATH do host não encontrou `ollama`, `lms`, `llama-server`
ou `vllm`. Isso não prova ausência de instalação GUI ou fora do PATH. Nenhum
servidor local foi descoberto/acionado nem modelo baixado para contornar a lacuna.

Revisão documental posterior identificou gap concreto de framing, sem alterar
código congelado: Ollama v0.40.6, commit2476d5ead197abe04629651028f83d48dc75d2b2,
escreve JSON nonstream sem fixar Content-Length. O servidor Go consultado possui
buffer anterior ao chunking de2048bytes; respostas maiores podem usar chunked
mesmo com Connection:close. Por leitura, nosso slice pode recusar resposta
legítima; não é uma observação com daemon real nem garantia da versão Go de um
binário instalado. LM Studio documenta o protocolo, não garante esse framing.
Próximo slice: decoder chunked bounded, limites de linhas/chunks/trailers/body,
prazo/cancelamento e recusa CL+TE ambíguos. Chunked HTTP não é SSE nem streaming
de tokens/áudio. Depois compor perfil e fazer prova de daemon explicitamente
selecionado. Fontes:
[Ollama pinado](https://github.com/ollama/ollama/blob/2476d5ead197abe04629651028f83d48dc75d2b2/middleware/openai.go#L158),
[servidor Go](https://github.com/golang/go/blob/go1.26.0/src/net/http/server.go#L323),
[LM Studio](https://lmstudio.ai/docs/developer/openai-compat/chat-completions).

## Provas reais desta rodada

Uma frase sintética curta (29 caracteres), referência C original360–370s,
Qwen Base0.6B/CUDA/baseline/seed42, timeout120s, concluiu sem chamada ao Core:

| Marco | Tempo observado |
| --- | --- |
| Preparação/supervisão total | 44,14s |
| Importações no worker | 25,437s |
| Carga do modelo | 6,422s |
| Geração incluindo condicionamento | 10,344s |
| WAV concluído | 2,08s de áudio,24kHz |
| Pico Torch CUDA registrado | 2328681472bytes |

Não é comparação com a final anterior2635chars/timeout300s: são workloads
diferentes. Não houve aceite perceptivo ou nova qualidade vocal demonstrada.
As importações/carga dominam esta prova; processo novo por turno paga esse custo
de novo. Um modelo residente pode reduzir essa parcela, mas ainda não foi
implementado/medido. Geração de2,08s em10,344s também não atende tempo real.
Métricas de Torch não incluem todo o uso de VRAM do driver/sistema.

Uma tentativa adicional única da mesma frase/seed/referência, com reuso opt-in,
atingiu120,03s/`timed_out`, zero partes/sem reprodução. O SDK aceitou a API e
concluiu condicionamento, mas não concluiu geração: importações89,281s,
carga16,000s, condicionamento4,625s; geração iniciou em109,953s. Não houve retry.
Não se pode atribuir a diferença ao reuso: inicialização variou fortemente e
ambos foram processos novos com cache/condições do host não controlados. Não é
warm-resident nem A/B conclusivo, ganho de velocidade ou equivalência de WAV.
O sidecar preservou a última fase iniciada sem promover áudio parcial.

Primeira tentativa ASR A/B/BA parou na primeira condição `quality` após90,19s
com `PermissionError`, sem completar a comparação. A GPU foi observada sem
ocupação durante uma consulta; isso não identifica a causa da falha. Não houve
retry automático, conclusão de beam1 ou ganho de velocidade declarado. A consulta
posterior não encontrou processos remanescentes selecionados daquela prova;
isso não autoriza terminar processos alheios ou alterar ACL. O original não foi
modificado e a captura física não foi aberta.

Segunda campanha com TEMP/TMP privado explícito também parou na primeira
condição `quality`, após91,76s. O trace local limitado mostrou WinError32 no
cleanup de `transcribe_bytes`/TemporaryDirectory; o contexto também era
PermissionError. Isso comprova arquivo/diretório ainda aberto naquela fronteira,
não quem mantinha o handle nem a causa inicial da falha. Não se aumentou timeout,
alterou ACL, finalizou processo por nome ou habilitou beam1 para mascarar isso.
Nenhuma das duas campanhas produziu comparação A/B válida.

Prova sintética única sem SDK/áudio, mesmo venv launcher e stdout em arquivo:
nonce/PPID/image/creationTime/handle próprio conferidos; `_stop` retornou em0ms
e confirmou launcher terminado, mas o worker real ainda vivia. Unlink imediato
de um sentinel exclusivo falhou WinError32; o worker saiu16ms depois, sem
TerminateProcess adicional. Comprova uma corrida de encerramento nessa topologia,
não a causa exata do handle no experimento ASR. O pequeno sentinel da prova ficou
retido fora do Git; não se repetiu unlink nem alterou ACL. Contenção de processo
próprio com confirmação de saída é o próximo slice; não se usará sleep arbitrário,
kill por nome ou ignorar cleanup para anunciar correção.

## Testes e histórico de falhas

ASR:14 REDs de feature/8pass iniciais; implementação e regressão130pass.
Primeira bateria de diagnóstico teve falhas de writer e dois erros de nomes
parametrizados enormes no Windows. Repro independente mostrou os.write3bytes
com LF produzindo4bytes CRLF: corrigido com O_BINARY, sem relaxar contagem.
IDs dos mesmos negativos foram limitados. Um oracle supunha dois eventos>500
bytes; corrigido para impor teto exato dos bytes já gravados. Diagnóstico novo:
76pass/1skip (symlink real indisponível no Windows; negativos sintéticos rodam).

Provider:117pass na primeira revisão; revisão independente encontrou requests
forjados/drift in-flight de modelo/configuração e pediu snapshots/fences. A
bateria combinada pós-hardening teve476pass/1skip/1falha apenas do oracle de
bytes descrito acima. Contagens se sobrepõem; não somar. São resultados intermediários.

Bateria integrada após reuso Qwen:658passed/1skip em81,48s, incluindo diagnóstico,
lote legado/novo, ASR, perfil privado, adapter e HTTP/Core real com motor scripted.
Ruff encontrou dois blocos de imports fora de ordem, corrigidos antes do gate.
Regressão JavaScript completa:1282passed/zero falhas, sem abrir microfone.
Pré-gate quick passou codificação/documentos/Ruff. Standard final Windows exit0:
11035passed/122skipped/zero falhas/errors,11157casos;129 hashes de arquivos de
código/testes/configuração modificados na árvore preservados antes/depois.
O gate qualifica código local, não latência, modelo real ou qualidade vocal.

Prévia anterior pausada para provas de recursos foi restaurada em
http://127.0.0.1:55203/, com novo runtime isolado, generativo desligado e perfil
privado antigo inalterado. QA no navegador integrado via CUA/Playwright624x668:
URL/título corretos, DOM significativo/sem overlay, console sem erros/avisos,
seção WAV abriu/fechou sem escolher arquivo. Captura JPEG fora do Git. Primeiro
seletor role=button não encontrou summary (generic no DOM); observação renovada e
texto exato funcionaram, sem alterar código. Não se automatizou pareamento,
permissão de mic, captura/reprodução ou novo pedido ao Core. A sessão não
pareada/aviso de atenção são esperados; isso não é aceite de conversa.
Outros viewports e microfone físico não foram requalificados nesta rodada.

## Próximos cortes com evidência

1. Confirmar encerramento do worker real por handle próprio antes de limpar
   temporários; rendezvous privado precisa binding/timeout/cancel/testes Windows.
   Sem confirmação, manter quarentena/artefatos, não matar PID incerto. A Web já
   indisponibiliza voz após falha SDK incerta. Só depois repetir ASR A/B.
2. Qualificar residência de modelos e arbitragem de recursos, sem supor que ASR,
   TTS e LLM cabem juntos na GPU4GiB. Medir cold-process e warm-model separadamente;
   reuso Qwen passou condicionamento real, mas não concluiu WAV/ganho entre partes.
3. Entregar partes ordenadas da final já aceita e projetar resposta oral curta
   no Core. Não cortar/resumir a final no browser nem falar raciocínio provisório.
4. Endpointing/VAD, hands-free/autosubmit, consentimento generativo e interrupção
   de áudio são contratos separados; cancelar áudio não desfaz Core/memória.
5. Em paralelo, adicionar decoding chunked HTTP limitado, compor perfil explícito
   do adapter local e provar servidor/modelo reais; qualificar framing e egress
   upstream antes de anunciar suporte. O slice atual não é Ollama plug-and-play.

Estudo: [conversa fluida](fluid-conversation-options-2026-10-18.md).
Contexto anterior: [ponte Web](local-web-voice-conversation.md).
Rollback: diagnóstico desligado, ASR quality, nenhum adapter local selecionado;
sem migração de banco ou permissões ampliadas. Sem OAuth, instalação, upload de
voz, API paga, commit, push ou merge nesta rodada.
