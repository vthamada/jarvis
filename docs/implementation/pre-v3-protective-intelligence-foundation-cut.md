# Pre-V3 Protective Intelligence Foundation Cut

## 1. Objetivo

Este documento abre a proxima frente macro recomendada depois do fechamento do
`pre-v3 hardening`.

O objetivo do recorte e construir a fundacao minima de `protective
intelligence` dentro do ecossistema do JARVIS, sem reabrir a ontologia do
sistema e sem introduzir capacidades ofensivas.

Leitura correta:

- este recorte e subordinado ao `documento_mestre_jarvis.md`;
- ele usa [protective-intelligence-architecture.md](../architecture/protective-intelligence-architecture.md)
  como arquitetura-base do eixo;
- ele nao reabre a robustez ja fechada do `v2`;
- ele prepara a primeira frente funcional nova antes do `v3`.

---

## 2. Por que esta e a proxima frente

Esta frente foi escolhida porque:

- parte de um baseline ja endurecido em dominios, memorias, mentes,
  observabilidade e gates;
- tem alto valor estrategico para o ecossistema pretendido do JARVIS;
- pode ser implementada por camadas pequenas, reversiveis e auditaveis;
- nao exige promover tecnologia externa nova a baseline central nesta fase;
- respeita a regra de seguranca governada e `through_core_only`.

Alternativas como `LifeOS`, `FinanceOS` e expansao ampla de superficie permanecem
validas, mas ficam depois desta fundacao por exigirem mais maturidade de
memoria, continuidade e governanca operacional.

---

## 3. Escopo que entra

Este recorte cobre apenas a fundacao minima do eixo:

1. contratos canonicos para caso, evidencia, achado, hipotese e sinal de risco;
2. `evidence-ledger-service` minimo com hash, proveniencia e cadeia de custodia;
3. `case-service` minimo com timeline, entidades e vinculo entre artefatos;
4. `risk-signal-service` minimo para consolidacao de risco e proximos passos;
5. observabilidade, governanca e gates minimos do novo eixo.

Principios obrigatorios:

- toda capacidade entra `through_core_only`;
- toda capacidade entra `advisory_only` por padrao;
- evidencia nao vira memoria mutavel comum;
- nenhuma acao ofensiva entra neste recorte;
- nenhuma automacao irreversivel entra sem aprovacao explicita posterior.

---

## 4. Escopo que nao entra

Nao entra neste recorte:

- retaliacao tecnica, `hack back` ou qualquer capability ofensiva;
- OSINT amplo com toolchain extensa desde o inicio;
- automacao de resposta critica em sistemas externos;
- `ProtectiveIntelligenceOS` como vertical de produto completa;
- promotoria de tecnologia externa como dependencia central;
- multimodalidade, voz, `computer use` amplo ou missao assincrona geral.

---

## 5. Ordem de implementacao

Ordem obrigatoria:

1. contratos compartilhados;
2. ledger de evidencia;
3. servico de casos;
4. servico de sinais de risco;
5. observabilidade, governanca e gate minimo do eixo;
6. documentacao viva e fechamento do lote.

Racional:

- primeiro estabilizar interfaces;
- depois introduzir persistencia e proveniencia;
- so entao conectar o eixo ao runtime observavel do sistema.

---

## 6. Relacao com o backlog micro

O micro backlog desta frente fica em:

- [execution-backlog.md](./execution-backlog.md)

Itens iniciais do lote:

- `MB-027`: contratos canonicos de `protective intelligence`;
- `MB-028`: `evidence-ledger-service` minimo;
- `MB-029`: `case-service` minimo;
- `MB-030`: `risk-signal-service` minimo;
- `MB-031`: observabilidade, governanca e gate do eixo.

Este documento abre a frente. A execucao so comeca quando o primeiro item
`ready` for puxado.

---

## 7. Criterios de pronto da frente

Esta frente so deve ser tratada como minimamente pronta quando:

- existirem contratos canonicos compartilhados para caso, evidencia, achado,
  hipotese e risco;
- evidencia tiver hash, proveniencia e trilha minima de custodia;
- casos puderem vincular timeline, entidades e artefatos;
- sinais de risco puderem ser consolidados sem sair do nucleo;
- observabilidade e gates do eixo existirem;
- `HANDOFF.md`, snapshot e backlog refletirem o mesmo estado real.

---

## 8. Decisao operacional desta rodada

Estado desta abertura:

- frente macro escolhida: `pre-v3 protective intelligence foundation`;
- documentacao aberta e backlog micro preparado;
- nenhuma implementacao do runtime foi iniciada nesta rodada.
