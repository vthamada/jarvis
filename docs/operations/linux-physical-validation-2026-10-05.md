# Prova fisica Linux - 2026-10-05

Atualizacao posterior: [campanha persistente e readiness](mb218-mb219-persistent-readiness-2026-10-05.md)
executou224 passed/5 skips Windows em ext4, aceite CLI entre containers e
gates finais. MB218/219 foram fechados tecnicamente no escopo local Linux/SQLite;
API mutante, autenticacao e power-loss continuam fora. Este documento registra
a primeira rodada tmpfs, cujas pendencias abaixo foram sucedidas por essa prova.

## Escopo e ambiente

Operador retomou Docker/Linux, informou que o reset acidental pela interface
atingiu apenas testes e autorizou atualizar Docker Desktop. WinGet verificou
o hash do instalador oficial antes da atualizacao 4.36.0 -> 4.93.0 (240920).
Windows 11 Home 25H2/build26200, WSL 2.3.26.0; Engine 29.8.1 linux/amd64 respondeu.
Nao houve novo reset, reboot, limpeza manual de sockets ou dados humanos.

Build limitado a tools/linux_validation; fontes selecionadas por archive,
sem .git/.venv/DB/audio/modelos e sem mount do host. Container usa rede none,
imagem read-only, caps removidas, no-new-privileges e /tmp tmpfs. Python3.11.17,
pytest9.0.2/ruff0.15.7. Imagem/cache de desenvolvimento permanecem no Docker.

Base resolvida: python:3.11-slim,
sha256:6f31d6e9ba2b0a787a3f81c37b004155b87b9efa1b771182bd550c1615745be5.
Imagem da primeira prova aprovada (antes do ajuste do interpreter):
sha256:096a0e9855d29a0002fa87626e3ef1cb80a1d6d9c85bc4a06e5d02d09f2e6ff9.
Container: jarvis-linux-validation-41ec631447044524ba5314326d985758.
Imagem final jarvis-linux-validation:py311-v1, usada pelos gates e repeticao fisica:
sha256:9c6c9e15e5ced09163e41fe475818cf80f9409e3e3f29fe33136c22a9a81b37b.
Container physical final: jarvis-linux-validation-f2ad1b8cc26d487a9d7002baa0822bea.
Container standard aprovado: jarvis-linux-validation-f975ef06004d42288ea85dbb78220100.
Container release aprovado: jarvis-linux-validation-881d1b8bbb6d4406a46115aaab83f63f.
Saida e codigos de retorno foram inspecionados no terminal desta rodada;
este documento e resumo, nao bundle bruto de logs nem atestacao assinada.

## Falha encontrada e correcao

A primeira bateria falhou em
test_crash_before_journal_then_paused_mission_cannot_start_effect[rollback].
O journal da mutacao fonte existia, mas a reserva do rollback ainda nao.
Recovery tentava vincular metadata sem rollback_operation_id ao plano canonico,
recusando por plan_binding_mismatch antes de reconhecer pedido novo necessario.

Sob resource lock, o kernel rele o journal; somente receipt/cleaned sem metadata
de rollback pode indicar pedido original necessario. Confere operation/receipt/
resource/root exatos com o plano e receipt persistido em Governance. Divergencia
continua recusada, sem converter tamper em ausencia. Console aceita somente os
codigos especificos de journal ausente/pedido necessario, revalida missao/workitem/
objective e reapresenta o pedido com a mesma confirmacao. Kernel ainda exige
staging/grant/claim e fence canonico para efeito novo. Nenhum efeito ou claim
e emitido pelo caminho que sinaliza ausencia.

Regressoes Linux reais cobrem restart antes da reserva, retry com a confirmacao
original, idempotencia, pausa anterior ao retry e tres planos estrangeiros.
Recovery historico de rollback ja reservado/claimed continua separado.

