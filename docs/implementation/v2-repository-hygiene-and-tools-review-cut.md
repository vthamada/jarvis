# V2 Repository Hygiene And Tools Review Cut

## 1. Objetivo

Este documento abre o recorte que sucede o fechamento do
`v2-native-memory-scope-hardening-cut`.

Ele existe para:

- reduzir carga cognitiva na superficie ativa de `docs/` e `tools/`;
- separar melhor o que continua vivo do que ja virou historico regeneravel;
- preservar gates, closures e rastreabilidade antes de qualquer limpeza;
- impedir que a malha documental cresca mais rapido do que o comportamento do sistema.

---

## 2. Leitura correta deste corte

O que este corte assume como baseline obrigatorio:

- `docs/implementation/v2-native-memory-scope-hardening-cut-closure.md` ja fechou o ultimo recorte funcional do baseline;
- `tools/engineering_gate.py --mode release` continua passando com eixo de memoria nativa endurecido;
- a proxima melhoria de maior valor agora e estrutural, nao abertura de capacidade nova;
- nenhuma limpeza pode quebrar `engineering_gate`, `verify_axis_artifacts` ou closures regeneraveis ainda usadas.

O que este corte passa a fazer acima desse baseline:

- inventariar a superficie ativa de implementacao e tooling;
- classificar docs e scripts entre manter, arquivar e deletar;
- preparar uma limpeza segura e auditavel do repositorio;
- manter a abertura de novos cortes funcionais condicionada a essa revisao.

---

## 3. Escopo do corte

### Sprint 1. Regenerable inventory

Status atual:

- concluida.

Objetivo:

- transformar a revisao estrutural em inventario regeneravel, nao em impressao manual solta.

Entregas esperadas:

- inventario da superficie ativa de `docs/implementation`;
- inventario categorizado da raiz de `tools/`;
- guardrails explicitos para impedir delete oportunista.

Leitura de fechamento:

- `tools/render_repository_hygiene_inventory.py` agora inventaria `docs/implementation` e `tools/` com classificacao inicial por familia;
- `docs/implementation/v2-repository-hygiene-inventory.md` passou a registrar esse inventario de forma regeneravel;
- `tests/unit/test_render_repository_hygiene_inventory.py` trava o artefato minimo dessa revisao;
- esta sprint nao apaga nada: ela apenas prepara a classificacao segura do que fica, do que arquiva e do que pode sair.

### Sprint 2. Docs classification

Status atual:

- concluida.

Objetivo:

- classificar a superficie de documentos ativos entre manter, arquivar e deletar.

Entregas esperadas:

- decisao formal por documento de implementacao;
- reducao de ambiguidade sobre qual doc guia o trabalho atual;
- criterio explicito para o que pode sair da pasta ativa sem perda real.

Leitura de fechamento:

- `tools/render_repository_hygiene_doc_decisions.py` agora classifica formalmente `docs/implementation` entre manter, arquivar e deletar;
- `docs/implementation/v2-repository-hygiene-doc-decisions.md` passou a registrar a decisao regeneravel por documento;
- a superficie ativa foi reduzida conceitualmente a docs fundacionais, snapshot de aderencia, cut atual, inventario atual e closure funcional mais recente;
- cuts e artefatos de recortes encerrados passaram a `archive candidate`;
- nenhum documento entrou em `delete candidate` nesta sprint porque todos os restantes ainda preservam valor de auditoria.

### Sprint 3. Tools classification

Status atual:

- concluida.

Objetivo:

- classificar os scripts de `tools/` entre baseline vivo, suporte regeneravel historico e delete candidate.

Entregas esperadas:

- leitura clara do que continua no caminho critico do repositorio;
- separacao entre tooling historico e tooling vivo;
- criterio de preservacao dos scripts exigidos por gate e rollout.

Leitura de fechamento:

- `tools/render_repository_hygiene_tool_decisions.py` agora classifica formalmente os entrypoints da raiz de `tools/`;
- `docs/implementation/v2-repository-hygiene-tool-decisions.md` passou a registrar a decisao regeneravel por script;
- gates, verificadores, ferramentas do piloto e artefatos do proprio corte seguem como baseline vivo;
- closures e renderizadores de recortes encerrados passaram a `archive candidate`;
- nenhuma ferramenta entrou em `delete candidate` nesta sprint porque a limpeza segura ficou reservada para a Sprint 4.

### Sprint 4. Cleanup and closure

Status atual:

- concluida.

Objetivo:

- executar a limpeza decidida e fechar o recorte com artefato regeneravel.

Entregas esperadas:

- limpeza real da superficie ativa sem quebrar gates;
- update dos documentos vivos apos a reorganizacao;
- fechamento formal do recorte com backlog curto residual.

Leitura de fechamento:

- docs classificados como `archive candidate` migraram para `docs/archive/implementation/`;
- entrypoints historicos classificados como `archive candidate` migraram para `tools/archive/`;
- `docs/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md` passou a registrar a decisao formal do recorte;
- `tools/close_repository_hygiene_and_tools_review_cut.py` passou a fechar o recorte de forma regeneravel;
- o recorte termina sem `delete candidate` executado e sem abrir novo cut funcional por inercia.

---

## 4. Definicao de pronto deste corte

Este corte deve ser considerado pronto quando:

- a superficie ativa de `docs/implementation` estiver menor e mais legivel;
- `tools/` separar melhor baseline vivo, historico regeneravel e scripts descartaveis;
- `tools/engineering_gate.py --mode release` continuar passando apos a limpeza;
- o proximo corte funcional puder ser aberto com menos ruido estrutural no repositorio.

---

## 5. Documento de apoio obrigatorio

Ler em conjunto com:

- `docs/implementation/v2-native-memory-scope-hardening-cut-closure.md`
- `docs/implementation/v2-repository-hygiene-inventory.md`
- `docs/implementation/v2-repository-hygiene-tool-decisions.md`
- `docs/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md`
- `HANDOFF.md`
- `README.md`
- `tools/README.md`
- `tools/render_repository_hygiene_inventory.py`
