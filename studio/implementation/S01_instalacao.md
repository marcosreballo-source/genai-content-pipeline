# S01: Instalação do Studio, ferramentas e primeiro material visível

**Depende de:** X03 (GATE X aprovado) · **Gate humano:** não (pede permissão para instalar programas)

## Preâmbulo
Siga o preâmbulo da X01. Leia `studio/implementation/mapping/studio_matrix.md` (nomes-alvo) e a linha S01 de `studio_adjustments.md`.

## Objetivo
Deixar as ferramentas prontas, instalar as skills, workflows e a rule do Studio na pasta de agentes (só itens novos, com prefixos `mf-`, `sl-`, `rep-`, `studio-`) e gerar os primeiros arquivos reais (.pptx, PDF) para o usuário ver.

## Tarefas
1. **Diagnóstico:** `python studio/scripts/studio_doctor.py`. Mostre ao usuário o que falta e os comandos sugeridos para o sistema dele. **Peça permissão** antes de instalar programas no computador (LibreOffice, TeX Live ou MiKTeX, poppler, mermaid-cli). Pacotes Python (`pip install ...`) podem ser instalados direto. Rode o doctor de novo até "essenciais OK".
   - LaTeX: recomende a distribuição completa (TeX Live ou MiKTeX com instalação automática de pacotes), que traz `babel-portuges`, `abntex2`, `biblatex` e `metropolis`.
   - Mermaid: se o `mmdc` não achar o Chrome, defina a variável de ambiente `STUDIO_CHROME` com o caminho do Chrome ou Chromium.
2. **Testes completos:** `python studio/scripts/tests/run_tests.py` (sem `--fast`). Todos devem passar. Teste pulado por falta de programa: registre no LOG.
3. **Instalar arquivos de agente** (copiar, não mover), com os nomes da matriz (padrão = mesmo nome):
   - `studio/agent_files/rules/studio-core.md` → `<AGENT_DIR>/rules/studio-core.md`
   - `studio/agent_files/workflows/*.md` → `<AGENT_DIR>/workflows/`
   - `studio/agent_files/skills/*/` → `<AGENT_DIR>/skills/`
   Se a matriz renomeou algum item, ajuste o `name:` no front-matter e as menções nos workflows **copiados** (nunca nos originais em `studio/agent_files/`).
4. **Rule:** confira no painel *Customizations > Rules* que `studio-core` está em **Model Decision** (ou Glob `studio/**`), **nunca Always On**. Peça ao usuário para reiniciar o Antigravity e confirmar que `/mf-deck`, `/mf-doc`, `/sl-add`, `/sl-coverage`, `/rep-review`, `/mf-template-add` e `/studio-next` aparecem.
5. **Guard:** `python knowledge_factory/scripts/kf_guard.py check --strict`. Tudo que você criou na pasta de agentes deve estar no namespace (X01).
6. **Primeiro material visível:**
   ```
   cp -r studio/examples/deck_todos_arquetipos studio/jobs/exemplo_deck
   python studio/scripts/mf_deck.py plan studio/jobs/exemplo_deck
   python studio/scripts/mf_deck.py build studio/jobs/exemplo_deck
   python studio/scripts/mf_deck.py preview studio/jobs/exemplo_deck
   python studio/scripts/mf_latex.py beamer studio/jobs/exemplo_deck
   cp -r studio/examples/doc_apostila_grafos studio/jobs/exemplo_doc
   python studio/scripts/mf_latex.py plan studio/jobs/exemplo_doc
   python studio/scripts/mf_latex.py build studio/jobs/exemplo_doc
   ```
   (No Windows sem `cp`, copie as pastas pelo Python ou pelo explorador.)
   Mostre ao usuário onde estão `build/deck.pptx`, `build/contact_sheet.png`, `build/deck_beamer.pdf` e `exemplo_doc/build/document.pdf`, e peça que abra o .pptx no PowerPoint para conferir a edição. Registre a impressão dele no LOG.

## Critérios de aceite
- [ ] Doctor com essenciais OK; testes completos passando (ou pulos justificados).
- [ ] Arquivos de agente instalados; rule fora de Always On; comandos visíveis após reiniciar.
- [ ] Guard `--strict` limpo.
- [ ] Exemplos gerados e abertos pelo usuário.

## Ao terminar
Atualize o LOG, resuma em até 150 palavras e **PARE**.
