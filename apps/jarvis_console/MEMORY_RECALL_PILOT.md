# Piloto local de recall canônico

`memory_recall_pilot` executa quatro turnos completos no Core atual, com bancos
SQLite reais e descartáveis em TEMP. É opt-in e usa somente um corpus público
fixo: não recebe conteúdo privado, paths de bancos humanos nem credenciais.
Antes de criar o runtime, resolve a base TEMP do host e recusa a raiz do
workspace ou qualquer descendente; a base verificada é passada explicitamente
ao criador do diretório temporário.

```powershell
.venv/Scripts/python.exe -X utf8 -m apps.jarvis_console.memory_recall_pilot --authorized
.venv/Scripts/python.exe -m pytest tests/integration/test_memory_recall_pilot.py -q
```

O fluxo cobre seed, follow-up na mesma sessão, segunda sessão do mesmo sujeito
e contexto de missão explícito, e uma sessão de sujeito distinto sem herança de
missão. Cada entrada percorre governança, memória canônica e síntese final; o
piloto verifica igualdade da síntese com o turno persistido e o evento
`memory_recovered`. Não escreve memória paralela e não cria ranking de recall.

## Resultado físico desta rodada

Com `assist_only`, os quatro turnos recebem `defer_for_validation`, sem dispatch
operacional. A segunda sessão recupera o contador do usuário anterior (2), mas o
contexto fica `seeded`, sem candidatos semânticos de missão. O sujeito distinto
tem contador zero e somente sua própria ref. Isso comprova persistência de
tracking entre sessões e isolamento deste corpus/binding, **não recall útil de
conteúdo ou continuidade aberta**. `continuity_action=continuar` e status genérico
`active` não são tratados como prova de utilidade. O resultado inclui
`persisted_tracking_only` e `useful_continuity_demonstrated=false`.

Essa recusa é mantida: o piloto não eleva autonomia para fabricar sucesso, não
pré-semeia uma missão fictícia como evidência empírica e não troca síntese final.

## Fronteiras e metadados

O port tem composição confiável local e binding explícito de sujeito/sessão/
missão; não autentica ninguém e não é endpoint público. Antes de ler memória,
recusa drift de identidade/ref/escopo e missão existente de outro owner. Refs
de usuário/candidato inesperadas também são recusadas. A API canônica direta
continua recebendo refs confiáveis; este slice não promove segurança multiusuário.

JSON apresenta IDs sintéticos, contadores, decisão, fontes canônicas e, quando
disponíveis, motivo/freshness/ref do candidato existente. Omite prompts, respostas,
briefs, áudio e paths do runtime. Eventos internos do Core podem conter conteúdo,
mas permanecem no runtime temporário, removido ao concluir o contexto Python.
TEMP segue ACL/políticas do host: não é sandbox de SO nem promessa contra sync.

Testes negativos usam doubles somente para adulteração controlada de refs/final;
o caso de fluxo completo e o comando acima usam Core e SQLite reais. Nenhuma
capability, retenção/exclusão, autenticação, recall vetorial ou ganho de inteligência
é promovido. Rollback: deixar de executar o módulo e remover os três arquivos do
slice; o runtime central permanece inalterado.
