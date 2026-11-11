#!/usr/bin/env python3
"""mf_deck.py: decks de alta qualidade a partir de especificações YAML (Material Factory / Studio).

O agente NUNCA escreve PowerPoint diretamente. Ele preenche campos curtos em YAML (um "arquétipo" por slide),
e este script valida, diagrama, ajusta o texto ao espaço e gera o .pptx (e o PDF/PNGs de prévia).

Fluxo de um job (pasta qualquer, ex.: studio/jobs/2026-10-02_status-eldorado/):
  brief.yaml   -> o quê, para quem, objetivo, duração, blueprint, estilo (kit ou template)
  outline.yaml -> 1 linha por slide: id, seção, arquétipo, mensagem-chave
  plan.yaml    -> gerado por 'plan': divide os slides em unidades (U01, U02...) que cabem numa rodada
  spec/U01.yaml ...  -> conteúdo dos slides da unidade (escrito pelo agente, uma unidade por rodada)
  assets/      -> imagens, dados
  build/       -> deck.pptx, deck.pdf, previews/, contact_sheet.png, qa_report.md, speaker_notes.md

Comandos:
  new <job> --blueprint <id> [--kit default | --template <id>]
  archetypes [--md]                 catálogo de arquétipos e limites (fonte da verdade)
  plan <job> [--per-unit 6]         valida o outline contra o blueprint e cria as unidades
  validate <job> [--unit U02] [--complete]
  build <job> [--kit X | --template Y] [--out build/deck.pptx]
  preview <job>                     PDF + PNG por slide + contact sheet (precisa do LibreOffice)
  qa <job>                          relatório consolidado (validação + ajuste de texto + densidade)
  notes <job>                       roteiro de fala (speaker notes) em Markdown
  inspect-template <arquivo.pptx|.potx> --id <id>   registra um template corporativo
  kit-check <kit_id>                contraste e campos do kit
"""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from studio_common import (STUDIO, UNIT_MAX_WORDS, SOFFICE_PATHS, Issues, dump_yaml, find_exe,  # noqa: E402
                           load_yaml, words)

try:
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.dml.color import RGBColor
    from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
    from pptx.enum.shapes import MSO_SHAPE, PP_PLACEHOLDER
    from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
    from pptx.oxml.ns import qn
    from pptx.util import Emu, Inches, Pt
except ImportError:  # pragma: no cover
    print("ERRO: python-pptx não instalado. Rode: pip install python-pptx", file=sys.stderr)
    sys.exit(2)

# ----------------------------------------------------------------------------------------------------------
# 1. Catálogo de arquétipos (fonte da verdade dos limites)
# ----------------------------------------------------------------------------------------------------------
S = lambda n: ("str", n)                                   # noqa: E731
LST = lambda mn, mx, item: ("list", mn, mx, item)          # noqa: E731
OBJ = lambda fields, req=(): ("obj", fields, list(req))    # noqa: E731
BUL = lambda n: ("bullet", n)                              # noqa: E731

COMMON = {"id": S(12), "archetype": S(20), "notes": ("words", 180), "sources": LST(0, 8, S(120)),
          "hidden": ("bool",)}

ARCH = {
    "title": dict(use="Capa: título, subtítulo, autor, evento e data.",
                  req=["title"], fields={"title": S(70), "subtitle": S(120), "author": S(80), "event": S(80),
                                         "date": S(40)}),
    "agenda": dict(use="Roteiro da apresentação (3 a 7 itens).",
                   req=["items"], fields={"title": S(60), "items": LST(2, 7, S(70))}),
    "section": dict(use="Divisória de seção (fundo escuro).",
                    req=["title"], fields={"number": S(4), "title": S(60), "subtitle": S(120)}),
    "bullets": dict(use="Título-mensagem + até 6 tópicos; 'takeaway' opcional em destaque no rodapé.",
                    req=["title", "bullets"], fields={"title": S(90), "bullets": LST(1, 6, BUL(120)),
                                                      "takeaway": S(120)}),
    "statement": dict(use="Uma frase forte, sozinha no slide (tese, insight, problema).",
                      req=["statement"], fields={"statement": S(160), "support": S(140)}),
    "big_number": dict(use="Um número que conta a história (ex.: '73%').",
                       req=["value", "label"], fields={"title": S(90), "value": S(12), "label": S(80),
                                                       "context": S(140)}),
    "kpis": dict(use="2 a 4 indicadores lado a lado.",
                 req=["items"], fields={"title": S(90), "items": LST(2, 4, OBJ({"value": S(10), "label": S(60),
                                                                                  "delta": S(24)},
                                                                                 ["value", "label"]))}),
    "two_column": dict(use="Dois blocos paralelos (ex.: problema/solução, teoria/prática).",
                       req=["title", "left", "right"],
                       fields={"title": S(90),
                               "left": OBJ({"heading": S(40), "bullets": LST(1, 5, BUL(100))}, ["bullets"]),
                               "right": OBJ({"heading": S(40), "bullets": LST(1, 5, BUL(100))}, ["bullets"])}),
    "comparison": dict(use="2 ou 3 opções comparadas; 'highlight' marca a recomendada.",
                       req=["title", "columns"],
                       fields={"title": S(90), "columns": LST(2, 3, OBJ({"heading": S(40),
                                                                            "items": LST(1, 5, S(80)),
                                                                            "highlight": ("bool",)},
                                                                           ["heading", "items"]))}),
    "image": dict(use="Imagem/figura com legenda; layout full, left ou right (left/right aceitam bullets).",
                  req=["image"], fields={"title": S(90), "image": ("path",), "caption": S(140), "source": S(100),
                                         "layout": ("enum", ["full", "left", "right"]),
                                         "bullets": LST(0, 4, BUL(100))}),
    "chart": dict(use="Gráfico nativo e editável (bar, column, stacked_column, line, pie, doughnut).",
                  req=["title", "chart"],
                  fields={"title": S(90), "takeaway": S(140), "source": S(100),
                          "chart": OBJ({"type": ("enum", ["bar", "column", "stacked_column", "line", "pie",
                                                          "doughnut"]),
                                        "categories": LST(1, 12, S(30)),
                                        "series": LST(1, 4, OBJ({"name": S(30), "values": ("numbers",)},
                                                                ["name", "values"])),
                                        "unit": S(12), "number_format": S(20), "highlight": S(30)},
                                       ["type", "categories", "series"])}),
    "table": dict(use="Tabela compacta (até 6 colunas x 7 linhas).",
                  req=["title", "columns", "rows"],
                  fields={"title": S(90), "columns": LST(2, 6, S(24)), "rows": LST(1, 7, LST(1, 6, S(40))),
                          "highlight_row": ("int",), "source": S(100)}),
    "timeline": dict(use="Marcos no tempo (2 a 6).",
                     req=["title", "events"],
                     fields={"title": S(90), "events": LST(2, 6, OBJ({"when": S(16), "label": S(40),
                                                                         "detail": S(90)}, ["when", "label"]))}),
    "process": dict(use="Etapas de um processo/método (2 a 6).",
                    req=["title", "steps"],
                    fields={"title": S(90), "steps": LST(2, 6, OBJ({"label": S(30), "detail": S(90)},
                                                                     ["label"]))}),
    "quote": dict(use="Citação/depoimento com autor.",
                  req=["quote"], fields={"quote": S(220), "author": S(60), "role": S(80)}),
    "code": dict(use="Trecho de código (até 18 linhas x 90 colunas).",
                 req=["title", "code"], fields={"title": S(90), "language": S(20), "code": ("code", 18, 90),
                                                "caption": S(120)}),
    "equation": dict(use="Equação em LaTeX (subconjunto mathtext no pptx; LaTeX completo no Beamer).",
                     req=["title", "latex"], fields={"title": S(90), "latex": ("latex",),
                                                     "explanation": LST(0, 3, S(110))}),
    "diagram": dict(use="Diagrama a partir de código Mermaid ou de uma imagem pronta.",
                    req=["title"], fields={"title": S(90), "mermaid": ("code", 40, 120), "image": ("path",),
                                           "caption": S(140)}),
    "team": dict(use="Pessoas (1 a 6) com papel; foto opcional.",
                 req=["members"], fields={"title": S(90), "members": LST(1, 6, OBJ({"name": S(40), "role": S(50),
                                                                                      "detail": S(80),
                                                                                      "photo": ("path",)},
                                                                                     ["name"]))}),
    "closing": dict(use="Encerramento/pedido (ask, CTA, próximos passos).",
                    req=["title"], fields={"title": S(70), "message": S(160), "items": LST(0, 4, S(80)),
                                           "contact": S(120)}),
    "references": dict(use="Referências (até 8), em formato já pronto.",
                       req=["items"], fields={"title": S(60), "items": LST(1, 8, S(220))}),
    "qa": dict(use="Slide de perguntas.", req=[], fields={"title": S(40), "contact": S(120)}),
}
DARK = {"title", "section", "closing", "qa"}
TYPICAL_WORDS = {"title": 25, "agenda": 40, "section": 15, "bullets": 85, "statement": 35, "big_number": 35,
                 "kpis": 45, "two_column": 95, "comparison": 90, "image": 45, "chart": 70, "table": 90,
                 "timeline": 80, "process": 80, "quote": 50, "code": 110, "equation": 50, "diagram": 70,
                 "team": 60, "closing": 50, "references": 120, "qa": 10}


def check_value(spec, val, where, iss, job):
    kind = spec[0]
    if kind == "str":
        if not isinstance(val, (str, int, float)):
            iss.err(where, "deve ser texto")
        elif len(str(val)) > spec[1]:
            iss.err(where, f"{len(str(val))} caracteres (máx. {spec[1]}); encurte ou divida o slide")
    elif kind == "words":
        if not isinstance(val, str):
            iss.err(where, "deve ser texto")
        elif words(val) > spec[1]:
            iss.err(where, f"{words(val)} palavras (máx. {spec[1]})")
    elif kind == "bool":
        if not isinstance(val, bool):
            iss.err(where, "deve ser true/false")
    elif kind == "int":
        if not isinstance(val, int):
            iss.err(where, "deve ser inteiro")
    elif kind == "enum":
        if val not in spec[1]:
            iss.err(where, f"valor '{val}' inválido; use {spec[1]}")
    elif kind == "numbers":
        if not isinstance(val, list) or not all(isinstance(x, (int, float)) for x in val):
            iss.err(where, "deve ser lista de números")
    elif kind == "path":
        if not isinstance(val, str):
            iss.err(where, "deve ser caminho")
        elif job is not None and not resolve_asset(job, val):
            iss.err(where, f"arquivo não encontrado: {val} (procure em assets/ ou caminho relativo ao job)")
    elif kind == "code":
        if not isinstance(val, str):
            iss.err(where, "deve ser texto em bloco (|)")
        else:
            lines = val.rstrip("\n").split("\n")
            if len(lines) > spec[1]:
                iss.err(where, f"{len(lines)} linhas (máx. {spec[1]})")
            long = [i + 1 for i, l in enumerate(lines) if len(l) > spec[2]]
            if long:
                iss.warn(where, f"linhas com mais de {spec[2]} colunas: {long[:5]}")
    elif kind == "latex":
        if not isinstance(val, str) or not val.strip():
            iss.err(where, "LaTeX vazio")
        elif val.count("{") != val.count("}"):
            iss.err(where, "chaves { } desbalanceadas")
    elif kind == "bullet":
        if isinstance(val, str):
            check_value(("str", spec[1]), val, where, iss, job)
        elif isinstance(val, dict):
            check_value(("str", spec[1]), val.get("text", ""), where + ".text", iss, job)
            subs = val.get("sub", [])
            if not isinstance(subs, list) or len(subs) > 3:
                iss.err(where + ".sub", "até 3 sub-tópicos")
            else:
                for j, s in enumerate(subs):
                    check_value(("str", 100), s, f"{where}.sub[{j}]", iss, job)
        else:
            iss.err(where, "tópico deve ser texto ou {text, sub}")
    elif kind == "list":
        _, mn, mx, item = spec
        if not isinstance(val, list):
            iss.err(where, "deve ser lista")
            return
        if not (mn <= len(val) <= mx):
            iss.err(where, f"{len(val)} itens (permitido {mn} a {mx})")
        for i, v in enumerate(val):
            check_value(item, v, f"{where}[{i}]", iss, job)
    elif kind == "obj":
        _, fields, req = spec
        if not isinstance(val, dict):
            iss.err(where, "deve ser objeto")
            return
        for r in req:
            if r not in val or val[r] in (None, "", []):
                iss.err(where, f"campo obrigatório ausente: {r}")
        for k, v in val.items():
            if k not in fields:
                iss.warn(where, f"campo desconhecido ignorado: {k}")
            elif v is not None:
                check_value(fields[k], v, f"{where}.{k}", iss, job)


