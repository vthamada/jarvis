# Runner empírico isolado — WP-EVOLUTION-01

Executa baseline e candidate por ports síncronos injetados, sem rede, SDK,
credenciais, banco ou alteração do Core. O avaliador possui corpus imutável
`exact-output-v1`, digest SHA-256 e scorer exato independente do candidate.
Dois casos são repetidos (2–10 vezes); dois casos distintos são holdout, executados
uma vez por braço. O holdout é separado, **não secreto**: este corpus pequeno e
transparente testa o pipeline e obediência a contratos, não inteligência geral.

```python
from evolution.empirical_runner import Arm, EmpiricalRunner, EvaluationResponse

class CorePort:
    def evaluate(self, request):
        # A composição externa invoca o Core soberano real com request.prompt,
        # identidade isolada, governança, memória temporária e síntese final.
        final_text = invoke_isolated_core(request)
        return EvaluationResponse.from_request(request, final_text)

report = EmpiricalRunner(
    baseline=Arm("baseline", "revision-1", "core_local", CorePort()),
    candidate=Arm("candidate", "revision-2", "core_local", CorePort()),
).run(run_id="evaluation-001")
metrics = report.export_metrics()  # uso/exportação explícita; nenhum arquivo é escrito
```

Ports recebem bindings de request/run/arm/revision/case/split/repeat, versão/digest
do corpus e digest do input. Não recebem a resposta esperada nem fornecem scorer.
Respostas precisam devolver todos os bindings exatos, status completed e texto
válido até 2.000 caracteres. A ordem dos braços alterna entre repetições. Erro,
resposta incompleta/adulterada, cancelamento ou prazo excedido não geram comparação
válida; métricas parciais não têm pass rate. Eventos de evidência são referências
determinísticas com hashes e latência, sem prompts, respostas ou exceções brutas.
IDs são labels técnicos escolhidos pelo operador: não coloque conteúdo sensível
neles. Não há armazenamento nem aprendizagem persistente.

Modos são declarados pela composição confiável: `fixture`, `core_local`,
`model_real`. Binding não autentica o port nem prova uso de um modelo; declarar
`model_real` num double não o transforma em evidência real. Qualquer execução
fixture termina `demonstration_only`; demais execuções terminam
`measurement_only_no_promotion`. Modos diferentes tornam a comparação inconclusiva.
**Nenhum score demonstra melhoria real do JARVIS, porcentagem de conclusão ou
autoriza promoção automática.** Evidência de execução/modelo, revisão humana,
amostragem representativa e gates continuam responsabilidade da composição.

Prazo/cancelamento são cooperativos, verificados antes e depois de cada chamada.
Um port bloqueado não é interrompido pelo runner. Os refs/hashs permitem vínculo,
não integridade contra um port hostil capaz de falsificar uma resposta bem formada.
Corpora/revisões não são alteráveis por configuração; evoluções exigem nova versão
e revisão do avaliador independente. Este módulo não entra no caminho do runtime
normal e pode ser removido sem migração.

Teste local/ponta a ponta dos ports, score e export:

```powershell
.venv/Scripts/python.exe -m pytest evolution/empirical_runner/tests
```

Os testes usam doubles efetivamente executados. Prova Core real deve ser composta
em runtime temporário pelo coordenador, sem substituir governança ou síntese final.
