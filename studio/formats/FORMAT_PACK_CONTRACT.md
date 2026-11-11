# Contrato de "format pack" (como o Studio produz qualquer tipo de material)

Todo formato segue o mesmo ciclo, para que o agente (com resposta curta) nunca precise "inventar" a forma:

```
brief -> plano (unidades pequenas) -> unidade escrita em SPEC (YAML/fragmento) -> validação por script
      -> build determinístico com template/kit -> prévia (PNG/PDF) -> QA automático + visual -> revisão por painel (rep_review)
```

## O que um pack precisa ter (`studio/formats/<pack>/`)
1. `pack.yaml`: comandos, arquivos do job, regra de unidade, lentes de revisão padrão, dependências.
2. Esquema da spec definido **no script** (fonte única) e documentação gerada a partir dele (ex.: `archetypes.md`).
3. `writing_rules.md`: as regras de qualidade que o agente segue ao escrever cada unidade (≤ 1 página).
4. Renderizador determinístico: o agente escreve conteúdo; o script decide layout, fontes, cores e numeração.
5. Validação com mensagens que apontam o campo exato (`U02/SL-07.bullets[3]`), incluindo o limite de 1200 palavras por unidade.
6. Prévia visual (PNG/PDF) e um `qa` que junta validação, ajuste de texto e checklist visual.
7. Blueprints ou modelos por contexto de uso (pitch, defesa, aula...), quando o formato tiver estrutura narrativa.
8. Exemplo completo testado em `scripts/tests/`.

## Packs prontos (Parte 1)
| Pack | Saídas |
|---|---|
| `deck` | .pptx editável (kit próprio ou template corporativo), Beamer PDF, prévias, roteiro de fala |
| `latex-doc` | PDF de qualquer template LaTeX registrado (apostila, livro, artigo, tese, relatório, manual) |

## Packs planejados
| Parte | Pack | Formatos | Motor |
|---|---|---|---|
| 2 | `assessment` | provas, listas, simulados, gabaritos, Moodle XML | exam.cls + YAML de questões |
| 2 | `diagram` | fluxograma, UML, mapa mental, kanban, organograma, arquitetura | Mermaid, PlantUML, Graphviz |
| 2 | `sci-figure` | ciclo de Carnot, circuitos (circuitikz), circuitos quânticos (quantikz/Qiskit), arquiteturas de redes | TikZ, matplotlib, qiskit |
| 2 | `plot` | gráficos de negócio, resultados de ML (curvas, matriz de confusão, ROC) | matplotlib/plotly + CSV |
| 2 | `notebook` | Jupyter didático e de replicação | nbformat + execução e checagem (nbclient) |
| 3 | `text` | resumos, posts de redes sociais, artigos de blog (Medium) | Markdown + pandoc |
| 3 | `script` | roteiros de vídeo-aula, explicação de código, defesa, pitch falado | spec de cenas (tempo, fala, visual) |
| 3 | `animation` | animações de física/matemática, CSS/JS | Manim, HTML/canvas |
| 3 | `web` | landing page, one-page, protótipo de SaaS, visualização interativa | HTML + Tailwind por seções |
| 3 | `mockup` | telas de app | HTML; importação no Figma por plugin (o Figma não gera telas sem API/plugin) |
