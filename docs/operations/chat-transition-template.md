# Chat Transition Template

Este arquivo existe para facilitar a troca de conversa sem perder foco,
prioridade ou contexto operacional do JARVIS.

Uso correto:

- usar quando um lote foi fechado e a proxima rodada vai abrir novo recorte;
- usar quando a conversa atual ficou longa demais e vale resetar contexto;
- usar para retomar o trabalho em um novo chat sem reconstruir a direcao na mao.

Nao usar como substituto de:

- `HANDOFF.md`, que continua sendo a retomada macro/tatico-operacional;
- `docs/implementation/execution-backlog.md`, que continua sendo a fila micro
  soberana;
- `docs/implementation/v2-adherence-snapshot.md`, que continua sendo a leitura
  de baseline e aderencia.

Tambem nao usar para carregar logs extensos, exploracao descartavel ou historico
bruto de varias rodadas. O objetivo aqui e preservar estado util, nao mover
ruido entre conversas.

---

## 1. Quando abrir novo chat

Abrir um novo chat costuma ser melhor quando:

- um lote inteiro foi concluido e o backlog ficou sem item `ready`;
- vamos repriorizar o nucleo ou abrir um novo lote `MB-xxx`;
- a conversa acumulou historico demais e o risco de inercia ficou alto;
- vamos trocar de modo de trabalho: implementacao, mapeamento, estudo, review
  ou fechamento.

Antes de abrir novo chat, considerar se basta compactar o estado atual:

- mesmo lote, mesma direcao e muito ruido intermediario: preferir resumir e
  continuar;
- lote fechado, repriorizacao, troca de modo ou contexto poluido: preferir abrir
  novo chat.

Compactacao automatica isolada nao e motivo suficiente para trocar de chat.

- primeira compactacao, mesmo lote e mesma direcao: continuar no mesmo chat;
- compactacao seguida de mudanca de lote, modo ou prioridade: abrir novo chat;
- duas compactacoes dentro do mesmo lote: preparar a troca no proximo marco
  natural;
- se a janela compactada volta rapido para zona alta de uso ou o agente comeca
  a revisitar decisoes ja fechadas, considerar abrir novo chat mesmo sem fechar
  o lote.

Faixas praticas de contexto:

- ate cerca de `50%`: normalmente seguir;
- entre `50%` e `65%`: atencao ao ruido, mas sem pressa para trocar;
- entre `65%` e `75%`: planejar troca no proximo checkpoint se a conversa nao
  estiver ficando mais clara;
- acima de `75%`: forte candidato a compactacao ou novo chat, a menos que o item
  atual esteja claramente em reta final.

Continuar no mesmo chat ainda pode ser suficiente quando:

- o item atual ainda esta aberto;
- a direcao nao mudou;
- o trabalho continua claramente dentro do mesmo lote.

Politica anti-fragmentacao:

- nao abrir novo chat por tamanho bruto da conversa apenas;
- preferir um chat por lote coerente, nao um chat por item pequeno;
- abrir por fronteira de trabalho, nao por ansiedade de contexto.

---

## 2. Prompt curto

Usar quando a transicao e simples e o estado do repositorio ja esta bem
sincronizado nos docs vivos.

```text
Quero continuar o desenvolvimento do JARVIS a partir do estado atual do repositorio.

Leia primeiro:
- HANDOFF.md
- docs/implementation/execution-backlog.md
- docs/implementation/v2-adherence-snapshot.md

Estado minimo:
- branch atual
- ultimo commit relevante
- `git status` resumido
- ultimo gate executado
- item `MB-xxx` mais recente e proximo candidato

Objetivo:
- mapear o proximo passo correto;
- propor o proximo lote do backlog se nao houver item `ready`;
- implementar o lote inteiro se ele estiver suficientemente claro;
- sincronizar os docs vivos sempre que o estado real mudar;
- rodar o gate adequado antes de fechar a rodada.

Regras:
- seguir AGENTS.md e a Constituicao de Engenharia;
- preservar a soberania do nucleo;
- nao reativar frentes `deferred` por inercia;
- nao tocar `.claude/`;
- preferir aprofundar o nucleo antes de abrir nova frente.
```

---

## 3. Prompt completo

Usar quando um lote acabou de ser fechado ou quando a proxima rodada exige
repriorizacao explicita.

