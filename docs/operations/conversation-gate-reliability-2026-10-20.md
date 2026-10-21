# Conversa, memoria e confiabilidade do gate

Data: 2026-10-20. Continuidade do WIP integrado, sem ampliar autoridade ou prazo
do produto. Slice de implementacao validado pelo standard; aceite de conversa
util com modelo real continua pendente.

## Mudanca entregue

A CLI `apps.jarvis_console.local_model_tool_loop_cli` aceita
`--include-phase-diagnostics`; a API Python tem `include_phase_diagnostics=False`.
A escolha pertence ao host, nunca ao documento de entrada ou resposta do modelo.
Sem a flag, o formato de saida anterior e preservado e o coletor nao e construido.
Com a flag, a resposta acrescenta:

- `phase_diagnostics`: no maximo 28 amostras, copiadas com schema estrito;
- `phase_diagnostics_clock_scope=per_component_operation`.

Cada amostra tem somente `component`, `event`, `phase`, `elapsed_ms` inteiro
0..120000 e `timing_mode`. Componente e `transport` ou `provider`. Nao ha
conteudo, URL, caminhos, modelo, tokens ou request IDs. Relogios reiniciam a cada
operacao e sao independentes entre os componentes. `live` significa relogio
real, nao prova de modelo ou pesos locais. Port injetado pode retornar lista vazia.
As amostras nao sao gravadas em memoria ou eventos canonicos. Continuam intactos
EOF obrigatorio, fences, IDs unicos, cancelamento, limite de quatro inferencias/
tres leituras por turno e prazo total maximo de 120 segundos. Nao ha warm-up,
retry ou fallback novo. Em erro de modelo divergente, ficam somente as fases
HTTP realizadas, sem parse aceito, leitura, anexo ou nova tentativa.

## Memoria e ferramentas: prova e limite

O teste publico `test_local_memory_control_flow.py` usa tres processos CLI e um
servidor HTTP scripted que calcula a resposta somente pelo payload recebido:

1. Primeiro turno declara uma preferencia arbitraria, le dois relatorios e grava
   uma final canonica. O processo encerra e o readback SQLite e verificado.
2. Duas copias quiescentes identicas desse runtime servem os bracos independentes.
   Os relatorios mudam; a segunda query nao repete a preferencia.
3. O braco com historia opt-in recupera a preferencia; o controle sem historia
   nao a recebe nem a recupera na analise. Ambos releem os relatorios atualizados.

Cada braco faz duas leituras governadas e tres respostas HTTP: nove respostas
scripted ao todo, zero chamadas de modelo. Finals, citacoes atuais e persistencia
apos restart sao conferidas. O fixture nao recebe a resposta esperada por
construtor, nem usa estado de pedidos anteriores para inferir a preferencia.
Isso prova integracao contextual, nao inteligencia, qualidade Qwen, causalidade
generalizavel, conversa cotidiana livre ou suporte Web/voz novo. Intents e
governanca anteriores continuam delimitando o pedido de analise.

## Duas fragilidades do gate

O standard anterior coletou 11689 testes e falhou em dois; os arquivos passaram
na repeticao sem mudancas (66 testes). A branch historica exata nao foi capturada.
A continuidade reproduziu dois mecanismos de falso negativo sem sleeps:

- `finish` esperava 20 segundos embora o ticket publico dure 120. Worker virtual
  com 40 segundos validos falhava antes de ler o resultado. Agora o teste usa o
  limite publico `TICKET_SECONDS`, sem alterar deadline ou comportamento runtime.
  Fixture `finally` fecha todos os servicos e verifica os workers mesmo se uma
  assercao falha. O teste de persistencia nao estabelece SLA de startup de 20s.
