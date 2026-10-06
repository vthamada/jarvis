# Job service: WP-JOBS-01 isolated ledger and explicit Core pilot

## MB221: inspecao readonly

`job_service.readonly.build_job_inspection`/console `job-inspect` consultam ate32
jobs exatos em ledger absoluto existente/quiescente, sem criar/migrar Core/store,
reconciliar lease, worker ou replay. mode=ro/query_only, transacao unica,
schema/linha/fingerprint validados; scope actor/session de todos IDs ou recusa.
Metadata default, refs opt-in; binding nao autentica. Path checks trusted-host,
nao sandbox por descritor. [Uso/limites MB221](../../docs/operations/parallel-wave-transport-transcript-and-job-inspection.md).

Base duravel SQLite de metadados, CAS e fencing. Nao ha scheduler, thread,
processo, rede, executor generico ou dispatch de ferramenta. Construir/reabrir
o store nunca executa nem retoma automaticamente qualquer step.

## API local

- `JobSpec(job_id, actor_ref, session_ref, responsibility_ref, approved_step_ref,
  task_ref, deadline, max_attempts=3)`: refs limitadas, deadline datetime aware
  UTC e ate dez tentativas. Nao aceita payload livre.
- `SqliteJobStore(path, clock=...)`: uma base explicita, conexoes fechadas por
  operacao, schema local v1. Relogio e infraestrutura confiavel.
- `register(spec)`: idempotencia por ID+fingerprint integral; conflito nao
  sobrescreve o trabalho existente.
- `get(job_id, actor_ref=..., session_ref=...)`: escopo exato.
- `claim(..., worker_id=..., expected_version=..., lease_seconds=30)`:
  `JobClaim` ou `None` se nao elegivel. BEGIN IMMEDIATE serializa writers;
  toda claim aumenta attempts/version/fencing e lease nunca excede deadline.
- `finish(claim, outcome)`: exige claim exata ainda vigente, mesmo worker,
  actor/session, fencing/version e lease; outcomes enumerados somente.
- `cancel(..., expected_version=...)`: revoga claims/fencing inclusive running.
- `retry(..., expected_version=...)`: somente failed, budget restante e
  deadline vigente; nao executa, nao zera attempts e nao libera needs_decision.
- `FixtureJobWorker(store, worker_id).run_once(...)`: chamada explicita de um
  step fixture: success, failure ou needs_decision. Sem callbacks executaveis.

Os actor/session sao bindings, nao autenticacao. Refs de responsabilidade e
step aprovado sao metadados vindos de um chamador autenticado pelo Core, nao
comprovantes verificados de aprovacao e nunca grants. O worker inicial aceita
apenas `fixture:success`, `fixture:failure`, `fixture:needs_decision`.

## Recovery e evidencia

Lease expirada permanece visivel ate nova chamada explicita claim/run_once.
Reclaim troca fencing e consome tentativa; deadline/budget esgotados reconciliam
para expired/failed sem execucao. Worker antigo nao pode finalizar depois de
reclaim/cancel. Needs_decision permanece parado; revisao humana/resume real e
slice futuro. Cancelar nao desfaz efeitos anteriores.

Lease de job nao e lease one-shot MB217 e nao concede autoridade fisica.
Nao ha garantia exactly-once generica: efeito externo sem receipt/idempotencia
requer reconciliacao propria. Telemetria de tasks fixture permanece fixture;
task Core usa metadata_ledger e piloto distingue core_local. Status/contagens/
codigos sao enumerados, sem conteudo, credenciais ou payload no ledger.
Runtime de producao, scheduler, notificacoes e executor real exigem gates e
permissao fresca de cada acao; nao sao capacidades promovidas neste slice.

```powershell
.venv/Scripts/python.exe -m pytest services/job-service/tests
```

Testes cobrem register -> claim -> fixture -> finish, writers concorrentes,
CAS/fencing, cancelamento, stale claim, retries limitados, deadlineUTC, restart
sem autoexecucao, host offline e isolamento actor/session. Desativar e retirar
o worker da composicao, preservando o ledger; nao apagar registros humanos.

## Piloto explicito de Core (`core:assist_only`)

`apps/jarvis_console/job_pilot.py` compoe o store com um `OrchestratorService`
real, somente em runtime SQLite temporario. O tipo de tarefa fechado foi
adicionado para distinguir evidencia real de Core de outcomes fixture; o
`FixtureJobWorker` recusa essa tarefa antes de claim. Nao ha callable livre,
scheduler, integracao autenticada de producao ou execucao de ferramentas.

O corpus fechado contem somente `acknowledgement` e `arithmetic`. O binding
exige actor/session exatos, responsabilidade `core-assist-pilot`, digest SHA256
do texto em `approved_step_ref` (`input-<hex>`) e `max_attempts=1`. Estes refs e
digest nao autenticam o operador nem comprovam aprovacao; sao integridade de
composicao local, nunca grants. O Core recebe `assist_only`, escopo vazio e
nenhum receipt. Eventos persistidos de governanca/sintese/memoria e turno
canonico exato sao verificados antes de registrar resultado no ledger.

Somente governanca `allow` pode registrar `succeeded`; block, defer e conditions
permanecem `needs_decision`, sem presumir condicoes cumpridas. `result_recorded`
significa resultado canonico registrado no ledger, nao sucesso/autoridade.
`canonical_final_verified` pode continuar verdadeiro depois de cancel/pausa,
pois a memoria canonica ja pode estar persistida. Nao se aceita sucesso do job
depois de fencing invalido, e o final nao e substituido para caber no executor.

`pause` revoga a claim e deixa `needs_decision`, sem resume automatico. Ela e
cooperativa no ledger: nao interrompe retroativamente o Core nem desfaz memoria.
Uma claim Core iniciada e expirada tambem exige revisao; nao pode ser reclamada
ou retry. Falha/crash entre persistencia de memoria e finish nunca dispara replay.
Abrir novamente o store nao executa nada. A transacao job + memoria/eventos
nao e atomica e nao ha garantia exactly-once cross-ledger. Recuperacao humana
autenticada e reconciliacao sao escopo futuro, nao exercido pelo piloto.

CLI exige `--authorized` explicito antes de ler stdin ou construir runtime;
API exige `authorized=True`. Corpus de runtime e em ingles.
TEMP resolvido dentro do workspace e recusado antes de criar qualquer runtime;
o diretorio base validado e passado explicitamente ao criador do temporario.
O `user_id` e
coerente com o actor; a sessao canonica deriva do par actor/session para evitar
compartilhamento acidental entre dois principals com mesmo ref de sessao.
CLI le o case por stdin (sem texto/conteudo em argv); stdout exporta apenas
status, contagens, codigos, request/memory IDs e flags. O runtime e removido no
fim; nenhum banco humano ou credencial e aberto. Default sem stdin seleciona
`acknowledgement` somente com opt-in; para uma entrada explicita:

```powershell
'{"case":"arithmetic"}' | .venv/Scripts/python.exe -m apps.jarvis_console.job_pilot --authorized
.venv/Scripts/python.exe -m pytest services/job-service/tests tests/integration/test_job_core_pilot.py
```

E2E executa Core real + SQLite e verifica cancelamento, pausa e lease expirada
depois de memoria persistida, excecao pos-commit, final adulterado, isolamento de
input/principal/sessao e restart sem replay. Nao promove jobs persistentes de
producao, notificacoes, escalonamento ou autoridade externa. Rollback: remover a
composicao opt-in mantendo o ledger; dados antigos fixture continuam schema v1.
