# Kits visuais

Um kit define cores, fontes, tamanhos e logo usados pelo renderizador de slides (modo kit) e pelas partes desenhadas no modo template.
1. Copie `default.yaml` para `<id>.yaml` (ex.: `icmc-usp`, `eldorado`, `startup-x`, `imoveis`).
2. Troque cores (hex sem #), fontes instaladas na máquina de quem apresenta e logo (coloque em `kits/assets/`).
3. `python studio/scripts/mf_deck.py kit-check <id>` (verifica contraste).
