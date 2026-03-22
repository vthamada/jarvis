# observability-service

Servico responsavel por logs, traces, auditoria e evidencia operacional do sistema.

Responsabilidades atuais:

- padronizar eventos internos;
- persistir a trilha local primaria;
- correlacionar `request_id`, `session_id`, `mission_id` e `operation_id`;
- auditar requests recentes;
- espelhar traces para camada agentic complementar quando configurado.
