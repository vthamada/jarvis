# Internal Pilot Plan

## 1. Objetivo

Este plano define a janela mínima do `internal pilot` do JARVIS `v1` após o `GO CONDICIONAL`.

O objetivo não e ampliar escopo. O objetivo e coletar evidência operacional real em ambiente controlado.

---

## 2. Escopo autorizado

Durante o piloto, limitar o uso a:

- planejamento;
- análise estruturada;
- produção de artefato textual;
- continuidade simples de sessão e missão.

Ficam fora do piloto:

- automação irreversivel;
- mutação livre de memória crítica;
- promoção evolutiva;
- expansao de operadores ou especialistas externos.

---

## 3. Gatilhos obrigatorios antes de iniciar

Antes da janela do piloto:

- `python tools/validate_v1.py --profile controlled`
- `python tools/go_live_internal_checklist.py --profile controlled`
- `python tools/internal_pilot_report.py --limit 5`

O ultimo comando deve produzir relatório vazio ou refletir apenas trilhas esperadas do ambiente atual.

---

## 4. Evidência mínima a coletar

Para cada request observada:

- `request_id`;
- decisão de governança;
- status operacional;
- eventos ausentes da trilha mínima;
- duracao do fluxo;
- anomalias percebidas pelo operador.

O relatório base deve ser extraido por:

```powershell
python tools/internal_pilot_report.py --limit 10
```

---

## 5. Critério de sucesso da janela inicial

Considerar a janela inicial aceitavel quando houver:

- trilha completa dos requests prioritários;
- ausencia de falha recorrente de governança;
- continuidade estável de memória entre requests relacionados;
- artefatos textuais utilizaveis;
- nenhuma necessidade de rollback por falha estrutural.

---

## 6. Próximo passo após o piloto

Depois da coleta inicial:

1. consolidar o relatório operacional;
2. comparar o baseline atual com a futura POC de `LangGraph`;
3. decidir se a POC segue para absorção parcial real no núcleo do pos-`v1`.
