# Campanha pública de missões do harness

Atualizacao2026-10-18: adapter canonico agora isola brief de binding/fontes pela
seam reviewed existente (bundle integral512/brief2048). Nao resolve envelope do
grader, briefs ambiguos ou campanha util. Nova prova separada de conversa com
gpt-6.1-sol renovou sessao expirada da mesma conta e parou na primeira inferencia
HTTP200/Content-Typeausente, sem resposta aceita/retry. Runbooks:
mission-routing-reviewed-sources.md e canonical-history-conversation-pilot-2026-10-18.md.
Resultados anteriores abaixo sao historicos, nao reexecutados apos esta mudanca.

Data: 2026-10-17. Protocolo opt-in implementado, baseline nativa executada e
um único piloto autorizado com conta real interrompido na sessão expirada.
Não houve resposta de modelo concluída nem comparação de qualidade válida.
Testes/transporte injetado continuam distintos da execução real abaixo.
O primeiro gate standard foi interrompido para incluir correções. O standard
final Windows passou: 10403 passed, 121 skipped, zero falhas/errors; 10524
casos no XML e 15 hashes de fontes/testes preservados. Isso fecha o protocolo
local, não homologa qualidade de modelo real ou conclui a campanha útil.

## O que está sendo medido

O catálogo `operator-missions-v1` contém 25 missões autoradas e sintéticas,
rotuladas `public_authored_synthetic`, sem dados privados do operador.
Há 16 casos `dev` e 9 `probe`: ambos são públicos, não um holdout secreto.
Conhecer ou ajustar o harness a esses casos pode melhorar o resultado sem
demonstrar generalização. O corpus anterior `operator-tasks-v1`, seus três
casos, digest, evaluator e defaults permanecem separados e inalterados.

Cada missão tem ID, categoria, split, brief, fontes, capabilities exigidas,
limites de revisão e digest. Fatos esperados, ordem esperada e artefato-oracle
ficam no avaliador; não entram no `ExecutionRequest` enviado ao candidato.
Esse request reutiliza `Binding`, `ExecutionRequest`, `ExecutionResult` e
`Source` v1: brief, fontes e binding públicos, deadline e `history=None`.

| Grupo | Dev | Probe | Recorte |
| --- | ---: | ---: | --- |
| Relatório/pesquisa | 3 | 2 | Correção, conflito, risco, injeção de fonte e limite da evidência. |
| Dados/artefato | 3 | 1 | CSV de despesas, deduplicação JSON/CSV e reposição proposta. |
| Priorização | 2 | 1 | Tickets, dependências de roadmap e janela de manutenção. |
| Memória/correções | 2 | 1 | Histórico corrigido, isolamento de sujeito e recall canônico. |
| Browser | 2 | 1 | Horário observado, formulário apenas rascunhado e navegação multietapa. |
| Code | 2 | 1 | Revisão estática, código proposto e execução de testes. |
| Integrações | 1 | 1 | Mapeamento proposto e leitura observada de conector. |
| Retomada | 1 | 1 | Decisão diante de dispatch incerto e recuperação canônica observada. |

IDs públicos por grupo:

- Relatório: dev `rpt-corrected-brief`, `rpt-source-conflict`, `rpt-release-risk`;
  probe `rpt-source-injection`, `rpt-evidence-boundary`.
- Dados: dev `data-expense-csv`, `data-incident-json`, `data-deduplicate-csv`;
  probe `data-stock-reorder`.
- Priorização: dev `priority-support`, `priority-roadmap`;
  probe `priority-maintenance`.
- Memória: dev `memory-meeting-correction`, `memory-canonical-recall`;
  probe `memory-subject-scope`.
- Browser: dev `browser-open-hours`, `browser-form-draft`;
  probe `browser-multistep-navigation`.
- Code: dev `code-review-boundary`, `code-patch-draft`; probe `code-run-tests`.
- Integração: dev `integration-field-map`; probe `integration-read-status`.
- Retomada: dev `resume-uncertain-dispatch`; probe `resume-canonical-recovery`.

Os IDs completos e capabilities atuais podem ser lidos sem abrir conta,
construir Core ou despachar port:

```powershell
python -m evals.operator_tasks.campaign_cli catalog
```

O catálogo é a fonte para seleção e digest, não uma pontuação pré-calculada.
Fontes `fixture://` e endereços `example.invalid` são fixtures autoradas,
nunca alegações de navegação na Web pública ou de integração de produção.

## Produto e avaliação fechados

