# Memory

Area reservada para componentes de memoria do sistema.

Subdominios esperados:

- memoria de sessao;
- memoria episodica;
- memoria critica;
- mecanismos de consolidacao.


Validacao operacional local:

- `sqlite` continua sendo o fallback padrao do `v1`;
- `PostgreSQL` e a candidata operacional e deve ser validado com `DATABASE_URL` real na porta `5433`;
- a validacao recomendada combina `python -m tools.benchmarks --postgres-url ...` com `pytest services/memory-service/tests/test_memory_postgres_integration.py -q`.
