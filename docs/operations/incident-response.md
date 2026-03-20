# Incident Response

## 1. Objetivo

Este documento define a resposta operacional mínima a incidentes do JARVIS no contexto de `v1` e de produção controlada.

Ele deriva principalmente de:

- `documento_mestre_jarvis.md`, capítulo `347. Estratégia de incidentes, contingência e recuperação operacional`
- `docs/operations/v1-operational-baseline.md`

Seu papel é transformar a política arquitetural de contenção em um guia operacional direto.

---

## 2. Princípio geral

Todo incidente deve ser tratado com prioridade para:

- contenção do impacto;
- preservação de evidência;
- restauração de baseline estável;
- registro claro para análise posterior.

---

## 3. Tipos mínimos de incidente

O `v1` deve reconhecer pelo menos:

- falha de núcleo central;
- falha de memória;
- falha de governança;
- falha de adaptador ou ferramenta;
- falha de observabilidade;
- falha de voz ou realtime, quando aplicável;
- regressão após mudança recente.

---

## 4. Classes mínimas de severidade

- `S1` — baixa severidade
- `S2` — severidade moderada
- `S3` — alta severidade
- `S4` — severidade crítica

Leitura prática:

- `S1`: degradação localizada, sem risco estrutural imediato;
- `S2`: impacto relevante, mas contido;
- `S3`: comprometimento sério de fluxo central ou governança;
- `S4`: risco estrutural, perda grave de controle ou necessidade de interrupção imediata.

---

## 5. Resposta mínima por severidade

### 5.1 S1

- registrar ocorrência;
- monitorar repetição;
- avaliar correção em próximo ciclo de mudança.

### 5.2 S2

- conter fluxo afetado;
- registrar evidência;
- avaliar rollback local;
- abrir ação corretiva.

### 5.3 S3

- suspender fluxo ou adaptador afetado;
- reduzir autonomia se aplicável;
- acionar revisão imediata;
- decidir por rollback parcial ou total do componente afetado.

### 5.4 S4

- interromper operação afetada imediatamente;
- restaurar baseline seguro;
- suspender promoções recentes;
- operar em modo restrito até revalidação.

---

## 6. Contenção mínima

Toda resposta a incidente deve considerar uma ou mais destas ações:

- bloquear fluxo atual;
- reduzir autonomia;
- desabilitar adaptador;
- pausar feature recente;
- reverter mudança recente;
- isolar área sob suspeita.

---

## 7. Recuperação operacional

A recuperação deve buscar:

- restaurar comportamento estável;
- revalidar o fluxo afetado;
- confirmar que a contenção foi suficiente;
- registrar impacto em memória, governança e operação.

---

## 8. Registro mínimo do incidente

Registrar ao menos:

- data e hora;
- componente ou fluxo afetado;
- severidade;
- sintoma observado;
- impacto;
- contenção aplicada;
- rollback executado ou não;
- próxima ação recomendada.

---

## 9. Postmortem

Todo incidente relevante deve gerar:

- causa provável;
- impacto real;
- evidência técnica disponível;
- ação corretiva;
- ação preventiva;
- decisão sobre teste, monitoramento ou política.

---

## 10. Relação com outros documentos

Usar em conjunto com:

- `docs/operations/v1-operational-baseline.md`
- `docs/operations/release-and-change-management.md`
- `HANDOFF.md`
- `CHANGELOG.md`

O Documento-Mestre continua sendo a referência normativa.