def validate_slide(sl, where, iss, job=None):
    a = sl.get("archetype")
    if a not in ARCH:
        iss.err(where, f"arquétipo '{a}' inexistente; veja 'mf_deck.py archetypes'")
        return
    spec = ARCH[a]
    fields = dict(COMMON, **spec["fields"])
    for r in ["id"] + spec["req"]:
        if r not in sl or sl[r] in (None, "", []):
            iss.err(where, f"campo obrigatório ausente: {r}")
    for k, v in sl.items():
        if k.startswith("_"):
            continue
        if k not in fields:
            iss.warn(where, f"campo '{k}' não existe em '{a}' e será ignorado")
        elif v is not None and k not in ("archetype",):
            check_value(fields[k], v, f"{where}.{k}", iss, job)
    if a == "diagram" and not (sl.get("mermaid") or sl.get("image")):
        iss.err(where, "diagram exige 'mermaid' ou 'image'")
    if a == "chart" and isinstance(sl.get("chart"), dict):
        ch = sl["chart"]
        n = len(ch.get("categories") or [])
        for i, s in enumerate(ch.get("series") or []):
            if isinstance(s, dict) and isinstance(s.get("values"), list) and len(s["values"]) != n:
                iss.err(f"{where}.chart.series[{i}]", f"{len(s['values'])} valores para {n} categorias")
        if ch.get("type") in ("pie", "doughnut") and len(ch.get("series") or []) > 1:
            iss.err(f"{where}.chart", "pizza/rosca aceita 1 série")
        if not sl.get("source"):
            iss.warn(where, "gráfico sem 'source': informe de onde vêm os dados")
    if a == "table" and isinstance(sl.get("rows"), list) and isinstance(sl.get("columns"), list):
        for i, r in enumerate(sl["rows"]):
            if isinstance(r, list) and len(r) != len(sl["columns"]):
                iss.err(f"{where}.rows[{i}]", f"{len(r)} células para {len(sl['columns'])} colunas")
    if a == "big_number" and not sl.get("sources") and not sl.get("context"):
        iss.warn(where, "número sem fonte/contexto: adicione 'sources' ou 'context'")
    if "[[PENDENTE" in str({k: v for k, v in sl.items() if not k.startswith("_")}):
        iss.warn(where, "contém [[PENDENTE...]]: dado/fonte ainda não fornecido (bloqueia o QA final)", "pending")
    wc = words({k: v for k, v in sl.items() if k not in ("id", "archetype", "notes", "sources")})
    if a in ("bullets", "two_column", "comparison") and wc > 75:
        iss.warn(where, f"slide denso ({wc} palavras); ideal ≤ 60. Considere dividir")


def resolve_asset(job, p):
    if not p:
        return None
    cand = [Path(p)] if Path(p).is_absolute() else [Path(job) / p, Path(job) / "assets" / p]
    for c in cand:
        if c.exists():
            return c
    return None


# ----------------------------------------------------------------------------------------------------------
# 2. Job: brief, outline, plano, unidades
# ----------------------------------------------------------------------------------------------------------
def load_blueprint(bid):
    if not bid:
        return None
    p = STUDIO / "formats/deck/blueprints" / f"{bid}.yaml"
    return load_yaml(p) if p.exists() else None


def load_slides(job, iss=None, complete=False):
    """Junta as unidades spec/U*.yaml na ordem do outline."""
    job = Path(job)
    outline = load_yaml(job / "outline.yaml", {"slides": []})
    order = [s.get("id") for s in outline.get("slides", [])]
    specs = {}
    for f in sorted((job / "spec").glob("U*.yaml")):
        data = load_yaml(f, {})
        for i, sl in enumerate(data.get("slides") or []):
            sid = sl.get("id")
            if sid in specs and iss:
                iss.err(f"{f.name}[{i}]", f"id repetido {sid}")
            sl["_unit"] = f.stem
            specs[sid] = sl
    ordered = [specs[i] for i in order if i in specs]
    extra = [s for k, s in specs.items() if k not in order]
    if iss:
        for s in extra:
            iss.warn(s.get("id", "?"), "slide não está no outline (vai ao final)")
        missing = [i for i in order if i not in specs]
        if missing:
            (iss.err if complete else iss.warn)("spec", f"{len(missing)} slide(s) do outline sem conteúdo: "
                                                        f"{', '.join(missing[:10])}")
        oarch = {s.get("id"): s.get("archetype") for s in outline.get("slides", [])}
        for s in ordered:
            if oarch.get(s.get("id")) and oarch[s["id"]] != s.get("archetype"):
                iss.warn(s["id"], f"arquétipo mudou do outline ({oarch[s['id']]}) para {s.get('archetype')}")
    return [s for s in ordered + extra if not s.get("hidden")]


BRIEF_TEMPLATE = """# brief.yaml: preencha com o usuário (no máximo 6 perguntas). Campos com * são obrigatórios.
title: ""            # * título de trabalho da apresentação
blueprint: {blueprint}   # * roteiro-base (lista: studio/formats/deck/blueprints/)
audience: ""         # * quem assiste (cargo, nível técnico, o que já sabe)
goal: ""             # * o que deve acontecer depois (decisão, aprovação, nota, investimento...)
duration_min: 10     # * tempo de fala
language: pt-BR
author: ""
event: ""
date: ""
backends: [pptx]     # pptx e/ou beamer
style:
  {style}
panel: ""            # painel de revisão (studio/review/panels/), vazio = o padrão do blueprint
sources: []          # IDs da Source Library (SRC-...) ou caminhos em assets/
constraints: {{}}      # ex.: {{max_slides: 12, required: [orcamento], notes: true}}
"""


def cmd_new(a):
    job = Path(a.job)
    if (job / "brief.yaml").exists():
        print(f"ERRO: {job}/brief.yaml já existe.", file=sys.stderr)
        return 2
    for d in ("spec", "assets", "build", "review"):
        (job / d).mkdir(parents=True, exist_ok=True)
    style = f"template: {a.template}" if a.template else f"kit: {a.kit}"
    (job / "brief.yaml").write_text(BRIEF_TEMPLATE.format(blueprint=a.blueprint or "", style=style),
                                    encoding="utf-8")
    bp = load_blueprint(a.blueprint)
    outline = {"slides": []}
    if bp:
        n = 1
        for sec in bp.get("sections", []):
            arches = sec.get("suggested_archetypes") or ["bullets"]
            k = (sec.get("slides") or [1])[0]
            for j in range(max(1, k)):
                outline["slides"].append({"id": f"SL-{n:02d}", "section": sec["id"],
                                          "archetype": arches[min(j, len(arches) - 1)],
                                          "message": f"<mensagem-chave: {sec.get('purpose', '')[:60]}>"})
                n += 1
    dump_yaml(outline, job / "outline.yaml")
    print(f"OK: job criado em {job}. Preencha brief.yaml; depois reescreva outline.yaml e rode 'plan'.")
    if a.blueprint and not bp:
        print(f"AVISO: blueprint '{a.blueprint}' não encontrado em formats/deck/blueprints/.")
    return 0


def cmd_plan(a):
    job = Path(a.job)
    iss = Issues()
    brief = load_yaml(job / "brief.yaml", {})
    outline = load_yaml(job / "outline.yaml", {"slides": []})
    slides = outline.get("slides") or []
    bp = load_blueprint(brief.get("blueprint"))
    if brief.get("blueprint") and not bp:
        iss.warn("brief.blueprint", f"blueprint '{brief.get('blueprint')}' não encontrado")
    for k in ("title", "audience", "goal", "duration_min"):
        if not brief.get(k):
            iss.err("brief", f"campo obrigatório vazio: {k}")
    seen = set()
    for i, s in enumerate(slides):
        w = f"outline[{i}]"
        sid = s.get("id", "")
        if not re.match(r"^SL-\d{2,3}$", str(sid)):
            iss.err(w, f"id '{sid}' fora do padrão SL-01")
        if sid in seen:
            iss.err(w, f"id repetido {sid}")
        seen.add(sid)
        if s.get("archetype") not in ARCH:
            iss.err(w, f"arquétipo '{s.get('archetype')}' inexistente")
        msg = str(s.get("message", ""))
        if not msg or msg.startswith("<"):
            iss.err(w, "mensagem-chave vazia ou ainda é o marcador do esqueleto")
        elif len(msg) > 90:
            iss.warn(w, f"mensagem com {len(msg)} caracteres; títulos-mensagem devem caber em ~90")
    if bp:
        secs = {sec["id"]: sec for sec in bp.get("sections", [])}
        count = {}
        for s in slides:
            sec = s.get("section")
            if sec not in secs:
                iss.warn(s.get("id", "?"), f"seção '{sec}' não existe no blueprint {bp['id']}")
            count[sec] = count.get(sec, 0) + 1
        for sid, sec in secs.items():
            rng = sec.get("slides") or [0, 99]
            c = count.get(sid, 0)
            if sec.get("required") and c == 0:
                iss.err("outline", f"seção obrigatória ausente: {sid} ({sec.get('name', '')})")
            elif c and not (rng[0] <= c <= rng[-1]):
                iss.warn("outline", f"seção {sid}: {c} slide(s); recomendado {rng[0]}–{rng[-1]}")
        rule = bp.get("duration_rule") or {}
        dur = brief.get("duration_min") or 0
        if rule and dur:
            target = dur * rule.get("slides_per_min", 1.0)
            lo = max(rule.get("min", 1), math.floor(target * 0.7))
            hi = min(rule.get("max", 999), math.ceil(target * 1.3))
            if not (lo <= len(slides) <= hi):
                iss.warn("outline", f"{len(slides)} slides para {dur} min; o blueprint sugere {lo}–{hi}")
    mx = (brief.get("constraints") or {}).get("max_slides")
    if mx and len(slides) > mx:
        iss.err("outline", f"{len(slides)} slides > limite do brief ({mx})")
    notes_on = bool((brief.get("constraints") or {}).get("notes")) or (bp or {}).get("notes_required", False)
    units, cur, cur_w = [], [], 0
    for s in slides:
        est = TYPICAL_WORDS.get(s.get("archetype"), 70) + (90 if notes_on else 15)
        if cur and (len(cur) >= a.per_unit or cur_w + est > 900):
            units.append(cur)
            cur, cur_w = [], 0
        cur.append(s)
        cur_w += est
    if cur:
        units.append(cur)
    plan = {"job": job.name, "notes_required": notes_on, "unit_max_words": UNIT_MAX_WORDS,
            "units": [{"id": f"U{i + 1:02d}", "slides": [s.get("id") for s in u],
                       "archetypes": [s.get("archetype") for s in u], "status": "todo"}
                      for i, u in enumerate(units)]}
    old = load_yaml(job / "plan.yaml", {})
    done = {u["id"]: u.get("status") for u in old.get("units", [])
            if (job / "spec" / f"{u['id']}.yaml").exists()}
    for u in plan["units"]:
        if done.get(u["id"]) == "done":
            u["status"] = "done"
    dump_yaml(plan, job / "plan.yaml")
    iss.print("Plano do deck:")
    for u in plan["units"]:
        print(f"  {u['id']}: {', '.join(u['slides'])}  ({', '.join(u['archetypes'])})  [{u['status']}]")
    print(f"{len(slides)} slides em {len(units)} unidade(s). Notas de fala obrigatórias: {'sim' if notes_on else 'não'}.")
    return iss.exit_code()