```text
Quero continuar o desenvolvimento do JARVIS a partir do estado atual do repositorio.

Contexto:
- o lote mais recente foi concluido;
- preciso retomar o trabalho sem perder o foco correto do sistema;
- se o backlog estiver sem item `ready`, o proximo passo e definir o lote seguinte do nucleo;
- frentes `deferred` nao devem ser reativadas por inercia;
- mantenha a soberania do nucleo, sem introduzir dependencia central nova e sem tocar `.claude/`.

Leia primeiro:
- HANDOFF.md
- docs/implementation/execution-backlog.md
- docs/implementation/v2-adherence-snapshot.md
- docs/architecture/technology-absorption-order.md
- e os arquivos centrais do runtime que forem necessarios

Estado operacional minimo a reconstruir:
- branch atual;
- ultimo commit relevante;
- `git status` resumido;
- ultimo gate executado;
- item `MB-xxx` encerrado;
- proximo item `ready` ou razao objetiva para nao haver um.

O que eu quero que voce faca:
1. reconstruir o estado atual do projeto a partir dos docs vivos e do codigo relevante;
2. dizer qual e o proximo passo mais correto;
3. se nao houver item `ready`, propor o proximo lote `MB-xxx+` com prioridade, dependencias, criterio de aceite, impacto esperado no baseline e modo de raciocinio recomendado por item;
4. se o lote estiver suficientemente claro e couber numa rodada disciplinada, implementar o lote inteiro;
5. sincronizar `HANDOFF.md`, `docs/implementation/execution-backlog.md`, `docs/implementation/v2-adherence-snapshot.md` e `CHANGELOG.md` sempre que o estado real mudar;
6. executar o gate adequado antes de tratar a rodada como fechada.

Regras:
- seguir AGENTS.md e a Constituicao de Engenharia;
- preferir mudancas pequenas, reversiveis e auditaveis;
- nao bypassar governanca, memoria canonica ou sintese final;
- tratar contratos compartilhados e eventos observaveis como interfaces estaveis;
- runtime e interfaces tecnicas novas em ingles;
- documentacao humana pode permanecer em portugues;
- se houver duvida entre abrir nova frente e aprofundar o nucleo, priorize aprofundar o nucleo.
```

---

## 4. Modos de raciocinio

Regra pratica:

- `low`: sincronizacao documental, lint, wiring simples, leitura dirigida,
  ajustes pequenos e validacao pontual, sem alterar comportamento relevante do
  runtime;
- `medium`: implementacao local, reversivel e de baixo raio de impacto,
  refactor contido, testes direcionados e integracao disciplinada quando o
  contrato ja estiver claro;
- `high`: repriorizacao, arquitetura, bugs ambiguos, seguranca, migracoes,
  tradeoffs, definicao de novo lote e qualquer implementacao relevante em
  runtime, memoria, governanca, observabilidade, contratos compartilhados ou
  baseline;
- `xhigh` ou equivalente: usar so em problemas realmente densos, caros e com
  justificativa clara.

Se houver duvida:

- planejamento e mapeamento: comecar em `high`;
- implementacao do nucleo: comecar em `high`;
- implementacao local e claramente delimitada: comecar em `medium`;
- rodada simples de manutencao: comecar em `low`.

---

## 5. Checklist de transicao

Antes de abrir o novo chat, conferir:

- `HANDOFF.md` atualizado;
- `execution-backlog.md` refletindo o estado real da fila;
- `v2-adherence-snapshot.md` sincronizado com o baseline;
- `CHANGELOG.md` registrando a rodada encerrada;
- gate apropriado executado;
- worktree em estado conhecido;
- branch e ultimo commit anotados;
- quantidade de compactacoes recentes entendida;
- percentual atual de contexto interpretado junto com o nivel de ruido;
- se a conversa atual ainda cabe em compactacao, decidir isso antes de abrir
  novo chat.

---

## 6. Regra pratica

Se houver duvida:

- mesmo lote ainda em execucao: continuar no chat atual;
- mesmo lote, mas muito ruido intermediario: resumir/compactar antes de trocar;
- primeira compactacao sem mudanca de direcao: continuar;
- compactacao recorrente e proxima rodada mais estrategica: trocar no proximo
  checkpoint;
- lote fechado e nova repriorizacao: abrir novo chat com este template.

Arvore curta de decisao:

1. O lote atual ainda esta aberto e a direcao nao mudou?
   - sim: continuar no mesmo chat, salvo ruido excessivo;
2. O problema e ruido, nao troca de frente?
   - sim: compactar ou resumir antes de trocar;
3. O lote acabou, a prioridade mudou ou houve mais de uma compactacao relevante?
   - sim: abrir novo chat.