- No teste de binding MCP, um clock local que expira apos construir o Core
  reproduziu `DID NOT RAISE`: o mutator nem chega a executar. O teste de binding
  agora usa relogio local estavel e exige que a adulteracao tenha sido atingida.
  Os clocks reais do cliente/asyncio e testes dedicados de expiry/cancelamento
  permanecem intactos; o caso expirado exige recusa, sem final ou memoria.

RED controlado: 2 failed/5,79s. A primeira execucao em ambiente restrito mostrou
o RED do worker mas travou no caso MCP; foi interrompida, sem resultado MCP.
A repeticao com permissoes de subprocesso produziu os dois REDs. Nao atribuir
automaticamente a falha historica ao mesmo ambiente ou inferir bypass do guard.
GREEN central dos dois arquivos mais lifecycle: 145 passed/186,65s.
CLI diagnostica: RED 7 failed/1 passed, depois 23 passed; com erro publico e
prova de memoria adicionais, selecao integrada: 132 passed/59,04s. Selecoes
sobrepostas, nao somar como casos unicos. Ajustes de quebra de linha do teste
diagnostico posteriores sao somente estilo; regressao fresca incluindo esse
arquivo e os fluxos CLI/historia: 42 passed/100,68s. Ruff global, document
guardrails e diff check passaram. 17 arquivos Python congelados antes do standard.

O primeiro novo standard foi interrompido apos aproximadamente14% ao aparecerem
falhas MCP em serie. Causa documental introduzida nesta continuidade: append de
notas/evidencias fez F01 ultrapassar oito itens por lista. O loader recusou no
RED de `test_current_inventory_exact_fronts_and_baselines`; nao era bypass ou
defeito do parser. Consolidaram-se as listas atuais F01/F02 e referencias, sem
apagar documentos historicos, relaxar validadores ou aumentar limites. Snapshot
MCP completo:21706/24576 bytes; runtime_verified/product_ready continuam false.
GREEN fresco de inventario/CLI/stdio/Core/guardrails:200 passed/137,06s.
O gate interrompido nao e um standard concluido. A segunda execucao integral
concluiu: 11591 passed, 124 skipped, zero falhas/errors, 11715 coletados,
2075,648s de pytest. Encoding, document guardrails e Ruff passaram antes da suite.
XML: `conversation-standard-20261020-02.xml`, na pasta privada de artefatos.
Os 17 hashes Python e o hash do inventario permaneceram identicos do inicio ao
fim. Nenhum piloto executou em concorrencia com os testes. Skips nao validam
plataformas ou capabilities ausentes.

## Modelo real

Preflight anterior somente GET `/api/tags` e `/api/ps`: `qwen3:4b-instruct` instalado,
2497293803 bytes, digest `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`,
nao carregado. Zero inferencias, aquecimento ou descarregamento nesta consulta.
Operador autorizou uma NOVA campanha de ate nove chamadas locais, com duas
interacoes e controle sem historia. Executada uma unica vez apos o standard,
sem concorrencia com testes. Preflight inerte separadamente confirmou zero
inferencias e nenhum runtime criado; a flag explicita reivindicou um diretorio
novo e irrepetivel para a campanha. Contador cobre todas as tentativas, sem
warm-up, retry, OAuth/API paga ou uso dos saldos interrompidos anteriores.

Resultado: 1 tentativa/1 inferencia concluida, 414 tokens de entrada/30 de saida,
primeiro byte e resposta HTTP completa aos 24140ms; transporte, EOF e parse do
provider concluiram. SQLite readonly confirmou `invalid_model_message` nos
eventos `model_tool_loop_finished` e `response_synthesized`, step1/tool_calls0/
observations0: recusa no parser da mensagem interna do loop, antes de proposta,
governanca de ferramenta ou leitura. Nao e falha de transporte, EOF, binding ou
memoria. O runner omitiu esse codigo de sua allowlist e mostrou
`diagnostic_code_withheld`; isso ocultou o diagnostico no log, nao causou a
recusa. O provider ja validara texto nao vazio, UTF8, tamanho e ausencia de NUL;
restam JSON invalido/duplicado/constantes ou root/kind incompativeis. Sem raw
recusado retido, nao e possivel distinguir essas variantes retroativamente.
Nao inferir uma variante textual especifica.
Sem analise aceita. A final nativa de recusa (2635 caracteres) foi persistida,
exportada e conferida exatamente apos reconstruir o Core; isso nao e sucesso
da tarefa. A campanha parou imediatamente, exit1 observado no processo, sem
segunda interacao ou controle. O guard de inferencia mostra `stopped=false`
porque o transporte concluiu; a parada foi aplicada pelo runner ao resultado
recusado do Core. As oito chamadas nao usadas nao autorizam nova tentativa.

