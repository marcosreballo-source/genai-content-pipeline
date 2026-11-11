---
name: workflow-new-assignment
description: >-
  Use this skill to start a new academic assignment. Execute this workflow when the
  student needs to produce a deliverable (paper, report, article, etc).
  Atua como Triador antes de iniciar o loop de produção.
---

# Workflow: Novo Trabalho Acadêmico (Triagem)

## Overview
Este workflow é a porta de entrada para a criação de trabalhos acadêmicos. Ele funciona como uma triagem que entende os requisitos do trabalho e, em seguida, delega a orquestração pesada de produção para a skill `workflow-assignment-loop`.

## Dependencies
- **workflow-assignment-loop**: Para executar a iteração autônoma de produção e revisão de qualidade.

## Pré-requisitos
- DKB da disciplina deve existir (executar workflow-new-discipline se necessário).
- ASB da disciplina deve existir.

## Workflow

### 1. Triagem e Entendimento
- Identifique o tipo de entregável sendo solicitado pelo usuário (código, paper, apresentação, script de teste).
- Localize e leia rapidamente o arquivo de enunciado/briefing do trabalho na pasta da disciplina.
- Estruture mentalmente ou no chat a estratégia inicial.

### 2. Delegação
- Invoque imediatamente a skill **`workflow-assignment-loop`**.
- Passe para essa skill todas as informações necessárias, incluindo:
  - O código da disciplina (`{disciplina_id}`).
  - O tipo de trabalho a ser produzido.
  - As eventuais diretrizes específicas levantadas pelo usuário.
  
*(O trabalho pesado de invocar Arquiteto e Revisor até bater a nota alvo será inteiramente feito pelo loop).*
