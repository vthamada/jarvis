# MB233/MB234 - leitura Web e inventario MCP

Apresentacao atual MB235 done local, gate standard global Windows aprovado:
final integral agora em disclosure acessivel, aberto por padrao e recolhido
somente apos parser/fences validos. Parser/protocolo deste recorte intactos.
Ver [runbook compacto](compact-local-conversation-web.md); comportamento
de final sempre visivel descrito abaixo registra a prova historica MB233.

Estado 2026-10-06: MB233 e MB234 done no recorte local; baterias focadas, provas
ponta a ponta e gate standard global Windows aprovados. MB234 desenvolvido
isoladamente em paralelo e aceito depois de MB233, WIP integrado 1 preservado.
Sem aceite de conta/modelo reais,
qualidade conversacional, nova prova Linux ou produto completo.

## Web - projecao readonly, final preservada

Startup nativo inalterado:

```powershell
.venv/Scripts/python.exe -m apps.jarvis_api --authorized --port 0
```

Opt-in do host e consentimento por consulta seguem [MB232](local-generative-analysis-web.md).
O painel nao habilita modelo. Nenhum protocolo v1/v2, Core, governanca, sintese
ou Memory mudou. Resultados v2 accepted/ALLOW podem exibir analise, premissas,
limitacoes e citacoes separadas, somente via textContent. Final canonica inteira
permanece visivel e exata; sem HTML/Markdown/links ativos, acoes, storage browser
ou request adicional. Transporte live declarado e injetado permanecem rotulados
sem verdade, identidade humana ou autoridade comprovadas.

Parser reconhece somente sufixo terminal literal MB229: marcador unico,
disclaimer exato, JSON ASCII e re-encoding canonico. Analise <=4000 codepoints,
ate8 premissas/8 limitacoes de512, ate4 quotes de512, total humano <=8000,
bloco literal <=64000 e final <=131072. Controles/formatacao Unicode invalidos
ou surrogates sao recusados conservadoramente na projecao. Citacoes apenas da
pergunta: input:sha256 UTF8, offsets por codepoint, quote exata e spans nao
sobrepostos. Hash local nao autentica origem. Falha remove somente projecao.
Epoch, sessao, ticket, query, final e todos os campos cercam callbacks tardios;
nova consulta, expiry, disconnect e pagehide limpam o painel. Parar espera
continua nao desfazendo Core ou Memory.

## MCP - snapshot autoral, sem bridge Core

```powershell
.venv/Scripts/python.exe -m apps.jarvis_console.readiness_mcp_cli --authorized --principal-ref operator://local --session-ref session://readiness --front-id F13 --format json --timeout-seconds 10
```

Principal/sessao sao labels readonly, nao autenticacao ou grants. Tool unica
read_product_readiness aceita somente front_id enum all/F01..F13/T01..T03.
Sem argumentos de script/path/servidor/inventario/scope/URL/conta; sem rede,
login/refresh/HTTP/OAuth. Modulos novos ReadinessBinding/FixedReadinessMcpClient
nao alteram o cliente fixture nem disfarcam seus labels como dados reais.

Servidor le somente docs/implementation/product-readiness.json <=131072 bytes,
reusando load_inventory/validate_inventory/build_report. Referencias validadas
por existencia/contencao, nunca leitura de conteudo. Nenhum SQLite/token/store
humano. local_repository_snapshot, authored_snapshot, authority none,
runtime_verified=false e product_ready=false. Selecao individual preserva
contagens globais16, nao valida textos omitidos e exige contagem nao zero
para o estado da propria frente retornada.

Python absoluto -I -B, script fixo, shell=False, cwd temporario proprio,
ambiente somente SystemRoot e stderr descartado. Loader sibling fixo sem
reinserir cwd/PYTHONPATH. Higiene de processo nao e sandbox de SO; codigo
conhecido conserva direitos do operador. Nao configurar servidores terceiros.

