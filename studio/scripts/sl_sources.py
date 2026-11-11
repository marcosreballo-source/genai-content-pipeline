#!/usr/bin/env python3
"""sl_sources.py: Source Library do Studio — bibliografia oficial, trechos, fichas fiéis e cobertura.

Princípio: nenhum material é produzido "de memória". Cada fonte é dividida em trechos pequenos (4 páginas, ou
~1500 palavras para textos/transcrições); para cada trecho o agente escreve UMA ficha (card) com transcrição
literal do que é definição/teorema/fórmula/algoritmo e paráfrase do resto. O script confere se a ficha não
resumiu demais, monta o índice de conceitos e diz, para um Knowledge Graph, o que está sem fonte, gerando
pedidos de bibliografia para o usuário providenciar.

Biblioteca: studio/sources/ledger.yaml + studio/sources/<SRC-id>/{chunks/, cards/}

Comandos:
  add <arquivo|URL> --type book|paper|docs|site|video|slides|list|transcript|notes --title ... [--authors "A; B"]
      [--year 2020] [--id SRC-x] [--copy] [--authority 0-10] [--origin <pipeline>]
  chunk <SRC> [--pages 4 | --words 1500]   divide PDF (com texto extraído) ou texto
  import-chunks <SRC> --dir <pasta>          registra trechos já gerados pelo seu pipeline de triagem
  next <SRC>                                 próximo trecho pendente + esqueleto da ficha
  validate <SRC> [--chunk C0003]             fidelidade das fichas (supersumarização, transcrições, campos)
  status [SRC]                               progresso
  index                                      índice de conceitos (concept_index.json)
  find "<termo>"                             onde um conceito aparece (fichas e texto dos trechos)
  pack --concepts "a; b" [--max-words 900]   pacote de fundamentação para um redator (só trechos literais)
  coverage --graph <knowledge_graph.md> [--source-report <source_report.md>] [--policy strict|warn] [--out <pasta>]
  requests [--open]                          pedidos de bibliografia
  fulfill <REQ-001> --source <SRC>           marca pedido como atendido
  bib [--out references.bib] [--only SRC-a,SRC-b]
"""
import argparse
import datetime
import json
import math
import os
import re
import shutil
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from studio_common import (STUDIO, UNIT_MAX_WORDS, Issues, dump_yaml, frontmatter_and_yaml_blocks,  # noqa: E402
                           load_yaml, slug, words)

LIB = Path(os.environ.get("STUDIO_SOURCES") or (STUDIO / "sources"))
LEDGER = LIB / "ledger.yaml"
TYPES = ["book", "paper", "docs", "site", "video", "slides", "list", "transcript", "notes", "standard", "repo"]
ITEM_TYPES = ["definition", "theorem", "lemma", "corollary", "proposition", "formula", "algorithm", "table",
              "example", "exercise", "claim", "figure", "quote", "procedure"]
MARKERS = re.compile(r"\b(Defini[çc][ãa]o|Definition|Teorema|Theorem|Lema|Lemma|Corol[áa]rio|Corollary|"
                     r"Proposi[çc][ãa]o|Proposition|Algoritmo|Algorithm|Exemplo|Example|Exerc[íi]cio|Exercise)"
                     r"\s+(\d+(\.\d+)*)", re.I)
SUGGEST = {
    "foundation": "capítulo de livro-texto clássico da área ou notas de aula de professor",
    "core": "livro-texto ou apostila de disciplina; documentação oficial se for ferramenta",
    "advanced": "artigo científico (survey ou original), capítulo avançado ou documentação oficial",
    "optional": "artigo, post técnico de fonte reconhecida ou vídeo de palestra",
}


def now():
    return datetime.date.today().isoformat()


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(w[:-1] if len(w) > 4 and w.endswith("s") else w for w in s.split())


def ledger():
    return load_yaml(LEDGER, {"sources": {}, "requests": {}})


def save_ledger(L):
    dump_yaml(L, LEDGER)


def src_dir(sid):
    return LIB / sid


def get_src(L, sid):
    if sid not in L["sources"]:
        raise SystemExit(f"ERRO: fonte {sid} não registrada (veja 'status').")
    return L["sources"][sid]


