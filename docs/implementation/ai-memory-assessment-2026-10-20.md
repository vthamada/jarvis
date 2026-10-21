# ai-memory: utilidade para o JARVIS

Data: 2026-10-20. Estudo estatico com tres agentes e revisao do root.
Snapshot: [5519b89cc653bec4cfccbb770c6b4e5dcfcda759](https://github.com/akitaonrails/ai-memory/commit/5519b89cc653bec4cfccbb770c6b4e5dcfcda759),
versao3.1.2 declarada no Cargo.toml. Nao instalamos, clonamos, executamos,
registramos MCP/hooks ou importamos historicos/credenciais. Referencia, nao
capability promovida nem autorizacao para integrar.

## Parecer

Util para recuperacao relevante e continuidade entre agentes. A melhor primeira
absorcao e o metodo de busca e de empacotamento de contexto, nao seu runtime
inteiro. O problema imediato do JARVIS nao e falta de armazenamento: e selecionar
memoria util para a conversa, com proveniencia e custo controlados. O estudo
nao resolve o timeout do Qwen nem comprova memoria real no segundo turno.

## O que merece aproveitar

| Mecanismo | Aplicacao proposta no JARVIS |
| --- | --- |
| FTS5, entidades e vizinhos de links, fundidos por RRF; vetores opcionais | Comparar com o overlap lexical atual, antes de adicionar banco vetorial |
| Brief em camadas e leitura sob demanda | Dar contexto inicial pequeno e aprofundar somente referencias relevantes |
| Handoff tipado, ownership e claim | Preservar pendencias, tentativas falhas e origem entre executores |
| Compactacao extrativa com versoes anteriores | Propor resumos reversiveis, preservando literais e fontes |
| Avaliacao por estagio e explicacao dos ranks | Separar recuperar evidencia, responder corretamente e cumprir tarefa |

O [recuperador](https://github.com/akitaonrails/ai-memory/blob/5519b89cc653bec4cfccbb770c6b4e5dcfcda759/crates/ai-memory-store/src/reader.rs)
implementa fusao de rankings e proveniencia; nao basta o claim do README.
O [brief e a continuidade](https://github.com/akitaonrails/ai-memory/blob/5519b89cc653bec4cfccbb770c6b4e5dcfcda759/docs/ARCHITECTURE.md)
sao historico nao confiavel, nao instrucoes atuais.
A [compactacao](https://github.com/akitaonrails/ai-memory/blob/5519b89cc653bec4cfccbb770c6b4e5dcfcda759/crates/ai-memory-consolidate/src/compaction.rs)
nao equivale a treinamento de pesos nem garante preservacao semantica universal.

## Contrastes e riscos concretos

1. **Outra fonte de verdade.** O projeto adota wiki Markdown/Git para paginas;
   no JARVIS o registro canonico permanece no MemoryService. Nao criar dois
   stores factuais com autoridade concorrente. O banco externo tambem guarda
   estado operacional: [reindex](https://github.com/akitaonrails/ai-memory/blob/5519b89cc653bec4cfccbb770c6b4e5dcfcda759/docs/lifecycle-ops.md#reindex)
   reconstroi paginas/links/FTS, nao sessoes, observacoes, handoffs e auditoria.
   Backup so da wiki nao recupera o sistema inteiro; purge nao apaga Git/backups.
2. **Consulta com efeitos.** Busca reforca contadores de acesso e retencao.
   Uma integracao nao pode ser chamada de zero-write apenas por usar memory_query.
   O [contrato programatico](https://github.com/akitaonrails/ai-memory/blob/5519b89cc653bec4cfccbb770c6b4e5dcfcda759/docs/programmatic-memory.md)
   exige ainda reconciliacao de exclusoes: feed incremental nao e snapshot completo.
3. **Defaults de autoevolucao diferentes.** Com provedor LLM configurado,
   scheduler habilitado e require_approval=false permitem aprovar propostas;
   o gate executavel e opt-in. Dream e outro mecanismo, desligado por padrao.
   Sao [defaults de codigo](https://github.com/akitaonrails/ai-memory/blob/5519b89cc653bec4cfccbb770c6b4e5dcfcda759/crates/ai-memory-cli/src/config.rs),
   nao uma promessa de aprendizagem segura. No JARVIS: proposta, avaliacao,
   governanca/Core/Evolution e aprovacao adequada antes de promover.
4. **Autorizacao nao transferivel.** Ha auth e grants por projeto, mas o
   [resolver normal](https://github.com/akitaonrails/ai-memory/blob/5519b89cc653bec4cfccbb770c6b4e5dcfcda759/crates/ai-memory-store/src/project_authz.rs)
   pode degradar para open em falhas de leitura; existe caminho strict separado.
   Isso e uma incompatibilidade com nossas garantias, nao uma vulnerabilidade
   nova alegada. Isolamento de diretorios tambem nao significa ausencia de
   [efeitos de purge sobre observacoes de outra coordenada da mesma sessao](https://github.com/akitaonrails/ai-memory/blob/5519b89cc653bec4cfccbb770c6b4e5dcfcda759/crates/ai-memory-mcp/tests/suite/admin_purge.rs).
5. **Privacidade e operacao.** A [politica de seguranca](https://github.com/akitaonrails/ai-memory/blob/5519b89cc653bec4cfccbb770c6b4e5dcfcda759/SECURITY.md)
   reconhece ausencia de criptografia propria em repouso e sanitizacao best-effort.
   Nao instalar setup/hooks/backfill nem reutilizar contas por causa deste estudo.
   Embeddings locais default best-effort podem baixar modelo e consumir recursos;
   zero-LLM nao significa zero inferencia/download. A
   [matriz](https://github.com/akitaonrails/ai-memory/blob/5519b89cc653bec4cfccbb770c6b4e5dcfcda759/docs/support-matrix.md)
   ainda qualifica Windows nativo como experimental. Licenca
   [MIT](https://github.com/akitaonrails/ai-memory/blob/5519b89cc653bec4cfccbb770c6b4e5dcfcda759/LICENSE);
   stack Rust propria, nao uma dependencia Python pequena.

## Evidencia de qualidade: o que os numeros nao dizem

O [relatorio3.1](https://github.com/akitaonrails/ai-memory/blob/5519b89cc653bec4cfccbb770c6b4e5dcfcda759/docs/benchmarks/longmemeval-s-3.1.0-release.md)
publica hit@5=0,951 em FTS e0,940 com embeddings locais em470 perguntas
respondiveis, usando outro SHA de medicao explicitado pelo autor. E recuperacao,
nao acuracia das respostas nem teste de abstinencia. Nao reproduzimos os numeros.
Nem implica que vetores melhoram o nosso corpus. A
[metrica implementada](https://github.com/akitaonrails/ai-memory/blob/5519b89cc653bec4cfccbb770c6b4e5dcfcda759/evals/src/retrieval/score.rs)
e o [harness](https://github.com/akitaonrails/ai-memory/blob/5519b89cc653bec4cfccbb770c6b4e5dcfcda759/evals/README.md)
devem orientar comparacoes equivalentes, sem transformar CI upstream em prova local.

## Lacuna local e fronteira proposta

O JARVIS ja tem turns canonicos, escopo, correcoes/frescor, influencia governada
e revisao humana. O ranking em
services/memory-service/src/memory_service/recall.py usa overlap lexical; o
seletor de inspecao nao esta integrado ao tool loop. Ja o historico em
services/orchestrator-service/src/orchestrator_service/canonical_history.py
e uma janela opt-in de tres pares/4000chars, sem anexos generativos literais.
Sinais de lifecycle 'consolidated' nao executam consolidacao de conteudo.

Fronteira futura: canonico JARVIS -> projecao descartavel -> candidatos ->
reidratacao canonicamente autorizada -> politica de influencia -> Core.
Conferir sujeito/escopo/hash/versao/lifecycle antes de expor conteudo. Nenhum
resultado recuperado concede permissoes. Preferir inicialmente um port de
ranking puro, nao a autoridade ou os hooks do servidor externo.

## Ordem de experimentos, ainda nao executados

1. Mesmo corpus sintetico e perguntas congeladas: janela atual vs lexical vs
   FTS/RRF derivado. Medir Recall@k/MRR, custo/latencia, fatos raros, correcao,
   expiracao, abstinencia e zero vazamento entre sujeitos.
2. Integrar candidatos explicaveis a conversa: snapshots iguais, fontes novas,
   controle sem memoria, teste HTTP scripted e depois piloto real autorizado.
   Aceite exige utilidade da resposta e final canonica, nao so label presente.
3. Compactacao/handoff como propostas versionadas: fontes intactas, replay,
   restauracao, conflitos e falhas de claim; sem autoaprovar memoria ou regras.

Nenhum desses experimentos foi realizado pelo estudo. Proximo desenvolvimento
recomendado: recall selecionado na conversa, com avaliacao, sem trocar o cerebro.
