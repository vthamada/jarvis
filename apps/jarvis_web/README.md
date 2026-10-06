# Cockpit local do JARVIS — WP-WEB-01

Estado: conversa implementada isolada, com **fixture permanente**, e importação
explícita de snapshot JSON local/offline. Não conectado ao Core, API, modelos,
memória canônica ou ferramentas. Não é uma capability promovida nem uma
demonstração de inferência real.

## Executar

Na raiz do repositório, iniciar explicitamente o servidor em primeiro plano:

```powershell
.venv/Scripts/python.exe -m apps.jarvis_web.serve --port 8765
```

Abrir `http://127.0.0.1:8765/`. Encerrar com Ctrl+C. Não há instalação de
pacotes, abertura automática de janela ou serviço persistente. `--port 0`
seleciona porta efêmera; o endereço aparece no terminal. O servidor só escuta
IPv4 loopback e só oferece assets explicitamente permitidos.

Após mudanças em `serve.py`/allowlist, um servidor já aberto precisa ser
reiniciado para servir módulos novos. Esta rodada não reiniciou o servidor
humano8765: a prévia usa outra instância com `--port 0`. Não trocar para servidor
HTTP genérico nem relaxar CSP para contornar assets404 de uma instância antiga.

## Fluxo inspecionável

- Conversa e envio **simulado**, sem interpretação do pedido por um modelo.
- Contexto do objetivo, atividade, artefato de exemplo e proposta de decisão.
- Inspeção somente leitura: nenhum botão cria autorização ou executa ação.
- Loading, falha, resposta incompleta e resultado vazio selecionáveis em
  “Cenários de demonstração”; cancelamento invalida callbacks pendentes.
- Reinício limpa a sessão local; não há persistência, cookies ou credenciais.
- Ctrl/Command+Enter envia, Esc fecha a inspeção; foco visível, dialog nativo,
  navegação por teclado e layout responsivo até viewport mobile.

## Importar snapshot local/offline

Selecionar explicitamente um JSON no campo “Snapshot local/offline”. O formato
é `jarvis-surface-snapshot-v1`, com `mode=core_snapshot`, `read_only=true` e
`authority=none`. Schema completo está exemplificado em
`tests/snapshot-fixture.json`. O servidor **não serve esse arquivo** nem lê
arquivos selecionados; o browser valida localmente, sem conexão/transmissão.

Limites: 65.536 bytes UTF-8, até 100 itens por lista, goal até 1.000 codepoints,
generated_at até 64 e demais textos/IDs/refs até 200 codepoints.
Campos extras/ausentes, JSON malformado, propriedades
duplicadas, versões inválidas, flags de autoridade e datas inválidas falham
fechado. Erros não refletem conteúdo do arquivo. Importações obsoletas são
descartadas; reset restaura fixtures. Snapshot anterior válido fica preservado
se a nova seleção for inválida.

A UI declara **origem não verificada**: o schema não comprova autenticidade,
integridade, freshness ou vínculo com um Core. Principal do arquivo não troca
identidade/sessão do cliente. Objetivo, work-items, metadados de artefatos e
atividade são apenas projeções declaradas. Nenhum conteúdo físico, challenge,
grant ou segredo é importado. Conversa permanece simulada, sem API live.

## Voz: revisão explícita de transcrição simulada

MB223 adiciona painel separado **Transcrição de arquivo · revisão local**,
com picker JSON de origem não verificada, edição e pacote offline único. Não
envia ao Core pelo browser; o comando opt-in transcript-review revalida e envia
ao Core persistente do console. Consentimento local, prazo120s, bytes/hash/texto
exatos; nada altera a conversa fixture abaixo. Runbook/testes/limites:
[Web -> Core](../../docs/operations/reviewed-transcript-web-to-core.md).

MB224 estende apenas o comando explícito do console com TTS local opt-in da
final persistida, consentimento vocal separado e alternativa textual preservada.
Não adiciona envio, playback ou acesso ao laboratório pelo browser. Limite de
600 codepoints no modo single; MB225 acrescenta `--tts-batch` somente no console,
ate6000 codepoints/600s. MB226 permite selecionar manualmente agregado ate600s/
32MiB, com preparacao interrompivel; nao realiza autoimport ou upload.
Qualidade vocal segue aceite proprio. Guia:
[Final persistida -> TTS](../../docs/operations/persistent-final-local-tts.md).

Abrir “Voz · revisão de transcrição” e marcar a permissão do **ensaio local**.
“Simular captura” produz somente texto de fixture. Não solicita permissão do
browser, não abre microfone e não usa o WAV de referência nem os modelos TTS.
A Web UI ainda não se conecta ao laboratório local Chatterbox/Qwen.

