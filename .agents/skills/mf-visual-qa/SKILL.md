---
name: mf-visual-qa
description: Gera o arquivo final (pptx/Beamer), as prévias em PNG, executa os portões determinísticos de visão computacional e tipografia (visual_qa_gates.py), realiza a auditoria multimodal com canário óptico e corrige via spec/assets. Use quando studio_next indicar 'gerar o deck' ou 'resolver o QA'. Uso do Studio: acionar apenas em comandos /mf-*, /sl-*, /rep-*, /studio-* ou em jobs do Studio.
---
## Procedimento Obrigatório (Zero Passividade)
1. **Verificação SOTA (60 dias) e Provisionamento de Assets:**
   - Para cada biblioteca gráfica usada no script de assets do job, garanta que a revisão de estado da arte ($\le 60$ dias) e o ambiente estão ativos:
     ```powershell
     .\.venv\Scripts\python.exe studio/tools/visual_sota_auditor.py check --library <lib>
     .\.venv\Scripts\python.exe studio/tools/visual_env_provisioner.py --ensure <lib>
     ```
2. **Build e Prévia Padrão do Studio:**
   ```powershell
   .\.venv\Scripts\python.exe studio/scripts/mf_deck.py build <job>
   .\.venv\Scripts\python.exe studio/scripts/mf_deck.py preview <job>
   .\.venv\Scripts\python.exe studio/scripts/mf_deck.py qa <job>
   ```
   *(Se o job utilizar renderizador customizado de template institucional, execute o renderizador e o gerador de preview do job).*
3. **Execução do Portão Determinístico de Geometria, Tipografia e Visão Computacional (`visual_qa_gates.py`):**
   ```powershell
   .\.venv\Scripts\python.exe studio/tools/visual_qa_gates.py <job>
   ```
   - Se o comando retornar `Exit Code != 0`, **PARE e CORRIJA IMEDIATAMENTE** antes de prosseguir:
     - `DEAD_GRAY_BOX_DETECTED` / `EMPTY_PLACEHOLDER`: gere o diagrama/card correspondente no script de assets e vincule-o ao slide;
     - `RIGHT_DESERT_DETECTED` / `VERTICAL_CEMETERY_DETECTED`: adicione o diagrama complementar na coluna vazia ou reestruture em cards de largura total;
     - `MICRO_FONT` / `TITLE_TOO_SMALL` / `LINE_COLLISION`: ajuste os tamanhos de fonte, entrelinha ($1.15$–$1.35$) ou divida o conteúdo;
     - `LOW_CONTRAST`: corrija a cor da fonte ou do fundo para contraste WCAG $\ge 3.0:1$.
4. **Inspeção Visual Multimodal Auditável (Com Canário Óptico e Subagente):**
   - Emita obrigatoriamente no chat o aviso:
     `[INICIANDO INSPEÇÃO VISUAL MULTIMODAL: Lendo qa_challenge_sheet.png, contact_sheet.png e slides via visão computacional]`
   - Invoque um subagente revisor isolado (`invoke_subagent`) ou leia diretamente via `read_file` os arquivos `build/qa_challenge_sheet.png`, `build/contact_sheet.png` e os slides listados em `flagged_slides`.
   - Extraia visualmente o código de 6 caracteres (`CANARY`) desenhado no banner azul de `build/qa_challenge_sheet.png` e preencha `CANARY_VERIFIED` em `build/visual_audit_report.md`.
5. **Trava Criptográfica Final (`--verify-audit`):**
   ```powershell
   .\.venv\Scripts\python.exe studio/tools/visual_qa_gates.py <job> --verify-audit --canary <CODIGO_LIDO_DA_IMAGEM>
   ```
   - Só considere o QA concluído quando `--verify-audit` retornar `EXIT CODE 0`.

## Proibições Estritas
- **NUNCA** peça ao usuário para abrir o contact sheet ou caçar erros visuais por você.
- **NUNCA** deixe `Picture Placeholder` vazio ou bloco cinza opaco esperando que o usuário insira diagramas técnicos.
- **NUNCA** edite `studio/scripts/*.py` nem altere o `.pptx` manualmente.
