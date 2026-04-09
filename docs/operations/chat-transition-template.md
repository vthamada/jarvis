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

---

## 1. Quando abrir novo chat

Abrir um novo chat costuma ser melhor quando:

- um lote inteiro foi concluido e o backlog ficou sem item `ready`;
- vamos repriorizar o nucleo ou abrir um novo lote `MB-xxx`;
- a conversa acumulou historico demais e o risco de inercia ficou alto;
- vamos trocar de modo de trabalho: implementacao, mapeamento, estudo, review
  ou fechamento.

Continuar no mesmo chat ainda pode ser suficiente quando:

- o item atual ainda esta aberto;
- a direcao nao mudou;
- o trabalho continua claramente dentro do mesmo lote.

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

## 4. Checklist de transicao

Antes de abrir o novo chat, conferir:

- `HANDOFF.md` atualizado;
- `execution-backlog.md` refletindo o estado real da fila;
- `v2-adherence-snapshot.md` sincronizado com o baseline;
- `CHANGELOG.md` registrando a rodada encerrada;
- gate apropriado executado;
- worktree em estado conhecido.

---

## 5. Regra pratica

Se houver duvida:

- mesmo lote ainda em execucao: continuar no chat atual;
- lote fechado e nova repriorizacao: abrir novo chat com este template.