O candidato deve devolver JSON UTF-8 com apenas `binding`, `status` e
`product`. O binding precisa repetir exatamente a execução e o digest da
missão. O produto contém apenas:

```text
kind: categoria solicitada
draft: true
facts: objeto de valores inteiros ou strings
citations: [{key, source_ref, start, end}]
order: array de IDs únicos, ou []
artifact: null ou {filename, media_type, text}
```

Cada fato deve ter uma citação contígua, em offsets de caracteres da fonte
fornecida. O grader confere valores/tipos, fonte e trecho, ordem, nome/media
type e conteúdo do artefato. CSV aceita diferenças de quebra de linha, não
células extras ou fórmulas; JSON aceita ordem de chaves, não chaves duplicadas
ou equivalência indevida entre booleano e inteiro. O draft de código tem um
formato deliberadamente estreito, não avaliação de equivalência semântica.
O JSON é limitado a 16 KiB e o texto de artefato a 8192 caracteres.

Não são aceitos campos de score, evaluator escolhido pelo candidato,
autorizações ou afirmações de recibo. Duplicatas, tipos impróprios, JSON
parcial, caracteres recusados e binding stale não fabricam produto válido.

Os resultados do grader são:

- `passed`: os critérios determinísticos daquele recorte passaram;
- `needs_rework`: produto bem formado, mas um ou mais critérios falharam;
- `blocked`: falta capability declarada pelo host, conclusão observada ou
  evidência independente exigida;
- `invalid_output`: envelope, produto ou binding recusados.

Estilo, utilidade para o operador, raciocínio amplo e qualidade geral exigem
revisão humana. Uma declaração do host também não é prova criptográfica.
Fonte correta não vira autoridade de execução; uma fonte com instrução
maliciosa continua sendo dado não confiável.

## Seis casos exigem observação real

| Missão | Capability que exige evidência independente |
| --- | --- |
| `memory-canonical-recall` | `memory_recall` |
| `browser-open-hours` | `browser_navigation` |
| `browser-multistep-navigation` | `browser_navigation` |
| `code-run-tests` | `code_execution` |
| `integration-read-status` | `integration_read` |
| `resume-canonical-recovery` | `durable_continuation` |

Esses casos não passam porque o candidato escreveu “feito”, copiou a resposta
da fixture ou produziu JSON perfeito. Além das capabilities do host, exigem
`verify_effect(binding, effect_capabilities)` independente, fornecido pela
composição confiável e não pelo resultado do modelo. O retorno precisa ser
`True` booleano exato. O host é responsável por verificar um recibo real,
correlacionado com a execução, e não por retornar `True` incondicionalmente.
Um callback positivo em teste de unidade prova apenas essa fronteira de API.

Os braços da CLI atual expõem somente `text_reasoning`, `source_reading` e
`artifact_drafting`; não fornecem esses seis executores/recibos. Portanto os
seis casos são contabilizados como `unsupported`, sem despacho, e continuam
no denominador. Os outros 19 são análises/rascunhos: preparar um formulário
não é submetê-lo; revisar código não é executar testes; analisar um checkpoint
incerto não é retomar uma tarefa. A campanha não promove essas capabilities.

## Duas execuções diferentes

### Baseline nativa: catálogo completo

```powershell
python -m evals.operator_tasks.campaign_cli native-baseline --authorized --timeout-seconds 30 --campaign-timeout-seconds 600
```

São 25 missões × 2 repetições = 50 células do braço `jarvis-native`, não
garantia de 50 chamadas ao Core. As seis capabilities não disponíveis geram
12 células `unsupported`; no máximo 38 despachos nativos elegíveis restam,
antes de cancelamento, prazo ou outras recusas. Cada despacho elegível usa
Core real em diretório temporário fora do repositório/OneDrive, com SQLite
descartável, sem abrir memória de produção, conta OAuth ou modelo externo.
O Core mantém governança, síntese final e memória canônica.

A segunda referência da grade, `unavailable-reference`, tem capabilities
vazias e não é executada. Suas 50 células não executadas permanecem visíveis:
a campanha total tem 100 medições esperadas. Isso não representa Hermes,
Dots, Codex ou qualquer harness externo executado, nem uma comparação válida
de qualidade entre dois sistemas disponíveis.

A porta nativa apresenta a final canônica exata ao grader, sem converter
prosa para o JSON pedido, completar fatos ou reparar respostas. Uma resposta
nativa legítima pode não satisfazer esse contrato de produto. Concluir que
um critério falhou não demonstra automaticamente a causa ou uma incapacidade
geral do Core. Registrar a classe de falha observada, sem ajustar a resposta
ao oracle durante a medição.

