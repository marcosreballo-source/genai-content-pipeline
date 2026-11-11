# Exemplos prontos

- `deck_todos_arquetipos/`: status de pesquisa com os 22 arquétipos de slide (pptx e Beamer).
  ```
  cp -r studio/examples/deck_todos_arquetipos studio/jobs/exemplo_deck
  python studio/scripts/mf_deck.py plan studio/jobs/exemplo_deck
  python studio/scripts/mf_deck.py build studio/jobs/exemplo_deck && python studio/scripts/mf_deck.py preview studio/jobs/exemplo_deck
  python studio/scripts/mf_latex.py beamer studio/jobs/exemplo_deck
  ```
- `doc_apostila_grafos/`: capítulo de apostila no template `studio-book`.
  ```
  cp -r studio/examples/doc_apostila_grafos studio/jobs/exemplo_doc
  python studio/scripts/mf_latex.py plan studio/jobs/exemplo_doc && python studio/scripts/mf_latex.py build studio/jobs/exemplo_doc
  ```
Os exemplos são para conferir a instalação e a qualidade visual; o conteúdo é fictício.
