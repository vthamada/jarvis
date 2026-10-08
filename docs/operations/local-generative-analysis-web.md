# MB232 - complemento generativo na Web local

Atualizacao 2026-10-06: MB235 done local melhora a apresentacao compacta desta
Web; parser/controller/API/Core/Memory intactos e standard global aprovado.
OAuth real conectado posteriormente, catalogo bloqueado acima256 KiB, sem
inferencia aceita. Ver compact-local-conversation-web.md e real-oauth-acceptance.md.
Evidencia e proximo recorte MB233/234 descritos abaixo sao historicos.

Estado 2026-10-06: MB232 done local; baterias focadas, browser e gate standard
global Windows completo aprovados, com 8314 casos coletados. Conta/modelo reais, utilidade/verdade da resposta
e qualidade conversacional permanecem aceites separados. Nao e API publica,
auth humana, autonomia ou ferramenta promovida.

## Default e opt-in explicito

A Web nativa MB231 permanece com modelos desativados:

```powershell
.venv/Scripts/python.exe -m apps.jarvis_api --authorized --port 0
```

Para uso futuro com uma conta ja configurada e escolhida explicitamente pelo
operador, os argumentos sao (substituir placeholders; nao executado nesta prova):

```powershell
.venv/Scripts/python.exe -m apps.jarvis_api --authorized --port 0 --enable-generative --credential-dir "CAMINHO_ABSOLUTO_ESCOLHIDO" --profile-ref "profile-64_HEXADECIMAIS" --model "MODELO_ESCOLHIDO" --generative-timeout-seconds 20
```

Configuracao incompleta/invalida e recusada antes de criar runtime ou abrir
conta. Profile/modelo so existem no host; nao sao expostos nem escolhidos pela
Web. Sem descoberta de contas, login, refresh, retry ou catalogo no startup.
O constructor do perfil e `port_for` sao inertes; o store/catalogo/inferencia
so podem ser abertos dentro de infer, depois da elegibilidade/privacidade Core.
Guia da seam existente: [MB229](generative-analysis-core.md).

Pareamento e consentimento sao distintos. A caixa de complemento comeca
desmarcada e autoriza somente a pergunta atual; e apagada antes do envio.
Sem caixa marcada, pedido v1 nativo, mesmo com host configurado. Host sem
perfil recusa pedido generativo com `generative_unavailable`, sem criar turno
ou tentar conta/modelo. Isso nao e autorizacao para acao, mic ou voz.

## Core soberano e contratos

Protocolos/rotas nativos v1 permanecem intactos. V2 usa POST
`/api/generative-tickets` com `{consent:true}` e `/api/generative-analysis`
com `{ticket,query,consent:true}`. Auth/CSRF/Origin/limites/fences sao os mesmos
de [MB231](local-authenticated-analysis-web.md). Extras, consentimentos falsos/
coercivos e ticket de outro modo sao recusados antes do Core/adapter.

`jarvis-local-analysis-v2` conserva as cinco chaves de envelope; result acrescenta
`generative_error_code`, `generative_evidence_mode` e
`generative_analysis_characters`. accepted exige ALLOW elegivel, erro nulo,
1..4000 caracteres e modo de evidencia da composicao. rejected/withheld exigem
zero caracteres, evidencia nula e diagnostico fixo, nunca texto rejeitado.
`core_local` descreve o Core, nao autentica pessoa/conta/modelo externo.

SynthesisEngine generativo e composto por ticket e restaurado no finally;
pedido v1 seguinte nao herda perfil. Decisao, identidade e Memory continuam
nativas; Operational.execute bloqueia antes de corpo/efeito. DEFER/BLOCK,
fora de escopo e padroes sensiveis nao abrem adapter. Detector de privacidade
e conservador de padroes conhecidos, nao DLP universal.

Modelo recebe somente pergunta atual, nao historico, identidade canonica,
cookie/CSRF ou caminho do store. Bloco de proposta e literal e nao verificado,
subordinado a final Core; parser nao comprova verdade semantica. Readback
valida metadados/eventos persistidos, bloco literal completo e final exata de
Memory/StoredTurn. Falha pode ter commit e retorna resultado incerto, sem rerun.

## Prazos e recuperacao

Orcamento cooperativo ate20s inclui factory/catalogo/inferencia; passa somente
tempo restante ao port. Nao interrompe arbitrariamente Python/factory bloqueante.
Snapshot de perfil/modelo/conta, request e result e revalidado antes/depois.
Troca/forja/timeout/cancelamento descartam entrega ou complemento, nao fabricam
rollback da memoria. Porta injetada nunca pode estabelecer evidencia live.

Espera Web30s, ticket/result120s, sessao900s e max64 tickets compartilhados
v1/v2; um Core ativo globalmente. Stop espera nao cancela commit. Disconnect/
expiry/close cercam entrega e sinalizam cancelamento cooperativo do port.
GET recupera ticket existente e sua versao; nunca repete POST/inferencia.
Reload browser e restart processo sao diferentes: auth/tickets nao sao duraveis,
stores novos sao preservados e inspecao readonly apos restart e separada.

## Evidencias desta rodada

Tres workers: perfil/port, Core/readback e Web v2; coordenador startup/HTTP/
browser/gate.222 Python novos:95 perfil,73 Core (57 unitarios/16 integracao),
17 startup,34 HTTP/Core,3 harness;141 Node novos (117 controller/24 DOM).
Todas as baterias novas passaram sem skips;830 Web Node completos passaram,
incorporados ao gate por pytest.349 auth/HTTP/v1/profile/startup focados e
159 service/Core (86 antigos+73 novos) passaram, mantendo testes v1 intactos.

Browser em runtime proprio com fixture injetada: final3131 codepoints byte-exata
ao exportador canonico; consentimento apagado, rótulo de teste/nonverified,
reload/GET e perda GET simulada recuperados com um unico POST generativo.
DEFER reteve complemento; pedido seguinte sem caixa marcada voltou ao v1.
Mobile390x844 sem overflow horizontal/scroll interno/botoes abaixo44px;
reload pareado sem erros de console.401 inicial sem pareamento e ERR_FAILED
provocado pela interrupcao sao esperados. Disconnect apagou final/consentimento.
Instancia propria encerrada, runtime/evidencias preservados e ignorados por Git.
Auditoria cruzada readonly de startup/HTTP/fixture sem bloqueador concreto.
Standard global Windows completo passou (8314 casos coletados). Depois da
sincronizacao documental/estado, 132 testes de inventario/startup/harness/UI,
gate quick, consulta readonly do inventario e diff-check passaram. O pytest
focado avisou somente sobre acesso negado ao cache, sem falha de teste.

Nao executamos helper de conta real, TLS/modelo externo, store humano, nova
prova Linux, commit ou push. Fixtures nao representam aceite de inferencia real.

## Desativacao e proximo recorte

Omitir opt-in/profile devolve v1 nativa; parar instancia propria/revogar sessao
sem apagar Memory/eventos. Nao relaxar CSP, migrar stores ou promover ferramenta.
MB233 ready: leitura humana readonly do complemento, mantendo final canonica
inteira e origem nao verificada. MB234 ready independente: MCP readonly do
inventario autoral, sem bridge no Core. Criterios e ownership na fila unica de
execucao; ambos ainda nao implementados.
