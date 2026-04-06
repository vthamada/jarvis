# Protective Intelligence Architecture for JARVIS

## 1. Objetivo

Este documento formaliza uma arquitetura defensiva e investigativa para o
ecossistema do JARVIS.

O objetivo e permitir que o sistema ajude em:

- inteligencia protetiva;
- triagem e investigacao;
- analise forense;
- antecipacao de risco;
- continuidade e resposta a incidentes;
- preservacao de evidencia e rastreabilidade.

Este documento **nao** altera a ontologia soberana do JARVIS. Ele existe como
desdobramento arquitetural subordinado ao:

- `documento_mestre_jarvis.md`;
- `docs/documentation/matriz-de-aderencia-mestre.md`;
- `docs/implementation/v2-adherence-snapshot.md`.

---

## 2. Tese arquitetural

O JARVIS pode incorporar um stack de `protective intelligence` sem deixar de
ser um sistema unificado.

A regra central e:

- o nucleo continua soberano;
- seguranca e governanca continuam constitutivas do nucleo;
- OSINT, forense, threat intelligence e incident response entram como
  capacidades subordinadas;
- nenhuma capability defensiva vira identidade paralela do sistema.

Em termos simples:

- isso **nao** e um "segundo cerebro de seguranca";
- isso e uma camada especializada de inteligencia protetiva governada.

---

## 3. Encaixe canonico no JARVIS

### 3.1 Dominio canonicamente adequado

O encaixe principal deve acontecer dentro do dominio:

- `defense_security_crisis_management`

Esse dominio deve absorver subdominios e capacidades como:

- `osint_public_intelligence`
- `digital_forensics`
- `threat_intelligence`
- `incident_response`
- `protective_operations`
- `continuity_and_crisis_management`

### 3.2 Relacao com governanca nuclear

Seguranca e governanca nao saem do nucleo.

Logo:

- politicas de risco continuam no `governance-service`;
- memoria critica continua protegida pelo `memory-service` e pelo
  `memory_registry`;
- especialistas dessa area continuam `through_core_only`;
- a sintese final continua sendo do JARVIS.

### 3.3 Relacao com a discussao de `SecurityOS`

Termos como `SecurityOS` ou `IntelOS` podem ser uteis como agrupamento de
produto, operacao ou roadmap.

Eles **nao** devem substituir:

- a taxonomia canonica de dominios;
- o papel do `domain_registry`;
- a hierarquia `core -> domains -> minds -> specialists -> tool layer`.

### 3.4 Papel como vertical derivada

Se esse eixo vier a ser empacotado como vertical do ecossistema, o papel
correto sera o de uma vertical derivada, por exemplo:

- `ProtectiveIntelligenceOS`
- `SecurityOS`
- `IntelOS`

Esses nomes devem ser entendidos como:

- visao de produto;
- agrupamento operacional;
- pacote de capacidades coordenadas.

Eles nao devem ser tratados como:

- nova ontologia soberana;
- nova taxonomia de dominios;
- substitutos do dominio canonico de seguranca;
- identidade paralela ao JARVIS.

---

## 4. Camadas do modulo integrado

### 4.1 Core orchestration

Camada soberana que decide:

- se o caso pertence ao eixo de seguranca e crise;
- quais mentes devem arbitrar o caso;
- quais memorias devem ser recuperadas;
- quais especialistas podem ser convocados;
- qual acao deve ser bloqueada, permitida ou condicionada.

Componentes atuais mais proximos:

- `orchestrator-service`
- `cognitive-engine`
- `governance-service`
- `observability-service`

### 4.2 Protective intelligence domain layer

Camada logica que organiza os casos e capacidades desse eixo.

Responsabilidades:

- classificar o dominio canonico do incidente;
- separar caso investigativo, risco operacional e evento de crise;
- vincular o caso a entidades, artefatos, memoria e missao;
- fornecer contrato estavel para especialistas e tools.

### 4.3 Protective services

Servicos novos sugeridos:

- `case-service`
- `evidence-ledger-service`
- `risk-signal-service`
- `intelligence-service` opcional em fase posterior

#### `case-service`

Responsavel por:

- abrir casos;
- registrar incidentes;
- manter timeline;
- vincular entidades, eventos e tarefas;
- organizar hipoteses e achados.

#### `evidence-ledger-service`

Responsavel por:

- registrar artefatos com hash e proveniencia;
- manter cadeia de custodia;
- armazenar metadados de coleta;
- impedir mutacao silenciosa de evidencia.

