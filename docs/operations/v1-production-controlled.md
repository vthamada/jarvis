# V1 Production Controlled

## 1. Objetivo

Este documento operacionaliza a estrategia de producao controlada do JARVIS `v1` a partir do Documento-Mestre.

Ele deriva principalmente de:

- `documento_mestre_jarvis.md`, capitulo `344. Estrategia de operacao do v1 em producao controlada`
- `docs/operations/v1-go-no-go-decision.md`

Seu papel e transformar a politica arquitetural em um guia de operacao pratica para o primeiro uso real do sistema.

---

## 2. Definicao operacional

Producao controlada do `v1` significa:

- uso real em escopo limitado;
- baixa tolerancia a operacao sem observabilidade;
- autonomia restrita e graduada;
- possibilidade clara de bloqueio, pausa e rollback;
- monitoramento reforcado desde o primeiro uso real.

Nao significa:

- producao ampla;
- automacao irrestrita;
- operacao silenciosa de alto impacto;
- autoevolucao promovida diretamente em producao.

No `v1`, a operacao controlada usa:

- trilha local persistida como observabilidade primaria;
- espelhamento agentic opcional quando configurado;
- checklist executavel antes de qualquer ampliacao de escopo.

---

## 3. Escopo permitido

O `v1` pode operar em producao controlada em casos como:

- analise e sintese de informacao;
- planejamento e estruturacao de tarefas;
- producao de artefatos textuais;
- continuidade de missao simples;
- uso de ferramentas de baixo risco e reversiveis;
- apoio tecnico observavel em escopo limitado.

---

## 4. Escopo proibido

O `v1` nao deve operar em producao controlada, neste estagio, em:

- acoes irreversiveis de alto impacto;
- automacoes amplas sobre sistemas criticos;
- operacoes financeiras, juridicas ou de seguranca de alto risco;
- alteracao livre de memoria critica;
- promocao evolutiva em ambiente produtivo;
- operacao multiagente ampla sem contencao madura.

---

## 5. Pre-condicoes para entrada em producao

Antes de liberar o `v1` para producao controlada, confirmar:

- nucleo central funcional no escopo do `v1`;
- memoria util minima funcionando com backend operacional definido;
- governanca minima robusta ativa;
- logs estruturados e rastreamento de fluxo operando;
- ambiente separado de sandbox evolutivo;
- cenarios prioritarios ja validados;
- politica minima de rollback definida.

---

## 6. Estado atual do baseline

No baseline atual do repositorio:

- a trilha central `orchestrator -> memory -> governance -> knowledge -> operational -> observability` esta integrada;
- `PostgreSQL` foi validado por teste de integracao e benchmark como backend operacional recomendado do `v1` local;
- `sqlite` permanece apenas como fallback local de desenvolvimento;
- a observabilidade local foi benchmarkada como suficiente para o `v1` controlado;
- o `evolution-lab` continua `sandbox-only`, com `manual_variants` como estrategia priorizada;
- a decisao formal atual e `GO CONDICIONAL` para producao controlada, em escopo reduzido e com monitoramento reforcado.

---

## 7. Checklist de entrada

Checklist minimo:

- `governanca`
  - classificacao de risco funcional
  - permissao, condicionamento e bloqueio basicos ativos
- `observabilidade`
  - logs estruturados
  - tracing minimo
  - registro de decisao
- `operacao`
  - fluxos de baixo risco validados
  - falhas sinalizadas corretamente
- `memoria`
  - recuperacao util
  - backend operacional validado
  - protecao minima de memoria critica
- `ambiente`
  - separacao clara entre producao e sandbox
  - comparacao evolutiva mantida em regime `sandbox-only`
  - validacao executada por scripts operacionais canonicos

---

## 8. Regime de monitoramento

Durante producao controlada, monitorar continuamente:

- sucesso dos fluxos prioritarios;
- taxa de erro por fluxo;
- falha por adaptador;
- incidencia de falso bloqueio;
- regressoes apos mudancas;
- estados interrompidos;
- latencia e estabilidade.

---

## 9. Resposta operacional minima

Toda anomalia relevante deve permitir pelo menos:

- bloquear o fluxo atual;
- reduzir temporariamente a autonomia;
- isolar adaptador ou servico suspeito;
- suspender mudanca recente;
- reverter para baseline conhecido;
- encaminhar revisao manual.

Scripts operacionais de apoio:

- `python tools/validate_v1.py --profile development|controlled`
- `python tools/go_live_internal_checklist.py --profile development|controlled`

---

## 10. Criterios de ampliacao de uso

So ampliar o uso do `v1` se houver:

- estabilidade repetida;
- ausencia de falhas graves de governanca;
- rastreabilidade suficiente;
- recuperacao confiavel apos falhas;
- baixa incidencia de estados quebrados;
- memoria util sem poluicao excessiva.

---

## 11. Criterios de contencao

Nao ampliar, ou reduzir escopo, se houver:

- falhas recorrentes de governanca;
- regressao importante apos mudanca;
- memoria inconsistente;
- operacao sem rastreabilidade;
- comportamento identitario instavel;
- alto volume de intervencao manual corretiva.

---

## 12. Relacao com o v2

A producao controlada do `v1` deve gerar evidencia para:

- estabilizar o nucleo;
- revelar limites reais do executor;
- qualificar futuras entradas de especialistas;
- orientar prioridades do `v2`.
