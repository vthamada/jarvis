# Documento Evolutivo do J.A.R.V.I.S.

**Data:** 13/05/2026  
**Objetivo:** consolidar a linha de pesquisa sobre autoevolução, continual learning, self-evolving agents e self-adapting language models, traduzindo essas ideias para a arquitetura do J.A.R.V.I.S.

---

## 0. Papel deste documento no projeto

Este documento é uma referência arquitetural e de pesquisa para a camada
evolutiva do J.A.R.V.I.S.

Ele não substitui:

- o [Documento-Mestre](../../documento_mestre_jarvis.md);
- o [execution-backlog](../implementation/execution-backlog.md);
- o [unified-gap-and-absorption-backlog](../implementation/unified-gap-and-absorption-backlog.md);
- a Constituição de Engenharia;
- os gates de validação do repositório.

Leitura correta:

- a visão evolutiva aqui descrita orienta decisões futuras;
- qualquer implementação deve ser fatiada no `execution-backlog.md`;
- nenhuma capacidade evolutiva pode bypassar Core, governança, memória canônica,
  síntese final, testes, observabilidade ou rollback;
- os estudos externos são insumos de tradução disciplinada, não autorização para
  substituir o cérebro soberano do sistema.

Estado atual em 2026-05-17:

- o projeto já possui partes da fundação evolutiva em `evolution-lab`,
  observabilidade, comparadores, verificadores de baseline/release, memória
  guiada, gates e registros de refinamento;
- os lotes `MB-110` a `MB-119` fecharam a continuidade minima e a primeira
  camada utilizavel de projetos/objetivos para operador humano;
- o lote ativo agora e `MB-120` a `MB-125`, focado em estrutura evolutiva e
  absorcao tecnologica governada;
- `MB-121` ja materializou o contrato minimo de candidato tecnologico:
  tecnologia externa entra como referencia, experimento, complemento controlado
  ou traducao promovivel, sempre subordinada ao nucleo e sem promocao automatica;
- `MB-122` conectou esse contrato ao `evolution-lab`, mantendo candidatos
  tecnologicos como propostas `sandbox-only` ate revisao humana baseada em
  evidencia;
- `MB-123` a `MB-125` fecharam a primeira camada operacional dessa absorcao:
  observabilidade, relatorio, comparador e console tornam candidatos visiveis
  sem promover, executar ou substituir o nucleo.
- `MB-126` abriu a proxima repriorizacao evolutiva: experiencia operacional e
  reflexao pos-tarefa governada. A intencao e transformar missoes reais em
  registros estruturados de outcome, falhas, decisoes, evidencias e aprendizados
  candidatos, ainda sem self-modification, autopromocao ou alteracao de pesos.
- `MB-127` a `MB-131` fecharam esse recorte, levando
  `experience_record`/`post_task_reflection` para contratos, memoria evolutiva
  bounded, `evolution-lab`, observabilidade, relatorio e console read-only.
- este documento deve alimentar próximas repriorizações, mas não muda sozinho a
  fila ativa.

---

## 1. Tese central

O J.A.R.V.I.S. pode ser evolutivo com as tecnologias atuais, mas a evolução deve ser implementada por camadas.

A abordagem correta não é permitir que o sistema se modifique livremente.

A abordagem correta é:

> O J.A.R.V.I.S. observa sua própria operação, registra experiências, reflete sobre resultados, consolida padrões, propõe melhorias, testa em sandbox, promove mudanças aprovadas e mantém rollback.

Isso permite evolução realista sem comprometer identidade, governança e confiabilidade.

---

## 2. O que significa “evoluir” no J.A.R.V.I.S.

Evoluir não significa apenas trocar modelo ou fazer fine-tuning.

No contexto do J.A.R.V.I.S., evolução pode significar:

- melhorar memória;
- melhorar roteamento;
- melhorar escolha de especialistas;
- criar skills reutilizáveis;
- refinar workflows;
- reduzir erros recorrentes;
- melhorar respostas;
- consolidar experiência;
- ajustar policies;
- propor mudanças estruturais;
- testar melhorias antes de promover.