def chunk_list(sid):
    d = src_dir(sid) / "chunks"
    ids = sorted({p.stem.split(".")[0] for p in d.glob("C*.*")}) if d.exists() else []
    meta = load_yaml(d / "chunks.yaml", {"chunks": {}}).get("chunks", {}) if d.exists() else {}
    return ids, meta


def card_paths(sid, cid):
    d = src_dir(sid) / "cards"
    return sorted(d.glob(f"{cid}.yaml")) + sorted(d.glob(f"{cid}.*.yaml"))


# ----------------------------------------------------------------------------------------------------------
def cmd_add(a):
    L = ledger()
    title = a.title or Path(a.path).stem
    authors = [x.strip() for x in (a.authors or "").split(";") if x.strip()]
    base = slug((authors[0].split(",")[0].split()[-1] if authors else title.split()[0]) + "-" + str(a.year or ""), 30)
    sid = a.id or f"SRC-{base}".rstrip("-")
    if sid in L["sources"]:
        k = 2
        while f"{sid}-{k}" in L["sources"]:
            k += 1
        sid = f"{sid}-{k}"
    d = src_dir(sid)
    (d / "chunks").mkdir(parents=True, exist_ok=True)
    (d / "cards").mkdir(parents=True, exist_ok=True)
    loc = a.path
    pages = None
    if not re.match(r"^https?://", a.path):
        p = Path(a.path)
        if not p.exists():
            raise SystemExit(f"ERRO: arquivo não encontrado: {p}")
        if a.copy:
            dst = d / f"original{p.suffix.lower()}"
            shutil.copy2(p, dst)
            loc = dst.as_posix()
        else:
            loc = p.resolve().as_posix()
        if p.suffix.lower() == ".pdf":
            try:
                from pypdf import PdfReader
                pages = len(PdfReader(str(p)).pages)
            except Exception as e:  # pragma: no cover
                print(f"AVISO: não consegui contar páginas ({e})")
    key = slug((authors[0].split(",")[0].split()[-1] if authors else title.split()[0]), 20).replace("-", "") + \
        str(a.year or "")
    L["sources"][sid] = {"title": title, "authors": authors, "year": a.year, "type": a.type, "location": loc,
                         "pages": pages, "authority": a.authority, "bibtex_key": key, "origin": a.origin,
                         "publisher": a.publisher, "url": a.path if a.path.startswith("http") else None,
                         "status": "registered", "added": now()}
    save_ledger(L)
    print(f"OK: {sid} registrada ({a.type}, {pages or '?'} págs.). Próximo: chunk {sid}  (ou import-chunks)")
    return 0


