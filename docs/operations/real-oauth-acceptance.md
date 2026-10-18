# MB236 - homologacao controlada OAuth

## Piloto separado F01/F04 - 2026-10-17

O operador autorizou ate10 chamadas com gpt-6.1-sol na mesma conta para um
piloto de missoes sinteticas publicas, sem renovacao automatica. Houve uma
unica tentativa de inferencia; o catalogo recusou siwc_credential_expired,
zero respostas de modelo concluidas e zero turnos Core no piloto. Parou sem
refresh, retry ou fallback pago. Tokens/custo/contagem HTTP desconhecidos.
Nao ha evidencia nova sobre Content-Type; MB236 continua blocked e a prova
gpt-6-astra abaixo permanece historica. Qualquer renovacao/nova tentativa
requer autorizacao. Protocolo/artefato: harness-mission-campaign.md.

## Atualizacao vigente: corpo recusado limitado - 2026-10-12

Operador autorizou uma tentativa adicional unica, mesma conta, gpt-6-astra e
pergunta sintetica exata, com leitura limitada apenas para diagnostico. Preflight
encontrou sessao expirada: um refresh oficial da mesma conta concluiu com
binding/plan scope preservados. Nenhum login de outra conta, API key ou import.

Sonda ignorada por Git, nao composicao de producao: uma chamada read1(4096)
somente em HTTP200 sem CT e encoding identity; timeout adicional <=2s e limitado
ao budget restante. Classifica prefixo sem refletir/persistir corpo, IDs ou
textos de erro. Self-test offline cobre opt-out, status/media/encoding/deadline,
limite, HTML/JSON/SSE aparente, conteudo secreto e TLS inseguro. O transporte
de producao nao mudou e continua recusando media type ausente antes do SSE.

Unico POST real retornou HTTP1.1/200, headers presentes, parser sem defeitos,
CT/CL ausentes, TE chunked declarado, encoding identity. TLS verificado/issuer
conhecido/peer publico; server cloudflare, sinais CF/cache presentes, sinais API
ausentes, cf-mitigated=challenge nao declarado. Isso nao exclui intermediarios.
A unica leitura entregou416 bytes, categoria sse_like_prefix_unvalidated.
Nao e HTML/JSON no prefixo observado, mas nao comprova eventos validos, stream
completo, completed, inferencia util ou componente que omitiu CT. Bytes nao
foram fornecidos ao parser/modelo/Core, nem gravados em evidencia. Zero retry,
descompressao, header inventado, fallback ou aceite generativo.

Browser proprio encerrou no finally com erro fixo: prova DOM/reload desta
tentativa NAO passou e nao foi repetida. Servidor proprio parado, stores
retidos. Export readonly quiescente validou unico turno/pergunta exata e
21 eventos: ALLOW/rejected/inference_failed, evidence null, analysis0, final
nativa2635 armazenada. Consistencia canonica nao substitui prova browser.
MB236 continua blocked; nao ha defeito local de transporte comprovado para
relaxar o guard. Proximo passo exige triagem da entrega upstream; outra
inferencia precisa nova autorizacao. Notas abaixo sao tentativas historicas.

## Estado vigente: investigacao de origem - 2026-10-12

MB236 blocked para aceite real. Operador autorizou investigar a origem da
resposta sem CT, corrigir apenas defeito comprovado e, se necessario, uma nova
tentativa unica com gpt-6-astra e a mesma pergunta. Nenhuma correcao de runtime
foi comprovada; nao substituir CT ausente por SSE, aceitar JSON/HTML, retirar
guard ou introduzir retry por hipotese. Runtime/corpus mantiveram hashes da
versao aprovada pelo standard anterior.142 regressoes locais HTTP/TLS/Core/
Memory/restart passaram, sem conta/modelo reais.

Controle publico GET /v1/models, sem autenticacao nem leitura de corpo:
HTTP1.1/401, CT presente, parser sem defeitos, server class cloudflare,
sinais CF e API presentes, via ausente, TLS verificado/issuer conhecido/peer
publico. Nenhum override HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/SSL_CERT_FILE/
SSL_CERT_DIR/OPENAI_BASE_URL observado. Esse controle nao reproduz o POST nem
comprova ausencia de intermediario transparente ou entitlement.

