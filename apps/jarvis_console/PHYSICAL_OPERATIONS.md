# MB218: fronteira de operacao fisica

`PhysicalOperationsConsole` recebe Orchestrator composto explicitamente,
operador e canonical user fixados pelo builder. Nao abre API, escolhe roots,
ativa registries ou autentica uma pessoa. `physical_bootstrap.py` e o CLI
pertencem ao coordenador; este modulo utiliza os servicos reais de Governance,
Memory, Operational, Observability e o coordenador de saga MB217.

## API e separacao

```python
console = PhysicalOperationsConsole(
    orchestrator, operator_identity_ref, canonical_user_ref,
    runtime_dir=private_request_directory,
)
prepared = console.prepare(
    mission_id=mission_id, work_item_ref=work_item_ref,
    artifact_ref=artifact_ref, resource_ref="text:notes/note.txt",
    desired_text=desired_text, session_id=session_id,
)
inspection = console.inspect(prepared["request_id"])
exact = {
    "challenge_id": prepared["challenge_id"],
    "action_fingerprint": prepared["action_fingerprint"],
}
confirmed = console.confirm(prepared["request_id"], **exact)
authorization = {**exact, "confirmation_receipt_id": confirmed["confirmation_receipt_id"]}
outcome = console.execute(prepared["request_id"], **authorization)
status = console.status(prepared["request_id"])
console.close()
```

`prepare` so cria preflight/attestation, grant condicionado e challenge. Nao
confirma, reserva saga, escreve alvo ou registra uma versao canonica. Preview
e sensivel e efemero: o retorno e exclusivamente para inspecao humana, nao logs.
`confirm` gera receipt sem executar; `execute` exige o mesmo request/challenge/
fingerprint e receipt separadamente, e nao confirma implicitamente.

`replace_text` exige `supersedes_artifact_ref` normalizado, mission/workitem/
resource/lineage coerentes, versao distinta e CAS do conteudo. Nao promove
artefatos logicos legados implicitamente. Canonical binding e hashed no
origin_request_id do intent imutavel de Governance: reseal do cache nao pode
mudar artifact/version/owner_mission/objective/workitem/lineage/revision.

## Persistencia e plataforma

`runtime_dir=None` indica input efemero em memoria, util para preparar/testar
no Windows. Nao promete restart ou recovery dessa preparacao. Store duravel
so esta disponivel no Linux: diretorio dedicado 0700, arquivos regulares
single-link 0600, owner atual, descritor pinned, O_NOFOLLOW, writes com fsync
e replacement atomico. Nenhum runtime store sensivel e criado no Windows.

Toda gravacao, inclusive a inicial, passa por arquivo temporario privado e
fsync antes da publicacao. A publicacao inicial nao sobrescreve um request
existente; a substituicao continua atomica. Falhas sincrônicas de write/fsync/
publicacao limpam o temporario sem trocar o registro anterior por bytes parciais.
Terminacao abrupta do processo ainda pode deixar um orphan privado: nao ha
varredura automatica de arquivos nem promessa de apagamento seguro. Se o fsync
do diretorio falhar depois da publicacao, o resultado e ambiguo e exige inspecao;
nao se deve apagar ledgers ou emitir confirmacao alternativa.

Na publicacao inicial por hard-link, crash antes de remover o staging pode
deixar o request com dois links; load recusa single-link violado em vez de
confiar no registro. Preservar evidencia e investigar o staging privado, sem
varredura/limpeza automatica ou retries que sobrescrevam o request existente.

## Fronteira canonica de primeiro efeito

O bootstrap vincula `memory.artifact_physical_effect_scope` ao Operational.
Scope SQLite revalida missao/workitem/objetivo/owner canonicos depois de staging
e antes da primeira claim, serializando writers ate efeito/receipt. Libera
antes do callback Memory; nao escrever/pausar Memory dentro desse scope.
Repository sem scope suportado falha fechado. Recovery historico deriva de
journal e claim consumida exata, nunca de flag da UI; pausa nao desfaz efeito
ja iniciado. Detalhes/TCB em `docs/security/mb219-threat-model.md` e na rodada
`docs/operations/parallel-wave-physical-boundary-and-task-evals.md`.

O CLI le o desired-file por descritor e valida objeto regular single-link,
limite de 256 KiB e UTF-8, recusando ancestors redirecionados/reparse points.
No Linux, O_NOFOLLOW/O_NONBLOCK impedem seguir symlink final ou bloquear em FIFO
trocado durante abertura. No Windows, flags binarios preservam os bytes de
entrada e a superficie segue prepare-only; prechecks nao sao sandbox contra
processo hostil do mesmo usuario. Refusas precedem criacao de runtime e sao
redigidas sem texto privado, paths de source ou detalhes de excecao.

O store guarda o **input do operador**, inclusive desired_text em claro, e
metadata/ref de request/challenge/plan. Ele nao e memoria canonica ou ledger
de autoridade. Esse input e sensivel: backups/transferencias precisam manter
protecao; fingerprints nao sao anonimização. Store nao serializa contratos
de preflight/request efemeros, diff, preview ou bytes antigos do alvo.
Reconstrucao do request carrega autoridade/attestation do ledger Governance;
Operational faz fresh read e exige fingerprint exato antes de execucao.

