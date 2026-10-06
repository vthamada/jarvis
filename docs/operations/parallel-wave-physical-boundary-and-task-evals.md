# Rodada 2026-10-04 — fronteira fisica e tarefas de produto

Pedido: implementar pendencias MB218/219 e um pacote independente por
multiagentes. Console, corpus de seguranca e avaliadores tiveram ownership
disjunto; coordenador integrou Memory/Operational/kernel e documentacao.
Nenhuma dependencia central nova, API publica, login, commit/push ou efeito em
arquivo humano. Docker/Linux permanece adiado pelo operador.

Atualizacao posterior: o operador retomou Docker em 2026-10-05. Prova fisica e
gates Linux aprovados estao registrados em
[evidencia Linux](linux-physical-validation-2026-10-05.md); o adiamento acima
descreve esta rodada historica, nao o estado atual. MB218/219 nao foram fechados.

## Entregas

MB218: leitura de desired-file por descritor, tipo regular/single-link,
ancestors sem redirects e limite de bytes, preservando UTF-8/newlines.
Request store publica inclusive o primeiro registro via staging privado
duravel e sem overwrite; falhas sincronas limpam staging. Cache de receipt
exige request, operador, challenge e fingerprints exatos. Nao ha promessa de
limpeza apos crash/power-loss, nem autenticacao humana duravel.
Detalhes em `apps/jarvis_console/PHYSICAL_OPERATIONS.md`.

MB219: dispatch marker da saga deixou de bastar para autorizar novo efeito.
Memory revalida missao ACTIVE, objective/owner e work item ativo/ready, alem
do plano persistido/recurso/linhagem exatos. O kernel distingue efeito novo
de reconciliacao historica. Nao ha flag correspondente na UI ou CLI.

Composicao nova obrigatoria: Operational recebe
`local_text_file_canonical_physical_effect_scope_provider`, vinculado a
`memory.artifact_physical_effect_scope`. Provider parcial/invalido falha
fechado antes do backend/journal. O port nao deve ser um no-op em producao;
nullcontext nos testes de wiring e apenas fixture rotulada.

O scope SQLite usa BEGIN IMMEDIATE para impedir pausa/rebinding por outra
conexao/processo entre a revalidacao e primeiro claim/efeito. Entra apos
staging, antes da claim nova, e sai antes do callback canonico que escreve
Memory. Ordem: resource lock -> Memory scope -> Governance claim. Os bancos
da composicao sao separados. O lock serializa todos os writers da Memory
durante esse trecho local, nao apenas a missao; falha/timeout recusa o efeito.
Nao fazer callback que pause/escreva Memory dentro do mesmo scope.
PostgreSQL e repositories sem essa implementacao recusam efeito novo;
nenhum fallback de mutex local ou no-op foi adicionado.

Claim consumida exata pode ser reconciliada apos pausa sem emitir nova claim.
Journal staged ou rollback_reserved somente recebe tratamento historico se
lookup Governance verificar a claim exata; outras fases continuam exigindo
verificacao historica antes do efeito. Uma pausa nao e cancelamento retroativo
de um efeito que ja comecou. Hash reseal sozinho nao concede autoridade.
TCB/limites e resposta a incidente em `docs/security/mb219-threat-model.md`
e `docs/security/mb219-incident-runbook.md`.

WP-QUALITY-01 independente: `evals/operator_tasks` implementa tres tarefas
versionadas, scorer externo ao candidato e metricas sem conteudo: relatorio
fundamentado, CSV revisavel e continuidade apos correcao. Corpus sintetico
publico, output estrito/bounded/replay-bound, nenhuma escrita de artifact ou
promocao. Resumo exige revisao humana; timeout sincrono nao preempta port.
README do pacote documenta limites e reproducao.

## Evidencia e reproducao

Suites focadas do console: 67 passed/18 skipped; corpus Memory MB219:
41 passed/4 skipped fisicos Linux (inclui 21 fixtures de decisao do kernel);
scope/wiring: 26 passed/10 skipped;
operator tasks: 75 passed. Esses grupos podem se sobrepor e nao devem ser
somados como total unico. Testes SQLite de concorrencia usam conexao real no
Windows; nenhum teste finge backend Linux.

Bateria integrada inicial: 203 passed/29 skipped, incluindo Memory saga e
composicao Orchestrator; 21 testes adicionais de modos do kernel passaram
separadamente. Primeiro gate expôs race preexistente nas leituras independentes
id/request de decision attribution: uma insercao concorrente identica podia
ser recusada. Releitura somente do counterpart ausente quando o presente e
exato preserva ambas as identidades/fingerprint/links; sem overwrite e sem
aceitar conflitos. 12 testes da area passaram, seis determinísticos novos
com SQLite real. Gates standard e release globais Windows passaram, incluindo
validation development/smokes SQLite TEMP. Detalhes no HANDOFF. Nenhum skip
de backend foi convertido em passe nem estado de capability foi promovido.

Piloto Core real isolado: cinco turnos/finais canonicos, 121 eventos,
tres tarefas `needs_decision`; governanca allow_with_conditions=3 e
defer_for_validation=2. Condicoes nao satisfeitas nao viram permissao.
Produtos uteis e recall semantico nao foram demonstrados; resultado fixture
correto prova o pipeline do avaliador, nao inteligencia do sistema.

```powershell
.venv/Scripts/python.exe -m pytest -o addopts='' tests/unit/test_mb219_physical_effect_boundary.py tests/unit/test_mb219_scope_lock.py tests/integration/test_mb219_physical_boundary.py -q
.venv/Scripts/python.exe -m pytest tests/unit/test_operator_tasks.py tests/integration/test_operator_tasks_flow.py -q
.venv/Scripts/python.exe -m evals.operator_tasks.core_pilot --authorized
.venv/Scripts/python.exe tools/engineering_gate.py --mode standard
.venv/Scripts/python.exe tools/engineering_gate.py --mode release
```

Resultado integrado dos gates fica em HANDOFF. Prova Linux real permanece
pendente: novas fronteiras pause/stage/claim, rollback contra edicao humana,
corpus adversarial e hard-crash precisam executar no backend suportado.
Release gate no Windows nao substitui essa prova nem aceitação MB218.

O modo physical de `tools/run_linux_validation.py` inclui agora as novas suites
MB219 e os testes de wiring/receipt proof, alem do console/hard-crash/saga.
19 testes locais do runner passaram (inclui lista sem duplicatas/corpus exigido).
Isso valida preparacao e comando, nao executa Docker nem prova Linux.

## Estado e reversao

MB218 continua in_progress e MB219 blocked pela dependencia; a implementacao
de subpacotes nao e fechamento dos dois MB. API SFC-005 continua ausente.
Antes de promocao: Linux real, aceite operacional e revisao de readiness,
incluindo campanha de falhas de storage e ownership humano para multiusuario.

Nao executar o console fisico/piloto e a reversao operacional deste slice.
Reverter codigo requer reverter provider, kernel e composicao juntos;
nunca retirar apenas a guarda e manter efeito habilitado. Nenhuma migration,
registro ativo ou dado humano foi alterado. Nao apagar journal/claim/store
para tentar refazer uma operacao: preservar evidencia e consultar runbook.