Para a unica tentativa, uma sonda efemera ignorada por Git observou metadados
do socket TLS e do HTTPResponse real sem modificar headers, ler corpo ou
substituir resposta. Usa os seams explicitos de factory em GenerativeProfile/
SessionInferencePort, mantendo Core/governanca/memoria/sintese. Por isso e
instrumented_diagnostic/injected_transport, NAO evidencia de aceite live.
Sem monkeypatch global da rede, endpoint/proxy/CA configurable ou token de
outro app. Self-test sobre HTTPResponse real/sockets BytesIO sinteticos validou
que classificacao nao le corpo/reflete valores; verifica recusa de TLS inseguro.
Primeira sonda inline teve erro de sintaxe antes de rede, corrigido localmente.

Mesmo perfil/escopo/vinculo carregados e sessao nao expirada, zero refresh.
Uma instancia Web propria UUID nova e Chrome headless proprio cercado somente
ao origin loopback; exatamente um POST Web/pergunta exata autorizada. Catalogo,
selecao gpt-6-astra e provider setup passaram. Dois registros sidecar fixos
sem valores/IDs remotos/certificados/paths privados, alem dos23 diagnosticos
normais: TLS issuer_category=known_public_issuer e peer_category=public_address;
response server_category=cloudflare, api_trace_present=false,
cloudflare_trace_present=true, via_present=false, envoy_hint_present=false,
cache_hint_present=true, media_present=false, parser_defects_present=false.
api_trace testa presenca de x-request-id/openai-processing-ms/openai-version;
cache_hint testa x-cache/cf-cache-status, NAO seus valores nem HIT/MISS/challenge.
Issuer conhecido e categoria de uma lista local, NAO pinning de CA oficial.
Sinais declarados por headers nao autenticam quem os escreveu.

HTTP1.1/status200, headers presentes, CT e CL ausentes, TE chunked declarado;
recusa unsupported_response_encoding antes do leitor SSE/corpo. A diferenca
de sinais frente ao GET e compativel com resposta gerada/alterada na borda,
mas nao prova onde CT foi omitido, nem WAF/cache, causa de conta/permissao/quota
ou corpo SSE valido. Nao concluir que todo erro200 venha da API de modelos.
Sem corpo, trace IDs ou headers brutos nao ha correlacao para identificar
definitivamente o componente upstream. Nao inventar correcoes de payload/UA/
headers, nem repetir o POST para testar hipoteses sem novo consentimento.

ALLOW/rejected/inference_failed, evidence_mode=null, analysis_characters=0,
final nativa2635, SHA256
8c0479b51b6abd48a82812b65696e768e902e831ca8e7b4ea79a48990d933f5c.
Consentimento apagado, zero pageerrors, reload/recovery GET exatos. Browser
fechado no finally; somente servidor proprio parado. Export readonly dos dois
SQLite quiescentes validou pergunta/final/bindings/quatro eventos, authority=none.
Store e SQLite retidos; sem refresh/reenvio/fallback/tools/promocao/login/push.

Proximo recorte depende de triagem da entrega externa ou diagnostico adicional
explicitamente delimitado; nao presumir SSE valido por status e nao reenviar
automaticamente. OpenAI Docs manteve endpoint publico/mesmo modelo e exigencia
de completed. [Revisao PR-1](pr-1-documentation-review-2026-10-12.md) separa
esse bloqueio do erro preexistente do CI Linux. Notas abaixo historicas.

Gate standard final do checkout Windows:9222 casos/9111 passed/111 skipped/
zero failed/errors. Hashes de runtime/corpus iguais aos da versao anterior;
somente investigacao/sondas efemeras e documentacao nesta rodada.25 registros
host (23 normais +2 sidecar) validados por contagem/schema. Nenhuma nova
inferencia apos a tentativa unica; gate local nao aprova o CI Ubuntu do PR.

## Estado vigente: parsing/enquadramento - 2026-10-12

