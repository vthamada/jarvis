# Sagas de artefatos físicos e canônicos

Status: runbook operacional de fechamento do `MB-217`.

## Escopo

Este corte coordena uma mutação física comprovada pelo `MB-216` com a
ativação ou o rollback de uma versão canônica de artefato. Não existe
transação distribuída entre Operational, Governance e Memory; por isso, uma
saga persistida registra cada fronteira e permite recovery sem inferir efeitos.

Uma mutação física concluída não ativa automaticamente um artefato. Uma
transição canônica também não prova, isoladamente, que o arquivo ainda está no
estado esperado. A composição só conclui quando as duas verdades estão ligadas
por IDs, hashes, fingerprints, revisions e receipts exatos.

## Fonte de verdade normalizada

Versões fisicamente comprovadas usam registros normalizados e imutáveis para:

- plano reservado da saga;
- eventos append-only e hash-chained da saga;
- versão física canônica;
- head da linhagem protegido por revision/CAS;
- item de outbox e sua entrega append-only.

Esses registros são a fonte de verdade de owner, version, lineage, recurso,
operação física e receipts. O JSON legado de `MissionStateContract` permanece
uma projeção de compatibilidade. Um upsert integral da missão não pode criar,
alterar nem apagar uma versão física normalizada. Na leitura, a projeção
normalizada prevalece sobre entradas JSON com o mesmo artifact ref ou lineage.

Artefatos legados continuam `logical_only` ou `unverified_legacy`. Eles não
devem ser promovidos silenciosamente a fisicamente verificados, mesmo que um
path ou artifact ref coincida. `ArtifactResultContract`, `location_ref` e
`rollback_plan_ref` não são evidência física.

## Invariantes comuns

- cada saga possui purpose imutável: `apply` ou `rollback`;
- operation ID, receipt e artifact version não podem ser reutilizados em outra
  missão, saga, versão ou recurso;
- retry idêntico retorna o registro existente; mesmo ID com payload diferente
  falha fechado;
- owner, version, lineage, predecessor, resource e bindings físicos são
  imutáveis no banco, não apenas validados em Python;
- somente uma versão pode ser o head ativo de uma linhagem;
- a próxima versão e a revision da linhagem devem ser exatamente sequenciais;
- timestamps são evidência, mas revision, sequence e fingerprints são a
  autoridade de ordenação;
- nenhuma fase, evento ou telemetria pode conter bytes, diff ou path absoluto;
- falha ou incerteza nunca é convertida em sucesso por conveniência.

## Fluxo de apply

1. Memory reserva um `ArtifactPhysicalApplyPlanContract` imutável antes do
   primeiro efeito físico. O plano prende missão, owner, work item, lineage,
   predecessor, artifact/version, operation ID, resource, preflight, hashes e a
   revision esperada.
2. A saga append-only registra `reserved` e, antes da chamada física,
   `effect_dispatched`.
3. Operational executa ou recupera exatamente a transação `MB-216` indicada.
   Claim histórico, journal e receipt seguem as regras do runbook do `MB-216`.
4. Governance persiste o `LocalTextMutationReceipt`. A saga somente avança a
   `physical_applied` após lookup exato dessa evidência.
5. Operational revalida o estado físico atual e executa o commit canônico por
   callback enquanto conserva o mesmo resource lock do `MB-216`.
6. Memory insere a versão imutável, avança o head com CAS, grava
   `canonical_committed` e cria o item de outbox na mesma transação.
7. Após leitura exata do commit, a saga pode registrar `completed`. A entrega
   observável ocorre pelo outbox e é idempotente.

Falha antes do claim físico pode permitir cancelamento seguro da reserva. Após
o claim, a operação não é cancelada nem reemitida: recovery usa a autoridade
histórica e a mesma operação.

### Falha depois do efeito: compensação precanônica

Se o efeito físico do apply foi comprovado, mas a versão ainda não foi ativada
canonicamente, a reversão é uma nova saga de rollback em modo
`precanonical_compensation`. Ela possui operation ID, intent, confirmação,
grant, claim, journal e rollback receipt próprios; nunca reutiliza a autoridade
do apply.

A sequência persistida é `rollback_reserved` ->
`rollback_effect_dispatched` -> `physically_rolled_back` ->
`compensation_committed` -> `completed`. O commit de compensação e o evento
`compensated` da saga de apply original são gravados atomicamente. A
compensação não cria versão, não avança a revision e não altera o head
canônico:

- para um `replace` ainda não canônico, o arquivo volta ao conteúdo físico da
  versão que continua como head canônico;
- para um `create` ainda não canônico, o target volta a estar fisicamente
  ausente.

Esse segundo caso é somente compensação física precanônica. O lifecycle
canônico existente não possui transição `active -> absent`; rollback canônico
somente restaura uma versão superseded após um replace concluído.

## Verificação fresca sob o resource lock

O receipt de Governance comprova um efeito histórico; não comprova sozinho o
estado atual do arquivo. Antes da ativação canônica, a composição deve adquirir
o resource lock do `MB-216` e, sob esse lock:

1. carregar o mutation receipt persistido exato e confirmar que ele pertence ao
   plano, operation ID, resource e hashes da saga;
2. confirmar que não existe rollback receipt aplicável;
3. reabrir e validar o journal hash-chained do `MB-216`;
4. revalidar root, anchors, named chain, device/inode, tipo, link count, hash
   atual, identidade pós-escrita e policy/backend;
5. rejeitar edição posterior, troca por inode novo com os mesmos bytes e leitura
   instável;
6. construir uma attestation content-free presa à saga e à revision esperada;
7. invocar um callback limitado que realiza o CAS canônico;
8. liberar o lock somente após commit ou rollback da transação canônica.

Não deve existir uma rota produtiva `verify` seguida de `commit` sem lock entre
as chamadas. Se o processo morrer nessa janela, o lock é liberado e o recovery
repete toda a verificação; uma attestation anterior não é reutilizada.

### Lease de attestation one-shot

Uma attestation selada pelo próprio caller não prova proveniência. Operational
emite, sob o resource lock, uma lease efêmera presa ao plano, receipt e
attestation exatos. Essa lease:

- existe somente em memória e na autoridade que a emitiu;
- só pode ser consumida uma vez, na mesma thread e dentro do callback canônico;
- rejeita substituição de receipt, attestation, autoridade ou contexto;
- desaparece ao sair do callback, inclusive por exception;
- não sobrevive a restart.

Memory combina o consumo dessa lease com o lookup integral do receipt em
Governance. Depois de restart, Operational precisa reabrir journal e recurso,
reobservar o estado físico sob lock e emitir uma lease nova; fingerprint
self-sealed ou lease anterior nunca autoriza o commit.

## Prova exata em Governance

Governance é a autoridade para a existência do mutation receipt e do rollback
receipt. Lookup deve comparar o contrato persistido inteiro e seus bindings,
não aceitar um fingerprint recalculado fornecido pelo caller como prova de
proveniência. Receipt ausente, forjado, divergente, ligado a outra operação ou
já revertido bloqueia a ativação antes do callback canônico.

A versão canônica referencia o mutation receipt exato. O rollback referencia
tanto esse mutation receipt quanto o rollback receipt exato. Nenhuma das duas
provas transfere autoridade para outra saga.

## Fluxo de rollback

Rollback canônico é uma saga distinta e não uma fase tardia do apply. Ele só é
válido para uma versão ativa que supersede outra versão normalizada:

1. Memory reserva um `ArtifactPhysicalRollbackPlanContract` com saga ID e
   physical operation ID novos, revision atual e bindings da versão ativa e da
   versão a restaurar.
2. A saga registra `rollback_reserved` e `rollback_effect_dispatched`.
3. Governance exige intent, confirmação, grant e joint claim de rollback novos,
   ligados ao mutation receipt original.
4. Operational executa ou recupera o rollback `MB-216` e Governance persiste o
   rollback receipt exato.
5. A saga registra `physically_rolled_back` somente após a prova persistida e a
   revalidação física do estado restaurado.
6. Memory avança a revision da linhagem, reativa a versão restaurada, registra
   `canonical_rolled_back` e cria o outbox na mesma transação.
7. Leitura exata confirma o commit antes de `completed`.

O grant de apply nunca autoriza rollback. Falha de rollback não autoriza apagar
o artefato, forçar a projeção canônica ou reutilizar backup/stage fora do
journal e da autoridade originais.

## Recovery após restart

