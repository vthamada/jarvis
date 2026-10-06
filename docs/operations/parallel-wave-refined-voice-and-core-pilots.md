# Referencias vocais refinadas e pilotos de composicao Core

Rodada 2026-10-03. Desenvolvimento isolado autorizado pelo operador, sem
promocao de capability, autenticacao, OAuth, deploy, commit/push ou retomada
Docker/Linux. Porta humana8765 e bancos de producao nao foram utilizados.

## Voz

`apps/jarvis_voice_lab/reference_selection.py` sugere recortes proximos da
referencia C preferida pelo operador. Energia em blocos20ms permite procurar
bordas relativamente quietas, mas nao identifica fala, musica, locutor, palavras
completas ou qualidade. Cada sugestao continua exigindo revisao humana. Original
somente leitura; extracao exata gera novo WAV privado fora de Git/OneDrive.

Whisper Small e Turbo processam cada janela exata, offline e sequencialmente
com TTS nesta RTX3050/4GiB. Downloader Turbo usa pesos publicos pinned
`openai/whisper-large-v3-turbo@41f01f3fe87f28c78e2fbf8b568835947dd65ed9`, com
hashes verificados. Nenhum audio foi enviado. Discordancia textual entre modelos
e diagnostico; concordancia tambem nao comprova transcricao correta. ICL continua
`qwen_icl_draft`, review_required=True, sem confirmacao inventada.

Modelo Qwen Base0.6B, mesma frase de qualificacao/seed42 da comparacao anterior;
nao mudou simultaneamente para modelo1.7B. Baixa energia nao prova que o corte
esta semanticamente completo. SDKs/pesos em .research ignorado; referencias,
amostras e manifest com rascunhos em TEMP. Entrega explicita pode copiar artefatos
para Codex visualizations, com hash conferido. Nao ha playback automatico.

Quatro inferencias reais Qwen CUDA concluiram, mono PCM16/24kHz. Original
498.25s manteve SHA256 `ae8a1a7f3da99650a3e94f20726c71698bd892270aefa6bb540a63fc8c753aab`.
Small/Turbo discordaram nas tres janelas. Transcricoes continuam rascunhos;
nenhuma escuta/identidade/qualidade foi atestada pelo agente. C2 x-vector-only
usa a mesma referencia/frase/seed, mas nao transcricao, como controle separado.

| Ensaio | Recorte original | Duracao gerada | SHA256 amostra |
| --- | --- | --- | --- |
| C1 Qwen ICL draft | 364.34–374.94s | 8.7200416667s | fd07e7a46e7db349da425d36040758e653d5369dedf85c76e817df147d5906da |
| C2 Qwen ICL draft | 367.34–377.70s | 9.68s | c6e21528683a306f65c5c5b733b7ea92d800bf28e67c0f1851e44d4ef466cdda |
| C3 Qwen ICL draft | 361.60–371.72s | 10.00s | 4cfd5393ad5cc91309d942615a0f349b08d55b3a0bf6e0c44d07470b8e01e209 |
| C2 x-vector-only controle | mesmo C2 | 10.40s | 5f8e497e217bfa96ed02cf1ef8a880ab80bd4e6f023a7205a559c0067978df5a |

Referencias e samples de entrega tiveram hashes comparados a origem/resultado;
manifest privado conserva recortes/rascunhos. C3 foi extraido com duracao por
frames10.12s; marcas nao sao alinhamento fonetico. Nenhuma qualidade aprovada.

## Memoria entre sessoes

`python -m apps.jarvis_console.memory_recall_pilot --authorized` executa corpus
publico fixo em Core real/SQLite temporario. Quatro turnos,115 eventos e finais
conferidos com turnos canonicos. Sessao B do mesmo sujeito observa2 interacoes
anteriores; sujeito distinto observa0/ref propria. Bindings confiaveis locais
nao sao autenticacao ou endpoint multiusuario. Seletores/ref drift e adulteracao
de final sao recusados; politica canonica de retrieval nao foi substituida.

Limite observado: assist_only retorna defer_for_validation, contexto seeded,
nenhum candidato semantico. Persistencia/tracking demonstrados; continuidade
semantica util NAO demonstrada. Nao aumentar autonomia so para fabricar sucesso.
Detalhes: `apps/jarvis_console/MEMORY_RECALL_PILOT.md`.

## Tarefa duravel ligada ao Core

`python -m apps.jarvis_console.job_pilot --authorized` aceita por stdin somente
selecao de caso publico fixo (ou caso default), nao texto/executor arbitrario.
Task `core:assist_only`, input SHA256 e actor/session exatos, max_attempts=1.
Preflight e finish validam versao/fencing/lease/deadline. Cancelamento e pausa
revogam resultado; restart nao reexecuta Core. Worker fixture recusa task Core.

Governanca adiada vira needs_decision, nao sucesso. Job ledger e memoria
canonica sao transacoes distintas: falha/pausa/cancelamento depois de persistir
Core NAO desfazem o turno. Sem promessa exactly-once, scheduler, replay automatico
ou despacho externo. Detalhes: `services/job-service/README.md`.
Execucao fisica final:30 eventos Core, registro canonico conferido, ledger
needs_decision e reopen needs_decision sem execucao adicional.

## Observacao MCP composta com Core

`python -m apps.jarvis_console.mcp_pilot --authorized` chama subprocess stdio
readonly fixture proprio e relata metadados enumerados no Core real temporario.
Bruto externo fica fora de prompt/memoria; readiness exige igualdade exata ao
texto conhecido, output hostil vira unrecognized_untrusted_text. Descriptor
readOnlyHint e binding nao concedem autoridade. Prazo/cancelamento recusam
entrada Core; apos handle_input sincrono comecar, nao ha interrupcao atomica.

Execucao real normal/injection:3 eventos MCP,29 Core, final canonico1086 chars,
governanca defer_for_validation. completed significa relatorio composto, NAO
permitir task/grant. Timeout real recusou sem Core. Chamada MCP fixa antecede
Core: NAO e despacho MCP governado/promovido. Sem contas/servidores pessoais.
Detalhes: `apps/jarvis_mcp/CORE_PILOT.md`.

## Rollback e proximos recortes

Validacao focada conjunta:345 Python passed/1 skip de symlink Windows e42 JS
passed. Testes incluem slice e fluxo ponta a ponta real dos tres pilotos;
modelos nao entram no gate offline e nao houve teste de qualidade por escuta.
Gate standard global Windows passou apos estabilizacao dos workers. Encoding,
guardrails documentais, Ruff e pytest globais concluiram. Nenhum gate release,
skip ou piloto isolado comprova hardware/Linux, autenticacao ou utilidade aberta.

Rollback: nao invocar pilotos; nao alteraram registry ou baseline de capability.
MB218 in_progress/MB219 blocked continuam; Windows validado nao comprova Linux.
Proximos resultados de produto: revisar referencia/transcricao pela escuta;
conversa/inferencia real subordinada ao Core; recall semantico util sem bypass;
chamada MCP autorizada pelo Core antes de coletar, nao depois. Esses resultados
nao foram fechados pelos pilotos desta rodada.
