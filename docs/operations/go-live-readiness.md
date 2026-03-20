# Go-Live Readiness

## 1. Objetivo

Este documento define o regime mínimo de **readiness e go-live** do JARVIS `v1` em produção controlada.

Ele deriva principalmente de:

- `documento_mestre_jarvis.md`, capitulo `346. Plano de readiness e go-live do v1`
- `docs/operations/v1-production-controlled.md`
- `docs/operations/v1-go-no-go-decision.md`

Seu papel e transformar a prontidao do `v1` em checklist operacional claro.

---

## 2. Principio geral

O `go-live` do `v1` só deve ocorrer quando houver:

- capacidade funcional mínima;
- governança mínima ativa;
- observabilidade suficiente;
- contencao e rollback claros;
- escopo real de uso explicitamente limitado.

---

## 3. Checklist mínimo de readiness

Antes de liberar o `v1`, confirmar:

- ambiente operacional identificado;
- configuração mínima reproduzivel;
- núcleo central funcional no escopo pretendido;
- memória util básica operando;
- governança mínima robusta ativa;
- observabilidade mínima ativa;
- rollback operacional definido;
- cenarios prioritários aprovados;
- sandbox evolutivo separado e sem promoção automatica.

Checklist executável associado:

- `python tools/validate_v1.py --profile development`
- `python tools/go_live_internal_checklist.py --profile development`
- repetir ambos no perfil `controlled` quando `DATABASE_URL` estiver ativo.

Os scripts executáveis agora fazem preflight explícito do ambiente e devem ser tratados como gate formal de `go/no-go`. No perfil `controlled`, eles falham cedo quando:

- `ruff` não esta instalado no ambiente oficial;
- `DATABASE_URL` não foi definida;
- o PostgreSQL não responde;
- as credenciais de `DATABASE_URL` estão incorretas.

Usar `docs/operations/internal-pilot-plan.md` como plano mínimo da primeira janela operacional após esse gate.

---

## 4. Estado atual do baseline

Leitura objetiva do estado atual:

- `núcleo central funcional`: atendido;
- `memória util básica`: atendido, com `PostgreSQL` validado como backend operacional recomendado e `sqlite` mantido como fallback local;
- `governança mínima robusta`: atendido no escopo atual do `v1`;
- `observabilidade mínima`: atendido, com benchmark favoravel para o `v1`;
- `sandbox evolutivo separado`: atendido, mantendo `sandbox-only` e sem promoção automatica;
- `configuração mínima reproduzivel`: atendido para baseline local;
- `readiness documental final`: atendido;
- `decisão formal de go/no-go`: atendido, com `GO CONDICIONAL` registrado em `2026-03-19`.

---

## 5. Critérios de go

Só autorizar `go-live` se:

- fluxos prioritários estiverem estáveis;
- bloqueios e permissoes estiverem funcionando;
- logs e tracing estiverem ativos;
- falhas residuais conhecidas estiverem documentadas;
- escopo de uso estiver claramente delimitado.

---

## 6. Critérios de no-go

Negar `go-live` se houver:

- falha recorrente de governança;
- comportamento central imprevisivel;
- memória inconsistente;
- ausencia de rollback claro;
- observabilidade insuficiente;
- estados quebrados frequentes.

---

## 7. Smoke checks de lancamento

Executar antes do `go-live`:

- entrada e síntese básicas;
- recuperacao mínima de memória util;
- bloqueio de ação indevida;
- execução simples de baixo risco;
- registro de logs e traces;
- simulacao de falha local com recuperacao controlada;
- comparação sandbox entre baseline e candidata sem promoção.

Execução recomendada:

```powershell
docker compose -f infra/local-postgres.compose.yml up -d
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5433/jarvis"
python tools/validate_v1.py --profile controlled
python tools/go_live_internal_checklist.py --profile controlled
```

---

## 8. Pendencias práticas antes do go-live

Antes do primeiro uso real, ainda faltam:

- congelar o escopo operacional inicial do primeiro uso real;
- registrar a janela de observação do primeiro rollout controlado;
- definir quem acompanha e interrompe o fluxo em caso de anomalia.

---

## 9. Regime de lancamento inicial

O primeiro `go-live` deve seguir:

- escopo reduzido;
- janela de observação conhecida;
- monitoramento reforçado;
- facilidade de reversao;
- registro explícito das primeiras ocorrencias.

---

## 10. Resultado esperado do go-live

O `go-live` do `v1` não deve provar maturidade total.

Ele deve provar:

- utilidade controlada;
- estabilidade mínima;
- governança funcional;
- rastreabilidade suficiente;
- capacidade de conter e corrigir falhas.

---

## 11. Relação com próximos passos

Após o `go-live`, o foco deve ir para:

- observação do uso real;
- correcao de falhas estruturais;
- ajuste de escopo operacional;
- geracao de evidência para expansao do `v1` e preparacao do `v2`.
