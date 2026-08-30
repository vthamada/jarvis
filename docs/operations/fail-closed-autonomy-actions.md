# Autonomia fail-closed por ação

Status: baseline operacional do `MB-213`.

## Objetivo

A escada de autonomia agora decide uma ação canônica completa, e não apenas um
nível textual. A mesma política é aplicada pela Governança, pelo Orquestrador e
novamente pelo serviço operacional imediatamente antes de qualquer escrita.
Confirmação, receipt ou claim nunca ampliam nível, capability ou tipo de ação.

## Matriz operacional

| Nível efetivo | Ação local reversível | Ação externa | Confirmação mínima |
| --- | --- | --- | --- |
| `assist_only` | bloqueada | bloqueada | nenhuma confirmação transforma guidance em execução |
| `confirm_before_action` | permitida somente após confirmação exata | bloqueada | obrigatória |
| `bounded_core_action` | permitida após governança; modo explícito mais estrito continua válido | bloqueada | não obrigatória por padrão |
| `supervised_external_action` | permitida somente após confirmação exata | política admite preparação, mas o runtime atual bloqueia porque não há adapter externo registrado | obrigatória |

`irreversible_action`, `automatic_promotion` e `core_mutation` permanecem
globalmente bloqueadas em todos os níveis.

## Projeção obrigatória

Uma ação operacional só pode avançar quando todos os campos formam uma projeção
coerente:

- níveis solicitado, máximo e efetivo conhecidos e consistentes;
- status da escada compatível com o rebaixamento calculado;
- `autonomy_action_kind` canônico;
- capability selecionada conhecida, dentro do máximo e forte o bastante para a
  ação (`local` para efeito local e `supervised_external` para efeito externo);
- listas allowed/blocked idênticas à política do nível;
- modo e indicador booleano de confirmação coerentes;
- ausência de erros de validação herdados.

Valor ausente, desconhecido, contraditório ou projetado por um caller resulta em
`invalid_fail_closed` ou decisão `block`. Para ações de preparação ou execução,
a ausência simultânea dos modos solicitado e planejado também bloqueia. Um modo
explícito mais estrito pode elevar uma ação bounded para confirmação, mas nunca
reduzir a exigência mínima da política.

## Decisão compartilhada

`evaluate_autonomy_action(...)` produz uma decisão imutável e total:

- `allow`: a projeção é válida; `side_effect_allowed` só é verdadeiro para um
  action kind executável permitido;
- `require_confirmation`: a ação pode ser preparada, mas não produzir efeito;
- `block`: nenhum dispatch ou writer pode ser alcançado.

Os campos de autoridade permanecem falsos: a decisão não autoriza promoção,
mutação do Core, ativação de runtime nem dispatch de ferramenta por si só.

## Pontos de enforcement

1. O Planejamento recomenda capability e modo, sem autoridade executiva.
2. A escada deriva a projeção efetiva a partir do pedido explícito e do plano.
3. A Governança bloqueia projeções inválidas ou condiciona ações que exigem
   confirmação.
4. Native e LangGraph usam o mesmo predicate para decidir se uma operação pode
   ser preparada.
5. Ação externa sem adapter é bloqueada antes de challenge ou claim.
6. O Orquestrador revalida o dispatch persistido e a claim exata.
7. O serviço operacional exige `allow` e `side_effect_allowed` imediatamente
   antes do writer.

## Falha segura e rollback

Em dúvida, configure ou derive `assist_only`, mantenha adapters desabilitados e
preserve apenas guidance/read-only. Nunca restaure defaults que inferem poder a
partir de nível, capability, ação ou confirmação ausentes.

O rollback deste slice é lógico: interromper preparação e execução, mantendo
ledger, eventos e artefatos históricos para auditoria. O rollback físico de
arquivos ainda pertence aos slices de adapter transacional posteriores.

## Limites conhecidos

`MB-214` passou a registrar grants exatos por adapter/operação/recurso, mas o
descriptor continua `prepare-only`: não existe adapter físico, preflight,
journal ou rollback de arquivo neste ponto. Essas responsabilidades começam em
`MB-215`; a política desta página permanece uma condição adicional e nunca pode
ser substituída pelo grant.
