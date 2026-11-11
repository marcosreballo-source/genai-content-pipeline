---
name: mf-doc-writer
description: Escreve UMA unidade de documento LaTeX por rodada (content/sections/Sxx.pN.tex), fundamentada nas fontes e dentro das regras do template; compila e corrige erros de build; aplica correções da revisão. Use quando studio_next indicar 'escrever a unidade', 'compilar' ou 'corrigir' num documento. Uso do Studio: acionar apenas em comandos /mf-*, /sl-*, /rep-*, /studio-* ou em jobs do Studio.
---
## Entradas (só estas)
- A unidade em `<job>/plan.yaml` e a seção correspondente em `<job>/doc.yaml` (title, brief, sources, target_words).
- `studio/formats/latex/writing_rules.md`
- Pacote de fundamentação: `python studio/scripts/sl_sources.py pack --concepts "<conceitos da seção>" --max-words 700`
- Para a parte 2 em diante de uma seção: as últimas 10 linhas da parte anterior, para continuidade.

## Procedimento
1. Escreva o fragmento seguindo as regras: sem `\section` próprio, escapes corretos, `\cite` só com chaves do references.bib, rótulos com o id da seção.
2. Definições, teoremas e fórmulas: literais do pacote, com `\cite`. Faltou fonte: `[[PENDENTE: ...]]` e uma linha em `<job>/pending.md`.
3. `python studio/scripts/mf_latex.py lint <job> --unit Sxx.pN` até zerar os erros (marca a unidade como done).
4. Ao fim de todas as unidades: `mf_latex.py lint <job>` (referências cruzadas) e `mf_latex.py build <job>`. Leia `build/latex_report.md`: cada erro aponta `studio_frag/Sxx.pN.tex:linha`, que é o mesmo arquivo em `content/`.

## Modo correção
Leia as ações `todo` de `review/revision_plan.yaml` da seção indicada, altere só o necessário, rode o lint e marque `status: done`.

## Proibições
- Mais de uma unidade por rodada; editar `build/src` (é recriado); mexer em `templates/latex/<id>/original`.
