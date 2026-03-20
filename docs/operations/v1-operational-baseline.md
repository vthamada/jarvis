# V1 Operational Baseline

## 1. Objetivo

Este documento consolida o baseline operacional do JARVIS `v1` para uso controlado.

Ele substitui a leitura fragmentada que antes estava separada entre readiness, `go/no-go`
e producao controlada.

Fontes normativas:

- `documento_mestre_jarvis.md`
- `HANDOFF.md`
- `docs/operations/release-and-change-management.md`
- `docs/operations/incident-response.md`

---

## 2. Estado operacional atual

Leitura oficial do baseline atual:

- decisao vigente: `GO CONDICIONAL` para uso controlado;
- `internal pilot` ja executado com trilhas saudaveis;
- backend operacional recomendado: `PostgreSQL`;
- `sqlite` permanece apenas como fallback local de desenvolvimento;
- observabilidade local persistida e auditavel;
- `evolution-lab` permanece `sandbox-only`, sem promocao automatica.

Em termos praticos, o `v1` esta liberado para uso real controlado em escopo reduzido,
com monitoramento reforcado e rollback simples.

---

## 3. O que o v1 prova

O `v1` deve ser lido como prova de:

- entidade unica e coerente;
- continuidade util de sessao e missao;
- deliberacao convincente no escopo atual;
- operacao segura de baixo risco;
- governanca e rastreabilidade suficientes para uso controlado.

O `v1` nao deve ser avaliado como:

- multimodalidade plena;
- plataforma multiagente ampla;
- autoevolucao forte em producao;
- sistema de alto risco ou alta autonomia irrestrita.

---

## 4. Escopo autorizado

O `v1` esta autorizado para:

- analise e sintese de informacao;
- planejamento e estruturacao de tarefas;
- producao de artefatos textuais;
- continuidade simples de missao;
- operacao local de baixo risco e reversivel;
- uso interno ou controlado com operadores conscientes do escopo.

O `v1` nao esta autorizado para:

- acoes irreversiveis de alto impacto;
- automacoes amplas sobre sistemas criticos;
- operacoes financeiras, juridicas ou de seguranca de alto risco;
- mutacao livre de memoria critica;
- promocao evolutiva em ambiente produtivo;
- operacao ampla com baixa observabilidade.

---

## 5. Readiness minima

Antes de qualquer ampliacao de uso, confirmar:

- nucleo central funcional;
- memoria util operando no backend oficial;
- governanca minima robusta ativa;
- trilha de observabilidade e auditoria ativa;
- rollback operacional simples e conhecido;
- separacao clara entre baseline e sandbox evolutivo;
- scripts canonicos de validacao verdes.

Scripts canonicos:

```powershell
python tools/validate_v1.py --profile development
python tools/go_live_internal_checklist.py --profile development
python tools/validate_v1.py --profile controlled
python tools/go_live_internal_checklist.py --profile controlled
```

Quando o perfil `controlled` for usado, tratar `DATABASE_URL` com `PostgreSQL` como
pre-condicao obrigatoria.

---

## 6. Regime operacional autorizado

O uso controlado do `v1` exige:

- escopo pequeno e explicito;
- monitoramento reforcado;
- capacidade de pausa e bloqueio;
- rollback para baseline conhecido;
- registro de anomalias e decisoes relevantes.

Toda anomalia relevante deve permitir ao menos:

- bloquear o fluxo atual;
- reduzir temporariamente a autonomia;
- isolar adaptador ou servico suspeito;
- reverter para baseline conhecido;
- encaminhar revisao manual.

Ver tambem:

- `docs/operations/incident-response.md`
- `docs/operations/release-and-change-management.md`

---

## 7. Resultado do gate e do piloto

Estado consolidado em `2026-03-20`:

- o gate `controlled` ja foi executado com sucesso;
- o `internal pilot` ja foi executado;
- o piloto agora e evidencia operacional, nao pendencia aberta;
- nao ha sinal atual que justifique reabrir o nucleo do `v1`.

O plano detalhado da primeira janela foi preservado apenas como historico em:

- `docs/archive/operations/internal-pilot-plan.md`

---

## 8. Criterios de ampliacao ou contencao

So ampliar o uso do `v1` se houver:

- estabilidade repetida;
- rastreabilidade suficiente;
- baixa incidencia de falhas de governanca;
- recuperacao confiavel apos falhas;
- memoria util sem inconsistencia relevante.

Reduzir escopo, pausar ou aplicar rollback se houver:

- falhas recorrentes de governanca;
- memoria inconsistente;
- operacao sem rastreabilidade;
- regressao importante apos mudanca;
- alto volume de intervencao manual corretiva.

---

## 9. Baseline tecnico oficial

O baseline tecnico oficial do `v1` e:

- `orchestrator-service` como coordenador do fluxo principal;
- `PostgreSQL` como backend operacional recomendado;
- trilha local persistida como observabilidade primaria;
- `LangSmith` apenas como camada complementar quando configurado;
- `LangGraph` mantido como POC opcional, fora do caminho critico do `v1`;
- `evolution-lab` mantido em `sandbox-only`.

---

## 10. Relacao com o pos-v1

Este documento fecha o baseline operacional do `v1`.

Qualquer novo trabalho de:

- `LangGraph` como substrato principal;
- memoria semantica mais profunda;
- especialistas mais amplos;
- voz e multimodalidade;
- autoevolucao mais forte

deve ser tratado como pos-`v1`, `v1.5` ou `v2`, e nao como requisito para manter
o baseline atual utilizavel.
