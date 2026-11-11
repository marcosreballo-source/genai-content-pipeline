---
name: workflow-python-env
description: >-
  Use this skill to create and manage the central Python virtual environment for the semester using uv. Handles Zscaler proxy bypass automatically.
---

# Workflow: Inicializar Ambiente Python do Semestre

## Quando usar
No início de cada semestre ou quando o pipeline de automação reclamar de falta de pacotes/versão de Python ou quando houver a necessidade de isolar dependências para o workspace atual.

## Passos

1. **Definição de Versão**: Acorde com o usuário qual versão do Python será o padrão do semestre (ex: 3.12).
2. **Criação do VENV via UV**: Na raiz do semestre (ex: `S04/`), execute o comando para criar o ambiente virtual garantindo a versão desejada:
   `uv venv --python 3.12 .venv`
3. **Ativação e Instalação Base**: O agente deve instalar os pacotes essenciais (ex: `google-antigravity`, `pandas`, `jupyter`) no recém-criado ambiente. É **OBRIGATÓRIO** aplicar a regra de bypass do Zscaler:
   `uv pip install google-antigravity jupyter pandas --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org`
4. **Arquivo de Requisitos**: Gere um arquivo `requirements.txt` na raiz do semestre rodando `uv pip freeze`, para que todo o ambiente esteja documentado de forma reproduzível.
5. **Atualização de Scripts**: A partir deste momento, todos os scripts locais criados (como o script CEP) devem utilizar o interpretador deste `.venv` (ex: invocando `.venv\Scripts\python.exe` no Windows ou definindo o path adequadamente) em vez do Python global do sistema.
