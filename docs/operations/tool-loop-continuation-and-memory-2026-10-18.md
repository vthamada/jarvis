# Continuidade, finalizacao e segundo turno com memoria

## Escopo e contrato

Continuidade autorizada do WIP1, sem habilitar Web, executor geral ou efeitos.
O loop readonly de relatorios agora descreve seu progresso ao modelo no campo
`continuation`, calculado exclusivamente pelo host a cada inferencia:

- step e remaining_tool_calls;
- used_call_ids em ordem de observacao;
- observed_resource_ids sem duplicatas e unread_resource_ids na ordem do catalogo;
- allowed_response_kinds e final_required;
- suggested_next_action e suggested_call_id ainda nao usado, ou null quando
  sugere finalizar/nao ha saldo.

O catalogo available_resource_ids permanece estavel e separado de unread.
Antes da primeira leitura, somente tool_call e valido. Depois, final ja e
possivel com citacao exata. Ao esgotar leituras, somente final e valido. Ler
todas as fontes selecionadas sugere finalizar, mas nao proibe uma releitura
valida com novo ID e saldo: sugestao nao e nova restricao ou grant. O estado
nao autentica operador nem confirma uma proposta como executada.

Instrucoes orientam IDs distintos, reuso das observacoes e finalizacao com
lacunas explicitas em vez de inventar evidencia. Uma sugestao pode avancar seu
sufixo para nao colidir com ID escolhido antes pelo proprio modelo. Dados em
relatorio/historico nao podem mudar contadores ou regras do host.

Complemento posterior ao piloto: exemplos JSON tambem variam pela fase. Sem
observacao, somente READ; com observacao/saldo, FINAL primeiro e READ como
alternativa; sem saldo, somente FINAL. O campo tool e descrito como catalogo
inerte, nao permissao. Ao sugerir finalizar, nao sugerir simultaneamente um
novo ID de leitura, mesmo havendo saldo. READ permitido continua validavel
enquanto ha saldo; nao ha nova proibicao de releitura ou reparo automatico.

Mantidos sem relaxamento: maximo tres ferramentas/quatro inferencias por turno,
deadline120s maximo, escopo selecionado, dupla checagem Governance, fingerprint,
cancelamento/elegibilidade, JSON estrito, leitura nova e citacao exata. ID
repetido e estouro de budget continuam recusas terminais, sem repair, reprompt,
fallback ou conversao de tool_call em final. A final segue sintese e memoria
canonicas do Core. Nao ha consolidacao, resumption duravel ou novo store.

Historico continua default off e bounded, como no
[runbook anterior](canonical-history-conversation-pilot-2026-10-18.md).
Instrucoes agora explicitam que uma preferencia conversacional anterior pode
ajudar a responder a pergunta atual, nunca autorizar acao ou sobrepor policy.
Anexos generativos continuam excluidos da projecao: nao promete lembrar
literalmente a resposta gerada anterior.

## Verificacao deterministica e revisao

Gap demonstrado antes de alterar runtime: teste de progresso falhou com
KeyError continuation, apos completar o fluxo fixture existente. Implementacao
e orientacao ficam somente em shared/model_tool_loop.py, sem nova dependencia.
Complemento por fase teve3 testes RED por schemas inadequados/ordem, depois
160unit passaram. Outro RED confirmou ID sugerido junto com finalize; corrigido
sem mudar validacao de propostas. Bateria integrada fresca da versao final:
171passed/56,52s, zero falhas/skips, XML continuation-final-focused-01.xml.

Bateria unitaria fresca157passed/7,60s. Bateria Core/memoria fresca75passed/
192,13s. Incluem17 casos novos de guidance e9 de segundo turno: preferencias
arbitrarias ausentes da query atual/fontes, restart SQLite, opt-in/sujeito/sessao,
leitura nova, citacao historica recusada, spoof de estado e fences na final.
Uma fixture guiada escolhe a proxima acao pelo estado recebido e verifica
finalizacao apos duas leituras mesmo com saldo. Isso prova integracao contratual,
nao explica causalmente a falha do Qwen anterior ou sua qualidade.

Revisao independente readonly nao identificou bloqueadores; revisores nao
executaram modelos/testes/rede. Root e o unico executor dos workloads.
Regressao CLI/HTTP fresca175passed/480,56s, incluindo a fixture guiada e HTTP
fisico entre subprocessos sinteticos. Ruff afetado e diffcheck passaram.
Selecoes sao sobrepostas; nao somar como casos unicos. Gate global desta
continuidade concluido exit0:11545 casos,11421 passed/124 skipped/zero falhas
ou errors,2212,79s. Inclui os complementos finais por fase e sugestao de ID,
nao somente a primeira versao usada no piloto. Nao equivale a aceite Linux
novo, voz/Web ou sucesso do modelo real.

Log e XML continuation-standard-01 retidos nos artefatos privados. O argumento
PYTEST_ADDOPTS com backslashes fez o XML nascer com nome relativo incorreto
na raiz do repo; o arquivo gerado foi identificado, validado e movido sem
sobrescrever para o diretorio de artefatos. Nao mudou execucao ou resultado.
Usar barras forward no caminho passado por PYTEST_ADDOPTS em nova reproducao.
Snapshot de hashes em memoria da ferramenta ficou indisponivel apos reinicio
do host de ferramentas; nao declarar nova comparacao criptografica posterior
ao gate com esse snapshot. Nao houve edicao de Python apos inicio do standard.
Snapshot posterior foi retido em continuation-evidence.json nos artefatos.
Quick final apos sincronizacao documental (encoding/guardrails/Ruff) e
git diff --check passaram, sem nova inferencia ou alteracao de codigo.