def cmd_chunk(a):
    L = ledger()
    s = get_src(L, a.sid)
    d = src_dir(a.sid) / "chunks"
    loc = Path(s["location"]) if s.get("location") and not str(s["location"]).startswith("http") else None
    meta = {}
    if loc and loc.suffix.lower() == ".pdf":
        from pypdf import PdfReader, PdfWriter
        r = PdfReader(str(loc))
        n = len(r.pages)
        per = a.pages
        low_text = 0
        for i in range(math.ceil(n / per)):
            cid = f"C{i + 1:04d}"
            p0, p1 = i * per, min(n, (i + 1) * per)
            w = PdfWriter()
            text = []
            for k in range(p0, p1):
                w.add_page(r.pages[k])
                t = r.pages[k].extract_text() or ""
                text.append(f"\n[[página {k + 1}]]\n{t}")
            with open(d / f"{cid}.pdf", "wb") as fh:
                w.write(fh)
            joined = "".join(text)
            (d / f"{cid}.txt").write_text(joined, encoding="utf-8")
            if len(joined.strip()) < 60 * (p1 - p0):
                low_text += 1
            meta[cid] = {"loc": [p0 + 1, p1], "unit": "page", "words": words(joined)}
        s["chunk_pages"] = per
        if low_text > len(meta) * 0.3:
            print(f"AVISO: {low_text} trechos quase sem texto: PDF escaneado? Rode OCR (ex.: ocrmypdf) ou use "
                  f"seu pipeline e 'import-chunks'. Até lá, leia as páginas do PDF do trecho como imagem.")
    else:
        src_text = None
        if loc and loc.exists():
            src_text = loc.read_text(encoding="utf-8", errors="replace")
        elif a.text:
            src_text = Path(a.text).read_text(encoding="utf-8", errors="replace")
        if not src_text:
            raise SystemExit("ERRO: fonte não é PDF local; passe --text <arquivo .md/.txt> com o conteúdo "
                             "(página salva, transcrição, notas).")
        ws = src_text.split("\n")
        cur, cw, k = [], 0, 1
        for line in ws + [None]:
            if line is None or (cw >= a.words and line.strip() == "") or cw >= a.words * 1.4:
                if cur:
                    cid = f"C{k:04d}"
                    body = "\n".join(cur)
                    (d / f"{cid}.txt").write_text(body, encoding="utf-8")
                    ts = re.findall(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\b", body)
                    meta[cid] = {"loc": [ts[0], ts[-1]] if ts else [f"bloco {k}"], "unit": "time" if ts else "block",
                                 "words": words(body)}
                    k += 1
                cur, cw = [], 0
                if line is None:
                    break
            if line is not None:
                cur.append(line)
                cw += len(line.split())
    dump_yaml({"chunks": meta}, d / "chunks.yaml")
    s["status"] = "chunked"
    s["chunks"] = len(meta)
    save_ledger(L)
    print(f"OK: {len(meta)} trecho(s) em {d}. Processe um por rodada: 'next {a.sid}'.")
    return 0


def cmd_import(a):
    L = ledger()
    s = get_src(L, a.sid)
    d = src_dir(a.sid) / "chunks"
    files = sorted(p for p in Path(a.dir).iterdir() if p.suffix.lower() in (".pdf", ".txt", ".md"))
    if not files:
        raise SystemExit(f"ERRO: nada em {a.dir}")
    groups = {}
    for f in files:
        groups.setdefault(f.stem, []).append(f)
    meta = {}
    per = a.pages
    for i, (stem, fs) in enumerate(sorted(groups.items()), 1):
        cid = f"C{i:04d}"
        m = re.search(r"p?(\d+)\s*[-_a]+\s*p?(\d+)", stem)
        loc = [int(m.group(1)), int(m.group(2))] if m else [(i - 1) * per + 1, i * per]
        txt = ""
        for f in fs:
            shutil.copy2(f, d / f"{cid}{f.suffix.lower()}")
            if f.suffix.lower() in (".txt", ".md"):
                txt = f.read_text(encoding="utf-8", errors="replace")
        if txt and f.suffix.lower() == ".md":
            (d / f"{cid}.txt").write_text(txt, encoding="utf-8")
        meta[cid] = {"loc": loc, "unit": "page", "words": words(txt), "imported_from": stem}
    dump_yaml({"chunks": meta}, d / "chunks.yaml")
    s["status"], s["chunks"], s["origin"] = "chunked", len(meta), s.get("origin") or a.dir
    save_ledger(L)
    print(f"OK: {len(meta)} trecho(s) importados de {a.dir} (originais intactos).")
    return 0


CARD_TEMPLATE = """# Ficha do trecho {cid} de {sid} ({loc}). Regras: studio/agent_files/skills/sl-extract/SKILL.md
source: {sid}
chunk: {cid}
loc: {locv}            # páginas/tempos cobertos por este trecho
status: done           # done | partial | skipped
skip_reason: ""        # obrigatório se skipped (ex.: índice remissivo, página em branco)
summary: ""            # 2-4 frases: o que o trecho cobre
concepts:              # TODO conceito nomeado no trecho (nunca omitir)
  - name: ""
    aliases: []
    loc: 0             # página (ou tempo) onde aparece
    definition: ""     # LITERAL quando o trecho define o conceito; vazio se só é mencionado
items:                 # TRANSCRIÇÃO LITERAL de definições, teoremas, fórmulas, algoritmos, tabelas pequenas
  - type: definition   # {types}
    label: ""          # ex.: "Definição 2.3", "Eq. (4.1)", "Algoritmo BFS"
    loc: 0
    text: |
      ...
key_points: []         # paráfrases curtas do restante (cada uma com (p. N) no fim)
figures: []            # [{{label, loc, description, reusable: true|false}}]
open_questions: []     # o que ficou ilegível/ambíguo
"""


def cmd_next(a):
    ids, meta = chunk_list(a.sid)
    for cid in ids:
        if not card_paths(a.sid, cid):
            m = meta.get(cid, {})
            loc = m.get("loc", [])
            d = src_dir(a.sid) / "chunks"
            print(f"Próximo trecho: {cid} ({m.get('unit', 'page')} {loc}) · ~{m.get('words', '?')} palavras")
            for ext in (".txt", ".pdf", ".md"):
                if (d / f"{cid}{ext}").exists():
                    print(f"  ler: {(d / f'{cid}{ext}').as_posix()}")
            print(f"  escrever: {(src_dir(a.sid) / 'cards' / f'{cid}.yaml').as_posix()}"
                  f"  (se passar de {UNIT_MAX_WORDS} palavras: {cid}.a.yaml, {cid}.b.yaml)")
            print("\n" + CARD_TEMPLATE.format(cid=cid, sid=a.sid, loc=loc, locv=json.dumps(loc),
                                              types=" | ".join(ITEM_TYPES)))
            return 0
    print(f"Todos os {len(ids)} trechos de {a.sid} têm ficha. Rode 'validate {a.sid}' e 'index'.")
    return 0


def shingles(t, n=5):
    w = norm(t).split()
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def validate_card(sid, cid, cards, chunk_txt, meta, iss):
    where = f"{sid}/{cid}"
    loc = meta.get("loc") or []
    all_items, all_concepts, total_words = [], [], 0
    status = None
    for cp in cards:
        try:
            c = load_yaml(cp, {})
        except ValueError as e:
            iss.err(where, str(e))
            return
        total_words += words(c)
        status = c.get("status", status)
        if c.get("status") == "skipped":
            if not c.get("skip_reason"):
                iss.err(where, "status skipped sem skip_reason")
            continue
        if not c.get("summary"):
            iss.err(where, "summary vazio")
        for i, k in enumerate(c.get("concepts") or []):
            if not (k or {}).get("name"):
                iss.err(f"{where}.concepts[{i}]", "conceito sem nome")
            if (k or {}).get("loc") in (None, "", 0) and (k or {}).get("page") in (None, "", 0):
                iss.err(f"{where}.concepts[{i}]", "conceito sem loc (página/tempo)")
            all_concepts.append(k)
        for i, it in enumerate(c.get("items") or []):
            it = it or {}
            if it.get("type") not in ITEM_TYPES:
                iss.err(f"{where}.items[{i}]", f"type '{it.get('type')}' inválido")
            if not str(it.get("text", "")).strip() or str(it.get("text", "")).strip() == "...":
                iss.err(f"{where}.items[{i}]", "transcrição vazia")
            if it.get("loc") in (None, "", 0) and it.get("page") in (None, "", 0):
                iss.err(f"{where}.items[{i}]", "item sem loc")
            all_items.append(it)
        if words(c) > UNIT_MAX_WORDS:
            iss.err(where, f"ficha {cp.name} com {words(c)} palavras: divida em {cid}.a.yaml/{cid}.b.yaml")
    if status == "skipped":
        return
    if loc and meta.get("unit") == "page":
        for k in all_concepts + all_items:
            v = (k or {}).get("loc") or (k or {}).get("page")
            if isinstance(v, int) and not (loc[0] <= v <= loc[-1]):
                iss.warn(where, f"loc {v} fora do trecho {loc}")
    if chunk_txt:
        found = {m.group(0).lower() for m in MARKERS.finditer(chunk_txt)}
        typed = [it for it in all_items if it.get("type") in ("definition", "theorem", "lemma", "corollary",
                                                               "proposition", "algorithm", "example", "exercise")]
        if found and len(typed) < 0.7 * len(found):
            iss.err(where, f"possível supersumarização: {len(found)} marcadores no texto "
                           f"({', '.join(sorted(found)[:6])}) e só {len(typed)} item(ns) transcritos")
        cw = words(chunk_txt)
        if cw > 400 and total_words < 0.12 * cw:
            iss.warn(where, f"ficha com {total_words} palavras para trecho de {cw} ({total_words / cw:.0%}): "
                            f"confira se nada foi omitido")
        src_sh = shingles(chunk_txt)
        for i, it in enumerate(all_items):
            if it.get("type") in ("figure",):
                continue
            sh = shingles(it.get("text", ""))
            if len(sh) >= 3 and src_sh:
                hit = len(sh & src_sh) / len(sh)
                if hit < 0.35:
                    iss.warn(f"{where}.items[{i}]", f"transcrição não bate com o texto do trecho ({hit:.0%} de "
                                                    f"sobreposição): é paráfrase? OCR ruim? Marque verbatim: false")
    if not all_concepts and not all_items:
        iss.warn(where, "ficha sem conceitos nem itens")


def cmd_validate(a):
    L = ledger()
    s = get_src(L, a.sid)
    ids, meta = chunk_list(a.sid)
    iss = Issues()
    done = 0
    for cid in ids:
        if a.chunk and cid != a.chunk:
            continue
        cards = card_paths(a.sid, cid)
        if not cards:
            if a.chunk:
                iss.err(cid, "ficha ainda não escrita")
            continue
        txtf = src_dir(a.sid) / "chunks" / f"{cid}.txt"
        validate_card(a.sid, cid, cards, txtf.read_text(encoding="utf-8", errors="replace") if txtf.exists()
                      else "", meta.get(cid, {}), iss)
        done += 1
    pend = [c for c in ids if not card_paths(a.sid, c)]
    if not a.chunk:
        s["status"] = "extracted" if not pend else "extracting"
        s["cards_done"] = len(ids) - len(pend)
        save_ledger(L)
    iss.print(f"Fichas de {a.sid}: {done} validadas, {len(pend)} pendentes.")
    return iss.exit_code()


def cmd_status(a):
    L = ledger()
    rows = []
    for sid, s in L["sources"].items():
        if a.sid and sid != a.sid:
            continue
        ids, _ = chunk_list(sid)
        n = len(ids)
        done = sum(1 for c in ids if card_paths(sid, c))
        rows.append((sid, s.get("type"), n, done, s.get("status"), s.get("title", "")[:50]))
    print(f"{'Fonte':28s} {'tipo':8s} {'trechos':>7s} {'fichas':>6s}  status       título")
    for r in rows:
        pct = f"{r[3] / r[2]:.0%}" if r[2] else "-"
        print(f"{r[0]:28s} {r[1] or '':8s} {r[2]:7d} {r[3]:6d}  {r[4] or '':12s} {r[5]}  ({pct})")
    op = [k for k, v in (L.get("requests") or {}).items() if v.get("status") != "atendido"]
    print(f"\nPedidos de bibliografia abertos: {len(op)}" + (f" ({', '.join(op[:8])})" if op else ""))
    return 0


def build_index():
    L = ledger()
    idx = {}
    for sid in L["sources"]:
        for cp in sorted((src_dir(sid) / "cards").glob("C*.yaml")):
            try:
                c = load_yaml(cp, {})
            except ValueError:
                continue
            if c.get("status") == "skipped":
                continue
            for k in c.get("concepts") or []:
                if not k or not k.get("name"):
                    continue
                entry = {"src": sid, "chunk": cp.stem.split(".")[0], "loc": k.get("loc") or k.get("page"),
                         "definition": bool(k.get("definition")), "name": k["name"]}
                for nm in [k["name"]] + list(k.get("aliases") or []):
                    idx.setdefault(norm(nm), []).append(entry)
            for it in c.get("items") or []:
                if it and it.get("label"):
                    idx.setdefault(norm(it["label"]), []).append({"src": sid, "chunk": cp.stem.split(".")[0],
                                                                  "loc": it.get("loc"), "definition":
                                                                  it.get("type") == "definition",
                                                                  "name": it["label"]})
    (LIB / "concept_index.json").write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    return idx


def cmd_index(a):
    idx = build_index()
    print(f"OK: {len(idx)} termos indexados em {LIB / 'concept_index.json'}")
    return 0


def lookup(idx, name, aliases=()):
    keys = [norm(x) for x in [name, *aliases] if x]
    hits = []
    for k in keys:
        hits += idx.get(k, [])
    if not hits:
        for k in keys:
            kt = set(k.split())
            for ik, v in idx.items():
                it = set(ik.split())
                if kt and it and len(kt & it) / len(kt | it) >= 0.6:
                    hits += v
    seen, out = set(), []
    for h in hits:
        key = (h["src"], h["chunk"], str(h["loc"]))
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out


def cmd_find(a):
    idx = build_index()
    hits = lookup(idx, a.term)
    for h in hits:
        print(f"ficha  {h['src']}#{h['chunk']} loc {h['loc']}  {'[definição]' if h['definition'] else ''} {h['name']}")
    t = norm(a.term)
    n = 0
    for sid in ledger()["sources"]:
        for f in sorted((src_dir(sid) / "chunks").glob("C*.txt")):
            if t and t in norm(f.read_text(encoding="utf-8", errors="replace")):
                print(f"texto  {sid}#{f.stem}")
                n += 1
                if n > 20:
                    break
    if not hits and not n:
        print("Nada encontrado. Se o conceito é necessário, gere um pedido de bibliografia (coverage).")
    return 0


def cmd_pack(a):
    idx = build_index()
    out, total = ["# Pacote de fundamentação (trechos literais; cite como SRC#Cxxxx, p. N)", ""], 0
    seen_txt = set()
    for concept in [c.strip() for c in a.concepts.split(";") if c.strip()]:
        hits = sorted(lookup(idx, concept), key=lambda h: not h["definition"])
        out.append(f"## {concept}")
        if not hits:
            out.append("_SEM FONTE na biblioteca: não invente; registre lacuna._")
            continue
        for h in hits[:4]:
            for cp in card_paths(h["src"], h["chunk"]):
                c = load_yaml(cp, {})
                for k in c.get("concepts") or []:
                    if k and norm(k.get("name", "")) == norm(h["name"]) and k.get("definition"):
                        blk = f"- [{h['src']}#{h['chunk']}, p. {k.get('loc')}] {k['definition']}"
                        if norm(k["definition"]) in seen_txt:
                            continue
                        seen_txt.add(norm(k["definition"]))
                        out.append(blk)
                        total += words(blk)
                for it in c.get("items") or []:
                    if it and (norm(concept) in norm(it.get("label", "")) or norm(concept) in norm(it.get("text", ""))):
                        blk = f"- [{h['src']}#{h['chunk']}, p. {it.get('loc')}] {it.get('label', '')}: {it.get('text', '').strip()}"
                        if norm(it.get("text", "")) in seen_txt:
                            continue
                        seen_txt.add(norm(it.get("text", "")))
                        out.append(blk)
                        total += words(blk)
            if total > a.max_words:
                break
        out.append("")
        if total > a.max_words:
            out.append(f"_(limite de {a.max_words} palavras atingido)_")
            break
    text = "\n".join(out) + "\n"
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"OK: {a.out} ({total} palavras)")
    else:
        print(text)
    return 0


