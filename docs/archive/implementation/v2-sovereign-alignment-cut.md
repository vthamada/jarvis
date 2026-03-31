# V2 Sovereign Alignment Cut

## 1. Objetivo do corte atual

Este documento define o corte ativo do `v2` depois do encerramento formal do
`v2-alignment-cycle`.

Foco único:

- alinhar `domínios`, `memórias` e `mentes` ao Documento-Mestre com gramática canônica única;
- consolidar especialistas guiados por domínio sem perder soberania do núcleo;
- transformar aderência por eixo em gate contínuo de engenharia.

Fontes de direção:

- `HANDOFF.md`
- `docs/archive/implementation/v2-cycle-closure.md`
- `docs/archive/implementation/v2-alignment-cycle.md`
- `docs/documentation/matriz-de-aderencia-mestre.md`
- `documento_mestre_jarvis.md`

Status desta versão do corte:

- Sprint 1 concluída: sincronização documental e documento vivo soberano;
- Sprint 2 concluída: soberania completa do registry de domínios no runtime;
- Sprint 3 concluída: consumo canônico de memória por classe;
- Sprint 4 concluída: convergência de mentes com domínios canônicos;
- Sprint 5 concluída: especialistas guiados acima do shadow;
- Sprint 6 concluída: gates por eixo e fechamento formal do corte.

Leitura operacional correta neste momento:

- este documento permanece como a referência executiva do corte que acabou de ser concluído;
- o fechamento formal regenerável do corte passa a estar em `docs/archive/implementation/v2-sovereign-alignment-cut-closure.md`;
- o próximo recorte do `v2` deve partir deste baseline, e não reabrir as sprints já concluídas aqui.

---

## 2. Regra de leitura

Este documento é a fonte oficial do que entra em execução agora para o próximo
corte implementável do `v2`.

Ele deve ser lido junto da matriz de aderência para responder:

- qual eixo do mestre a sprint move;
- qual lacuna dominante ela fecha;
- o que continua conscientemente fora de cobertura;
- qual evidência mínima precisa existir antes de promoção.

Ordem obrigatória de execução:

1. docs vivos
2. domínios
3. memórias
4. mentes
5. especialistas
6. gates e fechamento

---

## 3. Frentes oficiais

### 3.1 Sprint 1

- eixo principal: `implementação, operação, release e incidentes`
- objetivo: sincronizar `HANDOFF.md`, `README.md`, `master-summary.md` e abrir o documento vivo do corte
- pronto quando:
  - o ciclo ativo for único em todos os docs vivos;
  - `v2-alignment-cycle` e `v2-cycle-closure` ficarem explicitamente históricos;
  - o commit de referência e os próximos passos não carregarem drift.

### 3.2 Sprint 2

- eixo principal: `domínios`
- objetivo: fazer `shared/domain_registry.py` e `knowledge/curated/domain_registry.json` governarem todo o roteamento runtime
- pronto quando:
  - `knowledge-service`, `cognitive-engine`, `specialist-engine` e `orchestrator-service` derivarem do registry;
  - labels legados ficarem só no adaptador curto de compatibilidade;
  - eventos publicarem rota resolvida, refs canônicas e origem do roteamento.

### 3.3 Sprint 3

- eixo principal: `memórias`
- objetivo: sair do shared packet opaco e expor consumo canônico por classe
- pronto quando:
  - cada convocação de especialista carregar classes consumidas, política por classe e write policy;
  - `DOMAIN`, `RELATIONAL`, `MISSION`, `EPISODIC` e `CONTEXTUAL` forem consumo explícito do fluxo guiado;
  - `memory_alignment_status` auditar coerência entre política e contexto anexado.

### 3.4 Sprint 4

- eixo principal: `mentes`
- objetivo: convergir arbitragem cognitiva com a taxonomia canônica de domínios
- pronto quando:
  - `shared/mind_registry.py` usar apenas refs canônicas em `domain_affinities`;
  - a arbitragem usar intenção, domínios canônicos, risco e continuidade;
  - o fluxo observável publicar mente primária, apoios, suprimidas, tensão dominante e domínio que puxou a arbitragem.

### 3.5 Sprint 5

- eixo principal: `especialistas subordinados`
- objetivo: consolidar `guided` como caminho principal das rotas já abertas
- pronto quando:
  - a coerência `rota -> domínio -> especialista -> memória` for validada antes da convocação;
  - `domain_specialist_completed` for o evento principal das rotas promovidas;
  - `shadow mode` existir só como trilha comparativa legada.

### 3.6 Sprint 6

