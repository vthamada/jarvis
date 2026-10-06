# Validacao Linux explicita

Este runner e uma ferramenta de desenvolvimento. Nao prepara ou inicia Docker,
WSL ou infraestrutura automaticamente. O operador retomou a execucao em
2026-10-05: a bateria physical em Docker Linux teve 202 passed/5 skips somente
Windows. Gates standard e release Linux passaram, incluindo baseline development
SQLite; isso nao comprova PostgreSQL/Node nem durabilidade em disco persistente.
Evidencia, limites e estado dos gates em
`docs/operations/linux-physical-validation-2026-10-05.md`.
Testes unitarios do runner nao provam efeitos fisicos Linux nem fecham MB218/MB219.

Quando o operador decidir executar, com Docker Linux disponivel:

```powershell
.venv/Scripts/python.exe tools/run_linux_validation.py --build --mode physical
```

`--build` permite explicitamente baixar a imagem base e dependencias de teste;
pode manter imagem/cache no Docker. Sem esse flag, exige imagem existente.
`standard` e `release` executam os gates Python correspondentes. A imagem nao
inclui Node ou PostgreSQL: skips/requisitos de outros backends continuam
explicitos, e nao constituem evidencia desses ambientes.
O entrypoint resolve apenas o interpreter confiado da imagem para um path real;
nao relaxa guardas de symlink em sources/modelos/audio. Sem Git/checkout na
imagem, metadados Git de artefatos de teste sao explicitamente unknown.

## Fontes e privacidade

### Campanha de volume persistente

```powershell
.venv/Scripts/python.exe tools/run_linux_validation.py --mode persistent
```

Opt-in separado: cria volume Docker novo/exclusivo, nunca adota volume existente
nem aceita path de host. Verifica UUID/labels/driver local/Options vazias antes
de cada fase e cleanup. Seis containers distintos exercitam CLI/Core com
prepare/confirm/crash86/recover/replace-rollback/verify; um setimo roda o corpus
fisico com basetemp dentro do volume. Imagem SHA e source archive/hash sao
os mesmos em todas as fases. O guest verifica mountinfo nao-tmpfs; identidade
Docker owned e verificada pelo host runner, nao somente por mountinfo.

Falha/timeout/interrupcao preserva o volume e imprime seu nome exato.
Sucesso remove apenas o volume sinteticamente criado; cleanup nao confirmado
falha a campanha. Sem prune, reset ou limpeza de dados existentes. Essa prova
e recovery de processo/container em filesystem persistente, nao power-loss,
reboot do host, disco realmente cheio ou fault injection do SQLite VFS.
Detalhes/resultado: `docs/operations/mb218-mb219-persistent-readiness-2026-10-05.md`.

### Archive de fontes

O runner transfere um archive de diretorios/arquivos de desenvolvimento
selecionados, incluindo alteracoes locais ainda nao commitadas. Nao monta o
workspace humano, nao copia `.git`, `.venv`, arquivos ocultos ou bases `.db`.
Recusa symlinks, junctions/reparse points e arquivos hardlinked. Valida limites
antes da leitura e le cada arquivo de forma limitada, recusando mudancas
observadas durante a leitura. Isso nao e uma sandbox contra um processo hostil
do mesmo usuario fazendo races no host.

Uma denylist exclui nomes comuns de dados `auth`, `credentials`, `secret(s)` e
`token(s)`, inclusive variantes com sufixos, em JSON/TOML/YAML/TXT/CSV. Modulos
Python como `auth.py` permanecem fontes. **Nao ha garantia de exclusao absoluta
de segredos:** qualquer arquivo visivel selecionado, incluindo fixtures,
documentos ou configs com outros nomes, pode conter dados privados. Revise as
fontes e o pequeno contexto `tools/linux_validation` antes de autorizar build
ou execucao; nao coloque tokens nem dados humanos nesses arquivos.

## Execucao, limites e cleanup

O comando gerado usa rede `none`, filesystem da imagem read-only, caps removidas
e `no-new-privileges`, sem mounts do host. Fontes e targets de testes ficam no
tmpfs Linux `/tmp`. O extractor aceita somente arquivos regulares relativos;
recusa links, duplicatas, `..`, paths absolutos, backslashes e drive names.
Metadados iniciais do entrypoint sao declaracao de configuracao, nao prova de
sucesso. Somente resultados efetivos dos testes/gates oferecem evidencia, com
skips e falhas preservados.
O modo physical usa `-ra` e somente o quiet padrao do pyproject para exibir
contagens e motivos dos skips. tmpfs nao prova durabilidade contra power loss
ou reboot do host; essa campanha exige storage persistente separado.

Build tem timeout de 10 minutos; execucao, 30 minutos. Cada execucao usa nome
unico `jarvis-linux-validation-<uuid>`, `--rm` e tentativa `docker rm --force`
desse nome em `finally`, inclusive em timeout/Ctrl+C, limitada a 15 segundos.
Nao remove imagens, caches, volumes ou outros containers. Cleanup e best-effort:
daemon inacessivel, interrupcao forcada do processo/maquina ou segundo Ctrl+C
podem impedir confirmacao. Preserve o nome unico/logs para inspecao manual,
sem enumerar/deletar recursos humanos por conveniencia.
