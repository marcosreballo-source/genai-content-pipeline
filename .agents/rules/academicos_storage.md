# Padrões de Armazenamento do AcademicOS (Taxonomia de Diretórios)

Todos os agentes do AcademicOS DEVEM respeitar estritamente a hierarquia de diretórios abaixo ao ler ou salvar arquivos na memória. É expressamente PROIBIDO salvar qualquer artefato fora desta estrutura ou pular o nível de `{disciplina_id}`.

## Estrutura Obrigatória

- **Conhecimento (DKB)**: `_academicos_memory\discipline_knowledge_base\{disciplina_id}\`
- **Estratégia (ASB)**: `_academicos_memory\academic_success_blueprint\{disciplina_id}\`
- **Entregas (Trabalhos/Projetos)**: `_academicos_memory\assignment_repository\{disciplina_id}\{assignment_id}\`
  - Arquivos de planejamento e rascunhos ficam na raiz do assignment.
  - O código-fonte finalizado, PDFs e zips que serão submetidos ao professor DEVEM ser copiados para a subpasta obrigatória `\entregaveis_finais\`. Isso cria um histórico rastreável blindado contra edições no projeto ativo.
- **Avaliações (Revisões/Provas)**: `_academicos_memory\evaluation_repository\{disciplina_id}\{evaluation_id}\`
- **Pesquisas Acadêmicas**: `_academicos_memory\research_repository\{disciplina_id}\{research_id}\`

## Regras de Versionamento
- Relatórios iterativos (como revisões de código, avaliação textual e feedbacks) NUNCA devem ser sobrescritos.
- Utilize o sufixo `_v{N}` (ex: `review_report_v1.md`, `review_report_v2.md`) para manter o histórico de melhorias da etapa.
- **Imutabilidade de Pacotes de Entrega (`.zip`) e Entregáveis Consolidados**:
  - É terminantemente PROIBIDO sobrescrever pacotes de submissão (`.zip`) ou arquivos de entrega anteriores, mesmo quando a versão anterior contiver erros que estão sendo corrigidos.
  - Sempre que um pacote já existir (ex: `entrega_exercicio3.zip` ou `entrega_exercicio2_v1.zip`), qualquer nova geração DEVE criar um novo arquivo iterando o número de versão (ex: `entrega_exercicio3_v2.0.zip`, `entrega_exercicio3_v3.0.zip`), preservando intactas todas as versões anteriores no diretório da atividade, em `06_delivery/` e em `\entregaveis_finais\`.
