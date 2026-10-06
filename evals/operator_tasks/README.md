# Operator tasks v1 — WP-QUALITY-01

Tres tarefas de produto executaveis complementam o comparador de outputs curtos
em `evolution/empirical_runner`: relatorio fundamentado, artefato CSV revisavel e
retomada apos correcao entre sessoes. Nao mudam a politica do Core, memoria,
governanca, capacidade de ferramentas ou sintese final. Nenhuma dependencia nova.

## Corpus e avaliacao

`corpus.py` contem somente fontes publicas sinteticas, briefs, fatos esperados e
versao `operator-tasks-v1`. As estruturas sao frozen e aninhadas em tuples; o
digest SHA-256 abrange briefs, fontes e expected metadata. O teste fixa o digest
da versao: mudar a referencia exige revisao e versionamento, nao editar o grader
para fazer um candidato passar. O request nao inclui expected facts nem grader.

Os produtos tem campos tipados, e nao uma resposta narrativa unica:

- relatorio: fatos da correcao vigente, citacoes por spans contiguos, total
  aritmetico e resumo livre; variantes de resumo/span sao aceitas;
- artefato: os mesmos fatos/citacoes e CSV com linhas coerentes, nomes e tipo
  revisaveis; ordem das linhas e LF/CRLF nao importam. Formula, linha duplicada,
  coluna oculta ou caminho arbitrario nao passam. O harness nao grava o arquivo;
- retomada: fatos corrigidos, proxima acao de revisao e vinculos de sujeito,
  sessao anterior diferente, recibo de correcao e observacao de historico pelo
  port separado do JSON do candidato.

Toda saida precisa manter `draft=true`: passar no scorer nao autoriza compra,
escrita, execucao ou promocao. O scorer verifica a parte estruturada do produto,
nao julga estilo, todas as alegacoes adicionais do resumo, nem utilidade geral.
Por isso `requires_human_review=true` permanece mesmo quando os criterios passam.

Envelope JSON estrito: `binding`, `status=completed`, `product`. Binding contem
run/request/case/version/task digest/revision/subject/session. Produtos aceitos:
campos comuns `kind,draft,facts,citations,total`; report acrescenta `summary`;
artifact `filename,media_type,csv_text`; resumption `next_action,prior_session_ref,
correction_receipt`. Citacao: `key,source_ref,start,end`; indices Python de Unicode.
Campos extras (inclusive score/grader), chaves duplicadas, JSON invalido,
incompleto, nonfinite, booleano no lugar de inteiro, controle/surrogate e payload
acima de 16 KiB sao recusados. Narrativa/CSV ate 2048 caracteres; ate 8 fatos e
citacoes. Request ids frescos impedem replay mesmo no mesmo run/case/session.

## Runner e modos de evidencia

`OperatorTaskRunner` chama um `TaskPort.execute(ExecutionRequest)` registrado pela
composicao confiavel; a resposta tipada do port e o envelope do candidato sao
validados separadamente. O candidato nao fornece score, modo de evidencia, uso,
grader ou tempo. `Registration` nunca deve ser derivada de input aberto/modelo.

- `fixture`: `FixtureTaskPort` interpreta a gramatica sintetica das fontes;
  demonstra pipeline, scorer e bindings, nao inteligencia ou recall semantico.
- `core_local`: `core_pilot` executa o Core soberano existente com stores SQLite
  descartaveis separados por caso. Retomada grava duas entradas publicas na
  primeira sessao e pede continuidade na segunda sem colar fontes no prompt
  final; nao altera ranking/recall nem reescreve a resposta para passar.
- `model_real`: modalidade reservada a um port real, explicitamente registrado
  com transporte/uso observados pela composicao. Nenhum port de provider, OAuth,
  credencial ou request de rede e implementado aqui; nenhum resultado desta
  entrega e rotulado assim. Ports conhecidos rejeitam rotulo divergente.

Tempo monotonic observado no runner, deadline 0..120s e rejeicao ao retornar
tarde. Isso nao e hard timeout/preemption: um port sincrono travado precisa de
isolamento de processo fora deste pacote. Uso nao observado e `null`, nao zero.
Observacao de historico e recibo sao vinculos de trusted composition, nao prova
criptografica de autenticacao ou de que o modelo consultou memoria corretamente.

Exports incluem apenas case/version/digest, modo, outcome, contagens/criterios,
latencia, uso opcional e retrabalho. Nao exportam run/subject/session ids, fontes,
prompts, resumo, CSV, spans, exceptions ou nomes de arquivos. Nao ha escrita em
disco automatica, HTTP, rede, dispositivos, arquivos do operador ou persistencia
de resultados. Todas as metricas mantem `promotion_allowed=false` e
`improvement_claim=false`. Ganho exige comparador, repeticoes, holdout e review
adicionais; estas tres tarefas publicas nao satisfazem isso por si so.

## Reproducao e resultado honesto

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_operator_tasks.py tests/integration/test_operator_tasks_flow.py -q
.venv/Scripts/python.exe -m evals.operator_tasks.core_pilot --authorized
```

Execucao local em 2026-10-04: tres tarefas, cinco turnos/finais canonicos, 121
eventos. As tres tarefas retornaram `needs_decision`; governanca observada
`allow_with_conditions=3`, `defer_for_validation=2`. O port conservador nao trata
condicoes como autorizacao satisfeita. Produtos uteis/retomada semantica nao foram
demonstrados: o Core ainda nao entregou os produtos estruturados solicitados.
O comando exige opt-in antes de construir runtime, recusa TEMP dentro do repo,
usa somente runtime temporario e remove cada diretorio ao sair, inclusive erro.
DATABASE_URL/LangSmith do ambiente nao sao usados pelo Core isolado existente.

## Reversao e integracao

Este e um harness opt-in removivel; desativar significa nao executar o modulo.
Rollback remove apenas `evals/operator_tasks` e seus dois testes novos. Nao ha
alteracao em contratos centrais, caminho padrao de runtime ou permissoes.
Testes vivem nos testpaths existentes; o gate standard do integrador executa a
bateria. Integrador sincroniza HANDOFF/backlogs/documentacao operacional.
