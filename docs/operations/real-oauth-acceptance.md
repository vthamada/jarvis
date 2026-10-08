# MB236 - homologacao controlada OAuth

Estado vigente 2026-10-06: MB236 blocked para aceite real; diagnostico local
validado, nova tentativa unica recusou formato/encoding da resposta HTTP200.
O restante deste documento registra o historico, nao autoriza outro envio.

## Rodada de diagnostico e nova tentativa autorizada

Operador autorizou uma nova tentativa unica apos diagnostico seguro e refresh
somente da mesma conta se expirada. Diagnostico host opt-in implementado:
fase/status/codigo allowlisted e status HTTP int; nenhum corpo, header bruto,
identidade, token, URL, pergunta ou resposta registrado pelo observador.
Contratos Web/Memory/sintese, caps, retry e authority intactos. CLI
--inference-diagnostics exige generative explicito, max256 linhas sanitizadas.
Default sem sink preserva a composicao anterior. Observer nao promove evidence
live; excecao/mutacao do callback nao ignora fences, expiry, cancel ou cleanup.
Callbacks sao sincronos confiaveis, sem preempcao; budgets sao cooperativos.
responses_request completed confirma escrita local, nao entrega ao modelo;
responses_stream completed confirma EOF de framing, nao semantica/cleanup/aceite.

Runtime/corpus congelados:326 novos (273 unitarios transporte,34 composicao
host,19 TLS/Core/Memory) e535 focados integrados passaram sem skips.177
regressoes passaram em bateria separada; ha sobreposicao, nao somar contagens.
Auditoria readonly revalidou bindings apos callback terminal. Standard global
Windows aprovado:8994 casos,8883 passed/111 skipped/zero failed ou errors.
Skips globais nao contam como validacao Linux/POSIX, symlink indisponivel ou
integracao opcional. Nenhuma credencial/conta humana usada nas baterias locais.

Depois do gate, leitura selecionada confirmou sessao expirada. Um refresh
explicito autorizado foi concluido, plan_scope_granted=true. Instancia propria
UUID nova, perfil/transporte padrao real, sem factory/CA/modelo injetados.
Chrome headless efemero cercado ao origin proprio enviou uma unica vez a
pergunta sintetica ja revisada com gpt-6-astra. Catalogo, selecao e provider
setup passaram; diagnostico observou HTTP200, depois responses_stream failed
com unsupported_response_encoding, antes de aceitar eventos SSE.

Esse codigo cobre duas verificacoes: Content-Type diferente de text/event-stream
OU Content-Encoding diferente de identity/vazio. O observador nao registra os
valores nem a verificacao que recusou; nao afirmar gzip, HTML, JSON, quota,
permissao ou resposta concluida do modelo. HTTP200 nao equivale a inferencia
aceita. Proximo recorte deve distinguir categorias fixas de MIME/encoding,
preservando privacidade/limites, e testar antes de corrigir somente causa provada.
Nao relaxar parser, descomprimir ou aceitar outro MIME por hipotese.

Uma tentativa Web, ALLOW/rejected/inference_failed, evidence_mode=null,
analysis_characters=0. Final nativa2635 caracteres; consentimento apagado,
zero pageerrors, reload/recovery GET exatos. Browser fechado no finally e
somente servidor proprio parado. Export readonly quiescente dos dois SQLite
confirmou pergunta/final/bindings/eventos exatos, SHA256 da final
8c0479b51b6abd48a82812b65696e768e902e831ca8e7b4ea79a48990d933f5c.
Runtime/screenshot locais ignorados por Git, stores preservados. Sem retry,
fallback pago, tools, conta alternativa, leitura de historico humano ou promocao.
Nova inferencia exige novo consentimento; refresh feito nao autoriza outro envio.
Modelo, utilidade e qualidade nao homologados; ultimo validado MB235.
Pos-metadados:296 testes dos consumidores readonly de inventario/MCP passaram;
gate quick, CLI readonly do inventario e diff-check aprovados. Runtime/corpus
de diagnostico inalterados apos standard; somente docs/estado e expectation
do inventario atualizados. Nenhum commit/push nesta rodada.

## Historico da primeira tentativa e correcao de catalogo

