# ADR-002 (proposta): Autoevolução em duas frentes e promoção baseada em evidência

## Status

**Proposta para revisão arquitetural; não aceita.** Direção de produto registrada
em 2026-10-12. O registro dessa direção não aprova a sequência de implementação
ou a solução técnica aqui propostas. Aceitação ou rejeição exige decisão explícita
de revisão; implementação e promoção dependem também de itens próprios no backlog
e de seus gates. Este registro não habilita capacidades, permissões ou execução.

Enquanto proposta nesta PR, este texto pode receber ajustes de revisão e não deve
ser consumido como decisão canônica aceita ou registro imutável. A organização
imutável de ADRs descrita no [audit MB-151](../documentation/documentation-canonicality-audit-mb151.md)
é uma estrutura-alvo proposta, explicitamente não executada naquele lote; não
atribui aceitação automática a um arquivo por sua localização. Uma futura decisão
aceita deve registrar explicitamente seu status e preservar o histórico de revisão.

## Contexto

A visão é construir um agente completo inspirado no J.A.R.V.I.S. da ficção:
ajudar amplamente, compreender objetivos, planejar e executar trabalho autorizado,
compor ferramentas e ampliar suas capacidades ao longo do tempo. Essa ambição vai
além de um assistente convencional, mas não é promessa de AGI nem afirmação de
que toda capacidade já existe.

O [Documento Evolutivo](../architecture/documento_evolutivo_jarvis.md) reúne a
pesquisa; o [Technology Study](../architecture/technology-study.md) já prevê radar
contínuo e absorção governada. Falta tornar explícita a ligação entre essa visão,
a experiência operacional, a pesquisa externa e a comprovação de melhoria.

A [Constituição de Engenharia](../documentation/engineering-constitution.md)
permanece vinculante: Core, identidade, governança, memória canônica e síntese
final continuam soberanos. A ambição do produto não amplia autorização.

## Decisão proposta

### 1. Duas fontes de evolução, um processo de admissão

- **Experiência própria:** tarefas e resultados verificáveis, falhas, feedback,
  recorrência e uso anterior geram hipóteses de melhoria.
- **Avanços externos:** ferramentas, algoritmos, papers, releases e padrões são
  acompanhados continuamente, classificados e relacionados a necessidades do
  sistema antes de virar experimentos.

Nenhuma fonte produz autoridade de runtime. Conteúdo externo permanece dado não
confiável; instruções nele contidas não viram política, permissão ou comando.
O radar pode pesquisar horizontes futuros sem instalar ou adotar as tecnologias.

### 2. Ordem de implementação

1. **Skills, ferramentas e workflows:** memória procedural, composição,
   recuperação contextual, uso de ferramentas e refinamento de fluxos.
2. **Código e algoritmos:** geração de variantes e patches delimitados, executados
   em sandbox contra avaliadores independentes; publicação e promoção separadas.
3. **Pesos de modelos:** pesquisa em laboratório distinto, com infraestrutura,
   dados, licenças, compute, checkpoints e avaliação de retenção próprios.

Essa sequência cria pré-requisitos e reduz risco; não reduz a visão final.
A terceira etapa não é trocar apenas um prompt ou um modelo via API. Nenhuma
etapa autoriza o sistema a modificar livremente o Core.

### 3. Runtime e evolução separados

O runtime consome somente versões admitidas, pelo caminho soberano existente.
O plano de evolução observa, propõe, constrói candidatos e experimenta sem
alterar o comportamento ativo. Reaproveitar Evolution Lab, miner, registries e
serviços de memória existentes, evitando um novo cérebro ou store paralelo.

Fluxo-alvo, ainda não comprovado integralmente no baseline:

```text
resultado verificável / hipótese externa ligada a uma necessidade
  -> candidato proposto
  -> miner ou builder com contrato, escopo e proveniência
  -> sandbox executando baseline e candidato
  -> avaliação independente e evidências reproduzíveis
  -> revisão autorizada e admissão de versão
  -> consumo real pelo runtime
  -> monitoramento de ganho, regressão e custo
  -> retenção, desativação ou rollback
```

O proponente não escolhe sozinho o critério final de sucesso, não altera o
avaliador/holdout durante a avaliação, não aprova sua própria promoção e não
concede permissões ao candidato. Alterar o avaliador exige versão e revisão
independentes, separadas da tentativa que será julgada.

### 4. Contrato mínimo de evidência

Antes de experimentar, fixar:

- necessidade e hipótese falsificável; baseline e candidato identificados por
  versão, código/configuração e dependências;
- corpus representativo, critérios de sucesso e falha, métrica primária e
  limites de regressão, latência, custo e intervenção humana;
- separação entre exemplos usados para propor/refinar e holdout não utilizado
  na otimização; prevenção de vazamento e registro das limitações;
