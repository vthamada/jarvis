# REA estático e diagnóstico local de inferência

Data: 2026-10-20. Recorte opt-in; não altera a inicialização padrão nem promove
um executor externo ao Core. Standard integral aprovado na continuidade abaixo;
dispatch REA governado e conversa util com modelo real continuam pendentes.

## O que foi implementado

`apps.jarvis_rea` admite Evidence de análise estática JavaScript e projeta somente
contagens e coverage para a seam soberana de revisão de fontes. O fluxo é:

```text
Evidence local selecionado -> validação/projeção -> revisão explícita
  -> Core/governança -> síntese nativa -> memória canônica/readback
```

A pergunta é literal e construída localmente; nenhum código, caminho, label,
limitação livre ou instrução do grafo entra no intent ou na seleção revisada.
O resumo tem até 512 caracteres. O envelope externo tem teto de 2 MiB, profundidade
24, 50.000 valores, coleção de 10.000 itens e string de 64 KiB. A CLI recusa
chaves JSON duplicadas, valores não finitos, UTF-8 inválido, arquivos não regulares,
UNC, symlinks/reparse points e troca de identidade do descriptor na abertura.
Essa seleção não é snapshot atômico nem prova contra toda corrida em ancestrais.

Uso explícito, com arquivo local regular selecionado pelo operador:

```powershell
python -m apps.jarvis_rea --evidence C:\JarvisPrivate\rea-evidence.json --authorized --confirm-reviewed-selection --session-id rea-static-review
```

`--include-content` inclui a resposta canônica se a proteção de exibição permitir;
o padrão só retorna status/contagens. A CLI normal usa o runtime local já existente
de source-review; portanto persiste a final conforme a política normal do Core.
As flags declaram consentimento/seleção local, não autenticação humana forte.

O documento admitido é `analyze_javascript_application`, provider
`rea-javascript-application`, versão `1`, formato `directory`, integridade `fail`.
Há validação dos campos consumidos, bindings e referências de grafos, contagens e
coverage; não é reimplementação integral do schema REA ou verificador RFC 8785.
Mesmo um documento estruturalmente válido pode ter sido fabricado.

Por isso `authority=none`, `origin_status=declared_unverified`,
`rea_semantic_digest_verified=false`, `rea_call_governed_by_core=false` e
`runtime_capability_promoted=false` permanecem explícitos. A URL fixa identifica
a revisão de referência do adapter; não autentica o produtor do arquivo.
A coleta acontece fora do Core: não se alega dispatch governado do REA.

## Referência e prova externa

