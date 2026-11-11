---
name: mf-deck-writer
description: Escreve UMA unidade de slides (spec/Uxx.yaml) por rodada a partir do outline aprovado, com conteúdo fundamentado e dentro dos limites dos arquétipos; também aplica correções vindas da revisão. Use quando studio_next indicar 'escrever a unidade' ou 'corrigir' num deck. Uso do Studio: acionar apenas em comandos /mf-*, /sl-*, /rep-*, /studio-* ou em jobs do Studio.
---
## Entradas (só estas)
- A unidade em `<job>/plan.yaml` (ids dos slides) e as linhas correspondentes de `<job>/outline.yaml`.
- `studio/formats/deck/archetypes.md`: só as seções dos arquétipos usados na unidade.
- `studio/formats/deck/writing_rules.md`
- Pacote de fundamentação: `python studio/scripts/sl_sources.py pack --concepts "<conceitos da unidade>" --max-words 700`
- `<job>/brief.yaml` (público e objetivo) e arquivos em `<job>/assets/`.

## Saída
- `<job>/spec/Uxx.yaml` com `slides:` na ordem do plano.

## Procedimento
1. Para cada slide da unidade, preencha os campos do arquétipo:
   - título-mensagem a partir da `message` do outline;
   - conteúdo só do pacote de fundamentação, do brief ou dos assets;
   - `sources` em todo slide com afirmação factual;
   - `notes` quando o plano disser "notas obrigatórias".
2. Dado ausente: `[[PENDENTE: ...]]` e uma linha em `<job>/pending.md`.
3. Rode `python studio/scripts/mf_deck.py validate <job> --unit Uxx` e corrija até zerar os erros (isso marca a unidade como done).
4. Responda ao usuário em até 5 linhas: unidade feita, pendências criadas, próximo passo (`studio_next.py`).

## Modo correção (revisão)
1. Leia em `<job>/review/revision_plan.yaml` as ações com `status: todo` do slide indicado.
2. Altere só o necessário no `spec/Uxx.yaml` correspondente, valide e marque a ação como `status: done`.
3. Se a correção exigir mudar o outline (novo slide, outra ordem), pare e peça aprovação.

## Proibições
- Escrever mais de uma unidade por rodada.
- Mudar arquétipo, ordem ou ids sem atualizar o outline.
- Conteúdo de memória quando o pacote voltar "SEM FONTE".
