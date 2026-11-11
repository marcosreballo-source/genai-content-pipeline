# Studio: produção de materiais, bibliografia oficial e revisão por personas

O Studio é uma camada **compartilhada**: a Knowledge Factory (cursos) e qualquer outro orquestrador (estudo, business, trabalho, gestão de imóveis...) o usam do mesmo jeito.

| Serviço | Prefixo | O que faz | Script |
|---|---|---|---|
| Material Factory | `mf-` | Apresentações (.pptx editável e Beamer) e documentos LaTeX a partir de templates | `mf_deck.py`, `mf_latex.py` |
| Source Library | `sl-` | Bibliografia oficial: trechos de 4 páginas, fichas fiéis, índice, cobertura e pedidos de bibliografia | `sl_sources.py` |
| Review Engine (REP) | `rep-` | Revisão particionada por persona x lente x fatia; consolidação; banco de perguntas; calibração com feedback real | `rep_review.py` |
| Piloto automático | `studio-` | Diz o próximo passo de qualquer job | `studio_next.py` |

## Como outro orquestrador usa o Studio
1. Cria um job numa pasta própria: `mf_deck.py new <pasta> --blueprint <id>` ou `mf_latex.py new <template> <pasta>`.
2. Preenche `brief.yaml`/`doc.yaml` com o que já sabe (público, objetivo, fontes `SRC-...`).
3. Chama `/mf-deck` ou `/mf-doc` apontando para a pasta e recebe de volta os arquivos em `<pasta>/build/` e a revisão em `<pasta>/review/`.

## Pastas
- `scripts/`: todos os scripts e os testes (`python studio/scripts/tests/run_tests.py`).
- `formats/`: format packs (deck, latex), blueprints, regras de escrita e o contrato para novos formatos.
- `kits/`: identidades visuais (cores, fontes, logo). `templates/`: templates pptx e LaTeX registrados.
- `sources/`: a biblioteca (ledger, trechos, fichas, índice).
- `review/`: lentes, personas e painéis.
- `agent_files/`: skills, workflows e rule a instalar na pasta de agentes do Antigravity.
- `implementation/`: deliveries de implantação, LOG e mapeamento.

Diagnóstico do ambiente: `python studio/scripts/studio_doctor.py`. Retomar qualquer trabalho: `python studio/scripts/studio_next.py <job>`.
