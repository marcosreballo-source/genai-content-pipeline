# Source Library (bibliografia oficial)

- `ledger.yaml`: todas as fontes (`SRC-...`) e os pedidos de bibliografia (`REQ-...`).
- `<SRC>/chunks/`: trechos (`C0001.pdf` + `.txt`, ou importados do seu pipeline de triagem).
- `<SRC>/cards/`: fichas fiéis (uma por trecho).
- `concept_index.json`: índice de conceitos gerado por `sl_sources.py index`.

Fluxo: `/sl-add` (registrar e fichar) → `/sl-coverage` (o que falta para um curso ou material) → produção com `sl_sources.py pack`.
