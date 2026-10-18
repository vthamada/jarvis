# Retomada duravel de tarefas nativas

Inicio: 2026-10-16; fechamento: 2026-10-17. Recorte F05 opt-in validado
localmente, sem depender do MB236. Gate standard Windows aprovado.

## O que funciona

Uma tarefa assist-only pode guardar uma pergunta privada benigna no ledger
existente e ser retomada explicitamente pelo ID, sem reenviar a pergunta.
O runner chama o Core nativo, que mantem governanca, sintese final e memoria
canonicas. Nao ha modelo, ferramenta externa, scheduler ou execucao ao abrir
o armazenamento. O loop de modelo/ferramenta da F01 nao e retomavel por este
runner; composicoes generativas, extrativas ou com esse loop sao recusadas.

| Estado apos interrupcao | Proxima retomada explicita |
| --- | --- |
| Input salvo, dispatch ainda nao iniciado | Claim novo, ou transferencia do mesmo dispatch apos lease expirada; uma tentativa. |
| Dispatch iniciado, lease ainda ativa | Apenas informa claim ativo, sem ler memoria possivelmente em escrita. |
| Dispatch iniciado, lease expirada e final canonica completa comprovada | Reconcilia recibo no ledger, sem chamar Core novamente; claim ativo tem precedencia. |
| Dispatch iniciado, final ausente/parcial/ambigua | `needs_decision`, sem replay nem novo request ID. |
| Cancelada ou pausada manualmente | Mantem a decisao, mesmo que apareca uma resposta antiga. |
| Concluida | Revalida recibo e recupera a mesma final canonica, sem inferencia. |

Um marcador `started` e commitado antes de chamar o Core. O Core reserva o
request ID deterministico globalmente antes de seus efeitos; a retomada nao
apaga essa reserva. A janela entre marcador e entrada no Core pode deixar
uma tarefa inconclusiva mesmo sem resposta: a seguranca e nao repeti-la.
Crash depois de salvar o turno, mas antes de flush dos eventos, tambem nao
autoriza adivinhar sucesso. Cancelar nao desfaz escritas ja feitas pelo Core.

## Persistencia e limites

- `DurableCoreJobStore` acrescenta uma tabela opt-in ao mesmo `jobs.db` v1.
  Input de ate 2048 bytes UTF-8, escopo, request/session deterministicos e
  fingerprint imutavel ficam ligados ao job. Nao e nova memoria factual,
  indice de recall ou permissao de execucao. APIs genericas de worker/retry
  recusam esse tipo; tentativa e no maximo uma.
- Claim, versao, fencing, prazo e binding sao revalidados antes do dispatch
  e dos commits. Um worker antigo perde autoridade; cancelamento e sticky.
  Estados/fase sao observaveis nos metadados; nao existe historico separado
  de todas as transicoes nesta tabela.
- A resposta nao e duplicada no ledger. O recibo readonly exige request
  claim, quatro eventos correlacionados, principal/sessao/superficie/input,
  hash da final, registro de memoria e timestamp exatos. Recusa drift,
  duplicidade, execucao de operacao/especialista/modelo ou stores em mutacao.
- So ALLOW nativo vira `succeeded`; BLOCK, DEFER e ALLOW_WITH_CONDITIONS
  resultam em `needs_decision`, sem concessao de autoridade. Hash e recibo
  comprovam consistencia local, nao autenticidade, verdade ou utilidade.
- Recuperar depois do prazo so registra uma final originalmente commitada
  dentro do prazo. Nao permite nova execucao apos deadline. Os dois bancos
  canonicos e o ledger nao compartilham transacao: nao e exactly-once generico.
- Metadados nao expoem input/final. O texto privado fica em SQLite sem
  criptografia, protegido pelas permissoes do SO. Flags/actor/session nao
  autenticam pessoa; hashes/IDs nao anonimizam texto ou identidade.

## Uso local explicito

Escolher um diretorio novo privado, fora do repositorio e do OneDrive, cujo
pai ja exista; por exemplo, uma subpasta dedicada de LocalAppData. A CLI
recusa roots/home, symlinks/reparse points, arquivos hardlinked e pasta
preexistente sem marcador proprio. No POSIX exige ownership/permissoes
privadas. Esse preflight de host confiavel nao e sandbox adversarial de
handles, prova de ACL Windows ou protecao contra usuario host malicioso.

Fornecer este documento por stdin UTF-8/EOF; nao colocar pergunta em argv:

```json
{"schema_version":"jarvis-durable-core-input-v1","query":"Compare documentation and observability pilot reports."}
```

```powershell
python -m apps.jarvis_console.durable_task_cli submit --authorized --confirm-input --runtime-dir ABSOLUTE_PRIVATE_NEW_DIRECTORY --job-id daily-task --actor-ref local-operator --session-ref daily --deadline-seconds 600
python -m apps.jarvis_console.durable_task_cli resume --authorized --runtime-dir ABSOLUTE_PRIVATE_NEW_DIRECTORY --job-id daily-task --actor-ref local-operator --session-ref daily --expected-version 0
```

Substituir placeholders; manter o mesmo diretorio/IDs em restart. `submit`
somente persiste input confirmado; `resume` executa ou recupera conforme estado.
Usar sempre a versao retornada em `job.version` na proxima chamada, nao repetir
cegamente o exemplo com zero. `pause`/`cancel` usam os mesmos argumentos e versao
atual; nenhuma pausa e desfeita automaticamente. Nao ha fila em background.

