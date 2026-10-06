# Observacao HTTPS credentialless - MB227

## Estado e fronteira

Implementacao local concluida em 2026-10-05. Bateria consolidada inicial:676
testes passaram, zero skips, incluindo regressao HTTP fixture. Depois:56 CLI
e22 runner passaram (78), incluindo novo preflight de texto forjado oversized
antes de encode;699 testes focados distintos aprovados/zero skips.
Auditoria independente:573 HTTPS passaram, sem bloqueador restante (duplicados
da bateria, nao somados ao total). Gate standard global Windows passou completo;
PYTEST_ADDOPTS=--maxfail=1 --tb=short apenas para diagnostico, sem excluir testes.
O gate global possui skips de perfis/plataformas; zero skips e somente a bateria
focada deste recorte, nao alegacao de cobertura universal.
Nao houve requisicao a alvo externo, login, acesso a store humano,
promocao de capability, commit ou push nesta rodada.

`CredentiallessHttpsReader` permite um GET HTTPS explicitamente autorizado para
uma URL canonica e um IPv4 publico numerico fixados pelo operador. E adapter
isolado e CLI standalone, nao browser engine, navegacao autonoma, pesquisa com
modelo ou ingresso governado no Core. Registries, memoria canonica, governanca
e sintese final nao foram alterados. Conteudo remoto tem `authority=none` e
`untrusted_data=true`: HTML, scripts e instrucoes permanecem dados, nunca codigo
ou instrucao executada. Referencias de principal/sessao/escopo/finalidade sao
bindings declarados, nao autenticacao ou grant.

## Uso explicito

API: `operational_service.adapters.browser.CredentiallessHttpsReader`,
`HttpsReadScope`, `HttpsReadRequest` e `HttpsReadLimits`. Cada `observe` exige
`authorized=True`; um reader ocupado recusa outra chamada. Scope e limites sao
copiados/revalidados antes de callbacks/I/O. Request deve repetir exatamente
os seis campos do scope. Nao existe descoberta automatica de alvos.

CLI independente, sem bootstrap do Core ou store:

```powershell
Get-Content -Raw -LiteralPath .\source.json |
  .venv/Scripts/python.exe -m apps.jarvis_console.https_read_cli --authorized
```

`source.json` deve conter exatamente `scope`, `request` e, opcionalmente,
`limits`. Exemplo de schema **nao funcional**, nao executar como campanha:

```json
{
  "scope": {
    "principal_ref": "operator:local",
    "session_ref": "session:read",
    "scope_ref": "scope:source",
    "purpose_ref": "purpose:read",
    "url": "https://example.test/document",
    "ipv4_pin": "8.8.8.8"
  },
  "request": {
    "principal_ref": "operator:local",
    "session_ref": "session:read",
    "scope_ref": "scope:source",
    "purpose_ref": "purpose:read",
    "url": "https://example.test/document",
    "ipv4_pin": "8.8.8.8"
  },
  "limits": {"deadline_seconds": 10}
}
```

O exemplo nao representa associacao DNS/certificado real. Campanha externa
requer escolha e autorizacao de alvo de leitura conhecido, pin correspondente
ao host e verificacao operacional pelo operador. GET nao garante ausencia de
efeitos no servidor. Pin e restricao de destino de rede, nao fingerprint de
certificado. Confianca TLS usa CAs nativas do sistema e hostname obrigatorio.

Sem `--include-content`, JSON omite URL, pin, texto, digest e identidades. Com
opt-in, conteudo exato/proveniencia sao exibidos apenas se o redactor existente
permitir todos os campos; caso sensivel, o bloco inteiro e omitido. Nunca se
altera texto mantendo hash original. Redacao e heuristica, nao garantia geral
de deteccao de PII. Queries podem conter dados privados fornecidos pelo
operador: nao inserir segredos na URL. O adapter nao anexa credenciais, cookies
ou identidade de cliente. JSON ASCII escaped nao executa HTML/ANSI.

Stdin UTF-8: ate64KiB, EOF obrigatorio, profundidade12, sem chaves duplicadas,
BOM ou numeros nao finitos. Nao ha deadline sobre produtor de stdin. Saida
ate1MiB. Exit0: observado;3: recusado/cancelado;2: input/opcoes invalidos.
Erros publicos fixos nao ecoam valores privados. `--help` nao le stdin/rede.

## Perfil de transporte e limites

- HTTPS443, host DNS ASCII lowercase, URL exata com slash/path e query opcional;
  sem userinfo, fragmento, porta explicita ou normalizacao oculta.
- IPv4 publico canonico: recusa redes privadas, loopback, link-local, multicast,
  reservadas e lista explicita de redes especiais. Perfil conservador tambem
  recusa todo192.0.0.0/24, incluindo excecoes globalmente acessiveis.
