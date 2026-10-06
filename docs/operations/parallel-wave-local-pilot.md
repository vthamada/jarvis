# Primeira onda paralela: piloto local

Data: 2026-10-02. Desenvolvimento isolado, sem promocao de capability.

## Entregas

Tres implementadores entregaram modulos disjuntos; coordenador integrou contrato
e piloto vertical, sem nova dependencia central:

- `services/inference-service`: provider deterministico e adapter Responses
  com transporte injetado. Conclusao e EOF exigidos; falhas descartam texto
  parcial. Identidade, eventos, uso, limites e cancelamento validados.
- `apps/jarvis_web`: cockpit HTML/CSS/JS contra fixtures versionadas. Conversa,
  atividade, objetivo, inspecao readonly, erros, cancelamento e reset. Sem Core.
- `operational_service.adapters.code_sandbox`: patch CAS e interpretador AST
  aritmetico restrito, sobre copia imutavel em memoria. Sem exec/eval, imports,
  shell, subprocesso, rede ou escrita do patch no host.
- `apps.jarvis_console.code_pilot`: proposta JSON estrita -> patch fixture ->
  testes interpretados -> metadados allowlisted -> fluxo normal do Core com
  governanca, memoria e sintese final. Texto bruto nao vira instrucao/autoridade.

O Core pode deferir sob `assist_only`: testes do experimento nao alteram sua
decisao. Provider marcado live e recusado; nao houve modelo real conectado.

## Executar

Na raiz do repositorio:

```powershell
.venv/Scripts/python.exe -m apps.jarvis_console.code_pilot
.venv/Scripts/python.exe -m apps.jarvis_console.code_pilot --scenario test-failure
.venv/Scripts/python.exe -m apps.jarvis_console.code_pilot --scenario unsafe
.venv/Scripts/python.exe -m apps.jarvis_web.serve --port 8765
```

O piloto retorna 0 somente para fixture passed; negativos retornam 1. Saida
padrao omite fonte/diff/provider diagnostics. Runtime temporario persiste memoria
e eventos durante a leitura e e removido ao fim. Nao herda bancos/tracing do
operador. `candidate_host_effects=false` refere-se ao patch; SQLite temporario
e um efeito local explicitamente isolado, nao ausencia de toda escrita.

Abrir `http://127.0.0.1:8765/`; Ctrl+C encerra. Servidor estatico allowlisted,
loopback, GET/HEAD, sem conexao cliente ou credenciais. Nao servir a raiz inteira.

## Verificacao e limites

```powershell
.venv/Scripts/python.exe -m pytest services/inference-service/tests services/operational-service/tests/test_code_fixture_sandbox.py tests/unit/test_model_inference_contract.py tests/unit/test_sqlite_connection.py tests/integration/test_isolated_code_pilot.py apps/jarvis_web/tests/test_serve.py
node --test apps/jarvis_web/tests/controller.test.mjs
.venv/Scripts/python.exe tools/engineering_gate.py --mode standard
```

Casos positivos/adversariais e caminho integrado comprovam sintese Core, memoria,
nenhum dispatch e isolamento. Revisao cruzada corrigiu inconsistencias de
streaming e injeção de console de producao sob etiqueta temporaria.

Conexoes SQLite de Memory/Observability agora preservam commit/rollback e liberam
handles ao sair do contexto transacional, permitindo limpar runtime no Windows
sem GC. Nao e migracao de schema. Um probe inicial com builder padrao encontrou
`specialist_shared_memory.consumer_profile` ausente na base local antiga; piloto
final nao a reutiliza. Nenhuma limpeza/migracao dessa base foi feita.
Consulta readonly encontrou uma claim experimental em `runtime_request_claims`,
sessao `isolated-code-pilot`, deixada por esse probe inicial antes da falha;
nao houve turno final. Registro preservado, nao removido ou promovido.

Verificacao concluida: 240 testes Python da onda, 13 testes JS, browser smoke
desktop/mobile e gate standard completo passaram no Windows. Os skips dessa
plataforma nao comprovam backend Linux. Sem gate release ou promocao runtime.
Packaging recebeu src do inference-service e assets Web; wheel/instalacao nao
foram verificados (setuptools/wheel nao instalados na venv; sem download novo).

Ainda ausentes: OAuth/login/token/HTTP, inferencia real, API autenticada, aprovacao
Web autoritativa, sandbox de SO, patch real, deploy, voz e ganho autoevolutivo
demonstrado. Transporte sincrono tem deadline/cancel cooperativos: deve limitar
suas operacoes bloqueantes. Nao existe preempcao de Python arbitrario.

## Proximo recorte e rollback

Prioridade: fronteira cliente/Core autenticada e readonly, depois auth/provider
suportado com consentimento/evidencia real. Manter badge fixture ate isso existir.
Code precisa isolamento de processo/arquivos e permissionamento antes de patch
real. MB218/219 seguem abertos, sem fechamento da composicao fisica por estes WP.

Rollback: parar servidor/desativar piloto; remover novos pacotes e entries de
packaging/bootstrap/testes se necessario. Nao apagar dados/ledgers humanos.
A correcao de conexoes e reversivel separadamente.
