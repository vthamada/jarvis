# WP-CODE-01: code fixture isolado

Este pacote implementa um ciclo funcional de patch predefinido -> copia de
workspace em memoria -> testes interpretados -> diff para review. Nao e um
sandbox de sistema operacional, nao executa Python arbitrario e nao prova
capacidade de gerar software com um modelo. Nao foi conectado ao Core,
Specialist Engine ou registry operacional.

O coordenador acrescentou um consumidor experimental em
`apps.jarvis_console.code_pilot`: proposta offline -> este interpretador ->
metadados no Core real. Isso nao ativa o pacote como adapter de producao nem
comprova geracao por modelo real. Runbook: `docs/operations/parallel-wave-local-pilot.md`.

## Uso

```python
from operational_service.adapters.code_sandbox import (
    CandidatePatch, FixtureCase, FixtureCodeSandbox, FixtureWorkspace, source_digest,
)

before = "def add(a, b):\n    return a - b\n"
after = "def add(a, b):\n    return a + b\n"
workspace = FixtureWorkspace({"src/add.py": before})
patch = CandidatePatch("src/add.py", before, after, source_digest(before))
case = FixtureCase("src/add.py", "add", (2, 3), 5)
result = FixtureCodeSandbox().run(workspace, (patch,), (case,))
assert result.status == "passed"
print(result.telemetry())  # status/counts/hash; nunca conteudo
review_diff = result.diff  # sensivel: acesso explicito, nao enviar a logs
```

Workspace e resultado sao copias imutaveis. Um hash e igualdade exata do
`before_text` verificam CAS, sem transformar conteudo em confianca. Apenas
substituicoes de arquivos existentes `.py` sao aceitas; nao existe operacao
de criacao/remocao, symlink ou filesystem host. Paths usam subconjunto ASCII
relativo, sem traversal, drive, UNC, ADS, controles, aliases Windows ou
colisoes case-insensitive. Isso e validacao de nomes em fixture, nao prova
de seguranca para um futuro backend de arquivos reais.

## Subconjunto e limites

Cada arquivo so pode conter funcoes sem decoradores, anotacoes, defaults,
variadicos ou efeitos. Cada funcao tem um unico `return` de inteiros,
argumentos posicionais, operadores `+`, `-`, `*`, `//`, `%` e sinais unarios.
Chamadas, imports, atributos, strings, booleanos, loops, classes, assignment
e outros nodes falham fechados. O AST e interpretado diretamente; nao ha
`exec`, `eval`, compilacao de bytecode, shell, subprocess, rede ou escrita host.
Todos os arquivos sao validados, inclusive os nao exercitados pelos casos.

Limites fixam source/total/arquivos/patches/casos/nodes/profundidade/argumentos
e magnitude de inteiros. A multiplicacao e bounded por operandos de ate 128
bits mesmo com configuracao ampliada. Deadline/cancelamento sao cooperativos
e checados entre fases/nodes/casos. Parsing e diff bounded nao sao preemptivos;
este pacote nao oferece timeout OS nem isolamento de processo. Callbacks de
clock/cancel sao controles confiaveis do harness, nao dados do candidato.
Clock deve ser numerico finito e monotono; regressao, NaN, callback com erro
ou cancelamento nao booleano falham fechados com motivo sanitizado. Casos e
patches devem ser listas/tuplas finitas, nao iteradores de comprimento desconhecido.

`passed` significa somente que os casos fornecidos passaram no interpretador.
`test_failed` distingue produto incorreto; `rejected`, `timed_out`, `cancelled`
nao disponibilizam workspace/diff, mesmo apos testes parciais. E necessario ao
menos um caso. A evidencia sempre declara `fixture`, `model_generated=False`
e `host_effects=False`; nenhum receipt ou grant e emitido. `diff`, workspace,
patch e casos sao dados sensiveis, omitidos de repr/telemetry. Hashes de codigo
ainda devem ser tratados como fingerprints nao anonimizados.

## Verificacao e proximos slices

```powershell
.venv\Scripts\python.exe -m pytest services/operational-service/tests/test_code_fixture_sandbox.py
```

A bateria inclui bug real da fixture, patch CAS, testes interpretados, diff,
preservacao do original, sintaxe hostil, aliases/traversal, limites, cancelamento
e deadline. A inferencia nao esta conectada: o patch do teste e predefinido.
Aplicacao governada em repositorio real, comandos de teste reais, egress,
symlinks, receipts, isolamento OS e geracao por modelo exigem slices futuros
e seus gates. Nao substituir este interpretador por execucao irrestrita.
Rollback: remover/desabilitar o import deste pacote; nenhum dado humano muda.
