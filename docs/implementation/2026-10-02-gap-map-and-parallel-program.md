# JARVIS: lacunas, OAuth, Dots e programa paralelo

Data de verificacao: 2026-10-02.
Baseline auditado: `c3524ab` / `MB-217`.
Status: auditoria e proposta de repriorizacao; nao e implementacao de runtime.

Desdobramento posterior solicitado pelo operador:
[mapa executavel de implementacao paralela](parallel-implementation-map.md).
Ele explicita 13 frentes e tres transversais; o agrupamento de oito frentes
neste relatorio fica como contexto da auditoria, nao lista final de dispatch.
Desenvolvimento isolado pode ocorrer em paralelo antes da promocao de superficie.

Este documento responde ao pedido do operador de investigar Hermes, os novos
recursos da OpenAI, autoevolucao e frentes paralelas. Nao substitui o
Documento-Mestre, a Constituicao, a fila micro nem uma decisao de fase.
Nenhuma autenticacao foi iniciada e nenhuma credencial existente foi lida.
`MB-218` continua o unico item tecnico `ready`; `MB-219` depende dele.

## 1. Diagnostico de produto

O JARVIS possui uma fundacao extensa de contratos, memoria, governanca,
continuidade, observabilidade e operacao reversivel. Ainda nao tem o motor de
linguagem e os consumidores suficientes para transformar essa fundacao em um
assistente fluido de uso diario. Concluir mais microitens nao demonstra, por si,
que uma tarefa real do operador ficou mais facil.

Contagem das 114 capabilities do Implementation Master Map:

| Estado | Quantidade | Leitura correta |
| --- | ---: | --- |
| `implemented_baseline` | 77 | Slice delimitado implementado, nao produto final completo |
| `minimum_baseline` | 8 | MVP delimitado que ainda precisa aprofundamento |
| `partial_runtime` | 7 | Runtime parcial |
| `documentation_only` | 2 | Visao documentada |
| `missing` | 4 | Ausencia registrada |
| `deferred_by_phase` | 13 | Depende de fase/consumer |
| `research_only` | 2 | Horizonte, nao compromisso de produto |
| `human_decision_required` | 1 | Decisao humana/documental |

Os 37 itens fora de `implemented_baseline` nao sao 37 pequenas tarefas. A
fracao 77/114 nao e percentual de conclusao: o mapa inclui documentacao e
comandos CLI, enquanto a lacuna de inferencia nem possui track proprio.

### Inventario completo dos estados limitados registrados

| Classe | IDs e trabalho restante |
| --- | --- |
| Missing | `COG-009`: comparar rotas/planos; `KNW-005`: pesquisa e importacao externa; `SFC-005`: API; `SFC-010`: notificacoes |
| Minimum | `COG-010`: estrategia longa; `EVL-007`: skills de recorrencia; `SPC-006`: onboarding de dominio; `KNW-007`: packs; `KNW-008`: conflitos de fontes; `OBS-006`: evals substantivos por dominio; `GOV-006`: incident response; `SFC-009`: conflitos entre superficies |
| Partial | `MEM-008`: consolidacao; `MEM-009`: retencao/esquecimento; `SPC-007`: memoria profunda delimitada; `OBS-010`: abuso/seguranca; `GOV-004`: mutacao de memoria; `GOV-008`: secrets/privacy; `DOC-008`: consolidacao do roadmap |
| Documentation | `SPC-008`: especialista operacional de software; `SPC-009`: especialista operacional de pesquisa |
| Deferred | `MEM-010/011/012`: memoria temporal/organizacional/vetorial; `ACT-006/007/008/009/010`: browser/computer/software/scheduler/integracoes; `SPC-010`: protective intelligence; `GOV-010`: controles da vertical; `SFC-006/007/008`: web/voz/mobile |
| Research | `EVL-009`: adaptacao parametrica; `EVL-010`: automodificacao profunda |
| Human decision | `DOC-009`: hierarquia/revisao arquitetural |

### Lacunas de produto mal representadas no mapa

- Inferencia real, auth, catalogo de modelos, streaming, limites e erros.
  Executive usa classificacao por palavras; Synthesis compoe texto estruturado.
- Loop bounded de linguagem -> proposta de ferramenta -> decisao do Core ->
  resultado -> sintese, sem ferramenta executada por autoridade do modelo.
- Composicao `MB-218`: configurar roots, executor transacional, autoridade
  compartilhada e verificadores, nao apenas adicionar comandos CLI.
