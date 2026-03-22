# Apps

Esta area concentra interfaces e superficies de produto do JARVIS.

Estado atual:

- `apps/jarvis_console/` implementa o console textual minimo do baseline;
- a interface de console usa diretamente o `orchestrator-service` atual;
- web UI e voice runtime permanecem fora do caminho critico do ciclo atual.

Leitura correta:

- `jarvis-console` faz parte do baseline encerrado do `v1`;
- novas superficies devem seguir o `pos-v1` e nao reabrir o baseline sem necessidade.
