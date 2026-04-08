# Hermes Agent Repository Review

## 1. Objetivo

Este documento faz a revisao profunda do `Hermes Agent` como tecnologia externa
que ja saiu do nivel de curiosidade e passou a merecer leitura mais rigorosa.

O foco aqui nao e adotar o Hermes.
O foco e responder:

**o que o Hermes realmente tem de forte, o que disso conversa com o JARVIS, e
onde esta o limite seguro de traducao.**

---

## 2. Fontes oficiais lidas

Fontes principais desta revisao:

- README oficial:
  `https://raw.githubusercontent.com/NousResearch/hermes-agent/main/README.md`
- release `v0.7.0`:
  `https://raw.githubusercontent.com/NousResearch/hermes-agent/main/RELEASE_v0.7.0.md`
- features overview:
  `https://hermes-agent.nousresearch.com/docs/user-guide/features/overview`
- tools:
  `https://hermes-agent.nousresearch.com/docs/user-guide/features/tools/`
- skills:
  `https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/`
- memory:
  `https://hermes-agent.nousresearch.com/docs/user-guide/features/memory/`
- memory providers:
  `https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers/`
- checkpoints:
  `https://hermes-agent.nousresearch.com/docs/user-guide/features/checkpoints/`
- security:
  `https://hermes-agent.nousresearch.com/docs/user-guide/security/`
- delegation:
  `https://hermes-agent.nousresearch.com/docs/guides/delegation-patterns/`
- architecture:
  `https://hermes-agent.nousresearch.com/docs/developer-guide/architecture/`

---

## 3. O que o Hermes Agent e

Pelas fontes oficiais, o Hermes e um agente operacional persistente com:

- CLI propria;
- gateway multicanal;
- tools e toolsets amplos;
- skills instalaveis e criadas pelo proprio agente;
- memoria persistente e providers plugaveis;
- subagentes com contexto isolado;
- cron scheduler;
- varios backends de terminal;
- checkpoints e rollback de arquivo;
- fluxo de pesquisa e trajetorias para treino/evals.

Leitura correta:

- o Hermes e mais uma **plataforma operacional de agente** do que um nucleo
  cognitivo soberano;
- o "self-improving" dele e real, mas centrado em `skills`, `memory`, `session
  recall` e `trajectory collection`, nao em autoevolucao profunda do nucleo.

---

## 4. O que a arquitetura oficial mostra

Pela pagina de arquitetura e pelo README, o Hermes se organiza em torno de
blocos bem definidos:

- loop principal do agente;
- builder de prompt/contexto;
- ferramentas e toolsets;
- estado de sessao e persistencia;
- skills e hub/marketplace;
- gateway de plataformas;
- subagentes;
- terminal backends;
- memoria e providers externos;
- checkpoints e seguranca operacional.

Isso importa porque mostra um projeto grande o bastante para ser levado a serio:

- nao e um wrapper fino sobre API de modelo;
- existe desenho de produto e operacao;
- existe separacao entre runtime, memory, tools, skills e channels.

Ao mesmo tempo, isso aumenta a cautela:

- a superficie de produto e grande;
- o risco de importar mais stack do que o necessario tambem e grande.

---

## 5. Sinais de engenharia positivos

Os sinais mais fortes encontrados nas fontes oficiais foram:

- foco claro em persistencia cross-session;
- skills com lifecycle explicito, incluindo criacao e melhoria durante o uso;
- separacao entre memoria interna simples e memory providers externos;
- subagentes com contexto e terminal isolados;
- checkpoints/rollback antes de mutacoes de arquivo;
- docs de seguranca relativamente concretas, cobrindo aprovacoes, isolamento e
  scans;
- suporte a varios backends de terminal e operacao remota;
- trajetorias para pesquisa, treinamento e avaliacao.

Leitura pratica:

- o Hermes parece um projeto serio de runtime operacional;
- ele nao depende apenas de "hype" ou claims vagos de autonomia;
- varias capacidades importantes ja aparecem como produto, nao apenas como
  roadmap.

---

## 6. Sinais de cautela

Os pontos de cautela sao estes:

- a plataforma puxa naturalmente para seu proprio modo de operar;
- memoria, skills e channels vivem dentro de uma gramatica propria;
- o valor do Hermes esta muito ligado ao runtime operacional inteiro, nao a um
  pacote pequeno e isolado;
- o "self-improving" dele pode ser facilmente superestimado se lido como
  autoevolucao cognitiva do nucleo;
- a prioridade do projeto externo esta mais em agent productization do que em
  ontologia cognitiva soberana.

Leitura para o JARVIS:

- importar o Hermes inteiro seria um erro de direcao;
- traduzir partes dele como padroes operacionais pode gerar bastante valor.

---

## 7. Onde ele conversa melhor com o JARVIS

Os melhores pontos de conversa hoje sao:

- [memory_registry.py](../../shared/memory_registry.py)
- [mind_registry.py](../../shared/mind_registry.py)
- [domain_registry.py](../../shared/domain_registry.py)
- [service.py](../../services/memory-service/src/memory_service/service.py)
- [service.py](../../services/orchestrator-service/src/orchestrator_service/service.py)
- [service.py](../../evolution/evolution-lab/src/evolution_lab/service.py)

