---
name: sl-coverage
description: Verifica se cada conceito de um Knowledge Graph (ou de um outline/sumário) tem fonte na biblioteca, gera pedidos de bibliografia para o usuário providenciar e aplica a política do projeto (strict bloqueia produção sem fonte). Use em /sl-coverage, no gate de grafo da KF ou antes de produzir material técnico. Uso do Studio: acionar apenas em comandos /mf-*, /sl-*, /rep-*, /studio-* ou em jobs do Studio.
---
## Procedimento
1. Garanta índice atualizado: `python studio/scripts/sl_sources.py index`.
2. Projeto KF:
   `sl_sources.py coverage --graph knowledge_factory/projects/<P>/03_knowledge/knowledge_graph.md --source-report knowledge_factory/projects/<P>/01_discovery/source_report.md --policy <strict|warn> --out knowledge_factory/projects/<P>/03_knowledge`
   A política vem do campo `bibliography` do `_state.yaml` (padrão: strict).
3. Sem grafo (outros orquestradores): monte um grafo mínimo (`nodes` com id, name, level, criticality, outcomes) a partir do outline ou sumário e rode o mesmo comando.
4. Leia `coverage_report.md` e apresente ao usuário **os pedidos de bibliografia** numa tabela curta: conceito, por que é necessário, tipo de fonte sugerido. Diga explicitamente: "não vou produzir estes tópicos sem fonte".
5. Quando o usuário trouxer o material: skill sl-ingest e sl-extract nos trechos relevantes, depois `sl_sources.py fulfill <REQ> --source <SRC>` e rode a cobertura de novo.
6. "Fraco" (só menção, sem definição) com criticidade essential: trate como pedido, salvo se o usuário aceitar.

## Proibições
- Marcar como coberto um conceito só porque "é conhecido".
- Usar `effort_minutes: 0` (assumido) para contornar a cobertura sem o público realmente dominar o conceito pela EDS.
