# Evolution Lab

## 1. Objetivo

Este documento resume o papel do laboratório evolutivo do JARVIS como ambiente separado de experimentação e melhoria controlada.

Ele deriva principalmente da camada evolutiva do Documento-Mestre.

---

## 2. Papel do laboratório

O laboratório evolutivo existe para:

- observar desempenho;
- gerar hipóteses de melhoria;
- testar variações em sandbox;
- comparar baseline e candidata;
- produzir evidência antes de qualquer promoção.

---

## 3. O que pode entrar no laboratório

- melhoria de prompt;
- melhoria de workflow;
- melhoria de roteamento;
- melhoria de avaliação;
- melhoria de eficiencia;
- refinamento de especialistas subordinados.

---

## 4. O que não deve entrar diretamente em produção

- auto-modificacao livre do núcleo;
- mudanca direta de identidade;
- mudanca direta de governança sem validação reforçada;
- promoção evolutiva sem benchmark e rollback.

---

## 5. Regra permanente

O laboratório evolutivo serve ao sistema, mas não governa o sistema.

---

## 6. Estado atual no repositório

O repositório já possui um primeiro corte operacional do laboratório evolutivo:

- serviço local `evolution-lab`;
- persistencia local de propostas e decisóes;
- comparação entre baseline e candidata por métricas simples;
- decisão `sandbox-only`, sem promoção automatica;
- referencia explícita de rollback para o baseline avaliado;
- `manual_variants` priorizado como estratégia de evolução do `v1` após benchmark dirigido.

Esse corte existe para iniciar `M6` sem antecipar autoevolucao ampla.

---

## 7. Limite atual

O laboratório atual ainda não faz:

- promoção automatica;
- alteracao direta do núcleo em produção;
- governança evolutiva completa;
- expansao ampla alem do conjunto congelado do benchmark do `v1`.