Revisar o texto e escolher “Confirmar texto e simular pedido” delega **esse
texto exato**, incluindo espaços, ao controller da conversa fixture existente.
Geração, revisão, principal e sessão precisam coincidir; confirmar não cria
challenge, receipt, grant ou autoridade. Não há integração live com o Core.
O próprio cenário da conversa determina completed/error/incomplete/empty.
Somente o resultado completed dessa rodada pode aparecer como alternativa
textual final e habilitar “Simular reprodução”. Nada é sintetizado ou audível.
Interromper a simulação preserva a alternativa textual.

Revogar a permissão ou descartar limpa texto/final do controller de voz e
invalida callbacks. Texto já confirmado permanece na conversa fixture em
memória até reiniciar; revogar não promete apagar histórico de outra superfície.
Reset, divergência de sessão e retorno BFCache exigem nova permissão. O prazo
de revisão/rodada é 30 segundos; conteúdo expirado nunca habilita reprodução.
Falha/incomplete/empty da transcrição não envia pedido. Cenários de transcrição
ficam no painel de voz, separados dos cenários da resposta na conversa.

`voice-controller.mjs` exporta `createVoiceController` e `handleVoicePageHide`.
Eventos locais são limitados a 64 entradas de nome/evidenceMode/authority;
não contêm transcrição nem resposta. Todos declaram synthetic_fixture/none.
Não são observabilidade canônica ou prova de áudio/Core em produção.

## Controllers e observabilidade

`fixtures.mjs` exporta `FIXTURE_VERSION = jarvis-cockpit-fixture-v1` e
`createFixture()`. `controller.mjs` exporta `createController(options)` com
`getSnapshot`, `subscribe`, `setScenario`, `submit`, `cancel`, `reset`,
`dispose`, além de `handlePageHide` para preservar uso após retorno de BFCache.
`submit(..., {exactText:true})` preserva literalmente o texto revisado pela voz;
é apenas comportamento de fixture, sem modificar autorização. Callback de
resposta já entregue não pode anexar uma segunda resposta.
Depois de dispose, comandos são recusados. Identidade/sessão divergentes são
recusadas sem adicionar pedido.
`importSnapshotFile(file)` e `cancelSnapshotImport()` possuem generation própria.
`snapshot.mjs` exporta `validateSnapshot`, `parseSnapshot`, `readSnapshotFile`,
`SNAPSHOT_VERSION` e `MAX_SNAPSHOT_BYTES`.
Eventos de atividade são dados locais de fixture, não receipts do Core.

O cliente usa `textContent` para conteúdo variável. CSP bloqueia conexões,
embeds, submissões HTTP e recursos externos; servidor não registra paths,
conteúdo ou query strings. Host é validado; caminhos, arquivos privados,
symlinks, queries, métodos de escrita e proxy são negados. Não servir pelo
servidor HTTP genérico na raiz do repositório.

## Testes

```powershell
node --test apps/jarvis_web/tests/*.test.mjs
.venv/Scripts/python.exe -m pytest apps/jarvis_web/tests/test_serve.py -q
```

JS testa estados completos, erro/incomplete/empty, cancelamento, callback
obsoleto, troca de identidade, reset, validação e isolamento de snapshots,
schema/bytes, arquivos inválidos, importações obsoletas e ausência de autoridade.
Python testa o fluxo HTTP completo de assets, HEAD, allowlist, Host,
redaction, CSP e métodos sem efeito. A verificação de browser desta rodada
está registrada em `tests/browser-verification.md`. A integração offline
exporter do Core -> JSON -> controller Web já foi testada em
`tests/integration/test_surface_snapshot_export.py`; conexão live/API e aceite
de piloto permanecem futuros. O picker não havia completado na primeira rodada;
o smoke de redesign2026-10-04 confirmou importação da fixture JSON pelo picker
e DOM offline, sem demonstrar autenticidade de snapshot/Core live.
`voice-controller.test.mjs` também cobre o fluxo inteiro permissão -> captura
simulada -> revisão exata -> conversa existente -> final fixture -> reprodução
simulada/interrupção, prazo, identidade, geração/revisão obsoletas, revogação,
BFCache, reset, dispose e eventos sem conteúdo. `test_voice_ui_contract.py`
valida DOM/labels/defaults seguros/foco/ausência de captura e egress; isso não
substitui smoke de browser e não comprova áudio real.

## Design e evolução

### Redesign orientado à conversa — 2026-10-04

