# Go-Live Readiness

## 1. Objetivo

Este documento define o regime minimo de **readiness e go-live** do JARVIS `v1` em producao controlada.

Ele deriva principalmente de:

- `documento_mestre_jarvis.md`, capitulo `346. Plano de readiness e go-live do v1`
- `docs/operations/v1-production-controlled.md`
- `docs/operations/v1-go-no-go-decision.md`

Seu papel e transformar a prontidao do `v1` em checklist operacional claro.

---

## 2. Principio geral

O `go-live` do `v1` so deve ocorrer quando houver:

- capacidade funcional minima;
- governanca minima ativa;
- observabilidade suficiente;
- contencao e rollback claros;
- escopo real de uso explicitamente limitado.

---

## 3. Checklist minimo de readiness

Antes de liberar o `v1`, confirmar:

- ambiente operacional identificado;
- configuracao minima reproduzivel;
- nucleo central funcional no escopo pretendido;
- memoria util basica operando;
- governanca minima robusta ativa;
- observabilidade minima ativa;
- rollback operacional definido;
- cenarios prioritarios aprovados;
- sandbox evolutivo separado e sem promocao automatica.

Checklist executavel associado:

- `python tools/validate_v1.py --profile development`
- `python tools/go_live_internal_checklist.py --profile development`
- repetir ambos no perfil `controlled` quando `DATABASE_URL` estiver ativo.

Os scripts executaveis agora fazem preflight explicito do ambiente e devem ser tratados como gate formal de `go/no-go`. No perfil `controlled`, eles falham cedo quando:

- `ruff` nao esta instalado no ambiente oficial;
- `DATABASE_URL` nao foi definida;
- o PostgreSQL nao responde;
- as credenciais de `DATABASE_URL` estao incorretas.

---

## 4. Estado atual do baseline

Leitura objetiva do estado atual:

- `nucleo central funcional`: atendido;
- `memoria util basica`: atendido, com `PostgreSQL` validado como backend operacional recomendado e `sqlite` mantido como fallback local;
- `governanca minima robusta`: atendido no escopo atual do `v1`;
- `observabilidade minima`: atendido, com benchmark favoravel para o `v1`;
- `sandbox evolutivo separado`: atendido, mantendo `sandbox-only` e sem promocao automatica;
- `configuracao minima reproduzivel`: atendido para baseline local;
- `readiness documental final`: atendido;
- `decisao formal de go/no-go`: atendido, com `GO CONDICIONAL` registrado em `2026-03-19`.

---

## 5. Criterios de go

So autorizar `go-live` se:

- fluxos prioritarios estiverem estaveis;
- bloqueios e permissoes estiverem funcionando;
- logs e tracing estiverem ativos;
- falhas residuais conhecidas estiverem documentadas;
- escopo de uso estiver claramente delimitado.

---

## 6. Criterios de no-go

Negar `go-live` se houver:

- falha recorrente de governanca;
- comportamento central imprevisivel;
- memoria inconsistente;
- ausencia de rollback claro;
- observabilidade insuficiente;
- estados quebrados frequentes.

---

## 7. Smoke checks de lancamento

Executar antes do `go-live`:

- entrada e sintese basicas;
- recuperacao minima de memoria util;
- bloqueio de acao indevida;
- execucao simples de baixo risco;
- registro de logs e traces;
- simulacao de falha local com recuperacao controlada;
- comparacao sandbox entre baseline e candidata sem promocao.

Execucao recomendada:

```powershell
docker compose -f infra/local-postgres.compose.yml up -d
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5433/jarvis"
python tools/validate_v1.py --profile controlled
python tools/go_live_internal_checklist.py --profile controlled
```

---

## 8. Pendencias praticas antes do go-live

Antes do primeiro uso real, ainda faltam:

- congelar o escopo operacional inicial do primeiro uso real;
- registrar a janela de observacao do primeiro rollout controlado;
- definir quem acompanha e interrompe o fluxo em caso de anomalia.

---

## 9. Regime de lancamento inicial

O primeiro `go-live` deve seguir:

- escopo reduzido;
- janela de observacao conhecida;
- monitoramento reforcado;
- facilidade de reversao;
- registro explicito das primeiras ocorrencias.

---

## 10. Resultado esperado do go-live

O `go-live` do `v1` nao deve provar maturidade total.

Ele deve provar:

- utilidade controlada;
- estabilidade minima;
- governanca funcional;
- rastreabilidade suficiente;
- capacidade de conter e corrigir falhas.

---

## 11. Relacao com proximos passos

Apos o `go-live`, o foco deve ir para:

- observacao do uso real;
- correcao de falhas estruturais;
- ajuste de escopo operacional;
- geracao de evidencia para expansao do `v1` e preparacao do `v2`.
