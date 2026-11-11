# Regras de escrita de fragmentos LaTeX (siga ao escrever content/sections/Sxx.pN.tex)

Vale para apostilas, livros, listas, artigos, relatórios, teses e capítulos feitos com `mf_latex.py`.

## 1. O que um fragmento pode conter
- Só conteúdo: parágrafos, `\subsection`, `\subsubsection`, listas, figuras, tabelas, equações, código e citações.
- **Não** escreva `\chapter`/`\section` da própria seção: o build gera o título a partir do `doc.yaml`.
- Proibido: `\documentclass`, `\usepackage`, `\begin{document}`, `\newcommand`, `\renewcommand`, `\def`, `\include`, `\maketitle`, `\tableofcontents`, `\bibliography`. Se precisar de um pacote ou comando novo, registre o pedido no `doc.yaml` (`needs:`) e pare.
- Use os ambientes que o template oferece (veja `scaffold_diff.md` e o preâmbulo). No `studio-book`: `definicao`, `exemplo`, `atencao`.

## 2. Escape e matemática
- Escreva `\%`, `\&`, `\#`, `\_` no texto. Um `%` sem barra transforma o resto da linha em comentário (o lint acusa).
- Matemática inline em `$...$`; equações numeradas em `\begin{equation}...\end{equation}` com `\label{eq:Sxx-nome}`.
- Dentro de `lstlisting`, use só ASCII e os acentos do português (o lint acusa outros símbolos).

## 3. Citações, figuras e referências cruzadas
- `\cite{chave}` somente com chaves que existem no `references.bib` do job (gere com `sl_sources.py bib --out <job>/references.bib`).
- Figuras em `assets/`:
  ```latex
  \begin{figure}[htbp]\centering
    \includegraphics[width=0.8\linewidth]{assets/curva.png}
    \caption{Legenda que diz a conclusão. Fonte: \cite{chave}.}
    \label{fig:S02-curva}
  \end{figure}
  ```
- Rótulos levam o id da seção: `fig:S02-...`, `tab:S02-...`, `eq:S02-...`. Para citar outra seção: `\ref{sec:S03}`.

## 4. Fidelidade às fontes
- Definições, teoremas e fórmulas vêm do pacote de fundamentação (`sl_sources.py pack`), copiados sem mudar o sentido e com `\cite`.
- Explicações, exemplos e transições podem ser autorais, mas sem afirmar fatos que as fontes não sustentam.
- Dado ausente: `[[PENDENTE: o que falta]]`. O build final bloqueia enquanto houver pendências.

## 5. Estilo
- Português claro e acadêmico. Uma ideia por parágrafo (3 a 6 frases).
- Defina cada termo antes do primeiro uso, respeitando a ordem dos pré-requisitos do Knowledge Graph quando houver.
- Didático (apostila/livro): conceito → exemplo → atenção/erro comum → exercício. Artigo/tese: afirmação → evidência → limite.

## 6. Tamanho
- Mire na `target_words` da unidade (±20%), sem passar de 1200 palavras.
- Se não couber, pare num ponto natural e avise. O `plan` pode ganhar mais uma parte (aumente `target_words` da seção).

## 7. Antes de entregar a unidade
`python studio/scripts/mf_latex.py lint <job> --unit Sxx.pN` sem erros. Ao final de todas as unidades, rode `build` e leia `build/latex_report.md`.
