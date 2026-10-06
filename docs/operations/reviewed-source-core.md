# Fonte revisada -> Core soberano - MB228

## Estado

Slice concluido localmente em 2026-10-05; gate standard global Windows passou
completo apos a correcao de compatibilidade legada. Nao e
promocao de pesquisa web, fact-checking, navegacao autonoma ou capability
publica. Nenhuma conta, modelo ou fonte humana foi acionada nos testes.

## Fronteira de autoridade

Uma fonte textual UTF-8 ate16KiB e uma selecao literal ate512 codepoints sao
revisadas localmente e vinculadas a principal/session/request/query/bytes/hash/
span/revisao. Consentimento fresco, prazo monotonic ate120s e consumo one-shot
sao exigidos antes do claim do request. URL e datas sao declaracoes; o hash e
fingerprint detectam inconsistencias, nao autenticam a origem ou o operador.
Exportar JSON de MB227 nao exporta consentimento, grant ou prova TLS.

`ReviewedKnowledgeContext` e argumento opcional de composicao local confiada,
nao campo de metadata, attachment ou input remoto. Query continua so a pergunta
do operador. Fonte fica fora de snippets/routing/rationale/instrucoes de
especialistas e modelos. `KnowledgeService` adiciona evidencia caller_declared,
freshness/conflict unknown e confidence unverified; degradacoes anteriores
missing/stale/conflict nao sao promovidas.

Admission exige analise read-only sem esclarecimento/operacao, surface console,
assist_only, scope vazio, metadata/attachments vazios e sem missao/adapter/receipt.
Checks de sujeito e tempo UTC confiado precedem claim/persistencia. Input.timestamp
nao governa admissao da fonte. Defaults e contratos sem fonte seguem intactos.

Governance nativa continua decidindo. DEFER_FOR_VALIDATION permanece DEFER,
mesmo com citacao. Synthesis pode anexar o literal apenas como dado nao confiavel
para revisao, preservando os erros missing_clause do workflow deferred; outros
erros, BLOCK ou qualquer efeito/request operacional retêm o fallback sem citacao.
Texto citado e JSON ASCII escaped com markup escapado; nao e instrucao, fato
verificado, conclusao da tarefa ou recibo de operacao. Sem grants ou efeitos.

## Memoria e observabilidade

A final soberana exata vai para a memoria canonica existente e sobrevive restart.
Ela tem retencao normal: cancelar/revogar apos handoff nao apaga nem desfaz o turno.
Nao existe shadow store, novo tipo de memoria ou importacao automatica de corpus.
A projecao read-side de turnos para Planning substitui o bloco literal marcado
por nota de fonte nao confiavel omitida; a resposta armazenada permanece integral.
No turno seguinte nao existe contexto tipado ou consentimento herdado. Isso nao
e promessa de deteccao universal de injection/PII ou limpeza de todo legado.

Eventos novos expoem so status/error_code/quote_characters e referencias opacas;
nao query, URL ou quote. Digest/ref nao e garantia de anonimato. A CLI e
content-free por padrao, include-content explicito passa pelo redactor existente
e omite o bloco inteiro se sensivel; nunca altera o literal mantendo seu hash.

## Composicao local

API confiada: `LocalKnowledgeReview` consent/propose/review/select/confirm;
`core.handle_input(contract, reviewed_knowledge=context, knowledge_review=review)`.
O contexto confirmado deve ser o objeto original; copias, replay, mismatch,
expiry exato, UTC futuro, clock rollback ou revogacao recusam antes do claim.
Cancelamento apos consumo nao retracta trabalho entregue ao Core.
Construir Core pode criar os stores locais antes do claim: se fonte/ticket
expira durante bootstrap, o request e recusado, nao se promete apagar os
diretorios inicializados. Nenhum turno/efeito dessa tarefa e autorizado.

CLI standalone: `python -m apps.jarvis_console.source_review_cli`
com --authorized --confirm-reviewed-selection --session-id e include-content
opcional. A selecao exata submetida e declarada pelo operador, nao atribuida a
revisao humana autenticada. Nao existe fetch implicito: se usar MB227 previamente,
restrinja seu max_body_bytes a16384 antes de observar, depois revise o envelope.
Nao automatize GET externo; alvos/pins/campanhas precisam de escopo autorizado.