- Escrita/rollback transacionais no Windows: o backend `MB-216` atual aceita
  Linux e falha fechado nas outras plataformas antes de journal/efeito.
  Linux/WSL integrado e paridade Windows nativa sao alternativas distintas;
  nenhuma foi selecionada ou implementada nesta auditoria.
- Instalacao e primeira tarefa real: configuracao guiada, diagnostico e uma
  demonstracao repetivel com retomada entre sessoes.
- Qualidade cognitiva e ganho evolutivo real: contratos/evidencias offline nao
  substituem execucao de tarefas e avaliacao substantiva do produto entregue.
- Pesquisa atualizada: corpus JSON e intake revisado existem, mas nao uma
  rotina de descoberta/importacao web. Radar implementado nao significa
  pesquisa externa autonoma.

Evidencias locais principais: `apps/jarvis_console/cli.py` (`JarvisConsole.build`),
`engines/executive-engine/src/executive_engine/engine.py`,
`engines/synthesis-engine/src/synthesis_engine/engine.py`,
`services/operational-service/src/operational_service/adapters/local_text_transaction.py`,
`services/knowledge-service/src/knowledge_service/service.py`, `pyproject.toml`.

## 2. ChatGPT OAuth como substrato de inferencia

### Hermes versus caminho oficial

