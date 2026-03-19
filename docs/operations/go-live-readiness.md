# Go-Live Readiness

## 1. Objetivo

Este documento define o regime mínimo de **readiness e go-live** do JARVIS `v1` em produção controlada.

Ele deriva principalmente de:

- `documento_mestre_jarvis.md`, capítulo `346. Plano de readiness e go-live do v1`
- `docs/operations/v1-production-controlled.md`

Seu papel é transformar a prontidão do `v1` em checklist operacional claro.

---

## 2. Princípio geral

O `go-live` do `v1` só deve ocorrer quando houver:

- capacidade funcional mínima;
- governança mínima ativa;
- observabilidade suficiente;
- contenção e rollback claros;
- escopo real de uso explicitamente limitado.

---

## 3. Checklist mínimo de readiness

Antes de liberar o `v1`, confirmar:

- ambiente operacional identificado;
- configuração mínima reproduzível;
- núcleo central funcional no escopo pretendido;
- memória útil básica operando;
- governança mínima robusta ativa;
- observabilidade mínima ativa;
- rollback operacional definido;
- cenários prioritários aprovados;
- sandbox evolutivo separado e sem promocao automatica.

---

## 4. Critérios de go

Só autorizar `go-live` se:

- fluxos prioritários estiverem estáveis;
- bloqueios e permissões estiverem funcionando;
- logs e tracing estiverem ativos;
- falhas residuais conhecidas estiverem documentadas;
- escopo de uso estiver claramente delimitado.

---

## 5. Critérios de no-go

Negar `go-live` se houver:

- falha recorrente de governança;
- comportamento central imprevisível;
- memória inconsistente;
- ausência de rollback claro;
- observabilidade insuficiente;
- estados quebrados frequentes.

---

## 6. Smoke checks de lançamento

Executar antes do `go-live`:

- entrada e síntese básicas;
- recuperação mínima de memória útil;
- bloqueio de ação indevida;
- execução simples de baixo risco;
- registro de logs e traces;
- simulação de falha local com recuperação controlada;
- comparacao sandbox entre baseline e candidata sem promocao.

---

## 7. Regime de lançamento inicial

O primeiro `go-live` deve seguir:

- escopo reduzido;
- janela de observação conhecida;
- monitoramento reforçado;
- facilidade de reversão;
- registro explícito das primeiras ocorrências.

---

## 8. Resultado esperado do go-live

O `go-live` do `v1` não deve provar maturidade total.

Ele deve provar:

- utilidade controlada;
- estabilidade mínima;
- governança funcional;
- rastreabilidade suficiente;
- capacidade de conter e corrigir falhas.

---

## 9. Relação com próximos passos

Após o `go-live`, o foco deve ir para:

- observação do uso real;
- correção de falhas estruturais;
- ajuste de escopo operacional;
- geração de evidência para expansão do `v1` e preparação do `v2`.
