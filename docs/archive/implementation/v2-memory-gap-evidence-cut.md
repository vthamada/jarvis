# V2 Memory Gap Evidence Cut

## 1. Objetivo

Este documento abre o recorte que sucede o fechamento do
`v2-governed-benchmark-execution-cut`.

Ele existe para:

- provar ou negar a existencia de uma lacuna real de memoria multicamada acima do baseline atual;
- impedir reabertura oportunista de `Mem0` sem evidencia soberana do proprio JARVIS;
- transformar a discussao de memoria multicamada em protocolo observavel, nao em preferencia abstrata;
- manter qualquer futura absorcao subordinada a `memory_registry`, contratos canonicos e governanca final.

---

## 2. Leitura correta deste corte

O que este corte assume como baseline obrigatorio:

- `docs/archive/implementation/v2-governed-benchmark-execution-cut-closure.md` ja fechou o benchmark governado com `Mastra` e `AutoGPT Platform` como referencia e `Mem0` como `absorver_depois`;
- `services/memory-service/src/memory_service/service.py` e `repository.py` ja persistem continuidade de sessao, continuidade de missao e `specialist_shared_memory`;
- `shared/memory_registry.py` ja define as 11 classes canonicas e suas politicas de compartilhamento;
- o baseline atual ainda nao provou, por evidencia propria, onde a separacao entre conversa, sessao, usuario e memoria compartilhada passa a ser insuficiente.

O que este corte passa a fazer acima desse baseline:

- explicitar hipoteses de lacuna de memoria multicamada;
- definir criterio de prova e sinais de reabertura para um futuro recorte de absorcao;
- manter `Mem0` apenas como candidata condicional, sem promover adaptador ou dependencia nova.

---

## 3. Escopo do corte

### Sprint 1. Gap evidence protocol

Status atual:

- concluida.

Objetivo:

- transformar a hipotese de lacuna de memoria multicamada em protocolo regeneravel de evidencia.

Entrega realizada:

- criado dataset versionado em `tools/benchmarks/datasets/v2_memory_gap_evidence_hypotheses.json`;
- criado renderizador `tools/archive/render_memory_gap_evidence_protocol.py`;
- criado artefato regeneravel `docs/archive/implementation/v2-memory-gap-evidence-protocol.md` com hipoteses, cobertura baseline, sinais de prova e sinais de nao-lacuna.

### Sprint 2. Baseline evidence collection

Status atual:

- concluida.

Objetivo:

- coletar evidencias locais do baseline atual de memoria sem introduzir framework externo.

Entregas esperadas:

- leitura comparavel da cobertura atual entre conversa, sessao, missao, usuario e memoria compartilhada;
- pontos em que o baseline atual ainda depende de id, resumo ou handoff indireto;
- racional curto sobre onde existe ou nao existe gargalo estrutural real.

Entrega realizada:

- criado dataset versionado em `tools/benchmarks/datasets/v2_memory_gap_baseline_scope_rules.json`;
- criado renderizador `tools/archive/render_memory_gap_baseline_evidence.py`;
- criado artefato regeneravel `docs/archive/implementation/v2-memory-gap-baseline-evidence.md` com leitura por escopo do baseline atual;
- o baseline ficou lido assim:
  - conversa, sessao e missao ja sao escopos operacionais suficientes nesta fase;
  - usuario aparece como escopo tipado e rastreado, mas ainda nao como memoria runtime rica;
  - `specialist_shared_memory` cobre bem handoff guiado, mas ainda nao prova um escopo mais forte por agente;
  - `organization scope` continua forma futura e ainda nao e lacuna comprovada do runtime atual.

### Sprint 3. Reopen or hold decision

Status atual:

- concluida.

Objetivo:

- decidir se a lacuna ficou comprovada o suficiente para abrir um recorte proprio de absorcao futura.

Entregas esperadas:

- decisao disciplinada entre `manter_fechado` ou `abrir_recorte_de_absorcao`; 
- backlog classificado do que corrigir no baseline antes de qualquer absorcao;
- atualizacao de `technology-study.md`, `HANDOFF.md` e do proprio corte.

Entrega realizada:

- criado dataset versionado em `tools/benchmarks/datasets/v2_memory_gap_decision.json`;
- criado renderizador `tools/archive/render_memory_gap_decision.py`;
- criado artefato regeneravel `docs/archive/implementation/v2-memory-gap-decision.md`;
- a decisao desta sprint ficou em `manter_fechado`, preservando `Mem0` em `absorver_depois`;
- o backlog antes de qualquer futura absorcao ficou restrito a provar consumidor canonico de user scope mais rico, recorrencia real de agent scope e necessidade soberana de organization scope.

### Sprint 4. Cut closure

Status atual:

- aberta.

Objetivo:

- fechar o recorte sem deixar a hipotese de memoria multicamada em aberto por inercia.

Entregas esperadas:

- fechamento formal do corte com artefato regeneravel;
- criterio claro do que continua como baseline soberano e do que sobe para fase futura;
- definicao explicita do status de `Mem0` apos a coleta de evidencia.

---

## 4. Hipoteses dentro do recorte

Este recorte investiga estas perguntas:

- o baseline atual separa bem conversa, sessao, missao e memoria compartilhada em todos os consumidores canonicos relevantes?
- `user_id` existe como chave, mas existe memoria de usuario suficiente como runtime governado, ou apenas rastreio minimo?
- existe lacuna real entre `specialist_shared_memory` e um escopo mais forte por agente ou por participante?
- a ausencia de escopo `organization` e de metricas explicitas de conflito entre escopos ja gera perda estrutural, ou ainda e apenas hipotese?

---

## 5. Definicao de pronto deste corte

Este corte deve ser considerado pronto quando:

- a hipotese de lacuna de memoria multicamada estiver quebrada em protocolo e evidencia minima do baseline;
- o recorte disser explicitamente se `Mem0` continua so como candidata condicional ou se sobe para um novo recorte;
- `tools/engineering_gate.py --mode release` continuar passando sem dependencia externa nova;
- `HANDOFF.md`, `README.md`, `docs/executive/master-summary.md` e `docs/architecture/technology-study.md` refletirem o mesmo estado real.

---

## 6. Documento de apoio obrigatorio

Ler em conjunto com:

- `docs/archive/implementation/v2-governed-benchmark-execution-cut-closure.md`
- `docs/archive/implementation/v2-governed-benchmark-decisions.md`
- `docs/archive/implementation/v2-memory-gap-evidence-protocol.md`
- `docs/archive/implementation/v2-memory-gap-baseline-evidence.md`
- `docs/archive/implementation/v2-memory-gap-decision.md`
- `docs/architecture/technology-study.md`
- `shared/memory_registry.py`
- `services/memory-service/src/memory_service/service.py`
- `services/memory-service/src/memory_service/repository.py`
