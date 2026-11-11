# X01: Snapshot para o Claude, verificação do pacote e inventário

**Depende de:** KF instalada (D18 concluída) · **Gate humano:** não

## Contexto
O usuário vai expandir o workspace com o **Studio** (pasta `studio/`), uma camada compartilhada por todos os orquestradores. Ela traz:
- **Material Factory** (`mf-`): slides .pptx editáveis e Beamer, documentos LaTeX a partir de templates;
- **Source Library** (`sl-`): bibliografia oficial com fichas fiéis e pedidos de bibliografia;
- **Review Engine** (`rep-`): revisão por personas e lentes.

Os scripts e as skills já vêm **prontos e testados** em `studio/`. O seu trabalho nesta fase é verificar, mapear o que já existe e instalar com segurança, sem afetar as outras frentes. **Você executa apenas a X01.**

## Preâmbulo (vale para todas as deliveries X e S)
1. Leia `studio/implementation/LOG.md` (crie-o nesta X01) e confirme que a delivery anterior está DONE.
2. Leia só os arquivos listados em "Entradas". Não reescreva scripts do Studio: só execute-os. Se um script falhar, mostre o erro e PARE.
3. Cada resposta tem no máximo ~1200 palavras. Tarefa maior: faça em partes, marque PARTIAL no LOG e pare.
4. Itens de outras frentes nunca são editados sem uma linha autorizada em `knowledge_factory/implementation/mapping/approved_changes.txt`.
5. Ao terminar: rode `python knowledge_factory/scripts/kf_guard.py check`. ERRO causado por você: reverta. ERRO causado pelo usuário: confirme com ele e rode `accept`. Depois atualize o LOG e PARE.

## Entradas
- `studio/README.md`, `studio/implementation/studio_roles_catalog.md`
- `knowledge_factory/implementation/LOG.md` (para ler `AGENT_DIR`)

## Tarefas
1. **Pacote:** confirme que `studio/` existe na raiz com `scripts/`, `formats/`, `review/`, `agent_files/` e `implementation/`. Nada de `studio/agent_files/` vai para a pasta de agentes nesta delivery.
2. **Testes rápidos:** `python studio/scripts/tests/run_tests.py --fast`. Todos devem passar. Se `import yaml/pptx/PIL/pypdf/matplotlib` falhar, rode `pip install pyyaml python-pptx pillow pypdf matplotlib` e repita. Falhou de novo: PARE e mostre a saída.
3. **Snapshot para o Claude (pedido do usuário):** pergunte se ele quer incluir o texto das skills/workflows das outras frentes (recomendado, para o manual e para o upgrade das áreas). Rode:
   ```
   python studio/scripts/studio_snapshot.py --other-fronts full      (ou --other-fronts names)
   ```
   Informe o caminho do .zip gerado em `studio/_snapshots/` e diga ao usuário: "anexe este arquivo na conversa com o Claude". O script mascara segredos e ignora binários.
4. **Inventário atualizado:** `python knowledge_factory/scripts/kf_inventory.py scan --out studio/implementation/mapping` (mesmo formato da M01, nova pasta).
5. **Namespace do guard:** acrescente ao final de `knowledge_factory/implementation/mapping/kf_namespace.txt` (sem mudar as linhas existentes):
   ```
   */skills/mf-*/*
   */skills/sl-*/*
   */skills/rep-*/*
   */workflows/mf-*.md
   */workflows/sl-*.md
   */workflows/rep-*.md
   */workflows/studio-*.md
   */rules/studio-*.md
   ```
   Explique ao usuário: a partir daqui, itens com esses prefixos são reconhecidos como do Studio pelo guard.
6. **LOG:** crie `studio/implementation/LOG.md`:
   ```markdown
   # LOG de implantação do Studio
   AGENT_DIR: <valor da KF>
   Snapshot: <caminho do zip> (outras frentes: full|names)
   | Delivery | Status | Data | Guard | Notas |
   |---|---|---|---|---|
   | X01 | DONE | <hoje> | OK | <notas> |
   | X02, X03, S01 a S08, U01 | TODO | | | |
   ## Decisões e desvios
   ```

## Critérios de aceite
- [ ] Testes `--fast` passando.
- [ ] Snapshot gerado e entregue ao usuário.
- [ ] Inventário em `studio/implementation/mapping/`.
- [ ] Namespace estendido; `kf_guard.py check` limpo.

## Ao terminar
Resuma em até 120 palavras (inclua o caminho do snapshot) e **PARE**.
