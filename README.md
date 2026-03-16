# JARVIS

JARVIS e um sistema agente stateful, multimodal e governado.

Este repositorio materializa a base estrutural definida em [documento_mestre_jarvis.md](/d:/Users/DTI/Desktop/jarvis/documento_mestre_jarvis.md) e nos derivados tecnicos em `docs/`.

## Estado atual

O projeto esta na fundacao do monorepo:

- estrutura principal criada;
- servicos e engines centrais com esqueletos minimos;
- convencoes iniciais de Python, testes e tooling registradas;
- documentacao canonica e operacional sincronizadas.

## Estrutura principal

- `apps/`: interfaces e superficies de produto
- `services/`: servicos centrais do sistema
- `engines/`: engines cognitivas e executivas
- `memory/`: componentes de memoria
- `knowledge/`: componentes de conhecimento e retrieval
- `governance/`: politicas e mecanismos de governanca
- `observability/`: suporte a logs, traces e metricas
- `evolution/`: laboratorio evolutivo
- `shared/`: contratos, schemas, tipos, eventos e estado
- `infra/`: infraestrutura e automacao local
- `tests/`: testes compartilhados do repositorio
- `tools/`: scripts e utilitarios

## Bootstrap minimo

### Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
pytest
```

### Node

```powershell
npm install
npm run lint
```

## Documentos principais

- [Documento-Mestre](/d:/Users/DTI/Desktop/jarvis/documento_mestre_jarvis.md)
- [HANDOFF](/d:/Users/DTI/Desktop/jarvis/HANDOFF.md)
- [CHANGELOG](/d:/Users/DTI/Desktop/jarvis/CHANGELOG.md)
- [Plano da Sprint 1](/d:/Users/DTI/Desktop/jarvis/docs/implementation/sprint-1-plan.md)
