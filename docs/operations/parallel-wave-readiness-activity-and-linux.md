# Rodada F05/F13/T03 - 2026-10-12

Pacotes isolados autorizados pelo operador; integracao coordenada no checkout,
sem commit/push/merge ou promocao de capability. MB236 permanece blocked e
ultimo MB integrado validado permanece MB235. A sondagem OAuth e independente:
ver [estado atual](real-oauth-acceptance.md).

## Implementacoes

- F05: [atividade readonly de jobs](readonly-job-activity.md). CLI opt-in de
  selecao explicita produz contagens sem conteudo/identidades ou escrita.
  Claim interrompida continua running depois de crash real e dois leitores
  novos; nenhuma reconciliacao, scheduler ou notificacao.
- F13: [piloto MCP de inventario para Core](readiness-mcp-core-pilot.md).
  Cliente/servidor stdio reais, enums/contagens/hash sem texto autoral no prompt,
  governanca/sintese/Memory/restart reais. A consulta precede o Core; nao e
  despacho MCP governado nem autenticacao humana ou ferramenta promovida.
- T03: somente duas fixtures de teste corrigidas. Caminhos absolutos nativos
  sem IO, patch de Path restaurado mesmo em erro e executable do teste
  resolvido antes de validar asset. Runtime/guardas de symlink intactos.

Sem novos contratos compartilhados, dependencias centrais, migração, registry
ou acesso a contas/dados humanos pelos workers. Ownership e DOR na
[fila unica](../implementation/execution-backlog.md).

## Evidencia focada

F05:71 testes novos passaram no estado final; reader/CLI legados+nova bateria antes do ajuste
de saida110 passed/2 skips symlink Windows. F13:160 passed no host autorizado,
60 unitarios/58 integracoes novos e42 stdio existentes. Root confirmou bateria
integrada jobs+diagnosticoHTTP/TLS/Core/Memory com exit0 no host, sem inferencia
externa. Ruff nos pacotes novos passou. Revisao cruzada encontrou e reproduziu
exit120/Exception ignored em pipe fechado no shutdown do Python; corrigido no
boundary de saida, com pipes reais, timeout efetivo e descritores padrao
estritamente delimitados. F13 tambem recebe vinculacao explicita de sujeito,
Memory ID/decisao e envelopes persistidos, nao somente nomes/contagens de eventos.

T03: baseline Windows155 passes, Linux dois positivos falharam devido ao
drive Windows; reporter quebrava sob monkeypatch global. Apos correcao158
passes em cada SO no modulo. Caso pipeline Linux com launcher symlink falhou
antes e passou apos resolver interpreter confiado. Corpus vizinho final512
passes tanto Windows host quanto Docker Linux. Guards negativos de redirects
e hardlinks permanecem. Nenhum skip novo ou validacao relaxada.

Windows sandbox teve25 falhas no corpus vizinho (Temp/SQLite/processos); mesma
selecao passou no host com temporarios proprios, sem mudanca de runtime. Provas
antigas F13 em sandbox tiveram startup/fixture I/O sem traceback final e nao
contam como sucesso; foco final129 host foi completo.

## Gates e limites

Gates globais aprovados: Windows9303 passed/111 skipped em9414 casos,
Linux9185 passed/239 skipped em9424 casos, ambos exit0/zero failed/errors.
Contagens derivadas dos marcadores completos do pytest (-qq omite resumo).
Execucoes interrompidas nao sao provas de sucesso.14 arquivos de apps/
diagnostico/corpus permaneceram com hashes congelados apos os gates.
Primeiro Linux standard na imagem antiga falhou: sete erros de coleta por
cryptography ausente. Dockerfile atual ja declara cryptography==46.0.7 em
ferramentas de desenvolvimento. Imagem antiga preservada; nova tag exclusiva
de testes construida: jarvis-linux-validation:mb236-py311-20261012, SHA
06227a71f8091cae6663926523eeab05c4b5f976ffcc8a293854b38a1d00c7ac.
Sem alterar Dockerfile/runtime ou instalar no venv. Dois snapshots Linux
foram interrompidos exclusivamente nos containers proprios para incorporar
correcoes da revisao, exit137; nao contam como pass e logs foram preservados.
Gates Windows igualmente interrompidos antes do fim so atingiram arvores
de processos identificadas pelos logs exclusivos, nao sessoes humanas.
Execucao Linux do snapshot pelo runner oficial fica sem rede/mount de dados
humanos; a imagem nao inclui Node/PostgreSQL, skips nao validam esses ambientes.
CI remoto do PR-1 nao mudou por esses testes locais.

Primeiro Linux completo com imagem atual terminou exit1:9172 passed/239
skipped/3 failed, contagens derivadas dos marcadores porque -qq omite resumo.
As tres falhas foram comprovadas e corrigidas sem alterar apps/conta/runtime:
archive omitindo Dockerfile (agora apenas o caminho exato e regular entra),
e dois filhos -I de testes SIWC sem ROOT para importar shared. Runner32 passou
em Windows/Linux com archive/extrator real e negativos de contencao/segredos/
links/hardlinks; storage88 casos: Windows82 passed/6 skips e Linux85 passed/
3 skips preexistentes. Isolamento -I/locks/timeouts e protecoes mantidos.
Nova execucao global Linux inclui essas correcoes e passou; Windows global
cobre apps finais anteriores a essas mudancas exclusivamente auxiliares.
Foco combinado Windows final303 passed/6 skipped em309 casos, exit0,
valida tambem as ferramentas/fixtures atuais com os dois modulos novos.
Uma tentativa adicional de foco combinado usou basetemp dentro do workspace
OneDrive e recebeu siwc_storage_path_refused nos casos de armazenamento
sintetico. Erro de configuracao do coordenador: guard corretamente recusou
local sincronizado; nenhuma correcao ou relaxamento no runtime. Reexecucao
usou temporario proprio do host fora do repo/OneDrive e passou303/6 skips,
como gates/worker valido. Nenhum acesso a conta real nesse foco.
Depois da sincronizacao final do inventario,253 testes report/contratos/stdio
passaram, sem skips. Quick global, document guardrails e git diff --check
passaram. Nenhuma fonte de runtime mudou apos os gates; metadados nao fecham
MB236 nem promovem produto ou ferramenta. Sem sessoes de teste pendentes.

## Desativacao e continuidade

Nao invocar os dois modulos novos desativa os slices, sem perda de dados ou
alteracao de boot normal. Fixtures corrigidas mantem requisitos anteriores.
F05 ainda precisa executor real/receipts/Web; F13 ainda precisa despacho
governado antes da chamada. Outra inferencia real exige autorizacao propria;
nenhuma dessas implementacoes transforma resposta sem CT em aceite de modelo.