---

## 3. Níveis de evolução

### Nível 1 — Memória evolutiva

O sistema registra e reaproveita experiências.

Exemplos:
- preferências do usuário;
- decisões anteriores;
- padrões de projeto;
- falhas e correções;
- contexto de missão;
- histórico de especialistas usados.

**Maturidade:** alta.  
**Uso recomendado:** V1.

---

### Nível 2 — Reflexão pós-tarefa

O sistema analisa o que aconteceu depois de uma missão.

Perguntas:
- o plano funcionou?
- houve erro recorrente?
- a memória usada foi adequada?
- o especialista escolhido foi correto?
- alguma regra precisa ser criada?
- algo deve virar skill?

**Maturidade:** alta.  
**Uso recomendado:** V1/V2.

---

### Nível 3 — Skill evolution

O sistema transforma padrões recorrentes em skills.

Exemplos:
- uma rotina de análise vira skill;
- um processo de release vira playbook;
- uma correção recorrente vira procedimento;
- um fluxo de pesquisa vira template.

**Maturidade:** alta.  
**Uso recomendado:** V2.

---

### Nível 4 — Evolução de workflow

O sistema melhora sequências de execução.

Exemplos:
- ajustar checkpoints;
- trocar ordem de ferramentas;
- criar workflow_profile;
- comparar versões de fluxo;
- promover o fluxo mais eficaz.

**Maturidade:** média/alta.  
**Uso recomendado:** V2.

---

### Nível 5 — Roteamento adaptativo

O sistema aprende a escolher melhor:

- rota;
- domínio;
- mente cognitiva;
- especialista;
- ferramenta;
- nível de autonomia.

**Maturidade:** média/alta.  
**Uso recomendado:** V2.

---

### Nível 6 — Evolução estrutural supervisionada

O sistema propõe mudanças estruturais, mas não aplica sozinho.

Exemplos:
- novo especialista;
- novo registry;
- novo contrato;
- novo sinal observável;
- novo gate;
- novo serviço.

**Maturidade:** média.  
**Uso recomendado:** V2/V3 com human-in-the-loop.

---

### Nível 7 — Adaptação paramétrica isolada

O sistema pode adaptar componentes estreitos.

Exemplos:
- classificador de intenção;
- roteador de especialistas;
- ranker de memória;
- avaliador de risco;
- modelo pequeno especializado.

**Maturidade:** média/baixa.  
**Uso recomendado:** V3, sempre isolado e validado.

---

### Nível 8 — Autoevolução profunda do núcleo

O núcleo central altera pesos, comportamento profundo ou arquitetura central de forma contínua.

**Maturidade:** baixa.  
**Uso recomendado:** apenas pesquisa.

---

## 4. Mapa de maturidade

| Camada | Maturidade | Fase |
|---|---|---|
| Memória evolutiva | Alta | V1 |
| Reflexão pós-tarefa | Alta | V1/V2 |
| Skills reutilizáveis | Alta | V2 |
| Workflow evolution | Média/Alta | V2 |
| Roteamento adaptativo | Média/Alta | V2 |
| Mudança estrutural supervisionada | Média | V2/V3 |
| Fine-tuning isolado | Média/Baixa | V3 |
| Autoevolução do núcleo | Baixa | Pesquisa |

---

# 5. Estudos e papers relevantes

## 5.1 Surveys e mapas do campo

### A Survey of Self-Evolving Agents: On Path to Artificial Super Intelligence

**Link:** https://arxiv.org/abs/2507.21046

Organiza self-evolving agents em três perguntas:

- o que evolui;
- quando evolui;
- como evolui.

**Inspiração para o J.A.R.V.I.S.:**
- criar taxonomia oficial de evolução;
- diferenciar evolução de memória, tools, skills, arquitetura e modelo;
- impedir que “autoevolução” vire conceito vago.

---

### A Comprehensive Survey of Self-Evolving AI Agents

**Link:** https://arxiv.org/abs/2508.07407

Apresenta self-evolving agents como ponte entre foundation models estáticos e sistemas lifelong.

