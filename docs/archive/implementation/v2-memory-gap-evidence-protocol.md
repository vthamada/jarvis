# V2 Memory Gap Evidence Protocol

- cut: `v2-memory-gap-evidence-cut`
- sprint: `sprint-1-gap-evidence-protocol`
- hypothesis_count: `3`

## user scope is typed but not runtime rich

- hypothesis_id: `user_scope_is_typed_but_not_runtime_rich`
- why_it_matters: se user scope for apenas rastreio minimo, a separacao entre sessao e usuario pode parecer coberta sem estar realmente operacionalizada.
- baseline_signals:
  - InputContract, MemoryRecoveryContract e MemoryRecordContract carregam user_id
  - memory-service persiste user_id em interaction_turns
  - nao existe um pacote dedicado de memoria de usuario comparavel a session_continuity ou specialist_shared_memory
- proof_signals:
  - baseline atual nao consegue produzir contexto de usuario alem de ids e rastreio basico
  - consumidores canonicos precisam reconstituir estado por sessao quando deveriam herdar memoria de usuario
  - existe perda observavel quando a mesma pessoa aparece em sessoes diferentes
- hold_signals:
  - os consumidores atuais nao exigem memoria de usuario alem do rastreio atual
  - a continuidade por sessao e missao cobre o comportamento necessario nesta fase

## shared memory does not fully cover a stronger agent scope

- hypothesis_id: `shared_memory_does_not_equal_agent_scope`
- why_it_matters: o baseline atual pode estar cobrindo handoff suficiente para especialistas promovidos, mas ainda nao prova se isso substitui um escopo mais forte por agente ou participante.
- baseline_signals:
  - specialist_shared_memory existe por session_id e specialist_type
  - consumer_mode, mission_context_brief, domain_context_brief e continuity_context_brief ja enriquecem o handoff
  - nao existe escopo persistente mais forte por agente alem do pacote mediado pelo nucleo
- proof_signals:
  - o mesmo especialista precisa reconstruir contexto demais em sessoes ou missoes relacionadas
  - hints de dominio e continuidade nao bastam para handoffs recorrentes
  - o custo de compor shared memory cresce mais rapido do que o ganho do baseline
- hold_signals:
  - domain_guided_memory_packet atual permanece suficiente para as rotas promovidas
  - nao existe perda clara entre especialistas recorrentes no runtime atual

## organization scope is still a future shape, not a proven gap

- hypothesis_id: `organization_scope_is_still_only_a_future_shape`
- why_it_matters: isso impede tratar ausencia de organization scope como lacuna comprovada quando ela pode ser apenas uma possibilidade futura.
- baseline_signals:
  - o benchmark de Mem0 trouxe org scope como referencia externa
  - o baseline atual do JARVIS ainda nao tem consumidor canonico de organization memory
  - nao existe evento ou contrato corrente exigindo esse escopo como parte do runtime principal
- proof_signals:
  - um consumidor canonico passar a exigir contexto persistente acima de usuario e sessao
  - o baseline atual falhar em separar memoria compartilhada de contexto institucional
- hold_signals:
  - nenhum fluxo do runtime atual depende de organization scope para funcionar bem
  - a hipotese continuar sem consumidor soberano claro

