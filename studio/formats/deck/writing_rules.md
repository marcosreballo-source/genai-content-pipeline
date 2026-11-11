# Regras de escrita de slides (siga ao preencher spec/Uxx.yaml)

Estas regras valem para qualquer deck do Studio. Os limites de campo estão em `archetypes.md`. A estrutura do deck vem do blueprint (`blueprints/<id>.yaml`).

## 1. Título-mensagem
- O título de cada slide é **a conclusão** do slide, numa frase com verbo. Ruim: "Resultados". Bom: "O modelo supera o baseline em todas as classes de falha".
- No máximo 90 caracteres. Teste: lendo só os títulos em sequência, a história inteira precisa fazer sentido.
- A mensagem do outline (`message`) é o rascunho do título; refine-a, mas não mude o sentido sem atualizar o outline.

## 2. Um slide, uma ideia
Se precisar de "e também", divida o slide. Mais slides leves são melhores que poucos slides densos.

## 3. Arquétipo pela intenção

| Quero... | Use |
|---|---|
| afirmar uma tese ou provocar | `statement` |
| mostrar um número que conta a história | `big_number` (1) ou `kpis` (2 a 4) |
| comparar valores | `chart` column/bar |
| mostrar evolução no tempo | `chart` line ou `timeline` (marcos) |
| mostrar composição (≤ 5 partes) | `chart` pie/doughnut ou stacked_column |
| explicar etapas de um método | `process` ou `diagram` |
| contrastar duas coisas | `two_column` |
| recomendar entre opções | `comparison` com `highlight` |
| dados exatos que serão consultados | `table` (≤ 6 x 7) |
| prova social, voz do cliente ou do usuário | `quote` |
| explicar código ou fórmula | `code` / `equation` |
| listar pontos que não cabem nos acima | `bullets` (último recurso) |

Não use 3 slides de `bullets` seguidos. Alterne arquétipos para manter o ritmo.

## 4. Tópicos (bullets)
- No máximo 6, idealmente 3 a 4. Cada um com ≤ 12 palavras; sem ponto final.
- Paralelos: todos começam do mesmo jeito (verbo, ou substantivo forte).
- Sub-tópicos só quando acrescentam evidência (máx. 3).
- `takeaway`: a frase que o público deve lembrar. Use em slides decisivos.

## 5. Números e dados
- **Nunca invente número, data, nome ou citação.** Se o dado não existe nas fontes ou no brief, escreva `[[PENDENTE: descrição do dado]]`. O QA final bloqueia até alguém fornecer.
- Todo número tem comparação ("contra o quê?"), unidade e fonte (`source` no gráfico/tabela ou `sources` no slide).
- Gráficos: destaque a categoria que importa (`highlight`) e escreva no `takeaway` a conclusão, não a descrição.
- Use o formato numérico brasileiro em textos (1.234,5; 12%); em `chart.values` use números puros.

## 6. Fundamentação
- Conteúdo técnico vem do pacote de fundamentação (`sl_sources.py pack`) ou do material do usuário, nunca da memória.
- Cada slide com afirmação factual leva `sources: [SRC-x#C0003]` (ou `S-01`, ou URL).
- Definições: use a formulação da fonte (pode encurtar sem mudar o sentido).

## 7. Notas de fala (`notes`)
- Obrigatórias quando o blueprint ou o brief exigem (defesas, pitches, aulas, simpósios).
- 60 a 150 palavras: o que dizer além do slide, o exemplo a contar, a transição para o próximo slide.
- Não repita o texto do slide. A fala inteira deve caber na duração (130 palavras/minuto, conferido por `mf_deck.py notes`).

## 8. Linguagem por público
- Gestores e clientes: impacto (R$, tempo, risco), zero jargão, decisão explícita.
- Banca, journal e simpósio: precisão, terminologia da área, limitações declaradas.
- Iniciantes: defina antes de usar; um exemplo por conceito.
- Moradores: frases curtas, tom acolhedor, nada jurídico; regras sempre do regimento ou do perfil do imóvel.

## 9. Imagens e diagramas
- Prioridade: material do usuário > figura da fonte (com crédito) > documentação oficial > visual gerado.
- Mermaid: no máximo 7 nós e rótulos curtos; use `flowchart LR` para até 4 nós em linha, senão `flowchart TB`.
- Coloque arquivos em `assets/` e referencie pelo nome.

## 10. Antes de entregar a unidade
1. `python studio/scripts/mf_deck.py validate <job> --unit Uxx` sem erros.
2. A unidade inteira tem ≤ 1200 palavras (o validate confere).
3. Nenhum `[[PENDENTE]]` esquecido sem registro em `pending.md` do job.