- isolamento, permissões mínimas, limites de tempo/tentativas/compute, condições
  de parada e tratamento explícito de erros ou resultados inconclusivos;
- trilha de origem: fonte e versão, dados permitidos, licença, responsáveis pela
  revisão, execução, avaliador e resultados; hash não substitui autenticação;
- comparação pareada, repetição adequada e incerteza declarada. Uma melhora em
  um exemplo não é ganho sustentado, e participação de guidance não é causalidade;
- retenção de capacidades anteriores e de conhecimento útil, incluindo testes
  após sucessivas admissões, para detectar esquecimento e deriva;
- plano de desativação/rollback com versão anterior recuperável e teste de
  restauração antes da promoção.

Autoavaliação pode sugerir hipóteses, mas não é a única prova. A avaliação
substantiva deve conferir o resultado da tarefa, e não somente ausência de erro,
formato, rota ou fragmentos esperados. Declarações manuais e fixtures continuam
rotuladas como tal.

### 5. Radar tecnológico contínuo

Evoluir a entrada manual existente por etapas, sem alterar retroativamente a
autoridade do MB-208 ou MB-209:

1. Definir catálogo de fontes primárias por necessidade: documentação e
   changelogs oficiais, releases de repositórios, papers e artefatos de autores.
   Registrar URL canônica, versão/data, licença e vínculo com a lacuna.
2. Projetar coleta somente leitura com cadências por fonte, orçamento de rede,
   armazenamento e análise, timeout, retry/backoff e tratamento de indisponibilidade.
   Persistir checkpoints e deduplicar por identidade, versão e conteúdo.
3. Distinguir descoberta automática de referência efetivamente revisada.
   Não fabricar aprovação humana para alimentar contratos que a exigem.
   Conteúdo não confiável passa por triagem antes de qualquer consumidor.
4. Comparar relevância, maturidade, licença, segurança de dependências,
   compatibilidade, custo total e ganho esperado. Registrar descarte ou adiamento
   e suas razões; novidade isolada não cria prioridade.
5. Traduzir o padrão útil em hipótese e contrato do JARVIS, com sandbox e
   avaliador definidos. Instalação, execução e acesso a dados exigem autorização
   própria; uma referência aceita no radar não a concede.
6. Executar experimentos reais comparáveis, admitir somente versões autorizadas
   e acompanhar releases posteriores, regressões, incompatibilidades e reversão.

As cadências e os tetos numéricos serão fixados no slice de implementação
conforme fontes e orçamento disponíveis. Este documento não cria scheduler,
monitoramento operacional ou autorização de coleta recorrente por si só.

## Estado observado e fronteiras

Referência documental: commit
`250b128ea3cee92a72ed88afef48d0fccb83e3fc`, revisado em 2026-10-12.

| Fundação existente | O que comprova | O que ainda não comprova |
|---|---|---|
| [Skill Candidate Registry, MB-177](../architecture/skill-candidate-registry.md) | Persistência e versionamento de candidatos inativos pelo memory-service | Ativação ou benefício operacional |
| [Bounded Skill Miner, MB-178](../architecture/bounded-skill-miner.md) | Compilação determinística de especificação explícita e evidência elegível | Descoberta autônoma de skills ou aprendizado substantivo |
| [Evolution Lab](../architecture/evolution-lab.md) | Propostas, comparações, review e caminhos governados existentes | Ciclo completo com ganho sustentado e promoção autônoma |
| [Radar MB-208](../technology/technology-radar-intake.md) | Registro versionado de referências revisadas manualmente | Fetch, verificação independente de fonte/licença ou radar contínuo |
| [Packs MB-209](../technology/technology-experiment-packs.md) | Métricas derivadas de observações pareadas pré-produzidas | Execução do candidato, reprodução do sandbox ou ganho causal |
| [Runner empírico](../../evolution/empirical_runner/README.md) | Execução de ports injetados e avaliador exato em quatro casos | Representatividade, holdout secreto, prova de modelo real ou inteligência geral |
| [Job service](../../services/job-service/README.md) | Ledger durável, worker fixture e piloto explícito do Core | Scheduler, executor genérico ou coleta contínua |

No runner, dois casos são repetidos e dois são holdout público, uma vez por
braço. Isso testa mecanismos; não autoriza extrapolar capacidade. Modos
declarados pelo operador e evidências por atestação requerem validação externa
adequada ao risco.