def parse_graph(path):
    text = Path(path).read_text(encoding="utf-8")
    _, blocks = frontmatter_and_yaml_blocks(text)
    for b in blocks:
        if isinstance(b, dict) and isinstance(b.get("nodes"), list):
            return b["nodes"]
    raise SystemExit("ERRO: bloco YAML com 'nodes:' não encontrado no grafo")


def parse_source_report(path):
    if not path:
        return {}
    _, blocks = frontmatter_and_yaml_blocks(Path(path).read_text(encoding="utf-8"))
    for b in blocks:
        if isinstance(b, dict) and isinstance(b.get("sources"), list):
            return {s.get("id"): s for s in b["sources"] if isinstance(s, dict)}
    return {}


def all_items():
    out = []
    for sid in ledger()["sources"]:
        for cp in sorted((src_dir(sid) / "cards").glob("C*.yaml")):
            try:
                c = load_yaml(cp, {})
            except ValueError:
                continue
            for it in c.get("items") or []:
                if it and it.get("text"):
                    out.append({"src": sid, "chunk": cp.stem.split(".")[0], "loc": it.get("loc"),
                                "type": it.get("type"), "label": it.get("label", ""), "n": norm(it["text"])})
    return out


def cmd_coverage(a):
    idx = build_index()
    items = all_items()
    L = ledger()
    nodes = parse_graph(a.graph)
    srep = parse_source_report(a.source_report)
    rows, gaps = [], []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        if n.get("effort_minutes") == 0:
            rows.append((n.get("id"), n.get("name"), "assumido", "conhecido do público", ""))
            continue
        hits = lookup(idx, n.get("name", ""), n.get("aliases") or [])
        names = [norm(x) for x in [n.get("name", ""), *(n.get("aliases") or [])] if x]
        for it in items:
            if it["type"] in ("definition", "theorem", "algorithm", "procedure", "formula") and \
                    any(nm and re.search(r"\b%s\b" % re.escape(nm), it["n"]) for nm in names):
                hits.append({"src": it["src"], "chunk": it["chunk"], "loc": it["loc"], "definition": True,
                             "name": it["label"]})
        lib_ids = {srep.get(s, {}).get("library_id") for s in n.get("sources") or []} - {None}
        hits_auth = [h for h in hits if (L["sources"].get(h["src"], {}).get("authority") or 7) >= 6]
        defs = [h for h in hits if h["definition"]]
        if defs or len(hits_auth) >= 2:
            st = "coberto"
        elif hits:
            st = "fraco"
        else:
            st = "sem fonte"
        ev = "; ".join(dict.fromkeys(f"{h['src']}#{h['chunk']} p.{h['loc']}" for h in hits))
        ev = "; ".join(ev.split("; ")[:3])
        decl = ", ".join(sorted(lib_ids)) or "-"
        rows.append((n.get("id"), n.get("name"), st, ev or "-", decl))
        if st != "coberto" and n.get("criticality", "important") in ("essential", "important"):
            gaps.append((n, st))
    reqs = L.setdefault("requests", {}) or {}
    L["requests"] = reqs
    gkey = Path(a.graph).as_posix()
    existing = {(r.get("node"), r.get("graph")) for r in reqs.values()}
    new = []
    for n, st in gaps:
        key = (n.get("id"), gkey)
        if key in existing:
            continue
        rid = f"REQ-{len(reqs) + 1:03d}"
        reqs[rid] = {"node": n.get("id"), "concept": n.get("name"), "graph": gkey, "situation": st,
                     "criticality": n.get("criticality"), "level": n.get("level"),
                     "why": f"atende {', '.join(n.get('outcomes') or []) or 'objetivos do projeto'}",
                     "suggested": SUGGEST.get(n.get("level"), SUGGEST["core"]),
                     "status": "aguardando_usuario", "opened": now()}
        new.append(rid)
    save_ledger(L)
    out = Path(a.out) if a.out else Path(a.graph).parent
    out.mkdir(parents=True, exist_ok=True)
    cnt = {k: sum(1 for r in rows if r[2] == k) for k in ("coberto", "fraco", "sem fonte", "assumido")}
    md = ["# Cobertura bibliográfica do Knowledge Graph", "", f"Grafo: `{a.graph}` · gerado em {now()}", "",
          f"**Coberto:** {cnt['coberto']} · **Fraco:** {cnt['fraco']} · **Sem fonte:** {cnt['sem fonte']} · "
          f"**Assumido:** {cnt['assumido']}", "",
          "| Nó | Conceito | Situação | Evidência na biblioteca | Fontes declaradas |", "|---|---|---|---|---|"]
    md += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |" for r in rows]
    openreq = {k: v for k, v in reqs.items() if v.get("status") != "atendido" and v.get("graph") == gkey}
    md += ["", "## Pedidos de bibliografia (providencie e registre com sl_sources.py add)", ""]
    if openreq:
        md += ["| Pedido | Conceito | Situação | Por quê | Tipo de fonte sugerido |", "|---|---|---|---|---|"]
        md += [f"| {k} | {v['concept']} | {v['situation']} | {v['why']} | {v['suggested']} |" for k, v in openreq.items()]
    else:
        md.append("Nenhum.")
    (out / "coverage_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Cobertura: {cnt}. Relatório: {out / 'coverage_report.md'}")
    if new:
        print(f"{len(new)} pedido(s) de bibliografia novo(s): {', '.join(new)}")
    blocking = [n for n, st in gaps if n.get("criticality") == "essential" and st == "sem fonte"]
    if a.policy == "strict" and blocking:
        print(f"BLOQUEADO (política strict): {len(blocking)} nó(s) essencial(is) sem fonte: "
              f"{', '.join(n.get('id') for n in blocking)}")
        return 1
    return 0