### Piloto de modelo: somente dois casos dev

A autorização desta rodada é limitada à mesma conta ChatGPT/Codex via OAuth
já selecionada, modelo `gpt-6.1-sol`, no máximo 10 tentativas de `infer` no
total, sem renovação de sessão, login novo, retry automático ou fallback pago.
Se a sessão estiver expirada ou houver falha de inferência/sessão/controle,
parar e relatar; não ampliar a autorização para completar o número planejado.

A seleção implementada são os dois primeiros casos `dev` compatíveis com
texto/rascunho e sem efeito: `rpt-corrected-brief` e `rpt-source-conflict`.
Dois casos × dois braços × duas repetições = 8 despachos planejados. O teto
compartilhado de 10 tentativas inclui falhas e abertura lazy que não conclui;
não é autorização para retries ou para mais missões. Pode haver menos
inferências se Core, prazo ou cancelamento recusarem o caminho.

Os dois braços são:

- `model-reference`: uma inferência do mesmo modelo, sem ferramentas,
  persistência ou Core; referência one-shot, não Hermes ou outro produto;
- `jarvis-canonical`: o modelo como complemento generativo do Core, com
  ALLOW nativo, final canônica e readback exato. O grader recebe apenas a
  análise literal já registrada nessa final, identificada como não verificada;
  não há reparo de JSON, inserção de oracle ou substituição da síntese soberana.

O guard é compartilhado e lazy. Uma falha de inferência ou sessão o interrompe
e impede chamadas seguintes. Uma inferência concluída com produto malformado
ou `needs_rework` não é, por si só, uma falha de transporte/sessão nem aciona
esse stop. Não confundir a pontuação do produto com a disponibilidade do motor.

Exemplo de comando com placeholders; substituí-los por diretório privado e
identificador do perfil da mesma conta já configurada, não por tokens:

```powershell
python -m evals.operator_tasks.campaign_cli pilot --authorized --confirm-input --credential-dir "ABSOLUTE_PRIVATE_CREDENTIAL_DIRECTORY" --profile-ref "PROFILE_REF_OF_SAME_ACCOUNT" --model gpt-6.1-sol --max-calls 10 --timeout-seconds 30 --campaign-timeout-seconds 600
```

O caminho deve ser absoluto, fora do repositório e do OneDrive. O profile ref
válido tem formato `profile-` seguido de 64 dígitos hexadecimais minúsculos.
Não enviar senha, código OAuth, cookies, tokens ou conteúdo do credential
store. Flags de autorização e referências de perfil não autenticam uma pessoa.
Os comandos acima descrevem uso local; não concedem nova autorização futura.

## Leitura honesta das métricas

`completed` na campanha significa que as células selecionadas foram
contabilizadas, não que todas passaram. `inconclusive` informa interrupção
de controle/prazo/limite. `not_run`/`unsupported` não devem desaparecer do
denominador nem ser convertidos em sucesso por recusa segura.

O relatório conserva braço, revisão, evidence mode, modelo/provider, ambiente,
política, capabilities, limites, categoria/split/repetição e classe de resultado.
A ordem dos braços alterna entre casos e repetições. Condições declaradas iguais
permitem apenas `matched_configuration_only`, não comprovação de orçamento
interno idêntico, equivalência experimental completa ou vencedor.

`port_dispatches` não é número de chamadas HTTP nem de inferências internas.
O guard do piloto conta tentativas de `infer`, incluindo as que falham.
Catálogo/carregamento e transporte têm suas próprias operações; não inferir
o número de requests HTTP desse contador. Tokens só são informados quando
observados e completos. Custo, consumo monetário e quota API/da conta continuam
desconhecidos, não zero; não há estimativa inventada de preço ou saldo.

Não exportar prompts, fontes, respostas, artefatos ou credenciais nos relatórios
de métricas. Filtros de display e limites não são DLP universal. A memória do
piloto é descartável; isso não muda a política ou os dados do runtime do usuário.

Exit 0 indica que a CLI produziu um resultado: examinar status e medições no
JSON. Exit 2 indica recusa da CLI; exit 3 vale para interrupção que chegou até
seu handler. Interrupção capturada por uma porta/guard pode produzir campanha
inconclusiva ou resultado de erro com exit 0. Deadlines são cooperativos e
checados no retorno, não preempção de processo ou sandbox para código hostil.

