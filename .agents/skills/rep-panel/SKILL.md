---
name: rep-panel
description: Monta e calibra painéis de revisão por personas (professor e monitor de disciplina, banca, revisores de journal, público de simpósio, jurados, investidores, clientes, gestores, participantes de oficina, moradores, administração e revisão jurídica do imóvel) a partir de documentos reais (enunciado, rubrica, edital, call, instruções aos autores, regimento) e de feedback real recebido. Use em /rep-panel ou antes da primeira revisão num contexto novo. Uso do Studio: acionar apenas em comandos /mf-*, /sl-*, /rep-*, /studio-* ou em jobs do Studio.
---
## Criar ou adaptar uma persona
1. Parta da persona genérica mais próxima em `studio/review/personas/` e copie-a para um id específico (ex.: `prof-ssc0xxx-2026`, `banca-mestrado-fulano`, `juri-edital-x-2026`).
2. Registre os documentos-base na Source Library (sl-ingest) e liste-os em `calibration.basis` (ex.: `SRC-enunciado-t2#C0001`).
3. Ajuste a partir dos documentos (só o que estiver escrito neles):
   - `rubric`: os critérios e pesos REAIS (copie a rubrica oficial quando existir);
   - `priorities`: pesos das lentes coerentes com a rubrica;
   - `red_flags` e `typical_questions`: do edital, do enunciado ou de arguições anteriores registradas.
4. Persona inspirada numa pessoa real: use só critérios públicos ou que o usuário relatou. Nada de traços de personalidade inventados.

## Montar um painel
Copie um painel de `studio/review/panels/` e ajuste `personas` (com pesos), `lenses` e `overview_lenses`. Registre no `brief.yaml` (`panel:`) ou no `doc.yaml`.

## Calibrar com feedback real (depois da apresentação ou da correção)
1. Peça ao usuário o feedback real (nota comentada, parecer, perguntas da banca).
2. Compare com `review/consolidated.yaml` do job e escreva `review/calibration_<persona>.yaml`:
   ```yaml
   job: <job>
   real_feedback:
     - {text: "...", matched_finding: C-003, lesson: "..."}   # matched_finding: null se a simulação não pegou
   simulated_not_raised_by_real: [C-007]
   add_red_flags: ["..."]
   ```
3. `python studio/scripts/rep_review.py calibrate <persona> --record review/calibration_<persona>.yaml`
4. Recall abaixo de 50%: revise prioridades e rubrica da persona com o usuário.
