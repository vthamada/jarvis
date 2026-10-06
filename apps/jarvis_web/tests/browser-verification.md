# Verificação de browser — 2026-10-02

Escopo: cockpit fixture servido pelo próprio `serve.py` em porta efêmera,
Codex in-app browser em segundo plano, sem conexão ao Core/provider. Esta
verificação não prova inferência, execução de ferramenta ou autorização real.

Observado por DOM/accessibility tree e screenshots:

- Desktop: conversa, contexto e composer presentes, com painéis escuros,
  status fixture e inspeção read-only.
- Viewport mobile 390 × 844: conteúdo em coluna única e navegação rolável;
  `clientWidth = scrollWidth = 375` após descontar a scrollbar. Sem overflow
  horizontal de documento. Reiniciar permanece acessível no cabeçalho.
- Envio de `<img src=x onerror="alert(1)">` aparece literalmente como texto;
  o DOM mantém zero elementos `img`. Não foi executado como HTML.
- Envio mostra loading e depois resposta explicitamente simulada.
- Cenário de falha apresenta mensagem recuperável, estado `error` e atividade
  de fixture; nenhuma resposta final fabricada.
- Ctrl+Enter envia; Cancelar descarta o callback e preserva estado `cancelled`.
- Inspecionar proposta abre dialog com `Somente inspeção`; nenhum controle
  autoriza ou executa. Esc fecha e retorna foco ao botão de inspeção.
- Reiniciar retorna a dois itens de conversa e cenário default.

Durante essa verificação corrigimos overflow mobile e reposicionamos o reset
para continuar disponível no mobile. A inspeção de respostas incompletas e
vazias, identidade trocada e callback obsoleto é coberta pela suíte Node.
Viewport temporário foi restaurado, tab de teste fechado e servidor de teste
encerrado. Nenhum processo de longa duração é necessário para os testes.

A revisão cruzada posterior adicionou denial de headers Host duplicados e
guards após dispose, além de preservar subscribers no retorno de BFCache;
esses casos passaram na suíte automatizada. Não são alegados como teste de
BFCache real no browser: o fluxo de lifecycle foi exercitado no controller.

Reproduzir: executar servidor conforme README, visitar endereço loopback,
repetir envios/cenários e inspecionar no mobile. Não substituir essa verificação
por abrir HTML com servidor genérico na raiz do repositório.

## Segunda onda: importação de snapshot

O DOM inicial da nova superfície, incluindo input de arquivo e aviso de origem
não verificada, foi confirmado em tab Chrome exclusiva de teste em loopback.
O browser in-app estava indisponível nessa rodada. A automação do file chooser
não completou e foi interrompida; portanto **importação do arquivo no browser
não foi verificada**. Não alegamos confirmação visual do snapshot importado.

A integração offline exporter do Core -> JSON -> validator/controller Web foi
testada pelo coordenador em `tests/integration/test_surface_snapshot_export.py`.
Isso valida dados e estados, não substitui o smoke completo do picker/DOM.
Tab Chrome exclusiva foi fechada e servidor efêmero próprio encerrado após a
interrupção; nenhuma tab do operador nem seu servidor in-app foi alterado.
