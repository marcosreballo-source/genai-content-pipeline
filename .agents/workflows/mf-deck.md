---
description: Cria ou continua uma apresentação de alta qualidade (pptx editável e/ou Beamer) com brief, outline aprovado, unidades curtas, prévia visual, QA e revisão por painel. Uso do Studio.
---
0. Ler `<AGENT_DIR>/rules/studio-core.md` e aplicá-la durante todo o comando.
1. Se o usuário indicou um job existente, pule para o passo 4. Senão, defina a pasta do job: `studio/jobs/<AAAA-MM-DD>_<slug>/`, ou a pasta indicada por outro orquestrador.
2. Skill **mf-brief**: escolha o blueprint e rode `python studio/scripts/mf_deck.py new <job> --blueprint <id> [--kit <kit> | --template <id>]`; depois preencha `brief.yaml`.
3. Skill **mf-deck-architect**: escreva o outline, rode `mf_deck.py plan`, mostre ao usuário e PARE até ele aprovar (`outline.approved`).
4. Rode `python studio/scripts/studio_next.py <job>` e execute **apenas** o passo indicado, com a skill indicada:
   - escrever unidade: **mf-deck-writer** (uma unidade por rodada);
   - gerar, prévia ou QA: **mf-visual-qa**;
   - revisão: **rep-reviewer** (painel do brief ou o padrão do blueprint);
   - corrigir: **mf-deck-writer** em modo correção.
5. Ao fim de cada passo, diga ao usuário em até 5 linhas o que foi feito e qual é o próximo passo. Se o usuário pedir "continue", volte ao passo 4.
6. Quando `studio_next` disser PRONTO: rode `mf_deck.py notes <job>` e entregue `build/deck.pptx`, `build/deck.pdf` (e `deck_beamer.pdf` se houver), `build/speaker_notes.md` e `review/qa_bank.md`.
