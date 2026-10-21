# Experimento de replay Hermes e conversa com memória

Data de início: 2026-10-20. Gate standard03 aprovado; campanha real encerrada.
Nenhum aceite macro ou MB236 muda
pela existência deste experimento. A direção é a
[composição seletiva](../architecture/technology-absorption-order.md).

## Hipótese e mudança real

O [último piloto](structured-local-conversation-2026-10-20.md) concluiu uma
comparação de duas fontes, mas não finalizou o segundo turno; controle sem
histórico não executou. Não há causa isolada para a latência nem memória útil
real já aceita. A hipótese desta rodada é que apresentar o histórico como
pares conversacionais, separado do progresso atual, pode ajudar o modelo.
É uma hipótese, não uma correção causal comprovada dos timeouts.

O pacote `apps/jarvis_hermes` reutiliza composição/substituição de contexto e
cópia para replay do Hermes em
`0b8dee00fafe975f10be40172322d0ccfabfa7f6`. Arquivos, símbolos, hashes e adaptações
estão na [proveniência](../../apps/jarvis_hermes/PROVENANCE.md); o aviso MIT está
preservado. Não é uma reimplementação apenas inspirada no projeto.

O loop Hermes completo foi inspecionado e depende de estado de agente,
persistência, compressão, retries/fallbacks e dispatcher próprios. A fatia
extraída é menor: replay de contexto dentro do loop JARVIS, não o loop completo
nem a API de native tool calling. O texto upstream que tratava memória como
autoritativa foi substituído por orientação explícita de dados não confiáveis.
A fence textual não é a fronteira de segurança; validação e permissões nativas
continuam sendo essa fronteira.

`--hermes-context` é um opt-in do host na CLI local. O provider seleciona o mesmo
schema de fase pelo JSON Core original e só então separa o histórico em mensagens
user/assistant; a query atual recebe o progresso como sidecar efêmero de dados.
O sistema original e a totalidade do payload permanecem vinculados pelas fences.
Não há store paralelo, nova seleção de memória, estado entre chamadas ou nova
dependência. Default-off não altera o payload anterior. O Core mantém três
leituras, quatro inferências por turno,120s, governança, citações e síntese final.

## Comparação e limites predefinidos

Baseline: `jarvis_structured`, schema por fase/progresso ativo. Candidata:
`hermes_context`, mesmo schema e mesmos controles, com replay ligado. Cada lado
usa fontes, modelo e prazo iguais. A ordem é fixa: baseline, depois candidata.
Temperatura/seed/output-token defaults, residência, janela e hardware do servidor
não são controlados ou atestados pelo runner. Tempos e consumo devem ser
registrados, sem concluir causalidade ou superioridade por essa única execução.

O corpus público sintético está em `evals/operator_tasks/hermes_comparison.py`,
digest `9024e8fb93c248298500b6a3e58cf489dc4a9396f4d30f7bb415e327cf3dc0a0`:

1. Seed: ler dois relatórios, responder12itens/180ms e usar a preferência
   explicitamente fornecida nessa primeira query.
2. Memória: após restart, usar a preferência anterior e reler revisões13itens/
   170ms. A segunda query e as novas fontes não contêm a preferência esperada.
3. Controle: mesma query/fontes revisadas e snapshot inicial idêntico dos dois
   bancos, mas sem enviar histórico. Declarar preferência indisponível.

A recusa de ferramenta proibida é testada separadamente com modelo scripted,
sem ser contada como conversa útil. Cada turno permitido exige duas fontes,
fatos associados a seus campos/unidades, citações literais e final exata em
restart/export. O corpus pede layout compacto explícito e usa critérios
determinísticos; não é avaliação semântica geral ou holdout secreto.

