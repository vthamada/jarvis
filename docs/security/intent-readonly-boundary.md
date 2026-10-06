# Fronteira lexical de intenção e pedidos read-only

Este slice corrige roteamento, não concede autorização operacional nem comprova
qualidade de resposta com modelo real. A interpretação lexical permanece uma
heurística limitada; ela não é um parser de linguagem natural.

## Limites preservados

- Preparar um artefato textual (`draft`/`prepare`/`gerar`) não equivale a executar
  uma operação. Análise com essas palavras não deve gerar clarificação apenas
  pelo verbo de redação.
- Uma negação local pode restringir roteamento, mas não autoriza outro comando.
  Comandos positivos em outras cláusulas continuam exigindo contenção.
- Planejamento explicitamente read-only não solicita despacho operacional.
- Risco é inspecionado sobre o texto completo. Negação, código e citação não
  removem marcadores destrutivos nem promovem uma intenção sensível.
- Citações, instruções de fonte, negação indireta/dupla, caracteres de controle
  ambíguos e entradas acima do limite não podem ampliar autoridade operacional.
- `assist_only`, Governance, Memory canônica e Synthesis continuam soberanos.
  A diretiva lexical não substitui recibo de confirmação, grant ou decisão final.

## Evidência reproduzível

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_intent_scope_adversarial.py tests/integration/test_intent_scope_core_flow.py -q
```

A bateria independente cobre inglês e português, redação versus operação,
negação local versus comandos mistos, risco em conteúdo citado/negado, controles
e limites. O fluxo ponta a ponta usa apenas SQLite temporário e conteúdo sintético.
Intercepta as entradas de execução Operational; exige ausência de despacho,
resultado operacional, grant e claim de ação. Compara o retorno de Synthesis com
o texto realmente persistido na interação canônica e verifica que os eventos de
governança, síntese e memória foram persistidos.

O controle anterior ao patch confirmou que um pedido de comparação com `draft`
e `No purchase or tool execution` caía em `clarification_only` e
`explicit_confirmation_required`, com Governance `allow_with_conditions`.
Planejamento read-only ainda roteava para `plan_and_operate`, contido pela escada
de autonomia em vez de pela intenção. Essa evidência não implica que seja correto
alterar Governance globalmente: os testes não exigem `allow` nos pedidos benignos.

## Não demonstrado

Não há prova de compreensão semântica geral, autenticação, produção útil do
artefato solicitado, execução autorizada, qualidade em corpus aberto ou promoção
de capability. Nenhum harness/grader é flexibilizado por este slice. Nenhuma conta,
modelo externo, dado humano, ambiente Linux ou repositório humano é usado nos
testes. O gate global e a documentação de estado permanecem responsabilidade da
integração da rodada.
