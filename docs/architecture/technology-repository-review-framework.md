# Technology Repository Review Framework

## 1. Objetivo

Este documento define a camada de analise profunda de repositorio para tecnologias externas
que ja sobreviveram a triagem arquitetural inicial do JARVIS.

Ele nao substitui:

- `docs/architecture/technology-study.md`
- benchmark governado
- decisao por corte

Ele entra depois dessas camadas, quando uma tecnologia deixa de ser apenas curiosidade,
referencia conceitual ou benchmark leve e passa a exigir due diligence tecnica real.

## 2. Quando usar

A revisao de repositorio deve ser aberta quando a tecnologia estiver em pelo menos um destes estados:

- `absorver_depois`
- candidata seria a complemento futuro
- referencia forte para uma camada que o JARVIS provavelmente vai materializar
- potencial de acoplamento alto caso seja absorvida sem inspe??o mais rigorosa

Nao abrir esta revisao para toda tecnologia estudada. Ela deve ser usada apenas onde houver
probabilidade real de reaproveitamento ou risco relevante de decisao errada.

## 3. Pergunta central

A pergunta que esta revisao responde e:

**esta tecnologia continua fazendo sentido para o JARVIS quando saimos das docs e olhamos o repositorio real?**

## 4. Blocos obrigatorios da analise

### 4.1 Encaixe arquitetural

Responder:

- que lacuna concreta do JARVIS ela ataca
- em que camada ela poderia entrar
- o que ela nao pode substituir
- qual seria a menor superficie util de absorcao

### 4.2 Estrutura real do repositorio

Inspecionar:

- organizacao do monorepo ou repo principal
- modulos centrais
- pacotes distribuiveis
- pontos de extensao
- exemplos e demos
- presenca de server, sdk, cli e variantes paralelas

### 4.3 Qualidade de engenharia

Verificar:

- licenca
- linguagem principal
- build system
- testes
- tipagem
- release cadence
- breaking changes ou migration guides
- clareza das dependencias centrais
- presenca de observabilidade ou mecanismos de depuracao

### 4.4 Traducao para o JARVIS

Produzir uma tabela minima com:

- conceito externo
- equivalente ou vizinho no JARVIS
- encaixe possivel
- bloqueio atual
- risco de acoplamento

### 4.5 Decisao disciplinada

A analise deve terminar em apenas uma destas saidas:

- `rejeitar`
- `usar_como_referencia`
- `benchmark_adicional`
- `absorver_depois`
- `abrir_recorte_de_absorcao`

A decisao precisa explicitar:

- ganho esperado
- risco principal
- condicao de reabertura

## 5. Guardrails

- nenhuma analise de repositorio promove tecnologia automaticamente ao nucleo
- docs oficiais nao bastam; repositorio real importa
- hype, stars ou popularidade nao contam como evid?ncia suficiente
- integracao futura so pode acontecer sem romper identidade, memoria canonica,
  governanca final, sintese soberana ou registries centrais
- a revisao deve privilegiar a menor traducao util e reversivel

## 6. Estrutura recomendada do artefato final

Cada revisao profunda deve responder, no minimo:

1. o que a tecnologia e
2. quais fontes oficiais foram lidas
3. como o repositorio esta organizado
4. que sinais de qualidade de engenharia o repositorio mostra
5. o que encaixa no JARVIS
6. o que nao encaixa
7. qual seria o menor ponto de absorcao possivel
8. decisao final e gatilhos de reabertura

## 7. Ordem recomendada atual

Pelo estado atual do JARVIS, a ordem mais defensavel para esse tipo de revisao e:

1. `Mem0`
2. `Mastra`
3. `AutoGPT Platform`, somente se a camada operacional continua do sistema ganhar prioridade real