**Inspiração para o J.A.R.V.I.S.:**
- tratar o sistema como agente que aprende com ambiente e feedback;
- evoluir configurações, memória, workflows e habilidades.

---

### Continual Learning in Large Language Models: Methods, Challenges, and Opportunities

**Link:** https://arxiv.org/abs/2603.12658

Survey sobre continual learning em LLMs.

Tópicos:
- continual pre-training;
- continual fine-tuning;
- continual alignment;
- catastrophic forgetting.

**Inspiração para o J.A.R.V.I.S.:**
- entender riscos de adaptação de pesos;
- manter núcleo estável;
- preferir evolução operacional antes de evolução paramétrica.

---

### The Future of Continual Learning in the Era of Foundation Models

**Link:** https://arxiv.org/abs/2506.03320

Defende três direções:
- continual pre-training;
- continual fine-tuning;
- continual compositionality.

**Inspiração para o J.A.R.V.I.S.:**
- reforça a ideia de evolução por composição;
- favorece especialistas, tools e workflows em vez de um núcleo que muda sozinho.

---

## 5.2 Self-adapting language models

### Self-Adapting Language Models — SEAL

**Link:** https://arxiv.org/abs/2506.10943  
**Código:** https://github.com/Continual-Intelligence/SEAL

Ideia central:
- LLMs são poderosos, mas estáticos;
- o modelo gera self-edits;
- self-edits podem incluir dados de fine-tuning e diretivas de update;
- updates persistentes são avaliados por desempenho downstream.

**O que inspira no J.A.R.V.I.S.:**
- self-edit como proposta de evolução;
- validação antes da promoção;
- evolução por evidência.

**O que não copiar no V1:**
- alteração livre de pesos do núcleo.

---

### Search over Self-Edit Strategies for LLM Adaptation

**Link:** https://arxiv.org/pdf/2601.14532

Estuda quais estratégias de self-edit funcionam melhor.

**Inspiração para o J.A.R.V.I.S.:**
- comparar estratégias evolutivas;
- criar Evolution Lab;
- medir qual tipo de mudança realmente melhora o sistema.

---

### Self-Consolidating Language Models — SCoL

**Link:** https://arxiv.org/html/2605.07076v1

Propõe consolidação paramétrica compacta, como updates LoRA em partes selecionadas.

**Inspiração para o J.A.R.V.I.S.:**
- adaptação isolada em subsistemas;
- não aplicar no núcleo central no início.

---

### Transformer-Squared: Self-adaptive LLMs

**Link:** https://arxiv.org/abs/2501.06252  
**Código:** https://github.com/SakanaAI/self-adaptive-llms

Ideia central:
- adaptação em tempo de inferência;
- identificação de propriedades da tarefa;
- mistura dinâmica de vetores especialistas.

**Inspiração para o J.A.R.V.I.S.:**
- roteamento adaptativo;
- mind_registry;
- domain_registry;
- escolha dinâmica de modo cognitivo.

---

## 5.3 Self-evolving agents e lifelong learning

### Building Self-Evolving Agents via Experience-Driven Lifelong Learning

**Link:** https://arxiv.org/abs/2508.19005  
**Site:** https://ecnu-icalk.github.io/ELL-StuLife/

Propõe Experience-driven Lifelong Learning.

Pilares:
- Experience Exploration;
- Long-term Memory;
- Skill Learning;
- Knowledge Internalization.

**Inspiração para o J.A.R.V.I.S.:**
- base conceitual do EvolutionOS;
- experiência como matéria-prima da evolução;
- memória e skills como caminho principal.

---

### Experience-Driven Lifelong Learning via Skill Self-Evolution

**Link:** https://arxiv.org/html/2603.01145v2

Transforma experiências de interação em skills reutilizáveis.

Ciclo:
- extração;
- representação;
- refinamento;
- recuperação;
- compartilhamento.

**Inspiração para o J.A.R.V.I.S.:**
- skill_registry;
- extração de skills a partir de missões reais;
- lifecycle de skill.

---

### EvolvingAgent: Curriculum Self-evolving Agent with Continual World Model

**Link:** https://arxiv.org/abs/2502.05907

