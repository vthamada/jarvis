# OpenMausBot: avaliação para o JARVIS

Data: 2026-10-20. Classificação: **usar como referência**, com candidatos a
absorção posterior. Nenhuma capability foi promovida por este estudo.

## Conclusão

O OpenMausBot é útil principalmente como referência de **produto operacional**:
interface acompanhando trabalho real, múltiplos motores, aprovações, intervenção
humana, retomada de tarefas e controle de browser/computador. Há implementação
substancial dessas peças, não somente uma apresentação visual.

Não recomendo incorporar o aplicativo inteiro nem substituir o Core do JARVIS.
O produto delega boa parte da agenticidade a agentes externos completos, enquanto
o JARVIS deve manter governança, memória canônica e síntese final próprias. O
ganho imediato é traduzir mecanismos pequenos para nossos contratos e testar
separadamente cada fronteira; não copiar a frota de CLIs como cérebro.

## Alvo e método

- Repositório: [milind-soni/OpenMausBot](https://github.com/milind-soni/OpenMausBot).
  O ponto ao final do link enviado foi interpretado como pontuação.
- Revisão examinada: [`1db45cab1266a3cf34728dd69833675e67223a06`](https://github.com/milind-soni/OpenMausBot/commit/1db45cab1266a3cf34728dd69833675e67223a06),
  resolvida de `main` em 2026-10-20. Todos os links de código abaixo estão fixados
  nessa revisão, não na branch mutável.
- Inspeção estática de README, manifests/licenças e caminhos de drivers, eventos,
  permissões, sessões, tarefas, browser, VM, voz e avaliação. A árvore consultada
  tinha 4.587 entradas e não estava truncada. Isso não equivale a uma auditoria
  integral das 4.587 entradas.
- Não houve instalação, execução de código externo, login, chamada a modelos,
  criação de VM, exposição de portas ou teste de segurança dinâmico. Conteúdo do
  repositório foi tratado como dado, não como instrução para este ambiente.

As comparações comerciais com Muse, dots, Grok Bot e Manus no README são
alegações do projeto, **não um benchmark independente** e não foram usadas para
concluir superioridade do harness.

## O que existe no código

| Área | Evidência inspecionada | Leitura para o JARVIS |
| --- | --- | --- |
| Motores e protocolos | [Registry de drivers](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/drivers/builtIn.ts) registra Claude/Codex, ACP e provedores API. [Contratos](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/contracts.ts#L83) separam envio, capacidade, cursor e interrupção. | Um contrato comum com capacidades explícitas é valioso. Instância indisponível não precisa derrubar os demais motores. Não implica equivalência entre todos os drivers. |
| Codex como agente externo | [Driver Codex](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/drivers/codex.ts#L324) inicia sessões por app-server JSON-RPC, reafirma permissões e verifica a sandbox resolvida. | Referência de isolamento e compatibilidade. Não resolve automaticamente o transporte OAuth do JARVIS nem autoriza reutilizar credenciais/configurações de outro aplicativo. |
| Loop API | [Loop OpenAI-compatible](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/drivers/openai-chat.ts#L613) itera chamadas estruturadas, resultados e resposta, com tetos. [Parser](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/drivers/openai-chat-protocol.ts) rejeita deltas/chamadas malformados. | Útil comparar terminação, identificação e classificação de erros. Os limites de 64 rodadas/200 ferramentas não devem substituir nossos limites autorizados. |
| Eventos e UI | [Bus](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/harness/bus.ts) normaliza eventos, agrega deltas e grava NDJSON redigido; [replay SSE](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/host/sse-replay.ts) limita retenção e detecta lacunas. | Boa referência de UI acompanhando eventos do runtime, em vez de animação representar execução inexistente. Replay de interface não é retomada do executor. |
| Permissões | [Gate de aprovação](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/drivers/chat-tool-approval.ts) distingue pergunta/aprovação e fecha pedidos em abort/timeout. [Escopo de ferramentas](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/shared/tool-scope.ts) valida seletores e precedência de exclusão. | Absorver os estados/falhas como referência; a aprovação humana continua pertencendo à governança do JARVIS. Catálogo visível não é autorização para execução. |
| Tarefas e reinício | [Store SQLite](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/runtime/store.ts) guarda atribuições/eventos/inbox. [Reconciliação](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/runtime/runtime.ts#L75) diferencia trabalho distribuído, efeito externo registrado, pergunta pendente e rerun. | Referência relevante para F05; exige tradução para nossos recibos, CAS/fencing e estados incertos. Não há prova aqui de exactly-once genérico de efeitos externos. |
| Browser e intervenção | [Refs DOM](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/browser/cdp/refs.ts) não reciclam números e invalidam referências; [controle por perfil](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/browser/control.ts) recusa inclusive leituras do bot durante takeover humano. | Referência forte para F09: alvo obsoleto, mudança de controle, segredo digitado pelo usuário e resultado tardio. Ainda exige navegador/fixture reais no JARVIS. |
| VM/computador | [Lease de VM](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/local-vm-lease.ts), [pool de assentos](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/local-vm-seat-pool.ts) e [controle humano](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/computer-control.ts) modelam contenção e posse. | Referência para F10; não prova isolamento físico ou segurança de telas neste Windows. Um lease em memória não substitui nosso fencing durável. |

## Pontos especialmente úteis para nossas pendências

### Continuação e finalização

O OpenMausBot também [recusa um ID de ferramenta repetido](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/drivers/openai-chat.ts#L728).
Portanto, remover nossa recusa não é a lição a extrair. O projeto acrescenta
nudges limitados para respostas que anunciam uma ação mas não chamam ferramentas;
isso é distinto de repetir automaticamente operações já executadas.

O [handoff ao esgotar orçamento](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/turn-continuation.ts)
registra contexto para continuidade e classifica somente certos términos por
limite como continuáveis. O texto do handoff não constitui recibo de efeito.
Para o JARVIS, a próxima experiência deve medir as fases da latência e conservar
orçamento/finalização explícitos; este estudo **não comprova** que um nudge ou
tetos maiores solucionaria nosso piloto Qwen.

### F05 — tarefas duráveis

Reaproveitar conceitualmente uma árvore explícita de atribuições e resultados,
uma inbox durável e estados distintos para `needs_input`, espera e término.
No código inspecionado, reinício pode reencaminhar uma execução interrompida sem
efeito externo registrado; quando há efeito externo registrado, interrompe essa
via. A segurança depende da completude desse registro. Adoção no JARVIS deve
exigir prova de crash antes/depois do dispatch e depois do efeito, recibo exato,
reconciliação e ausência de replay incerto — não uma cópia do estado `rerun`.

### F06 — Web UI

Prioridade é tornar visíveis trabalho real, bloqueio, pedido de aprovação,
interrupção e resultado canônico. O replay SSE bounded e o estado de log incompleto
são boas referências de falha honesta. Não absorver o aplicativo Electron/React
inteiro nem confundir streaming do provedor com resposta final aprovada.

O bus continua entregando atualizações ao vivo quando a escrita do log falha e
informa a incompletude. Isso pode servir como UX degradada, mas **não** autoriza
o JARVIS a promover sucesso auditável sem sua evidência canônica obrigatória.

### F09/F10 — browser e computador

Absorver primeiro observação, vínculo de alvo, invalidação de refs e takeover
humano. Depois, em outro slice autorizado, input governado com cancelamento e
resultado tardio. A [saída de rede via SOCKS](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/browser/egress/gate.ts)
resolve e conecta somente endereços aprovados pela política, uma referência
melhor que validar apenas a URL inicial.

A [política desktop](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/browser/egress/policy.ts#L110)
admite rede local conforme configuração e destinos locais em condições próprias;
ela parte de uma confiança diferente da leitura credentialless delimitada do
JARVIS. Não copiar esses defaults. Aprovar leitura pública não habilita LAN,
cookies, autenticação, downloads, formulários ou ações.

### Voz, MCP e modelos — complementos, não troca do núcleo

- O [player](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/src/lib/tts/index.ts)
  pré-busca o próximo trecho enquanto toca o atual e usa token/abort para impedir
  playback tardio. A [preparação de fala](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/tts/speech-text.ts)
  separa texto audível de sintaxe de tela. São referências de fluidez.
- O [adapter Chatterbox](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/tts/chatterbox.ts)
  consome um servidor de voz existente; ele não treina nem comprova a qualidade
  de uma clonagem PT-BR de Eduardo Borgerth. Não resolve a qualidade da referência
  de voz do JARVIS por si só.
- O [MCP externo documentado](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/docs/mcp-server.md)
  separa inspeção/coordenação de concessões humanas. É um bom princípio; não
  conectar este MCP nesta rodada, porque isso criaria outro executor completo.
- O [driver OpenAI-compatible](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/drivers/openai-compat.ts)
  e a sinalização de capacidades interessam a modelos locais/remotos. A seleção
  de origem, credencial, egress e orçamento deve continuar explícita no JARVIS.

## Riscos e o que não importar

1. **Licença mista:** [LICENSE](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/LICENSE)
   é Apache-2.0; [LICENSING.md](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/LICENSING.md)
   exclui `enterprise/`, cuja [licença própria](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/enterprise/LICENSE)
   restringe produção e redistribuição. Não importar essa pasta. Eventual cópia
   de OSS exige preservar notices e analisar também as licenças de terceiros e
   marcas. Nenhum código foi copiado neste estudo.
2. **Credenciais:** a [configuração de motores](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/docs/custom-engines.md)
   documenta secrets em texto claro em `config.json` com modo Unix `0600`.
   Isso não é armazenamento cifrado e o modo Unix não comprova ACL no Windows.
   Não importar contas, tokens, config ou permissões; manter o store privado do
   JARVIS fora do repositório/OneDrive.
3. **Orçamento e repetição:** há [retry transitório](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/drivers/retry.ts)
   e correções/nudges configuráveis. Não aplicar automaticamente a campanhas em
   que o usuário autorizou uma única tentativa, teto específico ou parada na
   primeira falha. Cancelamento, recusa e efeito incerto nunca viram nova licença
   para executar.
4. **Modelo não vira autoridade:** os modos Full/Auto do produto e a execução
   nativa de agentes completos não devem contornar o Core, a governança ou a
   síntese do JARVIS. Registrar uma ferramenta não a torna aprovada.
5. **Complexidade:** o [composition root](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/index.ts)
   é extenso; a [documentação de módulos host](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/server/host/README.md)
   registra sua decomposição. Importar o servidor inteiro adicionaria grande
   acoplamento e superfície de manutenção, sem prova de resolver nosso gargalo.

## Decisão e sequência recomendada

| Decisão | Mecanismo | Critério antes de promoção |
| --- | --- | --- |
| Usar como referência agora | IDs/terminals, estado incerto, eventos verdadeiros e replay com lacuna | Preservar contratos atuais; testes de finalização, cancelamento e export canônico |
| Absorver depois — F05 | Árvore de atribuições/inbox e recuperação discriminada | Crash/restart com SQLite real, recibos, fencing e nenhum replay de efeito incerto |
| Absorver depois — F06 | Atividade/approvals/streaming derivados do runtime | UI e Core reais, desconexão/reconnect, resposta canônica exata e dados sensíveis ausentes |
| Absorver depois — F09/F10 | Refs invalidadas, takeover, contenção e egress por conexão | Fixture controlada, mudança de alvo/foco, segredo durante takeover, cancelamento e teste físico |
| Rejeitar nesta integração | Substituir o Core por OpenMausBot/CLIs, copiar enterprise/ ou importar contas/defaults permissivos | Incompatível com o recorte e as fronteiras atuais |

Para comparar comportamento, o [programa de evals](https://github.com/milind-soni/OpenMausBot/blob/1db45cab1266a3cf34728dd69833675e67223a06/evals/README.md)
separa cenários determinísticos, replay redigido e smoke de modelo real opt-in.
Isso é um desenho de evidência aproveitável, não um placar observado: os testes
externos não foram executados e sua quantidade não comprova qualidade do modelo.

Resultado deste recorte: **análise estática concluída; integração de OpenMausBot
não realizada nem autorizada como substituto do harness**. A absorção do REA é
outra frente, com contrato/implementação e evidência próprios.
