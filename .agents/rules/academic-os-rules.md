# AcademicOS — Regras Globais do Sistema

Estas regras se aplicam a TODOS os agentes do AcademicOS. São invioláveis.

## Princípios Arquiteturais

### P1 — Primazia do Material
Todo material fornecido pelo professor (slides, PDFs, apostilas, rubricas, enunciados) possui prioridade MÁXIMA. O conhecimento presente nos materiais da disciplina SEMPRE prevalece sobre conhecimento geral do modelo.

### P2 — Conhecimento Contextual > Geral
Os agentes DEVEM priorizar a Discipline Knowledge Base (DKB) sobre conhecimento pré-treinado. Se a DKB contém uma definição, USE-A — mesmo que o modelo "saiba" uma definição diferente.

### P3 — Profundidade Obrigatória
Nenhum agente produz saída superficial. Todos os agentes possuem critérios mínimos de densidade. Resumos excessivos são PROIBIDOS. Parágrafos de 1-2 frases são PROIBIDOS (exceto transições). Listas sem desenvolvimento são PROIBIDAS.

### P4 — Rastreabilidade
Toda afirmação de peso DEVE ser rastreável ao material da disciplina ou a uma referência bibliográfica. Afirmações sem fundamentação são PROIBIDAS em entregáveis acadêmicos.

### P5 — Memória Compartilhada
Agentes comunicam-se EXCLUSIVAMENTE via artefatos persistentes na pasta `_academicos_memory/`. Nunca por passagem direta de contexto entre invocações.

Estrutura da memória:
- `_academicos_memory/discipline_knowledge_base/` — Base de conhecimento por disciplina
- `_academicos_memory/academic_success_blueprint/` — Estratégias de sucesso por disciplina
- `_academicos_memory/assignment_repository/` — Entregáveis produzidos
- `_academicos_memory/research_repository/` — Pesquisas e revisões bibliográficas
- `_academicos_memory/evaluation_repository/` — Avaliações, revisões e simulados

### P6 — Separação de Responsabilidades
Cada agente tem escopo exclusivo. Nenhum agente duplica a função de outro. Em particular: SOMENTE o Knowledge Curator lê e processa materiais brutos do professor. Nenhum outro agente deve interpretar PDFs, slides ou apostilas diretamente.

### P7 — Revisão Obrigatória
Nenhum entregável acadêmico é considerado finalizado sem passar pelo Academic Reviewer. O ciclo obrigatório é: Produção → Revisão → Melhoria → Revisão Final.

### P8 — Produção Fragmentada (Content Expansion Protocol)
Conteúdo extenso DEVE ser decomposto em fragmentos e produzido iterativamente. Nenhum agente de produção opera em resposta única para documentos acima de 1000 palavras.

O protocolo obrigatório é:
1. Gerar Expansion Plan (outline + estimativas de extensão por seção)
2. Produzir cada seção como um fragmento separado, com foco total
3. Consolidar os fragmentos em documento coerente
4. Harmonizar (consistência terminológica, transições, eliminar repetições)

### P9 — Persistência Definitiva de Entregáveis e Artefatos
Nenhum entregável final, draft útil, manifesto (ex: `discipline_manifest.md`) ou plano de expansão deve ser deixado apenas como um "artefato de UI" na pasta `.gemini`. Todos os artefatos gerados DEVEM ser salvos fisicamente nas respectivas pastas do workspace em `_academicos_memory/` (ex: `_academicos_memory/assignment_repository/{disciplina}/` ou `_academicos_memory/discipline_knowledge_base/{disciplina}/`). O sistema deve operar de forma que, se o chat for apagado, todo o conhecimento e entregáveis permaneçam estruturados no disco.

### P10 — Blindagem Total contra Vazamento de Metadados e Jargões Internos (Zero Jargon Policy)
Entregáveis acadêmicos (relatórios, websites, documentos LaTeX, notebooks, resumos, apresentações, códigos-fonte para entrega) são trabalhos formais do discente submetidos a docentes universitários.
É TERMINANTEMENTE PROIBIDO incluir qualquer menção a siglas, arquivos ou infraestrutura interna do AcademicOS no texto dos entregáveis finais, tais como:
- Siglas internas: `DKB`, `ASB`, `CEP`, `AcademicOS`, `Content Expansion Protocol`, `Discipline Knowledge Base`, `Academic Success Blueprint`.
- Agentes internos: `Assignment Architect`, `Academic Reviewer`, `Format Reviewer`, `Knowledge Curator`, etc.
- Pastas e memória: `_academicos_memory`, `assignment_repository`, `evaluation_repository`, etc.
- Scripts e ferramentas auxiliares de automação interna (ex: scripts auxiliares de geração, raspadores) NÃO devem ser citados no texto do trabalho, salvo quando explicitamente exigido pelo enunciado da atividade.
As informações da DKB e do ASB servem EXCLUSIVAMENTE para orientar o raciocínio e a profundidade do agente nos bastidores. No documento final, todo argumento deve ser justificado com fundamentação teórica, técnica ou metodológica formal da respectiva área do conhecimento, sem jamais citar a base ou o sistema nominalmente.