Versao fixa2025-11-25: initialize -> notifications/initialized -> tools/list ->
tools/call, JSON-RPC UTF8/JSONL individual. Referencias oficiais:
[stdio](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports),
[lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
e [tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools).
Descriptor/version/schema exatos; structuredContent e JSON TextContent iguais.
Annotations nao concedem autoridade. Sampling/elicitation/roots/paginacao,
extras/duplicatas/tipos/ids divergentes e forjas recusados.

Snapshot <=24KiB UTF8, mensagem <=64KiB, agregado enviado+recebido <=256KiB;
ate32 requests/128 eventos, uma chamada por vez. Inteiro ou erro fixo, nunca
truncamento. Budget global de coleta0.01..10s inclui handshake/list/call/validacao,
nao deadline rigido de SO para spawn/FS/reap. Cancelamento cooperativo/notificacao,
close stdin, espera/terminate/kill e reap proprio, sem retry. Eventos/metadata
nao incluem prosa/argumentos/principal; erros CLI fixos. Nenhum consumidor deste
snapshot no Core. Nao disfarcar origem local como HTTPS/reviewed source nem
usar MCP como permissao. Bridge governada exige aceite posterior proprio.

## Provas desta rodada

145 Node parser e 33 DOM novos; Web1008/zero falhas/skips passou duas vezes.
8 Python Core real -> renderer -> JavaScript cobrem acentos/Unicode/markup/
linhas/limites/citacoes, restart exato e uma inferencia. 4 testes do harness
browser exigem opt-in/config antes de lancamento. MB234:159 novos (117unit/
42 stdio reais), 40 CLI unitarios e 3 CLI stdio reais. Bateria congelada de 217 passou
(214 Python novos +3 existentes do harness MB232). Standard global completo
aprovado com 8528 casos coletados, incluindo Web1008. Skips condicionais nao
sao provas de execucao. Apos sincronizar metadados, 311 focados, quick e CLI
textual real passaram. Sandbox Windows bloqueou numbered temp dirs do pytest;
runner proprio confirmado/encerrado e mesmos testes repetidos no host com
basetemp novo validado dentro do workspace, sem alterar assertions.

Chrome headless com perfil temporario, Core proprio e transporte injetado:
final3298 codepoints e SHA256 identico ao export canonico apos parar instancia;
projecaocitacao, reload/GET com unico POST generativo, consulta seguinte nativa
sem projecao, disconnect sem conteudo. Mobile390x844 sem overflow/scroll interno/
botoes abaixo44px, zero pageerrors. Runtimes/screenshot preservados em
.jarvis_runtime ignorado por Git. Ferramentas visuais do app tiveram timeouts;
tentativas nao contadas. Chrome instalado/Playwright bundled usados somente
no harness opt-in, sem dependencia central. Nao usar perfil humano.

Auditoria encontrou import sibling incompativel com -I, contagem selecionada
contraditoria e stdout fora do tratamento de falhas; corrigidos com testes
sem relaxar isolamento. Seis testes cobrem reconfigure/write com BrokenPipe,
OSError e UnicodeError, sem refletir detalhes no diagnostico. CLI real leu o
inventario sem Core/conta. Tentativa propria no sandbox presa teve PIDs exatos
confirmados/encerrados, nenhuma sessao humana. Node sem SystemRoot falhava antes
do harness Windows: corrigido somente ambiente minimo, assertions mantidas.

Sem banco humano, modelo/rede externos, mic/TTS, commit/push ou capability
promovida. Prova Linux MB218/219 nao valida automaticamente mudancas posteriores.

## Desativacao

Web: retirar projecao/asset, mostrar final integral e preservar v1/v2/auth/Memory.
MCP: nao invocar client/CLI, encerrar subprocess proprio e preservar inventario.
Ownership/aceites/proximos recortes permanecem na fila unica de execucao.
MB235 ready prioriza ergonomia Web, nao altera este parser nem o consumidor MCP.