Esfera integrada ao fundo (não um card separado), superfícies verde/ciano,
tipografia de leitura14–15px e títulos26–38px. Navegação e contexto secundário
mais leves; um único scroll de documento, sem rolagens internas de painéis.
Importação offline fica em “Dados da sessão”; voz, áudio e cenários ficam no
“Laboratório local”. Aviso permanente de demonstração/sem Core permanece.

Histórico fixture começa recolhido para priorizar o composer, mas está acessível
via disclosure nativo. Exemplos apenas preenchem/focam o campo; não enviam.
Um pedido local abre o histórico e compacta a presença; reset restaura a abertura.
Navegação reflete o hash e o link de voz abre seu painel antes de ancorar.
Nada muda nos contratos de conversa, snapshots, autorização ou áudio local.

Regressões DOM em `tests/test_design_ui_contract.py`; smoke de interação e
responsividade em `tests/design-browser-verification.md`. Mudança de design,
não integração live nem aceite perceptual do operador. Rollback: restaurar
HTML/CSS e handlers de apresentação; nenhum banco/estado canônico é alterado.

### Esfera de partículas — 2026-10-04

Referência visual fornecida pelo operador: esfera ciano translúcida, contorno
ondulado e pequeno núcleo. `particle-sphere.mjs` desenha Canvas2D sem biblioteca
externa: 3.200 partículas de superfície/220 centrais e dez filamentos. Movimento
até30fps, DPR limitado2, pausa manual, pausa em página oculta, ResizeObserver
e preferência reduced-motion (estático inclusive durante fala).

Apresentação não interpreta conteúdo nem representa consciência, identidade
verificada ou autoridade. A fala fixture existente continua explicitamente
simulada. Sua oscilação é sintética e marcada como tal; não implica áudio real.

Ensaio separado `local-voice-playback.mjs`: escolher WAV por picker, validar PCM16
mono/estéreo,8–96kHz,32MiB/600s, e clicar Reproduzir. File.arrayBuffer permanece
no cliente; sem upload, mic, URLs, armazenamento persistente ou codec externo.
AudioContext nasce somente no clique, PCM vira AudioBuffer, analyser mede RMS
normalizado da reprodução (não conteúdo/palavras). A esfera reage com envelope
suave; silêncio dá zero, interromper zera visual. `data-visual-mode`/`data-visual-level`
no canvas são metadados locais de apresentação, nunca receipts ou grants.

Remover/reset/pagehide descartam refs ao buffer e fecham contexto (não prometem
apagamento seguro de RAM). Leituras/resume/end atrasados são invalidados por
generation; MB226 converte em blocos16384frames/macrotarefas, permitindo
interrupcao durante preparacao. Picker limpa nome antesread; reselecao funciona
e cancel semFile conserva selecao. Ocultar página interrompe áudio e não retoma
automaticamente. Sem
autoplay, file.name no app/telemetria, hardware de captura ou servidor de áudio.
Diagnósticos são códigos allowlisted, sem exception bruta/paths. CSP permanece
connect-src none; servidor só ganhou os dois módulos estáticos allowlisted.

Browser IAB real: picker WAV sintético, reprodução e analyser deram
speaking_local/visual-level>0; interrupção voltou idle/0. Primeiro arquivo TEMP
foi inacessível ao browser, recusado; cópia explícita da fixture fora de TEMP
funcionou. Não foi usado WAV do dublador nem medida fidelidade. Mobile390x844
sem overflow horizontal; viewport temporário restaurado. 52 JS/36 Python Web
passaram; gate standard global Windows passou. Evidência em
`tests/presence-browser-verification.md`. Não é integração Core->TTS live.

Rollback do slice: retirar presence do HTML/imports/handlers, dois módulos/CSS
e suas entradas allowlist; nenhum contrato/capability Core ou banco mudou.

Atualizacao MB226 (2026-10-05): interoperabilidade Python aggregate->Node,
344 JS/173 Python focados sem skips, smoke IAB sintetico600s e mobile sem
overflow passaram; gate standard global Windows final passou. Nao e voz humana/Core live.
[Uso, limites e rollback do player longo](../../docs/operations/long-local-wav-web-playback.md).

A primeira versão usou referências de superfícies escuras/hairlines; a revisão
atual substitui essa densidade por conversa em primeiro plano e presença fluida.
System fonts locais, sem fontes/CDNs, dependências novas ou assets remotos.
Controles de interação têm targets mínimos44px, foco visível e reduced-motion.

Rollback: encerrar o servidor/remover o pacote; nenhum estado canônico muda.
Próximo slice: adapter para a fronteira cliente/Core validada, com identidade,
falha/cancelamento e revisão de segurança; não apenas remover o badge fixture.
