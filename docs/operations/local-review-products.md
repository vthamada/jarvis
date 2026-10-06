# Produtos locais de revisao - MB220

## Entrega

`code-review` e `research-review` sao comandos standalone utilizaveis sobre
textos escolhidos pelo operador. Nao constroem Core nem fazem fetch, leitura de
repositorio, escrita, execucao, ingestion ou grants. Nao sao inferencia de modelo,
resposta final soberana ou capability promovida. MB218/219 e o no-go API intactos.

Entrada: JSON UTF-8 por stdin ate65.536 bytes/profundidade12, produtor deve fechar
o pipe (limite de bytes nao e timeout). Terminal interativo e recusado.
Duplicatas aninhadas/escapadas, nonfinite, Unicode invalido, schema/campos/tipos
e excesso sao recusados com exit2, stderr fixo e nenhum output parcial.

Saida default contem apenas hashes/contagens/estados, nao query, paths virtuais,
diff, fonte ou citacao. `--include-content` opt-in exibe JSON escapado inclusive
em text. `--format json` usa envelope console/v1; produto JSON em outputs[0].
Conteudo que demande redacao pelas guardas existentes fica INTEIRAMENTE omitido:
content_withheld=true/content_withheld_reason=sensitive_display_content.
Nao modificar diff/quote mantendo hashes originais. Guardas nao detectam todo
segredo; fingerprints nao anonimizam, autenticam ou aprovam. Nao renderizar
objetos decodificados como HTML/Markdown confiavel. Observabilidade e projecao
bounded do console, nao eventos/receipts canonicos.

## Pesquisa offline

Exemplo PowerShell com dados publicos sinteticos:

```powershell
'{"schema_version":"jarvis-research-input-v1","query":"budget","as_of":"2026-10-05T12:00:00Z","sources":[{"source_ref":"provided:notes-v1","text":"The budget is 50. Review happens Thursday.","observed_at":"2026-10-04T12:00:00Z","expires_at":null}]}' | .venv/Scripts/python.exe -m apps.jarvis_console --format json research-review --include-content
```

Campos exatos: schema_version/query/as_of/sources; cada source contem
source_ref/text/observed_at/expires_at. ID ASCII nao e URL a buscar. Datas ISO
com timezone.16 fontes,2048 caracteres/query,16KiB UTF8/fonte,64KiB documento,
8 citacoes/512 caracteres cada/4096 totais. Controles/bidi inseguros recusados.

Selecao lexical Unicode NFC/casefold, melhor janela contigua por fonte, rank por
tokens distintos/ocorrencias/ref/offset. Nao e inferencia semantica. Cada quote
e slice exato do texto original, offsets codepoints Python/end exclusivo,
SHA256 e untrusted_evidence=true. Instrucoes de fontes nao conferem autoridade.

Validade e caller_declared_not_verified, inclusive as_of. Fontes expiradas ou
futuras ficam fora. expires_at=null entra como unknown, nao current. Agregado
current somente quando TODOS os trechos selecionados current. Verdade/conflito
sempre not_assessed. Citacao exata nao valida fatos ou resolve contradicoes.
Output jarvis-research-dossier-v1 permanece draft/requires_human_review=true.

## Patch em memoria

Exemplo PowerShell:1 para2 em arquivo VIRTUAL, nao aberto no host:

```powershell
'{"schema_version":"jarvis-code-review-input-v1","files":{"src/example.py":"value = 1\n"},"proposal":{"expected_snapshot_sha256":"178ac7cdb6a3aeae554edaf77e87823cc2743b0c501a1c7ff92c1e00f12a3d58","files":[{"path":"src/example.py","expected_sha256":"585c93666fcb046b7b264d3fa73202aa2a38254ae82a4b3ba19e873c2d5a9886","edits":[{"start":8,"end":9,"expected_text":"1","replacement":"2"}]}]}}' | .venv/Scripts/python.exe -m apps.jarvis_console --format json code-review --include-content
```

Campos exatos: schema_version/files/proposal; proposal contem
expected_snapshot_sha256/files; cada change path/expected_sha256/edits; cada edit
start/end/expected_text/replacement. Offsets codepoints Python originais sem
normalizar Unicode/CRLF. Somente arquivos existentes no bundle sao permitidos.
PatchReviewer existente aplica guards de path/traversal/preimage/hash/span/no-op.
Nao ha parser de diff livre.32 arquivos/base,8 alterados,32 spans,16KiB/arquivo,
limites de linhas/hunks; envelope ASCII serializado tambem deve caber em64KiB.

Snapshot/preview/verify conferem consistencia interna e segundo preview contra
fingerprint calculado da mesma proposta fornecida. Nao provam host atual,
baseline externo, origem confiavel ou aprovacao. Hashes nao sao grants. Output
jarvis-code-review-output-v1: draft/requires_human_review/read_only true,
tests_executed/host_effects/authority_granted false. Reviewable nao significa
codigo correto ou testes executados.

## Validacao e reversao

310 testes focados passaram/zero skips em2026-10-05: builders, inputguards,
reviewer, registry/assets e subprocess CLI real. Auditor independente sem
bloqueador; Ruff global passou. Sentinela sintetica de arquivo permaneceu intacta;
nenhum Core construido ou fetch durante dispatch. Somente dados sinteticos
testados, nao modelo real. Gate standard global Windows final passou;
MB220 done no escopo de ferramentas locais. Nao houve novo release Linux.

Primeiro gate global encontrou timeout de30s em um subprocess CLI de recusa
de preimage falsa. Bateria focada anterior passara; nenhuma guarda falhou.
Orcamento do teste de startup integral do console aumentado para60s, sem mudar
runtime/deadline de entrada. Reexecucao CLI:28 passed em39.24s. Gate global
completo repetido e aprovado, sem descartar o teste ou alegar aprovacao do gate
anterior. Quick final verifica docs sincronizadas depois do gate standard.

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_review_input.py tests/unit/test_code_review_cli.py tests/unit/test_offline_research.py tests/integration/test_review_products_cli.py
.venv/Scripts/python.exe tools/engineering_gate.py --mode standard
```

Sem nova dependencia, schema canonico, migration, credencial, commit/push.
Remover comandos/builders da composicao preserva stores. Integracao Core,
aplicacao de patches, pesquisa web e sintese livre exigem recortes/gates proprios.
