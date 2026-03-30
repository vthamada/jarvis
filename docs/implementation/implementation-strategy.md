# Implementation Strategy

## 1. Objetivo

Este documento preserva a estratégia prática que levou ao fechamento do `v1` do JARVIS.

Ele continua útil como referência de engenharia, mas não é mais o plano ativo do projeto.

Leitura correta hoje:

- para direção de médio prazo: `docs/roadmap/programa-ate-v3.md`
- para execução imediata: `docs/archive/implementation/post-v1-sprint-cycle.md`
- para histórico do `v1`: este documento

---

## 2. Princípios que estruturaram o v1

A implementação do `v1` obedeceu a:

- fundação antes de feature;
- contrato antes de integração complexa;
- identidade antes de automação ampla;
- governança antes de autonomia expandida;
- observabilidade desde o início;
- incrementos úteis e testáveis;
- estado persistente onde isso é estruturalmente importante.

---

## 3. Sequência histórica do v1

Sequência que estruturou o baseline:

1. alinhar baseline técnico e documental;
2. consolidar memória persistente e continuidade;
3. estruturar observabilidade mínima do fluxo;
4. fortalecer engines, conhecimento e operação útil;
5. endurecer governança para o `v1`;
6. consolidar benchmark, readiness e decisão de fechamento para produção controlada.

Leitura mais concreta dessa sequência:

- primeiro o repositório e a camada `shared/` foram materializados;
- depois o orquestrador passou a coordenar memória, governança e operação;
- em seguida a memória saiu de processo e passou a ser persistente;
- depois observabilidade, conhecimento, artefatos operacionais e readiness foram endurecidos;
- por fim, o baseline foi validado em `development`, `controlled` e `internal pilot`, antes de ser congelado.

---

## 4. Resultado prático

O baseline implementado do `v1` cobre:

- `orchestrator-service` como coordenador do fluxo;
- `memory-service` com persistência útil, `sqlite` como fallback local e `PostgreSQL` como backend operacional oficial;
- `governance-service` com decisão simples, condicionada, bloqueada e adiada para validação;
- `knowledge-service` com retrieval determinístico local e corpus curado externo ao código;
- `operational-service` com artefatos textuais de baixo risco;
- `observability-service` com trilha de eventos persistida e auditável;
- `evolution-lab` com comparação `sandbox-only` entre baseline e candidata;
- `engines/` dedicadas para identidade, executivo, planejamento, cognição e síntese;
- `jarvis-console` como interface textual mínima.

Capacidades operacionais que emergiram desse caminho:

- trilha auditável de eventos e decisões;
- validação executável por scripts canônicos;
- piloto interno com evidência reaproveitável;
- comparação controlada entre baseline e fluxo opcional de `LangGraph`.

---

## 5. Leitura correta do estado atual

O `v1` está encerrado e congelado para uso controlado.

Portanto, a sequência de engenharia ativa deixou de ser "fechar o `v1`" e passou a ser:

1. aprofundar continuidade entre missões;
2. medir essa continuidade com observabilidade e evidência;
3. decidir o corte entre `v1.5` e `v2`;
4. só depois absorver componentes externos com evidência suficiente.

---

## 6. Regra de execução que permanece válida

Mesmo no `pós-v1`, a regra continua sendo:

- não implementar módulos isolados apenas por completude estrutural;
- implementar ciclos integrados de capacidade;
- só absorver tecnologia externa quando houver problema real do núcleo, consumidor claro e delimitação do que entra agora.
