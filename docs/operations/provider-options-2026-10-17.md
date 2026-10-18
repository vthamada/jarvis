# Opcoes de provedores de IA: auditoria e proposta de integracao

Atualizacao18/10: adapter textual ChatCompletions e transporte HTTP loopback
foram implementados em isolamento e atravessaram Core com motor scripted.
Nao estao selecionaveis nos perfis Web/CLI nem foram provados com modelo real.
O levantamento abaixo e historico17/10; ver
[recorte atual e limites](voice-latency-diagnostics-2026-10-18.md).

Data de consulta: 2026-10-17. Escopo: leitura do JARVIS e documentacao/codigo
primarios externos. Nenhuma chamada de inferencia/catalogo autenticado, login,
instalacao, download de modelo, benchmark ou alteracao de runtime foi executada
nesta frente. Este documento nao promove nenhuma capability.

## Conclusao pratica

Podemos oferecer varios motores sem trocar o cerebro do JARVIS. A costura correta
ja existe em `ModelInferencePort`: o provedor produz dados; Core continua dono de
governanca, ferramentas, memoria e resposta final. Falta um caminho operacional
multi-provider: hoje o perfil Web/CLI generativo usa somente o adapter SIWC
`responses_plan`, alem das fixtures de teste.

Recomendacao: preservar OAuth atual e adicionar um adapter textual Chat
Completions independente, com perfis explicitos. Primeiro provar Ollama local;
depois OpenRouter e Groq por opt-in. OmniRoute deve entrar como gateway opcional
isolado, nao como dependencia central, memoria ou executor de ferramentas.
LM Studio e llama.cpp podem usar a mesma familia de protocolo. vLLM fica para
servidor Linux/GPU adequado, nao como primeiro runtime deste notebook Windows.

## O que existe de fato no repositorio

| Costura | Estado observado e consequencia |
| --- | --- |
| `shared/model_inference.py` | `InferenceRequest`, `InferenceResult` e `ModelInferencePort` neutros; deadlines, cancelamento, limites, provider/model binding, modos `fixture`, `injected_transport`, `live`. Historico textual user/assistant; ainda nao possui contrato nativo `tool_calls`/role tool. |
| `services/inference-service/src/inference_service/providers.py` | `FakeInferenceProvider` e `ResponsesPlanInferenceProvider`. O segundo serializa Responses e valida stream estritamente; nao e um adapter generico Chat Completions. |
| `services/inference-service/src/inference_service/http_transport.py` | `PlanResponsesHttpsTransport` fixa `api.openai.com` e `/v1/responses`, OAuth/scope/expiry, sem proxy/redirect/retry/fallback pago. Nao transformar esse transporte em `base_url` arbitrario. |
| `services/inference-service/src/inference_service/session_inference_port.py` | `SessionInferencePort` liga modelo/catalogo/sessao SIWC e distingue transporte real de injetado. Nao e provedor API-key universal. |
| `apps/jarvis_api/generative_profile.py` | `GenerativeProfile` e `_LazyPort` fixam `responses_plan`; factory padrao carrega perfil SIWC. Adicionar perfis novos e composicao explicita, nao forjar o provider id existente. |
| `apps/jarvis_console/generative_analysis_cli.py` e `model_tool_loop_cli.py` | Caminhos operacionais atuais tambem restringem `responses_plan`. Factories injetadas sao seams de teste, nao prova de integracao real. |
| `shared/model_tool_loop.py` | Loop pede JSON textual `tool_call`/`final`; Core autoriza e executa `read_local_report`, valida recursos/citacoes/binding. Pode ser reutilizado por outro port sem delegar execucao ao provedor. |
| `services/orchestrator-service/src/orchestrator_service/model_tool_loop.py` | `ModelToolLoopConfig` ja recebe port, modelo e provider/evidence esperados. Ponto de composicao, nao lugar para guardar chaves ou implementar HTTP. |
| `engines/synthesis-engine/src/synthesis_engine/generative_analysis.py` | Analise generativa subordinada, com validacao de esquema/citacoes e protecoes de egress; saida continua dado nao verificado. |

Nao se encontrou adapter operacional para OpenRouter, Groq, Ollama ou OmniRoute.
Este levantamento nao reexecutou testes nem valida o estado da conta OAuth.

## Endpoints, autenticacao e diferencas

URLs abaixo sao referencias de configuracao, nao endpoints contatados por este
estudo. Catalogo nao equivale a conta autorizada, inferencia disponivel ou modelo
capaz de cumprir o contrato do JARVIS.

