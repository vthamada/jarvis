# Observacao HTTP fixture e HTTPS isolada

## HTTPS credentialless - MB227

`CredentiallessHttpsReader` acrescenta GET HTTPS opt-in de URL canonica e IPv4
publico fixados, TLS nativo com cadeia/hostname/SNI e framing/bytes/prazo bounded.
CLI: `python -m apps.jarvis_console.https_read_cli --authorized`, JSON por stdin;
sem Core/store/grant, default content-free, texto/proveniencia opt-in.
Nao e browser engine nem campanha externa comprovada. API nao permite DNS,
proxy, redirect, retry, credentials ou trust inseguro. Conteudo nao confiavel
tem authoritynone; nenhuma execucao de HTML/JS.

Perfil, threat model, limites, corpus TLS real sintetico, rollback e estado de
validacao: [runbook MB227](../../../../../../docs/operations/credentialless-https-observation.md).

## HTTP fixture existente

`FixtureHttpReader` faz um único GET real para `http://127.0.0.1:PORT/PATH`
explicitamente configurado. É observação HTTP de fixture, não browser/computer
use completo. Sem DNS, proxy, redirects, cookies, login, JS, clique, download,
escrita em arquivos, subprocesso ou dependência nova. O GET não prova que um
servidor escolhido pelo operador seja livre de efeitos: configure somente um
endpoint fixture de leitura conhecido.

`FixtureReadScope` fixa URL, principal, sessão, escopo e finalidade. A igualdade
do request delimita o consumer, mas **não autentica** principal nem concede
permissão do Core. O perfil aceita somente IPv4 numérico `127.0.0.1`, porta
explícita e path simples sem escapes, query, fragmento ou traversal. Headers e
body têm limites; Content-Length é obrigatório; somente text/plain e text/html
UTF-8 são dados admissíveis. HTML, scripts e instruções de injection continuam
texto não confiável, nunca instruções executadas.

Resultado: status/error_code, texto, URL exata, instante UTC, digest e tamanho.
`telemetry()` omite texto, URL, digest e referências de identidade. O evento é
local ao adapter isolado, não um novo evento compartilhado promovido. Prazo total,
timeout de inatividade e cancelamento são conferidos entre blocos de I/O; polling
de leitura tem até 50 ms. Não há retry nem worker em background.

Exemplo de consumer (a URL deve apontar para seu fixture de leitura):

```python
from operational_service.adapters.browser import (
    FixtureHttpReader, FixtureReadRequest, FixtureReadScope,
)

scope = FixtureReadScope(
    "operator://fixture", "session:fixture", "scope:fixture", "purpose:read",
    "http://127.0.0.1:12345/fixture",
)
reader = FixtureHttpReader(scope)
result = reader.observe(FixtureReadRequest(
    scope.principal_ref, scope.session_ref, scope.scope_ref, scope.purpose_ref, scope.url,
))
assert result.authority == "none"
```

Teste real em servidor local efêmero (não usa a porta do cockpit do operador):

```powershell
.venv/Scripts/python.exe -m pytest services/operational-service/tests/test_browser_fixture_reader.py
```

Não integrado ao Operational Service, registries, Core ou memória canônica.
Desativação: remover o consumer/import deste adapter; não há store a migrar.
Leitura externa e ações reais exigem slices, governança e gates próprios.
