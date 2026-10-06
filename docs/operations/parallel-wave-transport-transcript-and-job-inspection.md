# MB221: transporte, revisao de transcricao e inspecao de jobs

Data: 2026-10-05. Tres workers disjuntos; coordenador integra/revisa e roda gate.
Estado: MB221 done no escopo local; gate standard global Windows passou.
Nenhuma capability externa, API mutante ou autonomia nova promovida.

## Inferencia SIWC opt-in

`inference_service.http_transport.PlanResponsesHttpsTransport` implementa o
callable existente com biblioteca padrao, sem nova dependencia. Construcao nao
abre rede. OAuth bearer somente em memoria, fornecido pela composicao confiavel
com `authorized=True`, `expires_at` UTC epoch e
`granted_scopes=("chatgpt.tokens.use.direct",)`. Scope/expiry sao declaracoes,
nao prova de OAuth. Login, PKCE/state/nonce, ID token, catalogo, refresh e
armazenamento seguro continuam pendentes. Sem leitura de tokens de apps,
arquivos ou ambiente, chave API ou fallback pago.

HTTPS fixo `api.openai.com:443/v1/responses`, certificado/hostname verificados,
sem proxy/redirect/retry/endpoint configuravel. Payload model/input/store:false/
stream:true/instructions opcional, modelo escolhido explicitamente. SSE UTF8
estrito limitado por bytes/linhas/eventos; JSON duplicado/nonfinite/frame
truncado/sentinel ambiguo recusados. Provider publica somente completion
semantica + EOF limpo, nunca texto parcial. Erros/telemetria content-free;
recursos fechados mesmo em falha/cancelamento. Deadline e cancelamento
cooperativos, socket usa tempo restante; nao garantem kill de DNS ou I/O
arbitrario. Fabrica injetada nao prova rede/TLS real. Metadados transport:
injected_transport/fixed_https_transport; provider conserva injected_transport,
nunca presume live. E2E doubles -> sintese extrativa -> Core local nao promove
prosa livre ou dispatch de tools.

A skill OpenAI Docs orientou endpoint publico e ausencia de fallback pago.
Fontes oficiais revalidadas nesta rodada:

- [Models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [Preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
- [Sign-in](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)

## Transcricao revisada -> Core

`apps.jarvis_voice.transcript_review.LocalTranscriptReview` recebe documento
ASR via composicao confiavel, sem abrir WAV/modelo/microfone/rede. Exige
review_required true, Portuguese, duracao ate900s/1000segmentos validos.
Candidato ate4000 caracteres, textos exatos unidos por newline sem truncamento.
Transcricao longa exige recorte previo explicito. SHA256 de fonte e binding
declarado, nao prova speaker/autenticacao/execucao ASR. Sem envio automatico.

Sequencia programatica:

1. construir review com identidade voice/single_surface/scope vazio;
2. `consent(identity, granted=True)` e `propose(document, identity=identity,
   source_sha256=...)` retornam ticket com deadline ate120s;
3. `review(ticket, identity=identity)` exibe candidato; `edit(ticket,
   reviewed_text, identity=identity)` preserva revisao exata;
4. `confirm(ticket, identity=identity, candidate_hash=view.candidate_hash,
   revision=view.revision)` retorna VoiceRequest sem chamar Core;
5. `ReviewedVoiceCorePort(core, identity, transcript_review=review).interact(request)`
   consome `take_request` atomicamente antes de Core. Mesmo objeto/geracao/
   consentimento/prazo; replay/copia/revogacao e downgrade para fixture recusados.

Port sem review so aceita reviewed_voice_fixture, nunca request local por default.
Lock serializa consumo/revogacao. Pos-handoff nao e possivel unsend/desfazer
memoria; falha Core nao restaura ticket nem retry. Revisao nao confirma acao:
VOICE/TEXT assist_only sem receipt/grant/adapter_request. Governanca/memoria/
final soberanos. Eventos/snapshot/repr bridge sem texto/digest/refs; view e
divulgacao local explicita, nao telemetria. Nao logar repr do VoiceRequest legado.
Nao conecta UI/hardware/TTS nem melhora perceptualmente clonagem vocal.

## Jobs existentes sem escrita

Comando standalone (45 comandos no registry/completions):

```powershell
.venv/Scripts/python.exe -m apps.jarvis_console --format json job-inspect `
  --job-db C:\private\jobs.db --actor-ref actor-one --session-ref session-one `
  --job-id job-one
```

Repetir --job-id ate32 IDs exatos; --include-refs e divulgacao, nao autenticacao.
Default: jarvis-job-inspection-v1, authority none, status/version/fencing/
tentativas/evidence/leasepresent, sem IDs/conteudo. Redactor detecta referencia
sensivel => retirar referencias inteiras, nunca alterar bindings. Erros fixos.

SQLite mode=ro/query_only/trusted_schema off, transacao unica e limites/progress
budget. Arquivo absoluto existente regular singlelink ate128MiB, parents sem
symlink/reparse, sem UNC/traversal/ADS; header DELETE e sem wal/shm/journal.
Schema1/linhas/fingerprint validados. Scope actor/session exato para TODOS IDs
ou nenhuma saida. Nunca instancia store writable, cria/migra/reconcilia lease/
claim/termina job/worker/Core. Claim expirada permanece visivel sem replay.
Preflight trusted-host/quiescent, nao FD sandbox contra atacante mesmo UID.

## Validacao e rollback

Baterias locais/adversariais, E2E Core e subprocess CLI sem request OpenAI,
modelo, hardware/audio ou banco humano. Dois testes de symlink indisponiveis
neste Windows por privilegio de criacao; nao e nova prova fisica Linux/TLS.
Gate standard global Windows aprovado: encoding/document guardrails/Ruff e
suite pytest completa. Isto nao e gate release Linux novo ou promocao externa.

Resultado focado:472 passed/2 skips em29.43s, incluindo128 transport,74 review,
49 job readonly,7 failure mappings,14 E2E HTTPS-injetado/Core,12 E2E review/Core,
11 E2E CLI jobs e regressoes dos providers/stores/console/assets/voice fixture.
Dois skips exclusivos de criacao de symlink no host. Ruff global e diff check
passaram. Revisao cruzada identificou downgrade do modo review para fixture;
corrigido com refusals em port opt-in e corpus revoke/replay/failure. Erros de
composicao CLI e CAS das fixtures corrigidos antes da bateria final.

Rollback: nao injetar transport/review; retirar job-inspect da superficie.
Default Core nativo e stores intactos. MB218/219 done local Linux/SQLite e
no_go_for_public_mutating_api permanecem inalterados.