No [backlog](../implementation/execution-backlog.md), MB236 permanece bloqueado
para homologação com modelo real. O
[Engineering Gate do commit de referência](https://github.com/vthamada/jarvis/actions/runs/37708534221)
concluiu com falha. Recuperar um baseline validado e homologar inferência são
pré-condições para alegações que dependam disso. Esta PR não corrige esses
bloqueios nem declara avanço de capacidade.

## Fundamentos de pesquisa e tradução

As referências abaixo já integram o Documento Evolutivo. A tradução proposta
para o JARVIS é uma proposta arquitetural, não um resultado demonstrado pelos
papers neste repositório.

| Referência primária | Mecanismo | Aplicação e limite |
|---|---|---|
| [Reflexion](https://arxiv.org/abs/2303.11366) | Feedback verbal e memória episódica, sem atualizar pesos | Reflexão pós-tarefa ligada a resultado; texto de reflexão não prova melhoria |
| [AutoSkill](https://arxiv.org/abs/2603.01145) | Extrair, manter e recuperar skills a partir de interação, sem retreinar o modelo | Proponente e memória procedural; ainda exige validação, versionamento e política de dados |
| [Voyager](https://arxiv.org/abs/2305.16291) | Currículo, biblioteca de código executável e feedback do ambiente, sem fine-tuning do LLM | Skills composicionais; resultados em Minecraft não demonstram generalidade fora daquele ambiente |
| [AlphaEvolve](https://arxiv.org/abs/2506.13131) | Variantes de código propostas por LLMs e seleção evolutiva guiada por avaliadores | Evolução delimitada de algoritmos; depende da qualidade e do custo do avaliador |
| [SEAL](https://arxiv.org/abs/2506.10943) | Self-edits produzem dados/diretivas de fine-tuning e updates persistentes de pesos | Laboratório paramétrico com treinamento e avaliação downstream; não equivale a memória textual |
| [Transformer²](https://arxiv.org/abs/2501.06252) | Vetores especialistas treinados por RL modulam componentes singulares dos pesos na inferência | Adaptação paramétrica com acesso aos pesos; roteamento de especialistas do JARVIS é apenas analogia |

Não importar frameworks inteiros por associação de nomes. A
[ordem de absorção](../architecture/technology-absorption-order.md) e o
[framework de review](../architecture/technology-repository-review-framework.md)
continuam orientando absorção pequena, reversível e ligada a lacunas.

## Marcos propostos e critérios de aceite

Estes marcos são critérios para futura decomposição, não novos itens executáveis
nem promessa de prazo. O [execution-backlog](../implementation/execution-backlog.md)
continua sendo a fila canônica.

| Marco | Evidência necessária para aceite |
|---|---|
| Baseline confiável | Resolver e registrar falhas aplicáveis do gate; homologar inferência real quando requerida; preservar distinção fixture/Core/modelo e limitações |
| Radar contínuo somente leitura | Fontes, cadências e tetos definidos; evidência de coleta, retomada após falha e dedupe; toda referência com proveniência e triagem; nenhuma instalação ou execução implícita |
| Ciclo operacional de skills/tools/workflows | Uma necessidade real percorre proposta, miner/builder existente, comparação executada, review, versão admitida e consumo rastreável; candidato continua inativo antes da autorização |
| Melhoria demonstrada | Baseline/candidato avaliados em amostra e repetições definidas previamente, holdout separado, retenção, custo e regressões; ganho acima do limiar pré-registrado, ou resultado inconclusivo/rejeitado |
| Promoção e reversão | Decisão autorizada ligada à versão e evidências; implantação delimitada em trabalho próprio; rollback exercitado e monitoramento com condições de parada |
| Evolução de código/algoritmos | Patch restrito, sandbox reproduzível, avaliador independente e testes de compatibilidade/segurança; nenhuma alteração de testes para mascarar falha |
| Laboratório paramétrico | Modelo/dados licenciados, orçamento e infraestrutura próprios, checkpoints, avaliação downstream/holdout/retenção e reversão; sem alteração autônoma dos pesos do Core |

A passagem de um marco exige o anterior relevante; pesquisa pode ocorrer em
paralelo sem promover capacidade. Não se conclui um marco apenas pela existência
de um contrato, README, status ou score.

## Consequências

### Positivas

- preserva a ambição ampla com uma ordem verificável de construção;
- conecta experiência e avanço externo ao mesmo padrão de evidência;
- evita recriar fundações existentes ou confundir cadastro com aprendizado;
- torna custo, retenção, regressão e reversão parte da aceitação.

### Custos e limites

- exige manutenção de corpus, avaliadores, fontes e proveniência;
- avaliações reais e repetidas consomem orçamento e podem ser inconclusivas;
- revisão e admissão separadas limitam velocidade em troca de controle;
- adaptação de pesos demanda infraestrutura distinta e continua pesquisa.

## Não objetivos

- ativar coleta, scheduler, ferramentas, skills ou modelos nesta mudança;
- instalar dependências, alterar runtime, governança ou permissões;
- corrigir CI ou inferência nesta PR de documentação;
- prometer inteligência geral, autoaperfeiçoamento irrestrito ou autopromoção;
- substituir os documentos históricos, o backlog ou os gates de engenharia.
