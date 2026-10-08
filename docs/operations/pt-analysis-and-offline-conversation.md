# MB230 - analise PT-BR e leitura offline da conversa canonica

Estado 2026-10-06: MB230 done local; baterias focadas e gate
standard global Windows completo aprovados. Nao e API Web, autenticacao, modelo real ou promocao
do sistema completo. MB229 permanece preservado.

## Comportamento entregue

Executive reconhece verbos EN/PT delimitados no mesmo slot de analise.
Knowledge usa aliases delimitados de documentacao, observabilidade, telemetria,
relatorio e piloto somente na copia usada para selecionar dominios. Entrada,
fontes, pesos, especialistas, autonomia e governanca permanecem intactos.
Pares EN/PT atravessam o Core nativo com as mesmas decisoes; pedidos sem
evidencia suficiente continuam DEFER, sem chamada ao modelo.

Orchestrator acrescenta `conversation_readback` a `memory_recorded` somente
apos armazenar o turno. Schema `jarvis-conversation-readback-v1`: timestamp
exato do record, hash do principal ou null, hash UTF-8 da pergunta e da final.
StoredTurn nao possui request_id/memory_record_id; a correlacao depende desse
binding novo e dos envelopes canonicos. Registro legado sem binding e recusado;
nao ha migracao, backfill ou associacao aproximada por tempo.

## Exportacao opt-in readonly

Selecionar explicitamente dois bancos SQLite existentes, absolutos e quiescentes
(sem WAL/SHM/journal ativo), sujeito canonico, sessao e pedido. Exemplo com
placeholders, nao caminhos/identidades descobertos automaticamente:

```powershell
.venv/Scripts/python.exe -m apps.jarvis_console.conversation_export --authorized --memory-db ABSOLUTE_MEMORY_DB --events-db ABSOLUTE_EVENTS_DB --session-id SELECTED_SESSION --request-id SELECTED_REQUEST --principal-ref EXACT_CANONICAL_MEMORY_USER
```

Por padrao stdout contem somente metadados. `--include-content` solicita pergunta
e final integrais; filtros de dados conhecidos podem reter ambos por inteiro.
Nao constitui filtro universal de PII. Principal e o user_id canonico da Memory,
nao autenticacao OAuth ou identidade humana. Nenhum Core e construído, pedido
reexecutado, conta selecionada ou token lido/refrescado. O comando nao grava
arquivo; salvar stdout e uma decisao separada do operador.

Limites: 256 MiB por DB, SELECT readonly em tabelas canonicas, prazo10s com
cancelamento/progress fence, eventos bounded e ambiguidade recusada. Symlink,
reparse/hardlink, views/virtual tables e mudanca observavel do arquivo falham
fechado. Quatro eventos correlacionados, ordem causal, binding, principal,
conteudo/intent e record reuse na sessao sao verificados. Nao autentica bancos
editaveis nem prova unicidade global de request/record entre todas as sessoes.

## Contrato e importacao Web

Pacote flat `jarvis-conversation-pack-v1`, authority=none,
operator_authenticated=false, runtime_capability_promoted=false. Contem refs
SHA-256 pseudonimas (nao anonimizacao garantida), timestamp UTC, intent, decisao
de governanca e estado/erro/modo/count da analise generativa. Origin
`canonical_core_export` e declaracao nao autenticada.

Com conteudo, query/response_text sao byte-exatos UTF-8, contagens por codepoint,
hash SHA-256 de `schema + NUL + query + NUL + response_text`. Sem conteudo,
campos textuais ausentes/hash null. Teto262144 bytes, pergunta16000 e final131072
codepoints; Unicode de controle e surrogates recusados salvo CR/LF/tab.
JSON duplicado/extra, UTF-8 invalido, datas invalidas e estados incoerentes
falham fechado. Hash valida consistencia, nao assinatura, origem ou autoridade.

No cockpit, abrir painel **Conversa canonica**, consentir e selecionar JSON.
O leitor nao faz upload/network/storage, nao aciona Core/modelo/TTS e nao muda
a conversa de demonstracao. Texto entra exclusivamente por textContent.
Rotulo constante: **pacote offline - origem nao autenticada** (UI usa travessao).
Nova selecao limpa conteudo anterior durante leitura; invalido ou outra sessao/
sujeito recusam e removem anterior. Descartar limpa contexto/consentimento e
devolve foco. Revogar, reset e pagehide invalidam callbacks, limpam conteudo e
exigem nova permissao; selecao de arquivo tambem perde o nome apos leitura.

## Evidencia e limites

599 testes Python novos (290 intent,82 binding,122 exportador,36 dominios,
14 Core PT,50 Core/export/restart e5 Web) e209 Node novos. Suite Web completa:
553 Node; wrapper pytest executa todos via Node real, se disponivel. Baterias
novas passaram sem skips no Windows; Node ausente e skip explicito, nao aceite JS.
Fixtures de Graph nao comprovam backend LangGraph instalado. Analise fixture
aceita nao e inferencia/modelo/qualidade reais.

Prova Playwright real: servidor static proprio em porta efemera, pacote publico
de Core nativo/SQLite/restart, final exata, contexto estrangeiro/hash errado
recusados, revogacao/descarte/pagehide limpos. Mobile390x844 sem overflow e
botao44px. Consentimento fechado inicial, nenhum upload. CSP connect-src none
permanece; um fetch diagnostico proposital foi bloqueado e produziu dois erros
de console exclusivamente dessa prova negativa, nao da importacao. Navegacao
limpa posterior e importacao nova verificadas sem erros de console.

Primeiro standard global chegou a100% e falhou em dois testes: contrato de
design exigia rolagem unica, corrigida removendo max-height/scroll interno do
novo painel, sem enfraquecer teste; piloto MCP real/injection retornou refused.
Suites isoladas passaram; causa dessa recusa nao estabelecida pelo traceback
(assert mostrava somente status). Assertion agora inclui somente result.reason
fixo, sem conteudo privado. Deadline/default runtime inalterados. Nova execucao
standard integral aprovada (7790 casos coletados; skips de plataforma/opt-in
na suite antiga, zero skips nas baterias novas). Nao dispensar a prova MCP ou considerar gate parcial
como fechamento.106 Web/MCP focados passaram apos correcao; browser mobile real
repetido com overflowY visible/maxHeight none, sem overflow horizontal ou erros
de console. Encerradas somente abas/servidores proprios, superficie humana intacta.
Logs ignored em .jarvis_runtime/test-evidence/mb230-standard-*
e artefatos browser em mb230-browser, todos sinteticos.

## Rollback

Nao selecionar pacotes/nao executar exportador e suficiente para desativar uso.
Remover painel/allowlist/aliases e campos aditivos em rodada auditada, preservando
Memory/eventos ja armazenados. Nao apagar dados canonicos ou repetir Core.
Proxima fronteira MB231 ready: conversa Web local com sessao autenticada, em item separado;
pacote offline nao e token/ticket/grant para ela.
