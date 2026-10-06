# Terceira onda: voz revisada e observacao HTTP local

Data: 2026-10-02. Desenvolvimento isolado, sem promocao de capability.

Gate standard global Windows passou; bateria focada 263 Python passed,
11 skipped (dez Linux, um symlink OS) e 25 JS passed. CLI do piloto voz/Core
completou com memoria/sintese reais e speech sintetico. Nenhum skip comprova
execucao fisica Linux; nao houve gate release nesta rodada.

## Entregas e prova

- `apps/jarvis_voice`: consentimento vinculado a identidade/sessao local,
  audio sintetico bounded, STT fixture completo, revisao da transcricao,
  confirmacao da revisao exata, sintese final e TTS/playback simulados.
  Cancelamento, troca de identidade, deadlines e resultados tardios sao testados.
- `apps/jarvis_console/voice_pilot.py`: o texto revisado percorre o Core real,
  governanca, memoria canonica SQLite temporaria e sintese soberana. So a
  resposta final do Core e elegivel para TTS fixture. Usa canal voice/input text,
  assist_only e scope vazio; confirmacao de transcricao nao vira action receipt.
  Labels locais nao autenticam. Sem banco/tracing herdado do ambiente.
- `operational_service/adapters/browser`: um GET real de texto UTF-8 em
  endpoint fixture configurado com IPv4 numerico 127.0.0.1, porta/path exatos.
  Testes E2E usam servidor temporario proprio. Nao usa a porta 8765 do operador.
  Sem DNS/proxy, redirects, cookie, login, JavaScript, clique ou controle de tela.
  Conteudo e dado nao confiavel, nunca instrucao/grant; provenance nao autentica
  a fonte. Binding principal/sessao/scope/finalidade e somente local.
- MB218: leitura de receipt ja persistido pela Governance permite reconciliar
  cache de confirmacao apos falha de escrita/reinicio. Nao cria/renova receipt,
  claim ou grant. Bindings exatos e contexto completo sao exigidos; receipt
  expirado pode ser encontrado historicamente, mas nao ganha validade nova.
- Runtime fisico Linux recusa ancestors writable nao protegidos por sticky/
  ownership confiavel antes de abrir ledgers. Isso nao elimina corridas de
  mesmo usuario nem a lacuna central primeiro claim/reconciliacao do MB219.

## Executar os pilotos e testes locais

Da raiz, usando Python da venv:

```powershell
.venv/Scripts/python.exe -m apps.jarvis_voice --consent --scenario completed
.venv/Scripts/python.exe -m apps.jarvis_console.voice_pilot
.venv/Scripts/python.exe -m pytest apps/jarvis_voice/tests tests/integration/test_isolated_voice_pilot.py services/operational-service/tests/test_browser_fixture_reader.py tests/unit/test_linux_validation_runner.py tests/unit/test_physical_bootstrap.py
.venv/Scripts/python.exe tools/engineering_gate.py --mode standard
```

O demonstrador voice pede consentimento explicito via flag e confirma somente
texto sintetico conhecido. O piloto Core tambem usa texto/audio conhecidos,
nao captura audio humano. Sua saida padrao contem metadados, nao audio/transcricao.
Texto revisado fica na memoria canonica do Core exclusivamente durante o piloto;
o runtime temporario e removido ao terminar normalmente. Nenhuma migracao dos
bancos humanos ou escrita de patch/artefato operacional por esses pilotos.

Reader nao e registrado como tool/capability; sua API e os exemplos estao no
README do adapter. Eventos de voz/HTTP sao content-free, nao snapshots de texto.
Ports de voz sao sincronos: deadlines e cancelamento descartam resultados
tardios, mas nao preemptam chamadas bloqueadas nem desfazem entrada ja entregue
ao Core. Stop best-effort fixture nao prova interrupcao de dispositivo real.

## Linux explicitamente adiado

Docker instalado falhou ao iniciar com socket temporario inacessivel
`userAnalyticsOtlpHttp.sock` (Windows erro 1920). Tentativas pontuais nao
removeram o socket; nenhum reset, imagem/container, reinstalacao ou reboot foi
feito. O operador pediu deixar essa questao para depois e continuar outras
frentes. Nenhuma nova tentativa de infraestrutura integra esta rodada.

`tools/run_linux_validation.py` e `tools/linux_validation/` ficam preparados e
testados localmente, mas **nao executados em Linux/container**. O README explica
arquivo de fontes selecionadas, limites, imagem dev, isolamento e cleanup
best-effort. Nao existe garantia de eliminar segredos em qualquer fonte visivel;
antes de futura execucao revisar arquivos selecionados. Nao ha host mount e a
rede do teste seria none; construir imagem exige acao explicita posterior.

MB218 permanece in_progress, MB219 blocked. Skips Windows, validacao estatica
ou gate standard local nao substituem prova fisica Linux nem gate release.

## Proximos slices e reversibilidade

STT/TTS, hardware/permissao de microfone, streaming e qualidade vocal reais
continuam pendentes. Eduardo Borgerth e identidade desejada futura sujeita a
autorizacao/licenciamento e material/provider validado; nenhuma voz foi clonada.
Browser engine, computer use, navegacao externa e efeitos exigem slices/gates
proprios. OAuth/modelo real, API autenticada, MCP/integracoes e autoevolucao
empirica nao foram resolvidos por estas fixtures.

Prioridade seguinte: UI de revisao da voz em modo fixture, cliente MCP local
readonly e runner empirico de evolucao isolado; boundary autenticado segue
dependente do corte governado. Infra Linux fica deferred por decisao do operador.
Rollback: deixar de compor estes pilotos/readers; sem apagar dados humanos,
sem desfazer receipts reais e sem registrar novas capabilities.