Principalmente nestes temas:

- memoria procedural e skills reutilizaveis;
- compressao de contexto e recall cross-session;
- subagentes isolados para pesquisa e execucao paralela;
- scheduled automation e runtime operacional persistente;
- terminal backends isolados;
- checkpoint/rollback em mutacoes operacionais.

---

## 8. O que nao deve entrar do Hermes no JARVIS

Nao deve entrar como substituicao:

- da ontologia de `dominios`, `mentes` e `memorias`;
- da governanca soberana;
- da sintese final do nucleo;
- do `memory_registry` como autoridade canonica;
- do runtime do `orchestrator-service` como cerebro do sistema.

Tambem nao deve entrar como confusao conceitual:

- `self-improving` operacional do Hermes nao equivale a autoevolucao governada
  do JARVIS;
- skill creation nao substitui evolucao cognitiva;
- memory provider plugavel nao substitui memoria soberana estratificada.

---

## 9. Tabela de traducao para o JARVIS

| Conceito no Hermes | Vizinho no JARVIS | Encaixe possivel | Bloqueio atual | Risco |
| --- | --- | --- | --- | --- |
| Skills instalaveis e editaveis | memoria procedural + tools + especialistas | artefatos proceduralizados de know-how | falta lifecycle formal de skills no nucleo | medio |
| FTS5 session search | recall cross-session e recovery soberano | busca em historico e memoria de sessoes | retrieval atual ainda mais centrado em classes e traces | medio |
| Memory providers externos | adaptadores futuros de memoria | complemento tardio por adaptador | risco de stack externa mandar no core | alto |
| Subagentes isolados | specialists subordinados + tarefas paralelas | parallel work e pesquisa fora da janela principal | ainda falta politica mais formal de delegation no nucleo | medio |
| Gateway multicanal | futuras superficies operacionais | camada futura de canais | nao e prioridade macro agora | medio-alto |
| Checkpoints/rollback | safety operacional e continuidade | mutacoes mais reversiveis em workflows e file ops | runtime atual ainda nao materializa isso como capability geral | medio |
| Cron scheduler | automacoes governadas | execucoes recorrentes por workflow | maturidade de tasks assincronas ainda insuficiente | medio |
| Trajectory collection | evolution-lab e pilot artifacts | dataset de melhoria e evals | baseline ainda mais focado em traces locais do proprio sistema | baixo-medio |

---

## 10. Leitura tecnica consolidada

Minha leitura tecnica e esta:

- o Hermes e uma referencia forte de **runtime operacional persistente**;
- ele e especialmente forte em `skills`, memoria curta persistente, session
  recall, subagentes e product surface;
- ele nao parece ser o melhor benchmark para arquitetura cognitiva profunda;
- ele e melhor como referencia de **operacao, continuity tooling e procedural
  learning** do que como referencia do cerebro do sistema.

Para o JARVIS, os ganhos mais defensaveis viriam de:

- lifecycle de skills;
- compressao de contexto mais disciplinada;
- busca cross-session;
- checkpoint/rollback;
- subagentes mais isolados;
- scheduled automations futuras.

---

## 11. Decisao desta revisao

**Decisao:** `usar_como_referencia`

Justificativa:

- o Hermes tem valor tecnico real;
- esse valor esta em padroes de runtime operacional e memoria procedural;
- o risco de absorcao ampla e alto demais para o momento do JARVIS;
- o ganho vem de traduzir padroes, nao de importar plataforma.

---

## 12. Menor ponto de absorcao plausivel

Se um dia houver recorte de absorcao inspirado no Hermes, o menor ponto
plausivel seria:

- um lifecycle de `skills` ou artefatos procedurais acima do `memory-service`;
- session search mais forte sobre traces e memoria canonicamente classificadas;
- checkpoint/rollback para mutacoes de arquivo e workflow de maior risco;
- subagentes bem delimitados para pesquisa/coding task paralela;
- scheduled workflows governados, mas ainda `through_core_only`.

---

## 13. Gatilhos de reabertura

Reabrir o Hermes como candidato mais forte somente se pelo menos um destes
sinais aparecer com evidencia local:

- o JARVIS precisar materializar memoria procedural reutilizavel como artefato
  do runtime, e nao apenas como classe de memoria;
- session recall e context compaction ficarem estruturalmente insuficientes no
  baseline atual;
- a camada de tarefas assincronas e agendadas ganhar prioridade macro real;
- o projeto abrir de forma explicita uma camada de gateway multicanal.

---

## 14. Conclusao

O Hermes reforca uma leitura importante para o JARVIS:

- existe muito valor no ecossistema atual;
- esse valor nao esta em terceirizar o cerebro;
- ele esta em roubar com criterio o que ha de melhor em runtime operacional,
  memoria procedural, recall e tooling de continuidade.

Em resumo:

- o Hermes e bom demais para ser ignorado;
- e arriscado demais para ser absorvido inteiro;
- portanto, deve ficar como referencia forte, nao como dependencia central.
