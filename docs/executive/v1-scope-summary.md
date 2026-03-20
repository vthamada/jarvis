# V1 Scope Summary

## 1. Objetivo

Este documento resume o escopo do `v1` do JARVIS em linguagem curta e acionavel.

---

## 2. O que o v1 precisa provar

O `v1` deve provar que e possivel construir um JARVIS com:

- identidade unificada;
- memoria util;
- nucleo executivo funcional;
- governanca minima robusta;
- operacao limitada, mas real;
- observabilidade suficiente;
- acesso minimo por console;
- base pronta para crescer para `v1.5` e `v2`.

---

## 3. O que entra no v1

Inclui:

- nucleo central minimo funcional;
- 12 mentes nucleares ativas;
- dominios prioritarios do primeiro corte;
- memorias minimas robustas;
- governanca basica;
- operacao de baixo risco;
- validacao e producao controlada;
- console textual minimo sobre o orquestrador atual.

---

## 4. O que nao entra plenamente no v1

Nao entra como foco principal:

- cobertura profunda e uniforme dos 30 dominios;
- especialistas maduros em producao ampla;
- autoevolucao ampla em producao;
- multimodalidade plena;
- operacao de alto risco;
- autonomia extensa em ambientes sensiveis;
- interface web completa;
- interface de voz;
- `LLM adapter` configuravel por provider/modelo.

---

## 5. Estado atual resumido

Hoje o `v1` ja demonstrou internamente:

- baseline integrado entre orquestracao, memoria, governanca, conhecimento, observabilidade e operacao;
- `PostgreSQL` validado como backend operacional recomendado para memoria;
- observabilidade suficiente para o escopo atual do `v1`;
- `manual_variants` priorizado no laboratorio evolutivo, mantendo `sandbox-only`;
- ciclo cognitivo mais unitario, com deliberacao estruturada, continuidade de missao e especialistas internos influenciando o plano;
- console textual minimo para acesso direto ao nucleo sem reabrir a arquitetura.

O que falta para o fechamento disciplinado do `v1` passa a ser hardening operacional final e consolidacao do baseline, nao nova ampliacao arquitetural ampla.

---

## 6. Criterio de sucesso

O `v1` e bem-sucedido se o sistema demonstrar:

- unidade perceptivel;
- continuidade basica;
- utilidade real;
- estabilidade minima;
- governanca suficiente para uso controlado;
- acesso minimo e coerente por interface textual.

---

## Atualizacao de fechamento do v1

O `v1` passa a incluir tambem:

- interface textual minima via `jarvis-console`;
- `baseline snapshot`, `containment drill` e `incident evidence` como artefatos operacionais do baseline;
- validacao verde em `development` e `controlled` para o pacote final do baseline.

Continuam explicitamente fora do `v1`:

- `LLM adapter` configuravel;
- interface web;
- interface de voz;
- `LangGraph` como substrato principal;
- memoria vetorial ou semantica mais profunda.
---

## Decisao de fechamento do v1

O `v1` fica congelado com este escopo final:

- nucleo unificado;
- memoria persistente e continuidade util;
- governanca e observabilidade suficientes para producao controlada;
- operacao segura de baixo risco;
- `jarvis-console` como interface textual minima.

Ficam fora do `v1` por decisao de escopo:

- `LLM adapter` configuravel;
- interface web;
- interface de voz;
- `LangGraph` como caminho principal do runtime;
- memoria semantica profunda;
- ampliacao ampla do ecossistema de especialistas.