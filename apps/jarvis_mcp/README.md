# MCP local readonly — WP-MCP-01

MB234 done local, standard global Windows aprovado: servidor/client proprios
do inventario autoral, tool read_product_readiness e CLI opt-in. Sem Core bridge,
contas ou servidor externo. [Runbook](../../docs/operations/web-projection-and-readiness-mcp.md).
O experimento fixture abaixo permanece independente e inalterado.

Experimento isolado sem SDK ou dependência central: client e servidor fixture próprio
conversam por stdio JSON-RPC real em subprocess. Só existe a tool
`read_fixture_status(record_id="health")`, cujo dado é sintético e constante.
Não consulta memória canônica, arquivos pessoais, credenciais ou rede.

## Uso local

```python
import asyncio
from apps.jarvis_mcp import FixtureBinding, LocalFixtureMcpClient

async def probe():
    binding = FixtureBinding("operator://local", "session://mcp-probe")
    async with LocalFixtureMcpClient(binding) as client:
        observation = await client.call(
            binding, "read_fixture_status", {"record_id": "health"}
        )
        return observation.metadata()  # sem texto externo

print(asyncio.run(probe()))
```

`FixtureBinding` congela principal/sessão/scope para impedir drift entre chamadas;
**não autentica ninguém nem concede autorização**. O scope aceito é exclusivamente
`("fixture.read",)`. O descriptor remoto e sua annotation `readOnlyHint` são dados:
não promovem tools nem atribuem autoridade. A allowlist local define toda chamada.

`McpObservation.text` é saída externa não confiável; inclusive instruções hostis são
preservadas como **dado**, nunca executadas. `authority="none"` e
`evidence_mode="local_subprocess_fixture"` são explícitos. `metadata()` exclui o texto
e pode compor evidência para uma integração futura controlada pelo Core. Este slice
não implementa despacho pelo Core, autenticação, MCP HTTP/OAuth, registry global,
servidores reais ou promoção de capabilities.

## Limites e encerramento

- Python absoluto `-I -B`, script fixture fixo, sem shell ou comandos arbitrários.
- CWD temporário próprio; environment vazio salvo `SystemRoot` no Windows; stderr
  descartado sem reflexão. Isso é higiene de processo, **não sandbox de SO**.
- Handshake `initialize` → `notifications/initialized` → `tools/list`; versão e
  descriptor exatos. Servidor não pode solicitar sampling/elicitation/roots.
- JSONL UTF-8 de até 64 KiB/mensagem e 256 KiB/sessão; rejeição de JSON inválido,
  chaves duplicadas, ids divergentes, schemas desconhecidos e resultados não-texto.
- Uma chamada de cada vez; texto de até 4096 caracteres; timeout configurável de
  0,01 a 10 segundos por espera de transporte; até 32 requests por sessão.
  Até 128 eventos, fechando sessão antes de aceitar chamadas sem espaço de audit.
  Sem retry implícito.
- Cancelamento por `asyncio.Event`, timeout ou cancelamento de task: sessão fechada,
  subprocess próprio finalizado e reaproveitamento recusado. Eventos são limitados
  e não incluem argumentos, bindings pessoais, stdout/stderr ou texto de tool.
- Encerramento fecha stdin, espera brevemente e depois terminate/kill se necessário;
  diretório temporário próprio removido após término.

`fixture_scenario` tem enum finito exclusivo de testes de falhas e não permite
selecionar um script, caminho, executable ou commandline externos.

## Evidência e fontes

```powershell
.venv/Scripts/python.exe -m pytest apps/jarvis_mcp/tests
.venv/Scripts/python.exe -m ruff check apps/jarvis_mcp
```

Bateria inclui fluxo real init/list/call, binding e arguments recusados antes do
despacho, drift de versão/schema/id, limites, output hostil como dado, stderr,
timeout, cancelamento, concorrência e fechamento do processo próprio.

Recorte baseado na especificação MCP 2025-11-25:
[stdio](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports),
[lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle),
[tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools).
Não pretende ser um client genérico nem suportar toda a especificação.
