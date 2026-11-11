# Scaffold do template studio-book

Arquivo principal: `main.tex` · classe `report` · motor `pdflatex`

## Mudanças feitas na CÓPIA (scaffold/); o original/ está intacto

- inserido \input{studio_meta} antes de \begin{document}
- removido o conteúdo-exemplo do corpo (7 linhas) e inserido \input{studio_body}
- \bibliography{exemplo} -> \bibliography{references}

## Mapa de metadados detectado (doc.yaml -> macro)

- `title` -> `\title{%s}`
- `author` -> `\author{%s}`
- `date` -> `\date{%s}`

## Trecho-exemplo removido do corpo (início)

```latex
\chapter{Primeiro capítulo}
Texto de exemplo \cite{exemplo2020}.
\begin{definicao}
Exemplo de definição.
\end{definicao}
\chapter{Segundo capítulo}
Texto de exemplo.
```

## Revise
- O corte do corpo começou e terminou no lugar certo?
- Algum comando de pré-texto (capa, folha de rosto, listas) ficou dentro do trecho removido?
- Faltou algum metadado obrigatório da classe no metadata_map?
Depois rode: python studio/scripts/mf_latex.py smoke studio-book
