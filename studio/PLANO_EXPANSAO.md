# Plano de expansão: da Knowledge Factory ao Studio

## 1. Em uma frase: o que você já tem
A Knowledge Factory (KF) é uma **linha de montagem de planejamento de cursos**. Cada etapa produz um documento formal que a seguinte usa:

```
fontes → EDS (o que ensinar, para quem) → grafo de conceitos → competências → currículo → manifesto de materiais → produção → auditoria
```

Ela entrega bem a parte de **planejar e rastrear**. Mas a produção, na D10, só ligou produtores que escreviam texto. Não havia nenhum programa que transformasse esse texto em PowerPoint ou PDF. Por isso você só viu `.md`.

## 2. O que muda: o Studio
O Studio é uma camada **compartilhada** e independente da KF. Cursos, estudo, business, Eldorado e imóveis passam a usá-la do mesmo jeito.

| Seu ponto | Resposta no Studio |
|---|---|
| 1. Manual do orquestrador | Snapshot da sua instalação (X01) → o Claude escreve o manual sobre o que realmente existe aí → o manual vira fonte da própria KF (curso "meta") |
| 2. Slides em todas as frentes | Material Factory: .pptx editável com 22 tipos de slide, identidade visual por contexto (kit) ou template institucional, Beamer do mesmo conteúdo, prévia em imagem, QA e roteiro de fala. 11 roteiros prontos: pitch de competição, investidor, cliente, disciplina, status de pesquisa, resultados para negócios, rampagem, aula, manual de imóvel, simpósio, defesa |
| 3. Templates LaTeX | Qualquer template baixado (abnTeX2/USP, SBC, IEEE, ACM, Beamer institucional...) é registrado sem ser editado. O Studio cria uma cópia com "encaixes", compila e aponta erros no trecho certo |
| 4. Independência com resposta curta | Os programas (scripts) fazem o trabalho pesado e já vêm prontos e testados. O Gemini só preenche fichas curtas (≤ 1200 palavras por rodada) e roda os comandos. `/studio-next` diz qual é o próximo passo |
| 5. Outros materiais | Mesmo ciclo para todo formato ("format pack"). Parte 1 traz slides e documentos LaTeX; Partes 2 e 3 trazem provas, diagramas, figuras científicas, gráficos, notebooks, textos, roteiros, animações, web e mockups |
| 6. Bibliografia oficial e aviso de falta | Source Library: sua triagem de 4 páginas continua sendo usada; cada trecho vira uma ficha que **transcreve literalmente** definições, teoremas, fórmulas e algoritmos (o script acusa quando a ficha resume demais) e o Studio emite **pedidos de bibliografia** quando um conceito do curso não tem fonte |
| 7. Revisão por personas | Review Engine (seu REP generalizado): revisão por **persona × tipo de cobrança × trecho**. 20 personas, 15 lentes e 12 painéis, calibráveis com rubricas e feedback reais |

## 3. Como o Gemini consegue fazer isso com ~1500 palavras de resposta
O segredo é que ele **nunca escreve o arquivo final**:
- **Slides:** escreve campos curtos em YAML ("título-mensagem", até 6 tópicos de 120 caracteres). O script cuida do layout, ajusta o texto ao espaço e gera o .pptx. O LibreOffice gera as imagens de prévia.
- **Documentos:** escreve fragmentos de seção. O script monta no template, compila e diz "erro na linha 12 do arquivo S03.p2".
- **Fontes:** uma ficha por trecho de 4 páginas. O script compara a ficha com o texto do trecho.
- **Revisão:** uma persona, até 3 lentes e uma fatia do material por rodada. O script junta, remove duplicatas, dá nota e gera o plano de correção e o banco de perguntas.
- **Nada inventado:** quando falta um dado, o Gemini escreve `[[PENDENTE: ...]]` e o QA final não deixa passar.

## 4. Avaliação honesta da revisão atual da KF
Pelo que foi planejado (vou confirmar no snapshot):
- **Boa** para coerência estrutural (objetivos, competências, cobertura do grafo, consistência entre artefatos), com achados que exigem evidência e blockers que travam.
- **Fraca** em quatro pontos:
  1. não revisa o material **renderizado** (visual);
  2. não simula o **aluno**;
  3. não tem **calibração** com a realidade (rubricas, feedback);
  4. quem produz e quem revisa são o mesmo modelo, na mesma lógica.

O Studio cobre esses quatro pontos. A S07 liga isso à KF.

Um limite importante: personas são **simulações**. Elas ficam boas quando calibradas com documentos reais (enunciado, rubrica, edital, instruções de journal) e com o feedback que você recebe depois de apresentar. O sistema mede isso (recall e precisão) e aprende as preferências reais.

## 5. Ordem de implantação (mesmo método do KF: mapear, aprovar, instalar, pilotar, substituir)
1. **X01–X03:** snapshot, mapeamento (sua triagem, o REP antigo, as skills de slides de cada frente, as áreas) e GATE.
2. **S01:** ferramentas e instalação. Você já vê um .pptx e PDFs reais gerados aí.
3. **S02:** kits e templates (USP/ICMC, Eldorado, startups, imóveis).
4. **S03:** piloto real de slides, com notas suas.
5. **S04:** triagem integrada e aviso de material faltante.
6. **S05:** REP absorvido e painéis calibrados.
7. **S06:** documento LaTeX real.
8. **S07:** KF passa a gerar .pptx/PDF com bibliografia obrigatória.
9. **S08:** pilotos em pitch, acadêmico e imóveis; substituição das skills antigas **só onde o Studio for igual ou melhor**, mantendo os comandos antigos como atalho.
10. **U01 (por área):** estudo, business, education, trabalho, imóveis passam ao padrão brief → especificação → Studio → revisão.

Nada das outras frentes é alterado antes da S08, e mesmo ali só com sua autorização item a item. O guard da KF continua vigiando.

## 6. Próximas partes
- **Manual (logo após o snapshot da X01):** escrito pelo Claude sobre a instalação real, no formato de fonte da Source Library (definições, procedimentos, exemplos), para a própria KF produzir um curso sobre o sistema.
- **Parte 2:** provas e listas (exam.cls + Moodle), diagramas (Mermaid, PlantUML, Graphviz), figuras científicas (Carnot, circuitos, circuitos quânticos, arquiteturas de redes), gráficos de negócio e de ML, notebooks executados e conferidos.
- **Parte 3:** resumos e posts (Medium, redes sociais), roteiros (vídeo-aula, explicação de código, defesa), animações (Manim, CSS/JS), landing pages, one-page e protótipos de SaaS, mockups (HTML importável no Figma via plugin).
- **Entre partes:** o `PART1_REPORT.md` e o `script_requests.md` que o Gemini acumula vêm para o Claude. Ajustes de script são feitos aqui, testados e devolvidos.

## 7. O que já foi verificado aqui antes de chegar a você
- 11 testes automáticos passando: slides, templates pptx/potx, Beamer, LaTeX, fontes, revisão e snapshot.
- Deck de exemplo com os 22 arquétipos renderizado e inspecionado visualmente (pptx e Beamer).
- Apostila de exemplo compilada com caixas de definição e código.
- O lint pegou, de propósito: `50%` sem escape, citação inexistente, ficha que resumiu demais, achado de revisão com localização inexistente e número divergente entre slides.
