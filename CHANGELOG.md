# CHANGELOG

Este changelog registra mudancas relevantes na documentacao canonica, nos artefatos de continuidade e nas decisoes estruturais do projeto `jarvis`.

Ele **nao** substitui o Documento-Mestre, o `HANDOFF.md` ou futuros ADRs detalhados. Seu papel e manter rastreabilidade objetiva do que mudou, quando mudou e por que a mudanca importa.

---

## 2026-03-17

### Operational Service

- substituido o esqueleto vazio do `operational-service` por um primeiro servico funcional minimo para tarefas seguras e deterministicas;
- adicionado suporte a:
  - execucao de `draft_plan`;
  - execucao de `produce_analysis_brief`;
  - execucao de `general_response`;
  - retorno via `OperationResultContract` com status e outputs estruturados;
- ampliados os testes do `operational-service` para cobrir task suportada e task nao suportada.

### Orchestrator Service

- integrado o `orchestrator-service` ao `operational-service`;
- o fluxo permitido agora gera `OperationDispatchContract`, executa a operacao e incorpora o resultado na sintese final;
- adicionados os eventos `operation_dispatched` e `operation_completed` ao fluxo permitido;
- ampliados os testes do `orchestrator-service` para validar despacho operacional permitido e a ausencia de operacao em fluxos bloqueados.

### HANDOFF

- atualizado para refletir que o projeto agora possui um fluxo minimo explicito `orchestrator -> governance -> memory -> operational`.

### Validacao

- validada por execucao Python direta a cadeia completa `orchestrator -> governance -> memory -> operational`;
- `pytest` continua pendente por ausencia de dependencia instalada no ambiente local atual.

---

## 2026-03-17

### Memory Service

- substituido o esqueleto vazio do `memory-service` por um primeiro servico funcional minimo em memoria de processo;
- adicionado suporte a:
  - recuperacao contextual por sessao com `MemoryRecoveryContract`;
  - registro episodico simples de turno com `MemoryRecordContract`;
  - janela curta de recuperacao para o contexto recente da sessao;
- ampliados os testes do `memory-service` para cobrir sessao vazia e continuidade basica de contexto.

### Orchestrator Service

- integrado o `orchestrator-service` ao `memory-service`;
- o fluxo minimo agora recupera contexto antes da decisao e grava o turno ao final;
- adicionados os eventos `memory_recovered` e `memory_recorded` ao fluxo principal;
- ampliados os testes do `orchestrator-service` para validar recuperacao de contexto entre dois turnos da mesma sessao.

### HANDOFF

- atualizado para refletir que o projeto agora possui um fluxo minimo explicito `orchestrator -> governance -> memory`.

### Validacao

- validada por execucao Python direta a cadeia `memory-service -> orchestrator-service` com recuperacao contextual na segunda interacao da mesma sessao;
- `pytest` continua pendente por ausencia de dependencia instalada no ambiente local atual.

---

## 2026-03-17

### Governance Service

- substituido o esqueleto vazio do `governance-service` por um primeiro servico funcional minimo;
- adicionado suporte a:
  - avaliacao de request com base em `InputContract`;
  - classificacao deterministica de risco;
  - geracao de `GovernanceCheckContract`;
  - geracao de `GovernanceDecisionContract` com `allow` e `block`;
- ampliados os testes do `governance-service` para cobrir um fluxo de baixo risco e um fluxo sensivel bloqueado.

### Orchestrator Service

- removida a politica minima de governanca que ainda estava embutida localmente no `orchestrator-service`;
- o `orchestrator-service` agora depende do `governance-service` para obter checagem e decisao;
- preservado o papel do orquestrador como coordenador do fluxo, emissor de eventos e sintetizador de resposta.

### HANDOFF

- atualizado para refletir que o projeto agora possui integracao minima explicita entre `orchestrator-service` e `governance-service`.

### Validacao

