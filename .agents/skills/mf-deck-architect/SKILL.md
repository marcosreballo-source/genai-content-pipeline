---
name: mf-deck-architect
description: Transforma o brief de uma apresentação no outline (uma linha por slide, com seção, arquétipo e mensagem-chave) seguindo o blueprint. Use depois do brief e antes de escrever slides, ou quando o outline precisar ser refeito. Uso do Studio: acionar apenas em comandos /mf-*, /sl-*, /rep-*, /studio-* ou em jobs do Studio.
---
## Entradas
- `<job>/brief.yaml`
- `studio/formats/deck/blueprints/<blueprint>.yaml`
- `studio/formats/deck/writing_rules.md` (seções 1 a 3)
- Fontes: se o deck é técnico, `python studio/scripts/sl_sources.py find "<tema>"` para saber o que existe na biblioteca.

## Saída
- `<job>/outline.yaml`, e `<job>/outline.approved` (vazio) somente depois de o usuário aprovar.

## Procedimento
1. Calcule o número de slides pela `duration_rule` do blueprint e pela duração do brief.
2. Percorra as seções do blueprint na ordem. Inclua todas as `required`; respeite `slides: [mín, máx]`.
3. Para cada slide, escreva:
   ```yaml
   - {id: SL-07, section: resultados, archetype: chart, message: "O modelo supera o baseline em todas as classes"}
   ```
   A `message` é a conclusão do slide (título-mensagem, ≤ 90 caracteres). Escolha o arquétipo pela intenção (tabela da seção 3 das regras).
4. Teste: lendo só as mensagens em sequência, o argumento completo fica claro? Se não, reordene.
5. Rode `python studio/scripts/mf_deck.py plan <job>` e corrija os ERROS. Avisos de faixa de slides podem ficar, se justificados.
6. Mostre ao usuário a lista de mensagens agrupada por seção e pergunte se aprova. Aprovado: crie `outline.approved`.

## Proibições
- Mensagens genéricas ("Introdução", "Resultados"). Cada uma deve afirmar algo.
- Mais de 60 slides num job: divida em dois decks.