| Última evidência durável | Estado permitido | Ação de recovery |
| --- | --- | --- |
| Nenhuma reserva | Nenhum efeito atribuível à saga | Iniciar uma saga nova |
| `reserved` | Sem canonical active | Retomar antes do claim ou cancelar com evidência pré-claim |
| `effect_dispatched`, sem receipt | Sem canonical active | Consultar claim/journal e usar recovery `MB-216`; não reexecutar fresh |
| Mutation receipt em Governance, evento ausente | `canonical_pending` | Anexar `physical_applied` com lookup exato; não repetir o efeito |
| `physical_applied` | `canonical_pending` | Revalidar estado atual sob lock e tentar o CAS canônico |
| Commit canônico com resposta incerta | Ativo no máximo uma vez | Ler por saga/version/revision e aceitar somente igualdade exata |
| `canonical_committed`, outbox pendente | Ativo | Publicar o item existente de forma idempotente |
| Apply com efeito comprovado, sem commit canônico | Head canônico anterior preservado | Reservar uma saga distinta de `precanonical_compensation`; nunca marcar o apply como canônico |
| Compensação física comprovada, commit incerto | Head canônico inalterado | Confirmar `compensation_committed` e o evento `compensated` do apply por leitura exata; não repetir rollback |
| `rollback_effect_dispatched`, sem receipt | Ainda canonicamente ativo | Recuperar o rollback `MB-216` pelo claim histórico |
| Rollback receipt em Governance, evento ausente | Fisicamente revertido, canônico pendente | Anexar `physically_rolled_back` por igualdade exata |
| `physically_rolled_back` | Pendente de reconciliação canônica | Revalidar o estado restaurado e tentar CAS de rollback |
| Commit de rollback com resposta incerta | Restaurado no máximo uma vez | Ler a revision/evento exatos; nunca repetir o efeito |
| Evidência truncada, conflitante ou estado físico divergente | `reconciliation_required` | Preservar evidência e encaminhar para intervenção manual |

Recovery nunca usa timestamps para adivinhar a fase. Ele consulta, na ordem,
plano imutável, cadeia de eventos, Governance, journal `MB-216`, versão/head
canônicos e outbox. A ausência de uma evidência não implica que o efeito
anterior não ocorreu.

## Outbox

O item de outbox nasce na mesma transação da versão, do CAS da linhagem e do
evento canônico da saga. Publicação ocorre depois do commit. Retry usa o mesmo
outbox ID e canonical event fingerprint; uma entrega append-only registra o
publisher e o fingerprint publicado.

Consumidores devem tratar o evento como idempotente. Falha de publicação não
reverte o commit canônico e não autoriza criar outro item equivalente. Um
evento nunca pode anunciar `active` ou `rolled_back` antes do respectivo commit.
Dentro de uma linhagem, revision e sequence canônicas definem a ordem; retry de
um item anterior não permite publicar uma transição posterior fora dessa ordem.

## Concorrência e persistência

### SQLite

- iniciar a transação crítica com `BEGIN IMMEDIATE` antes de ler predecessor e
  revision;
- habilitar foreign keys, journal/durabilidade qualificados e timeout de lock;
- impor UNIQUE, CHECK e triggers append-only para versões, planos e eventos;
- resolver conflito somente por igualdade integral do registro existente;
- testar restart em processo novo e resposta perdida depois de commit.

### PostgreSQL

- serializar a linhagem por row lock ou advisory transaction lock estável;
- proteger também a corrida da primeira versão, quando ainda não há predecessor
  para `SELECT FOR UPDATE`;
- combinar constraints, triggers append-only e CAS condicional;
- tratar serialization failure/deadlock como retry da mesma saga, nunca como
  permissão para criar outra operação;
- confirmar resultados por uma conexão nova após commit incerto.

A implementação e a matriz de testes exigem as mesmas decisões em SQLite e
PostgreSQL para reserva concorrente, replay, colisão, imutabilidade, apply,
rollback, compensação, recovery, outbox e overlay do JSON legado. A paridade
inclui lock transacional do primeiro head, e não apenas a presença das tabelas
no schema. Na rodada local de fechamento, a matriz SQLite foi executada e os
dois testes PostgreSQL focados do `MB-217` passaram contra PostgreSQL 17 local:
schema e ciclo register/compensation/replace/canonical rollback/outbox/reload/
CAS/append-only.

## Intervenção manual

Use `reconciliation_required` quando a automação não consegue provar uma
continuação única e segura. Esse checkpoint é terminal: recovery não pode
avançá-lo para uma fase de sucesso. Exemplos: receipt conflitante, journal
truncado, edição posterior, inode inesperado, root/config/policy divergente,
lineage CAS perdido para uma operação incompatível, rollback parcial ou commit
cross-store sem evidência suficiente.

