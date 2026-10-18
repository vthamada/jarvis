# Prazo de leitura e jobs de fixture Docker

Rodada independente 2026-10-14, implementacao local/gate aprovados; confiabilidade
da CLI ainda inconclusiva (abaixo). MB236 continua `blocked`;
F02 continua `partial`, F05/F11 `foundation`. Nao ha nova inferencia, login,
publicacao, geracao de codigo ou aplicacao de patch. Este recorte nao e um
executor generico nem promove capability. Ownership e aceite ficam na fila
[execution backlog](../implementation/execution-backlog.md).

## Leitura de memoria

O objetivo e aplicar o mesmo prazo monotonic de cinco segundos da revisao
de retencao tambem a conexoes e consultas SQLite. O caminho segue readonly,
sem inicializacao ou migracao de schema, sem WAL e sem politica de apagar,
arquivar ou consolidar memoria. Chamadores antigos sem deadline mantem seu
comportamento. Scope continua fornecido pelo chamador, nao autenticacao.

SQLite progress handler permite interromper a VM de uma consulta longa;
lock wait precisa usar somente o prazo restante. Isso nao e garantia de
tempo real ou preempcao de syscall/I/O do sistema operacional. Erros,
cancelamento ou expiracao descartam resultados parciais e fecham conexoes.

## Jobs das provas Docker

O objetivo e registrar e executar explicitamente uma unica fixture fixa pelo
ledger existente, com CAS/fencing, scope e binding exatos. Somente baseline,
candidate, isolation e timeout existentes; nunca codigo, imagem, comando ou
repositorio arbitrario. A identidade da fixture nao concede grant do Core.

Ledger e Docker sao duas transacoes distintas: nao ha exactly-once de efeito,
commit atomico ou autorizacao para replay. Estado `running` abandonado deve
exigir revisao, nao repetir trabalho. Sucesso requer evidencia fresca valida
do runner, cleanup confirmado e claim ainda valido. Baseline aprovado significa
observar tres falhas esperadas, nao tres testes verdes. Estado terminal no
ledger nao e por si uma prova persistida de execucao ou isolamento.

O worker de fixtures de metadados nao pode executar esses novos tasks. Nao ha
scheduler ou polling, nem ativacao no Core, API ou Web. O runner Docker segue
imagem pinada/pull-never, sem rede/host mounts, non-root/rootfs readonly e
cleanup apenas de seu container identificado. Nao alterar dados de terceiros.

Piloto standalone, com ledger temporario exclusivo, reabertura local e descarte
somente do proprio runtime temporario ao terminar:

```powershell
python -m apps.jarvis_console.code_fixture_job --authorized --scenario candidate
```

Nao cria ledger duravel de producao. A classe `CodeFixtureJobRunner` pode ser
composta explicitamente com `SqliteJobStore` local: registre `JobSpec` com
`task_ref=code-fixture:<scenario>`, responsabilidade `code-fixture-pilot`,
`max_attempts=1` e `CodeFixtureInput.step_ref`. Esse binding e checado antes
da aquisicao e rechecado ao validar claim. Uma sessao/ref fornecida nao e
autenticacao humana; executar somente com autorizacao local explicita.

Uma prova fresca aceita aparece em `fixture`; apos restart, estado historico
tem `result_accepted=false`/`fixture=null` e nao repete Docker. A evidencia
fisica nao e persistida no schema do ledger (`physical_proof_persisted=false`).
Leitura de atividade continua `evidence_mode=fixture`, nao implica prova atual
nem muda contrato de painel/API. `needs_decision` nao concede retry ou grant.
O timeout do runner e por subprocesso; lease de120s e margem de35s preservam
espaco para preflight/cleanup, sem promessa de tempo real. Expiracao/CAS invalido
ou cancelamento observado tornam a recusa permanente nesta tentativa.

## Evidencia e rollback

