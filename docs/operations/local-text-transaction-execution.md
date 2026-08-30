# Execução transacional de texto local

Status: runbook operacional do `MB-216`.

## Escopo

Este corte executa somente `create_text` e `replace_text` em roots locais
previamente configurados e permite `rollback_text` por uma autorização nova e
dedicada. Preflight, grant de execução, confirmação humana, claim, efeito,
receipt e rollback formam uma cadeia exata; nenhum desses elementos isolado
concede autoridade.

O backend físico liberado é Linux com `openat`, `O_NOFOLLOW`, `fsync` e
`renameat2(RENAME_NOREPLACE)` disponíveis nas arquiteturas explicitamente
suportadas. Windows falha fechado antes de criar journal ou tocar no target até
existir uma implementação equivalente baseada em handles.

## Identidade e ownership obrigatórios

O processo deve rodar com uma identidade POSIX dedicada ao serviço. Essa
identidade precisa ser proprietária do root configurado, de todos os parents
internos, do target existente e de `.jarvis-transactions`. Root, parents,
target e state directory não podem ser graváveis por group ou others; o state
directory deve ser privado.

Ancestrais externos também precisam ser exclusivos. A única exceção aceita é
um diretório sticky cujo owner seja `root` ou o próprio euid e cuja entrada
filha pertença ao euid do serviço. Código que executa com o mesmo euid, root e
administradores do host pertencem ao TCB. Por isso, compartilhar a identidade
do serviço com aplicações gerais invalida a fronteira de segurança.

Bind mounts no mesmo device não são distinguíveis apenas por `st_dev`. A
contenção adicional depende do rewalk por nomes e identidades `device/inode`,
dos handles presos e do boundary de identidade acima.

## Layout e filesystem

Cada alias possui um root absoluto configurado e exatamente um diretório
irmão interno `<root>/.jarvis-transactions`. O journal SQLite, stages e backups
ficam nesse diretório. O nome reservado nunca pode ser alvo de uma operação.

O root, seus parents internos, target e state directory precisam permanecer no
mesmo device. A engine verifica `st_dev` antes de staging/claim e falha fechada
em mountpoint cross-device. O ambiente deve oferecer:

- rename atômico no mesmo filesystem;
- semântica confiável de `fsync` para arquivo e diretório;
- SQLite WAL e locks locais coerentes;
- persistência de directory entries após flush;
- `renameat2(RENAME_NOREPLACE)` via símbolo libc ou syscall da arquitetura.

Filesystem de rede, FUSE sem garantias equivalentes, overlay não qualificado e
kernel/filesystem sem `renameat2` não estão liberados. Uma indisponibilidade
descoberta após o joint claim pode consumir a autorização sem produzir efeito;
nesse caso, somente recovery/reconciliação do mesmo journal é permitido.

## Sequência de autoridade

1. Operational materializa o preflight e o entrega diretamente ao attestor
   confiável pela composição única `preflight_and_attest_local_text_file`.
   A função interna de attestation isolada de Governance não é uma capability
   produtiva e não deve ser exposta a callers, console ou API.
2. Governance emite um grant de execução separado, curto e single-use, ligado
   ao preflight e a uma confirmação humana exata.
3. A ponte compara a operação física inteira com o contexto persistido:
   purpose, operação, recurso, sujeito, hashes before/desired, root, versões,
   grant, intent, confirmação e reservation.
4. A verificação ativa ocorre antes de qualquer state write.
5. Stage e backup são gravados e sincronizados; então Governance consome grant
   e confirmação atomicamente no joint claim.
6. O claim é reverificado imediatamente antes do primeiro syscall de efeito.
7. Rename, directory flush, evento aplicado e receipt content-free são
   persistidos; Operational registra o receipt em Governance.

O joint claim é o ponto irrevogável: depois dele não existe cancelamento
prometido. Uma verificação fresh negativa bloqueia aquela tentativa, mas o
mesmo claim histórico pode ser retomado por recovery depois do TTL ou de drift
do registry para concluir ou reconciliar um efeito já autorizado. Depois do
joint claim, recovery nunca emite outro grant ou claim. Antes do claim,
recovery de um stage durável pode consumir uma única vez o grant e a
confirmação ainda ativos e exatos; isso não reabre nem substitui autoridade.

O relógio transacional deve vir da mesma fonte confiável usada pela Governance,
ser timezone-aware e monotônico. Callers não podem fornecer `now`. Cada
transição crítica consulta novamente o relógio, inclusive após o claim e após o
efeito, preservando `claimed_at <= committed_at` e
`claimed_at <= rolled_back_at`.

## Recovery e rollback

Retry fresh é permitido somente antes do claim. Depois de claim, crash ou
resultado incerto, use a operação explícita de recovery com o mesmo root alias
e operation ID. O journal hash-chained e as identidades dos stages são
revalidados antes de continuar. Row alterada/truncada, desired/backup
ausente, corrompido ou substituído, versão de backend/policy incompatível e
parent/target divergente falham fechados.

Rollback não reutiliza o grant de apply. Governance exige mutation receipt
persistido, request derivado, intent novo, confirmação nova, registry rollback
ativo, grant novo, operation ID distinto e reservation distinta. A engine
deriva o root alias do `resource_ref` do receipt, abre somente esse journal e
recusa rollback se o target recebeu edição posterior. Replace restaura os bytes
exatos do backup; create remove somente o inode aplicado pela transação.

## Incidentes e limites de evidência

Os testes cobrem exceptions, concorrência, restart e hard crash com `os._exit`
em três boundaries: claim antes do journal, rename antes de journal/fsync e
rollback rename antes de journal/fsync. Eles comprovam reabertura de SQLite/WAL,
engine nova, recovery e idempotência no ambiente Linux qualificado.

Isso não equivale a ensaio de perda física de energia, cache de controladora ou
falha do hardware. Após power loss real, preserve root, journal, stages e
backups; não repita uma ação fresh; execute recovery/reconciliação sob a mesma
identidade e registre a limitação no incidente.

## Pausa segura

Para impedir novas mutações, ative snapshots de execution e rollback sem os
descriptors correspondentes e pare a emissão de grants. Preserve ledgers,
journals, stages, backups e receipts. Claims históricos permanecem auditáveis e
podem exigir recovery; apagar evidência para “desfazer” um claim é proibido.

Telemetria e incidentes devem usar apenas IDs, aliases, hashes, fases,
fingerprints e timestamps. Bytes do arquivo, diff sensível e path absoluto não
devem sair do boundary operacional.
