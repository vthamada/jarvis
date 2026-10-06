# Inference service: WP-CORE-01 isolated slice

Este pacote implementa o port `shared.model_inference.ModelInferencePort`, sem
SDK ou descoberta de tokens/ambiente. MB221 adiciona HTTPS/SSE explicito opt-in;
MB222 implementa OAuth local/catalogo/refresh com extra opcional PyJWT[crypto].
Sem ativacao default; nenhum login/request de conta ou modelo real foi testado.
Nao concede autoridade nem despacha ferramentas: o resultado e dado subordinado
ao Core, que continua dono da memoria, governanca e sintese final.

## APIs

- `FakeInferenceProvider(text=...)`: resposta deterministica com evidencia
  `fixture`; nunca ecoa automaticamente o prompt nem comprova um modelo real.
- `ResponsesPlanInferenceProvider(transport, clock=..., telemetry=...)`:
  payload textual Responses com historico explicito e parser de stream com
  evidencia `injected_transport`, nunca `live`.
- Ambos: `infer(request, cancellation=Event()) -> InferenceResult`.
- `ResponsesTransport`: callable injetado `(payload, *, timeout_seconds,
  cancellation) -> Iterable[dict]`.
- `PlanResponsesHttpsTransport`: HTTPS publico fixo, OAuth bearer em memoria,
  scope/expiry declarados e autorizacao explicita; certificados verificados,
  sem proxy/redirect/retry/fallback pago. SSE limitado e erros sem conteudo.

O transporte precisa respeitar deadline/cancelamento nas suas operacoes
bloqueantes. O adapter verifica antes/depois de chamadas e yields, fecha o
iterator quando possivel e limita eventos/bytes/texto. Nao interrompe Python
arbitrario bloqueado e nao deve ser tratado como sandbox de transporte hostil.

Texto so e entregue apos `response.completed` valido e termino limpo do stream.
Falha, stream interrompido, timeout, cancelamento, identidade/modelo divergentes,
usage malformado, output nao textual ou eventos apos conclusao descartam texto.
O parser inicial suporta um bloco visivel de texto: partes/done intermediarios
devem concordar com deltas e output final; delta depois de done e rejeitado.
Eventos de mensagem devem indicar assistant; summaries precisam de campos
textuais tipados, embora seu conteudo nao seja publicado. Streams multipart
complexos exigem slice proprio, em vez de aceitar ambiguidades silenciosamente.
Ha limites locais de output; nao se envia `max_output_tokens` neste fluxo.
Telemetry opcional inclui apenas status/codigo normalizado/contagens/evidencia:
nenhum prompt, texto, modelo, ID escolhido pelo usuario, erro livre ou segredo.

## Evidencia, testes e limites

```powershell
.venv/Scripts/python.exe -m pytest services/inference-service/tests
```

O E2E offline cobre request -> payload -> transporte injetado -> deltas ->
conclusao, incluindo consumo, erros finais apos texto parcial, cancelamento,
limites e redaction. Isso nao e E2E de OAuth/modelo real nem promocao integrada
ao Core de producao. Conta/elegibilidade e consentimento reais, revogacao remota
e streaming UI continuam pendentes. MB222 cobre conta/catalogo/refresh/storage
no recorte local testado, nao homologacao externa. MB221 liga
framing injetado a sintese extrativa/Core local nos testes, sem modelo real.
Modelos sao slugs explicitamente selecionados; nao ha alias fixo
nem fallback pago. Desativacao: remover a injecao do provider, sem alterar stores.

## Formato revalidado em 2026-10-05

O fluxo SIWC exige `store:false`, `stream:true`, input array, contexto completo
e sucesso somente apos conclusao. O adapter envia somente model/input/store/
stream e instructions opcionais; nao envia parametros unsupported ou tools.

- [Models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [Preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)

Runbook/limites/desativacao:
[MB221](../../docs/operations/parallel-wave-transport-transcript-and-job-inspection.md).
Timeout/cancelamento cooperativo nao e kill de DNS ou transporte hostil.

OAuth/conta isolada: SiwcAuthorizationFlow, SiwcLoopbackListener,
verify_id_token, SiwcHttpsClient, SiwcCredentialStore e SiwcSession.
Tokens/provider nunca autenticam operador nem concedem autoridade ao Core.
CLI standalone opt-in: chatgpt-account. Detalhes, instalacao opcional, threat
model, incidentes e limites: [MB222](../../docs/operations/siwc-local-account-and-catalog.md).