Artefatos privados: `memory-phase-real-20261020-01/pilot-diagnostics.jsonl`,
`seed/memory.db` e `seed/events.db`; nenhum raw de modelo recusado foi exibido.
Primeiro byte HTTP nao e primeiro token e nao separa carga de pesos/prefill/
geracao. Digest declarado pelo servidor coincide, sem atestacao de pesos.
Conversa util com modelo real e memoria no segundo turno permanece nao homologada.
Proximo aceite: aderencia do modelo ao protocolo de ferramentas, sem reparar
JSON, remover guardas ou repetir automaticamente. Nova prova exige autorizacao
nova; a recusa atual nao comprova que output estruturado resolveria a variante
desconhecida. O runner executado e seus artefatos ficam preservados.

## REA e Harness2

`binary_session` readonly do REA vivo relatou `open=false`, cleanup nao pendente,
Ghidra 12.1.4 disponivel e Java 21.0.12.1 proveniente da extensao Java do VS Code.
O JAVA_HOME do shell apontava para diretorio ausente; isso nao impediu o servidor
REA de ter seu JDK valido. Nao alterar globalmente PATH/JAVA_HOME para esse teste.
IDA Free 9.4 e `ida_mcp.dll` existem, mas o provider retorna `not_configured`:
instalacao nao equivale a registro upstream/target binding validado.
Nenhum binario foi aberto, nenhum plugin/listener iniciado ou configuracao
global alterada. Servidor REA pacote6.7.0 tem `build_commit=null`; disponibilidade
nao estabelece alinhamento ao SHA do fork usado no experimento estatico anterior.

O [estudo Harness2](../implementation/harness2-assessment-2026-10-20.md) identifica
APIs de encaixe no comparador e Evolution atuais. Absorver o metodo e possivel;
executar o framework exige adapter e experimento isolado proprios. Nao ha
runtime externo instalado, selecao obrigatoria de candidata, permissao editavel
ou promocao automatica. O corpus publico e o budget de despacho nao podem ser
apresentados como holdout secreto ou prova de teto interno de chamadas.

## Verificacao final e rollback

Standard integral aprovado no snapshot congelado, nao somente a bateria focada.
Uma inferencia local executada na campanha nova; nenhuma chamada OAuth/API
paga/commit/push/merge. MB236 inalterado. Memoria real nao promovida pela recusa.
Inventario final sincronizado sem promocao de status: snapshot MCP21768/24576
bytes, listas no maximo8 e textos no maximo390 caracteres; runtime_verified e
product_ready false. Gate quick e bateria fresca sobre esse inventario, CLI,
stdio, Core e guardrails:200 passed/120,469s, zero falhas/errors/skips. XML:
`readiness-final-green-20261020-01.xml`. Os mesmos17 arquivos Python continuam
sem drift depois do piloto e da atualizacao documental. Revisao independente
readonly nao encontrou enfraquecimento acionavel; cleanup de thread nao e
hard-kill, e as amostras nao sao spans unificados entre operacoes.
Omitir `--include-phase-diagnostics` desliga a observacao sem apagar memoria;
nao usar a bridge REA desliga sua admissao. Nenhuma migracao ou dependencia nova.