Estado 2026-10-06: blocked para aceite real, nao homologado. Correcao local validada;
tentativa Web unica com modelo escolhido recusou complemento/inference_failed.
DOR da correcao minima fechado:
cap2 MiB apenas para sucesso200 GET api.openai.com/v1/models, demais caps256 KiB
e contratos existentes preservados. Corpus unitario/E2E em arquivos novos e
auditoria readonly paralelos; coordenador unico do transporte/gate/conta.
Operador escolheu ChatGPT/Codex
via OAuth e conta nova no diretorio privado sugerido fora de Git/OneDrive.
Login SIWC real concluido, conta externa validada, plan_scope_granted=true,
DPAPI CurrentUser. Nao autentica operador JARVIS nem concede authority/tools.
Nao foram importados tokens do Codex, lidos stores nao escolhidos ou expostas
credenciais/URLs de autorizacao/callbacks. Perfil opaco fica no store escolhido.

## Bloqueio historico comprovado, nao hipotese de conta

Depois do connect, uma consulta CLI de catalogo retornou siwc_operation_refused.
Um unico diagnostico dirigido ao mesmo perfil, sem imprimir credenciais/corpo
remoto, confirmou siwc_response_limit_exceeded. A conta carregou corretamente;
o leitor oauth_http.py recusa body maior que262144 bytes antes de parsear JSON.
Isso estabelece somente tamanho acima256 KiB, nao tamanho integral, schema,
conteudo ou lista de modelos valida. Nao repetir consultas em loop.

Nao houve inferencia, selecao de modelo, refresh, retry de inferencia ou fallback
pago. Nao aumentar _MAX_BYTES globalmente para contornar a prova: primeiro
definir budget proprio do catalogo e corpus de sucesso/refusa, preservar caps
de discovery/JWKS/token/erros, schema/count, deadlines e cleanup. Corrigir o
transporte por evidencia, gate, depois revalidar a mesma consulta explicitamente.

Correcao local implementada, corpus e gate standard aprovados: cap fixo2 MiB somente
para status200 GET api.openai.com/v1/models, selecionado internamente pela
tupla host/path/method/status, sem flag publica. Todos os demais sucessos e
erros conservam256 KiB; resposta redirect/500 segue recusada. Esse cap e
budget finito escolhido para o slice, nao medida do body real ou limite oficial.
Corpus cobre acima256 KiB, exatamente2 MiB/+1, erros e endpoints antigos,
1025 registros/schema adversarial, deadline/expiry/cancel apos limite antigo,
cleanup e E2E injetado ate Memory. Preservar JSON depth16/UTF8 estrito e chunks4096.
CLI tem outro cap256 KiB para JSON projetado de slug/display_name: nao ampliar
nem truncar silenciosamente; nao ha prova de que a projecao o exceda.

## Validacao local desta rodada

Runtime e corpus congelados:114 unitarios novos e12 E2E novos aprovados sem
skips;540 existentes OAuth/conta/port/Core/profile/inventario aprovados. Gate
standard global Windows aprovado,8668 casos coletados. Apos o gate, uma unica
consulta real CLI da conta escolhida passou, com5 escolhas listadas e
fixed_https_transport/authority=none. Nenhuma inferencia, refresh ou fallback.
Operador autorizou a unica pergunta sintetica e escolheu gpt-6-astra.
Catalogo nao comprova entitlement
de inferencia nem qualidade. Nenhum corpo remoto ou credencial registrado.
Auditoria readonly nao encontrou bloqueador novo. Testesunitarios incluem CLI
real com store/session sinteticos: cap de exibicao256 KiB permanece inalterado.

TLS E2E em loopback proprio leu catalogo262145 bytes e2 MiB exatos, ordem/slug
exatos, uma coleta e uma inferencia injetada ate Core/SQLite/eventos/restart.
Metadata do catalogo nao entra no prompt/final. Oversize/schema/count/JSON/
cleanup/error/modelo nao listado recusam sem contactar modelo. DEFER/BLOCK nao
coletam catalogo. Transports/CAs/credenciais sao sinteticos; nao conta humana.

Primeiro focused tentou credenciais sinteticas dentroOneDrive:498 passed,
7failed/35setup errors por siwc_storage_path_refused. Repetido foraGit/OneDrive
em Temp UUID proprio validado:540passed. Nenhum guard foi relaxado. Uma falha
inicial de fixture E2E simulava cleanup dentrogetresponse/Connection:close;
ajustada somente injecao para cleanupfinal,12E2E finaispassaram. Nenhuma
assertion de produto foi removida. Fonte oficial nao substitui essas provas.

## Primeira tentativa real (historico)

Operador escolheu gpt-6-astra dentre os5 slugs listados e consentiu a unica
pergunta abaixo. Instancia CLI propria abriu runtime web-live/UUID novo, sem
store console/historico humano. Startup/perfil padrao real, nenhuma factory,
CA, resposta ou transporte de modelo injetados nesta tentativa.

