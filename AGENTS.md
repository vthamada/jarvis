# AGENTS

Este repositório exige implementação disciplinada, mas não burocrática.

Toda mudança feita por agente deve seguir a
[Constituição de Engenharia](d:/Users/DTI/Desktop/jarvis/docs/documentation/engineering-constitution.md).

Leitura correta:

- use as regras como guardrails mínimos;
- aplique rigor em proporção ao risco;
- não troque implementação por ritual.

## Regras obrigatórias

- preserve a soberania do núcleo;
- não bypassar governança, memória canônica ou síntese final;
- preferir mudanças pequenas, reversíveis e auditáveis quando suficientes;
- não promover capability sem teste, observabilidade e documentação;
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
