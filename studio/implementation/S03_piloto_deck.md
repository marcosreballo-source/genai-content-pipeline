# S03: Piloto real de apresentação (GATE S1)

**Depende de:** S02 · **Gate humano:** **SIM** (o usuário julga a qualidade)

## Preâmbulo
Siga o preâmbulo da X01. Use `/mf-deck` do começo ao fim. Uma unidade por rodada: esta delivery dura várias rodadas. A cada rodada, rode `studio_next.py` e registre no LOG `S03 em andamento: <passo>`.

## Objetivo
Produzir uma apresentação **real** que o usuário vai usar, passando por todas as etapas, e medir a qualidade com ele.

## Tarefas
1. **Escolha do piloto** (pergunte): de preferência algo curto e próximo, com 8 a 15 slides. Exemplos: status de pesquisa do Eldorado, trabalho de disciplina, pitch. Anote o blueprint, o kit ou template e o painel.
2. **Execute `/mf-deck`:** brief, outline (aprovação do usuário), unidades, build, preview, QA, revisão pelo painel, correções e delta. Fontes técnicas: se o tema exigir e a biblioteca estiver vazia, use material do usuário em `assets/` e cite como URL ou arquivo; a Source Library completa entra na S04.
3. **Beamer** (se fizer sentido para o contexto, ex.: acadêmico): `mf_latex.py beamer <job>` e compare as duas versões com o usuário.
4. **Entrega:** `deck.pptx`, `deck.pdf`, `speaker_notes.md`, `review/qa_bank.md`.
5. **Avaliação com o usuário (GATE S1)**, perguntas objetivas:
   - Nota de 1 a 5 para: estrutura e narrativa, design, conteúdo, notas de fala, utilidade das perguntas previstas.
   - Quantas edições manuais ele precisou fazer no .pptx, e quais.
   - O que ficou pior do que a forma antiga de fazer slides.
6. **Ajustes sem mexer em script:** cada problema apontado vira ajuste em kit (`studio/kits/`), blueprint (`studio/formats/deck/blueprints/`), regras de escrita (`writing_rules.md`) ou persona/painel. Problema que **só** um script resolveria: registre em `studio/implementation/script_requests.md` (será tratado pelo Claude na próxima parte) e não altere o script.

## Critérios de aceite
- [ ] Deck real entregue, com revisão consolidada sem blockers (ou blockers aceitos pelo usuário).
- [ ] Notas do usuário registradas no LOG.
- [ ] Ajustes feitos em dados (kit, blueprint, regras) e pedidos de script registrados.
- [ ] GATE S1 registrado como aprovado ou "aprovado com ajustes".

## Ao terminar
Resuma em até 150 palavras (notas do usuário e ajustes) e **PARE**.
