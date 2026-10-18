# Piloto readiness MCP -> relatório soberano

Slice local opt-in de F13: uma leitura real do inventário autoral do repositório
via servidor MCP stdio fixo, seguida de um relatório pelo Core soberano em runtime
SQLite temporário. Não é despacho MCP de runtime governado pelo Core: a consulta
é anterior à governança do relatório. Não promove capability nem integra a CLI
central, a Web UI ou contas de inferência.

## Execução

```powershell
python -m apps.jarvis_console.readiness_mcp_pilot --authorized --front-id F13 --timeout-seconds 10
```

`--front-id` aceita `all`, `F01`–`F13` e `T01`–`T03`. O cliente já existente
`FixedReadinessMcpClient` usa processo Python próprio `-I -B`, diretório temporário,
ambiente mínimo e servidor local fixo. Nenhum endpoint, comando arbitrário,
credencial, dispositivo ou modelo remoto pode ser configurado pelo piloto.
O inventário consultado é o do repositório que contém o módulo, não uma fonte
HTTPS simulada. `--workspace` delimita apenas a proteção contra armazenar o
runtime temporário dentro desse caminho; não seleciona outro inventário.

Saída: JSON de metadados sem final textual, nomes autorais, caminhos de evidência,
identificadores de principal/sessão ou hash do inventário. Código de saída `0`
indica relatório local concluído; `3` indica coleta/entrada recusada; `2` indica
opções inválidas ou falha. Diagnósticos não refletem texto de exceções.

## Fronteiras preservadas

1. Opt-in explícito e validação de limites/seleção/binding antes do transporte.
2. Inicialização, descriptor, espelho textual/estruturado e contrato do snapshot
   validados pelo cliente existente. A observação é revalidada no consumo e
   vinculada à seleção, sessão/principal congelados e request MCP fixo `3`.
3. Projeção apenas de IDs/status enumerados, contagens e SHA-256 canônico.
   Nomes, descrições, claims, referências e datas autorais não entram
   no prompt, eventos ou memória. O hash é evidência de identidade do documento,
   não prova de veracidade ou autorização.
4. O Core recebe um pedido `assist_only`, sem escopo de capability, ação,
   grant ou confirmação. Sua governança, síntese final, Memory e observabilidade
   reais são executadas; bindings e ausência de dispatch/grants são verificados.
5. Readback SQLite ligado ao sujeito canônico estático do piloto
   (`user_id == canonical_user_ref`, nunca identidade humana inferida do operador).
   Eventos únicos `input_received`, `governance_checked`, `response_synthesized`,
   `memory_recorded` vinculados a request/session/correlation/source; ID de memória,
   check/decisão de governança e hashes/timestamp de `conversation_readback`
   existentes conferidos contra resposta e turno persistido. Reconstrução dos
   serviços exige o mesmo turno/final e envelopes completos idênticos, sem
   repetir MCP nem input. Nenhum contrato central/evento novo.
6. Remoção somente dos diretórios temporários próprios ao encerrar. O piloto
   não conserva um histórico operacional de produção; a prova de reinício vale
   para a reconstrução local antes dessa remoção.

`operator_authenticated=false`, `authority=none`,
`mcp_call_governed_by_core=false`, `core_operation_dispatched=false`,
`runtime_capability_promoted=false`, `snapshot_runtime_verified=false` e
`product_ready=false` permanecem explícitos. Status `validated_slice` do
inventário é uma declaração autoral e nunca muda esses valores. Opt-in e labels
Python não autenticam um humano.

## Limites e falhas

Timeout finito entre `0.01` e `10` segundos: coleta e cercas antes da criação
do Core e antes de `handle_input`. Cancelamento de evento/task fecha o cliente
e seu processo próprio. O trecho síncrono do Core não é interrompível após
entrada; prazo/cancelamento não desfaz uma escrita já iniciada. Contrato inválido,
tamper, falta de Memory/eventos ou divergência após reconstrução impedem atestar
sucesso. Nenhum retry, fallback, elevação de autoridade ou análise generativa.

## Verificação e rollback

```powershell
python -m pytest tests/unit/test_readiness_mcp_pilot.py tests/integration/test_readiness_mcp_core_pilot.py tests/integration/test_readiness_mcp_stdio.py
python -m ruff check apps/jarvis_console/readiness_mcp_pilot.py tests/unit/test_readiness_mcp_pilot.py tests/integration/test_readiness_mcp_core_pilot.py
```

Corpus positivo por seleção, claims adversariais/injeção, drift de binding,
autoridade e schema, cancelamento/prazo, final/grants divergentes, Memory/eventos
ausentes e readback após reconstrução. Fixtures de falha na composição não são
prova de um backend externo; o caminho positivo usa stdio e SQLite reais.
O gate integrado do repositório é executado pelo coordenador antes de fechar
a rodada. Rollback: deixar de invocar o módulo opt-in; não há alteração em
registry, bootstrap, contrato compartilhado ou comportamento padrão.
