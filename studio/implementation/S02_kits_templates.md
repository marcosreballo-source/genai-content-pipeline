# S02: Identidades visuais (kits) e templates institucionais

**Depende de:** S01 · **Gate humano:** não (o usuário fornece materiais)

## Preâmbulo
Siga o preâmbulo da X01. Use a rule `studio-core` e as skills **mf-template-onboard** e **mf-visual-qa**.

## Objetivo
Criar os kits visuais dos contextos do usuário e registrar pelo menos um template PowerPoint e um LaTeX reais. Assim, os materiais saem com a cara de cada lugar.

## Tarefas
1. **Levantamento** (uma pergunta ao usuário): para cada contexto abaixo, ele tem template oficial (.pptx/.potx ou LaTeX), manual de marca, logo ou cores preferidas?
   - USP/ICMC (disciplinas, defesas, simpósios)
   - Eldorado (status, negócios, rampagem)
   - startups e pitches (uma marca por empresa)
   - gestão de imóveis
   - cursos que ministra
2. **Kits:** para cada contexto com cores ou logo, crie `studio/kits/<id>.yaml` a partir de `default.yaml`. Logos vão em `studio/kits/assets/`; use versões claras em `logo_on_dark` quando houver. Rode `python studio/scripts/mf_deck.py kit-check <id>` e ajuste até não haver aviso de contraste.
   - Sem cores definidas: proponha 2 opções de paleta (primária, destaque, escuro) com contraste aprovado e deixe o usuário escolher.
   - Fontes: só as instaladas na máquina de quem vai apresentar (ex.: Calibri, Arial, Segoe UI; no Mac, Helvetica Neue).
3. **Template PowerPoint** (se houver, ex.: modelo corporativo do Eldorado): `/mf-template-add`. Gere o exemplo `studio/jobs/exemplo_deck` com `--template <id>`, rode o preview e mostre o contact sheet.
4. **Template LaTeX** (pergunte qual é mais útil agora; sugestões: modelo de dissertação/tese da USP baseado em abnTeX2, template SBC de artigos, IEEE conference, Beamer institucional): `/mf-template-add`. O smoke precisa passar.
5. **Registro:** atualize `studio/templates/README.md` (id, uso, origem, licença, data).

## Critérios de aceite
- [ ] Pelo menos 2 kits além do default, com kit-check sem avisos.
- [ ] Pelo menos 1 template LaTeX real registrado com smoke OK.
- [ ] Template PowerPoint registrado com prévia aprovada pelo usuário (se ele tiver um).
- [ ] Guard limpo.

## Ao terminar
Atualize o LOG, resuma em até 150 palavras e **PARE**.