MB236 blocked para aceite real. Operador autorizou implementar metadados seguros
de parsing/enquadramento e uma nova tentativa unica com gpt-6-astra e a mesma
pergunta sintetica; renovar apenas a mesma sessao expirada. Nenhuma autorizacao
para relaxar SSE, descomprimir, fazer retries, trocar conta/modelo ou fallback.

Seis fases host opt-in e26 codigos fixos: responses_http_version (1.0/1.1/other/
unavailable), responses_header_count (empty/present/unavailable),
responses_header_parse (clean/missing_separator/other_defect/unavailable),
responses_media_presence (absent/present/unavailable), responses_content_length
(absent/zero/nonzero/invalid/multiple/unavailable) e responses_transfer_encoding
(absent/chunked/other/invalid/multiple/unavailable). Count distingue zero de
nao zero; nao registra nomes/quantidade exata. Clean significa ausencia de
defeitos registrados pelo parser stdlib, nao prova de conformidade de todos os
bytes remotos. Framing e declarado, nao prova de bytes de corpo validos.

Somente HTTPMessage exato e int/str exatos; metadados indisponiveis ou excepcionais
viram categoria fixa, sem stringify, texto de defeito, URLs, identidades ou tokens.
Schema5/max256 e erro publico unsupported_response_encoding intactos. None nao
inspeciona novos atributos; nao200 continua sem headers/corpo. check apos cada
observacao antes da seguinte/leitura. Guard/caps/timeout/cleanup/endpoint intactos,
nenhuma dependencia externa nova (email.errors da stdlib). Rollback: omitir
--inference-diagnostics; nao transforma observacao em autoridade/aceite.

Corpus com48 unitarios novos e9 TLS/Core/SQLite/restart,62 casos adicionais de
allowlist. Parser HTTPResponse real distingue CT ausente, CT vazio e headers
descartados apos linha invalida com MissingHeaderBodySeparatorDefect. Cobre
versao/CL/TE duplicados/invalidos, objetos opacos/subclasses, observer mutate/
raise, cancel/expiry/deadline em cada nova fase, None/no200, guard e no body read.
Testes red iniciais:35 falharam por observacoes ausentes,3 passaram. Primeiro
focused integrado722 passed/1 failed por expectativa da sequencia antiga de
eventos; atualizada para seis novas fases, depois723 passed. Dez adversariais
adicionados:48 unitarios finais passaram. Standard global Windows9222 casos:
9111 passed/111 skipped/zero falhas. Hashes runtime/corpus iguais apos gate;
skips nao homologam outro ambiente. Sem alteracoes de runtime apos standard.

Preflight local selecionado antes e depois do gate validou load/binding/escopo;
sessao nao expirada, zero refresh. Duas sondagens iniciais recusaram parametro
de caminho str em vez de Path; sonda corrigida, nenhum guard de produto mudado.
Uma instancia Web propria UUID nova, composicao/transporte real padrao, sem
factory/CA/resposta/modelo injetados. Browser Chrome headless efemero cercado ao
origin loopback proprio enviou exatamente uma vez:
Compare os relatórios de documentação e observabilidade do piloto

Catalogo/selecao exata/provider passaram. Registros host sanitizados23:
HTTP1.1/status200, response_headers_present, response_header_parse_clean,
response_media_absent/response_media_type_missing, response_encoding_identity,
response_length_absent e response_transfer_chunked; recusa
unsupported_response_encoding antes da leitura do corpo/SSE. Nao ocorreu o
defeito de separador reproduzido localmente. A evidencia restringe a hipotese
de descarte pelo defeito observado, mas nao identifica origem da omissao nem
comprova corpo valido, resposta concluida, quota/entitlement ou causa da conta.
Nao afirmar que o servidor bruto omitiu CT por inferencia do parser.

