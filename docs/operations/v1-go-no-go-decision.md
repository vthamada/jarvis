# V1 Go No-Go Decision

## 1. Objetivo

Este documento registra a decisão formal de `go/no-go` do JARVIS `v1` para produção controlada.

Data de referencia desta decisão: `2026-03-19`.

Ele complementa:

- `docs/operations/go-live-readiness.md`
- `docs/operations/v1-production-controlled.md`
- `HANDOFF.md`

---

## 2. Decisóo atual

**Decisóo:** `GO CONDICIONAL` para produção controlada do `v1`.

Isto significa:

- o baseline atual esta tecnicamente forte o suficiente para primeiro uso real em escopo reduzido;
- a liberacao não vale para uso amplo, silencioso ou de alto impacto;
- toda operação inicial deve ocorrer com monitoramento reforçado, rollback simples e escopo explicitamente limitado.

---

## 3. Base da decisão

A decisão de `GO CONDICIONAL` se apoia em evidência objetiva do repositório atual:

- suite principal `pytest -q` passando no baseline atual;
- benchmark dirigido implementado e executado com decisóes consolidadas;
- `memory-service` validado contra `PostgreSQL` local, agora tratado como backend operacional recomendado do `v1`;
- `observability-service` benchmarkado como suficiente para debugging, auditoria e correlação do fluxo;
- `knowledge-service` estabilizado no baseline com retrieval determinístico ponderado já absorvido;
- `evolution-lab` mantido em `sandbox-only`, sem promoção automatica;
- fluxo central integrado entre orquestracao, memória, governança, conhecimento, observabilidade e operação.

---

## 4. Escopo autorizado deste go

O `GO CONDICIONAL` autoriza apenas:

- análise e síntese de informação;
- planejamento e estruturacao de tarefas;
- produção de artefatos textuais;
- continuidade de sessão e missão simples;
- uso interno ou controlado com operadores conscientes do escopo do `v1`.

---

## 5. Escopo não autorizado

Esta decisão não autoriza:

- automações irreversiveis de alto impacto;
- operações financeiras, jurídicas ou de segurança de alto risco;
- alteracao livre de memória crítica;
- promoção evolutiva em ambiente produtivo;
- uso amplo com baixa observabilidade;
- expansao multiagente ampla sem nova rodada de maturacao.

---

## 6. Condições obrigatorias do primeiro uso real

Antes do primeiro uso real, manter obrigatoriamente:

- `DATABASE_URL` apontando para o backend `PostgreSQL` validado do projeto;
- observabilidade local ativa;
- benchmark e suite de testes verdes no baseline imediatamente anterior ao uso;
- rollback simples para baseline conhecido;
- escopo inicial documentado e pequeno;
- registro dos primeiros fluxos e anomalias relevantes.

---

## 7. Gatilhos automaticos de no-go ou rollback

A decisão deve ser revertida para `NO-GO` ou para rollback imediato se houver:

- falha recorrente de governança;
- perda de rastreabilidade do fluxo;
- memória inconsistente em uso real;
- regressao central após mudanca recente;
- operação fora do escopo autorizado;
- necessidade frequente de intervencao manual corretiva para manter o sistema utilizavel.

---

## 8. Próximos passos após esta decisão

Com a decisão formal registrada, os próximos passos corretos sóo:

1. congelar o escopo do primeiro uso real controlado;
2. executar a primeira janela de produção controlada com observação reforçada;
3. registrar ocorrencias, falhas e sinais de estabilidade;
4. comparar o baseline atual com a POC de `LangGraph` após a coleta do `internal pilot`;
5. decidir o destino editorial de `documento_mestre_do_jarvis.md`.
