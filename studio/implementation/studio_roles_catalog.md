# Catálogo de papéis do Studio (para o mapeamento X01–X03)

Use com `python knowledge_factory/scripts/kf_inventory.py similar --query "<sinais>" --top 6`. O padrão é só uma sugestão; a decisão segue as regras da X03.

| ID | Papel | Nome-alvo | Sinais para busca | Padrão |
|---|---|---|---|---|
| X01 | Divisão de PDFs/livros em trechos e triagem | `sl-ingest` + seu pipeline | chunk, pdf, páginas, triagem, dividir livro, OCR | INTEGRATE (seu pipeline continua sendo usado) |
| X02 | Fichamento/resumo de fontes | `sl-extract` | resumo, fichamento, extrair conceitos, notas de leitura, transcrever | ABSORB se exclusivo de cursos; INTEGRATE se de outra frente |
| X03 | Bibliografia e cobertura | `sl-coverage` | bibliografia, referências, fontes, cobertura | CREATE |
| X04 | Produção de apresentações | `mf-deck-*` | slides, ppt, pptx, apresentação, deck, beamer, pitch, marp | SUPERSEDE (após piloto em cada frente) |
| X05 | Documentos LaTeX e templates | `mf-doc-*`, `mf-template-onboard` | latex, overleaf, apostila, relatório, artigo, tese, abnt, template | SUPERSEDE ou INTEGRATE |
| X06 | Revisão (REP antigo, revisores genéricos) | `rep-*` + lentes/personas | revisão, review, REP, banca, avaliador, crítica, feedback | ABSORB/MERGE (o REP antigo vira lentes e personas) |
| X07 | Orquestradores de área | `<área>-*` v2 | estudo, business, education, trabalho, eldorado, imóveis, gestão | UPLIFT (um por vez, delivery U01) |
| X08 | Itens da KF que produzem, auditam ou analisam fontes | `kf-*` (internos) | kf-slide, kf-workbook, kf-source, kf-*-auditor | ADAPT interno (S07, com autorização) |
| X09 | Futuros formatos (diagramas, notebooks, provas, plots, web, animação, roteiros) | `mf-<pack>` | mermaid, uml, plantuml, notebook, jupyter, prova, lista, gráfico, landing, manim, roteiro | REGISTRAR para a Parte 2/3 (não agir agora) |

As disposições CREATE, ABSORB, MERGE, INTEGRATE, ADAPT e ISOLATE seguem `knowledge_factory/implementation/MIGRATION_PROTOCOL.md`. SUPERSEDE e UPLIFT estão em `STUDIO_PROTOCOL_ADDENDUM.md`.
