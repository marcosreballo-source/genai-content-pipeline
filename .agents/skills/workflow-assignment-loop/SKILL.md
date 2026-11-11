---
name: workflow-assignment-loop
description: >-
  Executa o Content Expansion Protocol (CEP) em loop iterativo. Orquestra o 
  Assignment Architect e o Academic Reviewer iterativamente até atingir nota
  ≥ 9.8 ou o limite de 5 tentativas.
---

# Workflow: Assignment Loop (Auto-QA)

## Overview
Este workflow é responsável pela melhoria contínua e autônoma de um entregável acadêmico. Ele cria um ciclo de feedback entre a produção (`assignment-architect`) e a revisão (`academic-reviewer`), parando apenas quando a qualidade atinge a nota de corte ou atinge o limite máximo de tentativas.

## Dependencies
- **assignment-architect**: Responsável pela redação, criação de testes, refatoração de código e aplicação de feedbacks.
- **academic-reviewer**: Responsável pela avaliação do entregável contra o ASB e geração do `review_report_v{N}.md`.

## Rate Limiting
N/A (Skill puramente instrucional de orquestração local de agentes).

## Workflow

### 1. Inicialização
- Verifique se os arquivos de contexto e enunciado estão disponíveis no workspace (repassados pelo Triador).
- Defina o `limite_tentativas = 5`.
- Defina a `nota_corte = 9.8`.
- Crie o artefato temporário no contexto para iniciar a contagem (Iteração = 1).

### 2. Produção / Refatoração (Assignment Architect)
- Invoque o **Assignment Architect** para redigir o entregável inicial (se Iteração 1) ou para aplicar rigorosamente as críticas do último `review_report`.
- Garanta que o entregável seja salvo no repositório correto conforme a regra `academicos_storage.md`.
- **Regra Estrita de Não-Sobrescrita**: Ao empacotar novas versões (`.zip`), NUNCA sobrescreva pacotes anteriores; itere sempre o número da versão no nome do arquivo (ex: `entrega_<tarefa>_v2.0.zip`).

### 2.5 Execução do Portão Determinístico de Validação (Princípio P13)
- Antes de invocar qualquer sub-revisor textual, execute:
  `.\.venv\Scripts\python.exe .agents/tools/qa_code_metric_gates.py <pasta_da_tarefa>`
- Se o portão retornar **Exit Code 1**:
  - A iteração é considerada **REJEITADA NO PORTÃO TÉCNICO**.
  - O pipeline NÃO deve acionar o `academic-reviewer` para avaliação textual.
  - O feedback detalhado de `qa_gate_audit_report.md` (tabelas divergentes, cabeçalhos errados, suíte não minimal ou pacote corrompido) deve ser devolvido imediatamente ao **Assignment Architect** para correção.
  - Volte para a Etapa 2 para refatorar até que o portão retorne **Exit Code 0 (APROVADO)**.

### 3. Revisão Acadêmica (Academic Reviewer)
- Invoque o **Academic Reviewer** para avaliar a versão recém-produzida.
- O revisor DEVE salvar o relatório usando o versionamento `_v{N}.md`.
- Leia o arquivo de relatório de revisão gerado e extraia a "Nota Estimada".

### 4. Condição de Parada (O Loop)
- Se a Nota Estimada for **>= 9.8**: Interrompa o loop e avance para a etapa 5.
- Se a Nota Estimada for **< 9.8** e a Iteração for **< 5**: Incremente a iteração (+1) e volte para a Etapa 2.
- Se a Nota Estimada for **< 9.8** e a Iteração for **== 5**: Interrompa o loop (falha no limite de tentativas) e avance para a etapa 5 aceitando a melhor versão gerada.

### 5. Relatório Geral (Conclusão)
- Gere um documento `loop_evolution_report.md` na pasta raiz da tarefa contendo:
  - Total de iterações executadas.
  - A evolução das notas ao longo das versões (Ex: v1=7.0 -> v2=8.5 -> v3=10.0).
  - Um breve sumário das principais mudanças estruturais realizadas no entregável ao longo do loop.
- Apresente o arquivo final ao usuário e declare o fim do workflow.

## Common Mistakes
- **Esquecer de incrementar a versão**: O agente falhar em instruir o reviewer a salvar como `_v2`, sobrescrevendo a `_v1`.
- **Loop Infinito**: Ignorar o limite de 5 iterações.
- **Falta de Triagem**: Rodar esse workflow sem que a DKB e o ASB tenham sido processados.
