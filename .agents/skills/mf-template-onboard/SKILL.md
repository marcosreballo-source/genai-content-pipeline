---
name: mf-template-onboard
description: Registra um template novo no Studio (PowerPoint .pptx/.potx institucional ou template LaTeX baixado: abnTeX2/USP, SBC, IEEE, ACM, LNCS, Beamer de instituição, classe de prova) e cria o kit de cores correspondente. Use em /mf-template-add ou quando o usuário fornecer um template. Uso do Studio: acionar apenas em comandos /mf-*, /sl-*, /rep-*, /studio-* ou em jobs do Studio.
---
## PowerPoint (.pptx ou .potx)
1. Coloque o arquivo em qualquer pasta e rode: `python studio/scripts/mf_deck.py inspect-template <arquivo> --id <id> --kit <id>`.
2. Leia `studio/templates/pptx/<id>/layouts.md` e confira o rascunho `template.yaml`:
   - cada arquétipo mapeado aponta para o layout certo e para os `idx` corretos;
   - `default` é um layout só com título (usado para gráficos, tabelas, processos...);
   - `content_box` cobre a área útil abaixo do título (em polegadas).
3. Crie `studio/kits/<id>.yaml` copiando `default.yaml` e trocando cores e fontes pelas da marca (peça o manual de marca ou extraia do template). Rode `mf_deck.py kit-check <id>`.
4. Teste: copie um job de exemplo, rode `mf_deck.py build <job> --template <id>` e `preview`, e confira o contact sheet.

## LaTeX (pasta baixada do Overleaf, CTAN, site do evento ou da instituição)
1. Baixe o template oficial e anote URL e licença. Não edite os arquivos baixados.
2. `python studio/scripts/mf_latex.py inspect <pasta> --id <id> --url <url> --license <licença>`
3. Leia `studio/templates/latex/<id>/scaffold_diff.md`. O corte do conteúdo-exemplo pegou só o corpo? Capa e pré-textuais continuam? Se não, ajuste à mão **só o arquivo em scaffold/**, mantendo os marcadores `\input{studio_meta}`, `\input{studio_body}` e `\input{studio_front_*}`.
4. Complete `metadata_map` no `template.yaml` com todos os campos que a classe exige (ex.: abnTeX2: titulo, autor, orientador, instituicao, local, data, preambulo, tipotrabalho).
5. Preencha `limits.pages_max` se o evento ou programa tiver limite.
6. `python studio/scripts/mf_latex.py smoke <id>`: os dois builds (original e scaffold) precisam passar. Se faltar pacote, rode `studio_doctor.py` e instale.
7. Para Beamer institucional: kind `beamer`; o tema é carregado pelo `preamble.tex` do template (campo `beamer_preamble`).

## Saída
Template registrado, kit criado (pptx) e o resultado do smoke ou do teste visual relatado ao usuário.
