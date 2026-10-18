# Resumo local de atividade de jobs (somente leitura)

Slice F05 opt-in, sem integração automática com Web ou scheduler. O módulo
`apps.jarvis_console.job_activity_cli` usa a projeção existente de
`job_service.readonly`, via `job_inspect_cli`, e não modifica seu contrato.
Não inicializa Core, worker, conta, banco, schema ou nova store.

## Uso autorizado

Use apenas um ledger SQLite local **existente e quiescente**, fechado, sem
WAL/SHM/journal, no modo DELETE e com schema v1 suportado. Informe um caminho
absoluto nativo do sistema operacional e entre 1 e 32 IDs distintos e explícitos.
O processo precisa ter permissão de leitura no host.

```powershell
python -m apps.jarvis_console.job_activity_cli --authorized `
  --job-db "C:\private\jobs.sqlite3" `
  --actor-ref "actor-one" --session-ref "session-one" `
  --job-id "job-one" --job-id "job-two"
```

O exemplo contém apenas labels sintéticos. `--authorized` registra a permissão
do operador para esta leitura; **não autentica identidade**. Actor/session e
referências de aprovação são bindings, não grants do Core. O banco privado deve
ficar fora do repositório e de pastas sincronizadas; os argumentos podem aparecer
na lista de processos ou no histórico do terminal do host. Não informe segredos
nesses campos. Não execute sobre stores em alteração concorrente.

## Contrato observável

A saída única JSON `jarvis-job-activity-v1` tem `read_only=true`, `authority=none`,
`operator_authenticated=false` e `activity_scope=explicit_selected_jobs_not_full_ledger`.
Não contém IDs, principal, sessão, worker, paths, deadlines, argumentos, textos,
artifacts ou resultados de jobs.

- `selected_job_count`: quantidade de IDs explicitamente selecionados; não é o
  total do ledger nem enumera jobs de outros principais/sessões.
- `status_counts`: contagens de registered/running/succeeded/failed/
  needs_decision/cancelled/expired, incluindo zeros.
- `evidence_counts`: separa fixture de metadata_ledger; nem uma claim nem um
  estado succeeded constitui prova de execução externa ou aceite de produto.
- `attempts_recorded`: soma das tentativas registradas no ledger, não novas
  tentativas iniciadas pela consulta.
- `progress`: grupos derivados desses estados: pending=registered,
  active=running, awaiting_decision=needs_decision e terminal=succeeded+failed+
  cancelled+expired. **Não representa percentual, sucesso nem trabalho restante
  estimado**. Needs_decision não é tratado como concluído.

Um running com lease vencida continua running. A leitura não consulta relógio
para reconciliar, reexecutar, renovar ou corrigir o registro. Reabrir a CLI não
retoma jobs, não faz retry, claim, cancel, notificação ou síntese final.

Ausência de autorização, referência inválida/duplicada, excesso de IDs, binding
divergente, ID ausente, schema incompatível, fingerprint inválido, source ativa
ou drift da projeção recusam a operação inteira: exit 2, stdout vazio, stderr
fixo `{"error_code": "job_activity_refused"}`. Nenhuma saída parcial revela a
contagem válida. O reader herdado usa SQLite `mode=ro` e query_only, valida
schema, registros e identidade do arquivo antes/depois. Isso não é isolamento
contra atacante same-UID, troca adversarial de descritor ou snapshot consistente
de banco ativo. Não há migração automática nem caminho alternativo de escrita.

Falhas de impressão (BrokenPipe/OSError/UnicodeError/ValueError) também retornam 2 sem
traceback ou texto da exceção. Se stderr estiver disponível, recebe apenas o
código fixo; se ambos os canais estiverem quebrados, nenhuma mensagem é
garantida. Uma falha física de saída pode ocorrer após parte do JSON público
ter sido escrita: não existe promessa de escrita atômica em pipes/terminais.
Print e flush ficam dentro da fronteira de erro. Depois de uma falha de I/O,
somente um `TextIOWrapper` real cujo descritor seja stdout (1) ou stderr (2)
pode ser redirecionado para o null device. Isso evita o segundo flush do CPython
no shutdown, que antes podia imprimir `Exception ignored` e trocar exit 2 por
120. Não redireciona streams saudáveis em recusas de validação/store, streams
fake ou descritores arbitrários. Se o próprio host impedir abrir/duplicar esse
descritor, o fallback é contido, mas o flush externo do interpretador não pode
ser garantido. A prova de pipes reais fechados usa subprocesso com barreira.

## Evidência e rollback

```powershell
python -m pytest tests/unit/test_job_activity_cli.py tests/integration/test_job_activity_cli_real.py
python -m ruff check apps/jarvis_console/job_activity_cli.py tests/unit/test_job_activity_cli.py tests/integration/test_job_activity_cli_real.py
```

A bateria cobre schema fechado, limites, autorização, privacidade, contagens,
isolamento, fingerprint, WAL e ausência de escrita com SQLite real. Um processo
writer separado termina abruptamente após commit da claim; dois novos processos
leitores preservam running, tentativas, versão/fencing e os fingerprints dos
arquivos. O integrador executa o gate global antes de fechar a rodada.

Rollback: não invocar o módulo. Ele não está registrado na CLI central nem
promovido como executor real, surface Web ou autenticação remota. Não exige
dependência central nova ou alteração no ledger existente.
