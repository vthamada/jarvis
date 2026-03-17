# CHANGELOG

Este changelog registra mudancas relevantes na documentacao canonica, nos artefatos de continuidade e nas decisoes estruturais do projeto `jarvis`.

Ele **nao** substitui o Documento-Mestre, o `HANDOFF.md` ou futuros ADRs detalhados. Seu papel e manter rastreabilidade objetiva do que mudou, quando mudou e por que a mudanca importa.

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
