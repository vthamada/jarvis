# Programa de Excelencia do JARVIS

## 1. Papel do documento

Este documento existe para registrar o mapa de maturidade de alto nivel do
JARVIS.

Ele nao substitui:

- o [Documento-Mestre](../../documento_mestre_jarvis.md) como fonte canonica de
  visao;
- o [programa-ate-v3.md](programa-ate-v3.md) como programa macro;
- o [HANDOFF.md](../../HANDOFF.md) como retomada tatico-operacional;
- os documentos ativos de corte e os snapshots de aderencia como orientacao de
  execucao imediata.

Leitura correta:

- este arquivo e um radar estrategico de excelencia;
- ele nao e backlog primario;
- ele nao deve reabrir baseline soberano ja fechado;
- ele serve para distinguir maturacao profunda de expansao prematura.

---

## 2. Fontes e enquadramento

Fontes principais desta revisao:

- [documento_mestre_jarvis.md](../../documento_mestre_jarvis.md)
- [auditoria-primaria-documento-mestre.md](../archive/documentation/auditoria-primaria-documento-mestre.md)
- [matriz-de-aderencia-mestre.md](../documentation/matriz-de-aderencia-mestre.md)
- [v2-adherence-snapshot.md](../implementation/v2-adherence-snapshot.md)
- [programa-ate-v3.md](programa-ate-v3.md)
- [technology-study.md](../architecture/technology-study.md)
- estado atual do runtime, dos registries, dos engines e dos gates

Este documento complementa a hierarquia vigente:

1. visao canonica no Documento-Mestre;
2. aderencia formal na matriz;
3. estado vivo do runtime no snapshot e no handoff;
4. macroprograma em `programa-ate-v3.md`;
5. excelencia como horizonte de maturidade neste arquivo.

---

## 3. Estado de partida consolidado

O JARVIS ja saiu da fase em que o principal problema era desvio de direcao. O
baseline atual ja preserva os pilares centrais do sistema.

### 3.1 O que ja esta solido

- arquitetura cognitiva composta, com registry de mentes e arbitragem soberana;
- memoria estratificada com classes formais, politicas declarativas e consumo
  real no runtime;
- dominios canonicos e rotas promoted/guided regidos por registry soberano;
- especialistas subordinados, sempre `through_core_only` e `advisory_only`;
- identidade, governanca e sintese final preservadas no nucleo;
- observabilidade, gates e evidencia local acima de conveniencia de fase;
- disciplina documental e guardrails de engenharia mais maduros do que nas
  fases anteriores.

### 3.2 O que ainda nao esta pleno

O runtime esta coerente com o Documento-Mestre, mas ainda nao opera no nivel de
excelencia mais alto que a propria visao descreve.

O gap atual nao e mais "falta de arquitetura". O gap atual e:

- materializacao profunda;
- influencia causal de memoria e composicao cognitiva;
- rigor operacional mais completo;
- algumas capacidades futuras ainda so mapeadas conceitualmente.

---

## 4. Gaps de materializacao prioritarios

Estes sao os gaps mais fortes do projeto hoje. Eles importam porque ja pertencem
ao coracao da visao do JARVIS e porque aumentam qualidade real do sistema sem
reabrir sua ontologia.

### 4.1 Metacognicao como deliberacao real

O sistema ja arbitra mentes no inicio do fluxo, mas ainda nao revisa a propria
estrategia cognitiva durante a execucao.

O que falta:

- detectar impasse cognitivo durante o fluxo;
- recompor mente primaria e apoios mid-reasoning;
- registrar mudanca de estrategia como evento observavel;
- fazer o resultado parcial do plano influenciar a propria arbitragem.

Sinal de excelencia:

- o sistema muda de estrategia cognitiva com justificativa rastreavel quando a
  tarefa revela natureza diferente da inicialmente percebida.

### 4.2 Memoria como influencia causal no raciocinio

Hoje a memoria ja entra melhor do que antes, mas ainda tende a funcionar mais
como contexto recuperado do que como fator que altera caminho de decisao.

O que falta:

- plano mudar de rota porque uma memoria relevante foi recuperada;
- sintese mudar framing, profundidade ou criterio por memoria relacional,
  procedural ou episodica;
