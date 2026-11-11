# S06: Piloto real de documento LaTeX

**Depende de:** S05 · **Gate humano:** **SIM** (aprovação da qualidade)

## Preâmbulo
Siga o preâmbulo da X01. Use `/mf-doc` (skills **mf-doc-architect**, **mf-doc-writer**, **rep-reviewer**). Várias rodadas; uma unidade por rodada.

## Objetivo
Produzir um documento real com um template registrado na S02, fundamentado nas fichas da S04, e avaliar com o usuário.

## Tarefas
1. **Escolha** (pergunte): de preferência curto (3 a 8 páginas). Exemplos: um capítulo de apostila do KT_Aramis, uma seção de artigo, um relatório de disciplina, uma lista de exercícios em formato de texto.
2. **Bibliografia:** `sl_sources.py bib --out <job>/references.bib --only <SRCs usados>`.
3. **Execute `/mf-doc`:** estrutura aprovada, unidades com `pack` de fundamentação, lint, build, revisão (painel acadêmico calibrado ou `curso-kf`) e correções.
4. **Inspeção:** abra o PDF e confira com o usuário:
   - títulos e capa preenchidos;
   - citações e referências resolvidas;
   - definições literais das fontes nas caixas certas;
   - nenhuma linha estourando a margem.
5. **Avaliação (nota 1 a 5):** fidelidade às fontes, clareza, formatação, esforço de edição manual. Problemas viram ajustes em `writing_rules.md`, no template (scaffold) ou em `script_requests.md`, como na S03.

## Critérios de aceite
- [ ] PDF real gerado sem erros no `latex_report.md`.
- [ ] Revisão consolidada sem blockers (ou aceitos).
- [ ] Notas do usuário e ajustes registrados no LOG.

## Ao terminar
Resuma em até 150 palavras e **PARE**.
