# Ecosystem Verticals Map for JARVIS

## 1. Objetivo

Este documento define um mapa derivado de verticais para o ecossistema do
JARVIS.

Ele existe para:

- organizar pacotes de capacidade orientados a produto e operacao;
- facilitar roadmap, priorizacao e empacotamento de especialistas, tools e
  workflows;
- manter a ontologia soberana do projeto intacta.

Este documento nao substitui:

- `documento_mestre_jarvis.md`;
- `shared/domain_registry.py`;
- `shared/mind_registry.py`;
- `shared/memory_registry.py`.

---

## 2. Regra central

O JARVIS continua sendo modelado canonicamente por:

- `Core` soberano;
- dominios canonicamente definidos no mestre;
- mentes;
- memorias;
- dominios operacionais;
- dominios meta;
- especialistas subordinados;
- tool layer;
- governanca.

As verticais existem apenas como:

- agrupamento de implementacao;
- empacotamento de produto;
- camada operacional derivada;
- visao de roadmap.

Em resumo:

- dominio e ontologia;
- vertical e empacotamento.

---

## 3. Quando uma vertical vale a pena

Uma vertical so faz sentido quando houver combinacao real de:

- workflows recorrentes;
- contratos proprios ou quase proprios;
- especialistas subordinados relevantes;
- memoria util por classe;
- governanca especifica do eixo;
- valor operacional ou de produto claro.

Sinais de que ainda nao vale a pena:

- o nome e mais forte do que a materializacao;
- a vertical so replica um dominio sem ganho pratico;
- a taxonomia canonica fica mais confusa em vez de mais clara;
- o runtime ainda opera melhor no nivel de dominio e workflow.

---

## 4. Familias de verticais

### 4.1 Verticais compostas prioritarias

Essas sao as verticais mais naturais para o ecossistema vivo do JARVIS.

#### `DevOS`

Combina principalmente:

- `computacao_e_desenvolvimento`
- `dados_estatistica_e_inteligencia_analitica`
- `inteligencia_artificial_e_sistemas_autonomos`
- `produtividade_execucao_e_coordenacao`
- dominios operacionais de artefatos e automacao

Papel:

- desenvolvimento assistido;
- manutencao de repositorios;
- analise tecnica;
- geracao de artefatos;
- automacao de engenharia.

Maturidade recomendada:

- primeira vertical forte do ecossistema

#### `ResearchOS`

Combina principalmente:

- `comunicacao_linguagem_e_argumentacao`
- `historia_civilizacoes_e_cultura`
- `estrategia_e_pensamento_sistemico`
- `dados_estatistica_e_inteligencia_analitica`
- dominio operacional de pesquisa e inteligencia

Papel:

- pesquisa profunda;
- analise comparativa;
- sintese de fontes;
- dossies e hipoteses;
- argumentacao estruturada.

Maturidade recomendada:

- primeira onda

#### `LifeOS`

Combina principalmente:

- `produtividade_execucao_e_coordenacao`
- `psicologia_e_comportamento_humano`
- `cognicao_aprendizado_e_inteligencia`
- `saude_medicina_e_bem_estar`
- dominios operacionais de assistencia pessoal e monitoramento contextual

Papel:

- continuidade de vida;
- rotina;
- prioridades;
- organizacao pessoal;
- suporte contextual de longo prazo.

Maturidade recomendada:

- segunda onda, apos memoria e continuidade mais maduras

#### `FinanceOS`

Combina principalmente:

- `financas`
- `economia`
- `direito_e_regulacao`
- `tomada_de_decisao_complexa`
- `estrategia_e_pensamento_sistemico`

Papel:

- analise financeira;
- planejamento;
- risco;
- vigilancia de exposicao;
- recomendacoes auditaveis.

Maturidade recomendada:

- segunda ou terceira onda, por sensibilidade alta

#### `ProtectiveIntelligenceOS`

Combina principalmente:

- `defesa_seguranca_e_gestao_de_crises`
- `computacao_e_desenvolvimento`
- `dados_estatistica_e_inteligencia_analitica`
- `tomada_de_decisao_complexa`
- monitoramento e vigilancia contextual

Papel:

- inteligencia protetiva;
- OSINT publico;
- forense;
- risco e antecipacao;
- resposta a incidentes.

Maturidade recomendada:

- segunda ou terceira onda, com governanca forte

Referencia derivada:

- `docs/architecture/protective-intelligence-architecture.md`

#### `ExecutiveOS`

Combina principalmente:

- `estrategia_e_pensamento_sistemico`
- `tomada_de_decisao_complexa`
- `negocios_gestao_e_organizacoes`
- `produtividade_execucao_e_coordenacao`
- `planejamento_e_coordenacao`

Papel:

- coordenacao de frentes;
- decisao estruturada;
- missao;
- acompanhamento;
- visao executiva do ecossistema.

Maturidade recomendada:

- segunda onda

---

### 4.2 Verticais compostas secundarias

Essas verticais fazem sentido, mas nao precisam nascer cedo.

#### `HealthOS`

- saude, bem-estar, performance e continuidade pessoal

#### `EducationOS`

- ensino, aprendizagem, memorizacao e desenvolvimento humano

#### `CreativeOS`

- criatividade, design, narrativa, branding e ideacao

#### `LegalOS`

- direito, regulacao, compliance e avaliacao normativa

#### `StrategyOS`

- cenarios, geopolitica, negocios, vantagem e trade-offs

#### `WorldModelOS`

- historia, cultura, sociedade, geopolitica, economia e futuros

---

### 4.3 Verticais tecnicas tardias ou especializadas

Essas verticais sao plausiveis, mas tendem a nascer apenas quando houver forte
valor pratico.

#### `DataOS`

- analytics, pipelines, BI, modelagem e inteligencia quantitativa

#### `InfraOS`

- infraestrutura, energia, logistica e resiliencia operacional

#### `AIOperationsOS`

- absorcao e operacao de sistemas autonomos e workflows agentic

#### `FutureOS`

- frontier tech, foresight, exploracao espacial e tecnologias emergentes

---

## 5. Ordem recomendada

Se o objetivo for construir um ecossistema vivo sem fragmentar o nucleo, a
ordem mais sensata tende a ser:

1. `DevOS`
2. `ResearchOS`
3. `LifeOS`
4. `ExecutiveOS`
5. `FinanceOS`
6. `ProtectiveIntelligenceOS`
7. `HealthOS`

Essa ordem privilegia:

- valor alto com risco controlavel;
- maturacao de memoria e continuidade antes de eixos sensiveis;
- consolidacao do proprio desenvolvimento do JARVIS antes de expansao maior.

---

## 6. O que nao fazer

- nao trocar a ontologia canonica por verticais;
- nao criar uma vertical sem contratos e workflows reais;
- nao fazer uma vertical competir com o `Core`;
- nao usar a vertical para mascarar lacuna ainda aberta no nivel de dominio,
  mente, memoria ou governanca;
- nao transformar nome de vertical em backlog artificial.

---

## 7. Veredito

Vale a pena modelar verticais como camada derivada do ecossistema.

Nao vale a pena:

- substituir o modelo canonico do mestre;
- reestruturar o runtime soberano em torno delas cedo demais.

Regra final:

- o mestre continua soberano;
- o runtime continua governado por registries canonicos;
- as verticais existem para organizar expansao, produto e implementacao.
