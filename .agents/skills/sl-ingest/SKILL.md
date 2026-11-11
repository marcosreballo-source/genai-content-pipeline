---
name: sl-ingest
description: Registra uma fonte na Source Library (livro, paper, documentação, site, vídeo/transcrição, slides de professor, lista de exercícios, norma, repositório) e a divide em trechos de 4 páginas (ou ~1500 palavras), ou importa os trechos já gerados pelo pipeline de triagem do usuário. Use em /sl-add ou quando houver pedido de bibliografia atendido. Uso do Studio: acionar apenas em comandos /mf-*, /sl-*, /rep-*, /studio-* ou em jobs do Studio.
---
## Procedimento
1. Identifique: tipo, título, autores (`"Sobrenome, Nome; ..."`), ano, editora ou site e autoridade (0 a 10; régua: 10 norma/documentação oficial, 8-9 livro-texto ou paper revisado, 6-7 material técnico reconhecido ou slides de professor da disciplina, 4-5 blog/vídeo, 0-3 sem autoria). Pergunte o que não souber.
2. Registre:
   `python studio/scripts/sl_sources.py add <arquivo|URL> --type <tipo> --title "..." --authors "..." --year AAAA --authority N`
   Arquivos grandes não são copiados (só referenciados); use `--copy` para materiais pequenos que podem mudar de lugar.
3. Divida:
   - **PDF**: `sl_sources.py chunk <SRC> --pages 4`. Se o script avisar "quase sem texto", o PDF é escaneado: use o pipeline de OCR do usuário (ou ocrmypdf) e importe.
   - **Site, transcrição de vídeo, notas**: salve o texto em .md/.txt (com timestamps, se for vídeo) e rode `sl_sources.py chunk <SRC> --text <arquivo> --words 1500`.
   - **Pipeline de triagem do usuário** (se a matriz de merge marcou INTEGRATE): rode o pipeline dele como sempre e depois `sl_sources.py import-chunks <SRC> --dir <pasta-de-saída-dele>`. Os arquivos dele não são alterados.
4. Informe quantos trechos há e estime as rodadas (1 ficha por rodada). Siga com a skill sl-extract (`studio_next.py --source <SRC>`).

## Proibições
- Registrar a mesma obra duas vezes (rode `sl_sources.py status` antes).
- Baixar material de fonte com restrição de uso sem avisar o usuário.
