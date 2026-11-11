# Scaffold do template studio-article

Arquivo principal: `main.tex` · classe `article` · motor `pdflatex`

## Mudanças feitas na CÓPIA (scaffold/); o original/ está intacto

- inserido \input{studio_meta} antes de \begin{document}
- conteúdo do ambiente 'abstract' trocado por \input{studio_front_abstract}
- removido o conteúdo-exemplo do corpo (4 linhas) e inserido \input{studio_body}
- \bibliography{exemplo} -> \bibliography{references}

## Mapa de metadados detectado (doc.yaml -> macro)

- `title` -> `\title{%s}`
- `author` -> `\author{%s}`
- `date` -> `\date{%s}`

## Trecho-exemplo removido do corpo (início)

```latex
\section{Introdução}
Texto de exemplo com citação \cite{exemplo2020}.
\section{Conclusão}
Texto de exemplo.
```

## Revise
- O corte do corpo começou e terminou no lugar certo?
- Algum comando de pré-texto (capa, folha de rosto, listas) ficou dentro do trecho removido?
- Faltou algum metadado obrigatório da classe no metadata_map?
Depois rode: python studio/scripts/mf_latex.py smoke studio-article
