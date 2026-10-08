# MB235 - conversa Web local compacta

Estado 2026-10-06: MB235 done local; 45 testes Node novos (33 DOM e
12 layout), Web completa1053 e bateria Python focada121 passaram. Browser
Chrome headless proprio e export canonico aprovados; gate standard global
Windows completo aprovado,8542 casos coletados. Sem aceite de modelo real,
voz, teclado/dispositivo fisicos
ou nova prova Linux. Instancias/browser de teste proprios encerrados. Login
OAuth real posterior concluido, catalogo bloqueado; nao e prova desta UI nem
aceite de inferencia. Ver [homologacao OAuth](real-oauth-acceptance.md).

## Uso e escopo

Startup permanece [MB231/232](local-generative-analysis-web.md):

```powershell
.venv/Scripts/python.exe -m apps.jarvis_api --authorized --port 0
```

Parear usa o segredo efemero do terminal. Posse da sessao local nao autentica
uma pessoa/conta nem concede permissoes. Modelo generativo continua default
off; host configura perfil e cada pergunta exige seu proprio consentimento.
Memoria/egress/limite de espera ficam visiveis junto do campo de mensagem.
Nenhum login, refresh de provider, modelo, voz ou acao e habilitado pela UI.

Ao conectar, introducao vira faixa compacta e setup de pareamento recolhe uma
vez. Verificar sessao e Desconectar permanecem fora do disclosure. Setup
pode ser aberto pelo summary com mouse/Tab/Enter/Espaco; polls nao resetam
essa escolha. O foco de um submit de pareamento pode seguir para a mensagem
no sucesso atual, inclusive quando o browser o perde ao desabilitar o botao.
Uma escolha posterior de foco/pointer pelo usuario cancela esse fallback.

## Final integral, nunca resumo substituto

Parser MB233, controller v1/v2, API, Core, governanca e Memory intactos.
Somente apresentacao em live-app/index/style mudou. IDs de disclosure:
live-shell/data-paired, live-pairing-details/summary e live-canonical-details/summary.

A final integral e escrita sem modificacao em textContent. Seu disclosure
comeca aberto; render/clearProjection reabre enquanto uma projecao esta
pendente ou recusada. Accepted sozinho nao recolhe nada. Somente o callback
de parser bem-sucedido, com epoch/sessao/ticket/query/final/campos atuais,
mostra complemento nao verificado e pode recolher a final tecnica.

Escolhas manuais de abrir/fechar sao locais e volateis, sem browser storage.
No recovery do mesmo resultado, escolha e restaurada apenas apos nova
validacao; pergunta/ticket/sessao/final diferentes a descartam. Native,
rejected, withheld e parsefail novos ficam abertos. Hash falho, troca de
contexto, disconnect/pagehide ou callback antigo nunca recolhem outra final.
Fechamento que esconderia o foco o transfere para um controle acessivel;
nao existe truncamento nem scroll interno da final/projecao.

Avisos de nao verificacao/sem autoridade permanecem fora da final recolhida.
Reload/recovery nao reenviam pedido; consultar usa GET. Parar de aguardar
continua interrompendo somente espera do browser, sem cancelar o Core ou
desfazer registros. Resultado de teste nao comprova verdade/qualidade.

## Evidencia desta rodada

Antes/depois medidos com o mesmo viewport390x844, pareado, sem teclado:

| Medida documental | MB234 | MB235 |
| --- | ---: | ---: |
| Topo textarea | 1215.53 px | 350.58 px |
| Borda inferior Enviar | 1670.63 px | 736.08 px |

Textarea, consentimento e Enviar operaveis na primeira tela; reducao de
934.55 px ate Enviar. Controles visiveis >=44px (checkbox tem label inteira
clicavel), sem overflow horizontal ou scroll interno. Desktop1040x900 e
viewport reduzido390x450 aprovados; isso nao e prova de teclado fisico/mobile.

45 Node novos e suite1053 passaram sem falhas/skips; 14 Python negativos
recusam harness sem opt-in/config exatos antes de require/launch. Bateria
focada121 inclui inventario, Core/renderer/parser e wrapper da suite Web.
Novo harness opcional tests/support/compact_live_web_browser.cjs usa somente
Chrome instalado/Playwright bundled explicitamente fornecidos pelo operador;
nenhuma dependencia central adicionada. --authorized exato e inputs sintéticos
em loopback proprio; nunca perfil de navegador humano.

Browser real: foco pos-pair na mensagem, summaries Enter/Espaco/Tab, escolha
manual preservada em recovery identico, final integral ao abrir disclosure,
reload/GET, uma submissao generativa e uma nativa, retorno nativo aberto,
disconnect sem conteudo, zero pageerrors. GET corrompido somente no browser
de teste recusou projecao e manteve texto bruto aberto; nao alterou Memory.
Final generativa3298 codepoints, hash UTF8 identico ao export canonico depois
de parar a instancia. Transporte injetado de teste, nenhum modelo/conta reais.
Pos-sincronizacao documental:379 inventario/UI/Core/MCP passaram, incluindo
stdio real e wrapper Web1053. Quick, CLI do inventario e diff-check aprovados.
F06 excedeu8 referencias no primeiro snapshot editado; consolidada a lista,
repetida toda a bateria afetada sem alterar schema/limites. Runtime intacto.

Primeira pergunta de teste ampliada foi contida pelo Core por limite de
autonomia: mantivemos a decisao e usamos a pergunta sintetica elegivel MB233
(que ja contem acentos). Outra tentativa encontrou Content-Length antigo
mantido pelo Playwright ao substituir JSON; removido somente no harness,
preservando headers restantes e recalculo UTF8. Provas anteriores incompletas
nao contadas como aceite. Nenhuma regra/assertion de produto foi relaxada.
Capturas antes/depois e runtimes proprios preservados em .jarvis_runtime,
ignorado por Git. Nenhum banco humano, conta/rede de modelo, mic/TTS ou push.

## Rollback

Reverter somente apresentacao compacta/disclosures para final sempre aberta
e setup completo. Sem migracao, exclusao de memoria, novo ticket ou reexecucao
de turno. F06 continua partial; criterio de produto/modelo reais e demais
frentes permanecem no inventario e backlog unicos.
