# knowledge-service

## Evidencia revisada request-scoped (MB228)

`source_review.LocalKnowledgeReview` fornece consentimento/revisao/confirmacao
one-shot de uma fonte fornecida (16KiB UTF-8, quote512), sem I/O ou autoridade.
`request_evidence.attach_reviewed_evidence` copia retrieval existente e anexa
somente evidencia declarada nao verificada; snippets e routing ficam intactos.
Contrato separado `shared.reviewed_knowledge` impede concatenar texto remoto a
InputContract.content ou ao corpus. KnowledgeService recebe contexto opcional
e relogio UTC confiado; defaults permanecem. Core integra Governance/Synthesis/
memoria normal, sem grants ou importacao. Runbook reviewed-source-core.md;
gate standard global Windows passou (619 novos focados/zero skips).

## Revisao lexical offline opt-in (MB220)

`knowledge_service.research` seleciona spans verificaveis de textos fornecidos,
sem fetch/corpus/registry/Core. Console `research-review` aceita stdin JSON
limitado, conteudo opt-in e validade declarada. Nao e resposta sintetizada ou
verdade verificada. Exemplos/testes: `docs/operations/local-review-products.md`.
O retrieval canonico existente nao mudou.

Serviço responsável por indexacao, retrieval e profundidade semântica.

Responsabilidades iniciais:

- registrar dominios;
- indexar conhecimento;
- sustentar retrieval estruturado.
