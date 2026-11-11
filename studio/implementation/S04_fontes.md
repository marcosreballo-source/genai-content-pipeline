# S04: Source Library com a sua triagem de PDFs e o gate de bibliografia

**Depende de:** S03 · **Gate humano:** não

## Preâmbulo
Siga o preâmbulo da X01. Leia o contrato `chunker` em `studio/implementation/mapping/studio_matrix.md`. Use `/sl-add` e `/sl-coverage` (skills **sl-ingest**, **sl-extract**, **sl-coverage**).

## Objetivo
Ligar o pipeline de triagem do usuário (trechos de 4 páginas) à Source Library **sem alterá-lo**, provar que as fichas não resumem demais e ativar o aviso de "falta material base" nos cursos.

## Tarefas
1. **Fonte real:** peça ao usuário um livro ou apostila já usado (ex.: a base do KT_Aramis). Registre: `sl_sources.py add ... --origin <nome do pipeline de triagem>`.
2. **Integração com a triagem (INTEGRATE):** peça ao usuário para rodar o pipeline dele como sempre (ou rode-o você, **sem mudar parâmetros**, se ele autorizar). Depois:
   ```
   python studio/scripts/sl_sources.py import-chunks <SRC> --dir <pasta de saída da triagem> --pages 4
   ```
   Confira em `studio/sources/<SRC>/chunks/chunks.yaml` se as páginas (`loc`) batem com os trechos. Se o padrão de nomes não traz páginas, registre o problema no LOG e use `--pages` para numerar em sequência. Sem pipeline utilizável: use `sl_sources.py chunk <SRC> --pages 4`.
3. **Fidelidade:** com a skill **sl-extract**, fiche os **3 primeiros trechos com conteúdo** (uma ficha por rodada) e valide cada um. Mostre ao usuário uma ficha e o trecho original lado a lado e pergunte se algo importante foi omitido. Ajuste o que for preciso só em dados (as regras da skill, num arquivo `studio/sources/EXTRACTION_NOTES.md` que a skill passa a ler); nunca no script.
4. **Índice e pacote:** `sl_sources.py index` e `sl_sources.py pack --concepts "<2 conceitos dos trechos>"`. Mostre o pacote ao usuário.
5. **Gate de bibliografia num curso real:** rode a skill **sl-coverage** sobre `knowledge_factory/projects/KT_Aramis/03_knowledge/knowledge_graph.md` com `--policy warn` (só diagnóstico nesta etapa). Mostre a tabela de pedidos de bibliografia. Isso é o "aviso de falta de material base" que o usuário pediu: ele providencia, e o fluxo `/sl-add` + `fulfill` fecha o pedido.
6. **Plano de processamento:** com o usuário, decida quais fontes processar por completo (estime rodadas: 1 trecho = 1 rodada) e registre em `studio/sources/backlog.md`.

## Critérios de aceite
- [ ] Fonte real importada da triagem (ou dividida pelo Studio), com páginas corretas.
- [ ] 3 fichas válidas e aprovadas pelo usuário quanto à fidelidade.
- [ ] Relatório de cobertura do KT_Aramis com pedidos de bibliografia apresentados.
- [ ] Pipeline de triagem intacto (guard limpo).

## Ao terminar
Atualize o LOG, resuma em até 150 palavras e **PARE**.
