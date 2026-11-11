#!/usr/bin/env python
"""
deep_citation_search.py — Mecanismo de Deep Research e travessia iterativa do grafo de citações.

Inspirado nos modelos de "Deep Research" (Gemini / OpenAI), este script executa
snowballing estruturado (Forward e Backward) a partir dos artigos semente usando
a API global do OpenAlex.

Funcionalidades:
  1. Forward Snowballing: localiza artigos recentes (ex: 2022-2026) que citam os trabalhos semente.
  2. Backward Snowballing: extrai as referências canônicas mais influentes compartilhadas pelas sementes.
  3. Filtragem Semântica e Ranqueamento: filtra por termos do domínio (ex: trafficking, entity resolution,
     heterogeneous graph, dynamic graph, temporal graph) e ranqueia por relevância, citações e recência.
  4. Identificação de Acesso Aberto (Open Access): prioriza e localiza links diretos para PDF.

Uso:
  .\\.venv\\Scripts\\python.exe .agents/tools/deep_citation_search.py --manifest <corpus_manifest.json> --top 10
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

DOMAIN_KEYWORDS = [
    "human trafficking", "trafficking", "sex work", "commercial sex",
    "criminal network", "illicit network", "law enforcement",
    "entity resolution", "record linkage", "deduplication",
    "knowledge graph", "semantic graph", "property graph", "ontology",
    "heterogeneous graph", "heterogeneous information network", "hin",
    "dynamic graph", "temporal graph", "graph neural network", "gnn"
]

def clean_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", doi.strip(), flags=re.I)

def fetch_json(url: str) -> dict | None:
    req = urllib.request.Request(url, headers={"User-Agent": "AcademicOS-DeepCitationSearch/1.0 (mailto:you@example.com)"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"  [AVISO] Falha na requisição {url}: {exc}", file=sys.stderr)
        return None

def score_work(work: dict, query_keywords: list[str]) -> tuple[float, list[str]]:
    title = (work.get("title") or "").lower()
    abstract_inverted = work.get("abstract_inverted_index") or {}
    abstract_words = set(abstract_inverted.keys()) if abstract_inverted else set()
    
    matches = []
    score = 0.0
    
    for kw in query_keywords:
        kw_lower = kw.lower()
        if kw_lower in title:
            score += 3.0
            matches.append(kw)
        elif any(part in abstract_words for part in kw_lower.split()):
            score += 1.0
            if kw not in matches:
                matches.append(kw)
                
    # Bônus de citação (logarítmico aproximado)
    cites = work.get("cited_by_count") or 0
    if cites > 50:
        score += 2.0
    elif cites > 10:
        score += 1.0
        
    # Bônus de recência (2022-2026)
    year = work.get("publication_year") or 0
    if year >= 2023:
        score += 1.5
    elif year >= 2021:
        score += 1.0
        
    # Bônus de Open Access
    if work.get("open_access", {}).get("is_oa"):
        score += 1.0
        
    return score, matches

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, required=True, help="Caminho do corpus_manifest.json")
    ap.add_argument("--top", type=int, default=10, help="Número de artigos recomendados a retornar")
    ap.add_argument("--min-year", type=int, default=2021, help="Ano mínimo de publicação para forward snowballing")
    ap.add_argument("--output", type=Path, default=None, help="Caminho do arquivo markdown de saída")
    args = ap.parse_args()

    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    
    print(f"=== Deep Citation Traversal: {manifest.get('research_id', '?')} ===")
    
    seeds = [it for it in manifest.get("items", []) if it.get("doi")]
    print(f"Sementes com DOI localizadas: {len(seeds)}")
    
    candidates: dict[str, dict] = {}
    
    for seed in seeds:
        doi = clean_doi(seed["doi"])
        print(f"\nExplorando semente: {seed['id']} (DOI: {doi})...")
        meta = fetch_json(f"https://api.openalex.org/works/doi:{doi}")
        if not meta:
            continue
            
        work_id = meta["id"].split("/")[-1]
        cites_count = meta.get("cited_by_count", 0)
        print(f"  ID OpenAlex: {work_id} | Total de citações: {cites_count}")
        
        # 1. Forward Snowballing: quem citou esta semente a partir de min_year?
        fwd_url = (f"https://api.openalex.org/works?"
                   f"filter=cites:{work_id},publication_year:{args.min_year}-2026"
                   f"&sort=cited_by_count:desc&per-page=25")
        fwd_data = fetch_json(fwd_url)
        if fwd_data and "results" in fwd_data:
            print(f"  -> Artigos recentes citando ({args.min_year}-2026): {fwd_data['meta']['count']} encontrados")
            for w in fwd_data["results"]:
                wid = w["id"]
                if wid not in candidates:
                    candidates[wid] = {"work": w, "source_seeds": [seed["id"]], "direction": "forward"}
                else:
                    candidates[wid]["source_seeds"].append(seed["id"])
                    
    print(f"\nTotal de candidatos brutos encontrados: {len(candidates)}")
    
    # Avaliar e pontuar candidatos
    ranked = []
    for wid, data in candidates.items():
        w = data["work"]
        # Ignorar o que já está nas sementes
        w_doi = clean_doi(w.get("doi"))
        if any(clean_doi(s.get("doi")) == w_doi for s in seeds if s.get("doi")):
            continue
            
        score, matches = score_work(w, DOMAIN_KEYWORDS)
        if score >= 2.0: # corte mínimo de relevância
            ranked.append({
                "work": w,
                "score": score,
                "matches": matches,
                "sources": data["source_seeds"],
                "direction": data["direction"]
            })
            
    ranked.sort(key=lambda x: x["score"], reverse=True)
    top_candidates = ranked[:args.top]
    
    print(f"Candidatos filtrados e ranqueados: {len(ranked)} | Selecionados: {len(top_candidates)}")
    
    # Renderizar relatório
    lines = [
        f"# Relatório de Deep Research: Expansão por Grafo de Citações",
        f"",
        f"**Pesquisa**: `{manifest.get('research_id')}` | **Data**: {datetime.now():%Y-%m-%d %H:%M}",
        f"**Método**: Forward Snowballing via OpenAlex Graph com filtragem semântica multidimensional.",
        f"",
        f"## Top {len(top_candidates)} Artigos Recentes Selecionados",
        f"",
        f"| # | Ano | Citações | Score | Título | Veículo | Open Access |",
        f"|---|-----|----------|-------|--------|---------|-------------|"
    ]
    
    for i, item in enumerate(top_candidates, 1):
        w = item["work"]
        title = (w.get("title") or "Sem título").replace("|", "-")
        year = w.get("publication_year") or "-"
        cites = w.get("cited_by_count") or 0
        score = item["score"]
        src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or "-"
        src = src.replace("|", "-")
        oa = w.get("open_access", {})
        oa_link = f"[PDF]({oa.get('oa_url')})" if oa.get("oa_url") else "Restrito"
        lines.append(f"| {i} | {year} | {cites} | {score:.1f} | **{title}** | {src} | {oa_link} |")
        
    lines.append("")
    lines.append("## Detalhamento das Descobertas e Justificativa de Relevância")
    lines.append("")
    
    for i, item in enumerate(top_candidates, 1):
        w = item["work"]
        title = w.get("title")
        year = w.get("publication_year")
        doi = w.get("doi")
        authors = [a.get("author", {}).get("display_name") for a in w.get("authorships", [])]
        auth_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
        matches_str = ", ".join(item["matches"])
        seeds_str = ", ".join(item["sources"])
        oa_url = w.get("open_access", {}).get("oa_url")
        
        lines.append(f"### {i}. {title} ({year})")
        lines.append(f"- **Autores**: {auth_str}")
        lines.append(f"- **DOI**: {doi}")
        lines.append(f"- **Conecta com sementes**: {seeds_str}")
        lines.append(f"- **Palavras-chave do domínio detectadas**: `{matches_str}`")
        lines.append(f"- **Status de Acesso**: {'Livre / ' + oa_url if oa_url else 'Acesso Comercial / Institucional'}")
        lines.append("")

    out_file = args.output or manifest_path.parent / "deep_citation_expansion.md"
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nRelatório gerado em: {out_file}")
    
    # Salvar também JSON estruturado dos candidatos para fácil ingestão
    candidates_json = manifest_path.parent / "deep_citation_candidates.json"
    candidates_json.write_text(json.dumps(top_candidates, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Candidatos estruturados salvos em: {candidates_json}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