Primeiro gate standard falhou na coleta de tres ferramentas de relatorio por
f-strings multiline compativeis somente com Python3.12, apesar do minimo3.11
declarado. Expressoes passaram a concatenacao explicita/precalculo, sem mudar
formato de saida. Check de grammar3.11 e testes existentes cobrem os tres tools.
Gate intermediario apontou uma linha acima do limite Ruff, tambem corrigida.

Primeira suite global completa apresentou11 falhas: cinco testes de voz
usavam sys.executable como symlink da imagem, dois snapshots exigiam Git,
dois testes PostgreSQL importavam psycopg antes de verificar ambiente e duas
bordas de manifesto dependiam de comportamento Windows/timestamps.
Runner agora resolve somente seu interpreter confiado; nenhuma guarda de
symlink de source/modelos/audio foi relaxada. Sem Git, identidade fica unknown;
nao ha commit ficticio. Testes PG usam a guarda existente antes do import;
nao executaram PostgreSQL nem viraram passes. Fixture nested/.. e resolvivel
em POSIX para testar a recusa lexical, e loader rele/compara bytes bounded
do mesmo descritor, detectando same-size/coarse-clock. Nao e snapshot atomico
contra adversario same-UID. 64 testes Windows focados passaram/6 skips PG.

Primeiro gate release passou a suite global, mas o verificador active-cut
nao encontrava shared sem instalacao editable. O gate agora chama esse verificador
como modulo; subprocess sem site/PYTHONPATH comprova a inicializacao da CLI.
No Windows, o teste de redacao MCP excedeu o prazo de 3 segundos sob carga,
recusando corretamente a entrada no Core. Reteste isolado passou; esse teste
usa agora --timeout 10 explicito e bounded, sem alterar o default do runtime
nem as baterias separadas de cancelamento/expiracao. 63 testes focados passaram.

## Resultados

- physical inicial aprovado: 202 passed/5 skipped em 18.24s, exit0;
- physical final na imagem dos gates: 202 passed/5 skipped em 28.77s, exit0;
- skips:1 bootstrap non-Linux refusal,2 CLI Windows refusal,1 transaction Windows
  fail-closed,1 receipt proof Windows fail-closed; nenhum skip Linux no corpus;
- 67 testes Windows focados passaram antes da ultima ampliacao; Ruff focado passou;
- 33 testes report/grammar e 20 testes runner Windows passaram;
- standard Linux aprovado: encoding, document guardrails, Ruff e suite completa;
- release Linux aprovado: suite completa, axis/release/active-cut/historical
  closure, baseline development (segunda suite completa e smokes SQLite de
  memory/observability/evolution/missao governada/console), exit0;
- piloto active-cut: 8 cenarios, 7/7 route matches e 7/7 workflow matches;
- standard Windows final aprovado apos ajuste do teste MCP: encoding,
  document guardrails, Ruff e suite completa, exit0;
- cleanup dos containers aprovados confirmado por inspect de seus nomes exatos:
  daemon respondeu No such container; nenhuma imagem/cache/volume foi removido;
- pytest global usa quiet duplicado e nao imprime total de passes; nao inferir
  contagem a partir dos percentuais nem converter skips em passes.

## Reproducao e limites

```powershell
.venv/Scripts/python.exe tools/run_linux_validation.py --build --mode physical
.venv/Scripts/python.exe tools/run_linux_validation.py --mode standard
.venv/Scripts/python.exe tools/run_linux_validation.py --mode release
```

Cada run usa container proprio/--rm/cleanup pontual, sem limpar imagens, caches
ou volumes. Nao houve PostgreSQL controlado ou Node nesta imagem; skips opcionais
na suite global nao constituem prova desses ambientes.

tmpfs valida chamadas Linux, concorrencia, no-follow, rename, processo crash e
recovery do corpus, nao durabilidade apos queda de energia ou reboot da maquina.
Ao final desta primeira prova, MB218 permanecia in_progress e MB219 blocked.
Aceite tecnico, auditoria/readiness e campanha de falhas em storage persistente
foram fechados posteriormente na evidencia vinculada no inicio;
nenhuma API SFC005, capability ou framework externo foi promovido.
