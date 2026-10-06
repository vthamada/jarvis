# Segunda onda: console fisico, snapshots e jobs

Data: 2026-10-02. MB218 em andamento; nenhum novo runtime promovido.

## O que existe

- Console `physical` integrado ao registry, parser, referencia e completions.
  Composicao explicita de Governance, Operational, Memory e Observability,
  com autoridades de receipt e attestation MB217 compartilhadas. Preparation,
  inspecao, confirmacao exata, execute, status, recovery e rollback delimitado.
- Exportador de objetivos/work items/artefatos pelo caminho de inspecao do Core
  real. SQLite da origem readonly, sem inicializacao/migracao/fallback; eventos
  locais ficam em runtime temporario. Artefatos sem versao sao omitidos, nao
  recebem versao inventada. Projecao JSON legada nao comprova efeito fisico.
- Web importa arquivo JSON offline com contrato v1, limites, validacao estrita,
  rejeicao de chaves duplicadas e protecao contra imports atrasados. Objetivos,
  artefatos e atividade sao visiveis sem substituir identidade/conversa fixture.
- `job-service` persiste steps fixture em SQLite: CAS, fencing, leases, deadline,
  retries limitados, cancelamento e reopen sem autoexecucao. Worker exige chamada
  explicita; nao ha scheduler, rede, subprocesso ou ferramenta real.

## Ver o estado do Core na Web

Usar banco explicito existente e quiescente em modo DELETE, com schema atual.
WAL, sidecars, banco ausente ou schema legado incompatível sao recusados sem
tentativa de reparo. Nao rodar exportacao contra store live concorrente; este
slice nao e backup/snapshot consistente de writers simultaneos.

```powershell
.venv/Scripts/python.exe -m apps.jarvis_console.snapshot --memory-db C:\caminho\runtime\memory.db --mission-id mission://id-real --output C:\caminho\snapshot-novo.json
.venv/Scripts/python.exe -m apps.jarvis_web.serve --port 8765
```

Na Web, selecionar explicitamente o arquivo pelo importador. `--output` cria
UTF-8 sem BOM e nunca sobrescreve arquivo existente. O arquivo pode conter
objetivos e referencias privados; proteger/compartilhar como dado humano.
O banco nao e enviado ao navegador. Limite 64 KiB/100 itens por colecao;
estados maiores sao recusados, nao truncados silenciosamente.

O badge diz origem nao verificada: `principal_ref` e rotulo, nao login, assinatura
ou credencial. Dados importados nao aprovam acoes. Conversa ainda e fixture;
nao existe API Core, conexao live, polling, armazenamento do snapshot no browser
ou consentimento OAuth nesta entrega. Se o servidor estatico ja estava aberto,
reiniciar pelo terminal para carregar o novo allowlist de assets.

## Console fisico opt-in

Detalhes e API: `apps/jarvis_console/PHYSICAL_OPERATIONS.md`. A CLI tem ajuda
completa e referencia gerada em `docs/operations/jarvis-console-command-reference.md`.

```powershell
.venv/Scripts/python.exe -m apps.jarvis_console physical --help
```

Todas as acoes exigem `--runtime-dir` absoluto e roots existentes declarados por
`--root notes=C:\caminho\notes`. Exige missao/work item canonicos ativos no
runtime selecionado; nao herda `DATABASE_URL` ou tracing do ambiente. Preferir
runtime dedicado, nunca apontar a base humana antiga por conveniencia.

Windows CLI: somente prepare, sem store duravel de requests, execute/recovery
ou promessa de retomada entre processos. Prepare nao escreve no root alvo;
pode criar ledgers de metadados no runtime selecionado. Input e UTF-8 NFC,
newlines LF (CRLF e recusado), ate 256 KiB. Preview/diff omitido por padrao;
`--show-diff` e escolha explicita para visualizar conteudo sensivel.

Linux: runtime owned 0700, roots nao redirecionados e `.jarvis-transactions`
preexistente privada por root. CLI `--enable-execution` e obrigatorio para
execute/recover/rollback; nao remove confirmacao, grants, reserva, journal,
receipt, attestation ou commit canonico. Requests locais owned 0600 guardam
input sensivel do operador, nunca o contrato efemero de preflight nem diff.
Plano/identidade/challenge/receipt ficam vinculados exatamente a Governance.
Status nao faz observacao fisica fresca. Cache nao concede autoridade.
Ownership de missao/work item e canonico; ownership humano multiusuario duravel
nao foi implementado (owner_context legado nao persiste em Memory).

Rollback canonico suporta replace com predecessor superseded; nao e undo-create
generico. Recovery nao abandona saga despachada nem repete efeito por conveniencia.
Resultado nao completed retorna falha na CLI e precisa inspecao/reconciliacao.
Fallback sem journal revalida missao/work item/objetivo antes de request novo;
reconciliacao historica continua apos pausa. MB219 registra endurecimento central
do primeiro claim e corrida pausa/precheck/efeito: guarda local nao e prova
atomica do kernel para consumidores diretos. Nao expor API antes desse fechamento.

## Jobs: limites de autoridade

API e evidencia em `services/job-service/README.md`. Somente task refs
`fixture:success`, `fixture:failure` e `fixture:needs_decision`; nao aceita codigo
ou callback arbitrario. Actor/session sao bindings, nao autenticacao. Approved
step ref e metadado, nao permissao verificada. Lease de worker nao e lease fisica
MB217; nao garante exactly-once para efeitos externos. Needs_decision continua
parado; notificacao/revisao humana real e integracao Core ficam para outro slice.

## Validacao e retomada

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_physical_operations_console.py tests/unit/test_physical_bootstrap.py tests/integration/test_physical_cli.py tests/integration/test_physical_operations_console_integration.py tests/unit/test_surface_snapshot.py tests/integration/test_surface_snapshot_export.py services/job-service/tests apps/jarvis_web/tests
node --test apps/jarvis_web/tests/controller.test.mjs apps/jarvis_web/tests/snapshot.test.mjs
.venv/Scripts/python.exe tools/engineering_gate.py --mode standard
```

Teste E2E exporta Memory real pelo Core e importa o resultado no controller Web;
hash da origem permanece igual. Revisao cruzada encontrou e corrigiu redirects
de ledgers e sidecars WAL criados por readers; ha regressao para ambos. CLI
positiva real e recusas Windows verificadas. Pytest global inclui agora tambem
os testes do console anteriormente fora de testpaths.

Fechamento desta onda: gate standard global final passou, assim como Ruff,
document guardrails e diff-check. Bateria focada: 154 testes Python passed,
8 skipped (sete Linux, um symlink que exige privilegio OS) e 25 testes JS passed.
Browser confirmou DOM inicial da importacao; automacao do file chooser nao
completou, sem alegacao de importacao visual. Controller E2E passou. Tab/servidor
exclusivos do teste encerrados; servidor 8765 do operador preservado.

Nesta maquina WSL so oferece docker-desktop sem Python e Docker daemon esta
parado. Nenhum servico foi iniciado, pacote instalado ou backend simulado.
Testes fisicos Linux ficam skipped: isso nao fecha MB218, nao abre MB219 nem
comprova release. Proxima prioridade integrada e executar/corrigir a bateria
fisica real Linux, depois gate release e revisao MB219; OAuth/API continuam
dependentes. Frentes isoladas restantes podem prosseguir sem essa promocao.

Rollback deste slice: retirar consumidores/novo comando e restaurar assets
gerados; parar servidor explicitamente. Preservar ledgers e inputs humanos,
sem apagar/migrar runtime existente. Nenhum commit/push nesta rodada.
