# Constituição de Engenharia

Esta política define o padrão mínimo de engenharia do JARVIS.

Ela existe para proteger quatro coisas:

- robustez;
- segurança;
- reversibilidade;
- coerência arquitetural.

Ela não deve virar burocracia. O uso correto desta política é como
conjunto de guardrails práticos para acelerar mudanças seguras, não para
travar a implementação.

## 1. Princípios base

### 1.1 Núcleo soberano

- identidade, governança, memória canônica e síntese final não podem ser
  terceirizadas para frameworks externos;
- absorções tecnológicas devem ser traduzidas para os contratos do JARVIS;
- nenhuma dependência nova pode assumir o papel de cérebro real do sistema.

### 1.2 Segurança por padrão

- preferir `fail-safe defaults`;
- aplicar privilégio mínimo;
- manter escrita sensível mediada pelo núcleo;
- exigir auditabilidade nas capabilities novas.

### 1.3 Reversibilidade

- toda capability nova deve ser removível ou desativável sem reescrever o
  sistema inteiro;
- promoções de runtime precisam ter rollback claro;
- experimentos externos ficam em sandbox até promoção formal.

### 1.4 Contratos e observabilidade

- contratos compartilhados, registries e eventos são parte da arquitetura;
- mudanças em contratos exigem compatibilidade explícita, ou migração clara;
- eventos críticos não são só debug; eles são evidência operacional.

## 2. Regras de implementação

Toda mudança relevante deve, no mínimo:

- ter justificativa arquitetural clara;
- respeitar os registries soberanos ativos;
- incluir testes proporcionais ao risco;
- manter documentação viva sincronizada quando mudar o estado real do projeto;
- passar pelo gate automatizado adequado;
- preservar governança, memória canônica e fronteiras do núcleo.

Mudanças que exigem justificativa mais forte:

- nova superfície de interface;
- novo registry;
- novo contrato compartilhado;
- novo tipo de memória;
- novo especialista promovido;
- nova dependência central;
- absorção de tecnologia externa fora de sandbox.

## 3. Proporcionalidade

Estas regras devem ser aplicadas com proporcionalidade.

Isso significa:

- não exigir ritual pesado para uma mudança pequena e localizada;
- não usar documentação como substituto de implementação;
- não tratar o gate como religião;
- subir o rigor quando o risco sobe.

Pergunta prática:

- esta exigência reduz risco real ou só aumenta atrito?

Se só aumentar atrito, a política precisa ser simplificada.

## 4. Definition of Done

Uma mudança deve ser tratada como pronta quando, em proporção ao seu risco:

- o contrato relevante está claro;
- a implementação está integrada ao runtime correto;
- há teste unitário ou de integração cobrindo o caso;
- há observabilidade suficiente para auditar o comportamento;
- a documentação viva foi sincronizada quando necessário;
- o gate correspondente passou.

Para promoções de capability, o padrão sobe:

- contrato
- teste
- observabilidade
- documentação
- rollback claro
- aderência aos registries soberanos

## 5. Política para absorção tecnológica

Nenhuma tecnologia externa entra por hype.

Toda absorção deve responder:

- qual lacuna real do JARVIS isso resolve;
- qual camada do sistema isso melhora;
- se isso complementa ou ameaça a soberania do núcleo;
- como isso será testado em sandbox;
- como isso será revertido se falhar.

Classificações válidas:

- `rejeitar`
- `usar como referência`
- `absorver depois`
- `promover como complemento`

## 6. Política do agente implementador

Qualquer agente que implemente mudanças neste repositório deve:

- preferir mudanças pequenas, reversíveis e auditáveis quando isso for
  suficiente para resolver o problema real;
- evitar refactors amplos sem necessidade clara;
- não promover capability sem teste, observabilidade e documentação;
- não deixar `HANDOFF.md` e documentos operacionais críticos em drift quando a
  mudança alterar o estado real do projeto;
- não bypassar governança, memória canônica ou síntese soberana;
- tratar encoding, lint, contratos e testes como parte da mudança, não como
  detalhe posterior.

O agente não deve:

- promover tecnologia externa direto ao núcleo;
- abrir nova superfície grande sem decisão explícita;
- reescrever contratos compartilhados por conveniência local;
- introduzir complexidade sem ganho material verificável.

## 7. Gate oficial do repositório

O gate mínimo local é:

```powershell
python tools/engineering_gate.py --mode standard
```

O gate de liberação local é:

```powershell
python tools/engineering_gate.py --mode release
```

Quando houver backend controlado disponível:

```powershell
python tools/engineering_gate.py --mode release --include-controlled
```

O gate é filtro mínimo. Ele não substitui julgamento técnico.

## 8. Revisão da política

Esta política deve permanecer curta, prática e revisável.

Ela deve ser simplificada quando:

- começar a gerar mais atrito do que redução de risco;
- deixar o time ou o agente conservador demais;
- virar documentação decorativa sem efeito real no runtime.

## 9. Política de linguagem

- a linguagem do sistema deve seguir a função da camada, não preferência local;
- contratos técnicos, nomes de campos, eventos, status, payloads, enums e identificadores novos de runtime devem convergir para inglês;
- documentação, visão de produto, labels visíveis e texto humano podem permanecer em português;
- ontologias canônicas derivadas diretamente do Documento-Mestre podem continuar em português enquanto forem tratadas como camada semântica, não como novo padrão para interfaces técnicas;
- ids legados em português não devem ser expandidos sem necessidade; novas interfaces estáveis devem preferir inglês.
