# Evolution Lab

## 1. Objetivo

Este documento resume o papel do laboratorio evolutivo do JARVIS como ambiente separado de experimentacao e melhoria controlada.

Ele deriva principalmente da camada evolutiva do Documento-Mestre.

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
- refinamento de especialistas subordinados.

---

## 4. O que nao deve entrar diretamente em producao

- auto-modificacao livre do nucleo;
- mudanca direta de identidade;
- mudanca direta de governanca sem validacao reforcada;
- promocao evolutiva sem benchmark e rollback.

---

## 5. Regra permanente

O laboratorio evolutivo serve ao sistema, mas nao governa o sistema.

---

## 6. Estado atual no repositorio

O repositorio ja possui um primeiro corte operacional do laboratorio evolutivo:

- servico local `evolution-lab`;
- persistencia local de propostas e decisoes;
- comparacao entre baseline e candidata por metricas simples;
- decisao `sandbox-only`, sem promocao automatica;
- referencia explicita de rollback para o baseline avaliado;
- `manual_variants` priorizado como estrategia de evolucao do `v1` apos benchmark dirigido.

Esse corte existe para iniciar `M6` sem antecipar autoevolucao ampla.

---

## 7. Limite atual

O laboratorio atual ainda nao faz:

- promocao automatica;
- alteracao direta do nucleo em producao;
- governanca evolutiva completa;
- expansao ampla alem do conjunto congelado do benchmark do `v1`.