def cmd_validate(a):
    job = Path(a.job)
    iss = Issues()
    files = sorted((job / "spec").glob("U*.yaml"))
    if a.unit:
        files = [f for f in files if f.stem == a.unit]
        if not files:
            print(f"ERRO: spec/{a.unit}.yaml não existe", file=sys.stderr)
            return 2
    plan = load_yaml(job / "plan.yaml", {"units": []})
    planned = {u["id"]: u["slides"] for u in plan.get("units", [])}
    brief = load_yaml(job / "brief.yaml", {})
    bp = load_blueprint(brief.get("blueprint")) or {}
    notes_on = plan.get("notes_required") or bp.get("notes_required", False)
    for f in files:
        try:
            data = load_yaml(f, {})
        except ValueError as e:
            iss.err(f.name, str(e))
            continue
        sl = data.get("slides") or []
        uw = words([{k: v for k, v in s.items() if k not in ("id", "archetype")} for s in sl])
        if uw > UNIT_MAX_WORDS:
            iss.err(f.name, f"unidade com {uw} palavras (máx. {UNIT_MAX_WORDS}); divida-a")
        if f.stem in planned and [s.get("id") for s in sl] != planned[f.stem]:
            iss.warn(f.name, f"slides diferentes do plano: esperado {planned[f.stem]}")
        for i, s in enumerate(sl):
            validate_slide(s, f"{f.stem}/{s.get('id', i)}", iss, job)
            if notes_on and not s.get("notes") and s.get("archetype") not in ("section", "qa"):
                iss.err(f"{f.stem}/{s.get('id', i)}", "notas de fala obrigatórias neste deck")
            for src in s.get("sources") or []:
                if not re.match(r"^([A-Z]{1,5}-[\w.-]+(#[\w.:-]+)?|https?://\S+)$", str(src)):
                    iss.warn(f"{f.stem}/{s.get('id', i)}", f"fonte '{src}' fora do padrão (SRC-x#C003, S-01 ou URL)")
    if not a.unit:
        load_slides(job, iss, complete=a.complete)
    iss.print(f"Validação de {len(files)} unidade(s):")
    if not iss.errors and a.unit:
        for u in plan.get("units", []):
            if u["id"] == a.unit:
                u["status"] = "done"
        if plan.get("units"):
            dump_yaml(plan, job / "plan.yaml")
    return iss.exit_code()


# ----------------------------------------------------------------------------------------------------------
# 3. Kit, medidas e ajuste de texto
# ----------------------------------------------------------------------------------------------------------
SW, SH = Inches(13.333), Inches(7.5)
MX = Inches(0.65)
TITLE_TOP, TITLE_H = Inches(0.42), Inches(1.0)
CONTENT_TOP, CONTENT_BOTTOM = Inches(1.7), Inches(6.85)
EMU_PT = 12700


def load_kit(kid):
    p = STUDIO / "kits" / f"{kid}.yaml"
    if not p.exists():
        raise SystemExit(f"ERRO: kit '{kid}' não encontrado em studio/kits/")
    k = load_yaml(p)
    base = load_yaml(STUDIO / "kits/default.yaml") if kid != "default" else {}
    for sec in ("colors", "fonts", "sizes", "footer"):
        merged = dict(base.get(sec) or {})
        merged.update(k.get(sec) or {})
        k[sec] = merged
    if not k.get("chart_palette"):
        k["chart_palette"] = base.get("chart_palette") or [k["colors"]["primary"], k["colors"]["accent"]]
    return k


def hx(c):
    return RGBColor.from_string(str(c).lstrip("#").upper())


