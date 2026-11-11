# Arquétipos de slide (gerado por mf_deck.py archetypes --md; não editar)

Campos comuns a todos: `id`* (SL-01), `archetype`*, `notes` (≤180 palavras), `sources` (lista), `hidden`. Campos com * são obrigatórios.

## title
Capa: título, subtítulo, autor, evento e data.

- `title`*: texto ≤70
- `subtitle`: texto ≤120
- `author`: texto ≤80
- `event`: texto ≤80
- `date`: texto ≤40

## agenda
Roteiro da apresentação (3 a 7 itens).

- `title`: texto ≤60
- `items`*: lista 2–7 de (texto ≤70)

## section
Divisória de seção (fundo escuro).

- `number`: texto ≤4
- `title`*: texto ≤60
- `subtitle`: texto ≤120

## bullets
Título-mensagem + até 6 tópicos; 'takeaway' opcional em destaque no rodapé.

- `title`*: texto ≤90
- `bullets`*: lista 1–6 de (tópico ≤120 (ou {text, sub: [≤3]}))
- `takeaway`: texto ≤120

## statement
Uma frase forte, sozinha no slide (tese, insight, problema).

- `statement`*: texto ≤160
- `support`: texto ≤140

## big_number
Um número que conta a história (ex.: '73%').

- `title`: texto ≤90
- `value`*: texto ≤12
- `label`*: texto ≤80
- `context`: texto ≤140

## kpis
2 a 4 indicadores lado a lado.

- `title`: texto ≤90
- `items`*: lista 2–4 de ({value*: texto ≤10, label*: texto ≤60, delta: texto ≤24})

## two_column
Dois blocos paralelos (ex.: problema/solução, teoria/prática).

- `title`*: texto ≤90
- `left`*: {heading: texto ≤40, bullets*: lista 1–5 de (tópico ≤100 (ou {text, sub: [≤3]}))}
- `right`*: {heading: texto ≤40, bullets*: lista 1–5 de (tópico ≤100 (ou {text, sub: [≤3]}))}

## comparison
2 ou 3 opções comparadas; 'highlight' marca a recomendada.

- `title`*: texto ≤90
- `columns`*: lista 2–3 de ({heading*: texto ≤40, items*: lista 1–5 de (texto ≤80), highlight: true/false})

## image
Imagem/figura com legenda; layout full, left ou right (left/right aceitam bullets).

- `title`: texto ≤90
- `image`*: caminho de arquivo
- `caption`: texto ≤140
- `source`: texto ≤100
- `layout`: full|left|right
- `bullets`: lista 0–4 de (tópico ≤100 (ou {text, sub: [≤3]}))

## chart
Gráfico nativo e editável (bar, column, stacked_column, line, pie, doughnut).

- `title`*: texto ≤90
- `takeaway`: texto ≤140
- `source`: texto ≤100
- `chart`*: {type*: bar|column|stacked_column|line|pie|doughnut, categories*: lista 1–12 de (texto ≤30), series*: lista 1–4 de ({name*: texto ≤30, values*: lista de números}), unit: texto ≤12, number_format: texto ≤20, highlight: texto ≤30}

## table
Tabela compacta (até 6 colunas x 7 linhas).

- `title`*: texto ≤90
- `columns`*: lista 2–6 de (texto ≤24)
- `rows`*: lista 1–7 de (lista 1–6 de (texto ≤40))
- `highlight_row`: inteiro
- `source`: texto ≤100

## timeline
Marcos no tempo (2 a 6).

- `title`*: texto ≤90
- `events`*: lista 2–6 de ({when*: texto ≤16, label*: texto ≤40, detail: texto ≤90})

## process
Etapas de um processo/método (2 a 6).

- `title`*: texto ≤90
- `steps`*: lista 2–6 de ({label*: texto ≤30, detail: texto ≤90})

## quote
Citação/depoimento com autor.

- `quote`*: texto ≤220
- `author`: texto ≤60
- `role`: texto ≤80

## code
Trecho de código (até 18 linhas x 90 colunas).

- `title`*: texto ≤90
- `language`: texto ≤20
- `code`*: bloco ≤18 linhas x 90 col
- `caption`: texto ≤120

## equation
Equação em LaTeX (subconjunto mathtext no pptx; LaTeX completo no Beamer).

- `title`*: texto ≤90
- `latex`*: LaTeX
- `explanation`: lista 0–3 de (texto ≤110)

## diagram
Diagrama a partir de código Mermaid ou de uma imagem pronta.

- `title`*: texto ≤90
- `mermaid`: bloco ≤40 linhas x 120 col
- `image`: caminho de arquivo
- `caption`: texto ≤140

## team
Pessoas (1 a 6) com papel; foto opcional.

- `title`: texto ≤90
- `members`*: lista 1–6 de ({name*: texto ≤40, role: texto ≤50, detail: texto ≤80, photo: caminho de arquivo})

## closing
Encerramento/pedido (ask, CTA, próximos passos).

- `title`*: texto ≤70
- `message`: texto ≤160
- `items`: lista 0–4 de (texto ≤80)
- `contact`: texto ≤120

## references
Referências (até 8), em formato já pronto.

- `title`: texto ≤60
- `items`*: lista 1–8 de (texto ≤220)

## qa
Slide de perguntas.

- `title`: texto ≤40
- `contact`: texto ≤120
