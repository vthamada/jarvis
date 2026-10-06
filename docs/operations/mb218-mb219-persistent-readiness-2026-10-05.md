# MB218/MB219 - campanha persistente e readiness local

Data: 2026-10-05. Continuidade autorizada pelo operador, com dois workers
disjuntos (aceite CLI e auditoria/corpus) e coordenador (runner, Docker e gates).
Sem nova dependencia de runtime, efeito em arquivo humano, login ou API publica.
Este registro complementa a [primeira prova Linux](linux-physical-validation-2026-10-05.md).

## Escopo da decisao

Aceite tecnico automatizado do console local, nao homologacao humana ou deploy.
Os criterios MB218 no execution-backlog nao exigem participacao do operador:
preview inspecionavel, confirmacao exata separada, restart/recovery e redacao.
MB219 exige corpus adversarial, runbook, gates e decisao explicita de fase.
Autenticacao multiusuario e resistencia a perda de energia nao sao entregas
desse recorte; nao converter esses limites em promocoes nem garantias falsas.

Decisao final, com os criterios e gates abaixo satisfeitos:
`go_for_bounded_local_linux_sqlite_opt_in`; `no_go_for_public_mutating_api`.
SFC-005 permanece fora da fila/exposicao atual: autenticacao/ownership humano
duravel e desenho do boundary externo exigem repriorizacao propria.
PostgreSQL sem implementation de first-effect scope e Windows fisico continuam
fail-closed. Nenhuma capability, framework ou modelo externo foi promovido.

## Prova entre containers

`tools/run_linux_validation.py --mode persistent` cria um volume novo com UUID,
labels exatos, driver local sem Options, e recusa nomes existentes/erros ambiguos.
Revalida ownership antes de cada fase e antes da remocao. Somente named volume
fixo /validation, nunca host bind; rede none, rootfs read-only, caps none,
no-new-privileges, memoria/CPU/PIDs bounded. Fontes selecionadas vao pelo archive,
sem .git/.venv/DB/audio/modelos do host. A denylist nao e um scanner de segredos.

Imagem pinada por SHA e o mesmo archive/hash em todas as fases. mountinfo do
guest comprova filesystem nao efemero; ownership named-volume e comprovado pelo
runner externo, nao inferido de mountinfo. Filesystem observado: ext4 na VM
Linux do Docker Desktop; nao prova o controlador/disco fisico do Windows.

| Fase em container novo | Verificacao efetiva | Exit esperado |
| --- | --- | --- |
| prepare | CLI real, root/alvo/op/hash/risco/validade; diff opt-in; challenge estrangeiro recusado; zero efeito | 0 |
| confirm | CLI real, receipt exato; replay de confirmacao recusado; status persistido; zero efeito | 0 |
| crash | Core/kernel reais, bytes escritos, saga effect_dispatched e versao canonica ainda ausente; os._exit abrupto | 86 |
| recover | CLI real e journal/receipts persistidos; mesma confirmacao/claim, sem nova autoridade; retry idempotente | 0 |
| rollback | replace CLI, challenge/receipt independente, receipt de apply recusado no rollback; predecessor restaurado | 0 |
| verify | reload Core, lineage revision3, receipts Governance/Memory exatos, outbox entregue e eventos redigidos | 0 |
| suite | corpus fisico e falhas abaixo em /validation/pytest-fixtures, nao /tmp tmpfs | 0 |

Exit86 em outra fase ou exit0 no crash falha a campanha. Fixture bounded32KiB,
0600/single-link/no-follow e root0700 nao sao fonte canonica nem autorizacao.
Falha/interrupcao preserva volume/journals; cleanup nao confirmado nao vira pass.
Sucesso remove somente containers e volume sinteticamente criados nesta chamada,
apos validar identidade; nunca prune, images, caches ou volumes preexistentes.

## Matriz de aceite e adversarial

| Criterio | Evidencia |
| --- | --- |
| Preview alvo/root, op, diff/resumo, hashes, risco e validade | persistent_scenario prepare + console unit/CLI corpus |
| Challenge/receipt exatos e independentes, confirmacao nao executa | prepare/confirm/rollback + Governance replay/expiry/clock tests |
| Status/recovery sobrevivem processo e container | seis fases + hard-crash/console integration; canonical commit pendente recuperado |
| Eventos/default CLI/errors nao vazam texto ou paths absolutos | verify + console/CLI/redaction corpus; preview apenas opt-in |
| Pausa lineariza com primeiro efeito | test_mb219_scope_process_boundary: apply/rollback, outro processo SQLITE_BUSY/LOCKED durante claim/rename, pausa depois; pausa vence => zero claim/efeito |
| Falhas de storage antes/depois da claim | test_mb219_storage_faults: apply/rollback x preclaim/receipt/canonical, seis casos com reload real |
| Paths, links, backup/journal tamper, edicao humana, concorrencia | corpus PHYSICAL_TESTS, sem skips do backend Linux suportado |

