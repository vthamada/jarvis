# Confirmação verificável de ação

Status: baseline operacional do `MB-212`.

## Objetivo

O fluxo de confirmação vincula uma decisão humana a uma ação local exata antes
de qualquer efeito físico. Ele não transforma a confirmação em permissão: a
autoridade continua sendo composta pela governança, pelo limite de autonomia e
pelo executor soberano.

## Cadeia de evidência

1. O runtime prepara um `ActionIntentContract` com identidade da requisição,
   sessão, missão, operador, handler, operação, alvo lógico, digests, risco,
   política, nonce e janela de validade.
2. A governança persiste atomicamente o intent, o dispatch preparado exato e
   o challenge imutável.
3. O operador confere o `action_fingerprint` e registra uma confirmação exata.
4. A governança persiste um receipt imutável, de uso único e sem autoridade.
5. Um envelope de apresentação fornece obrigatoriamente o receipt e o
   `origin_request_id` original. Ele seleciona o dispatch persistido; não cria
   nem substitui a ação confirmada.
6. Antes do efeito, o orquestrador recompõe a identidade da ação e reclama o
   receipt atomicamente.
7. Imediatamente antes da escrita, o serviço operacional reabre e verifica a
   claim exata. Só então o handler pode executar.

Intent, challenge, receipt e claim mantêm explicitamente:

- `single_use=True`;
- `read_only=True`;
- `immutable=True`;
- `execution_allowed=False`;
- `tool_dispatch_allowed=False`;
- `runtime_activation_allowed=False`;
- `promotion_authorized=False`;
- `automatic_promotion_allowed=False`;
- `core_mutation_allowed=False`.

## Uso pelo console

Prepare a ação com identidade e limites explícitos:

```powershell
python -m apps.jarvis_console ask "Prepare the bounded local action." --session-id demo --mission-id mission-demo --operator-identity-ref operator://local_console --requested-autonomy-level supervised_external_action --max-autonomy-level supervised_external_action --autonomy-confirmation-mode explicit
```

Quando a resposta trouxer `challenge_id`, `origin_request_id`,
`action_fingerprint` e `expires_at`, confira esses valores e registre a
atestação:

```powershell
python -m apps.jarvis_console action-confirm --challenge-id <challenge-id> --action-fingerprint <action-fingerprint> --operator-identity-ref operator://local_console
```

Apresente a ação em um novo envelope, preservando prompt, sessão, missão,
identidade e limites, e forneça obrigatoriamente receipt e origem:

```powershell
python -m apps.jarvis_console ask "Prepare the bounded local action." --session-id demo --mission-id mission-demo --operator-identity-ref operator://local_console --requested-autonomy-level supervised_external_action --max-autonomy-level supervised_external_action --autonomy-confirmation-mode explicit --action-confirmation-receipt-id <receipt-id> --origin-request-id <origin-request-id>
```

O comando `action-confirm` é mutante e aceita apenas saída textual. A resposta
não mostra conteúdo da ação, destino físico nem caminho absoluto.

O novo `ask` é somente o transporte da apresentação. O planejamento candidato
feito para esse envelope não substitui o dispatch confirmado e é descartado no
momento do claim. O runtime carrega o dispatch original pelo par explícito
receipt/origem, revalida sessão, missão, operador, fingerprint, validade,
handler e versão de política, e só então o executor reaplica seus limites atuais.
Essa escolha evita depender de um replanejamento que pode mudar legitimamente
com memória e continuidade entre reinícios.

## Persistência e contenção

O console iniciado com seu diretório de runtime usa `governance.db` para o
ledger append-only de confirmação. O dispatch preparado também fica vinculado
ao intent por fingerprint e sobrevive a retry e reinício. O mesmo objeto de
governança fornece o verificador ao serviço operacional, evitando stores ou
critérios divergentes.

O escritor local legado permanece contido no diretório de artefatos configurado
pelo runtime. Um destino físico fornecido pelo chamador não deve substituir
essa raiz. O fingerprint da ação já vincula os bytes derivados exatos, a raiz
canônica, o digest de precondição e o risco. Preflight do estado físico,
verificação física da precondição, proteção contra TOCTOU, escrita transacional
e rollback físico pertencem aos slices posteriores.

## Falha segura

O efeito deve permanecer bloqueado quando qualquer uma destas condições ocorrer:

- challenge ou receipt desconhecido, adulterado ou expirado;
- identidade do operador divergente;
- fingerprint, origem, sessão, missão, operação ou intent divergente;
- receipt apresentado sem o `origin_request_id` original explícito;
- receipt já confirmado ou já reclamado;
- claim ausente, incompleta ou rejeitada pelo verificador;
- erro de persistência ou indisponibilidade do verificador.

Uma claim consumida não é reutilizada mesmo se uma etapa posterior falhar. Uma
nova tentativa exige novo intent, challenge e confirmação.

## Limite de autenticidade

Neste corte, `action-confirm` registra uma atestação local declarada pelo
operador. Ele não prova presença física, biometria, posse criptográfica ou
autenticidade externa da identidade. Por isso, o receipt nunca é autoridade
isolada e não pode liberar execução fora da cadeia governada.

## Rollback operacional

Para desativar o fluxo, deixe de emitir ou consumir receipts e mantenha ações
que exigem confirmação em estado bloqueado. Não apague nem reescreva o ledger:
a evidência histórica deve permanecer auditável. Ações que não exigem
confirmação continuam sujeitas às políticas normais de governança e autonomia.