Agente com curriculum learning e world model contínuo.

**Inspiração para o J.A.R.V.I.S.:**
- missões longas;
- planejamento com experiência;
- world model como horizonte futuro.

---

### Self-Consolidation for Self-Evolving Agents

**Link:** https://arxiv.org/abs/2602.01966

Problema tratado:
- agentes acumulam muita experiência textual;
- memória cresce, fica ruidosa e consome contexto;
- é preciso consolidar padrões.

**Inspiração para o J.A.R.V.I.S.:**
- memory consolidation;
- compressão de experiência;
- aprendizado a partir de falhas, não só sucessos.

---

### Rethinking Experience Utilization in Self-Evolving Language Model Agents

**Link:** https://arxiv.org/abs/2605.07164

Ideia central:
- não basta armazenar experiência;
- o sistema precisa saber quando usar experiência.

**Inspiração para o J.A.R.V.I.S.:**
- memory_relevance_gate;
- uso seletivo de memória;
- evitar injetar contexto em excesso.

---

### Do Self-Evolving Agents Forget?

**Link:** https://arxiv.org/pdf/2605.09315

Investiga degradação de capacidades em agentes autoevolutivos.

**Inspiração para o J.A.R.V.I.S.:**
- regression testing evolutivo;
- medir se uma evolução piorou algo;
- impedir deriva de capacidade.

---

## 5.4 Reflexão, memória e comportamento

### Reflexion: Language Agents with Verbal Reinforcement Learning

**Link:** https://arxiv.org/abs/2303.11366  
**Código:** https://github.com/noahshinn/reflexion

Agentes melhoram por reflexão textual e memória episódica, sem alterar pesos.

**Inspiração para o J.A.R.V.I.S.:**
- post_task_reflection;
- memória de erros e sucessos;
- reflexão estruturada após missões.

---

### Generative Agents: Interactive Simulacra of Human Behavior

**Link:** https://arxiv.org/abs/2304.03442

Arquitetura com:
- memória;
- reflexão;
- planejamento.

**Inspiração para o J.A.R.V.I.S.:**
- sintetizar memórias em inferências;
- planejar comportamento com base em memória;
- criar continuidade narrativa.

---

### Voyager: An Open-Ended Embodied Agent with Large Language Models

**Link:** https://arxiv.org/abs/2305.16291  
**Site:** https://voyager.minedojo.org/

Agente que aprende em Minecraft com:
- currículo automático;
- skill library;
- feedback do ambiente;
- melhoria iterativa.

**Inspiração para o J.A.R.V.I.S.:**
- skill library;
- skills composicionais;
- aprendizado sem fine-tuning.

---

## 5.5 Autoaperfeiçoamento de código e scaffolds

### Self-Taught Optimizer — STOP

**Link:** https://arxiv.org/abs/2310.02304  
**Página:** https://www.microsoft.com/en-us/research/publication/self-taught-optimizer-stop-recursively-self-improving-code-generation/

Mostra um scaffolding program usando LLM para melhorar programas e depois melhorar a si mesmo.

**Inspiração para o J.A.R.V.I.S.:**
- evolução de scaffolds;
- melhorias em DevOS;
- autoaperfeiçoamento supervisionado de workflows.

---

### AlphaEvolve

**Link:** https://arxiv.org/abs/2506.13131  
**Blog:** https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/

Agente evolutivo de código:
- LLMs propõem mudanças;
- avaliadores testam;
- melhores variantes são selecionadas.

**Inspiração para o J.A.R.V.I.S.:**
- Evolution Lab;
- loops de melhoria com avaliadores;
- evolução de algoritmos e workflows técnicos.

---

### Agent0: Unleashing Self-Evolving Agents from Zero Data

**Link:** https://arxiv.org/html/2511.16043v1

Framework experimental de evolução sem dados externos.

**Inspiração para o J.A.R.V.I.S.:**
- autoaprendizagem em ambiente simulado;
- criação de currículos;
- pesquisa futura.

---

## 5.6 Autoavaliação e recompensa

### Self-Rewarding Language Models