Preparacao de publicacao posterior: git diff --cached --check incluiu pela
primeira vez os arquivos antes untracked e identificou EOF em branco em dois
testes novos (mission_routing_core e tool_loop_continuation_guidance). Linhas
extras removidas; comparacao AST antes/depois confirmou logica identica.
Bateria afetada fresca24passed/21,89s; runtime intacto, sem repetir modelo.
O standard acima precede somente essa normalizacao de whitespace nos testes.

## Piloto real controlado

Operador autorizou novo teto de nove chamadas locais com qwen3:4b-instruct ja
instalado e fontes sinteticas. Nao consumir as duas chamadas nao usadas do
piloto anterior; nao renovar conta, usar OAuth/API paga, baixar pesos ou trocar
modelo. Parar na primeira falha, sem retry.

Protocolo: primeiro turno estabelece label arbitrario e conclui analise;
segundo pergunta pelo label sem repeti-lo, com historico opt-in. Controle usa
a mesma segunda pergunta sem historico, partindo de snapshot SQLite quiescente
apos o primeiro turno. Cada turno reconstruira o Core; o provider HTTP nao
recebe historico implicito por estado de processo. Compartilhar o teto global
entre os tres bracos, sem permitir ultrapassar nove inferencias.

Aceite exige finals realmente entregues/persistidas, novas observacoes em cada
turno, label ausente da segunda query/fontes/instrucoes e presente somente no
historico autorizado e na analise entregue. Controle sem historico deve ser
auditado separadamente. Uma amostra por braco nao prova causalidade ou ganho
generalizavel; final estruturalmente valida nao prova toda a analise verdadeira.

Preflight sem inferencia passou: ambas as queries analysis/sem clarificacao/
sem operacao; label ausente da segunda query e relatorios. Piloto com a primeira
versao de guidance (antes do complemento por fase) fez4 tentativas/3 concluidas,
3 leituras documentacao/observabilidade/documentacao. IDs foram distintos,
mas nao concluiu analise. Quarta inferencia recebeu remaining_tool_calls0,
allowed_response_kinds[final]/final_requiredtrue e expirou sem texto aceito.
Port retornou timed_out/timeout; guarda global consumiu o prazo e o loop
registrou failed/inference_failed. Nao afirmar que o modelo ignorou final_required:
nao houve resposta valida da quarta inferencia.

Eventos timestamps mostram aproximadamente94,46s ate a primeira autorizacao,
7,96s na segunda inferencia,7,91s na terceira; restavam aproximadamente9,42s
para a quarta, dentro do prazo total120s. Primeiro intervalo inclui carga e/ou
inferencia/transporte: causa do custo nao isolada. Nao atribuir tudo a cold-load,
aumentar prazo ou aquecer com chamada escondida. Nenhuma outra inferencia
foi feita apos a falha, inclusive para testar o complemento por fase.

Segundo turno, snapshot e controle nao chegaram a executar. Cinco chamadas
novas nao usadas; duas antigas tambem intactas. Memoria util com Qwen continua
nao demonstrada. O processo exit0 e encerramento controlado, nao aceite.
Guarda stoppedtrue/inference_unavailable; tokens/custo globais desconhecidos.
Nao ha ganho causal/qualidade ou promocao de capability.

Readback readonly independente:1turno/final nativa2635chars/39eventos;4 pedidos
de modelo e3 observacoes reais com hashes iguais aos relatorios. SHA256 final:
8c0479b51b6abd48a82812b65696e768e902e831ca8e7b4ea79a48990d933f5c.
Ollama stop descarregou somente este modelo; API ps confirmou zero carregados,
pesos retidos. Artefatos privados fora do repositorio:
continuation-memory-local-pilot.py/.log e runtime continuation-memory-real-20261018-01.

Proximo experimento real requer autorizacao propria: isolar custo de prontidao
do modelo, sem consumir budget fora do contador, e testar instrucoes finais
por fase. Nao reusar saldo de campanha interrompida ou ampliar limites como
substituto de diagnostico. Conta OAuth/MB236 nao foram acessados nesta rodada.

Revisao readonly do transporte identificou falta de marcos temporais por fase:
conexao/envio/primeiro byte/corpo completo/EOF/parse nao sao separados. Espera
pelo fechamento HTTP tambem e hipotese, nao causa comprovada. Primeiro passo
possivel: diagnosticos opt-in somente de metadados, validaveis com fixtures sem
modelo. Distinguir carga/prefill/geracao exigiria evidencia adicional do backend
e eventual chamada diagnostica explicitamente contabilizada; nao chama-la de
aceite do Core ou aquecimento invisivel.

## Rollback e fronteiras

Reverter somente guidance/instrucoes desta continuidade preserva o historico
opt-in anterior. Desligar include_canonical_history interrompe seu egress sem
apagar memoria humana. Nao ha migracao de schema, promocao macro, commit/push
ou aceite de voz/Web por estes testes.