O provider `openai-codex` do Hermes usa client ID Codex fixo e
`chatgpt.com/backend-api/codex`. Seu modo opcional `codex_app_server` entrega
tambem o loop de ferramentas ao runtime Codex, nao somente geracao de texto.
Fontes primarias: [auth Hermes](https://github.com/NousResearch/hermes-agent/blob/main/hermes_cli/auth_codex.py),
[constantes](https://github.com/NousResearch/hermes-agent/blob/main/hermes_cli/auth_constants.py),
[runtime Codex](https://hermes-agent.nousresearch.com/docs/user-guide/features/codex-app-server-runtime/).

A OpenAI documenta Sign in with ChatGPT (SIWC) com uso de plano para apps
open-source, locais e self-hosted elegiveis. Nao importa conversas existentes;
apps comerciais/remotamente hospedados possuem condicoes diferentes.
Nao verificamos elegibilidade desta conta ou do cliente JARVIS.
[Escopo oficial](https://developers.openai.com/siwc/token-sharing-open-source).

Proposta: cliente proprio do JARVIS, identificador opaco persistente da
instalacao, registro dinamico, PKCE/state/nonce, validacao de identidade e
consentimento explicito para uso do plano. Nao copiar client ID Hermes nem
ler/reutilizar `auth.json` de Codex/Hermes.
[Registro](https://developers.openai.com/siwc/token-sharing-open-source/sign-in).

Inferencia SIWC usa a API publica `/v1/responses`, nao `backend-api`.
O catalogo da conta vem de `/v1/models`; modelo visivel no aplicativo Codex
nao prova acesso pelo JARVIS. Sucesso exige evento `response.completed`,
nao apenas texto parcial ou lista de modelos.
[Modelos e inferencia](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference).

### Restricoes que mudam o desenho

Na preview SIWC, HTTP exige `store:false`, `stream:true` e contexto em `input`.
Nao aceita `previous_response_id`, `conversation`, `background`,
`max_output_tokens` ou `multi_agent`. Tambem nao oferece Files upload,
transcricao, audio/video, computer use nativo, MCP hospedado, file search,
Code Interpreter ou geracao de imagens. Isso nao impede ferramentas locais
governadas; elas sao outra camada. Nao enviar parametros da API geral sem
verificar compatibilidade com este fluxo.
[Limites da preview](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations).

A API Responses geral tem Multi-agent beta, mas isso NAO demonstra que esse
parametro funciona com token SIWC: esta preview o exclui explicitamente.
Coordenacao propria do JARVIS pode usar chamadas individuais delimitadas.
[Multi-agent API](https://developers.openai.com/api/docs/guides/responses-multi-agent).

Access token dura uma hora; refresh token dura 30 dias e e rotativo.
Projetar refresh serializado, storage protegido fora do repo/telemetria,
logout/revogacao e recuperacao de falhas. Plus compartilha janela de cinco
horas entre apps; Pro nao possui essa janela especifica, o que nao significa
ausencia de todos os limites. Nao trocar silenciosamente para API paga.
[Tokens](https://developers.openai.com/siwc/token-sharing-open-source/token-reference),
[sessoes](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions),
[erros](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery).

### Fronteira arquitetural recomendada

O Core controla contexto, finalidade e decisao; o adapter fornece inferencia;
JARVIS valida e fecha a sintese e a memoria canonica. Primeiro slice sem
ferramentas. Orquestracao, identidade e permissoes nao migram para o provider.
Isso aplica o Documento-Mestre, secao 26.3.1.

Contrato proposto `ModelInferencePort`: request bounded, resposta estruturada,
cancelamento, prazo, contagem de chamadas e uso observado, erros normalizados
e nenhum efeito fora da chamada explicitamente permitida. Controle de
orcamento no cliente deve reconhecer que SIWC nao aceita `max_output_tokens`;
nao prometer teto exato de tokens no servidor.

Codex app-server pode receber token SIWC oficialmente. Considera-lo depois
como executor especialista isolado, nao como simples modelo: ele tem shell,
MCP e agentes locais. Read-only nao significa ausencia de ferramentas.
Necessita prova propria de contencao e governanca antes de promocao.
[Configuracao oficial](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server).

## 3. Dots e lancamentos da semana

O DevDay de 29/09/2026 apresentou Dots, ambientes Codex reutilizaveis, SIWC,
GPT-6.1 Sol e MCP Events. Disponibilidade por conta/workspace e maturidade
variam; anuncio nao comprova acesso local. Para JARVIS, a novidade prioritaria
e um caminho suportado de inferencia e os padroes de continuidade, nao uma
corrida para incorporar todos os produtos.
[Lancamentos](https://learn.chatgpt.com/docs/whats-new/devday-2026).

Dots sao agentes always-on com responsabilidades continuas, memoria, agentes
delegados e computador proprio. A documentacao descreve operacao entre
conversas e acesso por diferentes canais; rollout gradual. Nao identifica um
SDK publico que possamos simplesmente instalar como cerebro do JARVIS.
[Visao de Dots](https://learn.chatgpt.com/docs/dots).

Absorcao proposta, como referencia/experimento e nao promocao automatica:

| Padrao | Traducao JARVIS | Limite/aceite |
| --- | --- | --- |
| Responsabilidade alem de um chat | Objetivo duravel com proximo passo, dono e criterio de resultado | Run concluido nao equivale a entrega aceita |
| Delegacao visivel | Work package com contexto selecionado e resultado verificavel | Filho nao recebe autoridade nem toda memoria do pai |
| Pausar e acordar | Jobs com leases, retomada e condicoes explicitas | Sem worker/host ligado, local nao trabalha; cloud exige infraestrutura |
| Mesma entidade entre canais | Memoria canonica e identidade de superficie | Usar contexto nao concede permissao para divulga-lo |
| Pesquisa proativa separada | Descoberta read-only e candidatos revisaveis | Pesquisa nao autoriza envio, escrita ou controle de computador |
| Atividade e controles | Progresso, outputs, pedidos de decisao e cancelamentos distinguiveis | Parar pai, filhos e recorrencia sao operacoes diferentes |

Fontes: [tarefas e memoria](https://learn.chatgpt.com/docs/dots/tasks-and-memory),
[computadores](https://learn.chatgpt.com/docs/dots/computers-and-apps),
[controles](https://learn.chatgpt.com/docs/dots/controls).

Memoria/contexto atualizavel e continuidade nao comprovam treinamento de
pesos ou automodificacao. As paginas inspecionadas de Dots nao estabelecem
esse tipo de autoevolucao. Nao atribuir ao produto mecanismos nao documentados.

Ambientes preparados sugerem sandboxes repetiveis para nosso especialista
software/eval. MCP Events sugere intake idempotente de eventos, mas o protocolo
esta em draft; nao introduzir dependencia central nova ou scheduler amplo
agora. Modelos e Multi-agent API entram como alternativas avaliadas, respeitando
o contrato e a incompatibilidade SIWC descrita acima.

## 4. Autoevolucao: visao versus funcionamento real

A visao do Documento-Mestre, secao 25, continua correta: observar, refletir,
propor, testar comparativamente, selecionar, consolidar, versionar e reverter.
Hoje temos aprendizado procedural assistido e governado, nao melhoria
autonoma sustentada demonstrada.

| Etapa | Implementado | Limite atual |
| --- | --- | --- |
| Experiencia | Registro automatico de resultado, erros, contexto e feedback | Registro nao implica aprendizagem nova |
| Reflexao | Template automatico: erro -> recuperacao; sem erros registrados -> padrao reutilizavel | Nao interpreta causas abertas com LLM nem verifica sucesso substantivo |
| Recorrencia/skills | Sinais agrupados e instrucoes fornecidas compiladas em candidato inativo | Nao descobre/escreve a skill autonomamente |
| Guidance | Revisao humana; Planning consome etapa/restricao/criterio | Influencia declarada nao prova ganho causal |
| Workflow | Bundle, review, autorizacao, ativacao e rollback verificaveis | Lifecycle seguro nao prova workflow melhor |
| Eval de workflow | Compara observacoes previamente produzidas | Nao executa os workflows nem atesta produtor |
| Eval de skill | Valida checks booleanos fornecidos | Nao executa skill ao vivo |
| Domain eval | Executa Core e mede rota/contratos/fragmentos | Qualidade substantiva do produto ainda limitada |
| Metricas | Separa offline/runtime e marca falta de comparador | Sem comparador, nao alegar ganho sustentado |

Evidencias: `services/orchestrator-service/src/orchestrator_service/service.py`
(`_record_operator_experience` e `_record_post_task_reflection`),
`evolution/evolution-lab/src/evolution_lab/service.py` (mineracao/eval),
`engines/planning-engine/src/planning_engine/engine.py` (guidance),
`tools/workflow_variant_eval.py`, `tools/domain_eval_support.py`,
`docs/operations/workflow-variant-eval.md`,
`docs/operations/workflow-lifecycle.md`,
`docs/operations/longitudinal-learning-metrics.md`.

Proximo ciclo convincente: tarefa real -> falha/correcao -> hipotese com
evidencia -> candidato inativo -> execucao baseline/candidato em sandbox
equivalente -> validacao separada -> review -> reutilizacao -> ganho medido.
Nao mudar pesos ou codigo soberano para realizar esse primeiro ciclo.

Execucoes devem fixar inputs, memoria equivalente, versoes, avaliadores e
orcamento; repetir amostras e usar holdout. Medir sucesso, qualidade, retrabalho,
latencia, custo e regressoes. O executor confiavel emite a evidencia; nao aceitar
um booleano fornecido pelo proponente como prova de sucesso real.

## 5. Oito frentes, com ownership e dependencias

Sao work packages propostos, nao oito capabilities promovidas ou oito itens
ativos. Nesta sessao, tres agentes executaram auditorias read-only de
OAuth/Hermes, autoevolucao e lacunas. Nao houve implementacao paralela.

| Frente | Ownership proposto | Entrega verificavel | Dependencias |
| --- | --- | --- | --- |
| F1 Inferencia/auth | Novo pacote isolado de adapters/modelo/auth e testes | OAuth seguro, catalogo, resposta real, streaming e falhas explicitas | Port frozen; consentimento para smoke real |
| F2 Conversa/raciocinio | Engines Executive/Planning/Specialist/Synthesis, por submodulo | Pedido aberto -> contexto -> plano -> resposta util | F1; integracao central pelo coordenador |
| F3 Console/superficies | `apps/jarvis_console`, exceto composicao `JarvisConsole.build` do coordenador; depois API/web thin | MB218 utilizavel; depois mesma entidade via API/UI | MB217 agora; API/UI apos MB219 e decisao de fase |
| F4 Operacao/ferramentas | Adapters Operational e seus testes, por plataforma | Apply/rollback reais na plataforma escolhida; depois tools bounded | Contratos de grants/receipts; escolha Linux/WSL ou Windows |
| F5 Conhecimento/memoria | Knowledge/ingestao/recall/retention em modulos separados | Fontes atuais, contexto entre sessoes e esquecimento governado | Read/provenance ports; F1 para sintese aberta |
| F6 Trabalho duravel | Novo worker/job e adapters finos de notificacao | Retomar responsabilidade, cancelar e avisar resultado | Core/acao maduros; decisao de fase; nao agora |
| F7 Evolucao medida | Evolution Lab e runners comparativos separados | Propor, executar comparacao e reutilizar melhoria medida | F1 + casos reais + F8; lifecycle existente |
| F8 Qualidade/utilidade | Fixtures E2E, testes de integracao, metricas/gates | MB219 e placar de tarefas realmente resolvidas | Pode iniciar fixtures ja; cada frente faz seus testes |

Coordenador unico possui `shared/contracts/__init__.py`, registries, migrations,
composicao do console e Orchestrator/Governance/Memory centrais. Integracoes
nesses arquivos passam por ele; nao dividir arquivos gigantes entre writers
simultaneos. Cada agente recebe entradas, saídas, arquivos exclusivos, testes,
limites e condicao de aceite; resultados passam por revisao independente.

Com quatro slots disponiveis, usar coordenador + ate tres workers por onda,
nao prometer oito agentes simultaneos. Implementacao multiagente neste repo
e distinta de habilitar multiagentes no runtime do proprio JARVIS.

### Ordem e fronteiras de promocao

Esta sequencia descreve a proposta inicial de integracao. Para desenvolvimento
paralelo de clientes/adapters isolados e ownership detalhado, seguir o mapa
executavel acima; MB218/219 nao bloqueiam todos os prototipos das superficies.

1. Congelar o port de inferencia e o pacote de tarefas uteis. MB218 divide-se
   em composicao/CLI, observabilidade e E2E com ownership exclusivo.
   Experimento provider isolado e fixtures podem avancar em paralelo, sem
   promocao runtime ou abertura de superficies deferred.
2. Fechar MB218 -> MB219 e registrar repriorizacao formal do produto. Abrir
   slice de inferencia sem ferramentas; conectar conversa util ao Core.
3. Demonstrar uma tarefa real completa na plataforma operacional escolhida;
   aprofundar memoria/conhecimento que essa tarefa demanda. API thin/UI
   somente com contrato e decisao de fase registrados.
4. Depois, responsabilidades duraveis, notificacoes e especialistas
   operacionais; evolucao comparativa acompanha esses consumidores.
5. Voz/mobile, grafos/vetores/organizacao e verticais entram por evidencia;
   adaptacao de pesos/automodificacao profunda continuam pesquisa separada.

WIP-1 refere-se ao item integrado da fila atual. Subtarefas disjuntas podem
ser paralelas. Mudar para multiplos itens ativos exige repriorizacao registrada;
esta proposta nao altera silenciosamente a politica ou o backlog.

## 6. Marcos orientados a resultado

| Marco | Demonstracao de aceite |
| --- | --- |
| M1 Conversa real com continuidade | Entrar pelo fluxo autorizado, escolher modelo elegivel, responder tarefa aberta, lembrar contexto no dia seguinte, falhar claramente sem quota/consentimento |
| M2 Uma tarefa util ponta a ponta | Pedido -> plano -> entrega inspecionavel -> confirmacao exata -> efeito -> receipt/status -> restart -> rollback; no ambiente escolhido |
| M3 Aprendizado comprovavel | Correcao vira candidato; baseline/candidato executados de fato; review; reutilizacao; melhoria e ausencia de regressao medidas |
| M4 Responsabilidade continua | Trabalho aprovado retoma apos crash, respeita prazo/orcamento/cancelamento e notifica so resultado relevante |
| M5 Produto multissuperficie | API/UI mostram o mesmo objetivo, memoria, permissao e resultado sem criar cerebro paralelo |

M1 nao substitui gates nem promove acao. M2 nao autoriza autonomia ampla.
M3 exige varias observacoes e validacao separada, nao uma resposta melhor.
Nao ha prazo ou percentual de conclusao confiavel antes de executar esses
pilotos. "Sistema completo" deve ser definido por escopo de produto; capacidades
de pesquisa nao tornam esse escopo uma fila infinita de implementacao.

## 7. Testes e fechamento de cada slice

- F1: PKCE/state/nonce, identidade trocada, refresh concorrente/revogado,
  quota, timeout, stream interrompido, redaction e ausencia de efeito extra.
- F2/F5: contexto correto, fontes conflitantes, prompt injection, incerteza,
  memoria entre sessoes e isolamento de contexto por sujeito/canal.
- F3/F4: E2E real, tamper/replay, grant/challenge exatos, bytes restaurados,
  crash/restart/edicao humana e plataformas unsupported fail-closed.
- F6: lease/retry/idempotencia, cancelamento pai/filho/schedule, host offline,
  nenhuma mensagem ou acao sem permissao.
- F7/F8: produtos avaliados substantivamente, inputs equivalentes, evidencias
  confiaveis, holdout, repeticao e regressao bloqueando promocao.
- Cada frente entrega testes locais + E2E afetado, observabilidade, runbook,
  rollback e HANDOFF sincronizado. Gate standard por slice; release para
  promocao/liberacao conforme risco. Gate nao constitui autorizacao humana.

Esta rodada altera apenas planejamento/documentacao. Nao integra OAuth,
modelos, Dots, MB218 ou executor Windows; nao efetua commit/push.

Fechamento: tres revisoes independentes dos achados; `git diff --check`,
mojibake/BOM, document guardrails e gate standard completos passaram no
Windows usando o Python da `.venv`. Testes pulados nesta plataforma nao
representam validacao Linux nova. Nao houve gate release, login ou smoke
autenticado; promocao runtime nao esta em escopo desta rodada.
