# Roteamento de missões com fontes como dados revisados

## Escopo

`CanonicalMissionTaskPort` é um adapter experimental de avaliação em SQLite
descartável, não uma interface de produção nem um executor de efeitos. O `brief`
literal é agora o único texto em `InputContract.content`: IDs do binding e texto
de fontes não podem contaminar a classificação lexical do Executive.

O binding permanece nos campos de identidade, sessão e request do contrato e no
`ExecutionResult`. Os demais campos de avaliação continuam no controle local do
runner. Não são anexados ao texto de intenção nem a um wrapper de inferência.

## Fronteira reutilizada

O adapter serializa **todas as fontes originais**, na ordem original, em um JSON
compacto `{"sources":[{"ref":"...","text":"..."}]}`. Essa serialização preserva
as strings e seus offsets quando o JSON é decodificado; não corrige, resume,
recorta ou escolhe subconjunto de fontes.

O bundle entra pela seam existente `ReviewedTextSource` →
`LocalKnowledgeReview` → `Core.handle_input(reviewed_knowledge=...,
knowledge_review=...)`. O review é vinculado ao principal, à sessão, ao request e
ao brief exato; o Core consome o ticket, governa a resposta e produz/persiste a
síntese final. A seleção abrange o bundle inteiro. O provider não recebe novas
instruções ou caminhos alternativos por causa deste adapter.

A URL `https://mission-evaluation.example/supplied-sources` é uma **declaração
sintética**, nunca buscada pela rede. SHA-256, byte count e timestamps representam
a observação local do bundle; não autenticam autores, origem remota ou verdade.
O opt-in de composição do host permite selecionar os fixtures. A confirmação de
review neste adapter é programática: **não é evidência de revisão humana física**.
As fontes mantêm `authority=none` e `origin_status=declared_unverified`.

## Limites explícitos

- Brief: até 2.048 caracteres Unicode, sem reescrita para satisfazer roteamento.
- Bundle completo: até 512 caracteres Unicode, **incluindo JSON, refs e escapes**.
  Não é uma cota de 512 caracteres para cada fonte.
- Limite excedido: `canonical_mission_source_limit`, antes da construção do Core
  ou escrita do runtime. Não há truncamento ou fallback para `content`.
- Padrões sensíveis conhecidos nas strings originais são recusados antes da
  serialização, para que escapes JSON não escondam padrões do filtro nativo.
  O filtro nativo de egress continua intacto. Isso não é uma garantia geral de DLP.
- A seam exige ao menos um token lexical compartilhado entre query e fonte para
  propor o review. Sem match, a execução não publica produto; não injeta o brief
  no bundle para fabricar elegibilidade.
- Apenas `analysis` sem clarificação nem operação passa pelo preflight. Outros
  intents continuam não atendidos pelo adapter; não são promovidos a análise.
- A seam generativa continua expondo apenas uma quote revisada de até 512
  caracteres, sem ampliar contratos compartilhados.

Os modelos não recebem todos os campos do binding de avaliação por esta seam;
portanto, esta correção **não resolve sozinha o envelope JSON exigido pelo grader**.
Não há inserção posterior de binding, reparo de resposta ou aceite automático de
missões. Casos maiores e efeitos reais seguem não atendidos; a mudança não
constitui aceite de campanha, melhoria de pontuação ou prova com modelo real.

## Verificação focada

Comandos de reproducao:

```powershell
python -m pytest tests/unit/test_mission_routing_limits.py tests/integration/test_mission_routing_core.py tests/integration/test_canonical_mission_port.py tests/integration/test_mission_campaign_cli_real.py -q
python tools/engineering_gate.py --mode standard
```

Os testes novos cobrem brief literal, isolamento de comandos nas fontes, seam
real com ticket consumido, readback SQLite exato, inferência fixture pelo Core,
limites 512/513, preservação Unicode e recusa antes de I/O. Não fazem chamadas
OAuth, acesso à rede, download de modelos ou efeitos de ferramentas.

Rodada integrada2026-10-18:128 focados e389 de regressao aprovados, incluindo
estes recortes. Standard Windows completo exit0:11390 passed/124 skipped,
zero falhas/errors. Contagens sao de selecoes sobrepostas, nao somar como
casos unicos. Fontes Python preservadas durante o gate; nenhum ganho de
qualidade de campanha inferido desses testes. Evidencia consolidada em
[conversa e pilotos](canonical-history-conversation-pilot-2026-10-18.md).

Rollback: reverter o adapter e os testes desta mudança. Nenhum schema de banco,
contrato compartilhado, dependência central ou dado de produção foi migrado.