Identidade configurada e persistida por request e comparada ao intent. Owner
mission/objective/workitem/lineage sao verificados contra Memory. O campo
legado `MissionStateContract.owner_context` nao e persistido pelo repository
atual: seu guard opcional e apenas in-process, nao prova novo ownership humano
duravel. Este slice nao corrige/expande esse contrato de Memory.

Execucao/rollback/recovery exigem Linux e engine fisica opt-in antes de reservar
saga. Windows failclosed nao constitui evidencia fisica Linux. Status e
historico canonico/journal, nao attestation fresca de que um humano nao editou
o arquivo depois: `physical_state_verification=not_performed_by_status`.
Expiracao e exibida como challenge_state; status nao renova grants.

Se Governance persistiu a confirmacao, mas o processo caiu antes de atualizar
o request cache, status/inspect reconciliam somente o receipt ja existente,
verificando intent, challenge, operador e fingerprint exatos. O estado passa
a confirmed por evidencia persistida, nao por nova confirmacao. Nao se emite
outro receipt, renova validade ou consome claim. Confirm repetido permanece
recusado; usar o receipt apresentado por status. Falha ao salvar a reconciliacao
permanece fail-closed e pode ser retomada sem alterar o ledger.
Mesmo quando o cache ja tem um receipt ID, status e autorizacao revalidam
receipt/challenge/operator/action fingerprint exatos contra Governance; um ID
presente no cache nao dispensa esse binding.

## Rollback e recovery

`prepare_rollback(apply_request_id, session_id=...)` cria request/intent/grant/
challenge independentes a partir de receipt Governance e head normalizado.
`confirm_rollback` e `rollback` exigem seus proprios IDs/receipt; confirmacao de
apply nao serve para rollback. Hashes/target/resumo sao inspecionaveis sem ler
backup sensivel. Rollback canonico exige predecessor: initial v1 nao tem
predecessor canonico e e recusado neste console. Compensacao precanonica e
uma responsabilidade de recovery/saga, nao exclusao automatica de v1 ativo.

`recover` exige exatamente a autorizacao da saga iniciada; nao cria challenge
novo. Depois do efeito, usa journal e receipts historicos. Antes da dispatch
efetiva usa request reconstruido (se ainda valido). Apenas erros exatos
`local_text_transaction_journal_missing` e, no rollback anterior a sua reserva,
`local_text_rollback_request_required_before_journal` permitem retry original
antes da materializacao fisica. O segundo exige journal fonte receipt/cleaned
sem metadata de rollback, plano/source receipt exatos e receipt Governance
persistido. Journal da mutacao nao concede autoridade historica de rollback;
tamper, expiry e outras falhas nunca viram retries livres.
Esse fallback revalida missao ativa, work item ativo/desbloqueado e objective
original antes de reconstruir qualquer request. Uma missao pausada ainda pode
reconciliar journal historico existente, mas nao iniciar efeito sem journal.
Callback canonico/lease one-shot permanecem no MB217. `execute` repetido apos
reserva e recusado: usar `recover` explicitamente.

## Testes, observabilidade e limites atuais

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_physical_operations_console.py tests/unit/test_physical_bootstrap.py tests/integration/test_physical_cli.py tests/integration/test_physical_operations_console_integration.py
```

Preparacao/inspecao/confirmacao Windows usam servicos e preflight reais,
sem efeitos. Corpus Linux cobre durable restart, create/replace/rollback,
crash antes de canonical commit ou journal com missao pausada,
tamper/permissoes/hardlinks e edicao humana;
falhas injetadas de fsync/publicacao do request store e criacao sem overwrite;
skip Windows e explicito e nao conta como prova fisica. Gate global e docs de
estado sao coordenados pelo integrador. Em 2026-10-05, o corpus final em volume
ext4 passou (224 passed/5 skips exclusivos de Windows), com seis fases CLI entre
containers, pausa concorrente por processo e seis falhas storage/reload reais.
Gates release Linux/standard Windows passaram. MB218/219 tecnicamente fechados
somente no escopo local Linux/SQLite opt-in. Evidencia e limites:
`docs/operations/mb218-mb219-persistent-readiness-2026-10-05.md`. Nao prova
power-loss/reboot do host/controlador, nao autentica humanos nem abre API mutante.

Eventos de challenge/confirmacao usam allowlist content-free: ID gerado,
purpose, action fingerprint e marcador contains_content=False. Nao contem
source, diff, path absoluto, user text ou mensagens de excecao. Execucao e
lifecycle/outbox continuam emitidos pelo runtime real. Nenhum evento novo
compartilhado foi criado. Em falha de store apos receipt persistido, preservar
ledgers e input para reconciliacao por status: nao inventar confirmacao alternativa.

Rollback de software: desregistrar/desligar os comandos mutantes mantendo
store/journal/ledgers para status/inspecao/recovery; nao apagar dados humanos.
