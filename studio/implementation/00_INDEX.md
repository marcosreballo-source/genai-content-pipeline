# Studio, Parte 1: ordem de envio ao Gemini

Pré-requisito: a Knowledge Factory instalada (M01 a D18 concluídas).

## Instalação do pacote
Extraia o zip na **raiz do workspace**. Aparece a pasta `studio/` ao lado de `knowledge_factory/`. Extrair não altera nada da pasta de agentes; a instalação das skills acontece na S01.

## Como enviar cada delivery
- Uma conversa nova por delivery, com o prompt:
  ```
  Leia studio/implementation/<ARQUIVO>.md e execute exatamente o que está nele. Não execute nada de outra delivery.
  ```
- Responda às perguntas na mesma conversa. Avance só quando o LOG (`studio/implementation/LOG.md`) marcar DONE.
- As deliveries S03 a S06 e a U01 duram várias rodadas: para continuar, diga "continue a S03 a partir do LOG".

| # | Arquivo | O que acontece | Você faz |
|---|---|---|---|
| 1 | `X01_snapshot_inventario.md` | testes, **snapshot para o Claude**, inventário | anexa o .zip do snapshot na conversa com o Claude (para o manual) |
| 2 | `X02_mapeamento.md` | o que já existe e cobre o Studio (triagem, REP, slides, áreas) | responde 5 perguntas |
| 3 | `X03_plano_merge.md` | decisões de merge | **aprova a matriz (GATE X)** |
| 4 | `S01_instalacao.md` | ferramentas, skills e **primeiro .pptx/PDF real** | autoriza instalações; abre os exemplos |
| 5 | `S02_kits_templates.md` | identidades visuais e templates (pptx, LaTeX) | fornece templates, logos, cores |
| 6 | `S03_piloto_deck.md` | apresentação real do começo ao fim | **dá notas (GATE S1)** |
| 7 | `S04_fontes.md` | sua triagem de PDFs ligada à bibliografia; aviso de material faltante | escolhe um livro real; confere as fichas |
| 8 | `S05_revisao_rep.md` | REP antigo absorvido; painéis calibrados com rubricas reais | fornece enunciado, rubrica ou edital |
| 9 | `S06_piloto_documento.md` | documento LaTeX real | **dá notas** |
| 10 | `S07_integracao_kf.md` | cursos da KF saem em .pptx/PDF, com gate de bibliografia | **autoriza mudanças nos kf-*** |
| 11 | `S08_pilotos_cutover.md` | pilotos por frente; substituição das skills antigas de slides | **veredito por frente; GATE FINAL** |
| 12+ | `U01_uplift_area.md` | upgrade de uma área por vez | aprova desenho, piloto e cutover |

## Uso no dia a dia (depois da S01)
- Apresentação: `/mf-deck`. Documento: `/mf-doc`. Fonte nova: `/sl-add`. O que falta de bibliografia: `/sl-coverage`. Revisão: `/rep-review`. Template novo: `/mf-template-add`.
- Parou no meio? `/studio-next`: ele diz e executa só o próximo passo. Repita "continue" até aparecer PRONTO.

## Se algo sair do trilho
- Script com erro: o Gemini não deve reescrevê-lo. Copie o erro e traga para o Claude (vale também para `script_requests.md`).
- Guard acusou mudança em outra frente: se foi você, "pode aceitar"; se foi o Gemini, peça para reverter (`git checkout kf-baseline -- <caminho>` ou o backup).
