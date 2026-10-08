# MB222: conta local ChatGPT e catalogo SIWC

Atualizacao MB236 2026-10-06: diagnostico host opt-in validado com326 novos,
535 focados e standard global Windows8994 casos/8883 passed/111 skipped/
zero falhas. Sessao escolhida expirada; um refresh explicito autorizado passou.
Segunda tentativa unica com gpt-6-astra recebeu HTTP200 seguido de
unsupported_response_encoding antes de SSE. Codigo cobre MIME OU
Content-Encoding, nao distinguidos; nao afirmar compressao/resposta concluida.
Final nativa2635 exata ao export/GET/reload, sem reenvio/fallback/tools ou
modelo/qualidade homologados. MB236 blocked; ultimo validado MB235. Proximo
recorte candidato exige DOR/corpus/gate, nova inferencia novo consentimento.
Detalhes em real-oauth-acceptance.md. Notas abaixo sao historicas.

Historico MB236: budget de body2 MiB apenas para status200
GET api.openai.com/v1/models. Todos os demais endpoints/sucessos/erros mantem
256 KiB; JSON/depth/count/deadline/cleanup e cap de exibicao CLI intactos.
114 unitarios/12 E2E novos,540 existentes e gate standard global Windows
aprovados/8668 coletados. Conta real explicitamente escolhida conectada;
uma consulta real CLI retornou5 modelos. Tentativa Web unica com gpt-6-astra
recebeu ALLOW/rejected/inference_failed, final nativa preservada. Sem reenvio/
refresh/fallback pago; causa indeterminada, inferencia/qualidade nao aceitas. Ver
real-oauth-acceptance.md. Evidencia MB222 abaixo e historica.

Data: 2026-10-05. MB222 done no recorte local; gate standard global Windows
passou.613 testes focados passed/6 skips; storage final82 passed/6 skips apos
ultima regressao (contagem separada, sobrepoe o focused). Skips exclusivamente
POSIX ownership/mode e symlinks indisponiveis neste Windows; auditoria final
sem bloqueador. Nao e homologacao de conta/modelo real nem sistema completo.

## Comportamento e contrato

Cliente publico opt-in: state/nonce/PKCE S256 novos, callback IPv4 127.0.0.1
em porta efemera, correlacao/consumo one-shot, dynamic_agent_client -> oaiapp_.
Callback nao concede scope; somente resposta token validada. Destinos HTTPS
fixos para discovery/token/JWKS/catalogo, certificados verificados, sem proxy,
redirects, retries, secret/API key ou fallback pago. Nenhum login automatico.

PyJWT/cryptography verifica assinatura RSA, issuer/audience/subject, nonce,
datas e binding exato da conta no retorno. Slice suporta RS256; outros
algoritmos recusados, nao alegacao de que todo servidor usa apenas RS256.
Extra opcional siwc evita dependencia central no Core e crypto caseiro:
`python -m pip install -e ".[siwc]"` no ambiente deliberadamente escolhido.

Store sem path default/import de tokens de ambiente/outros apps. Diretorio
absoluto explicito fora de Git/OneDrive, parent existente, sem symlink/reparse/
hardlink. Windows DPAPI CurrentUser real sem plaintext fallback. POSIX owner-only
0700/0600 (plaintext privado, nao criptografia). UUIDv4 host persistente, registros
por client/subject, refs opacas sem email/tokens/identidades expostas.

Refresh explicito segura lock OS entre load -> request -> replace atomico,
inclusive entre processos; lock ocupado recusa sem request/retry. Rele tokens
mais recentes; valida replacement ID quando presente; retencao de ID/scope/
refresh se omitidos. Tokens/datas/scopes gravados juntos antes de ativar sessao.
Commit bem-sucedido e linearizacao local: cancel durante commit nao deixa disco
novo/sessao velha. Erros antes de replace preservam bytes. Fsync de diretorio
POSIX ou cleanup de lock pode falhar depois de replace: commit ambiguo, nao
garantia de power-loss nem promessa de preservar a dupla antiga nesses erros.
Falha de rede/invalid_grant/commit depois de rotacao remota nao prova que refresh
antigo segue valido. Sem retry automatico; reautorizacao explicita separada.

Catalogo so mostra models visibility:list na ordem fornecida e slug exato.
Provider MB221 exige selecao/scope/expiry; troca/refresh/disconnect invalidam
providers antigos inclusive streaming cooperativo. Sem inferencia automatica,
tools ou prosa livre promovida: E2E passa pela sintese extrativa e Core canonico.
OAuth autentica conta externa, NAO operador JARVIS, receipt ou scope de acao.
No-go API mutante mantido, memoria/governanca/sintese continuam soberanas.

## Uso humano deliberado

Comando standalone chatgpt-account; registry agora46 comandos. Exemplos nao
executados nesta rodada (parent C:/JarvisPrivate deve existir e ser privado):

```powershell
python -m apps.jarvis_console chatgpt-account --authorized --credential-dir C:/JarvisPrivate/siwc --action connect
python -m apps.jarvis_console chatgpt-account --authorized --credential-dir C:/JarvisPrivate/siwc --action profiles
```

Diretorio siwc novo/vazio ou store existente. Listener inicia antes do browser.
URL/state/code/nonce/tokens/client/subject/email nao impressos. Ref opaca JSON
usada como --profile-ref profile-<64hex> com --action catalog ou refresh;
connect com ref reautoriza mesma conta. Sem selecao implicita de perfil/modelo.
Timeout callback1..600s; HTTPS bounded. Sem opt-in/args validos/JWT extra no
connect: nenhuma init/rede/browser. Catalogo sensivel omitido integralmente.
Perfil opaco nao e segredo de autorizacao nem autenticacao humana.

## Evidencia, threat model e incidentes

Testes de fluxo/JWT/HTTPS/loopback/storage/session/CLI: RSA real, sockets
loopback reais, DPAPI sintetico temporario, locks entre processos/restart,
HTTPS/browser injetados, E2E provider -> sintese -> Core/memoria/eventos.
Nenhuma conta/store/token/browser humano ou modelo/request externo utilizado.
JWT opcional ausente: testes criptograficos skip explicito; runtime recusa.

Host/mesmo usuario sao TCB; nao ha protecao contra administrador, codigo
malicioso same-UID, rollback de backup ou host comprometido. Nao ha hard-kill
de DNS, revogacao remota, deleteperfil, garantia de power-loss ou homologacao
OAuth/modelo real. Web/stream UI/voz/mic/scheduler continuam gaps separados.
disconnect_local encerra memoria, NAO revoga servidor nem apaga store.
Rollback: retirar injecao/nao chamar fluxo opt-in; Core/native e stores intactos.

Incidente: parar provider, disconnect local, revogar nos controles oficiais da
conta. Nunca registrar tokens/callbacks em log/issues/terminal. Corruptstore/lock
ocupado nao dispara reset/apagamento. Reautorizar explicitamente sem callback
reutilizado; erro remoto nao comprova validade de tokens preservados localmente.

## Fontes oficiais

OpenAI Docs influenciou cliente publico sem secret/API key, assinatura JWT por
biblioteca mantida e catalogo por conta, sem promover motor externo ao nucleo.

- [Sign in](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
- [Profiles and sessions](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions)
- [Models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [JWT validation](https://developers.openai.com/siwc/website)
