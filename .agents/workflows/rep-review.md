---
description: Revisão de qualquer material por um painel de personas (REP): plano, unidades curtas, consolidação, plano de correção e banco de perguntas. Uso do Studio.
---
0. Ler `<AGENT_DIR>/rules/studio-core.md`.
1. Identifique o material: job do Studio (deck ou documento) ou arquivo avulso (`--file`, ex.: um .md exportado de outra frente).
2. Escolha o painel (`python studio/scripts/rep_review.py list`). Contexto novo ou com documentos reais (rubrica, edital, call): use antes a skill **rep-panel**.
3. `python studio/scripts/rep_review.py plan <job> --panel <painel> [--file <arquivo>]`
4. Uma unidade por rodada com a skill **rep-reviewer**, até todas validarem.
5. `rep_review.py consolidate <job>`: mostre o veredito, os blockers, os majors e as perguntas difíceis.
6. Se o material é do Studio, ofereça aplicar as correções (writer em modo correção) e depois `rep_review.py delta <job>`.
7. Depois do evento real, ofereça calibrar as personas com o feedback recebido (skill **rep-panel**).
