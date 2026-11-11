---
name: mf-brief
description: Levanta o brief de um material (apresentação ou documento) com no máximo 6 perguntas e escolhe blueprint, estilo e painel de revisão. Use no início de /mf-deck ou /mf-doc, ou quando brief.yaml/doc.yaml estiver incompleto. Uso do Studio: acionar apenas em comandos /mf-*, /sl-*, /rep-*, /studio-* ou em jobs do Studio.
---
## Entradas
- Pedido do usuário e materiais citados por ele.
- `studio/formats/deck/blueprints/*.yaml` (só os campos `id`, `name`, `contexts`), `studio/kits/*.yaml`, `studio/templates/`, `studio/review/panels/*.yaml` (só `id` e `name`).

## Saída
- `<job>/brief.yaml` (decks) ou os campos de topo de `<job>/doc.yaml` (documentos).

## Procedimento
1. Extraia do pedido tudo o que já foi dito. Não pergunte o que já está claro.
2. Escolha o blueprint pelo contexto:
   - pitch de competição: `pitch-competition`
   - captação: `investor-pitch`
   - venda/proposta: `client-pitch`
   - trabalho de disciplina: `class-presentation`
   - status de pesquisa: `research-update`
   - resultados para negócios: `business-results`
   - rampagem/oficina: `training-ramp`
   - aula de curso: `course-lecture`
   - manual de imóvel: `property-manual`
   - paper em simpósio: `symposium-talk`
   - defesa: `thesis-defense`
3. Faça no máximo 6 perguntas, todas numa mensagem, priorizando: público, objetivo (o que deve acontecer depois), duração ou tamanho, restrições externas (edital, template, limite), fontes disponíveis e estilo (kit ou template institucional).
4. Estilo: se houver template institucional registrado (`studio/templates/pptx/<id>`), use `style: {template: <id>}`; senão `style: {kit: <id>}` (padrão `default`).
5. Painel: o `panel_default` do blueprint, salvo pedido diferente.
6. Preencha o arquivo. Campos sem resposta ficam vazios e são listados ao usuário como pendentes.

## Proibições
- Não começar o outline antes de o brief ter público, objetivo e duração.
- Não inventar dados do evento, da banca ou do cliente.
