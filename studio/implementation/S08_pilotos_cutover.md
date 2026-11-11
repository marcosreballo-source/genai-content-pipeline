# S08: Pilotos nas outras frentes e substituição das skills antigas de slides (GATE FINAL da Parte 1)

**Depende de:** S07 · **Gate humano:** **SIM** (veredito por frente e autorização item a item)

## Preâmbulo
Siga o preâmbulo da X01 e o `STUDIO_PROTOCOL_ADDENDUM.md` (SUPERSEDE). Use `studio/implementation/mapping/studio_rename_map.md`.

## Objetivo
Provar o Studio em cada frente que usa slides e, só onde ele for igual ou melhor, aposentar a skill antiga, mantendo os comandos que o usuário já usa como alias.

## Tarefas
1. **Pilotos por frente** (as frentes escolhidas na X03; um piloto real ou realista por frente, via `/mf-deck`):
   - pitch (`pitch-competition` ou `investor-pitch`, painel `competicao-startup` ou `pitch-investidor`);
   - acadêmico (`symposium-talk` ou `thesis-defense`, Beamer + pptx, painel calibrado da S05);
   - gestão de imóveis (`property-manual`: preencha o perfil do imóvel a partir de `studio/formats/deck/profiles/property_profile_template.yaml` e do regimento registrado na Source Library; painel `manual-imovel`).
   Após cada piloto, peça o veredito: **melhor / igual / pior** que a forma antiga, com o motivo. Registre em `studio/implementation/mapping/supersede_verdicts.md`.
2. **Cutover** (só frentes com melhor ou igual), item a item com autorização:
   - backup em `studio/implementation/backup/<item>/`;
   - mova o item antigo para `studio/archive/` ou mantenha-o, se alguma frente votou "pior";
   - crie o alias com o nome antigo: um workflow cujo único passo é executar `/mf-deck` com o blueprint típico daquela frente;
   - atualize referências só nos arquivos autorizados;
   - rode `kf_inventory.py dangling --names <arquivo com os nomes removidos>` e `kf_guard.py check` (só `[aprovado]`).
3. **REP antigo:** com as lentes e personas absorvidas na S05, o orquestrador antigo pode ser arquivado (com alias para `/rep-review`), se o usuário autorizar.
4. **Testes de fumaça:** um pedido típico de cada frente (inclusive das que **não** migraram) funciona como esperado.
5. **Novo baseline:** com autorização, `kf_guard.py snapshot --force` e registro no LOG.
6. **Relatório da Parte 1:** `studio/implementation/PART1_REPORT.md` com as notas dos pilotos, o que foi substituído, os pedidos de script (`script_requests.md`) e as lacunas (`supersede_gaps.md`). **Este relatório e um novo snapshot (`studio_snapshot.py --other-fronts full`) vão para o Claude** preparar a Parte 2.

## Critérios de aceite
- [ ] Veredito registrado para cada frente pilotada.
- [ ] Substituições só onde aprovadas, com alias e backup; `dangling` limpo.
- [ ] Testes de fumaça OK em todas as frentes.
- [ ] `PART1_REPORT.md` e snapshot gerados.

## Ao terminar
Resuma em até 200 palavras e **PARE**. O GATE FINAL da Parte 1 é a aprovação do usuário.