```powershell
Get-Content -Raw -Encoding utf8 -LiteralPath .\reviewed-source.json |
  .venv/Scripts/python.exe -m apps.jarvis_console.source_review_cli `
    --authorized --confirm-reviewed-selection --session-id source-review-01
```

Somente execute apos ler e escolher a citacao. Use uma sessao nova ou de mesmo
sujeito; principal e fixado localmente como `user://local_operator`. Flags nao
autenticam identidade. Query nao recebe o texto da fonte. O documento possui
exatamente schema_version=`jarvis-source-review-v1`, authority=`none`,
origin_status=`declared_unverified`, query, source e selection. Source possui
text, source_url, observed_at, content_sha256, byte_count, media_type e
expires_at (null permitido); selection possui start, end, quote e content_sha256
(digest integral da fonte, nao apenas da selecao). Offsets sao codepoints Python,
fim exclusivo, quote exata. Datas UTC ISO, hash SHA256 lowercase de bytes UTF-8.

Stdin e JSON UTF-8 limitado64KiB/profundidade12, sem duplicatas/BOM/NaN;
EOF obrigatorio, nao deadline do produtor. Em shells legados com pipe nao UTF-8,
use JSON ASCII com escapes Unicode corretos. Nao passar paths via envelope.
--help nao constroi Core; flags invalidas nao leem stdin. Depois da admissao,
a fabrica constroi o Core local normal em `.jarvis_runtime/console`; o teste
injeta fabrica Core SQLite em diretorio descartavel, nunca store humano.

Status `recorded` significa turno persistido, nao analise concluida. CLI exige
readback da final exata, identidade/query/tempo/memoria e tres eventos persistidos
(governance_checked, response_synthesized, memory_recorded); audit fail nao
retorna sucesso e nao repete Core. Metadata relata decisao e status/contagem da
citacao. Include-content mostra somente final canonica, nao URL/body/query;
checa tambem quote crua validada para evitar que o escape oculte padroes do
redactor. Canonical final permanece integral mesmo quando display e omitido.
Saida JSON ASCII escaped ate256KiB; exit0 recorded,2 input/admission/audit
refused,3 interrupcao. Erros fixos nao ecoam documentos, argv ou exceptions.

## Validacao e rollback

Testes cobrem lifecycle, concorrencia, tamper/spans/Unicode/clock/expiry, routing
inalterado, guards da sintese, TLS real com CA sintetica/loopback proprio, Core
SQLite real, eventos, final/memoria/restart e default sem fonte. Caminho alternativo
usa scheduler fixture de LangGraph, nao prova de dependencia LangGraph instalada.
Nao houve nova prova Linux/rebuild Docker nesta rodada.

Gate obrigatorio: `python tools/engineering_gate.py --mode standard` completo
passou100% na segunda execucao, apos freeze da correcao legada. Env filho
PYTEST_ADDOPTS=--maxfail=1 --tb=short so altera diagnostico/stop-on-failure,
nao exclui testes. O global possui skips de perfis/plataformas; zero skips e
somente a bateria focada, nao cobertura universal. Apos docs finais, quick gate.
Consolidada frozen:618 passed/zero skips em32,39s (138 review,103 evidence,
103 contratos/E2E,92 synthesis,173 CLI,9 projection). Auditoria encontrou e
corrigiu expiry na igualdade, workflow DEFER annotation, quote em contexto de
resumo e display escapado sensivel; verificacao final independente5 selecionados
passed, sem bloqueador remanescente conhecido. Regressao de Knowledge (264),
Synthesis/Memory e Graph defaults tambem executada; testes sobrepostos nao
somados aos618. Quick gate e git diff --check passaram antes do standard.
Primeiro standard interrompeu em26%: input legado SimpleNamespace extrativo
nao tinha campo reviewed_knowledge opcional. Corrigido fallback None quando
ausente, sem ativar fonte;151 testes extrativos/synthesis/projection passaram.
Incluida regressao, total novo agora619; standard completo reiniciado apos
freeze. Nao contabilizar a tentativa parcial como gate aprovado.
Consolidada final apos compatibilidade:619 passed/zero skips em19,00s.
Desativacao: nao passar os argumentos opcionais/nao executar CLI. Nenhuma
migracao de registry/corpus/memory type e necessaria; finais ja persistidas
mantêm a politica normal. Objetivo de sistema completo continua aberto.
