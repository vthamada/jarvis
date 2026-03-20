# ADR-001: Absorção Parcial de LangGraph no Núcleo

## Status

Aceito

## Contexto

O Documento-Mestre define `LangGraph` como base principal de orquestracao stateful do JARVIS.

Ao mesmo tempo, o repositório atual já possui um baseline próprio funcional do `v1`, com:

- orquestracao central;
- memória persistente;
- governança;
- observabilidade;
- operação;
- ciclo deliberativo;
- especialistas subordinados internos.

Portanto, a decisão não e se `LangGraph` entra ou não. A decisão correta e **como ele entra sem desmontar um baseline funcional antes da hora**.

## Decisóo

`LangGraph` será absorvido de forma parcial e progressiva no núcleo do JARVIS.

Regra de absorção:

1. `LangGraph` entra como **substrato técnico de execução stateful**.
2. A arquitetura do JARVIS continua própria.
3. `shared/`, contratos, governança, memória e identidade não serão terceirizados ao framework.
4. A primeira adoção ocorrera por `POC` no fluxo do `orchestrator-service`, não por reescrita total do `v1`.

## O que deve ser reaproveitado

- checkpoints;
- durable execution;
- replay;
- time travel;
- pausas de `human-in-the-loop`;
- subgraphs para decomposicao do fluxo central.

## O que não será delegado ao LangGraph

- identidade do JARVIS;
- contratos canônicos;
- política de memória;
- política de governança;
- lógica de produto do núcleo;
- síntese final como decisão de sistema.

## Consequencias

### Positivas

- reduz custo de reescrever infraestrutura stateful manualmente;
- melhora debug, replay e controle operacional;
- aproxima o repositório da direção arquitetural canônica;
- prepara melhor o sistema para missóes multi-etapa e HITL.

### Negativas

- adiciona um novo substrato técnico no núcleo;
- exige desenho cuidadoso de limites entre framework e lógica própria;
- pode introduzir custo de migracao se for adotado cedo demais.

## Plano de entrada

1. endurecer `LangSmith` e a trilha observável do `internal pilot`;
2. executar o primeiro uso controlado do `v1`;
3. abrir `POC` de `LangGraph` no `orchestrator-service`;
4. medir ganho em:
   - replay;
   - fault tolerance;
   - HITL;
   - legibilidade do fluxo;
5. decidir a expansao ou não da adoção no núcleo.

## Não objetivos desta decisão

- não reescrever o baseline inteiro agora;
- não substituir a arquitetura do JARVIS por uma arquitetura prebuilt;
- não acoplar `LangGraph` a todo serviço antes de evidência real.