#### `risk-signal-service`

Responsavel por:

- consolidar sinais de risco;
- manter score e prioridade;
- sugerir alertas;
- acompanhar janelas de risco e proximos passos.

#### `intelligence-service` opcional

Responsavel por:

- correlacao entre entidades;
- enriquecimento de sinais;
- consolidacao de findings recorrentes;
- apoio a inferencia controlada de ameacas.

---

## 5. Especialistas subordinados

Especialistas sugeridos para o eixo:

- `osint_research_specialist`
- `forensic_analysis_specialist`
- `threat_intelligence_specialist`
- `incident_response_specialist`

Especialistas opcionais de fase posterior:

- `detection_correlation_specialist`
- `hunt_coordination_specialist`
- `case_intelligence_specialist`

Regras obrigatorias:

- todos permanecem subordinados ao nucleo;
- todos operam por `through_core_only`;
- todos sao `advisory_only` por padrao;
- nenhum responde ao usuario como identidade soberana;
- nenhum escreve diretamente em memoria critica ou ledger sem mediacao.

### 5.1 Papel de cada especialista

#### `osint_research_specialist`

- coleta publica;
- cruzamento de fontes abertas;
- timeline publica;
- consolidacao de contexto externo;
- apoio a correlacao de entidades.

#### `forensic_analysis_specialist`

- triagem de artefatos;
- metadados;
- comparacao de arquivos;
- achados tecnicos sobre evidencia;
- suporte a cadeia de custodia.

#### `threat_intelligence_specialist`

- cluster de sinais;
- priorizacao de risco;
- correlacao de TTPs e padroes;
- apoio a avaliacao de ameaca.

#### `incident_response_specialist`

- propostas de contencao;
- checklist de resposta;
- apoio a continuidade;
- recomendacoes de recuperacao e reducao de dano.

### 5.2 Especialistas opcionais de maturacao

Os especialistas abaixo sao uteis, mas devem entrar apenas quando o baseline
do eixo ja tiver:

- caso e ledger estaveis;
- governanca madura;
- observabilidade dedicada;
- trilha auditavel coerente.

#### `detection_correlation_specialist`

- unifica sinais de multiplas fontes;
- reduz ruido;
- consolida hipoteses de incidente;
- sugere clusters e relacoes entre eventos.

#### `hunt_coordination_specialist`

- organiza hunts orientados por hipotese;
- aciona consultas e verificacoes defensivas no proprio perimetro;
- prioriza sinais a partir de risco e caso;
- devolve achados ao nucleo, sem acao soberana propria.

#### `case_intelligence_specialist`

- consolida narrativa tecnica e executiva do caso;
- relaciona evidencias, achados, hipoteses e sinais de risco;
- preserva legibilidade de dossies e continuidade investigativa;
- ajuda a separar fato, hipotese e inferencia.

---

## 6. Tool layer permitida

O eixo deve usar uma `tool layer` especializada, mas sempre governada.

Exemplos defensivos e aceitaveis:

- hashing e fingerprint de arquivos;
- parsers de logs, metadados e cabecalhos;
- timeline builders;
- conectores de OSINT publico;
- correlacao de IoCs;
- ingestao de documentos, prints e anexos;
- canarios e sensores no proprio ambiente;
- verificadores de integridade e exposicao.

### 6.1 Familias de ferramentas candidatas

As familias abaixo sao candidatas de integracao. Elas devem entrar primeiro
como:

- referencia;
- experimento controlado;
- ou complemento subordinado.

Nenhuma delas deve assumir papel de cerebro do sistema.

#### Endpoint, DFIR e visibilidade de host

Exemplos de categoria:

- `Velociraptor`
- `Wazuh`
- `osquery`
- `Fleet`

Papel esperado:

- coleta remota no proprio ambiente;
- inventario e postura;
- visibilidade de endpoint;
- artefatos e hunts defensivos.

#### Timeline e reconstrucao de eventos

Exemplos de categoria:

- `Plaso`
- `Timesketch`
- `OSDFIR Infrastructure`

Papel esperado:

- super timeline;
- analise temporal;
- reconstrucao de sequencia de eventos;
- apoio a investigacao colaborativa.

#### Rede, NSM e trafego

Exemplos de categoria:

- `Zeek`
- `Suricata`
- `Arkime`

Papel esperado:

- visibilidade de trafego;
- correlacao de sessao;
- triagem defensiva de rede;
- apoio a investigações no proprio perimetro.

#### CTI, IoCs e enriquecimento

Exemplos de categoria:

- `MISP`
- `Cortex`
- `TheHive`

Papel esperado:

- observables e enriquecimento;
- casos e correlacao;
- apoio a threat intelligence e a narrativa de incidente.

#### OSINT publico e attack surface awareness

Exemplos de categoria:

- `Shodan`
- `Maltego`
- `SpiderFoot`
- `theHarvester`

Papel esperado:

- descoberta de ativos publicos;
- correlacao aberta;
- exposicao externa;
- apoio a OSINT dentro de limites publicos e defensivos.

#### Hunting e triagem por padroes

Exemplos de categoria:

- `YARA`
- `YARA-X`
- `Sigma`

Papel esperado:

- matching de arquivos e indicadores;
- regras de deteccao;
- hunting defensivo baseado em padroes;
- enriquecimento tecnico de achados.

#### Orquestracao de resposta

Exemplos de categoria:

- `Shuffle`
- `Cortex Responders`
- integracoes controladas do proprio ambiente

Papel esperado:

- playbooks;
- automacao controlada;
- escalonamento;
- resposta governada.

### 6.2 Regra de integracao das tools

Toda tool desse eixo deve ser tratada como:

- capability subordinada;
- invocada via especialistas ou servicos governados;
- observavel;
- reversivel quando aplicavel;
- e nunca diretamente soberana diante do usuario.

---

## 7. Memoria e evidencia

### 7.1 Regra central

Evidencia nao deve existir apenas como memoria mutavel.

Deve haver separacao entre:

- `memory`: contexto, relacoes, missoes, hipoteses, historico cognitivo;
- `ledger`: artefatos, hashes, origem, cadeia de custodia, integridade.

### 7.2 Classes de memoria mais relevantes

As classes mais uteis para esse eixo tendem a ser:

- `CONTEXTUAL`
- `RELATIONAL`
- `MISSION`
- `EPISODIC`
- `SEMANTIC`
- `PROCEDURAL`

Uso esperado:

- `CONTEXTUAL` para situacao ativa;
- `RELATIONAL` para vinculo entre entidades, casos e achados;
- `MISSION` para objetivo protetivo em curso;
- `EPISODIC` para historico de incidentes;
- `SEMANTIC` para padroes e conhecimento recorrente;
- `PROCEDURAL` para playbooks e resposta guiada.

### 7.3 Regra de escrita

- memoria continua sob politica do `memory_registry`;
- evidencia continua sob politica do `evidence-ledger-service`;
- escrita de especialista continua `through_core_only`.

---

## 8. Contratos principais

Contratos sugeridos:

- `CaseRecord`
- `EvidenceItem`
- `EvidenceChainEntry`
- `Finding`
- `Hypothesis`
- `RiskSignal`
- `ThreatProfile`
- `InvestigationDirective`
- `ProtectiveRecommendation`

### 8.1 `CaseRecord`

Campos minimos:

- `case_id`
- `case_title`
- `case_status`
- `mission_ref`
- `primary_domain`
- `linked_entities`
- `timeline_refs`
- `risk_level`

### 8.2 `EvidenceItem`

Campos minimos:

- `evidence_id`
- `case_id`
- `evidence_type`
- `source_type`
- `source_origin`
- `captured_at`
- `hash_sha256`
- `integrity_status`
- `custody_ref`

### 8.3 `Finding`

Campos minimos:

- `finding_id`
- `case_id`
- `author_type`
- `specialist_type`
- `confidence_level`
- `summary`
- `linked_evidence_refs`
- `linked_risk_signals`

### 8.4 `RiskSignal`

Campos minimos:

- `risk_signal_id`
- `case_id`
- `signal_type`
- `severity`
- `confidence_level`
- `time_sensitivity`
- `recommended_action`

---

## 9. Fluxo soberano do modulo

### 9.1 Fluxo principal

1. Um evento entra no JARVIS:
   - relato do usuario;
   - artefato suspeito;
   - incidente;
   - sinal de risco;
   - evento de continuidade.
2. O `knowledge-service` resolve o dominio canonico.
3. O `governance-service` define o envelope permitido.
4. O `case-service` abre ou atualiza o caso.
5. O `evidence-ledger-service` registra artefatos e integridade.
6. O nucleo convoca especialistas subordinados quando elegiveis.
7. Os especialistas retornam findings e recomendacoes.
8. O `risk-signal-service` recalcula risco e proximos passos.
9. O nucleo sintetiza uma resposta unica e auditavel.