## Resultados observados em 2026-10-17

### Baseline nativa completa

Artefato local fora do repositório:

`C:/Users/vtham/.codex/visualizations/2026/08/11/019ff2ec-5e21-75a2-a819-f8cf4aa2b4e0/mission-campaign-20261017/native-baseline.json`

| Braço | Denominador | Despachos | Não executadas | Unsupported | Produtos passed |
| --- | ---: | ---: | ---: | ---: | ---: |
| `jarvis-native` | 50 | 38 | 12 | 12 | 0 |
| `unavailable-reference` | 50 | 0 | 50 | 50 | 0 |

As 100 células foram contabilizadas. `status=completed` significa conclusão
da contabilização, não êxito das tarefas; `comparison_status=not_comparable`.
No braço nativo, os 38 despachos resultaram em `needs_decision`; houve 36
turnos do Core e `canonical_finals_verified=0` na porta de avaliação.
Esse zero não apaga os turnos gravados: significa que nenhuma final percorreu
o aceite/readback de produto dessa porta. Não houve produto aprovado pelo
grader, modelo externo, conta aberta ou harness externo executado na baseline.
As 12 células nativas unsupported são os seis casos de efeito × duas
repetições, sem fingir browser, integração, execução de código ou retomada.

O diagnóstico lexical público do primeiro brief encontrou clarificação
nativa: texto citado ou de fonte não estabelece escopo operacional
(`quoted or source text cannot establish operation scope`). Isso é evidência
da decisão realmente tomada, não um ALLOW presumido a partir da intenção do
teste. Os E2E passaram a registrar a decisão nativa real, sem bypass ou
relaxamento das guardas; o caminho positivo de análise canônica accepted é
verificado separadamente. O resultado observado não é um aceite genérico
dos briefs nem prova de que o Core tenha entregue relatórios úteis nessas
missões.

A recaptura após as correções, em `native-baseline-observed.json` no mesmo
diretório de artefatos, manteve 38 despachos, 36 turnos Core, zero produtos
aprovados e zero finais verificadas pela porta. Registrou
`clarifications_required=38`, `native_decisions_required=36` e duas recusas
de escopo antes de entrar no Core. São contadores sobre os mesmos despachos,
não 38 + 36 execuções distintas. O braço nativo continua com 50 células,
12 unsupported; a grade total continua com 100 células e sem referência
externa comparável.

Zero produtos neste contrato não significa inteligência zero. O protocolo
artificial serializa brief, binding e fontes no texto avaliado pelo Core,
acionando falso escopo lexical/clarificação em vez da rota de tarefa textual
pretendida. A próxima prioridade é um adapter de entrada estruturada e uma
rota de escopo apropriada, preservando a governança, antes de nova campanha
real consentida. Não converter esse diagnóstico em ALLOW forçado, resposta
reparada pelo oracle ou prova de competência ainda não medida.

### Único piloto OAuth autorizado

Artefato local fora do repositório:

`C:/Users/vtham/.codex/visualizations/2026/08/11/019ff2ec-5e21-75a2-a819-f8cf4aa2b4e0/mission-campaign-20261017/approved-model-pilot.json`

Foi executada uma única invocação do piloto, na mesma conta selecionada,
modelo solicitado `gpt-6.1-sol`, provider `responses_plan`, teto compartilhado
de 10 tentativas. O observado foi **1 tentativa de inferência e 0 concluídas**,
não oito chamadas feitas. As oito células planejadas foram contabilizadas:

| Braço | Denominador | Despachos | Não executadas | Produtos passed |
| --- | ---: | ---: | ---: | ---: |
| `model-reference` | 4 | 1 | 3 | 0 |
| `jarvis-canonical` | 4 | 0 | 4 | 0 |

Diagnóstico sanitizado observado, em ordem:

1. `session_preflight`: completed;
2. `catalog`: started;
3. `catalog`: failed, `siwc_credential_expired`;
4. `session_result`: failed, `session_inference_failed`.

O carregamento lazy da conta/perfil foi invocado, mas não houve inferência
concluída ou resposta aceita do modelo. O guard parou na primeira falha,
`stopped=true`; nenhum refresh, login novo, fallback pago ou retry foi feito.
O braço canônico não foi despachado: `core_turns=0` e nenhuma final canônica
verificada nesse piloto. A campanha é `inconclusive`, reason `cancelled`,
porque o stop do guard alimenta seu controle de cancelamento; o diagnóstico
observado é sessão expirada, não cancelamento manual comprovado.

