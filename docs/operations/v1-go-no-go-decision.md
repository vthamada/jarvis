# V1 Go No-Go Decision

## 1. Objetivo

Este documento registra a decisao formal de `go/no-go` do JARVIS `v1` para producao controlada.

Data de referencia desta decisao: `2026-03-19`.

Ele complementa:

- `docs/operations/go-live-readiness.md`
- `docs/operations/v1-production-controlled.md`
- `HANDOFF.md`

---

## 2. Decisao atual

**Decisao:** `GO CONDICIONAL` para producao controlada do `v1`.

Isto significa:

- o baseline atual esta tecnicamente forte o suficiente para primeiro uso real em escopo reduzido;
- a liberacao nao vale para uso amplo, silencioso ou de alto impacto;
- toda operacao inicial deve ocorrer com monitoramento reforcado, rollback simples e escopo explicitamente limitado.

---

## 3. Base da decisao

A decisao de `GO CONDICIONAL` se apoia em evidencia objetiva do repositorio atual:

- suite principal `pytest -q` passando no baseline atual;
- benchmark dirigido implementado e executado com decisoes consolidadas;
- `memory-service` validado contra `PostgreSQL` local, agora tratado como backend operacional recomendado do `v1`;
- `observability-service` benchmarkado como suficiente para debugging, auditoria e correlacao do fluxo;
- `knowledge-service` estabilizado no baseline com retrieval deterministico ponderado ja absorvido;
- `evolution-lab` mantido em `sandbox-only`, sem promocao automatica;
- fluxo central integrado entre orquestracao, memoria, governanca, conhecimento, observabilidade e operacao.

---

## 4. Escopo autorizado deste go

O `GO CONDICIONAL` autoriza apenas:

- analise e sintese de informacao;
- planejamento e estruturacao de tarefas;
- producao de artefatos textuais;
- continuidade de sessao e missao simples;
- uso interno ou controlado com operadores conscientes do escopo do `v1`.

---

## 5. Escopo nao autorizado

Esta decisao nao autoriza:

- automacoes irreversiveis de alto impacto;
- operacoes financeiras, juridicas ou de seguranca de alto risco;
- alteracao livre de memoria critica;
- promocao evolutiva em ambiente produtivo;
- uso amplo com baixa observabilidade;
- expansao multiagente ampla sem nova rodada de maturacao.

---

## 6. Condicoes obrigatorias do primeiro uso real

Antes do primeiro uso real, manter obrigatoriamente:

- `DATABASE_URL` apontando para o backend `PostgreSQL` validado do projeto;
- observabilidade local ativa;
- benchmark e suite de testes verdes no baseline imediatamente anterior ao uso;
- rollback simples para baseline conhecido;
- escopo inicial documentado e pequeno;
- registro dos primeiros fluxos e anomalias relevantes.

---

## 7. Gatilhos automaticos de no-go ou rollback

A decisao deve ser revertida para `NO-GO` ou para rollback imediato se houver:

- falha recorrente de governanca;
- perda de rastreabilidade do fluxo;
- memoria inconsistente em uso real;
- regressao central apos mudanca recente;
- operacao fora do escopo autorizado;
- necessidade frequente de intervencao manual corretiva para manter o sistema utilizavel.

---

## 8. Proximos passos apos esta decisao

Com a decisao formal registrada, os proximos passos corretos sao:

1. congelar o escopo do primeiro uso real controlado;
2. executar a primeira janela de producao controlada com observacao reforcada;
3. registrar ocorrencias, falhas e sinais de estabilidade;
4. decidir o destino editorial de `documento_mestre_do_jarvis.md`.
