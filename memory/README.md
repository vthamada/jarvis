# Memory

Area reservada para componentes de memoria do sistema.

Subdominios ativos ou previstos:

- memoria de sessao;
- memoria episodica;
- memoria de missao;
- memoria critica;
- mecanismos de consolidacao.

Validacao operacional local:

- `sqlite` continua sendo o fallback local;
- `PostgreSQL` e o backend operacional oficial e deve ser validado com `DATABASE_URL` real na porta `5433`;
- a validacao recomendada combina `python -m tools.benchmarks --postgres-url ...` com `pytest services/memory-service/tests/test_memory_postgres_integration.py -q`.
