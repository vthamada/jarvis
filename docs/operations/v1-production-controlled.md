# V1 Production Controlled

## 1. Objetivo

Este documento operacionaliza a estratégia de **produção controlada do JARVIS v1** a partir do Documento-Mestre.

Ele deriva principalmente de:

- `documento_mestre_jarvis.md`, capítulo `344. Estratégia de operação do v1 em produção controlada`

Seu papel é transformar a política arquitetural em um guia de operação prática para o primeiro uso real do sistema.

---

## 2. Definição operacional

Produção controlada do `v1` significa:

- uso real em escopo limitado;
- baixa tolerância a operação sem observabilidade;
- autonomia restrita e graduada;
- possibilidade clara de bloqueio, pausa e rollback;
- monitoramento reforçado desde o primeiro uso real.

Não significa:

- produção ampla;
- automação irrestrita;
- operação silenciosa de alto impacto;
- autoevolução promovida diretamente em produção.

---

## 3. Escopo permitido

O `v1` pode operar em produção controlada em casos como:

- análise e síntese de informação;
- planejamento e estruturação de tarefas;
- produção de artefatos textuais;
- continuidade de missão simples;
- uso de ferramentas de baixo risco e reversíveis;
- apoio técnico observável em escopo limitado.

---

## 4. Escopo proibido

O `v1` não deve operar em produção controlada, neste estágio, em:

- ações irreversíveis de alto impacto;
- automações amplas sobre sistemas críticos;
- operações financeiras, jurídicas ou de segurança de alto risco;
- alteração livre de memória crítica;
- promoção evolutiva em ambiente produtivo;
- operação multiagente ampla sem contenção madura.

---

## 5. Pré-condições para entrada em produção

Antes de liberar o `v1` para produção controlada, confirmar:

- núcleo central funcional no escopo do `v1`;
- memória útil mínima funcionando;
- governança mínima robusta ativa;
- logs estruturados e rastreamento de fluxo operando;
- ambiente separado de sandbox evolutivo;
- cenários prioritários já validados;
- política mínima de rollback definida.

---

## 6. Checklist de entrada

Checklist mínimo:

- `governança`
  - classificação de risco funcional
  - permissão e bloqueio básicos ativos
- `observabilidade`
  - logs estruturados
  - tracing mínimo
  - registro de decisão
- `operação`
  - fluxos de baixo risco validados
  - falhas sinalizadas corretamente
- `memória`
  - recuperação útil
  - proteção mínima de memória crítica
- `ambiente`
  - separação clara entre produção e sandbox

---

## 7. Regime de monitoramento

Durante produção controlada, monitorar continuamente:

- sucesso dos fluxos prioritários;
- taxa de erro por fluxo;
- falha por adaptador;
- incidência de falso bloqueio;
- regressões após mudanças;
- estados interrompidos;
- latência e estabilidade.

---

## 8. Resposta operacional mínima

Toda anomalia relevante deve permitir pelo menos:

- bloquear o fluxo atual;
- reduzir temporariamente a autonomia;
- isolar adaptador ou serviço suspeito;
- suspender mudança recente;
- reverter para baseline conhecido;
- encaminhar revisão manual.

---

## 9. Critérios de ampliação de uso

Só ampliar o uso do `v1` se houver:

- estabilidade repetida;
- ausência de falhas graves de governança;
- rastreabilidade suficiente;
- recuperação confiável após falhas;
- baixa incidência de estados quebrados;
- memória útil sem poluição excessiva.

---

## 10. Critérios de contenção

Não ampliar, ou reduzir escopo, se houver:

- falhas recorrentes de governança;
- regressão importante após mudança;
- memória inconsistente;
- operação sem rastreabilidade;
- comportamento identitário instável;
- alto volume de intervenção manual corretiva.

---

## 11. Relação com o v2

A produção controlada do `v1` deve gerar evidência para:

- estabilizar o núcleo;
- revelar limites reais do executor;
- qualificar futuras entradas de especialistas;
- orientar prioridades do `v2`.
