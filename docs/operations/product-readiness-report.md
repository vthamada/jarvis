# Inventário atual de prontidão do produto

O inventário em `docs/implementation/product-readiness.json` é uma projeção
autoral das 13 frentes de produto e três transversais já definidas em
`docs/implementation/parallel-implementation-map.md`. Não cria outra fila,
novos IDs MB, dependências ou critérios de promoção. Documento-Mestre,
Implementation Master Map e backlog único continuam soberanos.

Snapshot revisado: 2026-10-06. Último recorte validado: MB235, done local após
gate standard completo. MB233/234 entregam leitura humana Web e MCP readonly
do inventário; MB235 fecha a ergonomia compacta da Web existente com prova
no browser e final integral preservada. MB236 blocked para aceite real:
catálogo bounded e diagnóstico host opt-in validados,326 testes novos/535
focados e gate global8994 casos (8883 passed/111 skipped/zero falhas).
Segunda tentativa única autorizada com gpt-6-astra após refresh explícito
de sessão expirada recebeu HTTP200, mas recusou unsupported_response_encoding
antes do SSE. Código cobre MIME OU Content-Encoding, ainda não distinguidos.
ALLOW/rejected/final nativa2635 exata ao export/GET/reload. Sem reenvio/fallback/
tools ou inferência/qualidade homologadas. Próximo recorte candidato exige
DOR, categorias fixas/corpus/gate; nova inferência novo consentimento.
Consulte real-oauth-acceptance.md.
Leitura manual offline do MB230 não equivale à Web pareada MB231/232.
A existência do código
ou de um caminho de evidência não comprova automaticamente seu aceite.

## Consultar

Da raiz do repositório:

```powershell
python tools/product_readiness_report.py
python tools/product_readiness_report.py --format json
```

MB234 acrescenta consulta MCP stdio opt-in do JSON fixo, com cliente/servidor
próprios e scope readonly, sem Core ou sondagem dinâmica. Aceite local do
servidor próprio não valida terceiros nem consumidor governado. Comando e limites no
[runbook Web/MCP](web-projection-and-readiness-mcp.md).

A tabela resume o principal aceite restante. JSON inclui baseline disponível,
todos os aceites restantes, referências e contagens por estado. A saída é UTF-8.
É possível fornecer outro snapshot revisado em `docs/implementation/` com
`--inventory docs/implementation/outro-snapshot.json`; caminhos externos,
privados, absolutos e traversal são recusados.

O comando é readonly, usa somente a biblioteca padrão e não importa Core,
modelos, adapters ou runtime humano. Só lê o JSON selecionado. Referências são
validadas por existência e contenção no workspace; seus conteúdos não são
lidos, nem testes/gates executados. Nenhuma conta, rede, áudio, SQLite, token,
login ou refresh é acessado. Erros exibem apenas diagnóstico fixo.

## Interpretar os estados

| Estado | Significado limitado |
| --- | --- |
| `partial` | Há componentes/slices entregues; a frente ainda não fecha a experiência alvo. |
| `foundation` | Infraestrutura ou piloto existe; não comprova utilidade integrada real. |
| `not_implemented` | A frente dedicada não foi entregue; referências/componentes vizinhos não a substituem. |
| `validated_slice` | Um recorte delimitado foi validado; não representa toda a frente pronta. |

Não há estado `completed`, `promoted` ou `product_ready` para uma frente, nem
percentual fictício de conclusão. O relatório declara `product_ready=false` e
`runtime_verified=false`: é um inventário revisado, não sondagem dinâmica.
As contagens não são pesos de esforço, cronograma ou prova de qualidade.

Exemplos importantes: Web responsiva não fecha mobile; OAuth de provider não
fecha integrações de serviços; laboratório TTS não aprova naturalidade vocal;
TLS sintético não prova navegação externa; Linux/SQLite local validado não
promove API pública mutante, hardware power-loss ou toda mudança posterior.

## Manutenção e validação

Ao fechar um recorte, o coordenador revisa os fatos e aceites da frente, data,
`last_validated_mb` e `active_mb` (ou `null` quando não há recorte ativo).
Atualizar este arquivo é consequência do aceite no backlog único, nunca sua
substituição. Histórico detalhado e testes permanecem nos runbooks originais.
Critérios textuais são julgamentos autorais; o validador não decide sua verdade
semântica nem transforma alegações em evidência.

Schema estrito: campos desconhecidos/duplicados, IDs fora de ordem, frentes
ausentes, status não suportado, referência inválida e dados fora dos limites
são recusados. Caminhos devem ser relativos POSIX para fontes/docs permitidos;
symlinks não podem escapar do workspace ou disfarçar diretórios privados.

```powershell
python -m pytest tests/unit/test_product_readiness_report.py
python tools/engineering_gate.py --mode standard
```

Desativação: deixar de executar o relatório. Não há migration, serviço,
agendamento, promoção, mudança de política ou escrita em dados humanos.
