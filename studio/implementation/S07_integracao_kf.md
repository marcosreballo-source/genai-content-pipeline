# S07: A Knowledge Factory passa a usar o Studio (com autorização)

**Depende de:** S06 · **Gate humano:** **SIM** (autorização para alterar itens `kf-*`)

## Preâmbulo
Siga o preâmbulo da X01 e o protocolo da KF (`knowledge_factory/implementation/MIGRATION_PROTOCOL.md`, seção ABSORB imediato: backup, dry-run, uma mudança por rodada). Os itens `kf-*` estão no baseline do guard: **cada arquivo alterado precisa de linha aprovada em `approved_changes.txt`**.

## Objetivo
Fazer os cursos da KF saírem como arquivos reais (pptx, PDF), com bibliografia obrigatória e revisão por personas, usando o Studio em vez de produtores próprios.

## Tarefas
1. **Lista de mudanças** (mostre ao usuário e peça autorização item a item; registre os globs exatos em `approved_changes.txt` com `# MIG-S07-xx`):
   - a. `kf-slide-producer` (ou o produtor de slides da D10) vira adaptador: monta um job em `knowledge_factory/projects/<P>/06_production/slides/<A-xx>/`, com blueprint `course-lecture`, kit do curso e `sources` = `library_id` das fontes S-xx do ativo. O `outline.yaml` sai dos nós K-xx e das competências do ativo. Depois executa `/mf-deck` e devolve `build/deck.pptx` e `deck.pdf` como o ativo `A-xx`.
   - b. Produtor de apostila/workbook: mesmo padrão com `/mf-doc` (template `studio-book` ou o institucional).
   - c. `kf-source-analyzer`: cada fonte S-xx do `source_report` ganha o campo `library_id` (fonte registrada na Source Library). A análise de autoridade passa a usar o ledger.
   - d. `/kf-graph`: depois da validação do grafo, roda `sl_sources.py coverage` com a política do campo `bibliography` do `_state.yaml` (padrão da X03). Em `strict`, nó essencial sem fonte bloqueia a aprovação do grafo e gera pedidos de bibliografia para o usuário.
   - e. `/kf-audit`: mantém os 4 auditores e acrescenta `rep_review.py` com o painel `curso-kf` (persona aluno-curso = simulação do aluno com o perfil da EDS).
   - f. Rule `kf-core`: a regra de tamanho de lote passa de ~2000 para **1200 palavras**.
   - g. Template `_state.yaml` da KF: novo campo `bibliography: strict`.
2. **Execução:** uma mudança por rodada: backup, dry-run no `migration_log.md`, edição, guard (só mudanças `[aprovado]`) e teste de gatilho.
3. **Regressão:** reproduza 1 ativo de slides e 1 de apostila do módulo piloto do KT_Aramis (D11) pelo caminho novo. Compare com o resultado da D11 (antes: .md; agora: arquivo real) e registre em `knowledge_factory/projects/KT_Aramis/06_production/studio_comparison.md`.
4. **Cobertura:** rode `/sl-coverage` no KT_Aramis com a política definida e entregue ao usuário a lista de material base faltante.

## Critérios de aceite
- [ ] Mudanças a–g autorizadas e aplicadas uma por rodada, com backup e registro.
- [ ] Ativos de slides e apostila do KT_Aramis gerados como .pptx/.pdf pelo Studio.
- [ ] Gate de bibliografia ativo no `/kf-graph`.
- [ ] Guard: só mudanças aprovadas; outras frentes intactas.

## Ao terminar
Atualize o LOG (KF e Studio), resuma em até 150 palavras e **PARE**.
