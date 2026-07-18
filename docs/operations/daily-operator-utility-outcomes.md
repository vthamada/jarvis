# Daily Operator Utility Outcomes

## Objetivo

O `MB-198` adiciona uma leitura por periodo dos resultados observaveis do Daily
Operator Loop. O relatorio correlaciona eventos governados de work items,
artefatos, retomadas de open loops e feedback com snapshots canonicos de
missao. Ele e read-only e nao cria autoridade operacional ou evolutiva.

## Uso pelo console

```powershell
python -m apps.jarvis_console operator-outcomes
```

Por padrao, o comando le:

- `.jarvis_runtime/console/observability.db`;
- `.jarvis_runtime/console/memory.db`;
- as ultimas 24 horas ate o instante de geracao.

Periodo e stores podem ser explicitados:

```powershell
python -m apps.jarvis_console operator-outcomes `
  --period-start 2026-07-17T12:00:00+00:00 `
  --period-end 2026-07-18T12:00:00+00:00 `
  --observability-db .jarvis_runtime/console/observability.db `
  --memory-db .jarvis_runtime/console/memory.db `
  --format json
```

O comando e standalone: ele nao constroi o Core, nao executa work items, nao
retoma loops e nao escreve nos stores canonicos.

## Evidencia persistivel

O tool salva `latest.json` e um historico timestamped fora dos stores
canonicos:

```powershell
python tools/daily_operator_utility_report.py
```

O destino padrao e
`.jarvis_runtime/observability/operator-utility/`.

## Definicoes das metricas

| Metrica | Definicao |
| --- | --- |
| `completion_rate` | work items que atingiram `completed` / work items unicos observados no periodo |
| `rework_rate` | work items que sairam de `completed` / work items que atingiram `completed` |
| `stale_open_loop_count` | loops ainda abertos em snapshots canonicos com missao acima de 72 horas ou timestamp desconhecido |
| `feedback_coverage` | missoes correlacionadas com feedback / missoes correlacionadas no relatorio |
| `helpful_feedback_rate` | feedbacks `helpful` / feedbacks com evento observavel |
| `average_time_to_next_action_seconds` | tempo entre `open_loop_resumed` e a primeira transicao posterior de work item ou artefato na mesma missao |

`average_time_to_next_action_seconds` e latencia observada depois da retomada.
Ela nao e economia de tempo e nao deve ser interpretada dessa forma.
`saved_time_claim_status` permanece
`not_claimed_without_controlled_baseline`.

## Limitacoes e leitura correta

- metricas sem denominador aparecem como `unavailable`, nunca como zero;
- eventos sem timestamp ou mission id valido sao registrados como limitacao;
- ausencia de evidencia apos um resume nao produz latencia artificial;
- atingir `event_limit` ou `mission_limit` declara possivel incompletude;
- relatorio historico nao usa o snapshot atual para fingir um stale-loop count
  point-in-time;
- o relatorio mede outcomes observaveis, mas nao prova causalidade nem melhoria
  sem comparacao controlada;
- nenhum resultado promove memoria, skill, workflow ou proposta evolutiva.

## Relacao com o ciclo diario

Sequencia recomendada:

1. usar `daily-workspace` para escolher a decisao humana;
2. executar a missao pelos comandos governados;
3. usar `open-loops` e `resume-loop` quando houver retomada explicita;
4. registrar feedback com `mission-feedback` quando houver experiencia valida;
5. consultar `operator-outcomes` para verificar resultados e lacunas de
   evidencia;
6. tratar limitacoes como trabalho de instrumentacao, nao como ganho.
