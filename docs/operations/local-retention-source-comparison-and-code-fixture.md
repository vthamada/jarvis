# Memoria, fontes e fixture Linux locais

Recorte independente do MB236, 2026-10-13. F02/F03 continuam `partial` e
F11 `foundation`; ultimo MB validado MB235, MB236 `blocked`. Nenhum modelo,
refresh, credencial, conector externo ou publicacao faz parte desta rodada.
Plano de ownership e aceite em [execution backlog](../implementation/execution-backlog.md).

## F02: revisao de retencao, sem aplicar politica

`memory_service.retention_review.build_retention_review` produz um plano
imutavel sobre `StoredTurn` e `RecallScope`. Idade, estado declarado, expiry
e supersessao explicita sao sinais para revisao, nao decisoes de apagar,
arquivar, consolidar ou revogar. A politica canonica existente e o Core
continuam soberanos. Componentes de correcao ambiguos e timestamps
desconhecidos/futuros sao retidos para decisao, sem promover supersessao.

CLI standalone, opt-in, sobre banco canonico existente e quiescente:

```powershell
python -m apps.jarvis_console.memory_retention_cli --authorized --memory-db C:\JarvisPrivate\memory.sqlite --subject-id <canonical-subject> --session-id <selected-session> --as-of 2026-10-13T12:00:00Z --max-age-days 30
```

Use caminho real absoluto do banco autorizado; o exemplo nao cria banco.
Sujeito e sessoes sao labels fornecidos pelo chamador, nao autenticacao humana
ou grant do Core. Limites: 1..32 sessoes explicitas, ate100 turnos no total,
horizonte1..366 dias, JSON64KiB e deadline cooperativo5s. Desde2026-10-14,
o mesmo prazo inclui VM/lock SQLite; veja
[prazo/jobs](memory-deadline-and-code-fixture-jobs.md). Selecoes maiores
sao recusadas integralmente, nao truncadas. A origem precisa existir em modo
SQLite DELETE sem journal ativo/WAL, sem symlink/reparse/hardlink. Verificacao
de identidade antes/depois detecta mudancas; nao e sandbox de descritor nem
preempcao de I/O do SO/UDF bloqueante. Historico misto de sujeito e scope estranho
sao recusados antes da publicacao.

Saida por padrao: enums, contagens, idades e hash do plano; sem textos,
sujeito, sessao ou refs. `--include-refs` libera somente refs canonicas
derivadas para revisao consciente. Hashes sao consistencia/pseudonimos,
nao anonimizacao, autenticacao de origem ou autorizacao de aplicar o plano.
Erro/cancelamento/budget descarta parcial. CLI retorna exit2 e diagnostico
fixo `memory_retention_refused`. Nao escreve ou migra memoria/eventos.

## F03: comparar trechos fornecidos

`knowledge_service.source_comparison.build_source_comparison` aceita
`jarvis-source-comparison-input-v1`, envelope exato com `schema_version`,
`as_of`, `sources` e `claims`. Fontes usam o contrato local de pesquisa:
`source_ref`, `text`, `observed_at`, `expires_at`. Claims usam `topic_ref`,
`source_ref`, `start`, `end`, com offsets Unicode originais/end exclusivo.
Limites: UTF-8 JSON64KiB, ate16 fontes,32 claims e512 caracteres por trecho.
Nenhum fetch, crawl, modelo, persistencia ou despacho Core.

```powershell
Get-Content -Raw -Encoding UTF8 <authorized-input.json> | python -m apps.jarvis_console.source_comparison_cli --authorized
```

Arquivo local precisa ser escolhido/revisado pelo operador. Saida
`jarvis-source-comparison-v1` por padrao tem somente metadados/hashes, sem
refs literais/quotes. `--include-content` opt-in mostra trechos elegiveis
exatos e origem declarada nao verificada. Renderer pode reter integralmente
trechos sensiveis; nunca editar quote sob hash antigo. Entrada duplicada,
invalida ou grande e recusada, exit2/`source_comparison_refused`, sem refletir
conteudo privado em erro.

`matching_text`, `text_disagreement`, `insufficient_evidence` classificam
texto exato, nao verdade ou contradicao semantica. Copias integrais identicas
nao contam como duas fontes; conteudos diferentes tampouco provam origens
independentes. Datas sao declaradas; fonte futura/expirada nao fornece quote
elegivel. Expiry desconhecido permanece `unknown`, nunca `current`.
Instrucao embutida em fonte continua dado sem autoridade. Todas as saidas
mantem `facts_verified=false`, `authority=none` e revisao humana obrigatoria.

## F11: prova fisica de programas fixos, nao executor generico

`tools/run_code_fixture_linux.py` aceita somente `baseline`, `candidate`,
`isolation` ou `timeout`. Nao aceita codigo, comando, imagem ou repositorio
do usuario. Imagem local ja existente, Linux amd64, pin imutavel:
`sha256:06227a71f8091cae6663926523eeab05c4b5f976ffcc8a293854b38a1d00c7ac`.
Sem pull/build/download, host mounts, env privada, rede ou acesso a conta.