**Link:** https://arxiv.org/abs/2401.10020

Modelos usam avaliações próprias como recompensa para melhorar.

**Inspiração para o J.A.R.V.I.S.:**
- evaluator interno;
- autoavaliação estruturada;
- comparação de respostas.

**Risco:**
- viés de autoavaliação;
- reward hacking;
- falsa sensação de qualidade.

---

# 6. Proposta arquitetural: EvolutionOS

## 6.1 Nome do subsistema

Sugestões:
- EvolutionOS;
- Evolution Service;
- Self-Improvement Layer;
- Learning Operations Layer.

Recomendação:
> EvolutionOS

---

## 6.2 Papel do EvolutionOS

O EvolutionOS não substitui o Core.

Ele observa e melhora o sistema de forma governada.

No baseline atual, EvolutionOS deve ser entendido como uma camada lógica
composta por serviços e ferramentas já existentes, não necessariamente como um
novo serviço monolítico.

Responsabilidades:

1. coletar experiências;
2. gerar reflexões;
3. detectar padrões;
4. sugerir memórias;
5. sugerir skills;
6. sugerir workflows;
7. sugerir ajustes de roteamento;
8. testar melhorias em sandbox;
9. promover mudanças aprovadas;
10. registrar versões;
11. permitir rollback.

---

## 6.2.1 Correspondência com o baseline atual

| Conceito do EvolutionOS | Correspondente atual | Status |
|---|---|---|
| Experience Collector | eventos do `orchestrator-service`, piloto interno, `internal_pilot_report`, comparadores | parcial |
| Reflection Engine | sinais de refinamento em `evolution_from_pilot`, `evolution-lab` e relatórios | parcial |
| Experience Store | `memory-service`, checkpoints, replay, artefatos de piloto e histórico regenerável | parcial |
| Skill Miner | ainda não materializado como registry de skills candidatas | futuro |
| Skill Registry | não existe como registry soberano dedicado | futuro |
| Workflow Evolution Engine | `evolution-lab`, `compare_orchestrator_paths`, `verify_release_signal_baseline` | parcial |
| Routing Adaptation Engine | `domain_registry`, `mind_registry`, sinais de especialista e refinamento por workflow | parcial |
| Evaluator | gates, pilotos, comparadores, observabilidade e testes automatizados | parcial/ativo |
| Promotion Gate | `engineering_gate`, release gate, verificadores de baseline/release | ativo |
| Rollback Manager | ainda depende de Git, changelog, docs vivos e reversibilidade de lotes | futuro |

Implicação arquitetural:

- antes de criar um serviço novo chamado `EvolutionOS`, o projeto deve consolidar
  contratos compartilhados para experiência, reflexão, candidato evolutivo,
  evidência, promoção e rollback;
- qualquer novo registry evolutivo deve nascer subordinado aos registries
  soberanos existentes;
- a evolução precisa consumir evidência operacional real, não apenas intenção ou
  sugestão textual.

---

## 6.3 Componentes internos

### Experience Collector

Coleta:
- missão;
- intenção do usuário;
- rota;
- workflow_profile;
- mente primária;
- domínio;
- especialista;
- plano;
- tools;
- resultado;
- erros;
- feedback;
- custo;
- tempo;
- risco.

---

### Reflection Engine

Produz reflexão estruturada:

- o que funcionou;
- o que falhou;
- o que deve ser repetido;
- o que deve ser evitado;
- que memória deve ser criada;
- que skill pode ser candidata;
- que workflow deve mudar.

---

### Experience Store

Armazena experiências consultáveis.

Pode usar:
- PostgreSQL;
- pgvector;
- arquivos de auditoria;
- vínculos com mission_id;
- vínculos com memory_registry.

---

### Skill Miner

Detecta padrões que podem virar skills.

Exemplos:
- tarefas repetidas;
- correções recorrentes;
- sequências estáveis;
- prompts internos recorrentes;
- workflows repetidos com sucesso.

---

### Skill Registry

Registra skills formalmente.

