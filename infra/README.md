# Infra

Automação local, configurações de infraestrutura e base para ambientes futuros.

## PostgreSQL local

Arquivo principal para o backend operacional de memória:

- `infra/local-postgres.compose.yml`

Uso esperado:

```powershell
docker compose -f infra/local-postgres.compose.yml up -d
```

URL padrao correspondente:

```text
postgresql://postgres:postgres@localhost:5432/jarvis
```
