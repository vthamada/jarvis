# V1 Roadmap

## 1. Objetivo

Este documento preserva o roadmap do `v1` do JARVIS em nivel tatico como referencia historica.

Leitura importante no estado atual do repositorio:

- este roadmap permanece como historico do fechamento do `v1`;
- o planejamento ativo do `pos-v1` em diante fica em:
  - `docs/roadmap/programa-ate-v3.md`
  - `docs/archive/implementation/post-v1-sprint-cycle.md`

---

## 2. Estrutura do roadmap

O `v1` foi organizado em seis milestones:

1. `M1` - fundacao estrutural
2. `M2` - nucleo central funcional
3. `M3` - memoria e continuidade uteis
4. `M4` - conhecimento e operacao minima real
5. `M5` - governanca robusta e observabilidade
6. `M6` - consolidacao do `v1` e preparacao para `v2`

---

## 3. Leitura correta hoje

As milestones representam saltos estruturais de capacidade que levaram ao baseline encerrado do `v1`.

Leitura historica consolidada:

- `M1`: concluida
- `M2`: substancialmente implementada
- `M3`: substancialmente implementada
- `M4`: parcialmente implementada, no recorte correto do `v1`
- `M5`: substancialmente implementada
- `M6`: concluida no escopo do `v1`, com baseline congelado e uso controlado autorizado

---

## 4. Resultado estrutural do v1

O corte final do `v1` entregou:

- nucleo unificado funcional;
- memoria persistente com backend oficial em `PostgreSQL`;
- governanca suficiente para uso controlado;
- observabilidade auditavel com trilha local primaria;
- operacao textual de baixo risco;
- `jarvis-console` como interface textual minima;
- `evolution-lab` inicial em `sandbox-only`.

O que ficou explicitamente fora do `v1`:

- `LangGraph` como runtime principal do nucleo;
- memoria semantica profunda;
- web, voz e multimodalidade ampla;
- ecossistema amplo de especialistas;
- autoevolucao promotiva.

---

## 5. Relacao com o pos-v1

O roadmap do `v1` nao deve mais ser usado como plano ativo de implementacao.

Ele existe para:

- preservar a sequencia correta que levou ao baseline atual;
- explicar o recorte do `v1`;
- impedir que o `pos-v1` reabra escopo ja encerrado sem necessidade real.

O trabalho novo agora deve seguir:

- `docs/roadmap/programa-ate-v3.md`
- `docs/archive/implementation/post-v1-sprint-cycle.md`