def cmd_requests(a):
    L = ledger()
    for k, v in (L.get("requests") or {}).items():
        if a.open and v.get("status") == "atendido":
            continue
        print(f"{k}  [{v.get('status')}]  {v.get('concept')} ({v.get('situation')}) -> {v.get('suggested')}"
              + (f"  atendido por {v.get('source')}" if v.get("source") else ""))
    return 0


def cmd_fulfill(a):
    L = ledger()
    r = (L.get("requests") or {}).get(a.req)
    if not r:
        raise SystemExit(f"ERRO: {a.req} não existe")
    get_src(L, a.source)
    r.update({"status": "atendido", "source": a.source, "closed": now()})
    save_ledger(L)
    print(f"OK: {a.req} atendido por {a.source}. Processe a fonte e rode 'coverage' de novo.")
    return 0


def cmd_bib(a):
    L = ledger()
    only = {x.strip() for x in (a.only or "").split(",") if x.strip()}
    out = []
    kinds = {"book": "book", "paper": "article", "standard": "techreport", "docs": "misc", "site": "misc",
             "video": "misc", "slides": "misc", "repo": "misc"}
    for sid, s in L["sources"].items():
        if only and sid not in only:
            continue
        f = {"author": " and ".join(s.get("authors") or []) or "{Autor desconhecido}", "title": s.get("title"),
             "year": s.get("year"), "publisher": s.get("publisher"), "url": s.get("url"),
             "note": f"Studio {sid}"}
        if s.get("type") in ("site", "docs", "video") and s.get("added"):
            f["urldate"] = s["added"]
        body = ",\n".join(f"  {k} = {{{v}}}" for k, v in f.items() if v)
        out.append(f"@{kinds.get(s.get('type'), 'misc')}{{{s.get('bibtex_key') or sid},\n{body}\n}}")
    text = "\n\n".join(out) + "\n"
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"OK: {a.out} ({len(out)} entradas)")
    else:
        print(text)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add"); p.add_argument("path"); p.add_argument("--type", required=True, choices=TYPES)
    p.add_argument("--title"); p.add_argument("--authors"); p.add_argument("--year", type=int)
    p.add_argument("--id"); p.add_argument("--copy", action="store_true"); p.add_argument("--authority", type=int)
    p.add_argument("--origin"); p.add_argument("--publisher"); p.set_defaults(fn=cmd_add)
    p = sub.add_parser("chunk"); p.add_argument("sid"); p.add_argument("--pages", type=int, default=4)
    p.add_argument("--words", type=int, default=1500); p.add_argument("--text"); p.set_defaults(fn=cmd_chunk)
    p = sub.add_parser("import-chunks"); p.add_argument("sid"); p.add_argument("--dir", required=True)
    p.add_argument("--pages", type=int, default=4); p.set_defaults(fn=cmd_import)
    p = sub.add_parser("next"); p.add_argument("sid"); p.set_defaults(fn=cmd_next)
    p = sub.add_parser("validate"); p.add_argument("sid"); p.add_argument("--chunk"); p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("status"); p.add_argument("sid", nargs="?"); p.set_defaults(fn=cmd_status)
    p = sub.add_parser("index"); p.set_defaults(fn=cmd_index)
    p = sub.add_parser("find"); p.add_argument("term"); p.set_defaults(fn=cmd_find)
    p = sub.add_parser("pack"); p.add_argument("--concepts", required=True)
    p.add_argument("--max-words", type=int, default=900); p.add_argument("--out"); p.set_defaults(fn=cmd_pack)
    p = sub.add_parser("coverage"); p.add_argument("--graph", required=True); p.add_argument("--source-report")
    p.add_argument("--policy", choices=["strict", "warn"], default="warn"); p.add_argument("--out")
    p.set_defaults(fn=cmd_coverage)
    p = sub.add_parser("requests"); p.add_argument("--open", action="store_true"); p.set_defaults(fn=cmd_requests)
    p = sub.add_parser("fulfill"); p.add_argument("req"); p.add_argument("--source", required=True)
    p.set_defaults(fn=cmd_fulfill)
    p = sub.add_parser("bib"); p.add_argument("--out"); p.add_argument("--only"); p.set_defaults(fn=cmd_bib)
    a = ap.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