ALLOW/rejected/inference_failed, evidence_mode=null, analysis_characters=0,
final nativa2635 caracteres, SHA256
8c0479b51b6abd48a82812b65696e768e902e831ca8e7b4ea79a48990d933f5c.
Consentimento apagado, zero pageerrors; reload/recovery somente GET, final
exata. Browser fechado no finally e somente servidor proprio parado por Ctrl+C.
Export readonly dos dois SQLite quiescentes validou pergunta/final/bindings e
quatro eventos canonicos, authority=none. Logs/screenshot/runtime ignorados por
Git; store e SQLite retidos. Nenhum reenvio/fallback/tools/login/import/push.

Proximo recorte candidato: investigar a origem da resposta recebida sem
declaracao SSE, sem presumir corpo valido ou alterar parser por hipotese.
Nova inferencia exige nova autorizacao. Ultimo validado MB235; F01/F06 partial,
MB236/modelo/qualidade nao aceitos. OpenAI Docs preservou caminho oficial
publico/catalogo por conta/store:false/stream:true; nao substituiu modelo.
Notas abaixo sao historicas, nao o estado vigente.

Pos-metadados:307 consumidores readonly de inventario/MCP aprovados. Primeiro
resumo autoral ultrapassou o cap512 caracteres:66 failed/135 passed/106 setup
errors por invalid_product_readiness_inventory. Corrigido apenas o texto para
500 caracteres; nenhum cap, schema ou teste relaxado. Runtime/corpus com hashes
do standard preservados. Gate quick e diff-check finais aprovados.23 registros
host da prova validados contra o schema5; nenhum segundo envio ou refresh.

Estado vigente apos retomada 2026-10-12: MB236 blocked para aceite real.
Login oficial concluido e uma tentativa unica realizada; media type
ausente/vazio recusado antes de SSE. Notas seguintes registram o historico.

## Retomada e prova unica - 2026-10-12

Operador delegou escolha de recuperacao. Parent privado autorizado preparado
foraGit/OneDrive; connect real oficial iniciou novo registro local, pois
client/host/mapping antigos ausentes. URL/callback/state/nonce/codigo/tokens
nao registrados. Observer do lancamento do browser apenas imprimiu bool,
preservando chamada real, sem injecao de cliente/CA/token. Operador confirmou
ter escolhido mesma conta; CLI validou ID token/conta/plan scope e salvou em
DPAPI CurrentUser. Nao ha binding local antigo para comparar; nao alegar
restauracao do registro anterior ou comprovar igualdade apenas por email.
Nenhuma credencial de outro app/store foi buscada/importada. Perfil novo opaco
mantido somente no store/configuracao privada, nao neste documento.

Preflight local do perfil novo confirmou sessao nao expirada; zero refresh.
Hashes de runtime/corpus iguais a versao aprovada por standard8992 passed/
111 skipped. Instancia Web propria UUID nova, perfil/transporte padrao real,
sem factory/CA/modelo/resposta injetados. Browser Chrome headless efemero
cercado ao origin proprio enviou uma unica vez a pergunta autorizada com
gpt-6-astra. Catalogo, selecao exata e provider setup passaram; nao afirmar
contagem nova de modelos, pois houve apenas catalogo lazy do port nesta prova.

Diagnostico host observou HTTP200, response_media_type_missing e
response_encoding_identity, depois unsupported_response_encoding antes da
leitura do corpo/SSE. Media type missing cobre ausente/vazio/parte MIME vazia;
identity cobre identity/vazio/default de header ausente. Nao distingue ausencia
de valor vazio, nem prova encoding real do corpo, stream valido, causa do
servidor/gateway ou resposta concluida do modelo. Headers/corpo brutos e IDs
remotos nao registrados. A recusa nao e evidencia de quota/permissao/expiry.
O proximo recorte candidato deve investigar por que o media type esperado nao
foi declarado, com DOR/corpus/gate antes de corrigir causa comprovada. Nao
relaxar parser, ler/aceitar JSON ou presumir SSE valido por status200.

