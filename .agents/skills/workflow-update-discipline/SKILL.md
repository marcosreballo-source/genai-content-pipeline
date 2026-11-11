---
name: workflow-update-discipline
description: >-
  Use this skill to update an existing discipline with new materials. Execute this workflow when the student receives new slides, assignments, or documents for an ongoing discipline.
---

# Workflow: Atualizar Disciplina Existente

## Quando usar

Quando a disciplina já existe (já passou pelo `workflow-new-discipline`) e novos materiais didáticos são recebidos durante o andamento do semestre.

## Passos

1. **Ingestão no Workspace**: Certifique-se de que os novos materiais brutos foram colocados na raiz da pasta da disciplina: `S04/{codigo_disciplina}/`.
2. **Triagem e Anti-deduplicação**: Liste os novos arquivos na raiz. Antes de processá-los, compare-os com o inventário da disciplina (no `metadata.json`) e com os arquivos já existentes nas subpastas. 
   - Verifique por nomes semelhantes (ex: `Aula01 (1).pdf` vs `Aula01.pdf`).
   - Recomenda-se gerar um hash (ex: MD5/SHA-256) dos novos arquivos e comparar com os antigos, se possível, para identificar arquivos idênticos com nomes diferentes.
   - Remova automaticamente as duplicatas confirmadas da raiz e avise o usuário.
3. **Automação CEP (Content Expansion Protocol)**: Escreva e execute um script Python utilizando o Antigravity SDK (`google.antigravity`) que invoque o **Knowledge Curator**. 
   - O script deve passar APENAS a lista dos novos arquivos (não duplicados).
   - O Knowledge Curator fará o append de novos conceitos, definições e critérios na DKB existente sem apagar o histórico.
4. **Organização de Diretórios**: Mova os novos materiais analisados para as subpastas semânticas existentes (ex: `01_Aulas_Slides`). Se necessário, proponha novas categorias.
5. **Reavaliação Estratégica**: Invoque o agente **Academic Strategist** instruindo-o a atualizar o Blueprint da disciplina: "Use o academic-strategist para reavaliar {codigo_disciplina} considerando os novos materiais".
6. A disciplina está atualizada e pronta para os próximos desafios.
