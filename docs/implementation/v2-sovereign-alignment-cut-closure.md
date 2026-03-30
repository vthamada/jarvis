# Fechamento do V2 Sovereign Alignment Cut

## 1. Objetivo

Este documento registra o fechamento formal do `v2-sovereign-alignment-cut`.

Ele existe para:

- consolidar a evidencia funcional, observavel e comparativa produzida no corte;
- declarar o que o corte efetivamente resolveu no runtime;
- classificar backlog entre `proximo_corte_v2`, `manter_deferido` e `preservar_como_visao`;
- deixar o proximo recorte do `v2` subordinado aos axis gates ja estabilizados.

---

## 2. O que o corte entregou

O `v2-sovereign-alignment-cut` fechou estas capacidades:

- `shared/domain_registry.py` como fonte soberana de roteamento runtime e refs canonicas;
- consumo explicito de memoria por classe em handoffs guiados para especialistas;
- arbitragem cognitiva soberana por `mind_registry`, com sinais observaveis e dominio puxador da arbitragem;
- identidade do nucleo auditavel ao longo do fluxo;
- especialistas guiados acima do `shadow`, ainda `through_core_only` e `advisory_only`;
- gates permanentes por eixo em observabilidade, comparacao local, piloto e gate de engenharia.

---

## 3. Evidencia consolidada

Artefatos que sustentam o fechamento:

- `tools/compare_orchestrator_paths.py`
- `tools/internal_pilot_report.py`
- `tools/evolution_from_pilot.py`
- `tools/verify_axis_artifacts.py`
- `tools/close_sovereign_alignment_cut.py`
- `.jarvis_runtime/path_comparison_v2/`
- `.jarvis_runtime/v2_sovereign_alignment_cut/`

Leitura correta da evidencia:

- `domain_alignment_status`, `memory_alignment_status`, `mind_alignment_status`, `identity_alignment_status` e `axis_gate_status` deixaram de ser sinais auxiliares e viraram criterio real de prontidao;
- `guided` passou a ser o caminho principal das rotas promovidas, deixando `shadow` como trilha comparativa legada;
- o gate de release agora depende de artefatos minimos de aderencia e do documento vivo coerente com o runtime.

---

## 4. Decisao formal do corte

Decisao do ciclo:

- o `v2-sovereign-alignment-cut` esta formalmente concluido;
- o programa continua em `v2`;
- o baseline do `v2` agora deve ser lido como runtime soberano alinhado por eixo, e nao como fase de alinhamento ainda em aberto;
- o proximo recorte do `v2` deve expandir consumidores e workflows acima desse baseline, sem reabrir a soberania interna ja fechada.

Racional:

- o maior ganho deste corte foi transformar `dominios`, `memorias`, `mentes`, `identidade` e `soberania` em contratos observaveis e governados;
- o proximo ganho do sistema nao vem de repetir esse alinhamento, e sim de usar esse baseline para consumidores de dominio mais ricos e automacao operacional mais composta.

---

## 5. Entra no proximo corte do v2

1. consumidores canonicos de dominio acima do `guided` atual;
2. camada de workflows operacionais acima do nucleo soberano;
3. benchmarks governados de `AutoGPT Platform`, `Mastra` e `Mem0` em sandbox;
4. promocao do baseline do `v2` sempre subordinada a axis gates.

---

## 6. Manter deferido

1. `computer use` amplo;
2. voz e realtime como superficie oficial;
3. `pgvector` como fundacao canonica obrigatoria;
4. promocao evolutiva agressiva do laboratorio para o nucleo.

---

## 7. Preservar como visao

1. ecossistema robusto capaz de absorver o melhor do estado da arte;
2. ecologia completa das 11 memorias;
3. ecologia completa das 24 mentes governando todo o runtime.

---

## 8. Definicao de pronto do fechamento

O corte deve ser considerado formalmente fechado quando:

- os artefatos regeneraveis em `.jarvis_runtime/v2_sovereign_alignment_cut/` existirem;
- `tools/engineering_gate.py --mode release` exigir os artefatos minimos por eixo;
- `HANDOFF.md`, `README.md` e `master-summary.md` refletirem o mesmo estado real do runtime;
- o backlog do proximo recorte estiver classificado sem reabrir soberania interna ja decidida.

---

## 9. Artefato regeneravel

O fechamento formal do corte pode ser regenerado por:

```powershell
python tools/close_sovereign_alignment_cut.py --limit 20
```

Esse comando gera:

- `.jarvis_runtime/v2_sovereign_alignment_cut/cut_closure.json`
- `.jarvis_runtime/v2_sovereign_alignment_cut/cut_closure.md`