- validada por execucao Python direta a cadeia `governance-service -> orchestrator-service`;
- `pytest` continua pendente por ausencia de dependencia instalada no ambiente local atual.

---

## 2026-03-17

### Orchestrator Service

- substituido o esqueleto vazio do `orchestrator-service` por um primeiro fluxo funcional minimo;
- adicionado suporte a:
  - recebimento de `InputContract`;
  - classificacao simples de intencao;
  - geracao de `GovernanceCheckContract`;
  - avaliacao inicial de governanca com `allow` e `block`;
  - emissao de eventos internos prioritarios;
  - sintese textual basica coerente com a identidade inicial do sistema;
- ampliados os testes do `orchestrator-service` para cobrir um fluxo de baixo risco e um fluxo sensivel bloqueado.

### HANDOFF

- atualizado para refletir que o projeto saiu do estado de esqueleto puro do orquestrador e entrou no primeiro fluxo funcional minimo.

### Validacao

- validado o fluxo do `orchestrator-service` por execucao Python direta com carga manual de `sys.path`;
- `pytest` continua pendente por ausencia de dependencia instalada no ambiente local atual.

---

## 2026-03-16

### Documento-Mestre

- preenchida a secao `236.1 Blocos essenciais`, que estava vazia;
- adicionada a secao `235.5 Continuidade editorial e rastreabilidade` para formalizar a preservacao historica de numeracao e o papel de capitulos de `Encaminhamento` e `Proximo passo`;
- ampliada a secao `236.2 Itens que podem virar documentos derivados`;
- substituido o fechamento duplicado do fim do documento por capitulos operacionais e de maturidade;
- enxugado o bloco final do Documento-Mestre para manter no arquivo principal apenas definicoes canonicas e referencias para derivados operacionais;
- enxugados os blocos de roadmap de milestones e de implementacao, preservando no arquivo principal a sequencia canonica e deslocando a leitura tatica para derivados;
- realizado pente fino final para reduzir linguagem exploratoria em decisoes tecnologicas ja consolidadas.

### HANDOFF

- reestruturado para formato operacional de continuidade;
- removida a duplicacao excessiva do conteudo do Documento-Mestre;
- alinhado ao estado do projeto apos a consolidacao documental;
- atualizado para refletir a materializacao da Sprint 1 no repositorio real;
- atualizado novamente para refletir o inicio da Sprint 2 com base semantica compartilhada minima.

### Estrutura documental

- consolidada a separacao pratica entre:
  - `documento_mestre_jarvis.md` como artefato canonico;
  - `HANDOFF.md` como documento operacional de continuidade;
  - `CHANGELOG.md` como registro de mudancas relevantes;
- criada a politica de desmembramento em `docs/documentation/estrutura_de_documentos_derivados.md`;
- criado o pacote inicial de derivados de implementacao, operacao, arquitetura, executive summary e roadmap.

### Repositorio real

- criada a base estrutural do monorepo na raiz com:
  - `README.md`
  - `.gitignore`
  - `.editorconfig`
  - `.env.example`
  - `pyproject.toml`
  - `package.json`;
- criada a arvore principal do repositorio;
- criados os esqueletos minimos dos servicos centrais e das engines centrais;
- preparada a base compartilhada para a Sprint 2 em `shared/contracts`, `shared/schemas`, `shared/types`, `shared/events` e `shared/state`;
- implementada a primeira camada canonica de `shared/` com tipos, contratos, schemas, eventos e identidade/principios;
- adicionados testes iniciais de regressao estrutural em `tests/unit/test_shared_layer.py`.

### Validacao

- validada a estrutura criada com `rg --files` e inspecao recursiva de diretorios;
- validada a importacao dos esqueletos de servicos e engines com `python`;
- validada a importacao da nova camada `shared/` com `python`;
- a execucao de `python -m pytest` ainda nao foi concluida porque `pytest` nao esta instalado no ambiente local atual.