Falhas pontuais concretas: ENOSPC no os.fsync do staging .desired; EIO no commit
SQLite do rollback_reserved, receipt Governance ou commit canonico Memory.
SQL e I/O anteriores sao reais; falha commit aborta transacao e reload usa os
mesmos arquivos. Preclaim nao produz claim/efeito; apos efeito, recovery funciona
com missao pausada e callbacks proibindo nova confirmacao/claim. Esses proxies
nao simulam filesystem realmente cheio, SQLite VFS/fsync interno C ou power loss.

Auditoria de diff nao encontrou bypass no fallback pre-reserva: source journal
receipt/cleaned sem rollback metadata nao e autoridade historica de rollback;
plano/source receipt/Governance exatos precedem o codigo de pedido necessario.
Console revalida missao; kernel revalida/cerca primeiro efeito. Historical mode
na UI nao existe; journal + claim exata continuam obrigatorios.

## Resultados e identidades

- Windows focado final: 74 passed/13 skips Linux explicitos; Ruff global passou.
- Linux tmpfs final: 224 passed/5 skips exclusivos Windows, 30.95s, exit0.
- primeira campanha volume: seis fases +218 passed/5 Windows skips em182.53s;
  volume 3cddd0efb65146c28911da033225d393 removido apos sucesso.
- campanha volume final: seis fases aprovadas +224 passed/5 Windows skips em
  274.60s, exit0; nenhum skip do backend Linux no corpus fisico;
- gate release Linux final aprovado: suite completa, axis/release/active-cut,
  historical closure, baseline development (segunda suite completa e smokes SQLite);
- gate standard Windows final aprovado: encoding, document guardrails, Ruff e
  suite completa; skips de plataforma/backends opcionais nao sao passes;
- cleanup final confirmado por inspect dos nomes exatos: volumes ausentes e
  containers finais ausentes. Somente dados sinteticos de teste removidos;
- MB218 done por aceite tecnico CLI/restart/redacao; MB219 done por corpus,
  matriz storage, security audit, runbook, gates e decisao limitada de fase.

Imagem final: sha256:bfca5ed7ce4290892c8009f1abb441fdc8a9b147b3c52aba9115bb36b1a53bc0.
Archive final da campanha: sha256:cff799a82175a9eba8951643c3e33b3b21b2df6afde0f3d651908b45e1a4d246.
Volume final: jarvis-linux-validation-storage-525fd3634ee04dcf997f620880a3e280.
Container tmpfs: jarvis-linux-validation-5f685710c13b4216a5aea1d0432e20ff.
Container suite persistente: jarvis-linux-validation-635dbc44bcc2431186eec3936f68d704.
Container gate release: jarvis-linux-validation-854632d07b484c5288021d2a13bc8219.
Saidas/codigos inspecionados nesta sessao; este documento e resumo de evidencias,
nao bundle bruto, assinatura, commit Git ou snapshot criptografico do produto.
Atualizacao documental posterior nao altera o codigo congelado da campanha.

Referencia do contrato de volumes: [Docker volumes](https://docs.docker.com/engine/storage/volumes/)
e [volume create](https://docs.docker.com/reference/cli/docker/volume/create/).
O create pode reutilizar nome existente; por isso o runner exige prova previa
de ausencia e bindings proprios, em vez de confiar apenas no sucesso do create.

## Reproducao e resposta a falhas

```powershell
.venv/Scripts/python.exe tools/run_linux_validation.py --build --mode persistent
.venv/Scripts/python.exe tools/run_linux_validation.py --mode release
.venv/Scripts/python.exe tools/engineering_gate.py --mode standard
```

Em falha, anotar o validation_volume exato; inspecionar somente esse nome e
preservar evidencias. Nao usar reset Docker, volume prune, limpeza generica ou
reboot para transformar falha em sucesso. Runbook:
[incidente/reconciliacao](../security/mb219-incident-runbook.md).
Em runtime, desligar composicao mutante e preservar inspect/status/ledgers.
Rollback fisico governado restaura predecessor exato, nunca edicao conflitante.

## Limites mantidos

Process death/container replacement + ext4/fsync nao provam queda de energia,
reinicio do host, fault do controlador ou todas as falhas fisicas de SQLite/VFS.
Essas campanhas sao precondicoes de ampliacao de deployment/garantias, nao
evidencia ja obtida. TCB inclui Core/kernel/clock, UID confiado e Docker daemon;
sem sandbox contra administrador ou mesmo UID com controle dos bancos/daemon.
Sem PostgreSQL controlado, Node, autenticacao humana/multiusuario ou API mutante
nesta prova. Readiness local nao significa sistema completo ou produto diario.