`http_request_count=null`: não foi estabelecida uma contagem de requests HTTP.
Tokens de entrada/saída, custo e quota continuam desconhecidos, não zero.
`matched_configuration_only` descreve a configuração declarada, não um
experimento pareado concluído. Os zeros não permitem comparar qualidade,
atribuir vencedor ou homologar disponibilidade do modelo para o JARVIS.
Não houve segunda tentativa para obter uma saída favorável.

### Histórico de testes da integração

- Primeira integrada: 236 passed, 5 failed, 2 errors. As cinco fixtures
  usavam o run ID de controle `run`, que acionava guardas; as fixtures foram
  corrigidas sem relaxar o Core. Dois IDs de parametrização foram encurtados
  para os limites de caminho no Windows. Integrada revisada: 244 passed.
- CLI: um erro de collection por colisão de basename foi corrigido movendo/
  renomeando o teste. A execução no sandbox encontrou três `PermissionError`
  durante limpeza de fixtures. Isso não foi tratado como sucesso do runtime.
- A rodada no host teve 45 passed e 2 failed: expectativas E2E de ALLOW para
  o brief público não correspondiam à decisão real do Core. Não foi corrigido
  um suposto defeito do engine para forçar o resultado; os testes passaram a
  conferir a decisão observada e o positivo accepted ficou separado.
- Foco anterior dos oito arquivos: 269 passed em 6.01s. A revisão final ainda
  encontrou dois P2 reais: `KeyboardInterrupt` capturado pela porta canônica
  e revogação/prazo durante a factory sem nova checagem antes do dispatch.
- Três REDs reproduziram as bordas; os dois casos de revogação/prazo
  comprovaram `calls=[True]`, isto é, Core chamado quando deveria permanecer
  sem despacho. O integrador corrigiu a porta canônica para propagar
  `KeyboardInterrupt` e revalidar o controle antes de `handle_input`.
  Foco final: 272 passed em 22.84s. Isso prova o recorte exercitado pelos
  testes, não efeitos físicos ausentes nem qualidade SOTA.
- O primeiro gate standard foi interrompido em aproximadamente 2% para
  incorporar essas correções; não é aceite. O novo gate standard Windows
  terminou com exit 0 em `mission-campaign-final-gate-20261017`: 10403 passed,
  121 skipped, zero falhas/errors em 1717.77s. O XML confirma 10524 casos;
  todos os 15 hashes de fontes/testes congelados permaneceram iguais.
  Esse é o fechamento do protocolo local, não aceite de modelo/campanha real.

## Limites de conclusão e próximos registros

Prioridade técnica derivada, ainda não implementada: separar a instrução humana
do contexto fornecido (binding, fontes e protocolo), em vez de serializar tudo
no texto roteado pelo Executive. Avaliar contexto tipado, limitado e vinculado
ao request/session/principal, validado antes de despacho e publicação, usando
o precedente de reviewed-source sem ampliar silenciosamente seus limites.
Alternativa maior: ferramenta readonly governada de leitura de fontes
fornecidas, que exige experimento e orçamento de comparação próprios.
Nenhuma opção autoriza enfraquecer a guarda lexical, fornecer oracles,
reformular casos para subir a nota ou contornar síntese/memória canônicas.
O aceite deve manter o corpus/grader, bloquear pedidos humanos destrutivos e
tratar instruções dentro das fontes apenas como dados sem autoridade.

A evidência do gate integrado aprovado, XML e hashes está na pasta local
`C:/Users/vtham/.codex/visualizations/2026/08/11/019ff2ec-5e21-75a2-a819-f8cf4aa2b4e0/mission-campaign-final-gate-20261017/`.
Preservar falhas e execuções parciais; uma nova tentativa de modelo requer
direção compatível com a autorização do operador, não é consequência
automática deste runbook.

Este corpus pequeno/público, dois casos dev em piloto e duas repetições não
demonstram SOTA, equivalência com Hermes/Dots/outros agentes, autonomia geral,
qualidade de longo prazo, browser/código/integração operacional ou continuação
durável do loop. `winner`, `improvement_claim`, `promotion_allowed` e
`sota_claim` não são promovidos pela campanha. O primeiro objetivo é localizar
gaps verificáveis entre tarefa, suporte declarado, saída canônica e produto útil.

Desativação: não invocar a CLI/campanha. Nenhum scheduler é instalado, nenhum
login/refresh é iniciado pelo catálogo e nenhum default v1/Core é substituído.
Sem dependência central nova, commit, push ou merge implícito.