### P11 — Integridade Visual, Renderização Gráfica e Sintaxe Estrita de Links e Mídias
Entregáveis acadêmicos (`.md`, `.qmd`, `.html`, `.tex`, `.pdf`) e figuras anexas devem possuir apresentação gráfica impecável e portabilidade total:
1. **Links e Imagens Portáveis (Proibição Estrita de `file:///`)**:
   - Todo link para imagem ou anexo DEVE usar caminhos relativos ao diretório do documento (ex: `![Legenda](assets/figura.png)`, `[arquivo.csv](arquivo.csv)`).
   - É TERMINANTEMENTE PROIBIDO usar URIs locais absolutas do sistema operacional (`file:///c:/...` ou `<file:///...>`). Esses protocolos quebram visualizadores Markdown (VS Code, GitHub, Typora) e expõem a estrutura local de diretórios.
2. **Sintaxe Estrita de Links em Markdown**:
   - Links devem seguir estritamente `[texto](destino)`. Nunca inserir espaço entre os colchetes e os parênteses (ex: `[texto] (url)` ou `[texto] (<url>)`), o que faz o parser renderizar o código Markdown como texto cru.
   - Proibição absoluta de tags de imagem duplicadas consecutivas no documento.
3. **Padrão Gráfico e Prevenção de Colisão Visual (Matplotlib / Figuras Técnicas)**:
   - Em figuras com múltiplos painéis e títulos globais (`plt.suptitle`), é OBRIGATÓRIO reservar margem vertical suficiente (`top <= 0.84` no `gridspec` ou separação explícita com `fig.text`) para impedir colisões ou sobreposição de texto com os títulos dos subplots (`ax.set_title`).
   - Todos os pontos de dados, círculos ou anotações DEVEM estar contidos no enquadramento dos eixos (`xlim` e `ylim` calculados dinamicamente com folga proporcional, nunca hardcoded abaixo do alcance dos dados).
   - Figuras devem ser renderizadas com resolução mínima de 300 DPI e tipografia nítida.
4. **Inspeção Visual e Programática Obrigatória pelos Revisores**:
   - Nenhum revisor pode aprovar um trabalho com gráficos sem inspecionar visualmente o arquivo de imagem gerado (`read_file`) e executar validação programática de existência física e sintaxe dos links.

### P12 — Apresentações, Visualizações SOTA (Ciclo de 60 Dias) e Auditoria Visual Anti-Teatro
Entregáveis que envolvam apresentações (`.pptx`, `.pdf`, Beamer) ou visualizações de dados/diagramas em qualquer disciplina devem obedecer a quatro travas invioláveis:
1. **Revisão de Estado da Arte (SOTA) a cada 60 Dias Corridos e Provisionamento Automático (Zero Fallback):**
   - O ecossistema oficial compreende: **JS/Web** (`D3`, `plotly.js`, `Vega`, `Vega-Lite`, `nivo`, `Victory`, `Chart.js`, `vis.js`, `Highcharts`, `Google Charts`, `Leaflet`, `ECharts`, `Mermaid`), **Python** (`Bokeh`, `Dash`, `plotly.py`, `Altair`, `mpld3`, `Matplotlib`, `Seaborn`, `NetworkX`, `Pillow`, `Chaco`), **R** (`ggplot2`) e **TeX/Grafos** (`TikZ`, `PGFPlots`, `Graphviz`).
   - Antes de usar qualquer biblioteca, o agente DEVE rodar `.\.venv\Scripts\python.exe studio/tools/visual_sota_auditor.py check --library <lib>` (renovando o estudo SOTA se tiver $\ge 60$ dias corridos) e `.\.venv\Scripts\python.exe studio/tools/visual_env_provisioner.py --ensure <lib>`. É proibido rebaixar a qualidade visual por preguiça de provisionar a ferramenta recomendada.
2. **Síntese Ativa Multidisciplinar (Zero Placeholders Órfãos / Blocos Cinzas):**
   - É terminantemente proibido entregar slides com `Picture Placeholder` vazio ou retângulos cinzas opacos. O agente deve sintetizar autonomamente os diagramas técnicos, arquiteturas, fluxogramas ou gráficos da disciplina.
3. **Equilíbrio Espacial e Escala Tipográfica Auditada no PDF:**
   - É proibido deixar metade do slide em branco ("deserto lateral") ou colunas com mais de 60% de vazio vertical ("cemitério vertical"). Textos não podem sofrer colisão de linhas nem redução para fontes microscópicas.
4. **Cadeia de Custódia com Canário Óptico (`visual_qa_gates.py`):**
   - Nenhuma apresentação é considerada aprovada sem executar `.\.venv\Scripts\python.exe studio/tools/visual_qa_gates.py <alvo>`, inspecionar `qa_challenge_sheet.png` via visão (`read_file` / subagente auditor), registrar o aviso `[INICIANDO INSPEÇÃO VISUAL MULTIMODAL]` no chat e validar o código canário desenhado nos pixels com `--verify-audit --canary <CODIGO>`.

