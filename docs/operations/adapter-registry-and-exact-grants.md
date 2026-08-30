# Registry de adapters e grants exatos

Status: baseline operacional do `MB-214`.

## Objetivo

O registry soberano transforma um pedido tipado de adapter em uma permissão
curta, exata e auditável. A permissão não nasce de texto livre, `tool_class`,
nome de capability ou confirmação isolada. Ela depende simultaneamente da
política de autonomia, do descriptor ativo e de um `ActionIntentContract`
imutável.

Este corte é deliberadamente `prepare-only`: registry, intent, grant e claim
são evidência de governança sem autoridade de execução. Nenhum executor de
adapter, dispatch operacional, diretório, arquivo temporário ou artefato físico
é criado pelo fluxo do `MB-214`.

## Registry soberano

Cada `AdapterRegistrySnapshotContract` é um snapshot imutável e versionado,
persistido no mesmo `governance.db` usado pela confirmação de ações. Seus
descriptors aceitam somente chaves exatas:

- `adapter_id` e versão semântica;
- `action_kind` canônico `prepare_external_action`;
- operações explicitamente enumeradas;
- scopes de recurso explicitamente enumerados;
- fingerprint do descriptor e do snapshot.

Wildcard, fallback, import dinâmico, callable e referência de executor são
proibidos. O descriptor seed `local_text_file@1.0.0`, quando explicitamente
ativado pela Governança, permite somente `create_text` e `replace_text` no scope
lógico `configured_text_root`; ele ainda não implementa acesso ao sistema de
arquivos.

O snapshot mais recente é a única allowlist ativa. Um grant histórico continua
auditável, mas só pode ser reclamado se a mesma chave e o mesmo fingerprint de
descriptor ainda estiverem ativos. Assim, ativar um novo snapshot sem o
descriptor pausa novas claims; remover ou alterar o descriptor também bloqueia
grants anteriores sem apagar o ledger.

## Vínculo exato do grant

Um `AdapterGrantContract` expira e pode ser reclamado uma única vez. Seu
fingerprint cobre, no mínimo:

- sujeito, adapter, versão, operação, scope e recurso;
- registry e descriptor exatos;
- intent, fingerprint da ação e identidade do handler
  `adapter://<adapter_id>` na mesma versão;
- decisão canônica de autonomia e versão da política;
- nonce, emissão, expiração e exigência de confirmação.

Sujeito diferente da identidade do intent, recurso diferente do alvo, versão
divergente, política alterada, fingerprint adulterado ou janela expirada falham
fechados. O serviço de Governança recalcula a decisão de autonomia; não confia
em um booleano fornecido pelo caller.

## Confirmação e claim

Grant e confirmação são fatores conjuntivos:

1. uma ação cujo modo é `not_required` pode receber grant sem challenge;
2. uma ação cujo modo é `explicit_confirmation_required` recebe o mesmo grant
   exato e um challenge ligado ao mesmo intent;
3. na claim, a Governança valida primeiro grant, registry ativo, descriptor e
   autonomia;
4. somente depois valida o receipt exato;
5. claim do receipt e claim do grant são gravadas na mesma transação
   `BEGIN IMMEDIATE`.

Receipt inválido não amplia autoridade. Grant inválido não consome receipt. Em
retry ou concorrência, no máximo uma claim vence por grant, receipt e
`operation_id`. Todos os registros são append-only, possuem payload canônico e
SHA-256, e são revalidados ao serem reabertos após restart.

## Planejamento e orquestração

O Planejamento só seleciona a capability supervisionada quando recebe um
`AdapterActionRequestContract` tipado. Menções no prompt não inferem adapter ou
permissão. Os caminhos nativo e LangGraph usam o mesmo fluxo para:

1. resolver o descriptor no registry ativo;
2. recomputar a política fail-closed por ação;
3. construir o intent exato;
4. emitir e persistir o grant;
5. emitir challenge adicional quando necessário;
6. retornar apenas metadados e evidência para inspeção posterior.

Erros de registry, operação, scope, autonomia ou persistência encerram o fluxo
antes de challenge, claim ou efeito.

## Rollback operacional

Para desabilitar uma integração, ative um novo snapshot versionado sem o
descriptor correspondente ou com a versão substituta desejada. Não edite nem
apague snapshots, grants ou claims anteriores. O histórico permanece disponível
para auditoria, enquanto novas claims contra descriptors pausados, removidos ou
alterados são recusadas.

## Limites e continuidade

O registry `prepare-only` do `MB-214` continua sem interpretar paths, ler
arquivos ou conceder escrita. O preflight side-effect-free pertence ao
`MB-215`. Execução e rollback usam registries, grants, claims e receipts
separados fechados no `MB-216`; a operação qualificada está descrita em
`docs/operations/local-text-transaction-execution.md`. Um grant de prepare
nunca pode ser reutilizado por essas superfícies.