- historico de sucesso/fracasso influenciar arbitragem de mente e especialista;
- memoria semantica enriquecer dominio ativo alem do corpus curado estatico.

Sinal de excelencia:

- evals automatizadas detectarem diferenca estrutural de comportamento com e sem
  memoria relevante, nao apenas diferenca cosmetica de contexto.

### 4.3 Ciclo de vida de memoria como sistema vivo

O projeto ja tem registry e politicas por classe, mas ainda nao opera promocao,
consolidacao e arquivamento como sistema vivo.

O que falta:

- retencao por classe;
- consolidacao de episodios recorrentes;
- promocao governada entre camadas;
- arquivamento com referencia preservada;
- telemetria do corpus de memoria.

Sinal de excelencia:

- o corpus crescer com disciplina, nao por acumulacao ilimitada.

### 4.4 Composicao de mentes com profundidade

A composicao cognitiva atual e util, mas ainda mais declarativa do que
deliberativa.

O que falta:

- tensao dominante afetando plano e sintese;
- discordancia entre mentes gerando restricao, step extra ou criterio de
  validacao;
- historico de composicoes bem-sucedidas por dominio e workflow;
- composicao adaptativa diante da complexidade revelada da tarefa.

Sinal de excelencia:

- a combinacao entre mentes deixar de ser so configuracao observavel e passar a
  ser parte causal do comportamento do runtime.

---

## 5. Lacunas canonicas versus capacidades futuras

O documento original misturava duas coisas diferentes. Aqui elas ficam
separadas.

### 5.1 Lacunas canonicas que merecem cobertura melhor

Estas areas ja deveriam existir com formulacao mais forte nos artefatos
canonicos ou operacionais:

- arquitetura de tool use como camada subordinada ao nucleo;
- gestao da janela de contexto e criterio de compactacao;
- framework formal de evals por eixo e por workflow;
- modelagem explicita do usuario;
- defesa contra adversarial inputs e prompt injection;
- estrategia de deployment, operacao real, release e degradacao.

Leitura correta:

- aqui o problema e cobertura ainda incompleta ou dispersa;
- nao e correto tratar tudo isso como "nao existe em nenhum artefato".

### 5.2 Capacidades futuras que nao devem comandar o backlog imediato

Estas capacidades sao validas como horizonte, mas nao devem empurrar a fase
atual para fora do baseline soberano:

- missoes assincronas e comportamento proativo;
- RAG semantico mais profundo com embeddings;
- streaming e tratamento fino de latencia percebida;
- multimodalidade de entrada;
- resiliencia e modo degradado mais amplo;
- aprendizado por feedback implicito.

Leitura correta:

- isso deve permanecer como programa futuro ou trilha experimental;
- nao deve ser tratado como gap critico do baseline atual sem decisao de fase.

---

## 6. Regras de uso deste documento

Para este arquivo ser util, ele precisa ser usado com disciplina.

### 6.1 O que ele pode fazer

- ajudar a avaliar se o sistema esta ficando mais profundo, nao apenas maior;
- servir como filtro de excelencia para fases futuras;
- mostrar quais gaps sao centrais e quais sao expansao opcional;
- orientar o que deve ser medido antes de abrir novas superficies.

### 6.2 O que ele nao pode fazer

- substituir o ciclo ativo;
- virar backlog primario por conveniencia;
- concorrer com `programa-ate-v3.md`;
- tratar todo horizonte de excelencia como urgencia de implementacao.

---

## 7. Proximos passos que precisam ser implementados no sistema

A ordem abaixo considera o estado vivo do repositorio e o baseline atual do
`v2`.

### 7.1 Primeira frente: endurecer o baseline soberano

1. Fechar o uso de `workflow_profile` como contrato de comportamento, nao apenas
   como metadata de rota.
2. Garantir que `planning`, `synthesis`, `observability` e conclusao de
   especialista leiam o mesmo contrato soberano sem rederivacao local.
3. Tornar a trilha `mente -> dominio -> especialista -> memoria` mais explicita
   nos consumidores restantes.

Resultado esperado:

- o runtime deixa de depender de recomposicao implicita entre camadas.

### 7.2 Segunda frente: maturar memoria sem reabrir arquitetura

1. Aprofundar `semantic` e `procedural` como consumo real por workflow e nao
   apenas como hints enriquecidos.