Campos sugeridos:
- skill_id;
- name;
- domain;
- specialist_type;
- inputs;
- outputs;
- tools_allowed;
- risk_level;
- version;
- status;
- evidence;
- rollback_policy.

---

### Workflow Evolution Engine

Compara versões de workflows.

Pode propor:
- novo checkpoint;
- novo done criteria;
- novo workflow_profile;
- nova ordem de execução;
- remoção de passos inúteis.

---

### Routing Adaptation Engine

Aprende roteamento melhor.

Pode sugerir ajustes em:
- primary_route;
- workflow_profile;
- primary_mind;
- primary_domain_driver;
- linked_specialist_type.

---

### Evaluator

Avalia se uma mudança melhorou o sistema.

Métricas:
- sucesso;
- custo;
- latência;
- retrabalho;
- intervenção humana;
- erro recorrente;
- aderência ao contrato;
- regressão;
- segurança.

---

### Promotion Gate

Controla promoção.

Estados:
- observed;
- candidate;
- sandboxed;
- validated;
- promoted;
- deprecated;
- rolled_back.

---

### Rollback Manager

Permite reverter:
- skill;
- workflow;
- prompt;
- regra;
- política;
- memória procedural.

---

# 7. Ciclo evolutivo recomendado

```text
Executar missão
   ↓
Registrar experiência
   ↓
Avaliar resultado
   ↓
Gerar reflexão
   ↓
Detectar padrão
   ↓
Criar candidata de evolução
   ↓
Testar em sandbox
   ↓
Validar por gate
   ↓
Promover ou rejeitar
   ↓
Registrar aprendizado
```

---

# 8. Tipos de mudança e risco

| Mudança | Risco | Aprovação |
|---|---|---|
| Memória episódica | Baixo | Automática |
| Memória semântica | Médio | Gate leve |
| Memória procedural | Médio/Alto | Revisão |
| Skill candidata | Médio | Sandbox |
| Skill promovida | Alto | Aprovação |
| Workflow | Médio/Alto | Gate |
| Roteamento | Alto | Revisão |
| Governança | Crítico | Humana |
| Pesos de modelo | Crítico | Pesquisa |

---

# 9. Campos sugeridos

## 9.1 experience_record

```yaml
experience_id:
mission_id:
user_intent:
route:
workflow_profile:
primary_mind:
primary_domain_driver:
specialist_used:
tools_used:
plan_summary:
execution_summary:
outcome:
errors:
user_feedback:
reflection:
candidate_learning:
```

---

## 9.2 evolution_registry

```yaml
evolution_id:
source_mission:
source_route:
source_workflow_profile:
source_specialist:
change_type:
proposed_change:
reason:
evidence:
risk_level:
status:
validation_result:
promoted_at:
rolled_back_at:
owner:
```

---

## 9.3 skill_registry

```yaml
skill_id:
name:
description:
domain:
specialist_type:
inputs:
outputs:
tools_allowed:
risk_level:
version:
status:
created_from_experience:
success_evidence:
failure_modes:
rollback_policy:
```

---

# 10. Métricas de evolução

## Operacionais

- taxa de sucesso por rota;
- tempo médio de conclusão;
- custo por missão;
- número de intervenções humanas;
- número de rollbacks;
- retomadas com sucesso.

## Cognitivas

- aderência ao objetivo;
- qualidade da síntese;
- coerência com identidade;
- escolha correta de especialista;
- uso correto de memória.

## Segurança

- violações de política;
- ações bloqueadas;
- drift comportamental;
- regressões após evolução;
- falhas de tool use.

---

# 11. O que o J.A.R.V.I.S. pode aprender hoje

- preferências do usuário;
- rotinas;
- decisões passadas;
- padrões de trabalho;
- workflows que funcionam;
- erros recorrentes;
- especialistas adequados por tarefa;
- tools úteis por domínio;
- formas melhores de sintetizar;
- sinais de risco.

---

# 12. O que o J.A.R.V.I.S. não deve alterar sozinho

- identidade central;
- constituição do sistema;
- regras críticas de governança;
- permissões de alto risco;
- arquitetura do núcleo;
- memória normativa;
- pesos do modelo central.

---

