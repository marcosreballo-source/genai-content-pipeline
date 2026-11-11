# X03: Plano de merge do Studio (GATE X)

**Depende de:** X02 (DONE) · **Gate humano:** **SIM**

## Preâmbulo
Siga o preâmbulo da X01. Leia `studio/implementation/mapping/studio_overlap.md`, `studio/implementation/STUDIO_PROTOCOL_ADDENDUM.md` e as seções de disposição de `knowledge_factory/implementation/MIGRATION_PROTOCOL.md`. Só escreva em `studio/implementation/mapping/`.

## Regras de decisão (em ordem)
1. Item de outra frente cuja **saída** o Studio consome, sem substituí-lo (ex.: pipeline de triagem) → **INTEGRATE**.
2. Item compartilhado por várias frentes e coberto pelo Studio (ex.: skill de slides) → **SUPERSEDE**, sempre com piloto por frente antes do cutover.
3. Item exclusivo de cursos/KF coberto pelo Studio → **ABSORB** (vários no mesmo papel: **MERGE**).
4. REP antigo → **ABSORB/MERGE** nas lentes e personas: cada partição vira critério de lente existente ou lente nova (`studio/review/lenses/<id>.yaml`, criada na S05).
5. Workflows de área → **UPLIFT**, um por vez (U01), na ordem de benefício definida na X02.
6. Itens da KF (`kf-*`) → adaptação interna na S07, com entradas em `approved_changes.txt` aprovadas pelo usuário.
7. Sem relação → **ISOLATE**. Futuros formatos (X09) → apenas registrar para a Parte 2.

## Tarefas
1. **Perguntas ao usuário** (uma mensagem):
   - (a) Quais frentes devem pilotar o Studio para slides antes de substituir a skill antiga?
   - (b) Quais comandos antigos você quer manter como alias?
   - (c) Política de bibliografia padrão para novos cursos: `strict` (bloqueia tópico sem fonte) ou `warn`?
   - (d) Ordem das áreas no upgrade (sugira a da X02).
2. **Matriz** `studio/implementation/mapping/studio_matrix.md`:

   | Papel | Item(ns) | Disposição | Nome-alvo | Quando (S0x) | Alias | Dependentes | Notas | Aprovação |
   |---|---|---|---|---|---|---|---|---|

   Acrescente também a tabela **Itens intocáveis** (ISOLATE e originais de INTEGRATE).
3. **Contrato da triagem (INTEGRATE)**, no mesmo arquivo:
   ```yaml
   chunker:
     item: <nome>
     how_to_run: "<como o usuário roda hoje>"
     output_dir_pattern: "<pasta>"
     import_cmd: "python studio/scripts/sl_sources.py import-chunks <SRC> --dir <pasta> --pages 4"
     filename_pattern: "<ex.: livro_p001-004.pdf>"
     gaps: "<se o padrão de nome não traz páginas, como mapear>"
   ```
4. **Plano do REP:** a tabela da X02 com a decisão por linha (`lente existente: <id>` ou `nova lente: <id>`) e a lista de personas que o REP antigo tinha e o Studio não tem.
5. **Mapa de cutover** `studio/implementation/mapping/studio_rename_map.md`: item antigo, ação na S08 (arquivar com alias, manter ou bloqueado), referências a atualizar. Regra de segurança: se uma referência está numa frente que não aprovou o piloto, o item fica **manter**.
6. **Ajustes por delivery** `studio/implementation/mapping/studio_adjustments.md`: uma linha por delivery S01–S08/U01 dizendo o que muda (ex.: "S04: o chunker é `/triagem`; importar de `triagem/out/`").
7. **GATE X:** apresente contagens por disposição, os itens que serão substituídos e por qual piloto, o contrato da triagem, o plano do REP e a ordem das áreas. Peça aprovação linha a linha ou global e registre `GATE X: aprovado em <data>` no LOG.

## Critérios de aceite
- [ ] Todas as linhas com disposição e aprovação.
- [ ] Nenhum item de outra frente com ABSORB/MERGE.
- [ ] Contrato da triagem e plano do REP definidos.
- [ ] Guard limpo.

## Ao terminar
Atualize o LOG, resuma em até 150 palavras e **PARE**. A S01 só começa com o GATE X aprovado.
