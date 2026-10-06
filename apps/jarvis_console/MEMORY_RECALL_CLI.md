# Inspeção local readonly de recall

`memory-recall` inspeciona evidências lexicais do SQLite canônico existente. É
standalone: não instancia Core, não cria banco/runtime default, não migra schema,
não chama modelo/rede e não autoriza efeitos. Não é autenticação pública ou
promoção de recall semântico. O operador local deve ter autorização para ler o
banco explicitamente selecionado.

```powershell
python -m apps.jarvis_console memory-recall `
  --memory-db 'C:\absolute\existing-memory.db' `
  --subject-id 'user://local_operator' `
  --session-id 'session-example' `
  --query 'orçamento' --limit 4 --format json
```

`--session-id` é repetível, explícito, sem inferência por prefixo. O snapshot
canônico deve existir com `user_id` exato e listar cada sessão. Membership não
prova ownership: `session_subject_is_compatible` verifica toda a história da
sessão, não somente os turns mais recentes. Sessão mista/orphan é recusada. O
seletor adicionalmente compara exatamente `StoredTurn.user_id` e sessão.

Por padrão, saída contém status/contagens, refs SHA-256, frescor/motivos e
`authority=none`; não contém query, texto, matching tokens, sujeito, sessão ou
caminho. `--include-content` é opt-in para trechos limitados e explicitamente
`untrusted_evidence_only`, nunca instruções ou autorização. JSON usa ASCII
escapado; texto escapa controles, bidi e separadores de linha Unicode. Erros não
ecoam SQL, caminho, ids, query, conteúdo ou mensagens internas.

Limites: banco regular absoluto até 128 MiB e single-link, sem aliases hardlink,
UNC, symlink ou reparse em
qualquer ancestral; até 32 sessões, até 100 rows inspecionadas, até 32 resultados
(`--limit`, default 4), query até 2048 caracteres, conteúdo total de saída até
4096 caracteres. Fonte acima do limite e scan acima de 100 são recusados, sem
sucesso parcial. Há deadline monotônico para a seleção; isso não promete limite
de tempo para todo o I/O/SQLite. A janela de frescor lexical é de 30 dias.

Reader exige SQLite quiescente DELETE-mode sem WAL/SHM/journal. Nenhum fallback
para `immutable=1` ou writable store. Preflight de caminho/tamanho não é
descriptor-walk anti-race nem sandbox de filesystem: usar cópia canônica
quiescente, controlada pelo operador. O comando não prova resistência a troca
concorrente de ancestral. Não fornecer SQLite arbitrário de origem não confiável.

O comando não inventa lifecycle/correction refs ausentes em `StoredTurn` nem
resolve contradições livres. O módulo readonly aceita metadata explícita de
correção/revogação fornecida pela composição; este CLI inicial não a cria a
partir de prosa. Duas alegações livres podem retornar como evidência concorrente.

Testes TEMP persistem rows reais e snapshots, exercitam CLI/registry, ausência de
factory Core, ownership histórico misto/orphan, saída padrão, opt-in seguro,
recusas e igualdade de bytes/inventário antes/depois. Teste físico de symlink pode
ficar skipped no Windows sem privilégio; reparse preflight usa fixture unitária
identificada, não prova física. Gate integrado é responsabilidade da rodada.

Rollback: não usar o comando standalone. Não há migração ou estado a desfazer.
