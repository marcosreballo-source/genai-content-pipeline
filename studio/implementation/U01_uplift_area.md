# U01: Upgrade de um orquestrador de área para o padrão do Studio (repetir por área)

**Depende de:** S08 · **Gate humano:** **SIM** (aprovação do piloto e do cutover) · **Uso:** reenvie esta delivery uma vez para cada área, na ordem da X03 (estudo, business, education, trabalho, gestão de imóveis).

## Preâmbulo
Siga o preâmbulo da X01 e o `STUDIO_PROTOCOL_ADDENDUM.md` (UPLIFT). Diga no início qual área está sendo tratada e registre `U01-<área>` no LOG.

## O padrão (o que cada área passa a ter)
```
pedido -> brief da área (perguntas mínimas)
       -> artefato de especificação da área (ex.: estudo: mapa de tópicos com fontes; business: tese e números;
          trabalho: plano/status; imóveis: perfil do imóvel + regimento)
       -> bibliografia/insumos na Source Library (pedidos quando faltar)
       -> produção pelo Studio (/mf-deck, /mf-doc; futuros packs)
       -> revisão pelo painel da área (/rep-review)
       -> pacote final + calibração depois do uso real
```

## Tarefas
1. **Retrato da área:** liste os workflows e skills da área (fichas da X02), o que cada um produz e os pontos fracos que o usuário vê (pergunte: "o que mais te incomoda no resultado hoje?").
2. **Desenho v2** (mostre e peça aprovação antes de criar):
   - `/<área>-<tarefa>` (ex.: `/estudo-resumo`, `/biz-pitch`, `/eldorado-status`, `/imovel-manual`): passos numerados que chamam o Studio;
   - a skill de especificação da área (`<área>-spec`), que gera o artefato da área com front-matter e `[[PENDENTE]]` para lacunas;
   - o painel da área (de `studio/review/panels/` ou novo, via **rep-panel**);
   - o blueprint, se faltar um adequado (`studio/formats/deck/blueprints/<id>.yaml`, mesmo formato dos existentes).
   Reaproveite o que funciona nos workflows antigos (seção "Herdado de").
3. **Criação lado a lado:** crie os itens v2 com prefixo da área. Os antigos ficam intactos. Estenda `kf_namespace.txt` com o prefixo da área (ex.: `*/workflows/estudo-*.md`).
4. **Piloto real** da área do início ao fim e veredito do usuário (melhor / igual / pior).
5. **Cutover** (se melhor ou igual, item a item): alias com o nome antigo, backup e arquivamento, `dangling`, guard.
6. **Registro:** `studio/implementation/uplift_<área>.md` com o desenho, o piloto, o veredito e as pendências.

## Critérios de aceite
- [ ] v2 da área criada lado a lado e aprovada.
- [ ] Piloto real com veredito.
- [ ] Cutover só se aprovado; outras áreas intactas (guard).

## Ao terminar
Resuma em até 150 palavras e **PARE**. Para a próxima área, reenvie a U01.