# 13. Backlog sugerido

Este backlog é um roadmap arquitetural, não a fila executável corrente.

Regra de uso:

- para virar implementação, cada fase precisa ser traduzida em itens `MB-*` no
  `docs/implementation/execution-backlog.md`;
- cada item novo deve ter contrato, testes locais, teste ponta a ponta afetado,
  observabilidade, documentação e gate;
- fases posteriores não podem antecipar alteração de pesos, autoexecução ampla
  ou mudança estrutural sem sandbox, evidência e aprovação.

Relação com o backlog ativo:

- `MB-110` a `MB-114` não implementam EvolutionOS completo;
- esse lote cria uma base necessária para evolução operacional, porque objetivos,
  work items, checkpoints e artefatos vivos tornam possível medir experiência
  real ao longo do tempo;
- a fase evolutiva mais provável depois desse lote é `experience_record` e
  reflexão pós-tarefa, desde que a repriorização macro confirme esse caminho.

## Fase 1 — Fundação

- criar experience_record;
- registrar missões e outcomes;
- implementar post_task_reflection;
- criar evolution_log;
- conectar reflexão à memória;
- gerar relatório de padrões recorrentes.

## Fase 2 — Skills candidatas

- criar skill_registry;
- detectar padrões recorrentes;
- gerar skills candidatas;
- exigir validação;
- criar sandbox de skills.

## Fase 3 — Workflow evolution

- versionar workflow_profiles;
- comparar workflows;
- medir sucesso por rota;
- criar candidatas de workflow;
- validar por gate.

## Fase 4 — Roteamento adaptativo

- medir acerto de roteamento;
- detectar uso incorreto de especialista;
- propor ajuste governado;
- criar testes de regressão por rota.

## Fase 5 — Evolution Lab

- testar mudanças em sandbox;
- comparar baseline vs candidato;
- produzir relatório de promoção;
- permitir rollback.

## Fase 6 — Pesquisa avançada

- estudar SEAL-like self-edits;
- estudar SCoL-like consolidation;
- estudar LoRA em subsistemas;
- estudar world model contínuo;
- estudar autoavaliação com avaliadores externos.

---

# 14. Proposta de seção para o Documento-Mestre

Adicionar seção:

## Camada Evolutiva e Aprendizado Operacional

Texto sugerido:

> O J.A.R.V.I.S. deve evoluir primeiro por memória, reflexão, skills, workflows, roteamento e governança.  
> A evolução paramétrica do núcleo central é fronteira de pesquisa e não faz parte do baseline inicial.  
> Toda evolução deve ser observável, versionada, validada e reversível.

---

# 15. Formulação curta para o agente de desenvolvimento

> A camada evolutiva do J.A.R.V.I.S. não deve ser tratada como automodificação irrestrita.  
> Ela deve começar como aprendizado operacional governado: captura experiências, gera reflexão, detecta padrões, propõe skills e workflows, valida em sandbox, promove com gate e mantém rollback.  
> Alterações de peso do modelo central ficam fora do escopo inicial.

---

# 16. Conclusão

A autoevolução do J.A.R.V.I.S. é possível hoje, desde que seja entendida como evolução governada de comportamento, memória, skills, workflows, roteamento e avaliação.

A estratégia correta é:

- preservar o Core;
- evoluir ao redor dele;
- validar tudo;
- registrar tudo;
- promover com evidência;
- manter rollback;
- deixar alteração profunda de pesos para pesquisa futura.

Próxima tradução prática recomendada:

1. consolidar captura de experiencias pos-tarefa como memoria evolutiva;
2. gerar propostas de melhoria a partir de observabilidade;
3. usar o `evolution-lab` para comparar candidatos de prompt, plano, workflow e
   roteamento;
4. registrar candidatos tecnologicos externos primeiro como referencia,
   experimento, complemento controlado ou traducao promovivel, com evidencia,
   testes, sandbox e rollback antes de qualquer revisao manual;
5. manter fine-tuning, LoRA, self-edits persistentes e autoevolução profunda do
   núcleo como pesquisa até haver evidência, sandbox e rollback suficientes.
