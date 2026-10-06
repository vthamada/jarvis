# MB219 — threat model da fronteira física governada

Data: 2026-10-04; revisao final: 2026-10-05. Recorte: console local opt-in, `create_text`, `replace_text`,
rollback independente e reconciliação de artifacts físicos MB217/MB218.
MB218/MB219 foram fechados tecnicamente no escopo local Linux/SQLite opt-in:
corpus persistente224 passed/5 skips exclusivos Windows, seis fases CLI entre
containers e gates release Linux/standard Windows aprovados. Auditoria nao
identificou bypass concreto. Readiness limitada: nao promove API, autenticacao,
executor Windows, PostgreSQL first-effect ou garantia de power-loss.
Evidencia: [campanha persistente](../operations/mb218-mb219-persistent-readiness-2026-10-05.md).

## Ativos e fronteiras de confiança

- Bytes do arquivo alvo e da versão predecessora, diretórios permitidos e suas
  identidades físicas; nenhum path fora dos roots declarados é autorizado.
- Intenção, preflight, challenge/confirmation, grant e claim da Governance.
  Conhecer um id, confirmar uma tela ou recalcular um hash não concede autoridade.
- Journal físico, backup privado, receipt exato, attestation efêmera sob lock,
  saga, linhagem e commit da Memory canônica; UI/cache não são fonte canônica.
- Input sensível no request store local: pode conter o texto completo solicitado.
  Status/eventos não devem expor esse texto. Preview/diff exige opção explícita.
- Relógio injetado e registries soberanos compõem a autoridade da operação.
  Nenhum timestamp fornecido pelo cliente deve substituir o relógio confiável.

O operador local pode cometer erros ou apresentar requests alterados/repetidos;
outro processo pode tentar trocar paths/arquivos entre inspeção e execução.
O modelo, a UI e dados lidos de arquivos são fontes não confiáveis de propostas,
nunca autoridades de escrita. O código do Core, adapters de autoridade,
registries, kernel/OS, relógio confiável e dono dos diretórios privados integram
o trusted computing base (TCB). Não há isolamento contra administrador do host
ou atacante com controle completo do mesmo UID e dos bancos privados.

## Política crítica: primeiro efeito não é reconciliação

`effect_dispatched`/`rollback_effect_dispatched` é checkpoint de saga, não prova
de claim físico. Journal apenas `reserved`/`staged` também não prova claim.
Uma operação sem claim histórico exato precisa validar novamente missão ativa,
objetivo, owner canônico e work item ativo/ready na fronteira do primeiro claim.
O precheck do console sozinho deixa uma janela entre inspeção e efeito.

Uma claim já durável e verificada deve ser reconciliada pelo journal e pela
Governance, mesmo após pausa ou expiração da autorização para novos efeitos:
não se emite nova claim para tornar o histórico válido. Essa distinção deve
ser derivada pelo kernel de evidência confiável, nunca de checkbox ou flag da UI.
Pausa precisa linearizar com o primeiro claim/efeito; não é garantia de abortar
uma execução física que já começou com autoridade durável válida.

Na implementação desta rodada, o modo é derivado pelo kernel, e o primeiro
efeito canônico usa `MemoryService.artifact_physical_effect_scope`: SQLite
`BEGIN IMMEDIATE` cerca escritores canônicos durante claim/efeito e libera a
guarda antes do callback de commit, mantendo o lock físico do recurso. O modo
histórico passado ao authorizer não é, sozinho, prova: exige validação do journal
e da claim pelo kernel. Não expor esse parâmetro em superfícies externas.
Repositórios sem implementação da guarda, inclusive o caminho PostgreSQL atual,
recusam primeiro efeito; nenhum mutex/no-op é fallback autorizado.
Tradeoff: a guarda SQLite serializa todos os writers desse banco Memory, não
somente a missão/linhagem alvo. Efeitos longos podem aumentar contenção; timeout
ou falha de lock deve negar efeito novo, não degradar para guarda vazia.

## Corpus e limites da evidência

Os caminhos abaixo são suites existentes ou novos testes coletáveis. A existência
de um teste não equivale a execução no backend físico suportado.
`tests/unit/test_mb219_kernel_modes.py` usa objetos/callbacks de fixture sem I/O
físico: testa a seleção `staged`/`rollback_reserved`, verificação exata da claim e
entrada/saída da guarda, inclusive falha. Não inicializa backend Linux fictício.

