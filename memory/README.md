# Memory

Area reservada para componentes de memória do sistema.

Subdominios esperados:

- memória de sessão;
- memória episodica;
- memória crítica;
- mecanismos de consolidacao.


Validação operacional local:

- `sqlite` continua sendo o fallback padrao do `v1`;
- `PostgreSQL` e a candidata operacional e deve ser validado com `DATABASE_URL` real na porta `5433`;
- a validação recomendada combina `python -m tools.benchmarks --postgres-url ...` com `pytest services/memory-service/tests/test_memory_postgres_integration.py -q`.
