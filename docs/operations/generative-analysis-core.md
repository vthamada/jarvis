# Analise generativa subordinada ao Core (MB229)

Estado: MB229 done no recorte local, 2026-10-06. Nao e promocao de
conversa generativa ampla, modelo real, API publica ou autonomia operacional.

## Fluxo e fronteiras

Synthesis continua compondo a resposta nativa. O complemento opt-in so pode
ser tentado para analysis naturalmente ALLOW, core_guidance_only, sem
especialista, tool/adapter, efeito ou confirmacao pendente. core_reasoning e
cognicao interna legitima, nao efeito externo. O label request_confirmation_mode
bounded_autonomy nativo nao concede efeito: human_confirmation_required deve
permanecer false e autonomy_confirmation_mode not_required.

Uma tentativa de inferencia recebe somente a entrada atual e, quando houver
revisao local valida, a selecao literal de ate512 caracteres. Nao recebe corpo
inteiro, URL, historico, identidade, tokens, memoria recuperada ou registries.
Filtros de padroes sensiveis conhecidos recusam entrada/saida; nao sao garantia
universal de ausencia de segredos ou dados pessoais em linguagem natural.

O candidato JSON tem exatamente analysis, assumptions, limitations, citations.
Schema, tipos, tamanhos, referencias, offsets e citacoes exatas sao verificados.
Prosa nova permanece model-generated/unverified: validar estrutura nao prova
verdade nem elimina toda instrucao maliciosa em linguagem natural. Nao ha
actions, grants, tools, policy ou canal de escrita da memoria pelo modelo.

Falha, resultado parcial, correlacao/modelo/provedor incorreto, cleanup,
cancelamento, prazo e mudanca de bindings preservam a final nativa exata.
DEFER/BLOCK nao chamam inferencia nem catalogo. Configuracao default permanece
sem modelo; extrativo legado e generativo nao podem ser compostos simultaneamente.

Catalogo lazy e provider compartilham um unico budget de inferencia de ate120s;
nao ha login, refresh, retry ou descoberta de contas automatica. Cancelamento e
cooperativo: uma extensao Python injetada deve respeitar timeout; nao e sandbox
de processos nem mecanismo para matar codigo arbitrario.

A final unica passa pela Memory canonica. Readback confirma a final e eventos
persistidos; restart deve recuperar os mesmos bytes de texto. A projecao de
Planning omite anexos generativos nao confiaveis e citacoes, inclusive resumos
derivados, sem apagar a final ou o resumo canonicamente armazenados.
Novos eventos generative_* contem somente status/code/evidence/count. Campos
canonicos preexistentes de identidade de auditoria nao foram removidos.

## Uso explicito (nao executado com conta humana nesta rodada)

Uma conta ja conectada pelo fluxo chatgpt-account pode ser selecionada por
diretorio privado absoluto e profile-ref exatos. Nao procurar tokens de outros
aplicativos. O operador deve escolher modelo existente no catalogo da conta e
autorizar o envio da entrada. Diretorio privado continua fora do Git/OneDrive.

Documento stdin, UTF8 e EOF, com schema estrito:

```json
{"schema_version":"jarvis-generative-analysis-v1","query":"Compare documentation and observability pilot reports."}
```

```powershell
python -m apps.jarvis_console.generative_analysis_cli --authorized --confirm-input --session-id analysis-local --model SELECTED_MODEL --credential-dir ABSOLUTE_PRIVATE_DIRECTORY --profile-ref profile-EXACT_64_HEX --include-content
```

O exemplo exige um pipe stdin explicito e substituicao dos placeholders;
nenhum parametro conecta/login/refresh automaticamente. Sem include-content,
somente metadados. status recorded indica persistencia, nao verdade ou tarefa
concluida. generative_status accepted indica candidato estruturalmente aceito;
withheld preserva decisao nativa, rejected preserva fallback.

## Evidencia e limites

Baterias locais exercitam schema adversarial, privacidade, elegibilidade,
deadline/cancel, mutacao tardia, catalogo/provider, cleanup e persistencia.
HTTPS/SSE usa CA sintetica propria, loopback e conta/provedor fixtures. Isso
prova transporte TLS real e composicao local, nao uso de modelo externo.
O scheduler Graph de teste nao prova LangGraph instalado.

A prova fisica identificou socket fechado apos EOF com Connection: close;
transporte agora verifica cancelamento/prazo e evita retimar somente o leitor
ja fechado, preservando erros e timeout do leitor ativo. Cleanup do catalogo
falha fechado e tenta fechar ambos os recursos.

Nao houve campanha de conta/modelo real, nova prova Linux, voz humana, mic,
efeito operacional, commit ou push. Proxima homologacao real exige consentimento,
conta/modelo e campanha escolhidos; nao confundir fixture com live.

## Validacao e rollback

527 testes novos do slice MB229 passaram, incluindo54 provas E2E Core/HTTPS;
mais94 testes do inventario paralelo, total621 novos, sem skips nessas baterias.
Gate standard global Windows completo aprovado com runtime congelado; skips
opcionais/de plataforma nao equivalem a novas provas Linux ou PostgreSQL.
O primeiro gate completo encontrou corrida de startup no teste de cancelamento
MCP: prazo curto0.8s permanece no caso deadline; cancelamento por evento/task
aguarda RPC real com budget10s e exige processo encerrado. Tres casos focados
e a repeticao completa passaram. Nenhum timeout de producao foi ampliado.
Sincronizacao final do snapshot/documentos validada por bateria do inventario,
gate quick e git diff --check, sem alteracao posterior do runtime aprovado.

```powershell
python -m pytest tests/unit/test_generative_analysis.py tests/unit/test_session_inference_port.py tests/unit/test_generative_analysis_cli.py tests/unit/test_generative_projection.py tests/unit/test_generative_synthesis_scope.py tests/unit/test_oauth_catalog_cleanup.py tests/integration/test_generative_analysis_core.py tests/unit/test_product_readiness_report.py -q
python tools/engineering_gate.py --mode standard
```

Remover a composicao generative_port/generative_model desativa o complemento;
nao ha migracao, nova dependencia central ou memoria paralela. Finais historicas
continuam preservadas. O painel product-readiness e derivado para consultar o
estado por frente; nao altera governanca nem substitui Documento-Mestre/backlog.
