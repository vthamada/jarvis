# Presença cinematográfica na Web

Nota de evolução: este registro descreve o corte visual/manual já fechado.
A integração opt-in posterior de microfone e fala canônica tem contrato e
evidência separados em [conversa Web por voz](local-web-voice-conversation.md).

## Escopo e limites

Direção visual aprovada pelo operador: esfera volumétrica de partículas azul/ciano,
órbitas e filamentos, painéis translúcidos com cantos instrumentais e compositor
na base. O tema compartilhado `apps/jarvis_web/cinematic.css` cobre a demonstração
offline e a aplicação Web pareada, sem framework, assets remotos ou dependência
central nova. Reaproveita o renderer e o player WAV públicos existentes.

O visual não promove capacidade operacional. Não há agenda, sensores, métricas
ou progresso inventados. A fixture continua identificada como demonstração; a
Web live mostra conexão, contexto, reprodução local e consulta manual de jobs.
Governança, memória canônica, consentimento por pergunta, tickets, recuperação
sem reenvio e final integral permanecem nos contratos existentes do Core.

## Executar e observar

Na raiz, iniciar explicitamente uma das superfícies em primeiro plano:

```powershell
.venv/Scripts/python.exe -u -m apps.jarvis_web.serve --port 0
.venv/Scripts/python.exe -u -m apps.jarvis_api --authorized --port 0
```

Cada comando escolhe porta própria e informa a URL loopback. O segundo cria
runtime isolado e segredo temporário no terminal: pareamento local não comprova
identidade humana. Não publicar o segredo ou incluir o terminal em capturas.
Nenhuma instância já aberta pelo operador precisa ser reiniciada por este ensaio.
Servidores antigos precisam de reinício explícito para reconhecer novos assets;
não contornar 404 com servidor genérico ou relaxamento de CSP.

Na barra inferior, usar o botão de áudio local (live) ou “Ensaiar voz local”
(fixture). O aviso permanente informa “Áudio local manual · sem microfone”.
O botão abre o painel e leva o foco ao seletor visível, mas não abre
o picker nem reproduz som. Selecionar WAV PCM16 mono/estéreo, 8–96 kHz, até
32 MiB / 600 s. Clicar em reproduzir é uma ação separada.

O áudio permanece em memória no navegador; o nome do arquivo é apagado do input
antes da leitura. Nenhum upload, microfone, STT, TTS automático, armazenamento
ou inferência é iniciado. Não é ainda a fala automática da resposta do Core nem
uma nova prova de qualidade da clonagem. A voz escolhida pode ser um WAV já
produzido e autorizado pelo operador.

O `AnalyserNode` do player fornece RMS real ao renderer. `speaking_local` indica
reprodução efetiva; silêncio resulta em amplitude zero. Stop/remove/ocultação
da página interrompem o som; desconexão e pagehide descartam o arquivo. BFCache
não retoma áudio nem seleção antiga. A final textual não depende de áudio.

## Movimento, acessibilidade e segurança

- Canvas decorativo, estados textuais e botões nativos com alvo mínimo de 44 px.
- Pausa explícita e `prefers-reduced-motion` conservam uma cena estática.
- Um RAF, limite de 30 fps, 3.980 partículas, DPR até 2 e backing até 1.040 px.
- Ocultação suspende desenho; descarte remove listeners e invalida operações
  tardias. Amplitude não finita ou falha do analisador não cria fala fictícia.
- Layout usa fluxo normal: core primeiro no DOM, painéis refluem abaixo em
  telas estreitas. Sem overlays de painel, scroll aprisionado ou texto truncado.
- Focus-visible e forced-colors mantidos; sem fontes/URLs externas.
- ASSETS acrescenta somente CSS/módulos explícitos. CSP e Permissions-Policy
  permanecem inalteradas; não há rota de áudio/upload.

## Evidência da rodada de 2026-10-17

Teste novo antes da integração: 7 falhas esperadas e 5 passagens (RED de tema,
canvas/controles live e assets ainda ausentes). Após integração: 1.170 testes
JavaScript passaram; 79 testes Python Web/HTTP de atividade passaram no host.
Uma execução no sandbox falhou com WinError 10013 nos sockets loopback; não é
evidência de defeito do app. A primeira seleção de regressão incluiu caminho de
teste inexistente e coletou zero casos; corrigida sem mudar testes para passar.

Browser real: pareamento em runtime novo próprio; WAV sintético com alternância
silêncio/som, amplitude observada 0 e 0,179, modo `speaking_local`, stop/pausa
voltando a zero/idle. Nenhum erro de console nesse fluxo. Mobile 390 px sem
overflow horizontal; abrir controles revelou o input focado dentro da viewport.
Demais breakpoints e fluxo canônico são registrados no fechamento abaixo.

Primeira revisão: gate standard Windows exit0, 10.415 aprovados e121 ignorados
(10.536 marcadores de casos no log), zero falhas/errors;15 hashes preservados.
Durante o fechamento o operador reapresentou o conceito visual como referência
direta e pediu maior fidelidade. Revisão de composição/brilho em andamento;
esse gate não é aceite das alterações posteriores. Nenhum commit, push ou merge.

Revisão de fidelidade: marca centralizada, quatro painéis angulares em perspectiva,
esfera mais luminosa com 247 vértices compartilhados/469 conexões curvas e piso
perspectivo. Configuração técnica fica abaixo da conversa; avisos e consentimento
permanecem visíveis. Briefing apenas preenche/foca; contexto reflete o estado
real, sem inventar modelo, memória ou calendário. Parear a partir da configuração
agora revela o compositor acima dela, sem manter foco fora da viewport.

Validação desta revisão: 1.186 testes JS, 82 Python Web/atividade e 15 contratos
cinematográficos passaram. Um contrato antigo de foco precisou ser atualizado
após RED: não rolar durante pareamento deixou de ser correto com o novo fluxo.
Browser confirmou envio nativo ao Core, final integral e consentimento desligado;
320/390/1280 px sem overflow horizontal. Em 1280x800 e 1672x940 a barra de comando
live fica integral na primeira viewport; fixture também em 1672x940. Simulação
fixture terminou e o botão WAV revelou o seletor focado em 320 px. Sem prova em
dispositivo físico, leitor de tela ou benchmark de GPU.

Fechamento da revisão de referência: gate standard Windows exit0, 10.418
aprovados e 121 ignorados (10.539 marcadores), zero falhas/errors. Os 16 hashes
de código/testes congelados antes do gate permaneceram iguais depois dele.
Log separado: `cinematic-reference-standard-gate.log` no diretório de evidências
da rodada; o log da primeira revisão permanece histórico. A prévia final usa
outro runtime próprio pareado, Core nativo, complemento generativo e jobs
desativados. Captura mostra estado pronto e nenhuma gravação/segredo. Recorte
visual local fechado, sem promover captura, voz automática ou integração de
agenda. Sem commit, push ou merge; runtimes de ensaio retidos, não apagados.

## Reversibilidade

Tema é uma folha posterior às folhas legadas; removê-la desfaz a camada visual,
mas a nova composição de painéis é uma mudança separada de HTML. Remover a
ponte `live-presence` e seus controles/rotas estáticas desfaz o ensaio live.
Nenhuma migração de dados, credencial, política do Core ou pacote instalado.
