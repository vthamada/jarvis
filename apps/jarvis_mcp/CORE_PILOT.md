# Piloto MCP → evidência no Core — WP-MCP-01

Este slice complementa o client stdio readonly existente com um relatório pelo
Core real, em SQLite temporário fora do workspace. Não altera bootstrap normal,
registry, autenticação ou o serviço operacional. Não é promoção de capability.

## Fluxo e fronteira de autoridade

1. Opt-in explícito `--authorized` habilita somente este experimento.
2. O client fixo inicia o servidor fixture próprio, faz initialize/list e chama
   exclusivamente `read_fixture_status(record_id="health")` por stdio real.
3. A observação é validada contra principal/sessão, request RPC 3, ferramenta,
   servidor, protocolo, evidence mode e `authority="none"` esperados.
4. Uma projeção local entra no Core: status enumerado, comprimento e SHA-256 do
   texto, request RPC e labels locais fixas. Texto bruto, descriptors, credentials
   e stdout/stderr não entram no prompt nem na memória canônica. O hash é apenas
   evidência de conteúdo, não instrução ou atestado de identidade.
5. Core interpreta, verifica governança, mantém memória canônica e produz a síntese
   final. O piloto verifica o vínculo request/sessão, turno persistido, ausência de
   dispatch/grants e os eventos governance_checked/response_synthesized/memory_recorded.
6. Diretórios próprios de MCP e SQLite são removidos após encerramento; a CLI
   imprime apenas metadados sem texto bruto, síntese, labels pessoais ou caminhos.

`synthetic_ready` exige igualdade exata à mensagem constante da fixture; texto
desconhecido ou instruções hostis viram `unrecognized_untrusted_text`, nunca health=ok.
Resposta malformada, drift de descriptor/protocolo, timeout ou cancelamento na coleta
impedem entrada no Core. Cancelamento após coleta ou durante setup também impede
handle_input. Cancelamento de task encerra e recolhe o subprocess próprio; não
reaproveita a sessão fechada.

**A chamada MCP precede o relatório.** O Core governa a análise da evidência, não o
despacho MCP anterior. Por isso `mcp_call_governed_by_core=false`,
`core_operation_dispatched=false`, `operator_authenticated=false` e
`runtime_capability_promoted=false`. FixtureBinding/scope e opt-in não são grants.
Não há MCP HTTP/OAuth, servidores terceiros, descoberta de credentials, sampling,
elicitation, operação no host, modelo externo ou acesso aos bancos humanos.

O timestamp de InputContract é o horário local de criação do relatório em UTC, não
atestado de horário do servidor. `local_subprocess_fixture` prova transporte real
da fixture, não integração de ferramenta real. `core_local` prova Core normal,
governança/memória/síntese; não prova modelo de linguagem conectado.

O deadline (0,01–10 segundos) limita a coleta MCP completa. Core é síncrono: o
piloto verifica cancelamento antes da entrada, mas não interrompe um turno Core
já iniciado. Higiene de ambiente/processo não equivale a sandbox de SO. Diretórios
temporários usam as permissões do operador e não oferecem isolamento multiusuário.

## Execução local

```powershell
.venv/Scripts/python.exe -m apps.jarvis_console.mcp_pilot --authorized
.venv/Scripts/python.exe -m apps.jarvis_console.mcp_pilot --authorized --scenario injection
.venv/Scripts/python.exe -m apps.jarvis_console.mcp_pilot --authorized --scenario timeout --timeout 0.8
```

O enum `--scenario` seleciona apenas falhas sintéticas do servidor próprio; não é
API para scripts, executables ou servidores arbitrários. Código de saída 0 significa
relatório isolado concluído, não aprovação de ferramenta/output/capability. 3 indica
coleta ou entrada recusada; 2 indica opções inválidas ou indisponibilidade, sem refletir
texto de exception.

Prova local em 03/10/2026: caso normal executou 3 eventos MCP e 29 eventos Core,
registrou turno canônico e final de 1086 caracteres; governança retornou
`defer_for_validation`, sem dispatch/grants. Não se declara ganho de capability.
O caso injection também gerou relatório, preservando status unrecognized; o caso
timeout foi recusado sem entrar no Core. A bateria local conjunta passou 99 testes
(56 do piloto Core e 43 do client MCP).

## Verificação e rollback

```powershell
.venv/Scripts/python.exe -m pytest tests/integration/test_mcp_core_pilot.py apps/jarvis_mcp/tests
.venv/Scripts/python.exe -m ruff check apps/jarvis_console/mcp_pilot.py tests/integration/test_mcp_core_pilot.py
.venv/Scripts/python.exe tools/engineering_gate.py --mode standard
```

Bateria inclui subprocess real + Core real (caso normal, injection e stderr secreto),
parsing exato, bindings de principal/sessão/request, output/authority drift,
cancelamento/event/deadline/task e reap, setup com prazo expirado sem handle_input,
descriptor/schema/error recusados antes
do Core, final e memória/eventos falsificados, redaction, opt-in e TEMP fora do
workspace. Injeções de falha são explicitamente doubles de teste, não evidência de
servers ou providers reais. O gate global é executado na integração da rodada.

Rollback: não executar o módulo opt-in; remover os três arquivos exclusivos deste
slice. Não há migração de banco, alteração central ou configuração persistente.
