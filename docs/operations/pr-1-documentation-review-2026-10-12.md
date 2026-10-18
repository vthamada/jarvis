# PR-1: revisao documental e CI - 2026-10-12

## Atualizacao: correcao local autorizada

A rodada seguinte autorizou corrigir os defeitos de testes Linux. Fixtures TTS
agora usam sintaxe absoluta nativa sem IO e monkeypatch.context restaura Path
antes de assertions/reporting, inclusive em erro. Fixture do pipeline resolve
apenas o interpreter confiado do teste (launcher Linux era symlink); guardas
de assets/redirecionamento permanecem intactas. Sem runtime alterado ou skips
adicionados. Corpus vizinho512 passou tanto no host Windows quanto no Docker
Linux sem rede. No sandbox Windows,25 casos falharam por Temp/SQLite/processo;
mesma selecao passou no host autorizado com Temp proprio, sem relaxar testes.
Gates locais standard passaram: Windows9303/111 skips e Linux9185/239 skips,
zero falhas/exit0, contagens dos marcadores -qq. Runner incluiu Dockerfile
exato e testes SIWC filhos -I receberam ROOT explicito; nenhum runtime de
conta alterado. Essa correcao LOCAL nao altera o head
da PR nem torna seu CI remoto verde; nenhum commit/push/merge/review publicado.
Descricao e provas anteriores abaixo preservadas como historico.

## Escopo e resultado

[PR-1: docs: registrar visão e autoevolução em duas frentes](https://github.com/vthamada/jarvis/pull/1),
head `e9f414494196acaf1ebe347c8ae34b8d65cbf5b1`, base
`250b128ea3cee92a72ed88afef48d0fccb83e3fc`. Aberta, nao draft; exatamente dois
Markdown,339 adicoes/12 remocoes: ADR-002 proposta e Documento Evolutivo.
Nenhum runtime, dependencia, permissao, workflow ou backlog executavel alterado.

Nao foi identificado novo bloqueador material no diff documental revisado.
Isso nao aprova a arquitetura proposta nem torna o PR pronto para liberacao:
CI Linux vermelho e suite interrompida; erro terminal ja existe no baseline.
Nenhum merge, publicacao de review/comentario, resolucao de thread, push ou
alteracao de arquivos do PR foi feita nesta revisao. PR anexado ao chat.

## Consistencia documental

- Status/titulo/decisao e consumidor distinguem direcao de produto, proposta
  tecnica nao aceita e autorizacao de implementacao; candidatos nao se promovem.
- Core, governanca, memoria canonica e sintese continuam soberanos, em
  consonancia com a Constituicao de Engenharia.
- Registry MB-177 e miner MB-178 descritos como candidatos inativos e compilador
  deterministico, nao aprendizado autonomo. Conferidos nos docs do baseline.
- MB-208 manual, MB-209 observacoes pre-produzidas, runner de quatro casos com
  holdout publico e jobs sem scheduler permanecem fundacoes, nao aceite real.
- Seis resumos primarios de pesquisa conferidos. Distingue memoria/skills de
  adaptacao parametrica; nao transfere resultado dos papers para o JARVIS.
- 31 links relativos dos dois arquivos resolvem contra a arvore da base mais
  a nova ADR da PR; nenhum caminho quebrado.

A thread antiga sobre namespace ADR permanece aberta, mas outdated. A versao
atual esclarece proposta nao aceita e referencia o audit MB-151 corretamente:
ele declara a organizacao imutavel como estrutura-alvo nao executada. Nao
resolver a thread automaticamente nem interpretar localizacao como aceite.

## CI: evidencia independente e causa do erro terminal

Severidade alta para a verificacao (interrompe o gate); confianca alta na causa
do erro terminal reproduzido. Defeito preexistente, fora do diff documental.
Localizacao: tests/unit/test_transcript_tts_options.py:103-109 e fixtures C:/
do mesmo modulo; _local_path_syntax em persistent_tts.py:90 faz recusa legitima.

[Gate do head #40](https://github.com/vthamada/jarvis/actions/runs/38316101054/job/115032972604):
failure em Ubuntu24.04/Python3.11. Mojibake, document guardrails e Ruff passaram;
pytest terminou em INTERNALERROR e erro de teardown, nao suite aprovada.
[Gate da base #38](https://github.com/vthamada/jarvis/actions/runs/37708534221/job/113088627305)
tem o mesmo erro terminal no mesmo arquivo/linha; logs lidos independentemente,
nao apenas a descricao da PR. Isso nao classifica todas as demais falhas.

Reproducao fisica Linux local em imagem existente jarvis-linux-validation:py311-v1:
container efemero, sem rede, repo bind readonly, cap-drop ALL/no-new-privileges,
limites CPU/memoria e tmpfs proprio. Apenas
tests/unit/test_transcript_tts_options.py::test_enabled_defaults_and_paths_without_filesystem_io.
INTERNALERROR reproduzido, exit3: Path.exists usado pelo reporter encontra o
forbidden global do teste; mensagem pure option validation inspected filesystem.
Primeira inicializacao usou o entrypoint customizado da imagem e nao executou
o caso pretendido; repeticao com entrypoint Python explicito reproduziu o erro.
Containers proprios efemeros removidos automaticamente; repo nao alterado.

Causa especifica confirmada por reproducao pura no mesmo Linux, com mocks
restaurados antes do reporting: fixture C:/private-marker/... nao e absoluta em
POSIX. A configuracao recusa legitimamente esse caminho com ValueError;
filesystem_calls=0. O teste bloqueia stat/lstat/exists/is_file/is_dir/resolve/open
em Path globalmente. Quando a validacao recusa, pytest tenta formatar a falha
sob esse patch e o proprio reporter quebra, mascarando o erro original.

Direcao minima para correcao em recorte separado: fixtures com caminhos nativos
absolutos, mantendo casos negativos de sintaxe e privacidade; restringir o
patch a um contexto que restaure Path antes do pytest/reporting. Manter prova
de zero filesystem IO da configuracao e rodar corpus em Windows e Linux.
Nao relaxar validacao de caminho nem fazer skip para esconder a falha.
Nao foi implementada correcao TTS sob pedido de investigacao OAuth/review.

O gate Windows do checkout local nao substitui o gate Ubuntu do head remoto.
A revisao nao executou o PR em checkout separado nem alterou sua branch.
Head e9f4144/estado aberto reconfirmados apos a revisao. Gate standard final do
checkout Windows:9222 casos/9111 passed/111 skipped/zero falhas; runtime/corpus
inalterados por hashes, nao equivalencia a CI Ubuntu aprovada.
MB236 continua bloqueado independentemente desse PR documental;
[diagnostico OAuth](real-oauth-acceptance.md) tem escopo e evidencias separados.
