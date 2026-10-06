# Rodada 2026-10-04 - recall inspecionavel e patch revisavel

Continuidade autorizada pelo operador, com tres workers e integracao central.
Sem dependencia central nova, modelo/rede/conta, API, commit/push ou efeitos
em arquivos humanos. Linux/Docker permanece deferred; MB218 in_progress e
MB219 blocked nao mudam de estado por esta rodada.

## Entregas e limites

`memory_service.recall` seleciona StoredTurn canonico por sobreposicao lexical
Unicode normalizada, sujeito e sessoes exatos, frescor e budgets. Resultado
inclui refs derivadas, motivos, exclusoes e `untrusted_evidence_only`.
Nao e recall semantico nem evidencia de verdade: lifecycle/correcoes so entram
como metadados explicitamente confiaveis da composicao. Contradicoes livres
nao sao resolvidas automaticamente. Detalhes: `services/memory-service/RECALL_SELECTION.md`.

`memory-recall` permite inspecionar evidencia em SQLite existente/quiescente
DELETE-mode. Exige caminho absoluto e escopo explicito; nao cria banco nem
instancia Core. Snapshot canonico deve listar as sessoes pedidas. Conteudo
e opt-in e bounded; saida padrao omite query, sujeito, sessao, caminho e texto.
Banco ativo/WAL, redirects ancestrais e arquivos acima de128MiB sao recusados.
Nao e sandbox contra outro processo do mesmo usuario nem API de autenticacao.

`PatchReviewer` gera diff deterministico sobre snapshot/allowlist em memoria,
com spans, preimages e hashes exatos. `verify` recusa stale/human edit/tamper.
O hash esperado deve vir de referencia confiavel guardada pelo caller, nao
ser aceito cegamente do candidato. `reviewable` nao equivale a codigo correto,
testado, grant, efeito fisico ou aprovacao. Nenhum arquivo e escrito ou
subprocesso iniciado; fixtures verificam a aritmetica por expectativas
independentes. Detalhes: `services/operational-service/CODE_PATCH_REVIEW.md`.

## Correcao central de escopo

Core verifica subject scope antes da claim de request e da resolucao de pause,
inclusive entradas opcionais LangGraph. Memory repete a verificacao antes de
recuperar contexto e preparar memoria de especialistas. Probes metadata-only
consultam todo o historico de turnos, nao apenas a janela recente. Um sujeito
explicito nao recebe sessao/missao com owner estrangeiro/nulo ou estado
persistido sem prova de owner; novas sessoes vazias continuam permitidas.
Missoes relacionadas tambem exigem prova canonica, nao `session_origin` ou
`owner_context` derivado. Contexto legado sem `user_id` continua unbound.
Sessao de origem e refs de missao do contexto recorrente de especialistas
tambem sao revalidados antes do reuso. Contaminacao posterior nao preserva
elegibilidade por ter uma row antiga com user_id exato. Historico proprio
continua elegivel; lifecycle nativo ainda decide quais campos podem ser usados.

Nao migramos dados legados automaticamente. Atribuir owner ou dividir uma
sessao mista exige reconciliacao explicita futura. Probes nao reservam primeiro
uso concorrente de sessao vazia e nao autenticam identidades declaradas. Nao
apresentar essa mudanca como isolamento completo multiusuario. Metodos internos
que aceitam apenas session_id continuam APIs confiadas, nao endpoints publicos.

PostgreSQL recebeu a tabela de pause resolutions ja prevista em seus metodos
existentes; faltava inicializacao. Paridade SQL pode ser testada estruturalmente,
mas banco PostgreSQL real/controlado nao foi exercitado nesta rodada.

## Evidencia e proxima prioridade

Fixtures SQLite descartaveis verificam selecao/scopes, ausencia de escrita,
isolamento e entrada Core antes de efeitos. Nunca abrir DB humano nos testes.
177 testes focados passaram, com1 skip honesto de symlink Windows. As34
regressões centrais passaram. A fixture antiga de recorrencia foi alinhada com
turno canonico de origem, sem flexibilizar a guarda de contexto orfao.
O gate agregado e os totais finais ficam no HANDOFF; suite coletada nao e suite
passada e skips Windows nao substituem Linux.
Gate standard global final Windows passou apos as ultimas correcoes. Coleta
final3192 nao equivale a3192 passes; skips permanecem explicitamente sem prova.

Auditoria confirmou que `operator_tasks` ainda nao demonstra os tres produtos:
classificador lexical mistura pedidos de draft/analise e negacoes de execucao;
planejamento pede clarificacao e Governance preserva corretamente isso.
A sintese nativa ainda retorna prosa estrutural, nao os produtos pedidos.
Nao enfraquecer governanca, trocar final fora do Core ou alterar grader.
Proximo recorte de produto: interpretacao de intencao com corpus adversarial
e candidato de inferencia validado pela sintese soberana. Modelo real, auth,
utilidade conversacional e recall semantico permanecem pendentes.

## Operacao e reversibilidade

Para inspecao CLI, use exclusivamente banco autorizado e quiescente; instrucoes
e exemplo em `apps/jarvis_console/MEMORY_RECALL_CLI.md`. Nao abrir stores de
operadores durante testes. Em sessao legada/mista recusada, nao remover a guarda
ou inventar owner; reconciliar explicitamente dados/identidades em recorte futuro.

Seletor e patch reviewer sao complementos sem estado: desativar composicao nao
exige desfazer dados. Uma reversao central deve ser revisada por hunk, preservando
o restante do worktree pendente, e repetir o gate adequado. A tabela PostgreSQL
alinhada pode permanecer vazia; nao apagar dados ou schema como rollback.