### 9.2 Eventos observaveis sugeridos

- `protective_case_opened`
- `protective_case_updated`
- `evidence_registered`
- `evidence_integrity_verified`
- `protective_specialist_dispatched`
- `protective_specialist_completed`
- `risk_signal_registered`
- `protective_recommendation_issued`
- `protective_action_blocked_by_governance`

---

## 10. Governanca e limites

### 10.1 Limites obrigatorios

- nenhuma acao fora do proprio perimetro sem autorizacao valida;
- nenhuma degradacao de cadeia de custodia;
- nenhuma promocao de especialista sem observabilidade e teste.

### 10.2 Modos padrao

- `through_core_only`
- `advisory_only`
- `reversible_when_applicable`
- `audit_required`

### 10.3 Gate humano

Acoes sensiveis devem exigir gate humano explicito, por exemplo:

- exportacao de dossie consolidado;
- mudanca de classificacao de risco severo;
- acao de contencao com impacto operacional maior;
- compartilhamento externo de evidencias;
- qualquer acao com implicacao juridica direta.

### 10.4 Matriz de governanca por classe de acao

#### Monitorar

Permite por padrao, com observabilidade:

- coletar sinais do proprio ambiente;
- consolidar timeline;
- ler fontes publicas;
- registrar caso e evidencia.

#### Investigar

Permite com guardrails e escopo explicito:

- correlacionar entidades;
- enriquecer indicadores;
- comparar artefatos;
- produzir achados e hipoteses;
- abrir ou atualizar dossie tecnico.

#### Responder

Permite apenas de forma condicionada:

- sugerir contencao;
- preparar playbooks;
- escalonar caso;
- recomendar bloqueios ou isolamento.

Regra:

- resposta automatica so entra com governanca mais rigida, politicas claras e
  trilha auditavel.

#### Executar acao critica

Exige gate humano explicito e envelope de risco apropriado:

- bloquear host ou identidade;
- alterar configuracao sensivel;
- compartilhar evidencia externamente;
- executar resposta de alto impacto operacional;
- produzir efeito irreversivel.

---

## 11. Observabilidade e qualidade

Sinais que esse eixo deve expor:

- `case_integrity_status`
- `evidence_chain_status`
- `protective_governance_status`
- `protective_memory_alignment_status`
- `protective_specialist_alignment_status`
- `risk_signal_coherence_status`

Criticos de qualidade:

- hash e proveniencia de evidencia coerentes;
- findings sempre vinculados a caso e evidencia;
- hipoteses separadas de fatos;
- recomendacoes defensivas auditaveis;

---

## 12. Ordem de implementacao

### Fase 1 - contratos e ledger

- contratos de caso, evidencia, finding e risk signal;
- `evidence-ledger-service`;
- eventos minimos de integridade;
- gate de governanca inicial.

### Fase 2 - casos e timeline

- `case-service`;
- timeline de incidentes;
- entidades e vinculos;
- consolidacao de hipoteses e achados.

### Fase 3 - OSINT publico

- `osint_research_specialist`;
- ingestao de fontes abertas;
- correlacao basica com casos e entidades.

### Fase 4 - forense analitica

- `forensic_analysis_specialist`;
- triagem de artefatos;
- metadados;
- comparacoes controladas.

### Fase 5 - risco e antecipacao

- `risk-signal-service`;
- score e prioridades;
- alertas;
- playbooks defensivos.

### Fase 6 - gates e maturacao

- observabilidade dedicada;
- evals por caso e por workflow;
- gate de release especifico para o eixo;
- criterios de promocao de especialistas e tools.

---

## 13. Veredito

Integrar um modulo desse tipo ao JARVIS e viavel e coerente com a arquitetura
atual, desde que quatro regras sejam preservadas:

1. o nucleo continua soberano;
2. seguranca e governanca continuam constitutivas;
3. OSINT e forense entram como capacidades subordinadas;
4. o stack permanece auditavel e legalmente governado.

Essa e a forma correta de materializar um eixo de inteligencia protetiva dentro
do ecossistema do JARVIS sem fragmentar a identidade do sistema.

Se ele vier a ser tratado como vertical, deve existir apenas como camada
derivada de produto e operacao, nunca como substituto da arquitetura canonica.
