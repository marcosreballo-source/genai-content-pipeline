# Protocolo de Levantamento Bibliográfico — [research_id]

**Versão**: v[N] | **Data**: [AAAA-MM-DD] | **Status**: rascunho / aprovado pelo usuário / validado com orientador(a)

## 1. Objetivo do levantamento
[1 parágrafo: o que se quer mapear e para qual projeto]

## 2. Questões de pesquisa
| ID | Questão | Tipo (exploratória/comparativa) | Origem (documento e página que a motiva) |
|----|---------|---------------------------------|-------------------------------------------|
| QP1 | | | |
| QP2 | | | |

## 3. Escopo (PICo adaptado para Computação)
- **População/objeto**: [ex.: grafos de conhecimento / grafos semânticos]
- **Interesse/intervenção**: [ex.: construção, modelagem, resolução de entidades, aprendizado de representação]
- **Contexto**: [ex.: domínios heterogêneos, ruidosos, sensíveis — segurança pública, saúde]

## 4. Fontes de busca
| Fonte | Tipo | Quem executa | Formato de exportação |
|-------|------|--------------|-----------------------|
| DBLP | indexador CS (aberto) | agente (API) | JSON/BibTeX |
| OpenAlex | indexador aberto | agente (API) | JSON |
| IEEE Xplore | base de editora | usuário (VPN USP) | CSV |
| ACM DL | base de editora | usuário (VPN USP) | BibTeX |
| Scopus | indexador | usuário (CAPES) | CSV/RIS |
| Google Scholar | buscador | usuário (manual) | lista manual |
| Consensus / Scholar Labs | busca semântica | usuário (manual) | lista manual |

## 5. Strings de busca
| Fonte | String exata | Campos | Data da execução |
|-------|--------------|--------|------------------|
| Geral | ("knowledge graph" OR "semantic graph") AND (...) | título/resumo/palavras-chave | |

## 6. Critérios
**Período**: [ex.: 2015–2026] | **Idiomas**: [en, pt]

| Inclusão | Exclusão |
|----------|----------|
| CI1: | CE1: |
| CI2: | CE2: |

## 7. Snowballing
- **Backward**: referências dos trabalhos semente com relevância Alta.
- **Forward**: trabalhos que citam as sementes (via OpenAlex `cites:`), limitados a [N] por semente.
- **Rodadas máximas**: [N] (registrar em `workflow_state.json`).

## 8. Registro
Toda execução de busca é registrada em `search_log.md` (fonte, string, data, nº de resultados, nº após deduplicação, nº após triagem, nº incluídos).

