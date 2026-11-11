# Adendo ao protocolo de migração: SUPERSEDE e UPLIFT

Complementa `knowledge_factory/implementation/MIGRATION_PROTOCOL.md` (todas as regras invioláveis de lá continuam valendo).

## SUPERSEDE (um item compartilhado é substituído por um serviço do Studio, também compartilhado)
Quando: o item serve várias frentes (ex.: a skill de apresentações usada em disciplinas, trabalho e pitches) e o Studio faz a mesma função com mais qualidade.
1. **Coexistência:** até a S08, o item antigo continua funcionando e intocado.
2. **Piloto por frente:** para cada frente que usa o item, faça um material real pelo Studio e peça ao usuário um veredito (melhor / igual / pior). Só frentes com "melhor" ou "igual" migram.
3. **Cutover (S08), item a item com autorização:** backup em `studio/implementation/backup/`; o item antigo vai para `studio/archive/` (ou fica, se alguma frente votou "pior"); cria-se um **alias** com o nome antigo cujo corpo chama o workflow do Studio (`/mf-deck`); referências só nos arquivos autorizados.
4. Frente que votou "pior": registre o motivo em `mapping/supersede_gaps.md`; vira ajuste de kit, blueprint ou script numa próxima parte.

## UPLIFT (um orquestrador de área é refeito no padrão do Studio)
Quando: workflows de uma área (estudo, business, education, trabalho, imóveis) produzem materiais de forma "solta".
1. Construa a versão 2 **ao lado** (`<área>-*`), seguindo o padrão: brief → artefatos de especificação → produção pelo Studio → revisão por painel → pacote final.
2. Reaproveite o conteúdo útil dos workflows antigos numa seção "Herdado de".
3. Piloto real; com aprovação do usuário, cutover com alias (como no SUPERSEDE).
4. Uma área por vez (delivery U01, repetida por área).