`--include-content` e opt-in adicional somente de `resume`: rele a final da
memoria canonica depois de conferir o recibo. Filtros de padroes conhecidos
podem reter conteudo; nao sao DLP universal. Nao incluir segredos em input.
Exit 0 significa comando tratado: inspecionar estado/error_code no JSON,
nao supor tarefa aceita. Recusa retorna 2; interrupcao propagada a CLI retorna 3.
Interrupcao dentro do runner preserva checkpoint inconclusivo e retorna seus
metadados, sem retry; nesse caminho o comando tratado pode retornar 0.

`evidence_mode=canonical_recovery` distingue recuperacao de execucao fresca;
`core_invoked=false` acompanha a recuperacao. `result_recorded` nao implica
`result_accepted`: recusas canonicas continuam requerendo decisao. O resultado
de um job cancelado nao e aceito nem exposto por essa interface.

## Verificacao

Workers disjuntos implementaram store/checkpoint, recibo readonly e testes
de queda real; integrador implementou runner/CLI e centraliza subprocessos.
Sem processos pelos workers. Codex Process Jobs nao suporta win32; testes e
gate executados em primeiro plano conforme autorizacao existente do operador.

- Primeiros 54 testes do store e dois fluxos positivos com Core real passaram.
- Regressao RED comprovou leitura prematura de SQLite no claim ativo; runner
  passou a retornar antes da leitura canonica enquanto lease esta ativa.
- Primeira bateria integrada: 140 passed/10 failed. Falhas limitadas aos
  testes de recibo: query ativava especialista e corrupcao SQL esbarrava nos
  triggers append-only. Guards intactos; corrupcao apenas na base descartavel
  depois de contraprovar a protecao. A troca por greeting tambem selecionou
  especialista: 40 setups falharam. Fixture final usa a mesma pergunta analitica
  ja comprovada no E2E e confere contagens de especialistas zeradas.
- Primeira regressao ampliada: 559 passed/6 skipped/4 failed/40 errors. Alem
  da fixture acima, duas recusas de permissao no sandbox Windows (temp/hardlink)
  e um crash esperado nao atingido. Este ultimo revelou defeito real da lease
  fracionaria: float persistido divergia do datetime do claim por submicrossegundo.
  Banco original tambem reproduz a divergencia de 238ns; RED deterministico
  comprovou `claim_conflict`. Novo store persiste a mesma
  precisao microsecond do JobClaim, sem relaxar igualdade de CAS/lease.
- Revisao independente encontrou busyguard por fase incompleto, factory Core
  da CLI antes do guard e texto Unicode aceito mas incompativel com recibo.
  Cinco REDs reproduziram essas bordas e preflight sem binding. Guard agora
  cobre todo running ativo antes de leitura/factory; texto e validado antes
  de claim; ultima validacao revalida fingerprint e fase do checkpoint.
  Tres positivos finais (recibo, conditional e drift apos marcador) passaram.
- Tres subprocessos fixos morrem de verdade antes do dispatch, apos marcador
  e apos commit canonico. A recuperacao valida novo processo, fencing/uma
  tentativa, nenhum replay de dispatch incerto e uma unica final no Core.
- Cobertura adicional: escopo/versao/drift, opt-in, prazo, cancelamento/pausa,
  resultado condicionado, readonly e privacidade. Nao usa modelo, OAuth,
  credenciais, Docker ou efeitos externos. Validacao Linux nao feita aqui.

Regressao ampliada final em host Windows: 612 passed, 6 skipped, zero falhas/
errors em 159.07s; cobre os quatro arquivos novos e consumidores anteriores
de job, CodeFixture e export canonico. Os skips sao de plataforma/symlink,
nao validam outra plataforma. Ruff global, diff-check e gate quick passaram.
Smoke CLI adicional em tres processos separados passou: submit registered,
primeiro resume succeeded/Core chamado, segundo resume canonical_recovery/
Core nao chamado, final verificada, attempts=1 e versao inalterada. Runtime
somente sintetico em `durable-task-cli-smoke-20261016` no pai dos artefatos.
Gate standard Windows em primeiro plano concluiu exit0: 10131 passed,
121 skipped/10252 casos/zero falhas/errors em965.62s. XML confirma os totais;
12 hashes de fonte/testes preservados. Skips nao homologam outro ambiente,
modelo ou qualidade da resposta. Codigo/testes nao mudaram durante o gate;
apenas docs/inventario foram sincronizados depois.
Artefatos locais, fora do Git, em
`C:/Users/vtham/.codex/visualizations/2026/08/11/019ff2ec-5e21-75a2-a819-f8cf4aa2b4e0/durable-task-gate-20261016/`
(`source-manifest.json`, `standard.log`, `standard.xml`). A regressao tem seu
proprio `durable-task-host-regression-20261016/regression.xml` no mesmo pai.

## Desativacao e proximos aceites

Nao invocar nova CLI/runner retira o slice; construtores nao retomam nada.
O store padrao e os pilotos anteriores permanecem disponiveis. Nao apagar
ledger, reservas de request ou memoria para forcar retry. Nenhum reset/migracao
destrutiva, commit, push ou merge faz parte desta rodada.

Pendentes: continuacao duravel de passos de modelo/ferramenta; recibos e
reconciliacao de efeitos externos; executores reais aprovados, agendamento,
notificacoes e projecao de retomada na Web. F05 permanece foundation; MB236
blocked/ultimo MB235 preservados. Nao e um JARVIS autonomo completo.
