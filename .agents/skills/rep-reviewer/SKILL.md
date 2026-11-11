---
name: rep-reviewer
description: Executa UMA unidade de revisão por rodada, assumindo uma persona do painel e cobrando só os critérios das lentes daquela unidade, com achados localizados, evidência literal, notas pela rubrica e perguntas prováveis. Use quando studio_next indicar 'revisão: unidade Rxx' ou em /rep-review. Uso do Studio: acionar apenas em comandos /mf-*, /sl-*, /rep-*, /studio-* ou em jobs do Studio.
---
## Procedimento
1. Sem plano de revisão ainda: `python studio/scripts/rep_review.py plan <job> --panel <painel>` (para um arquivo avulso: `--file <arquivo.md>`).
2. `python studio/scripts/rep_review.py brief <job> <Rxx>`: imprime persona, rubrica, critérios das lentes, o material da fatia, as prévias e o formato de saída. **Leia só isso.** Se houver caminhos de PNG das prévias, olhe as imagens.
3. Escreva `<job>/review/<Rxx>.yaml` no formato indicado:
   - cada achado tem `location` existente, `evidence` literal (trecho do material), `problem` específico e `suggested_fix` acionável;
   - severidade: `blocker` impede apresentar ou entregar; `major` prejudica a nota ou a decisão; `minor` é polimento;
   - `scores` 1 a 5 por critério da rubrica, com uma frase de justificativa;
   - `questions`: as perguntas que ESTA persona faria, com dificuldade e resposta sugerida baseada no material;
   - `strengths`: até 3, concretos.
4. `rep_review.py validate <job> --unit <Rxx>` até zerar os erros. Pare (uma unidade por rodada).
5. Terminadas as unidades: `rep_review.py consolidate <job>` e mostre ao usuário o veredito, os blockers e as 5 perguntas mais difíceis.

## Postura
- Seja a persona: cobre o que ela cobraria, no tom dela, mas **só com base nos critérios e no material**.
- Não repita o mesmo achado com outras palavras; um achado por problema.
- Sem problemas reais na fatia: `findings: []`. Achado inventado para parecer rigoroso é falha grave.
