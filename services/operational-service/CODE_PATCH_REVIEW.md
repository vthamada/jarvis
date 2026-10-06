# WP-CODE-01 — propostas revisáveis sem efeitos no host

Atualizacao MB220: console standalone `code-review` torna o reviewer utilizavel
por stdin JSON limitado, sem host reads/aplicacao/execucao. Diff so opt-in;
segredo detectado omite conteudo inteiro preservando fingerprints. Guia:
`docs/operations/local-review-products.md`. Nao integra/promove o adapter no Core.

`operational_service.adapters.code_sandbox.patch_review` acrescenta preview de
patch estruturado sobre snapshots finitos em memória. Não lê repositório humano,
não escreve arquivos, não executa código ou subprocessos e não emite grants.
Não é um sandbox de sistema operacional ou capability promovida do runtime.
O núcleo continua responsável por identidade, governança, memória e síntese.

## Contrato

```python
from operational_service.adapters.code_sandbox.patch_review import (
    PatchReviewer, PatchProposal, FileEdits, TextEdit, text_sha256,
)

before = "def add(a, b):\n    return a - b\n"
reviewer = PatchReviewer(("src/math.py",))  # allowlist escolhida pelo operador
snapshot = reviewer.snapshot({"src/math.py": before})
offset = before.index("-")
proposal = PatchProposal(snapshot.sha256, (
    FileEdits("src/math.py", text_sha256(before), (
        TextEdit(offset, offset + 1, "-", "+"),
    )),
))
preview = reviewer.preview(snapshot, proposal)
assert preview.status == "reviewable"
verified = reviewer.verify(
    preview, snapshot, expected_proposal_sha256=preview.proposal_sha256,
)
assert verified.status == "reviewable"
assert verified.authority_granted is False
```

`snapshot()` copia apenas dicionário finito, valida texto/paths/limites e retorna
tupla de arquivos imutáveis. `TextEdit` usa offsets de caracteres Python no texto
original exato, sem normalização Unicode. Spans ordenados, não sobrepostos e não
vazios exigem preimage textual e hash do arquivo. Apenas arquivos existentes e
explicitamente allowlisted aceitam alterações. Remoção de span pode ocorrer, mas
arquivo vazio, criação, remoção de arquivo, rename, inserção zero-width e no-op
(inclusive no-op composto) são rejeitados. Não existe parser de diff livre.

O SHA-256 da proposta vincula o snapshot inteiro, paths, hashes, offsets e textos
dos spans. O hash do preview vincula proposta, base, candidato, diff e resumo.
`verify()` recomputa tudo contra o snapshot atual e rejeita tanto alteração humana
em qualquer arquivo da base quanto substituição do candidato/diff/resumo/flags.
Hashes são fingerprints de integridade e não são assinaturas, aprovação ou
autoridade. O chamador precisa preservar o hash esperado fora do candidato;
substituir simultaneamente candidato e expectativa não representa review válido.

## Limites e dados não confiáveis

Limites defaults: 32 arquivos/base, 8 arquivos alterados, 16 KiB/arquivo,
128 KiB/base/candidato, 32 spans, 512 linhas/arquivo, 128 KiB/diff e 64 hunks.
Há ceilings fixos em `ReviewLimits`. A análise e `difflib` são síncronos e bounded;
não oferecem deadline preemptivo de processo. Não há dependência nova.

Paths usam subconjunto ASCII relativo sem traversal, drive, UNC, ADS, backslash,
aliases reservados Windows, dotfiles, controles ou colisão case-insensitive.
Texto aceita Unicode visível; controles/invisíveis/bidi/surrogates e separadores
Unicode de linha são rejeitados. Quebras são LF; CRLF precisa de decisão explícita
em outro contrato, não de normalização silenciosa. Diff determinístico é ordenado
por path e preserva o marcador de ausência de newline no final do arquivo.

Conteúdo é não confiável, inclusive comandos, HTML e texto que parece instrução
ou grant. O consumidor deve escapar a saída quando exibida em HTML e nunca
interpretá-la como instruções. `repr` e `telemetry()` não incluem paths, source ou
diff. Hashes continuam sendo identificadores sensíveis, não anonimização.
Não logar `diff`, `proposal`, `candidate` ou resumos completos automaticamente.

`reviewable` significa somente preview verificável, não software correto,
aprovação de execução ou testes reais passados. Resultados sempre declaram
`evidence_mode=in_memory_preview`, `host_effects=False`, `tests_executed=False`
e `authority_granted=False`. Rejeição não entrega snapshot candidato ou diff.

## Evidência e próximos passos

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_code_patch_review.py tests/integration/test_code_patch_review_flow.py
```

A integração offline converte o candidato revisado ao interpretador aritmético
existente, usando expectativas independentes fixadas pela fixture. Distingue
patch correto de candidato revisável porém incorreto, stale/user-edit e tamper.
Esse teste prova composição local em memória, não geração por modelo real,
aplicação em repositório, comandos de teste reais ou isolamento OS. O adapter
isolado não foi ligado a registry, grants ou escrita física. O gate agregado é
executado pelo coordenador; este pacote não declara promoção por testes locais.

Aplicação física futura exige autoridade soberana, recibos, efeito e reconciliação
governados, isolamento próprio, revisão humana e seus testes/gates. Rollback deste
slice: deixar de importar o módulo; nenhum dado humano foi alterado.