2. Medir quando memoria altera decisao de plano e sintese.
3. Comecar politica nativa de consolidacao, promocao e envelhecimento sem
   inflar escopo de armazenamento.

Resultado esperado:

- memoria passa a influenciar caminho de decisao, nao apenas contexto anexo.

### 7.3 Terceira frente: aprofundar composicao cognitiva

1. Fazer tensao dominante influenciar criterio de plano ou validacao.
2. Permitir recomposicao cognitiva em casos de impasse observavel.
3. Medir quais composicoes funcionam melhor por dominio e workflow.

Resultado esperado:

- mentes deixam de ser apenas configuracao inicial e passam a operar como
  deliberacao interna real.

### 7.4 Quarta frente: formalizar excelencia como gate

1. Traduzir sinais de excelencia em evals por eixo e por workflow.
2. Separar claramente:
   - `baseline saudavel`
   - `maturacao recomendada`
   - `horizonte futuro`
3. Fazer os gates distinguirem falha estrutural de capacidade ainda deferida.

Resultado esperado:

- o projeto ganha criterio para crescer sem reabrir discussoes ja fechadas.

### 7.5 Quinta frente: so depois abrir superficie nova

Somente apos as frentes anteriores vale reavaliar:

- camada de tool use mais rica;
- assincronia e proatividade;
- resiliencia ampliada;
- multimodalidade;
- RAG semantico profundo;
- outras absocoes externas.

Resultado esperado:

- expansao entra por evidencia e por maturidade, nao por entusiasmo tecnologico.

---

## 8. Criterios objetivos de excelencia

Este documento so faz sentido se gerar criterio pratico.

### 8.1 Cognicao

- o sistema muda de estrategia quando a tarefa pede;
- essa mudanca e rastreavel;
- tensao entre mentes afeta comportamento final.

### 8.2 Memoria

- memoria relevante altera plano e sintese;
- existe politica por classe;
- o corpus tem ciclo de vida e nao cresce sem controle.

### 8.3 Dominios e especialistas

- o contrato de rota e soberano ponta a ponta;
- especialistas nao reabrem identidade nem governanca;
- dominio ativo, memoria guiada e especialista permanecem coerentes.

### 8.4 Qualidade e evidencia

- gates diferenciam saude estrutural de deferimento legitimo;
- evals capturam ganho real de comportamento;
- o runtime e explicavel por trilha e evento, nao por leitura heroica de codigo.

### 8.5 Operacao

- baseline continua reversivel, auditavel e disciplinado;
- crescimento funcional nao degrada a inteligibilidade do sistema.

---

## 9. O que nao fazer

- nao transformar este arquivo em backlog primario da fase;
- nao chamar capacidade futura de gap critico sem decisao de programa;
- nao abrir nova superficie antes de fechar o baseline soberano;
- nao absorver tecnologia externa porque ela parece avancada;
- nao criar um segundo mestre paralelo ao Documento-Mestre.

---

## 10. Conclusao

O JARVIS ja ultrapassou o ponto em que precisava apenas provar direcao. O que o
separa de um sistema realmente excepcional nao e mais a falta de arquitetura
base, mas a profundidade de materializacao dessa arquitetura.

Por isso, este documento deve ser usado como filtro de maturidade:

- o que aqui aparece como central deve aprofundar o nucleo;
- o que aqui aparece como futuro nao deve sequestrar o backlog atual;
- e qualquer expansao deve continuar subordinada ao Documento-Mestre, ao
  programa macro e ao baseline soberano do repositorio.

---

## 11. Referencias

- [documento_mestre_jarvis.md](../../documento_mestre_jarvis.md)
- [auditoria-primaria-documento-mestre.md](../archive/documentation/auditoria-primaria-documento-mestre.md)
- [matriz-de-aderencia-mestre.md](../documentation/matriz-de-aderencia-mestre.md)
- [v2-adherence-snapshot.md](../implementation/v2-adherence-snapshot.md)
- [programa-ate-v3.md](programa-ate-v3.md)
- [technology-study.md](../architecture/technology-study.md)
- [engineering-constitution.md](../documentation/engineering-constitution.md)
- [HANDOFF.md](../../HANDOFF.md)
- [service-breakdown.md](../implementation/service-breakdown.md)
