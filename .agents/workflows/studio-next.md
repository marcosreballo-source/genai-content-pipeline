---
description: Retoma qualquer trabalho do Studio do ponto em que parou, executando só o próximo passo (deck, documento, fonte ou revisão). Uso do Studio.
---
0. Ler `<AGENT_DIR>/rules/studio-core.md`.
1. Pergunte a pasta do job ou o id da fonte; se houver um único job em andamento em `studio/jobs/`, use-o.
2. `python studio/scripts/studio_next.py <job>` (ou `--source <SRC>`).
3. Execute **somente** o passo indicado, com a skill indicada.
4. Diga ao usuário em até 5 linhas o que foi feito e o próximo passo. PARE.
