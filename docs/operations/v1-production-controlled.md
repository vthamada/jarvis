# V1 Production Controlled

## 1. Objetivo

Este documento operacionaliza a estratégia de produção controlada do JARVIS `v1` a partir do Documento-Mestre.

Ele deriva principalmente de:

- `documento_mestre_jarvis.md`, capitulo `344. Estratégia de operação do v1 em produção controlada`
- `docs/operations/v1-go-no-go-decision.md`

Seu papel e transformar a política arquitetural em um guia de operação prática para o primeiro uso real do sistema.

---

## 2. Definicao operacional

Produção controlada do `v1` significa:

- uso real em escopo limitado;
- baixa tolerancia a operação sem observabilidade;
- autonomia restrita e graduada;
- possibilidade clara de bloqueio, pausa e rollback;
- monitoramento reforçado desde o primeiro uso real.

Não significa:

- produção ampla;
- automação irrestrita;
- operação silenciosa de alto impacto;
- autoevolucao promovida diretamente em produção.

No `v1`, a operação controlada usa:

- trilha local persistida como observabilidade primaria;
- espelhamento agentic opcional quando configurado;
- checklist executável antes de qualquer ampliacao de escopo.

---

## 3. Escopo permitido

O `v1` pode operar em produção controlada em casos como:

- análise e síntese de informação;
- planejamento e estruturacao de tarefas;
- produção de artefatos textuais;
- continuidade de missão simples;
- uso de ferramentas de baixo risco e reversiveis;
- apoio técnico observável em escopo limitado.

---

## 4. Escopo proibido

O `v1` não deve operar em produção controlada, neste estágio, em:

- ações irreversiveis de alto impacto;
- automações amplas sobre sistemas críticos;
- operações financeiras, jurídicas ou de segurança de alto risco;
- alteracao livre de memória crítica;
- promoção evolutiva em ambiente produtivo;
- operação multiagente ampla sem contencao madura.

---

## 5. Pre-condições para entrada em produção

Antes de liberar o `v1` para produção controlada, confirmar:

- núcleo central funcional no escopo do `v1`;
- memória util mínima funcionando com backend operacional definido;
- governança mínima robusta ativa;
- logs estruturados e rastreamento de fluxo operando;
- ambiente separado de sandbox evolutivo;
- cenarios prioritários já validados;
- política mínima de rollback definida.

---

## 6. Estado atual do baseline

No baseline atual do repositório:

- a trilha central `orchestrator -> memory -> governance -> knowledge -> operational -> observability` esta integrada;
- `PostgreSQL` foi validado por teste de integração e benchmark como backend operacional recomendado do `v1` local;
- `sqlite` permanece apenas como fallback local de desenvolvimento;
- a observabilidade local foi benchmarkada como suficiente para o `v1` controlado;
- o `evolution-lab` continua `sandbox-only`, com `manual_variants` como estratégia priorizada;
- a decisão formal atual e `GO CONDICIONAL` para produção controlada, em escopo reduzido e com monitoramento reforçado.

---

## 7. Checklist de entrada

Checklist mínimo:

- `governança`
  - classificação de risco funcional
  - permissao, condicionamento e bloqueio básicos ativos
- `observabilidade`
  - logs estruturados
  - tracing mínimo
  - registro de decisão
- `operação`
  - fluxos de baixo risco validados
  - falhas sinalizadas corretamente
- `memória`
  - recuperacao util
  - backend operacional validado
  - protecao mínima de memória crítica
- `ambiente`
  - separacao clara entre produção e sandbox
  - comparação evolutiva mantida em regime `sandbox-only`
  - validação executada por scripts operacionais canônicos

---

## 8. Regime de monitoramento

Durante produção controlada, monitorar continuamente:

- sucesso dos fluxos prioritários;
- taxa de erro por fluxo;
- falha por adaptador;
- incidencia de falso bloqueio;
- regressoes após mudancas;
- estados interrompidos;
- laténcia e estabilidade.

---

## 9. Resposta operacional mínima

Toda anomalia relevante deve permitir pelo menos:

- bloquear o fluxo atual;
- reduzir temporariamente a autonomia;
- isolar adaptador ou serviço suspeito;
- suspender mudanca recente;
- reverter para baseline conhecido;
- encaminhar revisão manual.

Scripts operacionais de apoio:

- `python tools/validate_v1.py --profile development|controlled`
- `python tools/go_live_internal_checklist.py --profile development|controlled`

---

## 10. Critérios de ampliacao de uso

Só ampliar o uso do `v1` se houver:

- estabilidade repetida;
- ausencia de falhas graves de governança;
- rastreabilidade suficiente;
- recuperacao confiavel após falhas;
- baixa incidencia de estados quebrados;
- memória util sem poluicao excessiva.

---

## 11. Critérios de contencao

Não ampliar, ou reduzir escopo, se houver:

- falhas recorrentes de governança;
- regressao importante após mudanca;
- memória inconsistente;
- operação sem rastreabilidade;
- comportamento identitario instavel;
- alto volume de intervencao manual corretiva.

---

## 12. Relação com o v2

A produção controlada do `v1` deve gerar evidência para:

- estabilizar o núcleo;
- revelar limites reais do executor;
- qualificar futuras entradas de especialistas;
- orientar prioridades do `v2`.
