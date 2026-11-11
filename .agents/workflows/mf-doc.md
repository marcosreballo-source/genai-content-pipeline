---
description: Cria ou continua um documento LaTeX (apostila, livro, lista, artigo, relatório, tese, manual) a partir de um template registrado, com fontes, unidades curtas, build e revisão. Uso do Studio.
---
0. Ler `<AGENT_DIR>/rules/studio-core.md` e aplicá-la durante todo o comando.
1. Job novo: `python studio/scripts/mf_latex.py list` para ver os templates. Sem o template desejado, rode antes `/mf-template-add`. Depois: `python studio/scripts/mf_latex.py new <template> <job>`.
2. Skill **mf-brief** (campos de topo do doc.yaml) e skill **mf-doc-architect** (seções). Mostre a estrutura e PARE até a aprovação (`doc.approved`).
3. Material técnico: skill **sl-coverage** sobre as seções. Pedidos de bibliografia abertos para seções essenciais: avise o usuário e só produza as seções cobertas.
4. Rode `python studio/scripts/studio_next.py <job>` e execute **apenas** o passo indicado (**mf-doc-writer** para escrever, compilar ou corrigir; **rep-reviewer** para revisar).
5. Ao fim de cada passo, diga em até 5 linhas o que foi feito e o próximo passo. "continue" volta ao passo 4.
6. PRONTO: entregue `build/document.pdf` e `review/report.md`.
