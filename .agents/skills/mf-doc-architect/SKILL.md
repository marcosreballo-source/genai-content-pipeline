---
name: mf-doc-architect
description: Define a estrutura de um documento LaTeX (apostila, livro, artigo, relatório, tese, manual) no doc.yaml (seções, níveis, metas de palavras, fontes e brief por seção) a partir do pedido, de um Knowledge Graph ou de um currículo KF. Use depois do brief em /mf-doc. Uso do Studio: acionar apenas em comandos /mf-*, /sl-*, /rep-*, /studio-* ou em jobs do Studio.
---
## Entradas
- Pedido/brief; `studio/templates/latex/<id>/template.yaml` (section_commands, front_envs, limits).
- Se vier da KF: `curriculum_blueprint.md`, `knowledge_graph.md` (ordem de ensino) e o manifesto (ativo `A-xx`).
- `python studio/scripts/sl_sources.py find "<tema>"` para ver o que há na biblioteca.

## Procedimento
1. Preencha `metadata` (todos os campos do `metadata_map`) e `front` (ex.: resumo, abstract).
2. Liste as seções com:
   ```yaml
   - {id: S03, title: "Busca em largura", level: 1, target_words: 1800, sources: [SRC-cormen-2009], brief: "definição, algoritmo, exemplo, exercício"}
   ```
   Didático: siga a ordem de pré-requisitos do grafo. Acadêmico: siga as seções exigidas pelo venue ou programa.
3. Metas de palavras: some e compare com o limite de páginas (cerca de 450 palavras por página A4 com figuras).
4. Toda seção técnica precisa de `sources`. Sem fonte na biblioteca, rode `sl_sources.py coverage` ou crie um pedido de bibliografia e avise o usuário.
5. `python studio/scripts/mf_latex.py plan <job>`; mostre a estrutura e o total de unidades ao usuário. Aprovado: crie `<job>/doc.approved`.
6. Gere o `.bib`: `python studio/scripts/sl_sources.py bib --out <job>/references.bib --only <SRCs>`.