Cada braço para na primeira falha. O segundo braço é um experimento independente,
não retry do primeiro. Há teto global24tentativas, quatro por turno e três turnos
por braço. Toda tentativa é contabilizada, inclusive falhas; não há warmup,
reparo, retry, OAuth, API paga, download ou reutilização de campanhas anteriores.
`local_model` identifica a composição pretendida com endpoint local, não uma
atestação independente de pesos ou de ausência de forwarding pelo servidor.

## Execução reproduzível

O executor é `evals.operator_tasks.hermes_local_experiment`. Sem `--execute`,
apenas valida lexicalmente a seleção e imprime preflight, com zero inferências
e sem criar diretório de campanha. Use um caminho absoluto novo, nunca um store
de uso cotidiano. Execute a partir da raiz do repositório. Por exemplo, com uma
pasta privada escolhida pelo operador:

```powershell
python -m evals.operator_tasks.hermes_local_experiment --runtime-dir C:/JarvisExperiments/hermes-run-01
python -m evals.operator_tasks.hermes_local_experiment --runtime-dir C:/JarvisExperiments/hermes-run-01 --execute --authorized-local --acknowledge-upstream-egress
```

O default seleciona apenas `qwen3:4b-instruct` no endpoint numérico loopback
`http://127.0.0.1:11434/v1/chat/completions`. Não inicia modelo ou serviço nem
procura credenciais. Loopback pode encaminhar dados para upstream; o executor
exige acknowledgement mesmo para o corpus público. As flags são consentimento
de host local, não autenticação humana ou permissão operacional do Core.

Artefatos da execução: manifest, tentativas e diagnósticos sem conteúdo bruto
do provider, resultados canônicos aceitos/recusas nativas, dois bancos por fase,
hashes de snapshots, orçamento e resumos comparativos. Arquivos de diagnóstico
são atualizados durante a execução e não são ledger imutável nem memória
canônica. Apenas os stores Core existentes alimentam histórico.

## Gate e verificação

O primeiro ajuste de `tools/engineering_gate.py` criou temporários no workspace.
Isso introduziu uma regressão: os testes de runtime privado recusaram corretamente
armazenamento dentro do repositório. O primeiro standard foi interrompido e não
está aprovado. A reprodução isolou `canonical_mission_runtime_refused`; os mesmos
arquivos inalterados de canonical mission e conta ChatGPT passaram fora do
repositório:29testes/25,13s. As guardas de privacidade não foram flexibilizadas.

A correção usa uma raiz UUID nova sob o TEMP do sistema, fora do
repositório; um pai privado existente pode ser escolhido com `--temp-root`.
TEMP/TMP/TMPDIR são propagados somente aos subprocessos, sem modificar ambiente
global ou apagar paths preexistentes. Quick não aloca temporários.
Standard/release mantêm seus checks, recusam PYTEST_ADDOPTS herdado não vazio
para impedir seleção oculta e emitem JUnit em `<run-root>/pytest-results.xml`,
fora do basetemp do pytest.28testes do gate passaram/17,70s, incluindo o teste
canônico original executado pelo caminho de temporários privados do gate.

A primeira bateria de18testes do gate incluiu filho intencionalmente reprovado
cujo XML conserva2casos/1falha, sem mascarar exitcode. Isso não detectou a
regressão de localização; a nova bateria deve exercitar o runtime privado real.
Sockets são uma restrição separada deste sandbox Windows; testes HTTP precisam
de execução autorizada com permissão de rede local. O gate não concede essa
permissão nem relaxa qualquer política do JARVIS.

Provider/replay: RED por opção ausente, seguido de175unitários verdes no primeiro
slice; regressão ampliada de oito arquivos encerrou exit0. Runner/grader:
53testes unitários/E2E verdes antes do executor reproduzível, com ambos os
formatos e recusa proibida. Revisões independentes eliminaram falsos positivos
de label, números fracionários/negativos/trocados e resumos completos vazios.
Os testes usam peer derivado do payload, não pesos reais ou retorno de factory
de produção como oráculo. A bateria ampliada do comparador e executor encerrou
79testes verdes/18,80s, incluindo execução completa dos dois braços pelo
CLI/HTTP/Core/SQLite e interrupção na primeira falha. Não são chamadas ao Qwen.

