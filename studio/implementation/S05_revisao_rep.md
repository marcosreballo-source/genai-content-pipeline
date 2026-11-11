# S05: Revisão por personas: absorver o REP antigo e calibrar painéis reais

**Depende de:** S04 · **Gate humano:** não (aprovações pontuais)

## Preâmbulo
Siga o preâmbulo da X01. Leia o "Plano do REP" em `studio/implementation/mapping/studio_matrix.md`. Use as skills **rep-panel** e **rep-reviewer**.

## Objetivo
Trazer para o Review Engine o que o REP antigo tinha de bom, sem perder nada; calibrar ao menos dois painéis com documentos reais; e revisar o piloto da S03 com eles.

## Tarefas
1. **Absorver o REP (ABSORB/MERGE):** para cada linha do plano:
   - **lente existente:** acrescente o critério ao arquivo `studio/review/lenses/<id>.yaml`, com novo id (ex.: `NAR-6`) e `severity_hint`, sem mudar os critérios que já existem;
   - **nova lente:** crie `studio/review/lenses/<id>.yaml` no mesmo formato (id, name, question, applies_to, criteria);
   - **personas do REP sem equivalente:** crie em `studio/review/personas/` a partir da genérica mais próxima.
   Registre cada item em `studio/implementation/mapping/migration_log.md` (`MIG-Sxx`). O orquestrador antigo continua intacto até a S08.
2. **Painel acadêmico calibrado** (pergunte qual disciplina ou evento): registre na Source Library o enunciado, a rubrica ou o edital (sl-ingest + sl-extract), crie a persona específica (ex.: `prof-<disciplina>-<ano>`) com a rubrica REAL e um painel `disciplina-<código>` (ou `simposio-<evento>`).
3. **Painel de trabalho calibrado** (Eldorado ou pitch): mesmo procedimento com o plano do projeto, o edital ou a call.
4. **Revisão do piloto:** `/rep-review` no job da S03 com um dos painéis calibrados. Compare com a revisão da S03 (painel genérico): o que o painel calibrado pegou a mais?
5. **Feedback real:** se o usuário já apresentou o piloto ou tem pareceres antigos (nota comentada, parecer de revisor, perguntas da banca), faça a calibração (`rep_review.py calibrate`) e mostre recall e precisão.
6. **Ajuda-memória:** escreva em `studio/review/HOW_TO_CALIBRATE.md` (até 300 palavras) o passo a passo para o usuário calibrar uma persona depois de cada apresentação real.

## Critérios de aceite
- [ ] Todas as partições do REP antigo mapeadas para lentes (existentes ou novas), registradas no migration_log.
- [ ] Dois painéis calibrados com documentos reais.
- [ ] Revisão do piloto com painel calibrado consolidada.
- [ ] Guard limpo; REP antigo intacto.

## Ao terminar
Atualize o LOG, resuma em até 150 palavras e **PARE**.
