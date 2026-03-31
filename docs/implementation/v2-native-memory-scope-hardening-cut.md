# V2 Native Memory Scope Hardening Cut

## 1. Objetivo

Este documento abre o recorte que sucede o fechamento do
`v2-memory-gap-evidence-cut`.

Ele existe para:

- endurecer nativamente os pontos de pressao real encontrados no baseline atual;
- enriquecer `user scope` sem abrir dependencia externa nova;
- fortalecer contexto recorrente para especialistas promovidos sem romper a mediacao do nucleo;
- manter `organization scope` fora do baseline ate existir consumidor canonico soberano.

---

## 2. Leitura correta deste corte

O que este corte assume como baseline obrigatorio:

- `docs/implementation/v2-memory-gap-evidence-cut-closure.md` ja fechou o recorte de prova de lacuna em `manter_fechado`;
- `docs/implementation/v2-memory-gap-decision.md` preservou `Mem0` em `absorver_depois`;
- o baseline atual continua forte em `conversation`, `session` e `mission`;
- a pressao real ficou concentrada em `user scope` e `specialist_shared_memory`, ainda sem justificar absorcao externa.

O que este corte passa a fazer acima desse baseline:

- endurecer contratos e runtime nativos de memoria por escopo;
- melhorar o valor do `user scope` dentro do proprio JARVIS;
- medir melhor recorrencia de especialistas antes de qualquer nocao mais forte de agent scope;
- manter o foco em correcoes soberanas, nao em novas tecnologias.

---

## 3. Escopo do corte

### Sprint 1. User scope hardening

Status atual:

- concluida.

Objetivo:

- enriquecer leitura e recuperacao de `user scope` acima de ids e rastreio minimo.

Entregas esperadas:

- contrato explicito para user context recuperavel;
- leitura nativa comparavel a session e mission continuity, quando houver dados suficientes;
- observabilidade minima para esse escopo.

Leitura de fechamento:

- `shared/contracts/__init__.py` agora exp?e `UserScopeContextContract` como contrato canonico do escopo de usuario;
- `shared/memory_registry.py` passou a tratar `user` como recovery scope default quando houver `user_id`;
- `memory-service` agora persiste snapshot nativo de user scope com intents recentes, foco de dominio, missoes ativas e preferencia de continuidade;
- `orchestrator-service` passou a emitir `user_scope_status` e `user_context_brief` nos eventos de memoria;
- `observability-service` agora resume esse escopo em `user_scope_status`, sem abrir dependencia externa nem promover `organization scope`.

### Sprint 2. Recurrent specialist context hardening

Status atual:

- aberta.

Objetivo:

- fortalecer o contexto recorrente de especialistas promovidos sem transformar handoff em agent runtime externo.

Entregas esperadas:

- leitura mais forte de recorrencia por especialista no baseline atual;
- criterio claro do que continua handoff e do que vira contexto recorrente soberano;
- limites explicitos de escrita e compartilhamento preservados.

### Sprint 3. Organization no-go guard

Status atual:

- aberta.

Objetivo:

- impedir promocao prematura de `organization scope` sem consumidor canonico real.

Entregas esperadas:

- regra explicita de no-go para organization scope no baseline atual;
- sinal claro de reabertura futura apenas se consumidor soberano surgir.

### Sprint 4. Cut closure

Status atual:

- aberta.

Objetivo:

- fechar o recorte provando que o baseline ficou mais forte sem abrir dependencia externa.

Entregas esperadas:

- fechamento formal do corte com artefato regeneravel;
- backlog curto do que ainda pode justificar recorte futuro;
- status de `Mem0` mantido ou revisado apenas por nova evidencia local.

---

## 4. Definicao de pronto deste corte

Este corte deve ser considerado pronto quando:

- `user scope` deixar de ser apenas ids e rastreio minimo quando houver evidencias suficientes para contexto nativo mais rico;
- especialistas promovidos tiverem leitura recorrente melhor sem romper `through_core_only`;
- `organization scope` continuar explicitamente fora do baseline enquanto nao houver consumidor canonico soberano;
- `tools/engineering_gate.py --mode release` continuar passando sem dependencia externa nova.

---

## 5. Documento de apoio obrigatorio

Ler em conjunto com:

- `docs/implementation/v2-memory-gap-evidence-cut-closure.md`
- `docs/implementation/v2-memory-gap-decision.md`
- `docs/implementation/v2-memory-gap-baseline-evidence.md`
- `docs/architecture/technology-study.md`
- `shared/memory_registry.py`
- `services/memory-service/src/memory_service/service.py`
- `services/memory-service/src/memory_service/repository.py`