Uma tentativa Web, ALLOW/rejected/inference_failed, evidence_mode=null,
analysis_characters=0; final nativa2635 caracteres. Consentimento apagado,
zero pageerrors, um POST Web, GET/reload exatos. Browser fechado no finally,
somente servidor proprio parado; dois SQLite quiescentes preservados.
Export readonly validou pergunta/final/bindings/eventos byte-exatos, SHA256
8c0479b51b6abd48a82812b65696e768e902e831ca8e7b4ea79a48990d933f5c.
Runtime, log sanitizado e screenshot locais ignorados por Git; store retido.
Sem retry, fallback pago, tools, historico humano ou promocao. Nova inferencia
exige novo consentimento. Ultimo validado MB235, MB236/qualidade nao homologados.
Sem commit/push. Fontes OpenAI Docs preservaram fluxo publico/validacao de
identidade e evitaram substituir modelo ou usar endpoint privado.
Pos-metadados da retomada:296 consumidores readonly de inventario/MCP passaram;
quick, CLI readonly e diff-check aprovados. Runtime/corpus mantiveram hashes
do standard; somente docs/estado da prova atualizados nesta retomada.

Estado vigente 2026-10-12: MB236 blocked para prova real. Diagnostico refinado
validado; store privado escolhido ausente antes de qualquer chamada externa.

## Refinamento MIME/encoding - 2026-10-12

Operador autorizou uma nova tentativa unica com gpt-6-astra e a mesma pergunta
sintetica; refresh somente da mesma sessao se expirada. Novas fases host
opt-in responses_media_type/responses_content_encoding classificam somente
headers ja lidos pelo guard antigo. Categorias fixas SSE/JSON/HTML/missing/
other/invalid e identity/gzip/deflate/br/other/invalid; sem valores brutos,
parametros, corpos, tokens, paths, identidades, pergunta ou resposta emitidos.
Schema de5 campos/max256, default None, erro publico
unsupported_response_encoding e criterios de recusa intactos. check apos
cada callback; nenhum parser/descompressor, retry/fallback, endpoint, budget
ou dependencia novos. Categoria conhecida e declaracao de header, nao prova
do corpo, causa do servidor ou conclusao do modelo. Erros nao200 continuam
sem leitura de headers/corpo e sem essas duas fases.

Implementacao/corpus congelados:69 unitarios novos/16 TLS/Core/Memory novos
passaram; allowlists acrescentam24 casos parametrizados existentes. Root
772 focados integrados passaram. Standard global Windows aprovado:9103 casos,
8992 passed/111 skipped/zero failed ou errors. Hashes de runtime/corpus iguais
antes/depois do gate; auditoria readonly sem bloqueador. Skips nao homologam
outro ambiente. Regressao antes da producao falhou pela ausencia de categorias.
Primeiro E2E14/2F identificou oracle errado de cancelamento; teste ajustado
somente para cancelled legado (recusas de headers continuam inference_failed),
depois16 passaram. Nenhum guard/assertion de produto relaxado.

Apos gate, leitura local somente do perfil escolhido recusou
siwc_storage_unavailable. Checagem dirigida por metadados confirmou parents
existentes e diretorio privado escolhido/arquivos de controle ausentes. Nao
registrar path/ref privados, nao atribuir causa/autoria da ausencia nem inferir
expiry/revogacao. Nao se chegou a catalogo ou inferencia real; zero refresh,
login, outra conta/store, import de tokens ou fallback. Nenhuma instancia
Web/browser real nova foi iniciada, nenhum novo screenshot/modelo/final real.
A tentativa unica autorizada nao foi realizada; nao alegar que foi enviada.

Retomada depende de restaurar o diretorio escolhido ou de autorizacao explicita
para login da mesma conta. Nao inicializar outro store, procurar credenciais
de outros apps ou repetir chamadas externas para contornar a ausencia.
Autorizacao de refresh condicionado nao e autorizacao de novo login. Nao
apagar dados nem sobrescrever evidencias anteriores. MB236/modelo/qualidade
permanecem nao homologados; ultimo validado MB235. Sem commit/push.
Estados seguintes sao historicos, nao prova nova desta rodada.
Pos-metadados:296 testes de consumidores readonly de inventario/MCP passaram;
quick, CLI readonly e diff-check aprovados. Runtime/corpus com hashes intactos
apos standard; somente docs/estado e expectation de inventario atualizados.

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
