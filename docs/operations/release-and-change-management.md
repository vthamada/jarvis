# Release And Change Management

## 1. Objetivo

Este documento operacionaliza a política de **releases, versionamento e mudança controlada** do JARVIS.

Ele deriva principalmente de:

- `documento_mestre_jarvis.md`, capítulo `345. Estratégia de releases, versionamento e mudança controlada`

Seu papel é transformar a política arquitetural de mudança em prática operacional mínima.

---

## 2. Princípios

Toda mudança relevante no projeto deve ser:

- explicitamente versionada;
- rastreável;
- validada antes de promoção;
- reversível quando aplicável;
- avaliada quanto a impacto em contratos, memória e governança.

---

## 3. Classes de mudança

Mudanças devem ser registradas como:

- editorial;
- estrutural sem impacto contratual;
- contratual compatível;
- contratual incompatível;
- operacional;
- governança;
- evolutiva em sandbox;
- promoção evolutiva.

---

## 4. O que deve sempre ser registrado

Para cada mudança relevante, registrar:

- data;
- artefato afetado;
- natureza da mudança;
- motivação;
- impacto esperado;
- risco conhecido;
- forma de validação;
- rollback previsto, quando aplicável.

---

## 5. Versionamento mínimo

Aplicar versionamento explícito em:

- serviços;
- contratos;
- políticas de memória crítica;
- regras de governança;
- componentes promovidos via evolução.

---

## 6. Gates antes de promover mudança

Nenhuma mudança relevante deve ser promovida sem:

- revisão do impacto técnico;
- verificação de contratos afetados;
- testes mínimos aplicáveis;
- análise de risco;
- validação em ambiente compatível com o nível de risco.

---

## 7. Regimes de promoção

Mudanças podem seguir:

- promoção direta de baixo risco;
- promoção gradual;
- promoção condicionada por observação reforçada;
- retenção em sandbox até nova evidência.

---

## 8. Rollback

Toda mudança relevante deve responder:

1. o que volta ao estado anterior?
2. como a reversão será feita?
3. há impacto em memória, estado ou contrato?
4. qual é o gatilho para reverter?

---

## 9. Relação com CHANGELOG e HANDOFF

Usar:

- `CHANGELOG.md` para registrar mudança relevante já consolidada;
- `HANDOFF.md` para registrar impacto operacional e próximos passos;
- Documento-Mestre para regras canônicas e políticas normativas.

---

## 10. Critério prático

Se a mudança altera:

- identidade;
- governança;
- memória crítica;
- autonomia;
- contrato compartilhado;
- operação produtiva;

então ela não deve ser tratada como mudança rotineira simples.
