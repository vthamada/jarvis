# CHANGELOG

Este changelog registra mudancas relevantes na documentacao canonica, nos artefatos de continuidade e nas decisoes estruturais do projeto `jarvis`.

Ele **nao** substitui o Documento-Mestre, o `HANDOFF.md` ou futuros ADRs detalhados. Seu papel e manter rastreabilidade objetiva do que mudou, quando mudou e por que a mudanca importa.

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
- criada a arvore principal do repositorio:
  - `apps/`
  - `services/`
  - `engines/`
  - `memory/`
  - `knowledge/`
  - `governance/`
  - `observability/`
  - `evolution/`
  - `shared/`
  - `infra/`
  - `tests/`
  - `tools/`;
- criados os esqueletos minimos dos servicos centrais e das engines centrais;
- preparada a base compartilhada para a Sprint 2 em:
  - `shared/contracts`
  - `shared/schemas`
  - `shared/types`
  - `shared/events`
  - `shared/state`;
- implementada a primeira camada canonica de `shared/` com:
  - tipos e enums oficiais;
  - estados iniciais;
  - contratos prioritarios;
  - schemas declarativos iniciais;
  - eventos internos prioritarios;
  - identidade, missao e principios do sistema;
- adicionados testes iniciais de regressao estrutural em `tests/unit/test_shared_layer.py`.

### Validacao

- validada a estrutura criada com `rg --files` e inspecao recursiva de diretorios;
- validada a importacao dos esqueletos de servicos e engines com `python`;
- validada a importacao da nova camada `shared/` com `python`;
- a execucao de `python -m pytest` ainda nao foi concluida porque `pytest` nao esta instalado no ambiente local atual.