### P13 — Integridade Numérica Estrita, Rigor Conceitual e Portões Determinísticos em Entregáveis Técnicos
Em entregáveis que envolvam experimentos quantitativos, análise de código, métricas de teste (ex: coverage, MC/DC, cfgcoverage) e modelos de fluxo de controle:

1. **Portão Determinístico Obrigatório (`qa_code_metric_gates.py`)**:
   - Nenhum entregável de código/teste pode ser submetido à revisão acadêmica sem a execução de `.\.venv\Scripts\python.exe .agents/tools/qa_code_metric_gates.py <pasta_da_tarefa>` retornando **Exit Code 0**.
   - O orquestrador `academic-reviewer` é terminantemente proibido de emitir nota ou aprovar o trabalho se o portão falhar.

2. **Conciliação Numérica Tríplice (Zero Divergência)**:
   - Todo número presente em tabelas ou texto do relatório DEVE ser identicamente congruente com:
     (a) Os cabeçalhos e docstrings dos arquivos de código-fonte entregues (`.py`);
     (b) Os arquivos de saída bruta (logs e evidências `evid_*.txt`);
     (c) Os artefatos binários ou estruturais gerados (tabelas CSV, pickles, matrizes de cobertura).
   - Se houver medições em etapas diferentes (ex.: antes vs. depois de remoção de requisitos inexecutáveis, ou preliminar vs. final), o relatório DEVE explicitar a qual etapa cada número pertence, sendo proibido misturar métricas de fases distintas na mesma tabela sem rotulagem explícita.

3. **Rigor Conceitual na Modelagem de Grafos de Controle (GFC/CFG)**:
   - Funções com múltiplos comandos de retorno (`return`) possuem **múltiplos nós finais/saídas distintas** no GFC ($N_f \subseteq N$), a menos que a ferramenta utilizada colapse comprovadamente esses nós.
   - Em laços condicionais (`while` / `for`), uma aresta de saída do laço NUNCA pode ser justificada como garantia de que o corpo foi executado, pois a condição de término pode ser satisfeita com zero iterações.

4. **Validação de Minimização (Além da Heurística Gulosa)**:
   - É expressamente proibido classificar um conjunto como "estritamente mínimo" com base exclusiva em algoritmos gulosos (*Greedy Set Cover*), visto que o problema de cobertura de conjuntos é NP-difícil e a heurística não garante a cardinalidade mínima global.
   - O agente DEVE realizar pós-verificação (teste de remoção elemento a elemento) para comprovar que nenhum caso é redundante e, sempre que viável, comparar a solução heurística com a resolução matemática exata (Branch & Bound / Programação Inteira).

5. **Versionamento Não-Destrutivo de Pacotes e Entregáveis**:
   - NUNCA sobrescreva pacotes `.zip` de entrega anteriores ao aplicar correções ou refatorações. Preserve o arquivo existente e gere sempre um novo arquivo com sufixo de versão incrementado (ex: `_v2`, `_v2.0`, `_v3`).

## Regras de Conduta dos Agentes

1. Agentes NUNCA devem ignorar slides, PDFs, apostilas, rubricas ou instruções do professor.
2. Agentes NUNCA devem gerar conteúdo superficial ou genérico.
3. Agentes DEVEM justificar conclusões e recomendações.
4. Agentes DEVEM favorecer profundidade, pensamento crítico, fundamentação e rigor acadêmico.
5. Sempre que possível, recomendações devem ser rastreáveis aos materiais da disciplina.

## Identificação Institucional do Estudante
Para qualquer entregável acadêmico, planilha, relatório, documento LaTeX ou script de entrega que exija identificação do aluno:
- **Nome do Estudante**: `<NOME_DO_ESTUDANTE>`
- **Número USP (NUSP)**: `<NUSP>`
- **Instituto / Unidade de Origem**: `Instituto de Ciências Matemáticas e de Computação (ICMC / USP)`
- **Curso**: `Bacharelado em Sistemas de Informação (BSI)`
- **Convenção de Datas em Entregáveis**: Em documentos dinâmicos (Quarto `.qmd`, R Markdown `.Rmd`, LaTeX, etc.), SEMPRE especificar a data real corrente no formato ISO (ex: `date: "2026-10-16"`), configurando `date-format: "DD/MM/YYYY"` e `lang: pt-BR` para evitar que o Pandoc infira datas genéricas (como `2026-01-01`).
Agentes produtores (`assignment-architect`, scripts de automação) DEVEM preencher automaticamente esses campos sem deixar placeholders ou células em branco. Agentes revisores (`format-reviewer`) devem auditar e validar a presença correta desses dados.


## Caminhos do Sistema

- **Workspace**: `<LOCAL_PATH>`
- **Skills**: `.agents/skills/`
- **Regras**: `.agents/rules/`
- **Memória**: `_academicos_memory/`
- **Disciplinas existentes**: scc540, ssc0504, ssc0524, scc0252, rad2810