```powershell
python tools/run_code_fixture_linux.py --authorized --scenario candidate
```

Container proprio: non-root65534, rootfs readonly, network none, caps dropALL,
no-new-privileges, pids32,256MiB,1CPU, tmpfs8MiB noexec. Python `-I -B` executa
somente fixture literal. Configuracao e ownership sao checados antes de start;
stdout/stderr cada um ate4KiB, timeout0.1..30s e cancelamento cooperativo.
Stop/rm somente por ID confirmado com nonce/purpose/nome/imagem proprios;
ausencia precisa ser confirmada. Ownership alterado preserva alvo e sinaliza
cleanup nao confirmado; nunca prune/cleanup de terceiros.

Baseline `a-b` deve falhar seus3 testes; candidato `a+b` deve passar os3.
Baseline `status=passed` significa observar exatamente a falha esperada,
nao testes verdes. Isolation tem5 checks locais de uid/rootfs/routes/ausencia
de marker; marker nao montado e esses checks nao provam sandbox adversarial
generico. Timeout usa loop literal e precisa provar alvo iniciado/ainda
executando no deadline, seguido de cleanup. Metadata/protocolo invalidos ou
cleanup inconclusivo nunca sao prova positiva. JSON exposto nao contem
stdout/stderr bruto, comando, caminho privado ou codigo.

Prova fisica E2E e explicitamente opt-in, para nao executar Docker no gate
global por acidente:

```powershell
$env:JARVIS_CODE_FIXTURE_TEST_AUTHORIZED = 'yes'
python -m pytest tests/integration/test_code_fixture_linux_real.py
Remove-Item Env:JARVIS_CODE_FIXTURE_TEST_AUTHORIZED
```

## Evidencia e lacunas

Dois implementadores com arquivos disjuntos, revisor independente readonly,
integracao, CLIs, testes reais e gates executados pelo coordenador. RED de
modulos/CLIs ausentes confirmado antes das implementacoes. Bateria final
F02/F03/CLIs:120 passed, com SQLite canonico sintetico/restart, scope/101turnos,
mutacao de identidade, pipes reais/UTF-8/duplicacao/65,537bytes e preservacao
de banco/eventos. O teste grande inicialmente falhou no setup pelo ID de
caso enorme; IDs curtos corrigiram o teste sem reduzir o limite ou a recusa.
Mais1 teste de historico misto antigo passou;43 unitarios F11 passaram.
Revisor encontrou; implementador corrigiu cleanup em interrupcao/spawn incerto, timeout
do cliente confundido com alvo e binding de script/cwd. Primeira campanha
fisica4falhas recusou antescreate: Docker omite Volumes vazio no template.
`index` para campo opcional corrigiu a causa comprovada, mantendo recusa de
volumes declarados. Ownership-only separado permite cleanup mesmo quando
config template falha, sem promover evidencia. Preflight timeout e uma
criacao inconclusiva posteriores nao contam como prova positiva; nenhum
alvo encontrado na inspecao do nome proprio dessa criacao. Candidato novo
completo passou3checks/cleanup; campanha final E2E4cenarios passou em20.42s,
todos cleanup verificados. Primeiro standard Windows terminou exit1:
9701 casos,9583 passed/115 skipped/3 failed/zero errors (marcadores -qq).
Dois positivos MCP recusaram report_entry_cancelled_or_expired com budget3s;
teste funcional agora usa10s ja permitido, sem mudar runtime/default/deadline.
Terceiro caso de drift teve DID NOT RAISE, sem reason capturado; isolado passou,
nao comprova aceite de timestamp adulterado. Teste de attestation agora isola
somente o clock de entrada do modulo e exige mutacao SQLite efetiva antes da
recusa especifica. Clock global/cliente/asyncio/UTC e controles de expiry reais
preservados. Revisao readonly aprovada;174 MCP/canonicos/deadline passaram
em134.87s. Reexecucao standard Windows exit0/9701 casos:9586 passed/115 skipped,
zero failed/errors (coleta e marcadores -qq).15 hashes de runtime/corpus iguais
apos gate. Skips nao comprovam Linux amplo, voz ou qualidade de modelo; os4
cenarios Linux fisicos desta rodada foram comprovados separadamente.
Consumidores finais de inventario/contratos/CLI/MCP stdio:296 passed em23.13s,
zero skips. Quick final (mojibake/document guardrails/Ruff) e diff-check aprovados.
Uma invocacao anterior usou nomes de arquivos de teste inexistentes e nao
executou casos; nomes reais corrigidos antes da bateria final, sem alterar teste.

Codex Process Jobs0.5.0 indisponivel em win32, comprovado na rodada anterior
(exit1/sem job); fallback e terminal foreground do coordenador/gate oficial.
Skips, mocks e gates antigos nao comprovam execucao fisica desta rodada.
Rollback operacional: nao invocar os novos modulos opt-in; nada ativado no
Core, API ou Web por padrao, nenhum contrato central/capability promovido.
Faltam retencao/consolidacao governadas, pesquisa com sintese util/modelo
real e fluxo Code generico brief/geracao/teste/review/aplicacao autorizada.
