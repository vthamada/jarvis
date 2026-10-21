# Harness²: avaliação para o JARVIS

Data: 2026-10-20. Classificação: **usar como referência** para F04
(autoevolução) e T02 (qualidade/utilidade); absorção experimental posterior.
Este estudo não instala o projeto, não altera o harness ativo e não promove
capability ou autoedição de produção.

## Conclusão

O Harness² é particularmente relevante à nossa visão autoevolutiva: ele separa
**o agente que resolve uma tarefa** do **processo que propõe e experimenta
melhorias no harness desse agente**. É mais próximo de um laboratório de
melhoria de harness do que de um novo assistente pessoal, modelo ou interface.

Vale absorver a disciplina de comparar execuções, guardar a hipótese e o efeito
observado, isolar avaliação da escolha e manter experiências anteriores
versionadas. Não vale habilitar o runtime externo como cérebro do JARVIS ou
permitir que um modelo altere nossas permissões, memória canônica e gates para
melhorar um placar. O código público contém decisões de pesquisa — inclusive
execução sem sandbox — incompatíveis com uma promoção direta ao nosso ambiente.

## Identidade e alcance da inspeção

- URL canônica: [google-research/harness2](https://github.com/google-research/harness2).
  O parâmetro `ref=producthunt` do link recebido é tracking; não foi interpretado
  como branch ou autorização.
- Repositório público confirmado pelo GitHub; revisão examinada:
  [`1cfe254e8d25b15f37048c3730134686abe60335`](https://github.com/google-research/harness2/commit/1cfe254e8d25b15f37048c3730134686abe60335),
  de 2026-10-14, mensagem `Fix arXiv link`. A árvore tinha 152 entradas, sem
  truncamento na resposta consultada.
- Inspeção estática de README/manifests/licenças, método, substrates, seleção,
  biblioteca, agenda/cache, avaliação, adapters dos três benchmarks e testes.
  Não foi uma auditoria integral de todas as dependências transitivas.
- Nenhuma instalação, execução de demo/teste externo, chamada de modelo,
  autenticação, download de dataset ou nova exposição de serviço foi realizada.
  Código e prompts externos foram tratados como dados, não instruções para este
  agente ou para o workspace.
- A [página do projeto](https://harness2.github.io) não estava acessível pelo
  leitor web nesta análise. Repositório e artigo primários estavam acessíveis;
  isso não foi tratado como inexistência do projeto.

## Artigo e evidência publicada

O [artigo v1](https://arxiv.org/html/2610.14224v1), submetido em 9 de outubro de
2026, descreve dois níveis: refinamento do harness na tarefa atual e uma
biblioteca de experiências que orienta refinamentos futuros, mantendo pesos do
modelo fixos. Relata três benchmarks, quatro configurações modelo–harness e
três execuções por condição principal; os ganhos máximos anunciados de um passo
são 11,5 pontos no WorkBuddy, 4,5 no JobBench e 11,8 pontos percentuais na medida
Partial do LAB. São resultados dos autores, não reproduzidos por nós e não uma
comparação contra o JARVIS. O próprio artigo ressalta custo adicional,
variabilidade e viés compartilhado do julgamento por modelo: contraste de
execução não garante correção nem transferência para outra tarefa.

Esses resultados motivam um experimento, não comprovam que o JARVIS ganhará a
mesma margem ou que este seja universalmente o melhor harness. A
[tabela de pins da release](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/dependencies/PINNED.md)
avisa que execuções históricas do artigo podem ter usado outras tarefas,
implantações de modelos e ferramentas locais. Rodar a release atual também não
é, por si só, reproduzir exatamente as tabelas publicadas.

## O que o código efetivamente implementa

| Camada | Evidência primária | Significado e limite |
| --- | --- | --- |
| Método separado do motor | [spec.py](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/spec.py) define contratos distintos para benchmark, substrate e canal de melhoria. | O otimizador usa agentes/modelos existentes; não fornece um modelo novo nem substitui inferência. |
| Propor, experimentar e compor | [recursion.py](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/recursion.py) cria candidatos gerais e de domínio, executa probes e composições em modos paralelo/sequencial. | Há pipeline executável real. Proposta inválida recebe nova tentativa limitada e pode cair no harness anterior; isso não prova segurança do candidato válido. |
| Superfície editável | [tree.py](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/tree.py) limita caminhos, tamanho always-on, frontmatter, referências a scripts e forma de hooks; verifica compilação Python. | São verificações de formato/compatibilidade, não uma sandbox ou prova de ausência de código malicioso. |
| Seleção | [selection.py](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/selection.py#L93) monta pool de finais e compara entregáveis anonimizados. | A escolha seleciona uma saída existente. Não é síntese final soberana do JARVIS nem certificado de melhoria. |
| Aprendizado entre tarefas | [library.py](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/library.py) mantém harness adotado, experiência e índice por domínio. [schedule.py](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/schedule.py#L669) restringe a biblioteca ao prefixo de tarefas anteriores. | É memória de experimentos do melhorador, não mudança de pesos nem memória canônica de usuário. A atribuição causal continua dependendo da evidência e interpretação. |
| Avaliação independente da escolha | [judge.py](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/judge.py) mede a execução já selecionada e mantém falhas de juiz sem pontuação. | Otimização online sem gabarito não significa benchmark sem avaliador. Ausência de nota não é zero nem aprovação. |
| Contaminação de contexto | [context.py](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/context.py#L399) filtra caminhos de gabarito e padrões de veredictos. Os adapters retiram critérios/artefatos de avaliação do material do melhorador. | Controle útil, porém não exaustivo: glob/marker não impede obtenção do gabarito por uma rede aberta ou toda forma de prompt injection. |
| Identidade e retomada de experimento | [runmark.py](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/runmark.py) registra conclusão explícita e fingerprint; [run_sweep.py](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/cli/run_sweep.py) recusa misturar modelos/tarefas na mesma configuração salva. | É cache/resume experimental, não journal/fencing ou exactly-once genérico de efeitos externos. Fingerprint curto de cache não equivale a atestação. |

As oito famílias editáveis abrangem instruções, guardrails, memória de domínio,
orientação de ferramentas, subagentes, skills, scripts e middleware. No JARVIS,
essa lista não pode ser importada como permissão para editar as oito famílias:
constituição, governança, política de memória e síntese ficam fora da superfície
do melhorador.

### Dois cuidados que mudam nossa adoção

1. O [pool publicado](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/selection.py#L93)
   **exclui os baselines**. Com `k=1`, a seleção é trivial sobre o único final.
   Portanto, adoção não significa ter vencido a configuração anterior, e a
   estrela de “adotado” não significa ótimo verificado. Para produção no JARVIS,
   é indispensável poder manter o baseline ou recusar todos os candidatos.
2. A [biblioteca](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/library.py#L51)
   exige campos de experiência presentes e bloqueia certos marcadores de juiz;
   não contém uma prova mecânica de que a lição é causal ou generalizável.
   “Selecionado”, “ajudou neste caso”, “efeito confundido” e “promovido para uso”
   precisam permanecer estados distintos no JARVIS.

## Custo e pré-requisitos reais

O [ledger](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/ledger.py)
conta, por tarefa/modo, **4k rollouts de execução e 3k sessões de melhoria**.
Seleção/reflexão ficam fora dessa identidade; tentativas adicionais são
registradas à parte. Uma sessão pode conter várias chamadas ao modelo.
Consequentemente, `k=1` não significa uma chamada nem um teto total de sete
chamadas de inferência. O teto precisa incluir todos os executores, editores,
seletores, reflexores, juízes e retries antes de autorizar uma campanha.

Segundo o [setup](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/docs/SETUP.md)
e o [manifest](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/pyproject.toml):

- Experimentos suportados usam Linux, Python 3.12/3.13, ferramentas de setup e
  Node; não é promessa de suporte nativo a este Windows.
- LAB acrescenta Pandoc/Poppler; WorkBuddy requer Docker, imagens e datasets.
- As rotas públicas documentadas usam modelos configurados e credenciais
  próprias, normalmente Vertex ADC/projeto com acesso aos modelos. O executor
  Codex usa um endpoint Responses; o bridge opcional usa LiteLLM/Vertex.
- O bridge WorkBuddy pode ouvir em todas as interfaces para atender containers;
  precisa isolamento de rede próprio. Não configura nem resolve automaticamente
  a conta OAuth ou o Ollama já escolhidos para o JARVIS.
- A demo não requer credenciais, mas executa Python real com editores
  determinísticos; não prova capacidade de um modelo real ou segurança de
  scripts gerados. Ela não foi executada nesta análise.
- O checkout fixado não contém `.env.example`, embora README/manifest o
  mencionem. É um gap de documentação/empacotamento observado na árvore, não um
  diagnóstico obtido por tentativa de instalação. As variáveis estão no setup.

As autorizações antigas dos pilotos locais/OAuth do JARVIS não abrangem esta
campanha externa, novas contas, gastos, downloads ou alterações de acesso.

## Segurança e confiabilidade: o que não copiar

O [substrate Codex](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/substrate/codex.py#L157)
desativa aprovações/sandbox e confiança de hooks. O caminho
[Claude do melhorador](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/proposer.py#L210)
também inicia com permissões puladas. Diretório temporário com contexto isolado
não é isolamento de kernel, e a checagem de sintaxe não limita efeitos de um
script/plugin executado pelo agente.

O [guia de experimentos](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/docs/EXPERIMENTS.md#web-access)
declara rede irrestrita e relata que, numa validação da release, uma execução
Codex baixou a rubric pública da própria tarefa sem solicitação. Isso **não
prova que as tabelas do artigo estejam contaminadas**; demonstra um risco real
de usar a release sem restrição de egress. Retirar arquivos locais de avaliação
do contexto não resolve esse outro canal.

Para qualquer experimento futuro:

- ambiente descartável sem credenciais/arquivos pessoais ou sockets do host;
- setup separado da execução: downloads permitidos não viram egress amplo do
  executor; gabaritos/juízes permanecem fora da rede e dos mounts do candidato;
- superfície de edição mínima, sem permissões, políticas, registries, memória
  canônica ou alteração dos testes que decidem a promoção;
- scripts/hooks apenas como propostas até revisão e execução restrita explícita;
- artefatos redigidos, namespaces imutáveis, cancelamento, orçamento global e
  rollback; nenhuma operação externa incerta pode ser repetida para “probar”;
- dataset/modelo/endpoint/versões/seed/egress e tarefas sem nota reportados
  separadamente. Melhor média com menor cobertura não pode esconder falhas.

Os [testes incluídos](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/tests/test_workflow.py)
cobrem aspectos como orçamento/resume, prefixo da biblioteca, proposta inválida
e falha de seleção. Combinam demo determinística e mocks em fronteiras. Não
foram rodados; sua existência não comprova que toda a matriz externa funciona
neste host nem que o sandbox é seguro.

## Relação com REA, OpenMausBot e JARVIS

| Projeto | Papel observado | Uso adequado nesta arquitetura |
| --- | --- | --- |
| REA | Inspecionar e estruturar evidência sobre aplicações/artefatos | Instrumento de investigação. A ponte atual do JARVIS importa projeção estática como dado não verificado; não concede autoridade ao produtor. |
| OpenMausBot | Produto/harness operacional com motores, eventos, UI, approvals e computadores | Referência de execução e experiência de usuário; não cérebro substituto. Ver [estudo próprio](openmausbot-assessment-2026-10-20.md). |
| Harness² | Melhorador de configurações de harness por experiências comparadas | Referência de laboratório para F04/T02, separada do runtime que atende o usuário. |
| JARVIS | Core soberano com governança, memória canônica, final e capacidades mediadas | Dono das autorizações e promoção. Pode consumir propostas/evidências dos três sem terceirizar essas decisões. |

REA pode ajudar a ler um sistema; OpenMausBot mostra como operá-lo como produto;
Harness² mostra como experimentar melhorias. Essa combinação é uma inferência
arquitetural nossa, não uma integração já demonstrada entre esses projetos.

O ponto de encaixe do JARVIS já existe no
[Operator Learning Loop](../operations/operator-learning-loop.md): experiência,
reflexão bounded, proposta em `needs_review`, revisão com evidência/testes/rollback
e medição baseline versus assisted. A contribuição do Harness² deve fortalecer
essa cadeia existente com contrastes de execução e condições de transferência,
não criar outra memória factual nem substituir o serviço de evolução. Aprovar
uma proposta, influenciar uma execução e autorizar uma promoção continuam
decisões separadas; sandbox verde não altera essa fronteira.

## Sequência concreta recomendada

| Classificação | Recorte | Aceite antes de avançar |
| --- | --- | --- |
| Usar como referência agora | Registrar hipótese → mudança mínima → contraste observável → resultado, incluindo efeito confundido/ausente | Nada muda no runtime só por uma reflexão. Vincular a um caso real e evidência, sem editar o oráculo |
| Absorver depois — T02 | Comparador baseline/candidato no corpus real já priorizado | Mesmas tarefas/ambiente/orçamento, controle sem mudança, baseline elegível, juiz cego e falhas visíveis; não somente qualidade textual |
| Absorver depois — F04 | Biblioteca de experiências com condição de uso, versões, evidência e rejeições | Não registrar preferências/hipóteses como fatos canônicos; avaliar transferência em tarefas separadas e manter rollback |
| Absorver depois — F01/F04 | Propostas restritas de instrução/ferramenta para erros comprovados de continuação | Primeiro conversa real termina e segunda interação usa memória; depois medir latência, qualidade e não regressão sem ampliar permissões |
| Rejeitar na produção atual | Execução sem sandbox, rede ampla, autopromoção, políticas editáveis ou escolha obrigatória de candidato | Incompatível com nossa constituição e com as autorizações vigentes |

O primeiro experimento útil não é “deixar o JARVIS reescrever tudo”. É comparar
uma única melhoria pequena de continuação/finalização contra a versão anterior,
em ambiente controlado, reservando finalização e respeitando o mesmo orçamento.
Depois, retenção e reutilização de uma lição devem melhorar outra tarefa, não
somente repetir a que gerou a lição. Esses são os dois aceites que tornam a
visão autoevolutiva verificável em vez de apenas uma narrativa.

## Viabilidade técnica confirmada no JARVIS

A inspeção do código local confirma pontos de encaixe, não uma integração
executada. A absorção do método pode reutilizar estas APIs existentes:

- `evals.operator_tasks.mission_corpus`: `MISSIONS`, `get_mission` e campos de
  `Mission`; `runner`: `Binding`, `ExecutionRequest` e `ExecutionResult`.
- `CanonicalMissionTaskPort.execute` e `snapshot`: Core isolado, fonte revisada,
  final canônica/readback e contadores, sem reparar o produto para o avaliador.
- `CampaignArm`, `CampaignBudget`, `MissionCampaign.run` e
  `CampaignReport.export_metrics`: dois braços, ordem alternada e denominadores
  que preservam recusas, falhas e capabilities não disponíveis.
- `CampaignInferenceGuard.infer` e `snapshot`: teto compartilhado de tentativas
  de inferência quando explicitamente composto, sem renovação ou fallback.

`CampaignBudget.max_calls` aceita somente `1`; o relatório declara que o
orçamento interno não foi verificado. Esse limite de despacho não contabiliza
automaticamente os executores, melhoradores, seletores e reflexores do Harness².
As 25 missões `dev/probe` são públicas: não equivalem a holdout secreto ou a
uma avaliação independente ainda não vista pelo melhorador.

Para integração real do framework externo seria necessário um `BenchmarkAdapter`
JARVIS (`tasks`, `domain_of`, `task_prompt`, `execute`, `trajectory`,
`deliverable_*`, `validate_tree`, `score`) e um substrate de edição restrita.
Nenhuma dessas interfaces autoriza modificar Core, permissões ou memória.
O comparador traduzido precisa manter baseline elegível e permitir rejeitar
todas as candidatas, sem confundir seleção, melhoria observada e promoção.

O Evolution já oferece `register_technology_experiment_pack`,
`claim_technology_experiment_eval_run` e `record_technology_experiment_eval_run`.
O pack MB-209 é inerte e exige `network_disabled` e `external_code_not_executed`;
não pode atestar honestamente uma execução externa com rede como se satisfizesse
esse isolamento. A execução do framework não foi aprovada nem realizada nesta
rodada; permanece separada da absorção do método e exige experimento próprio.

## Licença e estado final

O núcleo usa [Apache-2.0](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/LICENSE).
[Terceiros e datasets](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/dependencies/README.md)
têm termos próprios; o texto distribuído da
[licença WorkBuddy](https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/third_party/licenses/workbuddy-bench.LICENSE)
inclui limitação territorial referente à União Europeia. Não tratar o pacote
inteiro como apenas Apache, nem baixar/importar dados automaticamente.
O projeto se declara pesquisa, não produto Google oficialmente suportado.

Estado deste recorte: **análise estática concluída, sem teste de execução ou
promoção de Harness²**. Nenhuma nova dependência, conta, serviço, gasto,
autoedição ou acesso de rede foi habilitado no JARVIS.
