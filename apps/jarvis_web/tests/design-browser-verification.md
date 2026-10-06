# Verificação do redesign Web — 2026-10-04

Pedido: frontend ainda precisa melhorar bastante. Escopo: apresentação do
cockpit isolado, não integração Core, inferência, autorização ou aceite estético.
Servidor próprio `serve.py`, loopback/porta efêmera65238, IAB real. Não houve
restart do servidor humano8765, acesso a banco/credenciais ou WAV do dublador.

## Observado no browser

- Desktop1440x900: coluna de navegação, conversa central com esfera sem card,
  contexto secundário; campo de pedido e botão visíveis na abertura (bottom
  do botão877.9px). `clientWidth=scrollWidth=1425`, descontada scrollbar.
- Tablet900x900: nav horizontal, conversa/contexto em duas colunas;
  `clientWidth=scrollWidth=885`. Screenshot conferido após navegar/testar,
  sem afirmar que o campo inicialmente cabe na primeira dobra de tablet.
- Mobile390x844: coluna única, nav em duas linhas, anchors44px de altura;
  `clientWidth=scrollWidth=375`, antes e após pedido. Não há scroll horizontal
  de documento ou scrolls internos de histórico/painéis. Campo abaixo da
  primeira dobra no mobile, alcançável por scroll normal.
- “Organizar próximos passos” preenche o composer e move o foco; mantém os
  dois itens de fixture e histórico recolhido. Não envia automaticamente.
- Enviar mostra loading, abre histórico, compacta a esfera, oculta exemplos;
  depois mostra completed **fixture**, quatro mensagens e aviso de nenhum
  resultado real. Ctrl+Enter também funcionou no mobile.
- Texto `<img src=x onerror="alert(1)">` permaneceu literal, zero elementos img.
- Inspecionar proposta abre dialog somente leitura; fechar devolve foco ao
  botão de inspeção. Nenhuma autorização/execução apareceu.
- Link “Voz · ensaio” abriu details antes de navegar e atualizou seleção.
  Permissão de ensaio -> captura simulada -> revisão disponível -> descarte;
  nenhum mic/STT/TTS real foi usado. Reset revogou permissão, zerou campo,
  restaurou dois itens, histórico fechado e presença idle/level0.
- “Esfera + áudio local” expandido: picker de WAV sintético de12s -> ready
  sem reprodução automática -> clique Reproduzir -> speaking_local/level0.015
  -> Interromper/Remover -> idle, controles desabilitados, sem arquivo.
  Não é teste perceptual de clonagem ou fala ao vivo do Core.
- “Dados da sessão” expandido: picker da fixture JSON versionada do repositório
  importou objetivo/metadados offline e aviso origem não verificada; não trocou
  identidade da conversa nem trouxe challenge/grant. Esta rodada verifica o
  picker/DOM que não havia sido confirmado em uma rodada anterior.
- Console warn/error vazio durante o smoke. Servidor/CSP/allowlist inalterados.

Não houve automação de BFCache, mídia reduced-motion real ou teste exaustivo de
leitor de tela nesta rodada; lifecycle/reduced-motion continuam cobertos pela
suíte JS. Contratos DOM não substituem este smoke nem garantem qualidade visual.

52 testes JS e39 Python Web passaram; gate standard global Windows passou
(mojibake, guardrails documentais, ruff e pytest). Nenhuma capability promovida.

Screenshots locais fora do Git/OneDrive em Codex visualizations, pasta
`redesign-20261004`: `desktop.jpg`, `mobile.jpg`. Viewports temporários
restaurados antes da entrega; tab da prévia permanece como artefato.
Reproduzir: README operacional, visitar loopback e repetir os fluxos acima.