O operador deve preservar banco, WAL, journals, stages e backups; impedir novas
ações no recurso; coletar somente IDs, hashes e fingerprints; e registrar a
decisão fora da cadeia imutável original. Não é permitido editar rows, remover
eventos, trocar um receipt ou marcar `completed` manualmente. Uma eventual
correção deve ser uma nova operação governada e explicitamente ligada ao
incidente.

## Procedimento conceitual do operador

Ainda não existe API pública nem comando de console para estas ações. Os nomes
abaixo descrevem capacidades internas futuras; não devem ser implementados como
atalhos que contornem Orchestrator, Governance, Operational ou Memory.

1. **Inspecionar:** `inspect-artifact-saga --saga-id <id>` deve ler plano,
   eventos, receipts, journal, head, version e outbox sem escrever.
2. **Pausar o recurso:** `pause-artifact-resource --resource-ref <ref>` deve
   bloquear novas reservas/grants, preservando recovery de claims históricos.
3. **Reconciliar:** `recover-artifact-saga --saga-id <id>` deve executar a
   state machine normal, com igualdade exata e verificação física fresca.
4. **Entregar outbox:** `deliver-artifact-outbox --outbox-id <id>` deve publicar
   somente o item canônico existente e registrar entrega idempotente.
5. **Escalar:** `open-artifact-reconciliation-incident --saga-id <id>` deve
   registrar o bloqueio sem modificar a evidência original.

Nenhuma ferramenta futura deve oferecer `force-active`, `force-completed`,
edição direta de owner/version ou exclusão de journal/receipt.

## Pausa segura

Para parar novas sagas, desative reservas e emissão de grants antes de parar os
workers. Preserve acesso read-only a Memory, Governance e journals para
classificar operações existentes. Uma saga antes do claim pode permanecer
reservada; uma saga depois do claim precisa continuar recuperável por
autoridade histórica mesmo que o TTL original expire.

Missão pausada ou não ativa bloqueia uma nova reserva e um novo dispatch. Se
`effect_dispatched` ou `rollback_effect_dispatched` já foi persistido, a pausa
não interrompe o recovery necessário para levar o recurso a um estado provável
e seguro; ela continua bloqueando uma operação nova e incompatível.

Não apague outbox pendente, receipt, stage, backup, journal, WAL ou evento de
saga durante a pausa. Retomar significa executar primeiro a reconciliação das
sagas incompletas e somente depois liberar novas reservas para o mesmo recurso.

## Boundary de segurança

O processo Operational deve usar a identidade dedicada e os modos/ACLs
documentados pelo `MB-216`. Outro UID sem permissão não pode trocar root,
parents, target ou state directory. Código executando como o mesmo euid,
`root`, administrador do host ou com acesso direto aos bancos/journals pertence
ao TCB: ele pode modificar o arquivo ou fabricar estado fora das APIs, e esta
saga não promete defender contra comprometimento desse boundary.

Logs, eventos, exceptions e inspeções operacionais devem permanecer
content-free. Use aliases, IDs, phases, revisions, digests e fingerprints.
Paths absolutos, bytes, trechos de texto, diff e backup content não podem sair
do boundary operacional.

## Evidência de fechamento

- contratos, fingerprints e state machine: `shared/artifact_physical_saga.py`
  e `tests/unit/test_artifact_physical_saga_contracts.py`;
- lease efêmera one-shot: `shared/artifact_physical_attestation_authority.py`,
  `tests/unit/test_artifact_physical_attestation_authority.py` e
  `services/operational-service/tests/test_local_text_transaction_wiring.py`;
- persistência normalizada, CAS, compensação, overlay e paridade:
  `services/memory-service/tests/test_artifact_physical_saga.py` e
  `services/memory-service/tests/test_memory_postgres_integration.py`;
- coordenação, fault boundaries, retry exato e outbox:
  `services/orchestrator-service/tests/test_artifact_physical_saga_end_to_end.py`;
- fluxo real Governance -> Operational -> Memory -> Observability, com restart,
  create, replace e rollback canônico:
  `services/orchestrator-service/tests/test_artifact_physical_saga_real_integration.py`.

O E2E de mutação física roda no backend Linux. No Windows, o backend de
transação continua fail-closed antes de journal ou efeito, conforme o
boundary preservado do `MB-216`.