- Socket numerico: nenhum DNS, proxy, redirect, retry ou fallback. Host/SNI e
  peer conferidos; TLS minimo1.2, cadeia e hostname obrigatorios. API publica
  nao aceita CA/contexto customizado, verifyFalse ou rota privada.
- `SSLContext(PROTOCOL_TLS_CLIENT)` evita ativar keylog por `SSLKEYLOGFILE`;
  nao ha alteracao do ambiente global nem dependencia HTTP/crypto de runtime.
- HTTP1.1 status200, text/plain ou text/html UTF-8 estrito. Content-Length OU
  chunked, nunca ambos. Extensoes/trailers benignos bounded sao ignorados;
  framing ambiguo/duplicado, trailers criticos e gzip recusados.
- Exige EOF depois do corpo framed para detectar sobras tardias; envia
  Connectionclose. HTTP1.0,1xx,3xx,401/407 e corpo close-delimited sem framing
  explicito ficam fora deste perfil, mesmo quando validos no protocolo geral.
- Corpo256KiB; headers16KiB; trailers8KiB; linha de chunk4KiB;4096 chunks de
  dados; overhead64KiB. Limites podem diminuir, nunca ultrapassar tetos.
- Deadline unico default10s/teto60s; poll de socket <=100ms. Cancelamento e
  prazo conferidos antes/depois I/O, parse, crypto e cleanup. Operacoes nativas
  sincronas de trust/crypto/cleanup nao sao preemptiveis: nao e promessa de
  cancelamento hard-real-time. Nenhum resultado atrasado/parcial vira sucesso.
- Texto exato, UTC, URL exata, SHA256 e byte_count acompanham a observacao;
  controles binarios sao recusados, exceto CR/LF/TAB. Telemetria content-free
  e local ao adapter, nao novo evento compartilhado promovido.

## Threat model e provas

Corpus cobre SSRF/pins especiais/canonicalizacao, consentimento e mismatch de
bindings antes I/O; callbacks maliciosos, mutacao/reentrancia, erros privados;
DNS/proxy ausentes; partial send/SSLWantRead/Write, peer e SNI; CA desconhecida,
certificado expirado/hostname errado; smuggling CL+TE, linhas/framing/chunks,
extensoes/trailers/overhead, EOF/truncagem/sobras; UTF-8/binario, injection como
texto sem autoridade; cancelamento/deadline inclusive depois de cleanup;
CLI stdin->TLS->parser->JSON, integridade e redacao/default privacy.

TLS real usa CA/certificados sinteticos e servidor loopback temporario proprio.
Seams internas dos testes roteiam pin para esse servidor e confiam somente na
CA sintetica; nao existe flag de produto insecure/allow_private. Alguns casos
CLI sao `main` real in-process com stdin; subprocess prova recusas antes rede.
Isso nao prova campanha externa, Core/browser live nem Linux desta rodada.

`cryptography>=46` e somente dependencia **dev** para emitir certificados de
teste sem crypto caseiro. Runtime continua stdlib, `project.dependencies=[]`.
CI instala `.[dev]`; imagem do runner Linux declara cryptography==46.0.7 junto
a pytest/ruff somente dev.22 testes do runner passaram/zero skips, incluindo
coerencia metadata e delegacao ao gate completo. Nao houve rebuild Docker
nesta rodada; a imagem existente precisa ser reconstruida antes de nova prova.

```powershell
.venv/Scripts/python.exe -m pytest -o addopts='' tests/unit/test_https_contracts.py tests/unit/test_https_read_cli.py tests/unit/test_https_reader_callbacks.py services/operational-service/tests/test_https_protocol.py services/operational-service/tests/test_https_transport.py services/operational-service/tests/test_https_reader.py tests/integration/test_https_observation_flow.py services/operational-service/tests/test_browser_fixture_reader.py -q -ra --tb=short
.venv/Scripts/python.exe tools/engineering_gate.py --mode standard
```

Rollback: deixar de invocar/importar adapter ou CLI opt-in; nenhum store,
migration, grant ou registry a desfazer. Integracao ao Core e campanhas reais
exigem proximo slice proprio, governanca/evidencia e aceite de fase.

Repriorizacao: MB228 ready integra fonte revisada request-scoped ao caminho
nativo Knowledge/Governance/Synthesis/Memory. Um export JSON e declarado e
unverified, nao prova autenticada de origem/TLS; nenhum auto-trust/corpus import.
Nao fechar utilidade generativa, conta/modelo, voz real ou browser engine aqui.

Referencias primarias verificadas nesta implementacao:
[Python3.11 SSL](https://docs.python.org/3.11/library/ssl.html),
[RFC9112](https://www.rfc-editor.org/rfc/rfc9112.html),
[IANA IPv4 special registry](https://www.iana.org/assignments/iana-ipv4-special-registry)
e [cryptography X.509](https://cryptography.io/en/latest/x509/reference/).