Entrada de browser IAB indisponivel (timeout do controlador, antes de envio);
prova executada em Chrome headless efemero, com requests do browser cercados
somente ao origin loopback proprio. Um POST /api/generative-analysis, ALLOW,
generative_status=rejected, generative_error_code=inference_failed,
generative_evidence_mode=null, analysis_characters=0. Final nativa2635
caracteres preservada, consentimento apagado, zero pageerrors. Reload e
recovery GET recuperaram exatamente a mesma final, sem outro POST Web.
Nao houve refresh, retry de inferencia ou fallback.

Browser proprio fechado no finally; instancia propria parada por Ctrl+C.
Export readonly dos dois SQLite quiescentes validou bindings/eventos,
pergunta exata, ALLOW/rejected e final byte-exata (SHA256
8c0479b51b6abd48a82812b65696e768e902e831ca8e7b4ea79a48990d933f5c).
Runtime e screenshot permanecem locais ignorados por Git; stores preservados.

Essa evidencia NAO confirma resposta do modelo nem causa HTTP/conta/servico.
O erro fixo de sintese colapsa resultados nao completed, e o port tambem
colapsa varias causas. Um POST Web nao comprova um POST externo ou entrega
da pergunta ao modelo. Nao diagnosticar quota/expiry/permissao/modelo por
hipotese. Proximo recorte: diagnostico bounded de fase/codigo allowlisted,
sem corpos/headers/URLs privadas/credenciais, com corpus antes de outra prova.
Nova inferencia ou refresh exige consentimento separado; nao repetir esta
pergunta automaticamente. MB236 nao fecha por fallback nativo bem-sucedido.
Pos-metadados finais:296 testes de inventario/consumidores MCP readonly
passaram, gate quick, CLI readonly do inventario e diff-check aprovados.
Runtime e corpus126 congelados apos standard; alteracao posterior somente
de estado/documentacao e expectation do teste de inventario. Nenhum commit/push.

## Caminho existente e prova seguinte

chatgpt-account connect faz SIWC proprio em auth.openai.com, nao login/tokens
do Codex instalado. Catalogo usa GET api.openai.com/v1/models e escolha de slug
listado. Inferencia usa POST api.openai.com/v1/responses, store:false/stream:true.
Nao usar chatgpt.com/backend-api. Nenhuma chave API paga e necessaria neste
caminho; disponibilidade/permissao de modelo dependem da conta e do servico.

Catalogo validado e gpt-6-astra escolhido; qualquer nova tentativa requer
novo consentimento. Caminho para uma futura prova: iniciar apps.jarvis_api
com --authorized --port 0 --enable-generative e diretorio/perfil/modelo exatos.
Startup cria novo .jarvis_runtime/web-live/UUID retido; nao usar o default da
generative_analysis_cli que abre .jarvis_runtime/console existente. Nunca
escrever diretorio/perfil privado em arquivos de configuracao versionados.

Parear e consentir a pergunta sao etapas separadas. Revisar somente pergunta
sintetica curta, sem dados pessoais ou segredos, na elegibilidade nativa:
Compare os relatórios de documentação e observabilidade do piloto
Um POST generativo; sem automatico reenvio em falha/timeout/resultado incerto.
O timeout Web20s inclui catalogo e inferencia; stop espera nao desfaz commit.
Recovery/reload GET, nenhuma inferencia nova. Final integral exata de Memory/
eventos e export readonly do runtime proprio apos parar somente essa instancia.
Native control sem consentimento nao recebe modelo. Nenhum tool/mic/TTS/efeito.

Accepted/live/ALLOW confirma somente fluxo e estrutura do complemento. Verdade,
utilidade e naturalidade dependem de avaliacao separada com o usuario. OAuth
conectado nao encerra F01/F06/T02 nem torna o sistema completo.

Rollback: omitir perfil/modelo devolve Web nativa; fechar instancia propria sem
apagar stores. Nao desconectar/revogar/resetar conta implicitamente. Revogacao
remota exige consentimento e fluxo proprio; nao foi comprovada nesta rodada.

## Fontes oficiais verificadas com OpenAI Docs

As fontes confirmam SIWC OSS publico, PKCE/nonce e validacao de ID token; o
catalogo por conta e Responses, nao endpoint privado nem permissao para tools.
Essa verificacao manteve o fluxo existente e impediu promover login a inferencia.

- [Registration and sign-in](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
- [Models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [Preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
- [Errors and recovery](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery)

Catalogo real validado; segunda tentativa unica recusada em preflight de SSE
depois de HTTP200, inferencia/qualidade nao aceitas. Diagnostico local validado.
Fonte oficial nao substitui a prova fisica. Backlog unico: MB236 blocked,
MB235 done local.