Primeiro standard desta rodada falhou (abaixo); novo standard passou.
Gate anterior nao valida este recorte.
RED Code: modulo ausente; RED memoria:26 failed/1 passed, incluindo consulta
real que percorreu1.000.001 passos antes da verificacao. A primeira invocacao
de memoria teve27 erros de setup por permissao de temporarios no sandbox Windows;
escalacao limitada a fixtures proprias permitiu reproduzir o RED de runtime.
Primeira bateria Code305 passed/6 skipped; apos hardening121 passed/4 skipped.
Primeira bateria memoria291 passed/1 skipped/2 failed: dois processos CLI
excederam20s. Isolados, passaram em3.65s/3.36s sem alterar budget do produto ou
timeout do teste. Causa desses dois timeouts nao comprovada; nao classificar
como corrigidos, preexistentes ou aceite por mera repeticao. Campanha serial
fresca passou51 casos em46.83s, sem skips; gate integrado ainda necessario.
Code hardening/compatibilidade121 passed/4 skipped em10.13s. Campanha fisica
opt-in executou os quatro jobs em17.62s:4 passed/2 deselected; cleanup e
restart/succeeded confirmados. Inspecao readonly final dos containers rotulados
como code-fixture retornou vazio/exit0. Nao houve pull/build ou remocao de
recursos de terceiros. Revisao readonly aprovou os seams,
apos corrigir latch de cancelamento e revalidacao de binding apos claim.

Primeiro standard Windows:9801 casos,9674 passed/119 skipped/8 failed/0 errors,
exit1 (coleta e marcadores -qq). Nenhuma falha dos novos slices F02/F05/F11.
Sete casos de `test_core_binding_and_grant_drift_cannot_be_attested` retornaram
DID NOT RAISE; `test_canonical_subject_is_consistently_bound_to_memory`
recebeu refused. Razoes originais nao capturadas, nao afirmar causa dessas8
falhas nem aceite de binding adulterado. Isolados sem correcao:9 passed,
oito core_final_binding_refused e uma final completed, em6.58s; uma warning
de assert rewrite no processo de instrumentacao, sem mudanca de runtime.

Reproducao controlada do teste antigo change0: clock SOMENTE do modulo
avancado para4s apos construir Core real, com cliente/asyncio/UTC naturais.
Reproduziu DID NOT RAISE, reason report_entry_cancelled_or_expired e zero
handle_input. Isso comprova que o teste misturava entrada expirada com
attestation, nao a causa exata dos resultados originais. Ajustes apenas no
harness: clock de entrada isolado nas duas verificacoes de binding; drift
agora exige marcador de mutacao real apos replace/handle, e canonical_subject
exige exatamente uma captura efetiva. Coleta do negativo usa10s ja permitido;
default3s/teto/clientdeadline/cancelamento/runtime/UTC intactos.

Novo corpus dois casos reais stdio/Core-build documenta que entry expiry
recusa antes de handle, sem memoria final. Focados e reexecucao standard
apos esses ajustes:176 passed em63.57s. Reexecucao oficial standard Windows
com parada na primeira falha (`-x`, sem mudar selecao/skips/budgets) terminou
exit0:9803 casos,9684 passed/119 skipped/zero failed/errors. Contagem integral
dos marcadores -qq confirma que o fail-fast nao omitiu casos no resultado
aprovado.13 hashes de runtime/corpus preservados antes/depois. Nenhuma
mudanca de runtime MCP, conta, modelo ou promocao macro.

Verificacao CLI extra via `python -m`: candidate foi recusado, job
needs_decision/attempts1, fixture=null, sem prova aceita ou replay. Razao do
runner nao capturada nesse produto reduzido; causa original nao comprovada.
Inspecao readonly subsequente confirmou daemon/imagem e nenhum container
code-fixture remanescente. Uma tentativa diagnostica adicional em OUTRO job
temporario, invocando a mesma main com wrapper somente observador, passou
em3.27s: candidate3 testes, cleanup/execution_started true e restart succeeded.
O wrapper registrou apenas status/reason/flags sanitizados, sem mudar resultado.
Isso nao corrige nem explica a recusa original. Mecanica/provas locais e gate
aprovados; disponibilidade/confiabilidade CLI sob carga continua inconclusiva,
nao promover por repeticao. Sem aumentar timeout, retry automatico ou repair.

Pos-sincronizacao documental:296 consumidores inventario/contratos/CLI/MCP
stdio passaram em40.45s, zero skips. Quick final (encoding/documentos/Ruff)
e diff-check aprovados. Inspecao readonly final de containers code-fixture
retornou vazio/exit0. Nenhum container proprio remanescente ou publicacao.
Teste fisico requer opt-in; skips do gate global nao contam como execucao.
Rollback operacional: nao invocar o novo piloto/runner e nao configurar prazo
nos chamadores existentes. Nenhum componente e ativado automaticamente.

Faltam retencao governada real, tarefas uteis governadas com aprovacao e
operacao duravel, e brief/geracao/teste/review/aplicacao autorizada de codigo.
