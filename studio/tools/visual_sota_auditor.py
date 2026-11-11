#!/usr/bin/env python3
"""studio/tools/visual_sota_auditor.py: Auditoria autônoma do ciclo de 60 dias corridos do Estado da Arte (SOTA)
para as 26 bibliotecas de visualização de dados e diagramação do workspace.

Comandos:
  check --library <lib>          Verifica se a revisão SOTA da biblioteca tem < 60 dias corridos (Exit Code 2 se expirada)
  check-all                      Audita a vigência de todas as 26 bibliotecas do catálogo
  recommend --category <cat>     Retorna a biblioteca SOTA número 1 recomendada para a categoria visual
  update --library <lib> --version <v> [--date YYYY-MM-DD] [--notes "..."]   Atualiza a data de revisão SOTA
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
import yaml

REGISTRY_PATH = Path(__file__).resolve().parent / "visual_sota_registry.yaml"
TTL_DAYS = 60

DEFAULT_CATALOG = {
    "ttl_days": 60,
    "categories": {
        "scientific_static_plot": "Matplotlib",
        "statistical_distribution": "Seaborn",
        "network_graph_topology": "NetworkX",
        "card_composite_vector": "Pillow",
        "interactive_scientific": "plotly.py",
        "declarative_statistical_py": "Altair",
        "web_custom_dom_svg": "D3",
        "web_declarative_grammar": "Vega-Lite",
        "web_enterprise_dashboard": "ECharts",
        "web_geospatial_map": "Leaflet",
        "web_dynamic_network_3d": "vis.js",
        "software_architecture_flow": "Mermaid",
        "directed_automata_dag": "Graphviz",
        "mathematical_vector_tex": "TikZ",
        "r_grammar_of_graphics": "ggplot2",
    },
    "libraries": {
        "D3": {"ecosystem": "js", "pkg": "d3", "last_sota_review_date": "2026-11-04", "sota_version": "7.9.0", "recommended_for": "Visualizações customizadas de dados vinculadas ao DOM/SVG e transformações geométricas"},
        "plotly.js": {"ecosystem": "js", "pkg": "plotly.js-dist-min", "last_sota_review_date": "2026-11-04", "sota_version": "2.35.2", "recommended_for": "Gráficos científicos interativos e dashboards analíticos web"},
        "Vega": {"ecosystem": "js", "pkg": "vega", "last_sota_review_date": "2026-11-04", "sota_version": "5.30.0", "recommended_for": "Gramática declarativa JSON completa para visualizações estáticas e interativas"},
        "Vega-Lite": {"ecosystem": "js", "pkg": "vega-lite", "last_sota_review_date": "2026-11-04", "sota_version": "5.21.0", "recommended_for": "Gráficos declarativos concisos de alta velocidade e fidelidade estatística"},
        "nivo": {"ecosystem": "js", "pkg": "@nivo/core", "last_sota_review_date": "2026-11-04", "sota_version": "0.88.0", "recommended_for": "Componentes de gráficos altamente customizáveis em aplicações React + D3"},
        "Victory": {"ecosystem": "js", "pkg": "victory", "last_sota_review_date": "2026-11-04", "sota_version": "37.3.2", "recommended_for": "Visualizações responsivas e mobile-friendly baseadas em componentes React"},
        "Chart.js": {"ecosystem": "js", "pkg": "chart.js", "last_sota_review_date": "2026-11-04", "sota_version": "4.4.6", "recommended_for": "Prototipagem rápida e gráficos Canvas limpos para projetos leves"},
        "vis.js": {"ecosystem": "js", "pkg": "vis-network", "last_sota_review_date": "2026-11-04", "sota_version": "9.1.9", "recommended_for": "Grafos de rede dinâmicos, timelines e conjuntos de dados complexos em larga escala"},
        "Highcharts": {"ecosystem": "js", "pkg": "highcharts", "last_sota_review_date": "2026-11-04", "sota_version": "11.4.8", "recommended_for": "Dashboards executivos polidos de padrão corporativo"},
        "Google Charts": {"ecosystem": "js", "pkg": "google-charts", "last_sota_review_date": "2026-11-04", "sota_version": "current", "recommended_for": "Visualizações web rápidas integradas ao ecossistema Google"},
        "Leaflet": {"ecosystem": "js", "pkg": "leaflet", "last_sota_review_date": "2026-11-04", "sota_version": "1.9.4", "recommended_for": "Mapas interativos e visualização de dados geoespaciais"},
        "ECharts": {"ecosystem": "js", "pkg": "echarts", "last_sota_review_date": "2026-11-04", "sota_version": "5.5.1", "recommended_for": "Visualizações interativas de grandes volumes de dados e matrizes multidimensionais"},
        "Mermaid": {"ecosystem": "js", "pkg": "@mermaid-js/mermaid-cli", "last_sota_review_date": "2026-11-04", "sota_version": "11.4.0", "recommended_for": "Fluxogramas, diagramas de sequência, estados e arquitetura"},
        "Bokeh": {"ecosystem": "python", "pkg": "bokeh", "last_sota_review_date": "2026-11-04", "sota_version": "3.6.1", "recommended_for": "Visualizações interativas para navegadores web a partir do Python"},
        "Dash": {"ecosystem": "python", "pkg": "dash", "last_sota_review_date": "2026-11-04", "sota_version": "2.18.2", "recommended_for": "Aplicações analíticas e dashboards web em Python (Flask + Plotly + React)"},
        "plotly.py": {"ecosystem": "python", "pkg": "plotly", "last_sota_review_date": "2026-11-04", "sota_version": "5.24.1", "recommended_for": "Visualizações científicas interativas e exportação estática via Kaleido"},
        "Altair": {"ecosystem": "python", "pkg": "altair", "last_sota_review_date": "2026-11-04", "sota_version": "5.4.1", "recommended_for": "Visualização estatística declarativa em Python baseada em Vega-Lite"},
        "mpld3": {"ecosystem": "python", "pkg": "mpld3", "last_sota_review_date": "2026-11-04", "sota_version": "0.5.10", "recommended_for": "Ponte de figuras Matplotlib para interatividade D3 no navegador"},
        "Matplotlib": {"ecosystem": "python", "pkg": "matplotlib", "last_sota_review_date": "2026-11-04", "sota_version": "3.9.2", "recommended_for": "Gráficos científicos estáticos de qualidade de publicação (300+ DPI) e geometria 3D"},
        "Seaborn": {"ecosystem": "python", "pkg": "seaborn", "last_sota_review_date": "2026-11-04", "sota_version": "0.13.2", "recommended_for": "Visualização estatística de alto nível e paletas perceptualmente uniformes"},
        "NetworkX": {"ecosystem": "python", "pkg": "networkx", "last_sota_review_date": "2026-11-04", "sota_version": "3.4.2", "recommended_for": "Modelagem e plotagem de grafos, redes logísticas e topologias de qubits"},
        "Pillow": {"ecosystem": "python", "pkg": "pillow", "last_sota_review_date": "2026-11-04", "sota_version": "11.0.0", "recommended_for": "Síntese de cards tipográficos, badges, avatares e composição de imagens"},
        "Chaco": {"ecosystem": "python", "pkg": "chaco", "last_sota_review_date": "2026-11-04", "sota_version": "5.1.1", "recommended_for": "Plotagem científica interativa com zoom/pan em aplicações Python"},
        "ggplot2": {"ecosystem": "r", "pkg": "ggplot2", "last_sota_review_date": "2026-11-04", "sota_version": "3.5.1", "recommended_for": "Análise exploratória de dados e gráficos estáticos em R sob a Grammar of Graphics"},
        "Graphviz": {"ecosystem": "system", "pkg": "graphviz", "last_sota_review_date": "2026-11-04", "sota_version": "12.2.0", "recommended_for": "Grafos direcionados hierárquicos (DAGs), máquinas de estado e árvores sintáticas"},
        "TikZ": {"ecosystem": "tex", "pkg": "pgf", "last_sota_review_date": "2026-11-04", "sota_version": "3.1.10", "recommended_for": "Diagramas vetoriais matemáticos puros e esquemas formais em LaTeX"},
    },
}


def load_registry(custom_path: Path | None = None) -> dict:
    p = custom_path or REGISTRY_PATH
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.safe_dump(DEFAULT_CATALOG, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def check_lib(reg: dict, lib: str, today: dt.date) -> tuple[bool, int, dict]:
    libs = reg.get("libraries", {})
    match = next((k for k in libs if k.lower() == lib.lower()), None)
    if not match:
        raise SystemExit(f"ERRO: Biblioteca '{lib}' não registrada no catálogo SOTA.")
    info = libs[match]
    last_str = info.get("last_sota_review_date")
    if not last_str:
        return False, 9999, info
    last_date = dt.date.fromisoformat(str(last_str))
    days = (today - last_date).days
    ttl = int(reg.get("ttl_days", TTL_DAYS))
    return (0 <= days < ttl), days, info


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", help="Caminho opcional de registry YAML (para testes)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_chk = sub.add_parser("check")
    p_chk.add_argument("--library", required=True)
    sub.add_parser("check-all")
    p_rec = sub.add_parser("recommend")
    p_rec.add_argument("--category", required=True)
    p_upd = sub.add_parser("update")
    p_upd.add_argument("--library", required=True)
    p_upd.add_argument("--version", required=True)
    p_upd.add_argument("--date", help="Data ISO YYYY-MM-DD (padrão: hoje)")
    p_upd.add_argument("--notes", default="")
    args = ap.parse_args()

    reg_path = Path(args.registry) if args.registry else REGISTRY_PATH
    reg = load_registry(reg_path)
    today = dt.date.today()

    if args.cmd == "check":
        ok, days, info = check_lib(reg, args.library, today)
        if not ok:
            print(
                f"[SOTA EXPIRED - EXIT 2] Biblioteca '{args.library}' revisada há {days} dias (limite={TTL_DAYS} dias). "
                "Realize estudo do estado da arte e atualize via 'visual_sota_auditor.py update'.",
                file=sys.stderr,
            )
            return 2
        print(
            f"[SOTA VALID] {args.library} (v{info.get('sota_version')}, ecossistema={info.get('ecosystem')}) — "
            f"revisada há {days} dia(s) (restam {TTL_DAYS - days}d). Uso: {info.get('recommended_for')}"
        )
        return 0

    if args.cmd == "check-all":
        expired = []
        for name in reg.get("libraries", {}):
            ok, days, info = check_lib(reg, name, today)
            status = "OK" if ok else "EXPIRED"
            print(f"  [{status:7s}] {name:15s} | v{str(info.get('sota_version')):8s} | {days:3d}/{TTL_DAYS}d | {info.get('recommended_for')}")
            if not ok:
                expired.append(name)
        return 2 if expired else 0

    if args.cmd == "recommend":
        cats = reg.get("categories", {})
        lib = cats.get(args.category)
        if not lib:
            print(f"Categorias disponíveis: {', '.join(cats.keys())}", file=sys.stderr)
            return 1
        ok, days, info = check_lib(reg, lib, today)
        print(f"RECOMENDAÇÃO SOTA [{args.category}] -> {lib} (v{info.get('sota_version')}, {days}d): {info.get('recommended_for')}")
        return 0 if ok else 2

    if args.cmd == "update":
        libs = reg.get("libraries", {})
        match = next((k for k in libs if k.lower() == args.library.lower()), args.library)
        target_date = args.date or str(today)
        libs.setdefault(match, {})["last_sota_review_date"] = target_date
        libs[match]["sota_version"] = args.version
        if args.notes:
            libs[match]["recommended_for"] = args.notes
        reg_path.write_text(yaml.safe_dump(reg, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(f"[SOTA UPDATED] {match} atualizado para v{args.version} com data {target_date}.")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())