- eixo principal: `observabilidade, validação e evals`
- objetivo: promover os sinais por eixo a critério contínuo de engenharia e fechar o corte
- pronto quando:
  - `domain_alignment_status`, `memory_alignment_status`, `mind_alignment_status`, `identity_alignment_status` e `axis_gate_status` forem gates permanentes;
  - `engineering_gate.py --mode release` falhar sem artefatos mínimos de aderência;
  - o fechamento classificar backlog entre `corrigir agora`, `manter deferido` e `preservar como visão`.

---

## 4. Fora de escopo deste corte

Não entram neste corte:

- voz oficial;
- `computer use` amplo;
- `pgvector` como fundação obrigatória;
- promoção agressiva do `evolution-lab`;
- novos especialistas além das rotas já promovidas, salvo se necessários para fechar coerência do registry.

---

## 5. Regra tecnológica

Tecnologia externa só entra neste corte quando reduzir lacuna explícita em um dos
eixos soberanos.

Leitura correta:

- `domínios`, `mentes` e `memórias` definem a ontologia do sistema;
- tecnologia entra como mecanismo, complemento ou laboratório;
- nenhuma tecnologia externa assume identidade, governança, memória canônica ou síntese final do JARVIS.

---

## 6. Decisões delegadas ao Codex

Para este corte, o agente implementador pode agir sem intervenção do operador
quando a mudança permanecer dentro da direção já fechada pelo Documento-Mestre,
pela matriz de aderência e por este documento.

O Codex pode, sem pedir autorização adicional:

- sincronizar `HANDOFF.md`, `README.md`, `master-summary.md`, `CHANGELOG.md` e docs vivos quando a mudança só refletir o estado real do projeto;
- abrir, fechar e detalhar sprints dentro deste corte, desde que a ordem oficial de execução continue preservada;
- refatorar nomes técnicos para formas mais profissionais, limpas, robustas e duráveis;
- remover labels legados, heurísticas residuais e drift semântico quando já houver registry soberano equivalente;
- fortalecer contratos compartilhados, eventos observáveis, testes, verificações e gates;
- promover coerência entre `domain_registry`, `mind_registry`, `memory_registry` e runtime;
- endurecer validações de especialistas subordinados, desde que continuem `through_core_only` e `advisory_only`;
- criar ferramentas de verificação, fechamento de ciclo e auditoria quando elas apenas operacionalizarem regras já definidas;
- consolidar o estado vivo do corte atual sem abrir superfície nova de produto.

Regra de execução:

- assumir autonomia padrão para mudanças pequenas, reversíveis e auditáveis;
- escalar ao operador apenas quando a mudança atravessar fronteira ontológica, tecnológica ou estratégica;
- preferir implementação direta com evidência e gate, em vez de pedir confirmação para ajustes já cobertos pela direção ativa.

---

## 7. Decisões reservadas ao operador

Algumas decisões continuam fora da autonomia normal do agente implementador e
exigem validação explícita do operador.

O Codex não pode decidir sozinho:

- alterar a ontologia principal de `domínios`, `mentes` ou `memórias` definida no Documento-Mestre;
- promover tecnologia externa a dependência central, baseline oficial ou cérebro funcional do sistema;
- abrir nova superfície principal de produto, como voz oficial, `computer use` amplo ou nova interface soberana;
- mudar a prioridade macro do programa, reordenar ciclos ou redefinir o foco dominante do corte;
- promover especialista subordinado para autonomia acima das restrições `through_core_only` e `advisory_only`;
- afrouxar governança, memória canônica, síntese final ou critérios de gate para acelerar entrega;
- substituir artefatos canônicos do sistema por equivalentes externos;
- reabrir o baseline do `v1` ou desfazer decisões já marcadas como fechadas sem evidência forte.

Situações que devem ser escaladas:

- quando houver mais de uma opção arquitetural forte com trade-off relevante;
- quando uma absorção tecnológica puder alterar a soberania do núcleo;
- quando o corte atual deixar de ser o melhor lugar para atacar a lacuna principal;
- quando uma mudança de produto, identidade ou posicionamento do JARVIS entrar em jogo.

---

## 8. Critério prático de intervenção humana

O operador deve intervir apenas quando a decisão deixar de ser de implementação
e passar a ser de direção.

Heurística operacional:

- se o problema for `como implementar com a direção já fechada`, o Codex executa;
- se o problema for `qual direção seguir entre alternativas legítimas`, o operador decide;
- se a dúvida for `se isso muda a identidade do sistema`, a decisão é do operador;
- se a dúvida for `se isso melhora consistência, rigor ou aderência sem mudar a direção`, o Codex segue.

