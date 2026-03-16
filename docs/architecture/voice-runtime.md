# Voice Runtime

## 1. Objetivo

Este documento aprofunda a camada de voz do JARVIS em nivel arquitetural especializado, sem substituir o Documento-Mestre.

Ele deriva principalmente do capitulo `253. Especificacao detalhada da camada de voz e interacao em tempo real`.

---

## 2. Papel arquitetural

A camada de voz deve funcionar como fronteira stateful entre:

- interface;
- sessao realtime;
- nucleo central;
- observabilidade.

Ela nao deve se tornar um segundo nucleo do sistema.

---

## 3. Componentes centrais

- gateway de voz
- gerenciador de sessao realtime
- detector de turno e interrupcao
- orquestrador de resposta falada
- adaptador de voz do modelo
- integrador de tools em voz
- observador de qualidade de voz

---

## 4. Regra principal

A voz e expressao da identidade do sistema. Portanto:

- tom, postura e clareza devem ser consistentes;
- a camada de voz nao pode fragmentar a identidade;
- latencia e barge-in devem ser tratados como requisitos centrais.

---

## 5. Estado atual

Esta camada faz sentido como prioridade de arquitetura, mas nao como dependencia para iniciar a base do repositorio.
