# MB231 - conversa Web de analise com Core local

Estado 2026-10-06: MB231 done local; baterias focadas, browser final e gate
standard global Windows aprovados. Nao e API publica mutante, identidade humana,
modelo generativo, qualidade de resposta aprovada ou sistema completo.

## Executar explicitamente

Na raiz do projeto:

```powershell
.venv/Scripts/python.exe -m apps.jarvis_api --authorized --port 0
```

O terminal mostra URL127.0.0.1 com porta efemera e codigo de pareamento unico.
Abrir essa URL, digitar codigo em ate120s, enviar pergunta textual. Sessao900s,
um pareamento por instancia, oito tentativas maximas; apos revogacao/expiry,
parar e iniciar outra instancia. Nao usar localhost como alias. Sem codigo em
URL, parametros de conta/credencial/runtime humano ou instalacao de servico.
Ctrl+C encerra instancia propria, nao desfaz registros canonicos.

Cada inicio cria `.jarvis_runtime/web-live/<id-aleatorio>` fresco, preservado
no encerramento. Nunca abre/sobrescreve stores existentes automaticamente.
Pergunta/final podem permanecer em Memory/events nesse runtime; limpar UI ou
revogar sessao nao promete apagar dados em disco. Nao compartilhar o codigo,
cookies ou banco quando houver dados privados; nao ha apagamento automatico.

## Fronteira e soberania

Aplicacao separada do servidor `apps.jarvis_web.serve` de demonstracao/offline.
Loopback IPv4 exclusivo, Host/Origin exatos, CSRF e cookie HttpOnly/SameSiteStrict.
HTTP local nao autentica pessoa/OS nem protege contra processo local hostil que
ja possui acesso ao terminal, browser ou arquivos. Cookie HTTP sem Secure nao
equivale a TLS/multiusuario; nao expor por proxy/LAN/publico. Sem CORS amplo,
storage browser, uploads, mic, aprovacao de acao ou egress de modelos/ferramentas.

Core nativo decide e sintetiza, escreve Memory e eventos, depois serviço verifica
turno e binding de request/sessao/sujeito/eventos antes de entregar final exata.
Principal, user e ticket sao emitidos pelo servidor; JSON cliente nao os escolhe.
assist_only/maxassist_only, scope vazio; operacional.execute falha fechado antes
de corpo/efeito nesta composicao. Modelos desativados e observability sem adapter
externo, mesmo com DATABASE_URL/tracing de ambiente. Nenhum engine/governanca
central alterado; DEFER/BLOCK nao viram ALLOW por conveniencia da interface.

Limites: corpo32768 bytes UTF-8 JSON estrito (duplicatas/extras recusados),
query4000/final131072 codepoints; controles Unicode/surrogates recusados salvo
CR/LF/tab. HTTP no keepalive, oito requests concorrentes, leitura5s total/socket2s.
Erros antesbody descartam bytes opacos bounded40KiB/50ms para evitar RST Windows;
nao interpretam dados nem chegam ao Core. Deadline/autorizacao cercam admissao e
entrega; nao revogam bytes ja entregues ou executam interrupt arbitrario do Core.

## Tickets, falhas e retomada

Um pedido Core ativo globalmente, sem fila ilimitada;64 tickets por instancia,
prazo120s de ticket/resultados. POST nunca e repetido automaticamente. Replay
recusado; GET recupera resultado existente. Perda de resposta/espera30s conserva
ticket no controller para **Consultar resultado**. **Parar de aguardar** so aborta
espera browser, nao Core/commit/Memory. Nao tratar disconnect como rollback.

Falha depois de inicio/readback retorna `analysis_outcome_unknown`, result null:
pode haver commit; nao reexecutar para fabricar certeza. Ticket nao iniciado
tambem nao e reenviado por recuperacao; consultar/aguardar expiry antes de novo
pedido. Servico fechado/revogado/expired nunca entrega resultado antigo.

Reload da mesma instancia pode recuperar sessao por cookie e ultimo ticket
ainda valido, depois consulta explicita. Tickets/auth sao efemeros em memoria,
nao ledger duravel: restart do processo cria nova sessao/runtime, nao retoma ticket
antigo. Memory permanece preservada; inspecao offline existente e separada.

## Contrato local

`jarvis-local-session-v1`: authenticated=true, session_ref serverminted,
csrf_token, expires_in_seconds e last_ticket. Auth e posse da sessao local,
nao permissao para ferramenta.

`jarvis-local-analysis-v1`: status issued/running/completed/failed, ticket,
error_code e result. Completed inclui query/response_text exatos, intent,
governance_decision, memory_record_ref, timestamp UTC, evidence_mode=core_local,
generative_status=disabled e authority=none. Hash/ref nao e assinatura.

API allowlisted: POST pair/tickets/analysis/disconnect; GET session/results.
Clientheader obrigatorio, CSRF em requests protegidas (GETsession bootstrap
somente cookie/clientheader). API HEAD/querystrings/chunked/headers duplicados
recusados. Frontend valida schema/ticket/contexto/contagens, bytes/MIME/UTF-8/JSON,
usa textContent e invalida callbacks obsoletos em authfalha/pagehide/disconnect.

## Validacao, limites e rollback

Tres workers disjuntos auth/HTTP, Core/readback e cliente/controller; coordenador
startup, E2E HTTP/Core/restart, browser e gates.13 startup,191 auth/HTTP,
86 Core/service,12 HTTP/Core novos aprovados;136 Node novos/689 Web completos
aprovados, sem skips nas baterias. Gate oficial integra Web Node via pytest.
Standard global completo aprovado com8092 casos coletados; skips de plataforma
e opt-in existentes nao equivalem a nova evidencia Linux ou de modelo real.
Depois da sincronizacao de status/readiness:112 testes focados e gate quick
aprovados; runtime/testes funcionais permaneceram congelados.
Prova nova e Windows/SQLite/loopback, nao Linux/TLS/modelo/usuario/qualidade.
Recusa por sandbox10013 resolvida somente por execucao escalada de testes locais.

Browser real em instancia propria congelada: pareamento, PT, final2635 codepoints
igual ao exportador readonly da memoria/eventos; reload e GET recuperam ticket.
Interrupcao GET simulada por Playwright recuperou final com um unico POST;
nao e campanha de falhas de rede em producao. Mobile390x844 sem overflow horizontal,
scroll interno ou botoes abaixo44px; reload pareado sem erros de console.
401 inicial sem pareamento e apos disconnect sao recusas esperadas; ERR_FAILED
foi provocado no teste. Disconnect limpa DOM e recusa resultado antigo401.
Codigo do primeiro arranque expirou durante a preparacao: recusado corretamente,
sem ampliar prazo. Instancias proprias encerradas, stores preservados/ignorados.

Desativar: parar app opt-in/revogar sessao; manter fixture/offline e dados
canonicos para inspecao. Nao relaxar CSP da fixture, apagar runtime humano,
dispensar readback ou converter ticket em grant. Proximo recorte deve aproximar
utilidade da resposta/modelo, mantendo aceite de conta real separado e explicito.
MB232 ready: generacao opt-in usando seam MB229, default off, v1 preservada e
v2 explicita; configuracao no host e consentimento por ticket. Ownership e
aceites na fila unica `docs/implementation/execution-backlog.md`.
