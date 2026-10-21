# AGENTS

Este repositório exige implementação disciplinada, mas não burocrática.

Toda mudança feita por agente deve seguir a
[Constituição de Engenharia](docs/documentation/engineering-constitution.md).

Leitura correta:

- use as regras como guardrails mínimos;
- aplique rigor em proporção ao risco;
- não troque implementação por ritual.

## Regras obrigatórias

- preserve a soberania do núcleo;
- não bypassar governança, memória canônica ou síntese final;
- preferir mudanças pequenas, reversíveis e auditáveis quando suficientes;
- não promover capability sem teste, observabilidade e documentação;
- toda implementação nova relevante deve incluir bateria de testes que valide o
  slice local e o fluxo ponta a ponta afetado;
- não introduzir dependência central nova sem justificativa arquitetural clara;
- tratar contratos compartilhados e eventos observáveis como interfaces estáveis;
- sincronizar `HANDOFF.md` e documentação operacional quando a mudança alterar o
  estado real do projeto;
- executar o gate adequado antes de tratar a rodada como fechada.

## Gate mínimo

```powershell
python tools/engineering_gate.py --mode standard
```

## Gate de liberação

```powershell
python tools/engineering_gate.py --mode release
```

## Regras de absorção externa

- tecnologia externa entra primeiro como referência, experimento ou complemento;
- nada externo assume o papel de cérebro real do sistema;
- promoção só com evidência.

### Direção de composição tecnológica — 2026-10-20

- seguir a estratégia ativa em
  [Technology Absorption Order](docs/architecture/technology-absorption-order.md);
- partir de uma tarefa útil e de uma lacuna observada, não da lista de projetos;
- antes de reimplementar uma capacidade existente, comparar brevemente reuso de
  código, adaptação e implementação própria; justificar a escolha pelo custo
  total, compatibilidade e evidência, sem exigir uma nova pesquisa ampla;
- código externo pode compor uma implementação subordinada aos contratos nativos;
  soberania do Core não exige autoria própria de cada linha;
- manter uma autoridade por responsabilidade e memória canônica única;
- uma absorção só avança com origem/versão/licença, teste ponta a ponta,
  comparação pertinente, observabilidade e rollback; estudo não é integração;
- registrar resultado e limitações na fila única e no HANDOFF; não declarar
  superioridade geral com base em um componente, demo ou contagem de testes.

## Política de linguagem

- runtime e interfaces técnicas novas devem convergir para inglês;
- documentação e texto humano podem permanecer em português;
- ids legados em português não devem ser expandidos por conveniência local.