Fork solicitado: [vthamada/rea](https://github.com/vthamada/rea/tree/00a055be0fad728e1ba183c8de968d5538ba11ef),
commit `00a055be0fad728e1ba183c8de968d5538ba11ef`, pacote 6.7.0, licença MIT.
Não substituir por upstream/latest apesar dos links do manifest.

O Node global v25.9.0 não satisfaz os engines do fork. O Node bundled v24.19.0
satisfaz, mas o checkout não contém o addon/manifest nativos exigidos no Windows;
o build desse addon exige Linux/MinGW. Nenhum addon externo foi introduzido.
O Docker Desktop instalado foi iniciado, sem reset ou remoção de dados;
o daemon 29.8.1 respondeu com a permissão adequada.

Experimento Linux em artefatos privados, fora do repositório: archive Git do pin
acima, SHA-256 `906f8d70ff42621fb4ca3cd65526ebeb3ef84e7ebecf95149a858b8525b4d69e`.
Imagem oficial Node 24.19.0/bookworm-slim amd64, digest
`sha256:e5a8dee7bc1e6a215d224a7ef8206f7e77271bc3cabd5febf2beafac0674f174`.
Build usa `npm ci --ignore-scripts` e o script `compile` inspecionado, sem setup,
MCP global, instalação global, credenciais ou modelo. O contexto Docker contém
somente o archive público e Dockerfile, nunca o restante da pasta de artefatos.
Primeiro build falhou na obtenção de procps: conexão Debian HTTP/80 recusada.
Uma correção local do Dockerfile para HTTPS oficial, sem relaxar certificados,
também falhou por conexão recusada em 443.

A alternativa offline funcionou.549 dependências Linux exatas do lock foram
obtidas no host, nos artefatos: Node24.19.0/npm11.12.1, ambiente sanitizado,
configs sem conta, cache próprio e scripts/audit/fund desativados. Não entraram
no JARVIS. Imagem oficial Node/bookworm com procps, digest
`sha256:107ceb6ad85808049dccef12414bf17b08eceb299eaf755c0339dc5fc8958d6b`.
Contexto estrito acrescentou só o cache público; `npm ci --offline --ignore-scripts`
e `npm run compile` terminaram com a rede dos passos de build desativada.
Imagem resultante:
`sha256:edb29cc95bd245ce1e85373247b5fdfaf0046a9ec280ad781464b45f630b29cf`.

Duas análises do mesmo alvo sintético (dois JS/package.json) ocorreram em
contêineres próprios: sem rede, rootfs readonly, usuário node, sem capabilities,
no-new-privileges, CPU1/RAM768MiB/64PIDs/tmpfs128MiB, timeout externo40s e worker
heap128MiB/prazo10s. Só alvo readonly e sentinel foram montados, nunca contas,
repo JARVIS ou socket Docker. O sentinel no topo do JS não foi criado;
contêineres removidos e fonte preservada. Imagem/cache opcionais ficam fora do repo.

Evidence real:56.187bytes,2JS parseados,0parse failures,9nós/8arestas. A projeção
reportou imports=0/modules=0; imports conta somente arestas `imports` do
application graph, não todos os imports sintáticos ou relações semânticas.
Zero não comprova ausência de dependências. Não inflar contagem para encaixar
uma expectativa da fixture.

Na segunda observação, revisão/Core/SQLite reais registraram1final nativa1717chars
e3eventos correlacionados, idêntica após reconstrução. Decisão soberana
`defer_for_validation`, seleção `quoted_for_review`: não é análise útil homologada
nem execução autorizada. Oráculos iniciais do script privado presumiam ALLOW e
aresta imports e falharam; readback conferiu os valores efetivos, sem terceira
análise REA ou nova interação/modelo. Raiz REA:
`f893c8d00d97844e3218b9943eebfd4aa15b7d79d725d52385dbb17dfa985347`.
Hash da final:`49ad478a237718ae1c687d0ff5d8a69e30913eb2365ec0724db03170f276af69`.
Recibo privado:`rea-static-proof-20261020/run-f0a5e5a43ecc4168bbdf48ca75da13fa/proof.json`.
Não foi relaxado guard para forçar ALLOW; prova limitada não autentica o arquivo
nem fecha dispatch governado.

## Capacidades e sequência de absorção

| Família | Estado neste recorte | Próximo aceite |
| --- | --- | --- |
| JavaScript estático/diretório | REA real -> importação/Core/SQLite/restart demonstrados com decisão nativa de revisão | Gate verde, utilidade de análise selecionada e depois dispatch governado |
| Executor REA dentro do loop | Não conectado | Política exata pré-I/O, budget, cancelamento, recibo e resultado tardio |
| Electron/ASAR, .NET e binários | Reconhecidos, não ativados | Selecionar família e dependências/licenças; fixture e isolamento próprios |
| Browser/CDP/runtime capture | Não ativados | Egress, alvo/foco, takeover e permissões específicos |
| MCP genérico/setup | Não absorvidos | Nenhum comando stdio arbitrário ou configuração global implícita |

Essa divisão incorpora uma primeira fronteira útil sem declarar todo o REA
operacional. Nenhum framework externo assume identidade, memória ou síntese.

## Diagnóstico da conversa local

`LocalChatHttpTransport` e `ChatCompletionsInferenceProvider` têm
`phase_observer=None`, desligado por padrão. Quando fornecido, o callback recebe
apenas `event=local_inference_phase`, `phase`, `elapsed_ms` e `timing_mode`.
Fases: `connect_complete`, `request_sent`, `first_byte`, `headers_validated`,
`body_complete`, `peer_closed`, `provider_parse_complete`.

Milissegundos cumulativos 0..120000 por operação. Transporte e provider têm
origens próprias; não subtrair tempos de objetos diferentes como se fossem um
span único. `live` classifica apenas o relógio monotônico, não inferência real.
O callback não recebe texto, headers, URL, modelo, request ID ou tokens.
Na continuidade desta data, a CLI `apps.jarvis_console.local_model_tool_loop_cli`
passou a oferecer `--include-phase-diagnostics`, desligado por padrão. A composição
fornece o observer às duas instâncias e retorna no máximo 28 amostras allowlisted,
com componente `transport`/`provider`; não persiste diagnósticos na memória ou
eventos canônicos. Não há integração no cockpit nem logging global automático.
Não autoriza warm-up ou nova inferência. Ver o
[runbook de continuidade](conversation-gate-reliability-2026-10-20.md).
`first_byte` é primeiro byte HTTP, não primeiro token. Não distingue sozinho
carga fria, prefill e geração; isso exige medições do servidor e prova autorizada.

`body_complete` indica framing completo, não aceitação: EOF do peer continua
obrigatório. Há fences antes/depois do callback; alteração de configuração,
cancelamento, prazo e binding continuam revogando a publicação. Callbacks
best-effort não podem converter falha em texto final. Default-off não adiciona
chamadas ao relógio nem eventos ao fluxo existente.

## Verificação e limites

RED da API de fases: argumento `phase_observer` ausente. GREEN inicial: 54 passed.
Regressão com sockets liberados: 327 passed/19,69s, incluindo 6 provas TCP
content-length/chunked, EOF pendente, cancelamento e bytes extras tardios.
No sandbox restrito, a primeira seleção teve 49 failed/278 passed com erros de
transporte; o mesmo código/testes passou com permissão de loopback, sem ajuste.

RED da projeção: módulo ausente. RED adicional: coverage semântico
`complete+truncated` aceito indevidamente; guarda corrigida. RED da ponte: módulo
ausente. GREEN combinado projeção/ponte/source-review: 257 passed/18,10s.
Os envelopes unitários são sintéticos contract-shaped, não saídas REA observadas.
Core/SQLite/restart são reais; nenhum modelo, conta OAuth ou API paga foi usado.
A observação REA real acima é separada, não 257 execuções do analisador.
Fábricas do pin foram revisadas; usar directory/fail explícitos, não o default auto.

O primeiro gate standard desta rodada terminou com exit 1, 11.689 testes coletados e duas
falhas. A primeira foi a espera `join(20)` em
`test_default_core_policy_final_and_canonical_user_survive_sqlite_restart`
(consulta PT/allow); o worker nativo ainda estava vivo. Esse fluxo não usa o
transporte alterado. A segunda foi `DID NOT RAISE` em
`test_core_identity_grant_or_final_drift_cannot_be_attested[change0]`. O teste
não confirma ter alcançado a adulteração: o piloto admite recusas anteriores ao
guard, inclusive expiração do prazo total de 10 segundos. A inspeção prova essa
possibilidade, não qual branch ocorreu na execução global, nem um bypass.

Repetição integral dos dois arquivos, sem mudar código/testes: **66 passed em
246,14 s**. As falhas não se reproduziram nessa seleção; a causa exata permanece
inconclusiva. Não aumentar prazos, relaxar guardas ou classificá-las como
resolvidas sem evidência. Se repetirem, capturar a stack do worker e os marcos
de entrada/resultado do piloto sem conteúdo. Não houve novo standard aprovado;
o WIP permanece `in_progress`. Os 12 hashes de runtime/testes Python ficaram
inalterados durante a verificação. Não usar o gate anterior ou esta repetição
focada como aceite global das mudanças novas. MB236, conversa útil/memória de
modelo real e qualidade de voz permanecem pendentes. Nenhum saldo interrompido
de piloto foi reutilizado.

## Rollback

Não invocar `apps.jarvis_rea` desativa a ponte, sem apagar memória ou alterar o
Core. Omitir `phase_observer` mantém o comportamento anterior. Não há dependência
central nova, migração de banco, registry paralelo ou configuração global.
Imagem/checkout do experimento são opcionais e ficam fora do código do JARVIS.

## Continuidade de verificacao

As duas fragilidades dos testes descritas acima receberam reproduções
determinísticas e correções test-only na continuidade desta data; 145 testes de
serviço/MCP passaram. Isso não identifica retroativamente a branch histórica.
O standard integral posterior passou: 11591 passed/124 skipped, zero falhas e
errors, 11715 coletados. Os 17 hashes Python e inventario ficaram inalterados.
CLI default-off e memoria/controle scripted passaram; novo piloto Qwen max9
parou na primeira inferencia concluida,24,14s, por recusa do loop antes das
ferramentas. Sem segunda interacao/controle/retry; memoria real nao homologada.
Detalhes atuais no [runbook de continuidade](conversation-gate-reliability-2026-10-20.md).
O servidor REA vivo agora detecta Ghidra 12.1.4 com Java 21 disponível; IDA Free
9.4 e plugin estão instalados, mas o provider IDA está `not_configured`. Nenhum
alvo foi aberto ou analisado. Essa disponibilidade não substitui a prova do fork
pinado acima nem promove análise nativa governada no JARVIS.

## Estudos paralelos

[OpenMausBot](../implementation/openmausbot-assessment-2026-10-20.md) é referência
de produto operacional, eventos, tarefas e takeover. O pedido adicional
[Harness²](../implementation/harness2-assessment-2026-10-20.md) foi analisado no
pin1cfe254e: laboratório de melhoria para o Operator Learning Loop existente,
não motor. Não importar sandbox desativada, rede irrestrita, escolha obrigatória
de candidato ou políticas editáveis. Nenhum desses dois projetos foi
instalado/executado ou promovido nesta rodada.
