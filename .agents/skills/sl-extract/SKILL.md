---
name: sl-extract
description: Lê UM trecho de uma fonte e escreve sua ficha fiel (cards/Cxxxx.yaml), com transcrição literal de definições, teoremas, fórmulas, algoritmos e tabelas pequenas, e paráfrase curta do resto, sem resumir demais. Use quando studio_next --source indicar 'fichar o trecho'. Uso do Studio: acionar apenas em comandos /mf-*, /sl-*, /rep-*, /studio-* ou em jobs do Studio.
---
## Entradas
- Saída de `python studio/scripts/sl_sources.py next <SRC>`: caminhos do trecho (.txt e .pdf) e esqueleto da ficha.
- Leia o .txt. Se houver fórmulas, tabelas ou figuras mal extraídas, leia também as páginas do .pdf do trecho.
- Se existir, leia `studio/sources/EXTRACTION_NOTES.md` (ajustes combinados com o usuário) antes de começar.

## Regras de fidelidade (o coração da Source Library)
1. **Todo conceito nomeado entra em `concepts`**, com página (`loc`). Nunca omita um conceito porque "parece menor".
2. **Transcreva literalmente** em `items`: definições, teoremas, lemas, corolários, proposições, fórmulas numeradas, algoritmos/pseudocódigo, tabelas pequenas, enunciados de exemplos e exercícios. Use o rótulo da fonte (`Definição 2.3`, `Eq. (4.1)`).
3. Fórmulas em LaTeX dentro de `text` quando a extração vier quebrada (confira no PDF).
4. **Paráfrase só para explicação corrida**, em `key_points`: frases curtas, cada uma terminando com `(p. N)`.
5. `summary` tem 2 a 4 frases e não substitui nada acima.
6. Trecho sem conteúdo útil (índice, página em branco, propaganda): `status: skipped` + `skip_reason`.
7. Se a ficha passar de 1200 palavras, divida em `Cxxxx.a.yaml` e `Cxxxx.b.yaml` (mesmo cabeçalho, conteúdo dividido em ordem).
8. Ilegível ou ambíguo: registre em `open_questions`; não adivinhe.

## Procedimento
1. Escreva a ficha em `studio/sources/<SRC>/cards/<Cxxxx>.yaml`.
2. `python studio/scripts/sl_sources.py validate <SRC> --chunk <Cxxxx>`:
   - "supersumarização": faltam itens transcritos; volte ao texto;
   - "transcrição não bate": você parafraseou um item literal; corrija ou explique em `open_questions`.
3. Pare. Uma ficha por rodada. Ao terminar a fonte: `sl_sources.py validate <SRC>` e `sl_sources.py index`.