def lum(c):
    c = str(c).lstrip("#")
    r, g, b = (int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def lines_needed(text, size, width_pt, cw):
    cpl = max(1, int(width_pt / (size * cw)))
    total = 0
    for para in str(text).split("\n"):
        cur, n = 0, 1
        for w in para.split():
            L = len(w)
            if cur == 0:
                cur = L
            elif cur + 1 + L <= cpl:
                cur += 1 + L
            else:
                n += 1
                cur = L
            while cur > cpl:
                n += 1
                cur -= cpl
        total += n
    return total


def fit(paras, width_emu, height_emu, max_size, min_size, line=1.15, gap=0.4):
    """paras: [(texto, fator_de_tamanho, recuo_emu, cw)] -> (tamanho, cabe?)"""
    wpt, hpt = width_emu / EMU_PT, height_emu / EMU_PT
    for size in range(int(max_size), int(min_size) - 1, -1):
        h = 0
        for text, factor, indent, cw in paras:
            s = size * factor
            h += lines_needed(text, s, wpt - indent / EMU_PT, cw) * s * line + s * gap
        if h - size * gap <= hpt:
            return size, True
    return int(min_size), False


class Deck:
    def __init__(self, job, kit, template=None):
        self.job = Path(job)
        self.kit = kit
        self.c = kit["colors"]
        self.f = kit["fonts"]
        self.z = kit["sizes"]
        self.tpl = template
        self.report = []
        self.cur_id = ""
        if template:
            self.prs = Presentation(str(template["_pptx"]))
            _clear_slides(self.prs)
            self.SW, self.SH = self.prs.slide_width, self.prs.slide_height
        else:
            self.prs = Presentation()
            self.prs.slide_width, self.prs.slide_height = SW, SH
            self.SW, self.SH = SW, SH
        self.cache = self.job / "build" / "cache"
        self.cache.mkdir(parents=True, exist_ok=True)

    # ---------- primitivas ----------
    def log(self, field, size, ok):
        self.report.append({"slide": self.cur_id, "field": field, "size": size, "fits": ok})

    def rect(self, s, x, y, w, h, color, shape=MSO_SHAPE.RECTANGLE, line=None):
        sh = s.shapes.add_shape(shape, x, y, w, h)
        sh.fill.solid()
        sh.fill.fore_color.rgb = hx(color)
        if line:
            sh.line.color.rgb = hx(line)
            sh.line.width = Pt(1.25)
        else:
            sh.line.fill.background()
        sh.shadow.inherit = False
        if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
            sh.adjustments[0] = 0.08
        sh.text_frame.text = ""
        return sh

    def text(self, s, x, y, w, h, paras, *, size, min_size=None, color=None, font=None, bold=False, italic=False,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, field="text", line=1.12, gap=0.35, cw=0.5, shape=None):
        """paras: lista de str ou dicts {text, factor, bold, color, bullet, level, italic, font}"""
        norm = []
        for p in paras:
            d = {"text": p} if isinstance(p, str) else dict(p)
            d.setdefault("factor", 1.0)
            d.setdefault("level", 0)
            norm.append(d)
        indent = Inches(0.32)
        fparas = [(d["text"], d["factor"], (indent * (d["level"] + 1)) if d.get("bullet") else 0,
                   cw + (0.04 if d.get("bold", bold) else 0)) for d in norm]
        min_size = min_size or max(self.z.get("min_body", 12), int(size * 0.6))
        sz, ok = fit(fparas, w, h, size, min_size, line=line, gap=gap)
        self.log(field, sz, ok)
        if shape is None:
            shape = s.shapes.add_textbox(x, y, w, h)
        tf = shape.text_frame
        tf.word_wrap = True
        tf.auto_size = MSO_AUTO_SIZE.NONE
        tf.vertical_anchor = anchor
        for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
            setattr(tf, m, 0)
        for i, d in enumerate(norm):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = d.get("align", align)
            p.line_spacing = line
            p.space_after = Pt(sz * d["factor"] * gap) if i < len(norm) - 1 else Pt(0)
            r = p.add_run()
            r.text = str(d["text"])
            fnt = r.font
            fnt.size = Pt(round(sz * d["factor"], 1))
            fnt.bold = d.get("bold", bold)
            fnt.italic = d.get("italic", italic)
            fnt.name = d.get("font", font or self.f["body"])
            fnt.color.rgb = hx(d.get("color", color or self.c["text"]))
            if d.get("bullet"):
                _bullet(p, d["bullet"], d.get("bullet_color", self.c["accent"]), indent, d["level"])
        return shape

    def picture(self, s, path, x, y, w, h, align="center"):
        from PIL import Image
        with Image.open(path) as im:
            iw, ih = im.size
        sc = min(w / iw, h / ih)
        pw, ph = int(iw * sc), int(ih * sc)
        px = x + (w - pw) // 2 if align == "center" else (x if align == "left" else x + w - pw)
        return s.shapes.add_picture(str(path), px, y + (h - ph) // 2, pw, ph)

    # ---------- molduras ----------
    def new_slide(self, arch, dark=False):
        if self.tpl:
            return self._tpl_slide(arch, dark)
        s = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        bg = s.background.fill
        bg.solid()
        bg.fore_color.rgb = hx(self.c["dark"] if dark else self.c["background"])
        return s, None

    def _tpl_slide(self, arch, dark):
        lay = self.tpl["layouts"]
        key = arch if arch in lay else ("blank" if (dark or arch in ("statement", "quote", "big_number"))
                                         and "blank" in lay else "default")
        spec = lay.get(key) or lay.get("default")
        layout = _find_layout(self.prs, spec["layout"])
        s = self.prs.slides.add_slide(layout)
        if dark and key in ("blank", "default"):
            bg = s.background.fill
            bg.solid()
            bg.fore_color.rgb = hx(self.c["dark"])
        return s, (key, spec)

    def title_bar(self, s, title, info=None):
        if self.tpl:
            key, spec = info
            ph = _ph(s, spec.get("title"))
            if ph is not None and title:
                self.text(s, ph.left, ph.top, ph.width, ph.height, [title], size=self.z["title"],
                          min_size=self.z.get("min_title", 18), field="title", shape=ph,
                          color=self.c["text"], font=self.f["heading"], bold=True, anchor=MSO_ANCHOR.MIDDLE)
            elif ph is not None:
                _remove(ph)
            return
        if not title:
            return
        self.text(s, MX, TITLE_TOP, self.SW - 2 * MX, TITLE_H, [title], size=self.z["title"],
                  min_size=self.z.get("min_title", 20), font=self.f["heading"], bold=True,
                  color=self.c["primary"], anchor=MSO_ANCHOR.BOTTOM, field="title", line=1.05)
        self.rect(s, MX, TITLE_TOP + TITLE_H + Inches(0.1), Inches(0.9), Inches(0.06), self.c["accent"])

    def box(self, info=None):
        """Área de conteúdo (x, y, w, h)."""
        if self.tpl:
            cb = self.tpl.get("content_box") or {}
            return (Inches(cb.get("left", 0.6)), Inches(cb.get("top", 1.6)),
                    Inches(cb.get("width", self.SW / 914400 - 1.2)), Inches(cb.get("height", 5.2)))
        return MX, CONTENT_TOP, self.SW - 2 * MX, CONTENT_BOTTOM - CONTENT_TOP

    def footer(self, s, n, dark):
        if self.tpl or dark:
            return
        ft = self.kit.get("footer") or {}
        col = self.c["muted"]
        if ft.get("text"):
            self.text(s, MX, Inches(7.02), Inches(8), Inches(0.3), [ft["text"]], size=self.z["footer"],
                      min_size=8, color=col, field="footer")
        if ft.get("slide_numbers", True):
            self.text(s, self.SW - MX - Inches(1), Inches(7.02), Inches(1), Inches(0.3), [str(n)],
                      size=self.z["footer"], min_size=8, color=col, align=PP_ALIGN.RIGHT, field="number")
        logo = self.kit.get("logo")
        if logo and ft.get("logo", False) and resolve_kit_asset(logo):
            self.picture(s, resolve_kit_asset(logo), self.SW - MX - Inches(2.4), Inches(6.98), Inches(1.2),
                         Inches(0.38), align="right")

    # ---------- arquétipos ----------
    def a_title(self, d, s, info):
        if self.tpl and info[0] == "title":
            spec = info[1]
            self._fill_ph(s, spec.get("title"), [d["title"]], self.z["title"] + 10, "title", bold=True)
            sub = " · ".join(x for x in [d.get("subtitle"), d.get("author"), d.get("event"), d.get("date")] if x)
            self._fill_ph(s, spec.get("subtitle"), [sub] if sub else [], self.z["body"], "subtitle")
            return
        c = self.c
        self.rect(s, 0, 0, Inches(0.28), self.SH, c["accent"])
        x, w = Inches(1.1), self.SW - Inches(2.2)
        self.text(s, x, Inches(1.9), w, Inches(2.3), [d["title"]], size=44, min_size=30, bold=True,
                  font=self.f["heading"], color=c["on_dark"], anchor=MSO_ANCHOR.BOTTOM, field="title", line=1.02)
        if d.get("subtitle"):
            self.text(s, x, Inches(4.35), w, Inches(1.0), [d["subtitle"]], size=22, min_size=16,
                      color=c.get("on_dark_muted", "C9D3E0"), field="subtitle")
        meta = [m for m in (d.get("author"), " · ".join(x for x in (d.get("event"), d.get("date")) if x)) if m]
        if meta:
            self.rect(s, x, Inches(5.65), Inches(0.6), Inches(0.04), c["accent"])
            self.text(s, x, Inches(5.8), w, Inches(0.9), [{"text": meta[0], "bold": True}] +
                      [{"text": m} for m in meta[1:]], size=16, min_size=12,
                      color=c.get("on_dark_muted", "C9D3E0"), field="meta", gap=0.2)
        logo = resolve_kit_asset(self.kit.get("logo_on_dark") or self.kit.get("logo"))
        if logo:
            self.picture(s, logo, self.SW - Inches(3.0), Inches(0.6), Inches(2.3), Inches(0.9), align="right")

    def a_section(self, d, s, info):
        if self.tpl and info[0] == "section":
            spec = info[1]
            self._fill_ph(s, spec.get("title"), [d["title"]], self.z["title"] + 6, "title", bold=True)
            self._fill_ph(s, spec.get("subtitle"), [d["subtitle"]] if d.get("subtitle") else [], self.z["body"],
                          "subtitle")
            return
        c = self.c
        x = Inches(1.1)
        if d.get("number"):
            self.text(s, x, Inches(1.5), Inches(4), Inches(1.6), [str(d["number"])], size=88, min_size=60,
                      bold=True, color=c["accent"], font=self.f["heading"], anchor=MSO_ANCHOR.BOTTOM, field="number")
        self.text(s, x, Inches(3.2), self.SW - Inches(2.2), Inches(1.6), [d["title"]], size=40, min_size=28,
                  bold=True, color=c["on_dark"], font=self.f["heading"], field="title", line=1.02)
        if d.get("subtitle"):
            self.text(s, x, Inches(4.9), self.SW - Inches(2.2), Inches(1.2), [d["subtitle"]], size=20,
                      min_size=14, color=c.get("on_dark_muted", "C9D3E0"), field="subtitle")

    def _bullet_paras(self, items, primary=None):
        out = []
        for it in items:
            if isinstance(it, dict):
                out.append({"text": it.get("text", ""), "bullet": "■", "color": primary or self.c["text"]})
                for sub in it.get("sub", []) or []:
                    out.append({"text": sub, "bullet": "–", "level": 1, "factor": 0.85, "color": self.c["muted"],
                                "bullet_color": self.c["muted"]})
            else:
                out.append({"text": it, "bullet": "■", "color": primary or self.c["text"]})
        return out

    def a_bullets(self, d, s, info):
        if self.tpl and info[0] == "bullets":
            spec = info[1]
            self._fill_ph(s, spec.get("title"), [d["title"]], self.z["title"], "title", bold=True)
            paras = []
            for it in d["bullets"]:
                if isinstance(it, dict):
                    paras.append({"text": it.get("text", ""), "level": 0})
                    paras += [{"text": t, "level": 1, "factor": 0.85} for t in it.get("sub", []) or []]
                else:
                    paras.append({"text": it, "level": 0})
            if d.get("takeaway"):
                paras.append({"text": d["takeaway"], "level": 0, "bold": True})
            self._fill_ph(s, spec.get("body"), paras, self.z["body"], "bullets", native_levels=True)
            return
        self.title_bar(s, d["title"], info)
        x, y, w, h = self.box(info)
        tk = d.get("takeaway")
        bh = h - (Inches(1.05) if tk else 0)
        self.text(s, x, y + Inches(0.1), w * (0.92 if not tk else 1), bh - Inches(0.1),
                  self._bullet_paras(d["bullets"]), size=self.z["body"] + 2, min_size=self.z.get("min_body", 14),
                  field="bullets", gap=0.55)
        if tk:
            self._takeaway(s, tk, x, y + h - Inches(0.85), w, Inches(0.85))

    def _takeaway(self, s, text, x, y, w, h):
        self.rect(s, x, y, w, h, self.c["light"])
        self.rect(s, x, y, Inches(0.09), h, self.c["accent"])
        self.text(s, x + Inches(0.3), y, w - Inches(0.5), h, [text], size=self.z["body"], min_size=13, bold=True,
                  color=self.c["primary"], anchor=MSO_ANCHOR.MIDDLE, field="takeaway")

    def a_agenda(self, d, s, info):
        self.title_bar(s, d.get("title") or "Agenda", info)
        x, y, w, h = self.box(info)
        n = len(d["items"])
        row = min(Inches(0.8), int(h / n))
        for i, it in enumerate(d["items"]):
            yy = y + Inches(0.1) + i * row
            dot = self.rect(s, x, yy + (row - Inches(0.5)) // 2, Inches(0.5), Inches(0.5), self.c["primary"],
                            MSO_SHAPE.OVAL)
            self.text(s, x, yy + (row - Inches(0.5)) // 2, Inches(0.5), Inches(0.5), [str(i + 1)], size=16,
                      bold=True, color=self.c["on_dark"], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
                      field="agenda.n", shape=dot)
            self.text(s, x + Inches(0.8), yy, w - Inches(0.8), row, [it], size=self.z["body"] + 2, min_size=14,
                      anchor=MSO_ANCHOR.MIDDLE, field=f"items[{i}]")

    def a_statement(self, d, s, info):
        if self.tpl and info:
            self._clear_title(s, info)
        x, w = Inches(1.4), self.SW - Inches(2.8)
        self.rect(s, x, Inches(2.0), Inches(0.9), Inches(0.08), self.c["accent"])
        self.text(s, x, Inches(2.3), w, Inches(2.6), [d["statement"]], size=38, min_size=26, bold=True,
                  color=self.c["primary"], font=self.f["heading"], field="statement", line=1.08)
        if d.get("support"):
            self.text(s, x, Inches(5.0), w, Inches(1.2), [d["support"]], size=20, min_size=14,
                      color=self.c["muted"], field="support")

    def a_big_number(self, d, s, info):
        if d.get("title"):
            self.title_bar(s, d["title"], info)
        elif self.tpl and info:
            self._clear_title(s, info)
        top = Inches(1.9) if d.get("title") else Inches(1.2)
        x, w = Inches(1.2), self.SW - Inches(2.4)
        self.text(s, x, top, w, Inches(2.2), [d["value"]], size=120, min_size=72, bold=True,
                  color=self.c["accent"], font=self.f["heading"], anchor=MSO_ANCHOR.BOTTOM, field="value", line=1.0)
        self.text(s, x, top + Inches(2.35), w, Inches(0.9), [d["label"]], size=28, min_size=18, bold=True,
                  color=self.c["primary"], field="label")
        if d.get("context"):
            self.text(s, x, top + Inches(3.3), w * 0.8, Inches(1.0), [d["context"]], size=18, min_size=13,
                      color=self.c["muted"], field="context")

    def a_kpis(self, d, s, info):
        self.title_bar(s, d.get("title"), info)
        x, y, w, h = self.box(info)
        n = len(d["items"])
        gap = Inches(0.35)
        cw = int((w - gap * (n - 1)) / n)
        ch = min(h - Inches(0.4), Inches(3.2))
        cy = y + (h - ch) // 2
        for i, it in enumerate(d["items"]):
            cx = x + i * (cw + gap)
            self.rect(s, cx, cy, cw, ch, self.c["light"], MSO_SHAPE.ROUNDED_RECTANGLE)
            self.rect(s, cx, cy, cw, Inches(0.09), self.c["accent"])
            self.text(s, cx + Inches(0.3), cy + Inches(0.45), cw - Inches(0.6), Inches(1.3), [it["value"]],
                      size=54, min_size=30, bold=True, color=self.c["primary"], font=self.f["heading"],
                      anchor=MSO_ANCHOR.BOTTOM, field=f"items[{i}].value", line=1.0)
            if it.get("delta"):
                self.text(s, cx + Inches(0.3), cy + Inches(1.8), cw - Inches(0.6), Inches(0.4), [it["delta"]],
                          size=16, min_size=11, bold=True, color=self.c.get("accent2", self.c["accent"]),
                          field=f"items[{i}].delta")
            self.text(s, cx + Inches(0.3), cy + Inches(2.25), cw - Inches(0.6), ch - Inches(2.45),
                      [it["label"]], size=19, min_size=12, color=self.c["muted"], field=f"items[{i}].label")

    def _column(self, s, x, y, w, h, heading, bullets, field, card=False, highlight=False):
        fg = self.c["on_dark"] if highlight else self.c["primary"]
        tx = self.c["on_dark"] if highlight else self.c["text"]
        pad = Inches(0.3) if card else 0
        if card:
            self.rect(s, x, y, w, h, self.c["primary"] if highlight else self.c["light"],
                      MSO_SHAPE.ROUNDED_RECTANGLE)
        top = y + pad
        if heading:
            self.text(s, x + pad, top, w - 2 * pad, Inches(0.55), [heading], size=self.z["body"] + 2, min_size=14,
                      bold=True, color=fg, field=f"{field}.heading", anchor=MSO_ANCHOR.BOTTOM)
            self.rect(s, x + pad, top + Inches(0.62), Inches(0.6), Inches(0.05),
                      self.c["accent"] if not highlight else self.c["on_dark"])
            top += Inches(0.85)
        paras = self._bullet_paras(bullets, primary=tx)
        if highlight:
            for p in paras:
                p["bullet_color"] = self.c["on_dark"]
        self.text(s, x + pad, top, w - 2 * pad, y + h - top - pad, paras, size=self.z["body"], min_size=13,
                  field=f"{field}.bullets", gap=0.5)

    def a_two_column(self, d, s, info):
        if self.tpl and info[0] == "two_column":
            spec = info[1]
            self._fill_ph(s, spec.get("title"), [d["title"]], self.z["title"], "title", bold=True)
            for side in ("left", "right"):
                col = d[side]
                paras = ([{"text": col["heading"], "bold": True, "level": 0}] if col.get("heading") else []) + \
                        [{"text": b if isinstance(b, str) else b.get("text", ""), "level": 0} for b in col["bullets"]]
                self._fill_ph(s, spec.get(side), paras, self.z["body"], side, native_levels=True)
            return
        self.title_bar(s, d["title"], info)
        x, y, w, h = self.box(info)
        gap = Inches(0.6)
        cw = (w - gap) // 2
        self._column(s, x, y, cw, h, d["left"].get("heading"), d["left"]["bullets"], "left")
        self._column(s, x + cw + gap, y, cw, h, d["right"].get("heading"), d["right"]["bullets"], "right")

    def a_comparison(self, d, s, info):
        self.title_bar(s, d["title"], info)
        x, y, w, h = self.box(info)
        n = len(d["columns"])
        gap = Inches(0.35)
        cw = int((w - gap * (n - 1)) / n)
        for i, col in enumerate(d["columns"]):
            self._column(s, x + i * (cw + gap), y + Inches(0.05), cw, h - Inches(0.1), col["heading"], col["items"],
                         f"columns[{i}]", card=True, highlight=bool(col.get("highlight")))

    def a_image(self, d, s, info):
        self.title_bar(s, d.get("title"), info)
        x, y, w, h = self.box(info)
        if not d.get("title"):
            y, h = Inches(0.6), self.SH - Inches(1.4)
        img = resolve_asset(self.job, d["image"])
        cap_h = Inches(0.5) if (d.get("caption") or d.get("source")) else 0
        layout = d.get("layout", "full")
        if layout in ("left", "right") and d.get("bullets"):
            iw = int(w * 0.55)
            ix = x if layout == "left" else x + w - iw
            tx = x + iw + Inches(0.45) if layout == "left" else x
            self.picture(s, img, ix, y, iw, h - cap_h)
            self.text(s, tx, y + Inches(0.1), w - iw - Inches(0.45), h - cap_h, self._bullet_paras(d["bullets"]),
                      size=self.z["body"], min_size=13, field="bullets", gap=0.5)
            cap_x, cap_w = ix, iw
        else:
            self.picture(s, img, x, y, w, h - cap_h)
            cap_x, cap_w = x, w
        cap = " — ".join(t for t in (d.get("caption"), f"Fonte: {d['source']}" if d.get("source") else "") if t)
        if cap:
            self.text(s, cap_x, y + h - cap_h + Inches(0.08), cap_w, cap_h - Inches(0.08), [cap], size=13,
                      min_size=10, italic=True, color=self.c["muted"], field="caption",
                      align=PP_ALIGN.CENTER if layout == "full" else PP_ALIGN.LEFT)

    def a_chart(self, d, s, info):
        self.title_bar(s, d["title"], info)
        x, y, w, h = self.box(info)
        ch = d["chart"]
        low = (Inches(0.95) if d.get("takeaway") else 0) + (Inches(0.35) if d.get("source") else 0)
        types = {"bar": XL_CHART_TYPE.BAR_CLUSTERED, "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
                 "stacked_column": XL_CHART_TYPE.COLUMN_STACKED, "line": XL_CHART_TYPE.LINE_MARKERS,
                 "pie": XL_CHART_TYPE.PIE, "doughnut": XL_CHART_TYPE.DOUGHNUT}
        cd = CategoryChartData()
        cats = list(ch["categories"])
        series = ch["series"]
        if ch["type"] == "bar":                      # barras horizontais: maior no topo
            cats = cats[::-1]
            series = [dict(se, values=list(se["values"])[::-1]) for se in series]
        cd.categories = cats
        for se in series:
            cd.add_series(se["name"], se["values"])
        gf = s.shapes.add_chart(types[ch["type"]], x, y, w, h - low, cd)
        chart = gf.chart
        chart.font.size = Pt(13)
        chart.font.name = self.f["body"]
        chart.font.color.rgb = hx(self.c["text"])
        pal = self.kit["chart_palette"]
        plot = chart.plots[0]
        pie = ch["type"] in ("pie", "doughnut")
        nf = ch.get("number_format") or ('0%' if pie else 'General')
        multi = len(series) > 1
        chart.has_legend = multi or pie
        if chart.has_legend:
            chart.legend.position = XL_LEGEND_POSITION.BOTTOM
            chart.legend.include_in_layout = False
            chart.legend.font.size = Pt(13)
        if pie:
            se = plot.series[0]
            for i in range(len(cats)):
                pt = se.points[i]
                pt.format.fill.solid()
                pt.format.fill.fore_color.rgb = hx(pal[i % len(pal)])
            plot.has_data_labels = True
            dl = plot.data_labels
            dl.show_percentage, dl.show_value = True, False
            dl.number_format, dl.number_format_is_linked = "0%", False
            dl.font.size, dl.font.bold = Pt(14), True
            dl.font.color.rgb = hx(self.c["on_dark"])
        else:
            if hasattr(plot, "gap_width"):
                plot.gap_width = 70
            if ch["type"] == "stacked_column":
                plot.overlap = 100
            va, ca = chart.value_axis, chart.category_axis
            va.has_major_gridlines = True
            va.major_gridlines.format.line.color.rgb = hx(self.c["light"])
            va.format.line.fill.background()
            va.tick_labels.font.size = Pt(12)
            va.tick_labels.font.color.rgb = hx(self.c["muted"])
            if ch.get("number_format"):
                va.tick_labels.number_format, va.tick_labels.number_format_is_linked = nf, False
            ca.format.line.color.rgb = hx(self.c["muted"])
            ca.tick_labels.font.size = Pt(13)
            ca.has_major_gridlines = False
            hl = ch.get("highlight")
            for i, se in enumerate(plot.series):
                col = pal[i % len(pal)]
                if ch["type"] == "line":
                    se.format.line.color.rgb = hx(col)
                    se.format.line.width = Pt(3)
                    se.smooth = False
                    se.marker.format.fill.solid()
                    se.marker.format.fill.fore_color.rgb = hx(col)
                    se.marker.format.line.color.rgb = hx(col)
                else:
                    se.format.fill.solid()
                    se.format.fill.fore_color.rgb = hx(self.c["primary"] if (not multi and hl) else col)
                    if not multi and hl and hl in cats:
                        pt = se.points[cats.index(hl)]
                        pt.format.fill.solid()
                        pt.format.fill.fore_color.rgb = hx(self.c["accent"])
            if not multi and len(cats) <= 8 and ch["type"] != "line":
                plot.has_data_labels = True
                dl = plot.data_labels
                dl.font.size = Pt(13)
                dl.font.color.rgb = hx(self.c["text"])
                dl.number_format, dl.number_format_is_linked = nf, ch.get("number_format") is None
                dl.position = XL_LABEL_POSITION.OUTSIDE_END
        yy = y + h - low
        if d.get("takeaway"):
            self._takeaway(s, d["takeaway"], x, yy + Inches(0.1), w, Inches(0.8))
            yy += Inches(0.95)
        if d.get("source"):
            unit = f" · Unidade: {ch['unit']}" if ch.get("unit") else ""
            self.text(s, x, yy, w, Inches(0.3), [f"Fonte: {d['source']}{unit}"], size=11, min_size=9,
                      italic=True, color=self.c["muted"], field="source")

    def a_table(self, d, s, info):
        self.title_bar(s, d["title"], info)
        x, y, w, h = self.box(info)
        cols, rows = d["columns"], d["rows"]
        src_h = Inches(0.35) if d.get("source") else 0
        rh = min(Inches(0.62), int((h - src_h) / (len(rows) + 1)))
        gf = s.shapes.add_table(len(rows) + 1, len(cols), x, y, w, rh * (len(rows) + 1))
        tbl = gf.table
        tblpr = gf._element.graphic.graphicData.tbl.tblPr
        for child in list(tblpr):
            if child.tag == qn("a:tableStyleId"):
                child.text = "{5940675A-B579-460E-94D1-54222C63F5DA}"
        longest = max(len(str(c)) for r in rows for c in r) if rows else 10
        size = 16 if longest < 22 else (14 if longest < 32 else 12)
        hl = d.get("highlight_row")
        for ci, name in enumerate(cols):
            self._cell(tbl.cell(0, ci), name, size, True, self.c["on_dark"], self.c["primary"])
        for ri, r in enumerate(rows):
            fill = self.c["accent"] if hl == ri else (self.c["light"] if ri % 2 == 0 else self.c["background"])
            fg = self.c["on_dark"] if hl == ri else self.c["text"]
            for ci, val in enumerate(r):
                self._cell(tbl.cell(ri + 1, ci), val, size, hl == ri, fg, fill)
        self.log("table", size, longest < 40)
        if d.get("source"):
            self.text(s, x, y + rh * (len(rows) + 1) + Inches(0.12), w, Inches(0.3), [f"Fonte: {d['source']}"],
                      size=11, min_size=9, italic=True, color=self.c["muted"], field="source")

    def _cell(self, cell, val, size, bold, fg, fill):
        cell.fill.solid()
        cell.fill.fore_color.rgb = hx(fill)
        cell.margin_left = cell.margin_right = Inches(0.12)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf = cell.text_frame
        tf.word_wrap = True
        tf.paragraphs[0].text = ""
        r = tf.paragraphs[0].add_run()
        r.text = str(val)
        r.font.size, r.font.bold, r.font.name = Pt(size), bold, self.f["body"]
        r.font.color.rgb = hx(fg)

    def a_timeline(self, d, s, info):
        self.title_bar(s, d["title"], info)
        x, y, w, h = self.box(info)
        ev = d["events"]
        n = len(ev)
        ly = y + int(h * 0.36)
        self.rect(s, x, ly - Inches(0.025), w, Inches(0.05), self.c["muted"])
        seg = w / n
        for i, e in enumerate(ev):
            cx = int(x + seg * i + seg / 2)
            self.rect(s, cx - Inches(0.16), ly - Inches(0.16), Inches(0.32), Inches(0.32),
                      self.c["accent"] if i == n - 1 else self.c["primary"], MSO_SHAPE.OVAL)
            bw = int(seg - Inches(0.2))
            self.text(s, cx - bw // 2, ly - Inches(0.95), bw, Inches(0.6), [e["when"]], size=18, min_size=12,
                      bold=True, color=self.c["primary"], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.BOTTOM,
                      field=f"events[{i}].when")
            paras = [{"text": e["label"], "bold": True, "align": PP_ALIGN.CENTER}]
            if e.get("detail"):
                paras.append({"text": e["detail"], "factor": 0.82, "color": self.c["muted"], "align": PP_ALIGN.CENTER})
            self.text(s, cx - bw // 2, ly + Inches(0.4), bw, y + h - ly - Inches(0.4), paras, size=17, min_size=11,
                      align=PP_ALIGN.CENTER, field=f"events[{i}]", gap=0.3)

    def a_process(self, d, s, info):
        self.title_bar(s, d["title"], info)
        x, y, w, h = self.box(info)
        st = d["steps"]
        n = len(st)
        gap = Inches(0.45)
        bw = int((w - gap * (n - 1)) / n)
        longest = max(len(st_.get('detail') or '') for st_ in st)
        bh = min(h - Inches(0.3), Inches(2.9) + (Inches(0.5) if longest > 45 else 0))
        by = y + (h - bh) // 2 - Inches(0.2)
        for i, stp in enumerate(st):
            bx = x + i * (bw + gap)
            self.rect(s, bx, by, bw, bh, self.c["light"], MSO_SHAPE.ROUNDED_RECTANGLE)
            dot = self.rect(s, bx + Inches(0.3), by + Inches(0.3), Inches(0.62), Inches(0.62), self.c["accent"],
                            MSO_SHAPE.OVAL)
            self.text(s, 0, 0, Inches(0.62), Inches(0.62), [str(i + 1)], size=20, bold=True,
                      color=self.c["on_dark"], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
                      field=f"steps[{i}].n", shape=dot)
            paras = [{"text": stp["label"], "bold": True, "color": self.c["primary"]}]
            if stp.get("detail"):
                paras.append({"text": stp["detail"], "factor": 0.8, "color": self.c["text"]})
            self.text(s, bx + Inches(0.3), by + Inches(1.15), bw - Inches(0.6), bh - Inches(1.4), paras,
                      size=20, min_size=12, field=f"steps[{i}]", gap=0.45)
            if i < n - 1:
                ax = bx + bw + Inches(0.08)
                self.rect(s, ax, by + bh // 2 - Inches(0.15), gap - Inches(0.16), Inches(0.3), self.c["muted"],
                          MSO_SHAPE.RIGHT_ARROW)

    def a_quote(self, d, s, info):
        if self.tpl and info:
            self._clear_title(s, info)
        x, w = Inches(1.5), self.SW - Inches(3.0)
        self.text(s, x - Inches(0.2), Inches(0.7), Inches(2), Inches(1.8), ["“"], size=160, color=self.c["accent"],
                  font="Georgia", bold=True, field="mark", line=1.0)
        self.text(s, x, Inches(2.1), w, Inches(3.0), [d["quote"]], size=30, min_size=20, italic=True,
                  color=self.c["primary"], field="quote", line=1.15, anchor=MSO_ANCHOR.MIDDLE)
        who = [p for p in ({"text": d.get("author", ""), "bold": True},
                           {"text": d.get("role", ""), "factor": 0.85, "color": self.c["muted"]}) if p["text"]]
        if who:
            self.rect(s, x, Inches(5.35), Inches(0.6), Inches(0.05), self.c["accent"])
            self.text(s, x, Inches(5.5), w, Inches(1.0), who, size=18, min_size=13, field="author", gap=0.2)

    def a_code(self, d, s, info):
        self.title_bar(s, d["title"], info)
        x, y, w, h = self.box(info)
        cap_h = Inches(0.45) if d.get("caption") else 0
        bg = self.c.get("code_bg", "1E2430")
        lines = d["code"].rstrip("\n").split("\n")
        longest = max(len(l) for l in lines)
        size = max(10, min(20, int((w - Inches(0.8)) / EMU_PT / (longest * 0.6 + 1)),
                           int((h - cap_h - Inches(0.6)) / EMU_PT / (len(lines) * 1.25))))
        bh = min(h - cap_h, max(Inches(2.2), int(len(lines) * size * 1.3 * EMU_PT) + Inches(0.7)))
        self.rect(s, x, y, w, bh, bg, MSO_SHAPE.ROUNDED_RECTANGLE)
        tb = s.shapes.add_textbox(x + Inches(0.4), y + Inches(0.3), w - Inches(0.8), bh - Inches(0.6))
        tf = tb.text_frame
        tf.word_wrap = False
        for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
            setattr(tf, m, 0)
        for i, ln in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            r = p.add_run()
            r.text = ln if ln else " "
            r.font.size, r.font.name = Pt(size), self.f.get("mono", "Consolas")
            com = ln.strip().startswith(("#", "//", "--", "%"))
            r.font.color.rgb = hx("8B95A5" if com else self.c.get("code_fg", "E6EDF3"))
        self.log("code", size, size >= 11)
        if d.get("caption"):
            self.text(s, x, y + bh + Inches(0.12), w, cap_h, [d["caption"]], size=13, min_size=10,
                      italic=True, color=self.c["muted"], field="caption")

    def a_equation(self, d, s, info):
        self.title_bar(s, d["title"], info)
        x, y, w, h = self.box(info)
        img = self._mathtext(d["latex"])
        eh = int(h * (0.55 if d.get("explanation") else 0.85))
        if img:
            self.picture(s, img, x, y, w, eh)
        else:
            self.text(s, x, y, w, eh, [d["latex"]], size=28, min_size=16, font=self.f.get("mono", "Consolas"),
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, field="latex")
            self.report.append({"slide": self.cur_id, "field": "latex", "size": 0, "fits": False,
                                "note": "mathtext não suportou a expressão; usada versão texto (use backend beamer)"})
        if d.get("explanation"):
            self.text(s, x + Inches(0.5), y + eh + Inches(0.2), w - Inches(1), h - eh - Inches(0.2),
                      self._bullet_paras(d["explanation"]), size=self.z["body"], min_size=13, field="explanation",
                      gap=0.45)

    def _mathtext(self, latex):
        return render_mathtext(latex, self.cache, self.c["primary"])

    def a_diagram(self, d, s, info):
        self.title_bar(s, d["title"], info)
        x, y, w, h = self.box(info)
        cap_h = Inches(0.45) if d.get("caption") else 0
        img = resolve_asset(self.job, d["image"]) if d.get("image") else self._mermaid(d["mermaid"])
        if img:
            pic = self.picture(s, img, x, y, w, h - cap_h)
            if pic.height < (h - cap_h) * 0.45:
                self.report.append({"slide": self.cur_id, "field": "diagram", "size": 0, "fits": True,
                                    "warn": "diagrama muito largo e baixo (texto pequeno): use 'flowchart TB' ou divida"})
            if d.get("mermaid"):
                pic.top = y
        else:
            self.text(s, x, y, w, h - cap_h, ["[diagrama não renderizado: instale o mermaid-cli (mmdc)]"], size=18,
                      color=self.c["muted"], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, field="diagram")
            self.report.append({"slide": self.cur_id, "field": "mermaid", "size": 0, "fits": False,
                                "note": "mermaid-cli (mmdc) indisponível ou erro de sintaxe"})
        if d.get("caption"):
            self.text(s, x, y + h - cap_h + Inches(0.08), w, cap_h, [d["caption"]], size=13, min_size=10,
                      italic=True, color=self.c["muted"], align=PP_ALIGN.CENTER, field="caption")

    def _mermaid(self, src):
        return render_mermaid(src, self.cache, self.c, self.f)

    def a_team(self, d, s, info):
        self.title_bar(s, d.get("title") or "Equipe", info)
        x, y, w, h = self.box(info)
        m = d["members"]
        n = len(m)
        cw = int(w / n)
        dsz = min(Inches(1.7), cw - Inches(0.6))
        for i, p in enumerate(m):
            cx = x + i * cw
            ox = cx + (cw - dsz) // 2
            photo = resolve_asset(self.job, p.get("photo")) if p.get("photo") else None
            if photo:
                self.picture(s, photo, ox, y + Inches(0.3), dsz, dsz)
            else:
                circ = self.rect(s, ox, y + Inches(0.3), dsz, dsz, self.c["primary"] if i % 2 == 0 else
                                 self.c.get("accent2", self.c["accent"]), MSO_SHAPE.OVAL)
                ini = "".join(t[0] for t in p["name"].split()[:2]).upper()
                self.text(s, 0, 0, dsz, dsz, [ini], size=34, bold=True, color=self.c["on_dark"],
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, field=f"members[{i}].ini", shape=circ)
            paras = [{"text": p["name"], "bold": True, "color": self.c["primary"], "align": PP_ALIGN.CENTER}]
            if p.get("role"):
                paras.append({"text": p["role"], "factor": 0.85, "color": self.c["accent"], "bold": True,
                              "align": PP_ALIGN.CENTER})
            if p.get("detail"):
                paras.append({"text": p["detail"], "factor": 0.78, "color": self.c["muted"], "align": PP_ALIGN.CENTER})
            self.text(s, cx + Inches(0.15), y + dsz + Inches(0.5), cw - Inches(0.3), h - dsz - Inches(0.5), paras,
                      size=18, min_size=11, align=PP_ALIGN.CENTER, field=f"members[{i}]", gap=0.25)

    def a_closing(self, d, s, info):
        c = self.c
        if self.tpl and info and info[0] == "closing":
            spec = info[1]
            self._fill_ph(s, spec.get("title"), [d["title"]], self.z["title"] + 6, "title", bold=True)
            body = [d.get("message", "")] + list(d.get("items") or []) + [d.get("contact", "")]
            self._fill_ph(s, spec.get("subtitle") or spec.get("body"), [b for b in body if b], self.z["body"], "body")
            return
        self.rect(s, 0, self.SH - Inches(0.28), self.SW, Inches(0.28), c["accent"])
        x, w = Inches(1.1), self.SW - Inches(2.2)
        self.text(s, x, Inches(1.2), w, Inches(1.6), [d["title"]], size=44, min_size=28, bold=True,
                  color=c["on_dark"], font=self.f["heading"], anchor=MSO_ANCHOR.BOTTOM, field="title", line=1.02)
        yy = Inches(3.0)
        if d.get("message"):
            self.text(s, x, yy, w, Inches(1.1), [d["message"]], size=22, min_size=15,
                      color=c.get("on_dark_muted", "C9D3E0"), field="message")
            yy += Inches(1.2)
        if d.get("items"):
            paras = [{"text": t, "bullet": "■", "color": c["on_dark"]} for t in d["items"]]
            self.text(s, x, yy, w, Inches(1.9), paras, size=20, min_size=13, field="items", gap=0.4)
        if d.get("contact"):
            self.text(s, x, Inches(6.3), w, Inches(0.5), [d["contact"]], size=17, min_size=12, bold=True,
                      color=c["accent"], field="contact")

    def a_references(self, d, s, info):
        self.title_bar(s, d.get("title") or "Referências", info)
        x, y, w, h = self.box(info)
        paras = [{"text": f"[{i + 1}]  {t}"} for i, t in enumerate(d["items"])]
        self.text(s, x, y, w, h, paras, size=16, min_size=10, color=self.c["text"], field="items", gap=0.5)

    def a_qa(self, d, s, info):
        c = self.c
        if self.tpl and info and info[0] not in ("blank", "default"):
            self._clear_title(s, info)
        self.text(s, Inches(1), Inches(2.4), self.SW - Inches(2), Inches(1.6), [d.get("title") or "Perguntas?"],
                  size=60, min_size=40, bold=True, color=c["on_dark"], font=self.f["heading"],
                  align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, field="title")
        self.rect(s, (self.SW - Inches(1.2)) // 2, Inches(4.2), Inches(1.2), Inches(0.07), c["accent"])
        if d.get("contact"):
            self.text(s, Inches(1), Inches(4.5), self.SW - Inches(2), Inches(0.8), [d["contact"]], size=20,
                      min_size=13, color=c.get("on_dark_muted", "C9D3E0"), align=PP_ALIGN.CENTER, field="contact")

    # ---------- template: placeholders ----------
    def _fill_ph(self, s, idx, paras, size, field, bold=False, native_levels=False):
        ph = _ph(s, idx)
        if ph is None:
            return
        if not paras:
            _remove(ph)
            return
        tf = ph.text_frame
        norm = [{"text": p} if isinstance(p, str) else dict(p) for p in paras]
        fparas = [(d["text"], d.get("factor", 1), Inches(0.35) * (d.get("level", 0) + (1 if native_levels else 0)),
                   0.52 if (d.get("bold") or bold) else 0.48) for d in norm]
        sz, ok = fit(fparas, ph.width - Inches(0.2), ph.height - Inches(0.1), size, max(11, int(size * 0.55)))
        self.log(field, sz, ok)
        tf.clear()
        tf.word_wrap = True
        for i, d in enumerate(norm):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            if native_levels:
                p.level = d.get("level", 0)
            r = p.add_run()
            r.text = str(d["text"])
            r.font.size = Pt(round(sz * d.get("factor", 1), 1))
            if d.get("bold") or bold:
                r.font.bold = True

    def _clear_title(self, s, info):
        ph = _ph(s, (info[1] or {}).get("title"))
        if ph is not None:
            _remove(ph)

    # ---------- montagem ----------
    def add(self, d, n):
        a = d["archetype"]
        self.cur_id = d.get("id", f"#{n}")
        dark = a in DARK
        s, info = self.new_slide(a, dark)
        getattr(self, f"a_{a}")(d, s, info)
        if self.tpl:
            for ph in list(s.placeholders):
                if ph.has_text_frame and not ph.text_frame.text.strip() and \
                        ph.placeholder_format.type not in (PP_PLACEHOLDER.SLIDE_NUMBER, PP_PLACEHOLDER.FOOTER,
                                                           PP_PLACEHOLDER.DATE):
                    _remove(ph)
        self.footer(s, n, dark)
        if d.get("notes"):
            s.notes_slide.notes_text_frame.text = d["notes"]
        return s


def render_mathtext(latex, cache, color="1F3A5F", fontsize=44):
    """Equação -> PNG transparente via matplotlib mathtext (subconjunto do LaTeX). None se falhar."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1((latex + str(color)).encode()).hexdigest()[:12]
    out = cache / f"eq_{key}.png"
    if out.exists():
        return out
    expr = latex.strip()
    if not expr.startswith("$"):
        expr = f"${expr}$"
    try:
        fig = plt.figure(figsize=(0.01, 0.01))
        fig.text(0, 0, expr, fontsize=fontsize, color="#" + str(color).lstrip("#"))
        fig.savefig(out, dpi=220, transparent=True, bbox_inches="tight", pad_inches=0.08)
        plt.close(fig)
        return out
    except Exception:
        plt.close("all")
        return None


def render_mermaid(src, cache, colors, fonts):
    """Mermaid -> PNG com as cores do kit (precisa do mermaid-cli 'mmdc'). None se indisponível/erro."""
    mmdc = find_exe(["mmdc", "mmdc.cmd"])
    if not mmdc:
        return None
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1((src + json.dumps(colors, sort_keys=True)).encode()).hexdigest()[:12]
    out = cache / f"mmd_{key}.png"
    if out.exists():
        return out
    inp = cache / f"mmd_{key}.mmd"
    inp.write_text(src, encoding="utf-8")
    cfg = cache / "mermaid_config.json"
    cfg.write_text(json.dumps({"theme": "base", "themeVariables": {
        "primaryColor": "#" + colors["light"], "primaryTextColor": "#" + colors["text"],
        "primaryBorderColor": "#" + colors["primary"], "lineColor": "#" + colors["primary"],
        "secondaryColor": "#FFFFFF", "tertiaryColor": "#FFFFFF",
        "fontFamily": fonts["body"] + ", Arial, sans-serif", "fontSize": "22px"}}), encoding="utf-8")
    pup = cache / "puppeteer.json"
    pcfg = {"args": ["--no-sandbox", "--disable-setuid-sandbox"]}
    chrome = os.environ.get("STUDIO_CHROME") or os.environ.get("PUPPETEER_EXECUTABLE_PATH")
    if chrome:
        pcfg["executablePath"] = chrome
    pup.write_text(json.dumps(pcfg), encoding="utf-8")
    try:
        subprocess.run([mmdc, "-i", str(inp), "-o", str(out), "-c", str(cfg), "-p", str(pup), "-b", "transparent",
                        "-s", "3"], check=True, capture_output=True, timeout=120)
        return out if out.exists() else None
    except Exception:
        return None


def render_chart_png(ch, out, colors, palette, fonts, size=(10, 5.2)):
    """Gráfico do spec -> PNG via matplotlib (usado pelo backend Beamer e por documentos)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pal = ["#" + str(c).lstrip("#") for c in palette]
    plt.rcParams.update({"font.size": 15, "axes.edgecolor": "#" + colors["muted"],
                         "axes.labelcolor": "#" + colors["text"], "xtick.color": "#" + colors["text"],
                         "ytick.color": "#" + colors["muted"]})
    fig, ax = plt.subplots(figsize=size, dpi=200)
    cats, series, t = ch["categories"], ch["series"], ch["type"]
    pct = str(ch.get("number_format", "")).endswith("%")
    fmt = (lambda v: f"{v:.0%}") if pct else (lambda v: f"{v:g}")
    if t in ("pie", "doughnut"):
        vals = series[0]["values"]
        w, *_ = ax.pie(vals, labels=cats, colors=pal, autopct="%1.0f%%", startangle=90, counterclock=False,
                       wedgeprops={"width": 0.45} if t == "doughnut" else None, textprops={"fontsize": 14})
        ax.axis("equal")
    else:
        import numpy as np
        x = np.arange(len(cats))
        n = len(series)
        bw = 0.8 / n
        bottom = np.zeros(len(cats))
        for i, se in enumerate(series):
            v = np.array(se["values"], dtype=float)
            col = pal[i % len(pal)]
            if t == "line":
                ax.plot(cats, v, marker="o", lw=3, color=col, label=se["name"])
            elif t == "stacked_column":
                ax.bar(x, v, 0.6, bottom=bottom, color=col, label=se["name"])
                bottom += v
            elif t == "bar":
                ax.barh(x + (i - (n - 1) / 2) * bw, v, bw, color=col, label=se["name"])
            else:
                bars = ax.bar(x + (i - (n - 1) / 2) * bw, v, bw, color=col, label=se["name"])
                if n == 1:
                    hl = ch.get("highlight")
                    for b, c in zip(bars, cats):
                        if hl and c != hl:
                            b.set_color("#" + colors["primary"])
                        elif hl:
                            b.set_color("#" + colors["accent"])
                        ax.annotate(fmt(b.get_height()), (b.get_x() + b.get_width() / 2, b.get_height()),
                                    ha="center", va="bottom", fontsize=13, xytext=(0, 3), textcoords="offset points")
        if t == "bar":
            ax.set_yticks(x, cats)
            ax.invert_yaxis()
        elif t != "line":
            ax.set_xticks(x, cats)
        if pct:
            from matplotlib.ticker import PercentFormatter
            (ax.xaxis if t == "bar" else ax.yaxis).set_major_formatter(PercentFormatter(1.0))
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.grid(axis="x" if t == "bar" else "y", color="#" + colors["light"], lw=1)
        ax.set_axisbelow(True)
        if n > 1:
            ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=n)
    fig.tight_layout()
    fig.savefig(out, transparent=False, facecolor="white")
    plt.close(fig)
    return out


def _bullet(p, char, color, indent, level):
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(int(indent * (level + 1))))
    pPr.set("indent", str(-int(indent)))
    for tag in ("a:buClr", "a:buSzPct", "a:buFont", "a:buNone", "a:buChar", "a:buAutoNum"):
        for el in pPr.findall(qn(tag)):
            pPr.remove(el)
    from lxml import etree
    clr = etree.SubElement(pPr, qn("a:buClr"))
    etree.SubElement(clr, qn("a:srgbClr")).set("val", str(color).lstrip("#").upper())
    etree.SubElement(pPr, qn("a:buSzPct")).set("val", "75000" if char == "■" else "100000")
    etree.SubElement(pPr, qn("a:buFont")).set("typeface", "Arial")
    etree.SubElement(pPr, qn("a:buChar")).set("char", char)


def _ph(slide, idx):
    if idx is None:
        return None
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == idx:
            return ph
    return None


def _remove(shape):
    el = shape._element
    el.getparent().remove(el)


def _clear_slides(prs):
    lst = prs.slides._sldIdLst
    for sid in list(lst):
        prs.part.drop_rel(sid.rId)
        lst.remove(sid)


def _find_layout(prs, name):
    for m in prs.slide_masters:
        for l in m.slide_layouts:
            if l.name == name:
                return l
    raise SystemExit(f"ERRO: layout '{name}' não existe no template")


def resolve_kit_asset(p):
    if not p:
        return None
    for c in (Path(p), STUDIO / "kits" / p, STUDIO / "kits/assets" / p):
        if c.exists():
            return c
    return None


def potx_to_pptx(src, dst):
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "[Content_Types].xml":
                data = data.replace(b"presentationml.template.main+xml", b"presentationml.presentation.main+xml")
            zout.writestr(item, data)


def load_template(tid):
    d = STUDIO / "templates/pptx" / tid
    t = load_yaml(d / "template.yaml")
    f = d / t["file"]
    if f.suffix.lower() == ".potx":
        conv = d / (f.stem + "_converted.pptx")
        if not conv.exists():
            potx_to_pptx(f, conv)
        f = conv
    t["_pptx"] = f
    return t


# ----------------------------------------------------------------------------------------------------------
# 4. Comandos de build, prévia, QA, notas, templates
# ----------------------------------------------------------------------------------------------------------
def cmd_build(a):
    job = Path(a.job)
    iss = Issues()
    slides = load_slides(job, iss)
    for sl in slides:
        validate_slide(sl, sl.get("id", "?"), iss, job)
    if iss.errors:
        iss.print("Build bloqueado por erros de validação:")
        return 1
    brief = load_yaml(job / "brief.yaml", {})
    style = brief.get("style") or {}
    tid = a.template or (None if a.kit else style.get("template"))
    tpl = load_template(tid) if tid else None
    kit_id = a.kit or (tpl.get("kit") if tpl else None) or style.get("kit") or "default"
    kit = load_kit(kit_id)
    if not (kit.get("footer") or {}).get("text") and brief.get("title"):
        kit.setdefault("footer", {})["text"] = brief.get("title")
    deck = Deck(job, kit, tpl)
    index = []
    for n, sl in enumerate(slides, 1):
        deck.add(sl, n)
        index.append((n, sl.get("id"), sl.get("archetype"), sl.get("title") or sl.get("statement") or
                      sl.get("value") or ""))
    out = Path(a.out) if a.out else job / "build" / "deck.pptx"
    out.parent.mkdir(parents=True, exist_ok=True)
    deck.prs.core_properties.title = brief.get("title", "")
    deck.prs.core_properties.author = brief.get("author", "")
    deck.prs.save(out)
    over = [r for r in deck.report if not r["fits"]]
    (job / "build" / "build_report.json").write_text(json.dumps({"kit": kit_id, "template": tid, "slides": len(slides),
                                                                 "fit": deck.report}, ensure_ascii=False, indent=1),
                                                     encoding="utf-8")
    (job / "build" / "slides_index.md").write_text(
        "| Nº | ID | Arquétipo | Título |\n|---|---|---|---|\n" +
        "".join(f"| {n} | {i} | {ar} | {str(t)[:70]} |\n" for n, i, ar, t in index), encoding="utf-8")
    print(f"OK: {out} ({len(slides)} slides, kit={kit_id}, template={tid or '-'})")
    if over:
        print(f"AVISO: {len(over)} campo(s) não couberam no tamanho mínimo:")
        for r in over[:20]:
            print(f"  - {r['slide']}.{r['field']} {r.get('note', '')}")
    return 0


def cmd_preview(a):
    job = Path(a.job)
    pptx = Path(a.pptx) if a.pptx else job / "build" / "deck.pptx"
    if not pptx.exists():
        print("ERRO: rode 'build' antes.", file=sys.stderr)
        return 2
    soffice = find_exe(["soffice", "libreoffice"], SOFFICE_PATHS)
    if not soffice:
        print("AVISO: LibreOffice não encontrado; sem prévia. Instale-o (ver studio_doctor.py).")
        return 3
    with tempfile.TemporaryDirectory() as prof:
        r = subprocess.run([soffice, f"-env:UserInstallation={Path(prof).as_uri()}", "--headless", "--convert-to",
                            "pdf", "--outdir", str(pptx.parent), str(pptx)], capture_output=True, text=True,
                           timeout=300)
    pdf = pptx.with_suffix(".pdf")
    if not pdf.exists():
        print("ERRO: conversão para PDF falhou:", r.stderr[-500:], file=sys.stderr)
        return 1
    prev = job / "build" / ("previews" if not a.pptx else f"previews_{pptx.stem}")
    shutil.rmtree(prev, ignore_errors=True)
    prev.mkdir(parents=True)
    pngs = _pdf_to_png(pdf, prev, a.dpi)
    if pngs:
        _contact_sheet(pngs, job / "build" / ("contact_sheet.png" if not a.pptx else f"contact_sheet_{pptx.stem}.png"))
        print(f"OK: {pdf}, {len(pngs)} PNG(s) em {prev}/ e contact_sheet.png")
    else:
        print(f"OK: {pdf} (sem PNG: instale poppler/pdftoppm ou 'pip install pymupdf')")
    return 0


def _pdf_to_png(pdf, outdir, dpi):
    exe = find_exe(["pdftoppm"])
    if exe:
        subprocess.run([exe, "-png", "-r", str(dpi), str(pdf), str(outdir / "slide")], check=True,
                       capture_output=True, timeout=300)
        return sorted(outdir.glob("slide*.png"))
    try:
        import fitz
    except ImportError:
        return []
    doc = fitz.open(pdf)
    out = []
    for i, page in enumerate(doc, 1):
        p = outdir / f"slide-{i:02d}.png"
        page.get_pixmap(dpi=dpi).save(p)
        out.append(p)
    return out


def _contact_sheet(pngs, out, cols=4):
    from PIL import Image, ImageDraw
    ims = [Image.open(p).convert("RGB") for p in pngs]
    tw = 480
    th = int(ims[0].height * tw / ims[0].width)
    rows = math.ceil(len(ims) / cols)
    sheet = Image.new("RGB", (cols * (tw + 16) + 16, rows * (th + 40) + 16), "white")
    dr = ImageDraw.Draw(sheet)
    for i, im in enumerate(ims):
        r, c = divmod(i, cols)
        x, y = 16 + c * (tw + 16), 16 + r * (th + 40)
        sheet.paste(im.resize((tw, th)), (x, y))
        dr.rectangle([x, y, x + tw - 1, y + th - 1], outline=(200, 200, 200))
        dr.text((x, y + th + 6), f"{i + 1}", fill=(80, 80, 80))
    sheet.save(out)


def cmd_qa(a):
    job = Path(a.job)
    iss = Issues()
    slides = load_slides(job, iss, complete=True)
    for sl in slides:
        validate_slide(sl, sl.get("id", "?"), iss, job)
    rep = job / "build" / "build_report.json"
    if not rep.exists():
        iss.err("build", "build_report.json ausente: rode 'build'")
    else:
        data = json.loads(rep.read_text(encoding="utf-8"))
        for r in data["fit"]:
            if not r["fits"]:
                iss.err(r["slide"], f"'{r['field']}' não coube mesmo no tamanho mínimo {r.get('note', '')}".strip())
            elif r.get("warn"):
                iss.warn(r["slide"], r["warn"])
            elif r["field"] in ("bullets", "items") and r["size"] < 16:
                iss.warn(r["slide"], f"texto reduzido para {r['size']} pt em '{r['field']}': slide denso")
    for it in list(iss.items):
        if it.get("code") == "pending":
            it["level"] = "ERRO"
    seq = [s.get("archetype") for s in slides]
    for i in range(2, len(seq)):
        if seq[i] == seq[i - 1] == seq[i - 2] == "bullets":
            iss.warn(slides[i].get("id", "?"), "3 slides de tópicos seguidos: varie (statement, chart, process...)")
    if not (job / "build" / "contact_sheet.png").exists():
        iss.warn("preview", "sem prévia visual: rode 'preview' e inspecione contact_sheet.png")
    md = ["# QA do deck", "", f"Slides: {len(slides)}", "", iss.markdown(),
          "", "## Checagem visual (faça olhando contact_sheet.png e previews/)",
          "- [ ] Nenhum texto cortado ou encostando na borda",
          "- [ ] Títulos são frases-mensagem (dizem a conclusão), não rótulos",
          "- [ ] Um único foco por slide; nada compete com a mensagem",
          "- [ ] Gráficos legíveis a 3 m: rótulos ≥ 12 pt, destaque na série certa",
          "- [ ] Imagens nítidas, sem distorção, com fonte quando não forem próprias",
          "- [ ] Ritmo visual: alternância entre texto, número, imagem e diagrama"]
    (job / "build" / "qa_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    iss.print("QA:")
    print(f"Relatório: {job / 'build' / 'qa_report.md'}")
    return iss.exit_code()


def cmd_notes(a):
    job = Path(a.job)
    slides = load_slides(job)
    brief = load_yaml(job / "brief.yaml", {})
    out = [f"# Roteiro de fala: {brief.get('title', '')}", "",
           f"Duração alvo: {brief.get('duration_min', '?')} min · {len(slides)} slides", ""]
    total = 0
    for n, s in enumerate(slides, 1):
        t = s.get("title") or s.get("statement") or s.get("value") or s.get("archetype")
        w = words(s.get("notes", ""))
        total += w
        out += [f"## {n}. {t}  ({s.get('id')})", "", s.get("notes") or "_(sem notas)_", ""]
    out.insert(3, f"Palavras faladas: {total} (≈ {total / 130:.1f} min a 130 palavras/min)")
    (job / "build" / "speaker_notes.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"OK: {job / 'build' / 'speaker_notes.md'} ({total} palavras ≈ {total / 130:.1f} min)")
    return 0


def cmd_inspect(a):
    src = Path(a.file)
    d = STUDIO / "templates/pptx" / a.id
    d.mkdir(parents=True, exist_ok=True)
    dst = d / src.name
    if src.resolve() != dst.resolve():
        shutil.copy2(src, dst)
    path = dst
    if dst.suffix.lower() == ".potx":
        path = d / (dst.stem + "_converted.pptx")
        potx_to_pptx(dst, path)
    prs = Presentation(str(path))
    lines = [f"# Layouts de {src.name} ({prs.slide_width / 914400:.2f} x {prs.slide_height / 914400:.2f} in)"]
    guess = {}
    title_bottom = []
    names = {}
    for m in prs.slide_masters:
        for l in m.slide_layouts:
            phs = []
            for ph in l.placeholders:
                pf = ph.placeholder_format
                phs.append((pf.idx, str(pf.type).split(".")[-1].split(" ")[0], ph.name, ph.left, ph.top, ph.width,
                            ph.height))
            names[l.name] = phs
            lines.append(f"\n## {l.name}")
            for idx, typ, nm, x, y, w, h in phs:
                lines.append(f"- idx={idx} tipo={typ} nome='{nm}' pos=({(x or 0) / 914400:.2f},{(y or 0) / 914400:.2f}) "
                             f"tam=({(w or 0) / 914400:.2f}x{(h or 0) / 914400:.2f}) in")
    def find(pred):
        for n, phs in names.items():
            if pred(n.lower(), phs):
                return n, phs
        return None, None

    def idx_of(phs, kinds):
        for i, typ, *_ in phs:
            if any(k in typ for k in kinds):
                return i
        return None

    rules = [("title", lambda n, p: "title slide" in n or "capa" in n or "título" in n and "conte" not in n),
             ("section", lambda n, p: "section" in n or "seção" in n or "secao" in n),
             ("bullets", lambda n, p: ("title and content" in n or "título e conteúdo" in n)),
             ("two_column", lambda n, p: "two content" in n or "dois conte" in n or "comparison" in n),
             ("default", lambda n, p: "title only" in n or "somente título" in n or "apenas título" in n),
             ("blank", lambda n, p: n.strip() in ("blank", "em branco", "branco"))]
    for key, pred in rules:
        n, phs = find(pred)
        if not n:
            continue
        g = {"layout": n, "title": idx_of(phs, ["TITLE", "CENTER_TITLE"])}
        if key in ("title", "section"):
            g["subtitle"] = idx_of(phs, ["SUBTITLE", "BODY"])
        if key == "bullets":
            g["body"] = idx_of(phs, ["BODY", "OBJECT"])
        if key == "two_column":
            bodies = [i for i, typ, *_ in phs if "BODY" in typ or "OBJECT" in typ]
            if len(bodies) >= 2:
                g["left"], g["right"] = bodies[0], bodies[1]
            else:
                continue
        if key == "default":
            for i, typ, nm, x, y, w, h in phs:
                if "TITLE" in typ and y is not None and h is not None:
                    title_bottom.append((y + h) / 914400)
        guess[key] = g
    if "default" not in guess and "bullets" in guess:
        guess["default"] = {"layout": guess["bullets"]["layout"], "title": guess["bullets"]["title"]}
    sw, sh = prs.slide_width / 914400, prs.slide_height / 914400
    top = round((max(title_bottom) if title_bottom else 1.4) + 0.25, 2)
    tpl = {"id": a.id, "file": src.name, "kit": a.kit or a.id,
           "layouts": guess,
           "content_box": {"left": 0.6, "top": top, "width": round(sw - 1.2, 2), "height": round(sh - top - 0.7, 2)},
           "notes": "Revise: confira cada mapeamento com o layout real e ajuste content_box. Arquétipos sem layout "
                    "próprio são desenhados no layout 'default' com as cores do kit."}
    dump_yaml(tpl, d / "template.yaml")
    (d / "layouts.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not (STUDIO / "kits" / f"{tpl['kit']}.yaml").exists():
        print(f"AVISO: crie o kit studio/kits/{tpl['kit']}.yaml com as cores e fontes da marca "
              f"(copie default.yaml).")
    print(f"OK: {d}/template.yaml (rascunho) e layouts.md. Mapeados: {', '.join(guess) or 'nenhum'}")
    return 0


def cmd_kit_check(a):
    k = load_kit(a.kit)
    c = k["colors"]
    iss = Issues()
    for need in ("primary", "accent", "text", "muted", "light", "background", "dark", "on_dark"):
        if need not in c:
            iss.err("colors", f"cor ausente: {need}")
    pairs = [("text", "background", 7), ("primary", "background", 4.5), ("muted", "background", 4.5),
             ("on_dark", "dark", 7), ("accent", "background", 3), ("on_dark", "primary", 4.5),
             ("on_dark", "accent", 3)]
    for f, b, mn in pairs:
        if f in c and b in c:
            r = contrast(c[f], c[b])
            if r < mn:
                iss.warn(f"{f}/{b}", f"contraste {r:.1f}:1 (mínimo recomendado {mn}:1)")
            else:
                print(f"  ok {f}/{b}: {r:.1f}:1")
    if k.get("logo") and not resolve_kit_asset(k["logo"]):
        iss.err("logo", f"arquivo não encontrado: {k['logo']}")
    iss.print(f"Kit {a.kit}:")
    return iss.exit_code()


def cmd_archetypes(a):
    if not a.md:
        for k, v in ARCH.items():
            print(f"{k:12s} obrig.: {', '.join(v['req']) or '-':28s} {v['use']}")
        return 0

    def fmt(spec):
        k = spec[0]
        if k == "str":
            return f"texto ≤{spec[1]}"
        if k == "words":
            return f"texto ≤{spec[1]} palavras"
        if k == "bullet":
            return f"tópico ≤{spec[1]} (ou {{text, sub: [≤3]}})"
        if k == "list":
            return f"lista {spec[1]}–{spec[2]} de ({fmt(spec[3])})"
        if k == "obj":
            return "{" + ", ".join(f"{n}{'*' if n in spec[2] else ''}: {fmt(s)}" for n, s in spec[1].items()) + "}"
        if k == "enum":
            return "|".join(spec[1])
        if k == "code":
            return f"bloco ≤{spec[1]} linhas x {spec[2]} col"
        return {"path": "caminho de arquivo", "bool": "true/false", "int": "inteiro", "numbers": "lista de números",
                "latex": "LaTeX"}.get(k, k)

    out = ["# Arquétipos de slide (gerado por mf_deck.py archetypes --md; não editar)", "",
           "Campos comuns a todos: `id`* (SL-01), `archetype`*, `notes` (≤180 palavras), `sources` (lista), "
           "`hidden`. Campos com * são obrigatórios.", ""]
    for k, v in ARCH.items():
        out += [f"## {k}", v["use"], ""]
        for n, s in v["fields"].items():
            out.append(f"- `{n}`{'*' if n in v['req'] else ''}: {fmt(s)}")
        out.append("")
    text = "\n".join(out)
    dest = STUDIO / "formats/deck/archetypes.md"
    dest.write_text(text, encoding="utf-8")
    print(f"OK: {dest}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new"); p.add_argument("job"); p.add_argument("--blueprint")
    p.add_argument("--kit", default="default"); p.add_argument("--template"); p.set_defaults(fn=cmd_new)
    p = sub.add_parser("archetypes"); p.add_argument("--md", action="store_true"); p.set_defaults(fn=cmd_archetypes)
    p = sub.add_parser("plan"); p.add_argument("job"); p.add_argument("--per-unit", type=int, default=6)
    p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("validate"); p.add_argument("job"); p.add_argument("--unit")
    p.add_argument("--complete", action="store_true"); p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("build"); p.add_argument("job"); p.add_argument("--kit"); p.add_argument("--template")
    p.add_argument("--out"); p.set_defaults(fn=cmd_build)
    p = sub.add_parser("preview"); p.add_argument("job"); p.add_argument("--dpi", type=int, default=80)
    p.add_argument("--pptx", help="outro .pptx do job (padrão: build/deck.pptx)")
    p.set_defaults(fn=cmd_preview)
    p = sub.add_parser("qa"); p.add_argument("job"); p.set_defaults(fn=cmd_qa)
    p = sub.add_parser("notes"); p.add_argument("job"); p.set_defaults(fn=cmd_notes)
    p = sub.add_parser("inspect-template"); p.add_argument("file"); p.add_argument("--id", required=True)
    p.add_argument("--kit"); p.set_defaults(fn=cmd_inspect)
    p = sub.add_parser("kit-check"); p.add_argument("kit"); p.set_defaults(fn=cmd_kit_check)
    a = ap.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