| Opcao | Raiz e descoberta | Autenticacao / natureza |
| --- | --- | --- |
| OpenRouter | `https://openrouter.ai/api/v1`; `GET /models`, `POST /chat/completions` | Bearer API key propria; agregador cloud, cobranca/limites proprios. [Autenticacao](https://openrouter.ai/docs/api_reference/authentication), [catalogo](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties). |
| Groq | `https://api.groq.com/openai/v1`; `GET /models`, `POST /chat/completions`, `POST /responses` | Bearer `GROQ_API_KEY`; inferencia cloud em infraestrutura Groq. [Compatibilidade](https://console.groq.com/docs/openai), [API](https://console.groq.com/docs/api-reference). |
| Ollama local | `http://127.0.0.1:11434/v1`; `GET /models`, `POST /chat/completions`, `POST /responses` | API local sem autenticacao por padrao; modelo local precisa estar baixado. [Compatibilidade](https://docs.ollama.com/api/openai-compatibility), [autenticacao](https://docs.ollama.com/api/authentication). |
| OmniRoute | `http://127.0.0.1:20128/v1`; `GET /models`, `POST /chat/completions`, `POST /responses` | Bearer da instancia OmniRoute, separado das credenciais upstream; gateway self-hosted, nao fornecedor de pesos. [Contrato](https://github.com/diegosouzapw/OmniRoute/blob/release/v3.8.52/docs/reference/OPENAI_COMPATIBILITY.md). |
| LM Studio | `http://127.0.0.1:1234/v1`; `GET /models`, `POST /chat/completions`, `POST /responses` | Sem auth por padrao; API token pode ser exigido nas configuracoes. [Endpoints](https://lmstudio.ai/docs/developer/openai-compat), [auth](https://lmstudio.ai/docs/developer/core/authentication). |
| llama.cpp | Raiz definida pelo operador, normalmente `http://127.0.0.1:8080/v1`; `/models`, `/chat/completions` | `llama-server`, pesos GGUF; `--api-key`/`--api-key-file` opcionais. [Servidor oficial](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md). |
| vLLM | Raiz definida pelo operador, tipicamente `http://127.0.0.1:8000/v1`; `/models`, `/chat/completions` | Servidor proprio; chave via `--api-key`; nao e servico cloud necessariamente. [Serving](https://docs.vllm.ai/en/latest/serving/online_serving/). |

### OpenRouter: amplitude com politica de rota explicita

O catalogo informa modalidades, contexto, precos e parametros suportados.
Nao fixar numero de modelos ou escolher o modelo pelo nome comercial sem
consultar o catalogo do perfil. Ferramentas dependem do modelo e endpoint.
[Catalogo oficial](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties).

Para um piloto auditavel, selecionar modelo/provider exatos e usar
`provider.allow_fallbacks=false`, `require_parameters=true`,
`data_collection="deny"` e `zdr=true` quando exigidos. Sem
`require_parameters`, parametros podem ser ignorados; a rota padrao pode aceitar
providers que retêm dados. Falta de endpoint compativel deve falhar, nao baixar a
politica silenciosamente. Fallback de providers e fallback de modelos sao
decisoes diferentes. [Roteamento](https://openrouter.ai/docs/guides/routing/provider-selection).

ZDR filtra inferencia, nao necessariamente plugins e backends de ferramentas.
Nao habilitar server tools/MCP externos neste slice. Mesmo com ZDR o prompt
trafega para cloud; nao chamar isso de processamento local.
[Limites de ZDR](https://openrouter.ai/docs/guides/features/zdr).

### Groq: candidato de baixa latencia, nao o Grok

Groq e infraestrutura de inferencia, nao o modelo Grok/xAI. Suporta funcao local
proposta pelo modelo, remote MCP e ferramentas built-in, com capacidades por
modelo. Para JARVIS, usar apenas propostas de ferramentas executadas pelo Core;
nao ativar o loop server-side que executa pesquisa/codigo fora dele.
[Tool use](https://console.groq.com/docs/tool-use/overview).

Compatibilidade nao e total: alguns campos OpenAI sao recusados e `n`, quando
fornecido, deve ser 1. Latencia menor no nosso fluxo ainda exige medicao; nao
extrapolar tokens/s publicitarios para tempo de conversa.
[Compatibilidade](https://console.groq.com/docs/openai).

Por padrao, inferencia nao e retida, mas a politica documenta excecoes para
confiabilidade/abuso e features persistentes. ZDR pode ser habilitado; confirmar
controles da organizacao antes de enviar fontes privadas.
[Politica de dados](https://console.groq.com/docs/your-data).

### Ollama: distinguir local, proxy local para cloud e cloud direta

Ha tres casos diferentes: pesos executados localmente; servidor local autenticado
encaminhando modelo cloud; API direta `https://ollama.com/v1` com chave.
Loopback sozinho nao comprova privacidade local.
[Autenticacao e cloud](https://docs.ollama.com/api/authentication).

Para perfil estritamente local, desabilitar cloud com `OLLAMA_NO_CLOUD=1` ou
`disable_ollama_cloud`, selecionar pesos locais e provar ausencia de egress.
Nao aplicar essa mudanca automaticamente na instalacao do usuario.
[FAQ local-only](https://docs.ollama.com/faq).

Chat Completions suporta streaming, JSON e tools; a matriz atual do codigo marca
`tool_choice` como nao suportado. Responses tambem existe, mas e stateless, sem
`previous_response_id`/`conversation`. Logo nao basta trocar URL do parser SIWC.
[Documentacao de protocolo](https://docs.ollama.com/api/openai-compatibility),
[matriz legivel de campos](https://github.com/ollama/ollama/blob/main/docs/api/openai-compatibility.mdx).

O ambiente documentado em `parallel-wave-local-tts-and-empirical.md` tem RTX3050
Laptop/4GiB e RAM16GiB. Comecar por um modelo pequeno quantizado e contexto
limitado; tamanho dos pesos nao inclui KV cache/runtime nem garante qualidade.
LLM, ASR e TTS podem disputar a mesma VRAM. Provar sequencialmente e medir
residencia/descarregamento antes de prometer conversa simultanea em tempo real.

### OmniRoute: opcional, com traducao e automacao sob controle

Projeto identificado: [diegosouzapw/OmniRoute](https://github.com/diegosouzapw/OmniRoute),
gateway MIT; nao confundir com pesquisa academica homonima. Sua documentacao
mostra roteamento/combinations, traducao de protocolos e quotas. Tier gratuito
depende das contas/termos upstream; nao e credito universal concedido pelo app.

O contrato OpenAI-compatible depende do provider selecionado; o cliente continua
responsavel por executar tools e enviar resultados. `/v1/realtime` nao esta
implementado segundo a matriz consultada. Nao promove conversa duplex por si.
[Compatibilidade](https://github.com/diegosouzapw/OmniRoute/blob/release/v3.8.52/docs/reference/OPENAI_COMPATIBILITY.md).

Para experimento inicial: modelo/provider fixo, sem combo/`auto`, sem fallback,
sem injecao de memoria/skills, sem cache semantico e sem compressao. A API
documenta `X-OmniRoute-No-Cache`, `x-omniroute-no-memory` e
`x-omniroute-compression: off`; verificar configuracao efetiva e trace de rota.
Pin de conta nao e garantia permanente: documentacao descreve liberacao em
cooldown/quota nas chamadas posteriores. [API e limites de pinning](https://github.com/diegosouzapw/OmniRoute/blob/release/v3.8.52/docs/reference/API_REFERENCE.md).

Esses controles preservam citacoes exatas e evitam duas memorias concorrentes.
Ainda exigem prova: headers declarados nao demonstram que todo pipeline
respeitou-os. Nao importar tokens/cookies do Codex, perfis SIWC ou artificios de
contorno de restricoes para esse gateway. Auth upstream deve ser independente,
licitamente suportada e explicitamente configurada pelo operador.

As referencias OmniRoute usam branch movel `release/v3.8.52`, nao um commit
imutavel. Antes de executar experimento, fixar commit/release e revisar dependencias.

### Outros runtimes locais

LM Studio facilita operacao visual e oferece Responses/Chat Completions; tools
dependem do modelo/template. Evitar suas funcoes MCP externas neste slice e usar
protocolo sem memoria concorrente. [APIs e capacidades](https://lmstudio.ai/docs/developer/rest).

llama.cpp e alternativa mais enxuta para GGUF, com controle de offload/contexto.
Function calling depende de Jinja/template apropriado. Compativel no protocolo
nao significa que todo modelo produza chamadas corretas.
[Servidor e function calling](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

vLLM prioriza serving/batching e suporta tool calling com parser/template e flags
apropriados. Nao suporta Windows nativamente; documenta Linux/WSL. Avaliar quando
houver servidor/GPU com margem, nao impor infraestrutura nova para o primeiro
teste de modelos locais. [Tools](https://docs.vllm.ai/en/latest/features/tool_calling/),
[plataformas](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/).

## Slices minimos propostos, ainda nao implementados

Atualizacao18/10: adapter textual e transporte local com CL/chunked ja possuem
implementacao; composicao CLI explicita pelo Core esta em validacao nesta
continuidade. Perfis multi-provider, cloud e composicao Web continuam pendentes.
Ver [escopo e evidencia por camada](local-model-cli-and-asr-lifecycle-2026-10-18.md).
Nao interpretar os itens abaixo, propostos no estudo original, como aceite de
modelo/servidor instalado ou de privacidade de pesos locais.

1. **Adapter textual independente:** `ChatCompletionsInferenceProvider` e
   transporte limitado; converter instructions para mensagem system e historico
   para messages; somente texto, `n=1`, sem built-in tools, sem side effects.
   Comecar non-streaming limitado; streaming e melhoria separada. Recusar saida
   tool-only em vez de executa-la implicitamente.
2. **Perfis privados:** provider/protocolo/endpoint/modelo/auth_ref/capabilities,
   egress, timeout e budget explicitos. Chaves fora do front-end, Git e OneDrive;
   nao reaproveitar o formato SIWC para esconder semantica diferente.
3. **Endpoint policy:** origins HTTPS permitidas para cloud; HTTP somente
   loopback numerico explicitamente autorizado; sem URL vinda de prompt/modelo,
   redirects ou proxies implicitos. Validar IPv4/IPv6, credenciais em URL,
   path/query e DNS/SSRF; servico local nao pode virar proxy para rede privada.
4. **Composicao Web/CLI:** selecionar perfil sem chamar conta no constructor;
   manter elegibilidade/consentimento antes do I/O. Explicitar provedor/modelo,
   local/cloud, estado e erro. Falha nao troca para API paga, outra conta ou
   outro modelo silenciosamente. UI nao pode editar origem ou receber segredo.
5. **Tool loop existente:** reaproveitar propostas JSON textuais e a autorizacao
   Core. Native tool calls exigem futuro contrato compartilhado versionado e
   validacao propria; nao expandir roles neste primeiro slice por conveniencia.
6. **Roteamento opcional posterior:** medir qualidade/latencia/custo primeiro;
   depois politica Core-owned de fallback com consentimento, teto global de
   chamadas, rastreio de rota efetiva e rollback. Gateway nao decide autoridade.

Nao e necessario adicionar SDK/roteador central novo para esse recorte. O mesmo
adapter de protocolo pode ter politicas pequenas por provider, sem fingir que
todos suportam os mesmos parametros ou esquemas.

## Evidencia exigida antes de chamar integrado

| Requisito | Prova minima |
| --- | --- |
| Conformidade do port | Fixtures independentes positivas/negativas: binding, texto vazio/parcial, modelo divergente, JSON/UTF8 malformado, timeout/cancelamento, usage, limites, falha sem conteudo. |
| Transporte seguro | Integracao HTTP real local e HTTPS controlado; origem/redirect/proxy/auth/header/SSRF, resposta gigante/interrompida, cancelamento e cleanup. Sem segredo nos erros/logs/DOM. |
| Ferramentas soberanas | Mesmo corpus de propostas validas/invalidas pelo Core; recusas, recurso nao selecionado, citacao falsa, repeticao, revalidacao de consentimento e limites. |
| Modelo real | Piloto explicitamente autorizado por perfil/modelo e teto; tarefa sintetica, backend efetivo registrado, primeira falha para, sem retry/refresh/fallback automatico. |
| Utilidade | Comparar corpus existente de missoes com mesmo input/condicoes: sucesso verificavel, recusas corretas, citacoes, p50/p95, custo/tokens e falhas. Nao comparar apenas estilo da resposta. |
| Localidade e voz | Egress bloqueado/observado para perfil local; RAM/VRAM, contexto, cold/warm start e contencao ASR/LLM/TTS medidos. Medir tempo ate primeiro audio e fim do turno, nao somente tokens/s. |
| Fechamento | Testes slice + ponta a ponta afetado, observabilidade sem conteudo sensivel, documentacao/HANDOFF e gate standard pelo coordenador. |

Resultado desta rodada: arquitetura e opcoes verificadas por leitura, integracao
real e desempenho **nao verificados**. Nenhuma capability nova foi habilitada.