| Ameaça | Defesa e evidência auditável | Limite |
|---|---|---|
| Replay, receipt trocado, expiry | `services/governance-service/tests/test_action_confirmation_governance.py` (`test_confirmation_rejects_spoof_drift_expiry_and_replay`); `test_adapter_grant_governance.py` (`test_claim_is_exact_single_use_restart_safe_and_expiry_is_exclusive`); `test_adapter_execution_governance.py` (`test_joint_claim_is_atomic_idempotent_and_replay_safe`) | Histórico exato não é nova autorização; confirmar não executa. |
| Backdating/clock inválido | `test_adapter_execution_governance.py::test_tamper_and_backdated_paths_fail_closed`; `test_local_text_rollback_governance.py::test_trusted_clock_blocks_backdated_rollback_issuance`; `services/operational-service/tests/test_local_text_transaction.py::test_transaction_time_is_constructor_injected_and_invalid_clock_precedes_state_io` | Não garante relógio do host íntegro sob comprometimento administrativo. |
| Race e concorrência | Claims simultâneas em `test_adapter_execution_governance.py`; thread/process retries em `test_local_text_transaction.py`; reservation/CAS em `services/memory-service/tests/test_artifact_physical_saga.py`; lock commit/raw rollback em `test_local_text_transaction_receipt_proof.py` | Linux precisa execução real; concorrência de claim e pausa requer guarda do escopo canônico junto ao primeiro efeito. |
| Missão pausada/objetivo alterado/work item bloqueado após dispatch | `tests/unit/test_mb219_physical_effect_boundary.py`: chamada direta, apply e compensação pré-canônica, cinco formas de drift; testes físicos em `tests/integration/test_mb219_physical_boundary.py` | Reproduziu dez allows indevidos antes do patch; após patch, 20 testes diretos passaram no Windows. Isso não prova rename/lock Linux. |
| Crash após saga marker sem journal, ou staged sem claim | `tests/integration/test_physical_operations_console_integration.py::test_crash_before_journal_then_paused_mission_cannot_start_effect`; novos testes MB219 de pausa após stage e recovery staged sem claim | Checkpoints sem claim nunca ganham autoridade histórica. |
| Crash após claim/rename e antes do commit | `test_local_text_transaction_hard_crash.py` usa subprocesso com saída abrupta; `test_local_text_transaction.py` cobre seams injetadas; console integration cobre restart antes do commit; novo teste MB219 reconcilia claim exata após pausa | Crash de processo não equivale a prova de perda de energia/controlador de storage. |
| Disk full | `test_local_text_transaction.py::test_posix_enospc_during_stage_never_claims_or_mutates_target`; console suites cobrem falha de save após confirmation durável e reconciliação do receipt | ENOSPC é injetado; não prova todas as falhas de fsync/ledger/journal/commit sob filesystem realmente cheio. |
| Journal/backup tamper | `test_local_text_transaction.py::test_posix_journal_tamper_or_truncation_fails_hash_chain` e `test_posix_replace_recovery_revalidates_backup_before_claim`; governance ledger tamper tests; append-only saga tests | Hash chain detecta alteração não resealada; não é MAC/assinatura contra dono malicioso capaz de reescrever toda a cadeia/TCB. |
| Symlink/reparse/hardlink/FIFO/path swap | Preflight/transaction suites validam tipo, identidade, root, mode, no-follow/openat; bootstrap e request-store suites recusam redirects/permissions indevidas | Backend Windows físico recusado; não mapear garantias POSIX a NTFS. |
| Edição humana após confirmation | `tests/integration/test_physical_operations_console_integration.py::test_fresh_human_edit_after_confirmation_prevents_execute`; `tests/integration/test_mb219_physical_boundary.py::test_confirmed_rollback_does_not_overwrite_a_later_human_edit`; kernel recusa inode substituído no rollback | Nunca sobrescrever edição para forçar recovery; comparar hash e identidade atuais. Caso composto Linux permanece pendente no Windows. |
| Hash próprio/attestation fabricada | `services/memory-service/tests/test_artifact_physical_saga.py::test_self_sealed_attestation_is_not_authority_without_trusted_verifier`; `tests/unit/test_artifact_physical_attestation_authority.py` leases exatas, one-shot e thread-local; novos testes MB219 rejeitam substituição resealada | Digest sem origem confiável não autentica operador nem efeito físico. |
| Cache/status/UI elevado a autoridade | Testes console alteram input/plano/challenge/identidade; status read-only não confirma; CLI separa prepare/confirm/execute/rollback; snapshot Web sem ações | Identidades são bindings locais, não autenticação humana multiusuário durável. |

Paths abreviados `test_local_text_transaction*.py` ficam em
`services/operational-service/tests`; `test_*_governance.py` ficam em
`services/governance-service/tests`.

## Fechamento local e limites antes de ampliacao

1. Corpus Linux real/hard crash/pause-stage-claim executado em tmpfs e ext4:
   224 passed/5 skips apenas de contratos Windows, nao skips do backend Linux.
2. Gates release Linux e standard Windows aprovados; aceite tecnico CLI MB218
   cobre preview/confirm/restart/redacao. Nao representa homologacao humana.
3. Linearizacao composta provada em test_mb219_scope_process_boundary: outro
   processo SQLite recebe busy/locked durante after_claim/after_rollback_claim,
   escreve apos a guarda; pausa primeiro => zero claim/efeito. Seam sincroniza
   janela real, nao substitui processos, SQL, locks, claims ou rename.
4. test_mb219_storage_faults fecha seis casos apply/rollback x preclaim/receipt/
   canonical em volume persistente: falha concreta fsync/commit e reload real.
   ENOSPC/EIO sao injetados; nao provam disco cheio, VFS/fsync C ou power loss.
   Essas provas adicionais exigem campanha propria antes de ampliar garantias.
5. Definir autenticação/ownership humano durável antes de exposição multiusuário.
   O `owner_context` legado não é fonte de ownership persistido humano.
6. Documentar limites de storage/host e rollback: rollback canônico recupera
   predecessor de replace; não é undo-create genérico nem overwrite de edição
   humana conflitante.

Decisao: go_for_bounded_local_linux_sqlite_opt_in e no_go_for_public_mutating_api.
MB219 concluido somente nesse recorte, com API mutante ausente e adapters opt-in.
Auth multiusuario/host comprometido/hardware durability permanecem limites de
TCB e deployment, nao capacidades ja entregues. Linhas do corpus acima registram
tambem a evidencia historica inicial; a campanha final vinculada supersede os
avisos anteriores de backend Linux ainda pendente.

Resposta a incidentes e preservação de evidência:
[runbook MB219](mb219-incident-runbook.md).
