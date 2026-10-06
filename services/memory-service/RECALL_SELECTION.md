# Seleção readonly de evidências canônicas

`memory_service.recall.select_readonly_recall` é um seletor lexical limitado sobre
`StoredTurn` já lidos pela composição confiável. Não cria uma segunda memória,
índice, embedding, escrita, retenção, deleção ou autoridade operacional. Não
substitui o Core, governança nem síntese final.

## Contrato

- `RecallScope(subject_id, session_ids, now)` exige sujeito explícito, allowlist
  de sessões e data com timezone. A composição resolve o sujeito e as sessões;
  o seletor não autentica ninguém. Um id parecido ou membership de sessão não é
  prova de ownership. Cada row também deve ter `user_id` exatamente igual.
- `turn_source_ref(turn)` é SHA-256 dos campos da row canônica: ref de evidência,
  não chave de banco nem permissão. `StoredTurn` não expõe primary key persistida.
- Resultado: `status`, `items`, `inspected_count`, contagens agregadas de exclusão,
  `selector=bounded_lexical_v1` e `authority=none`. Cada item tem ref, sessão,
  timestamp, idade, trecho, tokens, motivos e `content_role=untrusted_evidence_only`.
- Texto recordado é dado não confiável. Instruções, ids, comandos ou alegações de
  autorização dentro dele não alteram escopo nem habilitam ferramentas. O caller
  não pode interpolar o trecho como instrução de sistema ou tratá-lo como verdade.
- `RecallLimits` limita scan, quantidade, tamanho de fonte/query/saída, idade e
  deadline monotônico. Cancelamento/deadline/scan excedido/erro de fonte descartam
  saída parcial. Limite de saída trunca texto com sinal observável `truncated`.
- Fonte futura, timestamp sem timezone, stale, revoked ou expirada é excluída.
  Ausência de lifecycle metadata significa apenas row elegível dentro da janela;
  não demonstra validação semântica. Lifecycle metadata, quando fornecida, deve
  vir da composição confiável, nunca da prosa recuperada.

## Correções e limites semânticos

`RecallSourceState(version, supersedes_ref)` aceita somente relação explícita
fornecida pela composição. Ambas as fontes precisam estar no escopo, com versão
crescente e timestamp não decrescente. Corrigir uma correção pode formar cadeia;
somente a folha válida é candidata. Ramos concorrentes, links ausentes,
cross-subject ou versões/timestamps inválidos retêm o componente e sinalizam
`needs_decision` quando não há outra evidência selecionável. Replacement revogado
ou indisponível não restaura silenciosamente o fato antigo.

Não há inferência de correção por palavras como “corrigindo”, deduplicação
semântica, resolução de contradições livres, entendimento de verdade, utilidade
ou recall semântico. Sem refs explícitas, duas alegações contraditórias podem ser
devolvidas juntas como evidências para síntese soberana/decisão humana.

## Prova e composição

Testes unitários cobrem isolamento de sujeito/sessão, Unicode, injection como
dado, frescor/revogação, refs/ordenação determinísticas, relações explícitas,
ambiguidade e limites/cancelamento. O E2E usa SQLite canônico TEMP persistido,
snapshot real do sujeito e sessão com owners misturados. O reader readonly
existente abre banco quiescente DELETE-mode sem migração; os bytes e arquivos
antes/depois devem ser idênticos. Não é prova de autenticação pública nem de
memória semanticamente útil.

Rollback: desligar a composição deste seletor e manter o fluxo anterior. Nenhuma
migração, alteração canônica ou dado auxiliar precisa ser revertido.