Verificação integrada pelo root após os merges locais dos agentes:670passed em
149,81s, sem falhas/errors/skips, em15arquivos provider/transporte/CLI/replay/
comparador/executor/gate/HTTP/memória. Inventário/contratos MCP:211passed/48,12s.
XMLs `hermes-integrated-20261020-01.xml` e `hermes-inventory-20261020-01.xml`
retidos nos artefatos privados.37arquivos Python/JSON/TOML/licença/proveniência
congelados por SHA256 antes do standard; snapshot
`hermes-code-freeze-20261020-01.json`, relativo ao primeiro standard interrompido.
A correção foi congelada em `hermes-code-freeze-20261020-02.json` (37arquivos).
O segundo standard concluiu, mas não passou:12027casos,11901passed/2failed/
124skipped/0errors,2115,180s no JUnit. Log `hermes-standard-20261020-02.log`;
JUnit preservado no run-root externo. As duas falhas são
`test_private_research_excluded_without_excluding_documentation` e
`test_mojibake_tools_ignore_ephemeral_test_roots`: o prefixo `.tmp_` do run-root
faz os scanners ignorarem os ancestrais das fixtures, inclusive docs válidos.
O nome temporário foi corrigido para `jarvis-engineering-gate-UUID`. RED
reproduziu ambos os scanners originais; GREEN29testes/23,99s inclui os dois casos
inalterados e a missão canônica através do diretório planejado. Scanner,
exclusões e Core não foram alterados.

Freeze03 preserva os mesmos37arquivos; em relação a freeze02 mudaram somente
`tools/engineering_gate.py` e `tests/unit/test_engineering_gate.py`. O terceiro
standard completo foi aprovado:12028casos,11904passed/124skipped/0failed/
0errors,2052,195s no JUnit, log `hermes-standard-20261020-03.log`.
JUnit: `C:/Users/vtham/AppData/Local/Temp/jarvis-engineering-gate-79926d601d6345a0b2b4a33a37c1f550/pytest-results.xml`.
Conferência posterior confirmou os37hashes e o conjunto de arquivos iguais a
freeze03. Aprovação global de testes não equivale à aceitação de utilidade.

Package-data inclui LICENSE/PROVENANCE para distribuição. Uma tentativa offline
de wheel falhou no TEMP do sandbox; após isolá-lo no workspace, a próxima expôs
ausência de setuptools.build_meta. Nenhuma dependência foi instalada; wheel não
foi validado e este experimento não é uma liberação de distribuição.

## Resultado real e rollback

Campanha real executada após o standard aprovado, em diretório privado novo
`hermes-real-comparison-20261020-01`, usando o executor acima e seu teto24.
Metadados GET imediatamente anteriores,2026-10-21T02:41:35Z, identificaram o
modelo instalado com digest
`0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0` e lista de
residência vazia; zero inferências de aquecimento. Isso é declaração do servidor,
não verificação independente dos pesos.

Resultado do corpus fixado:6tentativas reais,3por configuração, todas com
retorno do provider completed. Ambos os loops Core encerraram completed, com
duas observações/citações atuais, final persistida e readback/export exatos.
Não houve timeout ou erro de transporte nesta campanha. O comparador encerrou
partial: ambos falharam no seed e pararam conforme o protocolo. Não existem
snapshots, fases memory/control ou inferências dessas fases nesta execução.
Auditoria independente read-only confirmou17arquivos sem alteração por SHA256,
uma linha canônica por braço,3eventos model_requested/2tool_observed e nenhuma
operation_dispatched; finais SQLite e sujeitos coincidem. Todos os pedidos
transportaram history_pairs0, como esperado no seed.

