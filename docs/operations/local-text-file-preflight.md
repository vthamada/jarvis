# Preflight seguro de arquivo-texto local

## Objetivo

O slice `MB-215` prepara uma operacao `create_text` ou `replace_text` em um
root local explicitamente configurado. Ele valida permissao, escopo, path,
conteudo atual, conteudo desejado e rollback, mas nao cria diretorio, arquivo,
temporario, backup, journal, dispatch ou claim.

O resultado e evidencia de inspecao. Ele nao e autoridade de execucao e nao
pode ser reutilizado como grant de escrita.

## Fronteira de autoridade

Cada preflight exige um grant `prepare_external_action` real, ativo, nao
consumido e exatamente ligado a:

- sujeito;
- adapter e versao;
- operacao e resource ref;
- action fingerprint e intent fingerprint;
- descriptor e epoch de registry;
- SHA-256 UTF-8 exato do texto desejado como `content_digest` do intent;
- root-config fingerprint exato como `precondition_digest` do intent;
- expiracao real da autorizacao.

O `OperationalService` injeta a porta read-only da Governanca. O adapter chama
essa porta com o instante UTC efetivo antes do primeiro acesso ao filesystem.
Ausencia, excecao, retorno diferente de `True`, grant expirado, claim anterior,
descriptor removido ou qualquer binding divergente bloqueia o preflight sem
I/O no root. A verificacao usa uma transacao de leitura revertida e nao cria nem
consome linhas no ledger.

Trocar apenas `desired_text` ou reapresentar o mesmo grant depois de mudar o
alias/root nao e permitido: o bridge recomputa o hash do texto e reapresenta o
root CAS, e a Governanca compara ambos ao intent persistido antes do primeiro
`lstat`, `scandir`, `CreateFileW` ou `openat`.

Uma decisao `require_confirmation` ainda permite este preflight porque ele e
somente leitura. A confirmacao continua obrigatoria para uma futura mutacao.

## Configuracao de roots

Roots sao opt-in e associados a aliases canonicos em minusculas. A
configuracao rejeita, antes de tocar o filesystem:

- path relativo, root do volume ou root `/`;
- UNC, namespace extended/device e drive-relative;
- NUL, controles, formatos invisiveis, percentuais e Unicode nao NFC;
- segmentos `.`/`..`, separadores repetidos e nomes de device Windows.

O fingerprint de configuracao contem alias, identidade dos roots, allowlist de
extensoes, limite de bytes e versoes de policy/backend. Ele nao contem path
absoluto. O caller apresenta esse fingerprint como precondicao CAS.

## Politica de resource e conteudo

O resource usa a gramatica exata:

`text:<root-alias>/<relative-path>`

O path relativo:

- usa somente `/` e Unicode NFC;
- nao aceita absolute, drive, UNC, ADS, device, wildcard, `%`, controle,
  traversal, segmento vazio ou trailing dot/space;
- rejeita nomes reservados Windows, inclusive `CLOCK$`, `CONIN$`, `CONOUT$`,
  `COM1..9`, `LPT1..9` e variantes sobrescritas `¹²³`;
- respeita limites conservadores em bytes UTF-8 e unidades UTF-16;
- termina em uma extensao allowlisted; o baseline aceita `.md` e `.txt`.

Texto atual e desejado devem ser UTF-8 estrito, NFC, sem BOM, NUL, surrogate,
carriage return ou controles fora de LF e TAB. O adapter nao normaliza newline
nem conteudo silenciosamente. O limite padrao e 1 MiB e a leitura e limitada a
`max_bytes + 1` para detectar overflow.

`create_text` exige target ausente. `replace_text` exige arquivo regular com um
unico link e SHA-256 atual exatamente igual a `expected_current_sha256`.
Diretorio, symlink, junction, reparse point, hardlink, FIFO e target trocado
durante a leitura falham fechados.

## Leitura por handle e TOCTOU

No POSIX, root e parents sao percorridos por descritores `dir_fd` com
`O_NOFOLLOW`, `O_DIRECTORY` e `O_NONBLOCK`; target e aberto relativamente ao
parent e validado por `fstat` antes da leitura. A enumeracao de nomes para
detectar colisao casefold em create tambem usa o descritor do parent.

No Windows, roots, parents e target sao abertos com handles Win32 e
`FILE_FLAG_OPEN_REPARSE_POINT`. A implementacao valida atributos, File ID,
numero de links e o path final de cada handle antes de `ReadFile`; caminho
final remoto, reparse ou fora do root bloqueia. Parents case-sensitive sao
bloqueados para create, preservando a deteccao exata de colisao sem enumerar um
path que possa ter escapado.

Snapshots de identidade sao comparados antes/depois. Essa prova fecha leitura
fora do root no preflight, mas nao autoriza uma escrita posterior: o estado pode
mudar depois que o handle e fechado.

## Resultado e confidencialidade

O resultado frozen inclui:

- hashes before/desired e tamanhos;
- diff unificado deterministico com labels relativos;
- fingerprint do diff, snapshot, rollback e preflight;
- versoes de policy, diff, snapshot e backend;
- janela curta do preflight e expiracao real do grant;
- `execution_grant_required=True` e todas as autoridades de execucao falsas.

O diff pode conter linhas atuais e desejadas. Portanto
`contains_sensitive_diff=True`, `persistence_allowed=False` e
`telemetry_allowed=False` sao invariantes. Somente hashes e metadados sem path
absoluto podem entrar em evidencia duravel. O diff deve permanecer na memoria
do caller e ser descartado quando a inspecao terminar.

O fingerprint do preflight liga o `diff_sha256`, mas nao serializa novamente o
diff sensivel. Validadores puros recomputam fingerprints e rejeitam tamper ou
flags de autoridade.

## Plano de rollback

Como `MB-215` nao escreve, seu rollback operacional e desabilitar/remover o
descriptor e deixar novos preflights falharem. Nenhuma restauracao de dados e
necessaria.

O plano retornado e somente uma precondicao content-free para o proximo slice:

- create: `delete_created_file`, condicionado ao hash desejado;
- replace: `restore_previous_content`, ligado aos hashes before e desired.

Ele nao contem bytes de backup e declara `manual_execution_required=True`.

## Limite para MB-216

`MB-216` deve criar um novo action intent e um novo grant de execucao. O novo
grant precisa ligar, no minimo, `preflight_fingerprint`, hash desejado,
precondition/before hash, root-config fingerprint, operacao exata e uma versao
de descriptor mutante separada. Imediatamente antes do efeito, a implementacao
deve reabrir handles seguros, revalidar identidade e hashes, consumir grant e
confirmacao atomicamente e usar journal/backup duraveis.

O grant prepare-only de `MB-214`/`MB-215`, o diff ou o plano de rollback nunca
substituem essa nova autorizacao.

## Validacao operacional

O gate do slice inclui contratos/schemas, corpus lexical Windows, roots
perigosos sem I/O, symlink/reparse/junction/hardlink/FIFO, swaps deterministas,
leitura por handle, expiracao e forged grants antes de I/O, reproducibilidade
de diff/fingerprints, zero escrita e ledger inalterado.

Comandos de fechamento:

```powershell
python -m pytest services/operational-service/tests/test_local_text_file_preflight.py services/operational-service/tests/test_local_text_file_preflight_integration.py services/governance-service/tests/test_adapter_preflight_governance.py -q
python tools/engineering_gate.py --mode standard
```
