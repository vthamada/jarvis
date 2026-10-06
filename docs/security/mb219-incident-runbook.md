# MB219 — runbook local de incidente e reconciliação

Data: 2026-10-04; exercitado/revisado em 2026-10-05. Aplicável somente ao console físico local opt-in e aos roots e
runtime explicitamente configurados. Nenhum comando deste runbook concede nova
autorização. API mutante continua fora do escopo; não usar bancos humanos nos
testes. Consulte a sintaxe corrente em
[`PHYSICAL_OPERATIONS.md`](../../apps/jarvis_console/PHYSICAL_OPERATIONS.md).

## Interromper novos efeitos sem destruir histórico

1. Não iniciar mais `execute`, `rollback` ou retries automáticos. Retirar a
   composição opt-in de execução/adapters; manter inspeção somente leitura.
2. Não apagar journal, backups, requests, grants, claims, receipts ou saga; não
   resealar JSON/hash, não editar SQLite manualmente e não emitir uma segunda
   confirmação apenas para contornar erro. Nunca restaurar um backup sobre
   conteúdo humano conflitante.
3. Se houver processo já em execução, não prometer que pausa cancela uma claim
   física já durável. Coordenar o término/quiescência antes de backup/inspeção.
   Um kill pode deixar um efeito já aplicado sem commit canônico; recovery não
   deve ser substituído por limpeza de arquivos.

## Inspecionar e preservar

- Registrar request/saga/operation ids e códigos de erro permitidos, versão de
  registry/policy/backend, fase e timestamps. Não copiar texto solicitado, diff,
  conteúdo de backup, paths privados ou stack traces para logs compartilhados.
- Status é leitura de estado durável, não prova de bytes atuais. Se necessário,
  realizar inspeção fresca governada; interromper se identidade/hash divergir.
- Preservar evidência numa localização privada escolhida pelo operador. Bancos
  SQLite em WAL exigem backup consistente/quiescência; copiar apenas `.db`
  enquanto está aberto pode perder evidência. Não oferecer comando genérico de
  copiar/apagar diretórios, nem acessar secrets/accounts como parte do diagnóstico.

## Classificar antes de retomar

| Evidência durável | Ação permitida |
|---|---|
| Preparado/confirmado sem saga dispatch | Inspecionar; nova execução só com escopo canônico ativo, exact binding e autorização ainda válida. |
| Saga dispatch, journal ausente ou apenas staging sem claim exata | Não tratar como histórico autorizado. Corrigir causa e revalidar escopo antes de qualquer primeiro claim; pausa/objetivo/work item incompatíveis devem negar. |
| Journal da mutacao fonte receipt/cleaned, rollback ainda sem reserva | Nao e claim historica de rollback. Somente codigo exato de pedido necessario apos binding/source receipt/Governance verificados permite reapresentar o pedido original; revalidar missao/work item/objetivo antes de efeito novo. |
| Claim histórica exata + journal íntegro, sem receipt/commit completo | Recovery governado, mesma operação/evidência, sem nova claim. Pausa impede trabalho novo, não torna o histórico falso. |
| Receipt físico válido, commit canônico pendente | Reconciliar sob lock, attestation e CAS canônico; não afirmar artifact ativo antes do commit. |
| Journal/backup adulterado, root/arquivo trocado ou edição humana divergente | Falhar fechado e preservar evidência. Não resealar, forçar overwrite ou desabilitar verifier. Exigir investigação/decisão humana explícita. |
| Storage cheio/falha de fsync ou ledger indisponível | Parar retries; restaurar capacidade do storage com intervenção humana fora do runtime auditado. Depois inspecionar fases antes de retry/recovery exato. |

Rollback não é recuperação universal. Exige plano independente, mutation receipt
exato, confirmação/grant próprios, backup íntegro e conteúdo atual esperado.
Undo-create genérico e compensação arbitrária continuam não autorizados.

## Retomar e encerrar o incidente

Retomar somente após corrigir a causa, demonstrar coerência física/canônica e
verificar que a retomada não emitirá autoridade nova por engano. Executar a bateria
afetada em dados temporários; manter skips Linux explícitos no Windows. Gate
standard é mínimo; readiness MB219 exige também release e evidência física Linux.
Atualizar handoff/documentação de estado com causa, evidência, limitação residual
e decisão humana. Não elevar API ou capability por consequência do recovery.

Campanha exercitada: CLI em containers separados/volume ext4, crash86 antes
do commit canonico, recovery com a mesma confirmacao, replace/rollback e
verificacao de receipts/lineage/outbox/redacao. Corpus persistente:224 passed/
5 skips Windows; falhas ENOSPC/EIO pontuais e pausa concorrente por processo
incluidas. [Evidencia e limites](../operations/mb218-mb219-persistent-readiness-2026-10-05.md).
MB218/219 tecnicamente fechados para local Linux/SQLite; API mutante continua
ausente. Isso nao promete recovery apos power-loss/host reboot/controlador.
