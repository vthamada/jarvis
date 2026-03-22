# Evolution Lab

## 1. Objetivo

Este documento resume o papel do laboratorio evolutivo do JARVIS como ambiente separado de experimentacao e melhoria controlada.

Ele deriva da camada evolutiva do Documento-Mestre e do baseline operacional do `v1`.

---

## 2. Papel do laboratorio

O laboratorio evolutivo existe para:

- observar desempenho;
- gerar hipoteses de melhoria;
- testar variacoes em sandbox;
- comparar baseline e candidata;
- produzir evidencia antes de qualquer promocao.

---

## 3. O que pode entrar no laboratorio

- melhoria de prompt;
- melhoria de workflow;
- melhoria de roteamento;
- melhoria de avaliacao;
- melhoria de eficiencia;
- refinamento de especialistas subordinados;
- comparacao entre estrategias de continuidade.

---

## 4. O que nao entra em producao diretamente

- auto-modificacao livre do nucleo;
- mudanca direta de identidade;
- mudanca direta de governanca sem validacao reforcada;
- promocao evolutiva sem benchmark e rollback.

---

## 5. Regra permanente

O laboratorio evolutivo serve ao sistema, mas nao governa o sistema.

---

## 6. Estado atual no repositorio

O repositorio ja possui um corte operacional do laboratorio evolutivo:

- servico local `evolution-lab`;
- persistencia local de proposals e decisoes;
- comparacao entre baseline e candidata por metricas simples;
- decisao `sandbox-only`, sem promocao automatica;
- referencia explicita de rollback para o baseline avaliado;
- integracao com sinais do `internal pilot` e da comparacao de paths;
- `manual_variants` priorizado como estrategia inicial do baseline.

---

## 7. Relacao com o pos-v1

No ciclo atual, o laboratorio deve ser usado para:

- avaliar estrategias de continuidade entre missoes;
- comparar variantes sem reabrir o baseline do `v1`;
- transformar sinais reais do piloto em proposals controladas.

Ele nao deve ser usado para:

- justificar salto estrutural sem evidencia;
- promover mudanca automatica;
- virar fonte soberana de decisao sobre o nucleo.
