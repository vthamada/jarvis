# Atividade readonly de jobs na Web local

## Escopo - 2026-10-13

F05/F06 agora podem consultar manualmente, na Web pareada existente, o resumo
de 1..32 jobs previamente selecionados pelo host. O leitor anterior do ledger
continua soberano para validar fonte e scope. O painel nao cria tickets,
invoca Core/modelo, executa, recupera, reconcilia, cancela ou agenda jobs.
Nao e progresso percentual, notificacao, executor externo ou produto completo.
MB236 continua blocked; nenhuma nova inferencia, refresh ou conta foi usada.
Nenhum servidor terceiro MCP/REA instalado ou capability promovida.

## Opt-in do host

Sem os argumentos abaixo, a atividade permanece desativada. Configuracao
parcial ou argumentos de atividade sem enable sao recusados antes do runtime.
O construtor do profile nao abre o ledger; o arquivo precisa ser existente,
local, absoluto e quiescente no momento da consulta. Nao apontar para um
ledger ativo em WAL, arquivo com sidecars, symlink/junction ou dado nao aprovado.
Nao copiar tokens, credenciais, conteudo ou refs privadas para esta documentacao.

```powershell
.venv/Scripts/python.exe -m apps.jarvis_api --authorized --port 0 `
  --enable-job-activity --job-db "C:\ApprovedLocalDirectory\ledger.db" `
  --job-actor-ref "approved-actor" --job-session-ref "approved-session" `
  --job-id "selected-job"
```

O caminho e refs acima sao exemplos, nao um store provisionado. Podem ser
selecionados ate32 IDs distintos com varios --job-id. O host explicitamente
autoriza mostrar somente esse resumo agregado a quem possuir a sessao pareada
da instancia local. O browser nao envia caminho, scope, filtro ou job_id.
O scope do ledger e caller-supplied, nao identidade humana ou binding do Core.
Pareamento Web nao autentica pessoa nem concede grant operacional.
Instancias Python ja abertas precisam ser reiniciadas para carregar a nova
rota e allowlist do modulo Web; nao reutilize uma instancia antiga como prova.

Abra a URL loopback mostrada pelo servidor e pareie com o segredo temporario
de uma utilizacao. Abra "Atividade de tarefas" e clique "Consultar atividade".
Nenhuma leitura ocorre por abrir o painel, parear, recarregar ou enviar analise.
Se o profile nao estiver configurado, a interface informa indisponibilidade.
Para rollback, omita o opt-in ao reiniciar a instancia; nenhum dado e migrado.

## Fronteira e contrato

- GET /api/job-activity exige Host/origem local, X-Jarvis-Client, cookie pareado
  e CSRF. HEAD/POST/filtros/query sao negados. Sessao e revalidada apos leitura
  e serializacao, antes de publicar o resultado.
- Envelope jarvis-local-job-activity-v1: session_ref Web e activity com contrato
  jarvis-job-activity-v1 ja existente. Nenhum path/ref/conteudo de job e emitido.
  Perfil congelado, binding fenced antes/depois e metadata revalidada; produto
  ate4096 bytes, consumo HTTP Web ate8192 incluindo envelope/diagnosticos.
- Sete estados, contagens e tentativas dos jobs selecionados; running com lease
  vencido permanece running. Isso nao comprova worker atual ou efeito externo.
- Cliente preserva ticket, final e consentimento da conversa. Consulta tem
  prazo independente, AbortController e fences de geracao/sessao. Verificar a
  mesma sessao nao invalida a leitura; resultado/erro de sessao aposentada nao
  altera uma sessao nova. Disconnect/expiry/pagehide apagam o resumo.
- Painel usa textContent, enums/contagens e labels locais. Schema, somatorios,
  autoridade falsa, extras e respostas de outra sessao sao recusados. Falha
  apaga resultado anterior; sem polling, retry, armazenamento Web ou auto-send.
- Falhas HTTP sao codigos fixos job_activity_disabled/job_activity_unavailable
  ou recusas de sessao/fronteira; sem detalhe de origem ou refs privadas.
- Leitor de arquivo pressupoe host confiavel/quiescencia: nao e sandbox de FD
  contra troca adversarial de arquivos ou snapshot de escritor concorrente.

## Evidencia e limites

Gap demonstrado: rota inexistente retornava request_invalid antes da mudanca.
Corpus novo inclui profile/config/tamper, SQLite real, fonte/scope negados,
HTTP pareado/CSRF/revogacao durante leitura e startup sem IO de ledger.
Node verifica painel/controller e concorrencia. Revisao independente identificou
e corrigiu corrida de auth por identidade de objeto; lifetime separado conserva
verificacao da mesma sessao e impede erro antigo de desconectar sessao nova.

Bateria integrada atual:259 testes Python passaram (inclui runner Node amplo).
89 testes Node novos passaram; revisao independente207 com regressoes existentes.
Contagens se sobrepoem, nao somar como casos unicos. E2E adicional usa SQLite,
HTTP/fetch nativos e os modulos reais de controller/painel em seam DOM: dois
requests (pair/read), dois jobs e zero chamada Core, nenhum arquivo do ledger
alterado; dois reinicios leitores preservados.

Prova adicional no browser real/IAB com ledger proprio sintetico: painel mostrou
dois jobs (um registrado/um concluido), somente apos consulta manual. Verificar
sessao conservou o resumo. Reload iniciou sem resumo e nova consulta manual
mostrou os mesmos estados; desconectar apagou os dados e desabilitou consulta.
Zero logs de erro do browser. Aba propria encerrada; processo temporario de
teste nao permaneceu ativo apos encerramento da sessao de ferramentas. Nenhum
pedido de analise/inferencia foi enviado. Screenshot de prova exibido na sessao.
Nao comprova dispositivo humano, modelo real, jobs externos ou Linux desta rodada.

Uma execucao intermediaria sofreu erros de permissao de Temp/socket do sandbox
antes de assertions; verificacao seguinte usou Temp exclusivo e permissao
somente para testes sinteticos. Nenhuma protecao de produto foi relaxada.
Primeiro gate standard integrado nao terminou: sessao de ferramentas encerrada
antes do resultado final; nao contar progresso parcial como gate aprovado.
9533 testes coletados no estado atual. Codex Process Jobs recusou o launch com
Unsupported platform: win32 (exit1); nenhum job criado. Reexecucao pelo terminal
oficial em foreground concluiu: gate standard Windows aprovado, exit0,9533
casos coletados,9422 passed/111 skipped (contagens da coleta e marcadores -qq).
Zero failed/errors; skips nao homologam outro ambiente.13 arquivos de runtime
e corpus com hashes preservados apos metadados; nenhuma mudanca de fonte
de runtime/testes durante o gate. Gate quick e diff-check anteriores aprovados;
329 consumidores de inventario/MCP finais passaram/zero skips. Quick final e
diff-check aprovados apos metadados; fontes runtime/corpus permaneceram iguais.
Sem commit/push/merge nesta rodada.
