# Regra: Fontes Confiáveis (Bypass de Zscaler)

Sempre que o agente precisar instalar pacotes Python via `pip` ou `uv pip install` neste workspace, ele **DEVE OBRIGATORIAMENTE** adicionar as flags de trusted-host para evitar erros de certificado causados pelo proxy corporativo (Zscaler).

Flags obrigatórias:
`--trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org`

Exemplo de uso:
`uv pip install google-antigravity --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org`

**NUNCA** execute uma instalação de pacote sem essas garantias neste workspace, caso contrário, falhará com erros de SSL.
