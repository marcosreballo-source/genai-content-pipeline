# X02: Mapeamento do que já existe contra os papéis do Studio

**Depende de:** X01 · **Gate humano:** não (há perguntas ao usuário)

## Preâmbulo
Siga o preâmbulo da X01 (LOG, só as entradas, ≤ 1200 palavras por resposta, nada de outras frentes editado, guard no fim). Esta delivery é **somente leitura** fora de `studio/implementation/mapping/`. Orçamento: leia o arquivo completo de no máximo 6 itens por rodada; se houver mais, marque `X02 PARTIAL (rodada N)` no LOG com os pendentes e pare.

## Objetivo
Saber, com evidência, quais skills, workflows, rules e scripts do workspace já fazem (bem ou mal) o trabalho de cada papel do Studio, e como eles estão ligados às frentes. Base factual para a X03.

## Entradas
- `studio/implementation/studio_roles_catalog.md`
- `studio/implementation/mapping/inventory_raw.md` (X01) e `knowledge_factory/implementation/mapping/fronts.md` (M02)
- Saídas de `kf_inventory.py show <ID>` e `similar --inv studio/implementation/mapping`

## Tarefas
1. **Itens novos desde a M02:** compare o inventário novo com `fronts.md`. Para os itens que não estavam lá, proponha a frente e peça confirmação ao usuário numa única pergunta.
2. **Pergunta direta ao usuário** (uma mensagem, 5 itens):
   - (a) Qual workflow, skill ou script faz a **triagem/divisão de PDFs em trechos de 4 páginas**, e onde ele grava a saída?
   - (b) Onde está o **orquestrador antigo com o REP** (revisão particionada)?
   - (c) Quais skills ou workflows você usa hoje para **slides** em cada frente (disciplinas, Eldorado, pitches, imóveis, cursos)?
   - (d) Existe algo para **LaTeX/Overleaf**, apostilas ou relatórios?
   - (e) Quais são os workflows de cada **área** (estudo, business, education, trabalho, gestão de imóveis)?
3. **Candidatos por papel:** para X01–X09 rode `python knowledge_factory/scripts/kf_inventory.py similar --inv studio/implementation/mapping --query "<sinais>" --top 6`. Score ≥ 0.20 ou item indicado pelo usuário = candidato.
4. **Ficha de cada candidato** (até 90 palavras) em `studio/implementation/mapping/studio_overlap.md`:
   ```yaml
   - item: I-034 slide-maker
     fronts: [F1, F5, F7-eldorado]
     roles: [X04]
     does: "gera pptx a partir de tópicos"
     inputs_outputs: "lê <arquivo>; grava <pasta>/<nome>.pptx"
     quality_notes: "sem template, sem prévia, sem fonte"
     reusable: "boas regras de tom; checklist de tempo"
     dependents: [".agents/workflows/apresentacao.md"]
     suggested: SUPERSEDE
   ```
5. **Análises especiais** (seções próprias no mesmo arquivo):
   - **REP antigo:** tabela `Partição/cobrança do REP | Lente do Studio equivalente | Precisa de lente nova?`. Lentes do Studio: `studio/review/lenses/*.yaml`, só os nomes.
   - **Pipeline de triagem:** formato da saída (pasta, nomes dos arquivos, .pdf/.txt/.md, páginas por trecho). É compatível com `sl_sources.py import-chunks <SRC> --dir <pasta>`? O script lê .pdf/.txt/.md e infere páginas por nomes como `p001-004`; se o padrão for outro, descreva-o.
   - **Áreas:** para cada área, os workflows e os materiais que produzem (slides, documentos, outros) e uma nota de 1 a 5 sobre o quanto se beneficiam do Studio. Isso define a ordem do UPLIFT.
6. **Consolidação** ao fim do arquivo:
   - papéis sem candidato (CREATE);
   - itens compartilhados por várias frentes (candidatos a SUPERSEDE);
   - itens exclusivos de cursos (ABSORB/MERGE);
   - itens que alimentam o Studio sem serem substituídos (INTEGRATE);
   - dúvidas para o usuário.

## Critérios de aceite
- [ ] Respostas (a)–(e) registradas.
- [ ] Ficha de todos os candidatos, ou PARTIAL com os pendentes listados.
- [ ] Seções REP, triagem e áreas preenchidas.
- [ ] Guard limpo (nada alterado fora de `studio/implementation/mapping/`).

## Ao terminar
Atualize o LOG, resuma em até 180 palavras e **PARE**. Não decida o merge.
