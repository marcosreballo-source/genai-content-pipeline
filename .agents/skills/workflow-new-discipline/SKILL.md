---
name: workflow-new-discipline
description: >-
  Use this skill to start a new discipline. Execute this workflow when the student
  receives materials for a new discipline.
---

# Workflow: Iniciar Nova Disciplina

## Quando usar

Quando o estudante recebe materiais de uma nova disciplina.

## Passos

1. Criar pasta da disciplina na raiz do workspace: `S04/{codigo_disciplina}/`
2. Colocar todos os materiais do professor na pasta
3. Executar o **Knowledge Curator** diretamente neste chat, seguindo rigorosamente o Content Expansion Protocol (CEP) fragmentado descrito na skill `knowledge-curator`.
4. O Knowledge Curator processará **1 arquivo por vez** (ou blocos de páginas para arquivos longos). Cada turno de resposta do agente deve processar EXATAMENTE 1 arquivo e então PARAR, reportar o progresso, e só processar o próximo no turno seguinte.
5. NÃO tente gerar a DKB inteira de uma só vez. NÃO adivinhe conteúdo pelos nomes dos arquivos. A ingestão DEVE ser rigorosamente fragmentada, arquivo por arquivo.
6. Verificar a DKB consolidada em `_academicos_memory/discipline_knowledge_base/{codigo_disciplina}/`
7. **Organização do Diretório Raiz**: Analisar os arquivos brutos que estão soltos na pasta da disciplina e propor ao usuário um sistema de subpastas semânticas (ex: `01_Aulas_Slides`, `02_Atividades_Projetos`, `03_Administrativo_Plano`).
8. Após aprovação do usuário, usar comandos de terminal para criar as pastas e **mover (transferir)** os arquivos brutos para suas respectivas categorias, limpando a pasta raiz.
9. Invocar o **Academic Strategist**: "Use o academic-strategist para analisar {codigo_disciplina}"
10. Verificar o ASB gerado em `_academicos_memory/academic_success_blueprint/{codigo_disciplina}/`
11. A disciplina está pronta para uso pelos demais agentes.