| Configuração | Tentativas seed | Observações | Tempo do turno no host | Tokens declarados entrada/saída | Aceite seed |
| --- | ---: | ---: | ---: | ---: | --- |
| jarvis_structured | 3 | 2 | 73,172s | 1533/177 | Reprovado |
| hermes_context | 3 | 2 | 46,281s | 1684/157 | Reprovado |

O tempo inclui setup, Core, persistência, restart/export e avaliação, não só
inferência. Não inclui a clonagem pré-fase. Diferença de tempo nesta ordem fixa,
com residência/cache/defaults não controlados, não demonstra ganho causal.
Custo monetário é desconhecido/null, não zero. Nenhuma chamada de aquecimento,
retry, OAuth ou fallback pago;18tentativas do teto não foram utilizadas.

As três checagens reprovadas em ambos foram compact_analysis_layout,
fresh_numeric_facts e remembered_preference. A revisão humana independente
separa as causas: os fatos12itens/180ms e trace gap restante estão corretos e
sustentados pelas duas citações; fresh_numeric_facts depende do parser de layout
completo e sua reprovação não significa números errados. O renderer nativo
codifica pontuação no anexo JSON, por exemplo `\u003a`; isso não é erro do modelo
e o comparador decodifica o literal JSON antes de verificar o layout.
O baseline afirmou preferência not-available apesar da preferência explícita
na query seed; a candidata omitiu o label. Nenhum seguiu o layout Response label.
Não foram encontrados métricas, fontes extras, ações ou correções reais inventadas
nas análises. O seed nunca seria prova de memória: nele a preferência é explícita.

Há extração factual sintética correta e fechamento real do loop, mas não aceite
da preferência nem prova de memória após restart. A recusa proibida e a campanha
completa com memória/controle continuam comprovadas apenas com peer scripted.
Não reparar/reinterpretar respostas, alterar o grader ou continuar fases após a
falha para transformar este resultado em sucesso. Arquivos de evidência dentro
do diretório privado: comparison.json, inferences.json, os resumos por braço e
seed/canonical-result.json/budget.json; ausência de snapshots.json é esperada.

Decisão: manter a candidata experimental/default-off, sem promoção, claim de
superioridade, alteração macro ou desbloqueio MB236. O reuso é concreto, mas seu
benefício sobre o baseline não foi demonstrado neste caso.

## Próximo recorte orientado pelo resultado

1. Investigar a tensão textual em shared/model_tool_loop.py: instruções nativas
   dizem que query é dado, não instrução, enquanto o produto precisa atender à
   intenção/formato conversacional sem conceder autoridade sobre ferramentas.
   Essa contradição de orientação é observável; sua causalidade sobre este
   resultado não foi isolada. Qualquer correção precisa de testes de preferência
   e de recusa de pedidos que tentem ampliar escopo, sem relaxar o parser.
2. Melhorar a síntese visível pelo próprio Core: nesta fixture o prefácio interno
   tem2637caracteres antes do marcador generativo, para finais de3172/3040chars.
   Analysis curto correto não torna essa resposta bruta uma conversa compacta.
   Separar diagnóstico e resposta útil preservando autoria, qualificações,
   memória e readback canônicos; não contornar a síntese no front-end.
3. Só após nova verificação/aceite seed, executar uma campanha nova e explícita
   de memória após restart com fontes revisadas e controle sem histórico. Não
   aproveitar fases ausentes como prova nem trocar modelo/fixture após ver resultado.

Rollback: omitir `--hermes-context`/usar False. Não apagar stores ou migrar
memória. O pacote e o executor são opcionais; nenhuma promoção é automática.
Após a campanha, quick (encoding/document guardrails/Ruff) aprovado e
diff --check sem erros. Conjunto dos37arquivos e hashes ainda coincide com
freeze03; nenhuma mudança Python/JSON/TOML após o standard aprovado.
Sem commit, push ou merge nesta rodada.
