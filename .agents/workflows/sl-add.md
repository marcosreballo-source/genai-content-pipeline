---
description: Adiciona uma fonte à bibliografia oficial (Source Library) e a processa trecho a trecho com fichas fiéis. Uso do Studio.
---
0. Ler `<AGENT_DIR>/rules/studio-core.md`.
1. Skill **sl-ingest**: registre e divida (ou importe do pipeline de triagem).
2. Pergunte ao usuário se quer processar a fonte toda ou só capítulos ou páginas (informe o número de rodadas estimado). Para trechos específicos, processe só os ids pedidos.
3. Repita, uma ficha por rodada: `python studio/scripts/studio_next.py --source <SRC>`, skill **sl-extract**, `sl_sources.py validate <SRC> --chunk <C>`. A cada 5 fichas, mostre o progresso (`sl_sources.py status <SRC>`).
4. No fim: `sl_sources.py validate <SRC>`, `sl_sources.py index` e, se a fonte atendia um pedido, `sl_sources.py fulfill <REQ> --source <SRC>`.
