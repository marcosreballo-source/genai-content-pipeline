#!/usr/bin/env python3
"""mf_latex.py: documentos LaTeX a partir de templates registrados + backend Beamer dos decks (Studio).

Ideia central: o template baixado NUNCA é editado. O 'inspect' copia o original e gera um 'scaffold' (cópia com
marcadores) onde o conteúdo entra por \\input. O agente só escreve FRAGMENTOS (seções curtas em LaTeX), que
este script valida, monta e compila, devolvendo erros apontando para o fragmento certo.

Templates (studio/templates/latex/<id>/):
  original/   cópia fiel do que foi baixado
  scaffold/   cópia com marcadores STUDIO (gerada por 'inspect', revisável)
  template.yaml  motor, arquivo principal, comandos de seção, mapa de metadados, ambientes de abertura, bib
  scaffold_diff.md  o que o inspect mudou (para revisão)

Comandos:
  inspect <pasta|main.tex> --id <id>      registra um template baixado (ou um embutido: --builtin studio-book)
  smoke <id>                              compila o original e o scaffold com conteúdo de teste
  list                                    templates registrados
  new <id> <job>                          cria job de documento (doc.yaml + content/)
  plan <job> [--words 900]                divide as seções em unidades (partes) que cabem numa rodada
  lint <job> [--unit S02.p1]              valida fragmentos (comandos proibidos, chaves, citações, rótulos)
  build <job>                             monta e compila; relatório em build/latex_report.md
  beamer <deck_job> [--theme metropolis|default|<template_id>] [--engine pdflatex]
"""
import argparse
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from studio_common import STUDIO, UNIT_MAX_WORDS, Issues, dump_yaml, find_exe, load_yaml, words  # noqa: E402

TPL_ROOT = STUDIO / "templates" / "latex"
BUILTIN = TPL_ROOT / "_builtin"
FRONT_ENVS = ["resumo", "abstract", "agradecimentos", "dedicatoria", "epigrafe", "resumoumacoluna", "abstractumacoluna"]
APPENDIX_ENVS = ["apendicesenv", "anexosenv"]
META_GUESS = {  # macro -> chave do doc.yaml
    "title": "title", "author": "author", "date": "date", "subtitle": "subtitle",
    "titulo": "title", "autor": "author", "data": "date", "local": "local", "instituicao": "instituicao",
    "orientador": "orientador", "coorientador": "coorientador", "tipotrabalho": "tipotrabalho",
    "preambulo": "preambulo", "institute": "institute",
}
FORBIDDEN = [r"\\documentclass", r"\\usepackage", r"\\begin\{document\}", r"\\end\{document\}", r"\\include\{",
             r"\\maketitle", r"\\tableofcontents", r"\\bibliography\{", r"\\printbibliography", r"\\newcommand",
             r"\\renewcommand", r"\\def\\"]
UNICODE_MAP = {"≈": r"$\approx$", "≤": r"$\leq$", "≥": r"$\geq$", "→": r"$\rightarrow$", "←": r"$\leftarrow$",
               "⇒": r"$\Rightarrow$", "×": r"$\times$", "±": r"$\pm$", "∞": r"$\infty$", "α": r"$\alpha$",
               "β": r"$\beta$", "γ": r"$\gamma$", "δ": r"$\delta$", "ε": r"$\varepsilon$", "θ": r"$\theta$",
               "λ": r"$\lambda$", "μ": r"$\mu$", "π": r"$\pi$", "σ": r"$\sigma$", "τ": r"$\tau$", "φ": r"$\varphi$",
               "ω": r"$\omega$", "Δ": r"$\Delta$", "Σ": r"$\Sigma$", "Ω": r"$\Omega$", "•": r"\textbullet{}",
               "✓": r"$\checkmark$", "°": r"\textdegree{}", "€": r"\texteuro{}", "…": r"\ldots{}", "−": "--"}


# ----------------------------------------------------------------------------------------------------------
# utilidades
# ----------------------------------------------------------------------------------------------------------
def tx(s):
    """Escapa texto para LaTeX preservando trechos $...$ (matemática)."""
    if s is None:
        return ""
    s = str(s)
    parts = re.split(r"(?<!\\)(\$[^$]+\$)", s)
    out = []
    for p in parts:
        if p.startswith("$") and p.endswith("$") and len(p) > 1:
            out.append(p)
            continue
        p = p.replace("\\", "\x00")
        for a, b in (("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"),
                     ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")):
            p = p.replace(a, b)
        p = p.replace("\x00", r"\textbackslash{}")
        for a, b in UNICODE_MAP.items():
            p = p.replace(a, b)
        out.append(p)
    return "".join(out)


def strip_comments(text):
    return re.sub(r"(?<!\\)%.*", "", text)


def find_main(folder):
    cands = []
    for f in sorted(Path(folder).rglob("*.tex")):
        t = f.read_text(encoding="utf-8", errors="replace")
        if re.search(r"^\s*\\documentclass", t, re.M) and "\\begin{document}" in t:
            cands.append(f)
    if not cands:
        return None
    named = [c for c in cands if c.stem.lower() in ("main", "tese", "thesis", "dissertacao", "paper", "article",
                                                     "template", "modelo")]
    return (named or cands)[0]


def engine_hint(text):
    if re.search(r"\\usepackage(\[[^\]]*\])?\{(fontspec|unicode-math|polyglossia)\}", text):
        return "xelatex"
    return "pdflatex"


# ----------------------------------------------------------------------------------------------------------
# templates: inspect / scaffold / smoke
# ----------------------------------------------------------------------------------------------------------
def scaffold_main(text):
    """Insere marcadores STUDIO no main.tex. Retorna (novo_texto, mudanças, info)."""
    changes, info = [], {}
    bd = text.find("\\begin{document}")
    ed = text.rfind("\\end{document}")
    if bd < 0 or ed < 0:
        raise ValueError("main sem \\begin{document} ... \\end{document}")
    pre, body, post = text[:bd], text[bd:ed], text[ed:]
    macros = {}
    for m in re.finditer(r"^\s*\\([A-Za-z]+)\s*(\[[^\]]*\])?\{", strip_comments(pre), re.M):
        if m.group(1) in META_GUESS:
            macros[m.group(1)] = META_GUESS[m.group(1)]
    info["metadata_map"] = {v: f"\\{k}{{%s}}" for k, v in macros.items()}
    pre = pre.rstrip("\n") + "\n%% STUDIO:META (gerado pelo build a partir do doc.yaml)\n\\input{studio_meta}\n"
    changes.append("inserido \\input{studio_meta} antes de \\begin{document}")
    fronts = []
    for env in FRONT_ENVS:
        pat = re.compile(r"(\\begin\{%s\}(\[[^\]]*\])?(\{[^}]*\})?)(.*?)(\\end\{%s\})" % (env, env), re.S)
        if pat.search(body):
            body = pat.sub(lambda m: f"{m.group(1)}\n\\input{{studio_front_{env}}}\n{m.group(5)}", body, count=1)
            fronts.append(env)
            changes.append(f"conteúdo do ambiente '{env}' trocado por \\input{{studio_front_{env}}}")
    info["front_envs"] = fronts
    apps = []
    for env in APPENDIX_ENVS:
        pat = re.compile(r"(\\begin\{%s\})(.*?)(\\end\{%s\})" % (env, env), re.S)
        if pat.search(body):
            body = pat.sub(lambda m: f"{m.group(1)}\n\\input{{studio_appendix}}\n{m.group(3)}", body, count=1)
            apps.append(env)
            changes.append(f"conteúdo do ambiente '{env}' trocado por \\input{{studio_appendix}}")
    nc = strip_comments(body)
    first = re.search(r"\\(part|chapter|section)\{", nc)
    info["section_commands"] = (["chapter", "section", "subsection", "subsubsection"]
                                if re.search(r"\\chapter\*?\{", text) or re.search(
                                    r"\\documentclass(\[[^\]]*\])?\{(book|report|abntex2|memoir|scrbook|scrreprt)\}",
                                    text) else ["section", "subsection", "subsubsection"])
    if first:
        start = body.find(first.group(0))
        back = re.compile(r"\\(bibliographystyle\{|bibliography\{|printbibliography|postextual|appendix\b|"
                          r"begin\{apendicesenv\}|begin\{anexosenv\}|begin\{thebibliography\}|printindex)")
        bm = back.search(body, start)
        end = bm.start() if bm else len(body)
        removed = body[start:end]
        body = body[:start] + "%% STUDIO:BODY (seções do doc.yaml)\n\\input{studio_body}\n" + body[end:]
        changes.append(f"removido o conteúdo-exemplo do corpo ({len(removed.splitlines())} linhas) e inserido "
                       f"\\input{{studio_body}}")
        info["removed_sample"] = removed.strip()[:1500]
    else:
        body = body.replace("\\begin{document}", "\\begin{document}\n\\input{studio_body}", 1)
        changes.append("nenhuma seção-exemplo encontrada: \\input{studio_body} logo após \\begin{document}")
    if re.search(r"(?<!%)\\appendix\b", body) and not apps:
        body = re.sub(r"(\\appendix\b)", r"\1\n\\input{studio_appendix}", body, count=1)
        changes.append("inserido \\input{studio_appendix} após \\appendix (conteúdo-exemplo de apêndice pode "
                       "permanecer: revise)")
        apps.append("appendix")
    info["appendix"] = bool(apps)
    bib = re.search(r"\\bibliography\{([^}]*)\}", body)
    if bib:
        body = body.replace(bib.group(0), "\\bibliography{references}")
        info["bibliography"] = {"command": "bibliography", "file": "references.bib"}
        changes.append(f"\\bibliography{{{bib.group(1)}}} -> \\bibliography{{references}}")
    ab = re.search(r"\\addbibresource\{([^}]*)\}", pre)
    if ab:
        pre = pre.replace(ab.group(0), "\\addbibresource{references.bib}")
        info["bibliography"] = {"command": "printbibliography", "file": "references.bib"}
        changes.append(f"\\addbibresource{{{ab.group(1)}}} -> references.bib")
    return pre + body + post, changes, info


def cmd_inspect(a):
    if a.builtin:
        src = BUILTIN / a.builtin
        tid = a.id or a.builtin
    else:
        src = Path(a.path)
        tid = a.id
    if not tid:
        print("ERRO: informe --id", file=sys.stderr)
        return 2
    src_dir = src if src.is_dir() else src.parent
    dst = TPL_ROOT / tid
    if (dst / "template.yaml").exists() and not a.force:
        print(f"ERRO: template '{tid}' já registrado (use --force para refazer o scaffold).", file=sys.stderr)
        return 2
    orig = dst / "original"
    if orig.exists():
        shutil.rmtree(orig)
    shutil.copytree(src_dir, orig, ignore=shutil.ignore_patterns("*.aux", "*.log", "*.out", "*.toc", "*.pdf",
                                                                   "*.fls", "*.fdb_latexmk", "*.synctex.gz",
                                                                   "*.bbl", "*.blg"))
    main = (orig / src.name) if src.is_file() else find_main(orig)
    if not main:
        print("ERRO: nenhum .tex com \\documentclass e \\begin{document} encontrado.", file=sys.stderr)
        return 1
    text = main.read_text(encoding="utf-8", errors="replace")
    try:
        new, changes, info = scaffold_main(text)
    except ValueError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    scaf = dst / "scaffold"
    if scaf.exists():
        shutil.rmtree(scaf)
    shutil.copytree(orig, scaf)
    rel_main = main.relative_to(orig)
    (scaf / rel_main).write_text(new, encoding="utf-8")
    cls = re.search(r"\\documentclass(\[[^\]]*\])?\{([^}]*)\}", text)
    pkgs = sorted(set(p.strip() for m in re.finditer(r"\\usepackage(\[[^\]]*\])?\{([^}]*)\}", strip_comments(text))
                      for p in m.group(2).split(",")))
    tpl = {"id": tid, "kind": a.kind, "engine": a.engine or engine_hint(text), "main": rel_main.as_posix(),
           "class": cls.group(2) if cls else "?", "packages": pkgs,
           "section_commands": info["section_commands"],
           "metadata_map": info["metadata_map"] or {"title": "\\title{%s}", "author": "\\author{%s}",
                                                    "date": "\\date{%s}"},
           "front_envs": info["front_envs"], "appendix": info["appendix"],
           "bibliography": info.get("bibliography"),
           "limits": {"pages_max": None},
           "source": {"url": a.url or "", "license": a.license or "", "notes": ""}}
    dump_yaml(tpl, dst / "template.yaml")
    md = [f"# Scaffold do template {tid}", "", f"Arquivo principal: `{rel_main}` · classe `{tpl['class']}` · "
          f"motor `{tpl['engine']}`", "", "## Mudanças feitas na CÓPIA (scaffold/); o original/ está intacto", ""]
    md += [f"- {c}" for c in changes]
    md += ["", "## Mapa de metadados detectado (doc.yaml -> macro)", ""]
    md += [f"- `{k}` -> `{v}`" for k, v in tpl["metadata_map"].items()]
    if info.get("removed_sample"):
        md += ["", "## Trecho-exemplo removido do corpo (início)", "", "```latex", info["removed_sample"], "```"]
    md += ["", "## Revise", "- O corte do corpo começou e terminou no lugar certo?",
           "- Algum comando de pré-texto (capa, folha de rosto, listas) ficou dentro do trecho removido?",
           "- Faltou algum metadado obrigatório da classe no metadata_map?",
           "Depois rode: python studio/scripts/mf_latex.py smoke " + tid]
    (dst / "scaffold_diff.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"OK: template '{tid}' registrado em {dst}")
    print("\n".join(f"  - {c}" for c in changes))
    print(f"Revise {dst / 'scaffold_diff.md'} e rode 'smoke {tid}'.")
    return 0


def compile_tex(src_dir, main, engine, timeout=600):
    """Compila com latexmk (ou sequência manual). Retorna (ok, pdf, log_text)."""
    src_dir = Path(src_dir)
    main = Path(main)
    latexmk = find_exe(["latexmk"])
    flag = {"pdflatex": "-pdf", "xelatex": "-xelatex", "lualatex": "-lualatex"}.get(engine, "-pdf")
    common = ["-interaction=nonstopmode", "-file-line-error", "-halt-on-error"]
    if latexmk:
        cmd = [latexmk, flag, *common, main.name]
        r = subprocess.run(cmd, cwd=src_dir / main.parent, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    else:
        eng = find_exe([engine])
        if not eng:
            return False, None, f"motor {engine} não encontrado"
        r = None
        for i in range(3):
            r = subprocess.run([eng, *common, main.name], cwd=src_dir / main.parent, capture_output=True, errors="replace",
                               text=True, timeout=timeout)
            if i == 0 and (src_dir / main.parent / (main.stem + ".aux")).exists():
                aux = (src_dir / main.parent / (main.stem + ".aux")).read_text(errors="replace")
                if "\\bibdata" in aux and find_exe(["bibtex"]):
                    subprocess.run([find_exe(["bibtex"]), main.stem], cwd=src_dir / main.parent,
                                   capture_output=True, timeout=timeout)
                elif "abx@aux" in aux and find_exe(["biber"]):
                    subprocess.run([find_exe(["biber"]), main.stem], cwd=src_dir / main.parent,
                                   capture_output=True, timeout=timeout)
    logf = src_dir / main.parent / (main.stem + ".log")
    log = logf.read_text(encoding="utf-8", errors="replace") if logf.exists() else (r.stdout + r.stderr if r else "")
    pdf = src_dir / main.parent / (main.stem + ".pdf")
    ok = pdf.exists() and (r is None or r.returncode == 0)
    return ok, (pdf if pdf.exists() else None), log


def parse_log(log):
    """Extrai erros, avisos de referência/citação e caixas cheias, com arquivo:linha quando possível."""
    res = {"errors": [], "undef_cite": set(), "undef_ref": set(), "overfull": [], "missing_files": [], "other": []}
    cur = None
    lines = log.splitlines()
    for i, line in enumerate(lines):
        for m in re.finditer(r"\((\.?/?[^()\s]+\.tex)", line):
            cur = m.group(1)
        m = re.match(r"^(.*?\.(?:tex|vrb|sty|cls|bbl|aux)):(\d+): (.*)$", line)
        if m:
            ctx = " ".join(l.strip() for l in lines[i + 1:i + 3] if l.strip())[:160]
            res["errors"].append({"file": m.group(1), "line": int(m.group(2)), "msg": m.group(3), "ctx": ctx})
            continue
        if line.startswith("! "):
            res["errors"].append({"file": cur or "?", "line": 0, "msg": line[2:], "ctx": ""})
        m = re.search(r"Citation [`'](.+?)' .*undefined", line)
        if m:
            res["undef_cite"].add(m.group(1))
        m = re.search(r"Reference [`'](.+?)' .*undefined", line)
        if m:
            res["undef_ref"].add(m.group(1))
        m = re.match(r"Overfull \\hbox \(([\d.]+)pt too wide\).*lines (\d+)", line)
        if m and float(m.group(1)) > 10:
            res["overfull"].append({"file": cur or "?", "line": int(m.group(2)), "pt": float(m.group(1))})
        m = re.search(r"File [`'](.+?)' not found", line)
        if m:
            res["missing_files"].append(m.group(1))
    return res


def cmd_smoke(a):
    d = TPL_ROOT / a.id
    t = load_yaml(d / "template.yaml")
    work = d / "_smoke"
    shutil.rmtree(work, ignore_errors=True)
    ok_all = True
    for label, folder in (("original", d / "original"), ("scaffold", d / "scaffold")):
        w = work / label
        shutil.copytree(folder, w)
        if label == "scaffold":
            _write_generated(w, t, {"metadata": {k: f"Teste {k}" for k in t["metadata_map"]},
                                    "front": {e: "Texto de teste da abertura." for e in t.get("front_envs", [])}},
                             [("Seção de teste", 1, "Parágrafo de teste com matemática $x^2$.\n")], [], None)
        ok, pdf, log = compile_tex(w, t["main"], t["engine"])
        rep = parse_log(log)
        print(f"[{label}] {'OK' if ok else 'FALHOU'}" + (f" ({_pages(pdf)} págs.)" if pdf else ""))
        for e in rep["errors"][:5]:
            print(f"    erro {e['file']}:{e['line']}: {e['msg']} {e['ctx']}")
        for f in rep["missing_files"][:5]:
            print(f"    arquivo ausente: {f} (pacote/classe não instalado?)")
        ok_all &= ok
    print("OK: template pronto para uso." if ok_all else
          "Corrija o scaffold (ou instale pacotes faltantes) e rode smoke de novo.")
    return 0 if ok_all else 1


def _pages(pdf):
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(pdf)).pages)
    except Exception:
        return "?"


def cmd_list(a):
    for d in sorted(p for p in TPL_ROOT.iterdir() if p.is_dir() and not p.name.startswith("_")):
        if (d / "template.yaml").exists():
            t = load_yaml(d / "template.yaml")
            print(f"{t['id']:24s} {t.get('kind', ''):9s} {t.get('class', ''):14s} {t.get('engine', '')}")
    print("Embutidos disponíveis para registrar: " + ", ".join(p.name for p in BUILTIN.iterdir() if p.is_dir()))
    return 0


# ----------------------------------------------------------------------------------------------------------
# jobs de documento
# ----------------------------------------------------------------------------------------------------------
def cmd_new(a):
    t = load_yaml(TPL_ROOT / a.id / "template.yaml")
    job = Path(a.job)
    if (job / "doc.yaml").exists():
        print("ERRO: doc.yaml já existe", file=sys.stderr)
        return 2
    for d in ("content/sections", "content/appendix", "content/front", "assets", "build", "review"):
        (job / d).mkdir(parents=True, exist_ok=True)
    doc = {"template": a.id, "kind": "document", "audience": "", "goal": "",
           "metadata": {k: "" for k in t["metadata_map"]},
           "front": {e: "" for e in t.get("front_envs", [])},
           "sections": [{"id": "S01", "title": "Introdução", "level": 1, "target_words": 600, "sources": [],
                         "brief": "o que esta seção precisa cobrir"}],
           "appendix": [], "bibliography": "references.bib", "limits": {"pages_max": None}, "panel": ""}
    dump_yaml(doc, job / "doc.yaml")
    (job / "references.bib").touch()
    print(f"OK: job em {job}. Preencha doc.yaml (seções, metadados) e rode 'plan'.")
    return 0


def _units(doc, per):
    out = []
    for kind in ("sections", "appendix"):
        for s in doc.get(kind) or []:
            n = max(1, math.ceil((s.get("target_words") or per) / per))
            for i in range(1, n + 1):
                out.append({"id": f"{s['id']}.p{i}", "section": s["id"], "kind": kind, "part": i, "of": n,
                            "file": f"content/{'sections' if kind == 'sections' else 'appendix'}/{s['id']}.p{i}.tex",
                            "target_words": math.ceil((s.get("target_words") or per) / n)})
    return out


def cmd_plan(a):
    job = Path(a.job)
    doc = load_yaml(job / "doc.yaml")
    iss = Issues()
    t = load_yaml(TPL_ROOT / doc["template"] / "template.yaml")
    for k in t["metadata_map"]:
        if not (doc.get("metadata") or {}).get(k):
            iss.warn("metadata", f"'{k}' vazio")
    ids = set()
    for s in (doc.get("sections") or []) + (doc.get("appendix") or []):
        if not re.match(r"^[SA]\d{2}$", str(s.get("id", ""))):
            iss.err(str(s.get("id")), "id deve ser S01.. (seções) ou A01.. (apêndices)")
        if s.get("id") in ids:
            iss.err(s["id"], "id repetido")
        ids.add(s.get("id"))
        if not s.get("title"):
            iss.err(s.get("id", "?"), "título vazio")
        if s.get("level", 1) > len(t["section_commands"]):
            iss.err(s.get("id", "?"), f"level {s['level']} inexistente neste template")
    units = _units(doc, a.words)
    old = {u["id"]: u.get("status") for u in load_yaml(job / "plan.yaml", {"units": []}).get("units", [])}
    for u in units:
        u["status"] = "done" if old.get(u["id"]) == "done" and (job / u["file"]).exists() else "todo"
    dump_yaml({"template": doc["template"], "words_per_unit": a.words, "units": units}, job / "plan.yaml")
    iss.print("Plano do documento:")
    for u in units:
        print(f"  {u['id']:8s} -> {u['file']}  (~{u['target_words']} palavras) [{u['status']}]")
    print(f"{len(units)} unidade(s). Escreva uma por rodada e rode 'lint --unit <id>' após cada uma.")
    return iss.exit_code()


def _bib_keys(job, doc):
    f = job / (doc.get("bibliography") or "references.bib")
    if not f.exists():
        return set()
    return set(re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", f.read_text(encoding="utf-8", errors="replace")))


def lint_fragment(text, where, iss, bib, labels, job):
    for n, line in enumerate(text.splitlines(), 1):
        m = re.search(r"(?<=[\d\w])\s?(?<!\\)%(?=.*\S)", line)
        if m and not line.lstrip().startswith("%"):
            iss.err(where, f"linha {n}: '%' sem escape após texto ('{line.strip()[:40]}...'): o resto da linha vira "
                           f"comentário. Use \\%")
    body = strip_comments(text)
    for pat in FORBIDDEN:
        if re.search(pat, body):
            iss.err(where, f"comando proibido em fragmento: {pat.replace(chr(92) * 2, chr(92))}")
    depth = 0
    for ch in re.sub(r"\\[{}]", "", body):
        depth += ch == "{"
        depth -= ch == "}"
        if depth < 0:
            break
    if depth != 0:
        iss.err(where, "chaves { } desbalanceadas")
    lst_ok = set("áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÇ—–ºª°“”’")
    for blk in re.findall(r"\\begin\{lstlisting\}.*?\\end\{lstlisting\}", body, flags=re.S):
        bad = sorted({ch for ch in blk if ord(ch) > 127 and ch not in lst_ok})
        if bad:
            iss.err(where, f"caracteres não suportados dentro de código (lstlisting): {' '.join(bad)}; use ASCII")
    begins = re.findall(r"\\begin\{([^}]+)\}", body)
    ends = re.findall(r"\\end\{([^}]+)\}", body)
    for env in set(begins) | set(ends):
        if begins.count(env) != ends.count(env):
            iss.err(where, f"ambiente '{env}': {begins.count(env)} begin x {ends.count(env)} end")
    plain = re.sub(r"\\begin\{(lstlisting|verbatim|minted)\}.*?\\end\{\1\}", "", body, flags=re.S)
    plain = re.sub(r"\\(lstinline|verb)(.)(.*?)\2", "", plain)
    nomath = re.sub(r"\$\$.*?\$\$|\$.*?\$|\\\[.*?\\\]|\\\(.*?\\\)", "", plain, flags=re.S)
    nomath = re.sub(r"\\begin\{(equation|align|gather|multline|eqnarray)\*?\}.*?\\end\{\1\*?\}", "", nomath, flags=re.S)
    if plain.count("$") % 2:
        iss.err(where, "número ímpar de $: matemática não fechada")
    if re.search(r"(?<!\\)#", nomath):
        iss.err(where, "'#' sem escape (use \\#)")
    if re.search(r"(?<![\\\w])_|(?<=[A-Za-zÀ-ú])_(?=[A-Za-zÀ-ú])", nomath) and not re.search(r"\\(url|href|path|ref|label|cite)", nomath):
        iss.warn(where, "'_' fora de matemática (use \\_ ou $x_i$)")
    noenv = re.sub(r"\\begin\{(tabular\*?|tabularx|array|align\*?|matrix|pmatrix|bmatrix|cases|longtable)\}.*?"
                   r"\\end\{\1\}", "", nomath, flags=re.S)
    if re.search(r"(?<!\\)&", noenv):
        iss.warn(where, "'&' fora de tabela/alinhamento (use \\&)")
    for keys in re.findall(r"\\cite[pt]?\*?(?:\[[^\]]*\])*\{([^}]*)\}", body):
        for k in keys.split(","):
            if k.strip() and bib is not None and k.strip() not in bib:
                iss.err(where, f"citação '{k.strip()}' não existe no .bib")
    for lab in re.findall(r"\\label\{([^}]+)\}", body):
        if lab in labels:
            iss.err(where, f"rótulo '{lab}' repetido (também em {labels[lab]})")
        labels[lab] = where
    for g in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", body):
        if job and not any((job / c).exists() for c in (g, g + ".png", g + ".pdf", g + ".jpg")):
            iss.err(where, f"figura não encontrada: {g} (coloque em assets/ e use assets/arquivo)")
    if "[[PENDENTE" in text:
        iss.warn(where, "contém [[PENDENTE...]]: dado/fonte ainda não fornecido (bloqueia o build final)")
    w = words(re.sub(r"\\[A-Za-z]+(\[[^\]]*\])?(\{[^}]*\})?", " ", body))
    if w > UNIT_MAX_WORDS:
        iss.err(where, f"{w} palavras (máx. {UNIT_MAX_WORDS} por unidade)")
    return w


def cmd_lint(a):
    job = Path(a.job)
    doc = load_yaml(job / "doc.yaml")
    plan = load_yaml(job / "plan.yaml", {"units": []})
    iss = Issues()
    bib = _bib_keys(job, doc)
    labels = {}
    units = [u for u in plan["units"] if not a.unit or u["id"] == a.unit]
    if a.unit and not units:
        print(f"ERRO: unidade {a.unit} não está no plan.yaml", file=sys.stderr)
        return 2
    for u in units:
        f = job / u["file"]
        if not f.exists():
            (iss.err if a.unit else iss.warn)(u["id"], f"arquivo ainda não escrito: {u['file']}")
            continue
        w = lint_fragment(f.read_text(encoding="utf-8"), u["id"], iss, bib, labels, job)
        if w < u["target_words"] * 0.5:
            iss.warn(u["id"], f"{w} palavras para meta de ~{u['target_words']}")
        if re.search(r"\\(chapter|section)\{", strip_comments(f.read_text(encoding="utf-8"))):
            iss.warn(u["id"], "o título da seção é gerado pelo build; no fragmento use só \\subsection em diante")
    if not a.unit:
        allref = " ".join((job / u["file"]).read_text(encoding="utf-8") for u in plan["units"]
                          if (job / u["file"]).exists())
        sec_labels = {f"sec:{s['id']}" for s in (doc.get("sections") or []) + (doc.get("appendix") or [])}
        for r in re.findall(r"\\(?:ref|eqref|autoref|cref)\{([^}]+)\}", allref):
            if r not in labels and r not in sec_labels:
                iss.err("referências", f"\\ref{{{r}}} sem \\label correspondente")
    iss.print("Lint:")
    if a.unit and not iss.errors:
        for u in plan["units"]:
            if u["id"] == a.unit:
                u["status"] = "done"
        dump_yaml(plan, job / "plan.yaml")
    return iss.exit_code()


def _write_generated(src, t, doc, sections, appendix, job):
    src = Path(src)
    meta = ["% gerado por mf_latex.py; não editar"]
    for k, macro in t["metadata_map"].items():
        v = (doc.get("metadata") or {}).get(k)
        if v:
            meta.append(macro.replace("%s", tx(v)))
    (src / "studio_meta.tex").write_text("\n".join(meta) + "\n", encoding="utf-8")
    for env in t.get("front_envs", []):
        v = (doc.get("front") or {}).get(env) or ""
        if job and v and (job / v).exists():
            v = (job / v).read_text(encoding="utf-8")
        else:
            v = tx(v)
        (src / f"studio_front_{env}.tex").write_text(v + "\n", encoding="utf-8")
    cmds = t["section_commands"]
    for name, items in (("studio_body", sections), ("studio_appendix", appendix)):
        lines = ["% gerado por mf_latex.py; não editar"]
        for title, level, content in items:
            lines.append(f"\\{cmds[min(level, len(cmds)) - 1]}{{{tx(title)}}}")
            lines.append(content)
        (src / f"{name}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_build(a):
    job = Path(a.job)
    doc = load_yaml(job / "doc.yaml")
    t = load_yaml(TPL_ROOT / doc["template"] / "template.yaml")
    plan = load_yaml(job / "plan.yaml", {"units": []})
    src = job / "build" / "src"
    shutil.rmtree(src, ignore_errors=True)
    shutil.copytree(TPL_ROOT / doc["template"] / "scaffold", src)
    if (job / "assets").exists():
        shutil.copytree(job / "assets", src / "assets", dirs_exist_ok=True)
    frag_dir = src / "studio_frag"
    frag_dir.mkdir()
    by_sec = {}
    for u in plan["units"]:
        f = job / u["file"]
        if f.exists():
            shutil.copy2(f, frag_dir / f.name)
            by_sec.setdefault(u["section"], []).append(f"\\input{{studio_frag/{f.stem}}}")
        else:
            by_sec.setdefault(u["section"], []).append(f"% PENDENTE: {u['file']}\n\\textbf{{[{u['id']} pendente]}}")

    def items(lst, prefix):
        return [(s["title"], s.get("level", 1), f"\\label{{sec:{s['id']}}}\n" + "\n".join(by_sec.get(s["id"], [])))
                for s in lst or []]
    _write_generated(src, t, doc, items(doc.get("sections"), "S"), items(doc.get("appendix"), "A"), job)
    bib = job / (doc.get("bibliography") or "references.bib")
    if bib.exists():
        shutil.copy2(bib, src / "references.bib")
    ok, pdf, log = compile_tex(src, t["main"], t["engine"])
    rep = parse_log(log)
    iss = Issues()
    for e in rep["errors"]:
        iss.err(f"{Path(e['file']).name}:{e['line']}", f"{e['msg']} {e['ctx']}".strip())
    for c in sorted(rep["undef_cite"]):
        iss.err("citações", f"citação indefinida: {c}")
    for r in sorted(rep["undef_ref"]):
        iss.warn("referências", f"referência indefinida: {r}")
    for o in rep["overfull"][:30]:
        iss.warn(f"{Path(o['file']).name}:{o['line']}", f"linha estourando a margem em {o['pt']:.0f}pt")
    for m in rep["missing_files"]:
        iss.err("arquivos", f"não encontrado: {m}")
    pages = _pages(pdf) if pdf else 0
    lim = (doc.get("limits") or {}).get("pages_max") or (t.get("limits") or {}).get("pages_max")
    if lim and isinstance(pages, int) and pages > lim:
        iss.err("páginas", f"{pages} páginas > limite {lim}")
    for u in plan["units"]:
        f = job / u["file"]
        if f.exists() and "[[PENDENTE" in f.read_text(encoding="utf-8"):
            iss.err(u["id"], "ainda contém [[PENDENTE...]]: providencie o dado/fonte")
    pend = [u["id"] for u in plan["units"] if not (job / u["file"]).exists()]
    if pend:
        iss.warn("conteúdo", f"{len(pend)} unidade(s) pendente(s): {', '.join(pend[:10])}")
    out_pdf = job / "build" / "document.pdf"
    if pdf:
        shutil.copy2(pdf, out_pdf)
    md = ["# Relatório de build LaTeX", "", f"Template: {doc['template']} · motor: {t['engine']} · "
          f"resultado: {'OK' if ok else 'FALHOU'} · páginas: {pages}", "",
          "Arquivos `studio_frag/S02.p1.tex` correspondem a `content/sections/S02.p1.tex` no job.", "",
          iss.markdown()]
    (job / "build" / "latex_report.md").write_text("\n".join(md), encoding="utf-8")
    iss.print(f"Build {'OK' if ok else 'FALHOU'} ({pages} págs.):")
    if pdf:
        print(f"PDF: {out_pdf}")
    return 0 if ok and not iss.errors else 1


# ----------------------------------------------------------------------------------------------------------
# Beamer a partir do mesmo spec de deck
# ----------------------------------------------------------------------------------------------------------
def _items(lst, env="itemize"):
    out = [f"\\begin{{{env}}}"]
    for it in lst:
        if isinstance(it, dict):
            out.append(f"  \\item {tx(it.get('text', ''))}")
            if it.get("sub"):
                out.append("  \\begin{itemize}")
                out += [f"    \\item {tx(s)}" for s in it["sub"]]
                out.append("  \\end{itemize}")
        else:
            out.append(f"  \\item {tx(it)}")
    out.append(f"\\end{{{env}}}")
    return "\n".join(out)


def beamer_frame(s, ctx):
    a = s["archetype"]
    t = tx(s.get("title", ""))
    notes = f"\n\\note{{{tx(s['notes'])}}}" if s.get("notes") else ""
    F = lambda body, opts="", title=t: (f"\\begin{{frame}}{opts}{{{title}}}\n{body}\n\\end{{frame}}{notes}")  # noqa
    if a == "title":
        return "\\begin{frame}[plain]\n\\titlepage\n\\end{frame}" + notes
    if a == "agenda":
        return F(_items(s["items"], "enumerate"), title=tx(s.get("title") or "Agenda"))
    if a == "section":
        num = f"{tx(s['number'])}\\quad " if s.get("number") else ""
        sub = f"\\\\[0.6em]{{\\normalsize\\color{{studioMuted}}{tx(s['subtitle'])}}}" if s.get("subtitle") else ""
        if ctx.get("auto_section_page"):
            return f"\\section{{{tx(s['title'])}}}{notes}"
        return (f"\\section{{{tx(s['title'])}}}\n\\begin{{frame}}[plain,noframenumbering]\n\\vfill\n"
                f"{{\\LARGE\\bfseries\\color{{studioAccent}}{num}\\color{{studioPrimary}}{tx(s['title'])}}}{sub}\n"
                f"\\vfill\n\\end{{frame}}{notes}")
    if a == "bullets":
        tk = (f"\n\\vfill\n\\begin{{studioTakeaway}}{tx(s['takeaway'])}\\end{{studioTakeaway}}"
              if s.get("takeaway") else "")
        return F(_items(s["bullets"]) + tk)
    if a == "statement":
        sup = f"\\\\[1em]{{\\large\\color{{studioMuted}}{tx(s['support'])}}}" if s.get("support") else ""
        return F(f"\\vfill\n{{\\color{{studioAccent}}\\rule{{2cm}}{{2pt}}}}\\\\[0.6em]\n"
                 f"{{\\Large\\bfseries\\color{{studioPrimary}}{tx(s['statement'])}}}{sup}\n\\vfill", "[plain]", "")
    if a == "big_number":
        ctxt = f"\\\\[0.8em]{{\\color{{studioMuted}}{tx(s['context'])}}}" if s.get("context") else ""
        return F(f"\\vfill\n{{\\fontsize{{54}}{{58}}\\selectfont\\bfseries\\color{{studioAccent}}{tx(s['value'])}}}"
                 f"\\\\[0.4em]{{\\Large\\bfseries\\color{{studioPrimary}}{tx(s['label'])}}}{ctxt}\n\\vfill")
    if a == "kpis":
        n = len(s["items"])
        cols = "\n".join(f"\\column{{{0.95 / n:.2f}\\textwidth}}\\centering"
                         f"{{\\fontsize{{30}}{{34}}\\selectfont\\bfseries\\color{{studioPrimary}}{tx(i['value'])}}}\\\\"
                         + (f"{{\\small\\bfseries\\color{{studioAccent2}}{tx(i['delta'])}}}\\\\" if i.get("delta") else "")
                         + f"[0.3em]{{\\small\\color{{studioMuted}}{tx(i['label'])}}}" for i in s["items"])
        return F(f"\\vfill\n\\begin{{columns}}[T]\n{cols}\n\\end{{columns}}\n\\vfill")
    if a == "two_column":
        def col(c):
            h = f"{{\\bfseries\\color{{studioPrimary}}{tx(c['heading'])}}}\n" if c.get("heading") else ""
            return h + _items(c["bullets"])
        return F(f"\\begin{{columns}}[T]\n\\column{{0.48\\textwidth}}\n{col(s['left'])}\n"
                 f"\\column{{0.48\\textwidth}}\n{col(s['right'])}\n\\end{{columns}}")
    if a == "comparison":
        n = len(s["columns"])
        cols = []
        for c in s["columns"]:
            env = "alertblock" if c.get("highlight") else "block"
            cols.append(f"\\column{{{0.95 / n:.2f}\\textwidth}}\n\\begin{{{env}}}{{{tx(c['heading'])}}}\n"
                        f"{_items(c['items'])}\n\\end{{{env}}}")
        return F("\\begin{columns}[T]\n" + "\n".join(cols) + "\n\\end{columns}")
    if a in ("image", "diagram", "chart", "equation") and a != "equation":
        img = ctx["asset"](s)
        cap = " --- ".join(x for x in (tx(s.get("caption", "")), f"Fonte: {tx(s['source'])}" if s.get("source")
                                       else "") if x)
        capl = f"\\\\[0.3em]{{\\scriptsize\\itshape\\color{{studioMuted}}{cap}}}" if cap else ""
        tk = (f"\n\\begin{{studioTakeaway}}{tx(s['takeaway'])}\\end{{studioTakeaway}}" if s.get("takeaway") else "")
        if not img:
            return F(f"\\centering[{a} não renderizado]{capl}")
        h = "0.62" if (s.get("takeaway") or cap) else "0.75"
        if a == "image" and s.get("layout") in ("left", "right") and s.get("bullets"):
            pic = f"\\column{{0.55\\textwidth}}\\centering\\includegraphics[width=\\linewidth,height=0.7\\textheight," \
                  f"keepaspectratio]{{{img}}}{capl}"
            txt = f"\\column{{0.42\\textwidth}}\n{_items(s['bullets'])}"
            cols = (pic, txt) if s["layout"] == "left" else (txt, pic)
            return F(f"\\begin{{columns}}[c]\n{cols[0]}\n{cols[1]}\n\\end{{columns}}")
        return F(f"\\centering\\includegraphics[width=\\linewidth,height={h}\\textheight,keepaspectratio]{{{img}}}"
                 f"{capl}{tk}")
    if a == "equation":
        ex = _items(s["explanation"]) if s.get("explanation") else ""
        return F(f"\\vfill\n\\[ \\displaystyle {s['latex']} \\]\n\\vfill\n{ex}")
    if a == "table":
        cols, rows = s["columns"], s["rows"]
        hl = s.get("highlight_row")
        spec = "l" * len(cols)
        body = ["\\begin{tabular}{" + spec + "}", "\\toprule",
                " & ".join(f"\\textbf{{{tx(c)}}}" for c in cols) + " \\\\", "\\midrule"]
        for i, r in enumerate(rows):
            pre = "\\rowcolor{studioAccent!25} " if hl == i else ""
            body.append(pre + " & ".join(tx(c) for c in r) + " \\\\")
        body += ["\\bottomrule", "\\end{tabular}"]
        src = f"\\\\[0.4em]{{\\scriptsize\\itshape\\color{{studioMuted}}Fonte: {tx(s['source'])}}}" if s.get("source") else ""
        return F("\\centering\\small\n" + "\n".join(body) + src)
    if a in ("timeline", "process"):
        items = s["events"] if a == "timeline" else s["steps"]
        n = len(items)
        nodes = []
        for i, it in enumerate(items):
            x = i * (11.0 / max(1, n - 1)) if n > 1 else 0
            if a == "timeline":
                nodes.append(f"\\fill[{'studioAccent' if i == n - 1 else 'studioPrimary'}] ({x:.2f},0) circle (4pt);"
                             f"\\node[above=6pt,font=\\footnotesize\\bfseries,text=studioPrimary] at ({x:.2f},0) "
                             f"{{{tx(it['when'])}}};\\node[below=6pt,text width=2.1cm,align=center,font=\\scriptsize]"
                             f" at ({x:.2f},0) {{\\textbf{{{tx(it['label'])}}}\\\\{tx(it.get('detail', ''))}}};")
            else:
                nodes.append(f"\\node[draw=studioPrimary,fill=studioLight,rounded corners,text width=1.9cm,"
                             f"minimum height=2.2cm,align=center,font=\\scriptsize] (n{i}) at ({x:.2f},0) "
                             f"{{{{\\color{{studioAccent}}\\bfseries {i + 1}}}\\\\\\textbf{{{tx(it['label'])}}}\\\\"
                             f"{tx(it.get('detail', ''))}}};" + (f"\\draw[-latex,thick,studioMuted] (n{i - 1}) -- (n{i});"
                                                                if i else ""))
        line = "\\draw[thick,studioMuted] (-0.5,0) -- (11.5,0);" if a == "timeline" else ""
        return F(f"\\vfill\\centering\n\\resizebox{{\\linewidth}}{{!}}{{\\begin{{tikzpicture}}\n{line}\n"
                 + "\n".join(nodes) + "\n\\end{tikzpicture}}\n\\vfill")
    if a == "quote":
        who = " --- ".join(tx(x) for x in (s.get("author"), s.get("role")) if x)
        return F(f"\\vfill\n{{\\Large\\itshape\\color{{studioPrimary}}``{tx(s['quote'])}''}}\\\\[1em]\n"
                 f"{{\\normalsize\\bfseries {who}}}\n\\vfill", "[plain]", "")
    if a == "code":
        lang = {"python": "Python", "java": "Java", "c": "C", "cpp": "C++", "sql": "SQL", "bash": "bash",
                "r": "R", "matlab": "Matlab"}.get(str(s.get("language", "")).lower(), "")
        cap = f"\n{{\\scriptsize\\itshape\\color{{studioMuted}}{tx(s['caption'])}}}" if s.get("caption") else ""
        return (f"\\begin{{frame}}[fragile]{{{t}}}\n\\begin{{lstlisting}}[language={{{lang}}}]\n{s['code'].rstrip()}\n"
                f"\\end{{lstlisting}}{cap}\n\\end{{frame}}{notes}")
    if a == "team":
        n = len(s["members"])
        cols = "\n".join(f"\\column{{{0.95 / n:.2f}\\textwidth}}\\centering{{\\bfseries\\color{{studioPrimary}}"
                         f"{tx(m['name'])}}}\\\\{{\\small\\color{{studioAccent}}{tx(m.get('role', ''))}}}\\\\"
                         f"{{\\scriptsize\\color{{studioMuted}}{tx(m.get('detail', ''))}}}" for m in s["members"])
        return F(f"\\vfill\\begin{{columns}}[T]\n{cols}\n\\end{{columns}}\\vfill", title=tx(s.get("title") or "Equipe"))
    if a == "closing":
        its = _items(s["items"]) if s.get("items") else ""
        msg = f"{{\\large {tx(s['message'])}}}\\\\[0.8em]" if s.get("message") else ""
        ct = f"\n\\vfill{{\\bfseries\\color{{studioAccent}}{tx(s['contact'])}}}" if s.get("contact") else ""
        return F(f"\\vfill{msg}\n{its}{ct}")
    if a == "references":
        body = "\\begin{enumerate}\\scriptsize\n" + "\n".join(f"\\item {tx(i)}" for i in s["items"]) + "\n\\end{enumerate}"
        return F(body, "[allowframebreaks]", tx(s.get("title") or "Referências"))
    if a == "qa":
        ct = f"\\\\[1em]{{\\color{{studioMuted}}{tx(s['contact'])}}}" if s.get("contact") else ""
        return F(f"\\vfill\\centering{{\\Huge\\bfseries\\color{{studioPrimary}}{tx(s.get('title') or 'Perguntas?')}}}"
                 f"{ct}\\vfill", "[plain]", "")
    return F(f"% arquétipo {a} sem suporte no Beamer")


BEAMER_PRE = r"""\documentclass[aspectratio=169,11pt,xcolor={table}]{beamer}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{textcomp}
\IfFileExists{lmodern.sty}{\usepackage{lmodern}}{}
\IfFileExists{portuges.ldf}{\usepackage[brazil]{babel}}{}
\usepackage{amsmath,amssymb,booktabs,graphicx,listings,tikz,tcolorbox}
\usetikzlibrary{positioning}
@@COLORS@@
@@THEME@@
\newtcolorbox{studioTakeaway}{colback=studioLight,colframe=studioAccent,boxrule=0pt,leftrule=3pt,sharp corners,
  fontupper=\bfseries\color{studioPrimary}\small}
\lstset{basicstyle=\ttfamily\scriptsize, backgroundcolor=\color{studioCodeBg}, basicstyle=\ttfamily\scriptsize\color{studioCodeFg},
  commentstyle=\color{gray}, keywordstyle=\color{studioAccent}\bfseries, stringstyle=\color{studioAccent2},
  literate={á}{{\'a}}1 {à}{{\`a}}1 {â}{{\^a}}1 {ã}{{\~a}}1 {é}{{\'e}}1 {ê}{{\^e}}1 {í}{{\'i}}1 {ó}{{\'o}}1 {ô}{{\^o}}1 {õ}{{\~o}}1 {ú}{{\'u}}1 {ü}{{\"u}}1 {ç}{{\c c}}1 {Á}{{\'A}}1 {À}{{\`A}}1 {Â}{{\^A}}1 {Ã}{{\~A}}1 {É}{{\'E}}1 {Ê}{{\^E}}1 {Í}{{\'I}}1 {Ó}{{\'O}}1 {Ô}{{\^O}}1 {Õ}{{\~O}}1 {Ú}{{\'U}}1 {Ç}{{\c C}}1 {—}{{---}}1 {–}{{--}}1 {º}{{\textordmasculine}}1 {ª}{{\textordfeminine}}1 {°}{{\textdegree}}1 {“}{{``}}1 {”}{{''}}1 {’}{{'}}1,
  breaklines=true, frame=none, xleftmargin=6pt, xrightmargin=6pt, aboveskip=4pt}
\setbeamertemplate{navigation symbols}{}
\title{@@TITLE@@}
\subtitle{@@SUBTITLE@@}
\author{@@AUTHOR@@}
\institute{@@EVENT@@}
\date{@@DATE@@}
\begin{document}
"""


def cmd_beamer(a):
    import mf_deck
    job = Path(a.job)
    iss = Issues()
    slides = mf_deck.load_slides(job, iss)
    for s in slides:
        mf_deck.validate_slide(s, s.get("id", "?"), iss, job)
    if iss.errors:
        iss.print("Beamer bloqueado por erros de validação:")
        return 1
    brief = load_yaml(job / "brief.yaml", {})
    kit = mf_deck.load_kit(a.kit or (brief.get("style") or {}).get("kit") or "default")
    c = kit["colors"]
    out = job / "build" / "beamer"
    shutil.rmtree(out, ignore_errors=True)
    (out / "img").mkdir(parents=True)
    cache = job / "build" / "cache"

    def asset(s):
        if s["archetype"] == "chart":
            p = out / "img" / f"{s['id']}.png"
            mf_deck.render_chart_png(s["chart"], p, c, kit["chart_palette"], kit["fonts"])
            return f"img/{p.name}"
        if s["archetype"] == "diagram" and s.get("mermaid"):
            p = mf_deck.render_mermaid(s["mermaid"], cache, c, kit["fonts"])
        else:
            p = mf_deck.resolve_asset(job, s.get("image"))
        if not p:
            return None
        dst = out / "img" / f"{s['id']}{Path(p).suffix}"
        shutil.copy2(p, dst)
        return f"img/{dst.name}"
    colors = "\n".join(f"\\definecolor{{studio{n}}}{{HTML}}{{{str(c.get(k, d)).lstrip('#').upper()}}}" for n, k, d in
                       (("Primary", "primary", "1F3A5F"), ("Accent", "accent", "E4572E"),
                        ("Accent2", "accent2", "1B998B"), ("Text", "text", "1F2933"), ("Muted", "muted", "5B6675"),
                        ("Light", "light", "EEF1F5"), ("Dark", "dark", "0F1B2D"), ("CodeBg", "code_bg", "1E2430"),
                        ("CodeFg", "code_fg", "E6EDF3")))
    theme = a.theme or "metropolis"
    if theme == "metropolis" and find_exe(["kpsewhich"]) and subprocess.run(
            [find_exe(["kpsewhich"]), "beamerthememetropolis.sty"], capture_output=True, text=True).stdout.strip():
        th = ("\\usetheme[progressbar=frametitle,numbering=fraction]{metropolis}\n"
              "\\setbeamercolor{frametitle}{bg=studioDark,fg=white}\n\\setbeamercolor{progress bar}{fg=studioAccent,bg=studioLight}\n"
              "\\setbeamercolor{alerted text}{fg=studioAccent}\n\\setbeamercolor{normal text}{fg=studioText}\n"
              "\\setbeamercolor{block title alerted}{bg=studioAccent,fg=white}\n"
              "\\setbeamercolor{block title}{bg=studioLight,fg=studioPrimary}\n\\setbeamercolor{block body}{bg=studioLight!50}")
    elif theme in ("metropolis", "default"):
        th = ("\\usetheme{default}\n\\setbeamercolor{frametitle}{fg=studioPrimary}\n\\setbeamercolor{title}{fg=studioPrimary}\n"
              "\\setbeamercolor{structure}{fg=studioAccent}\n\\setbeamerfont{frametitle}{series=\\bfseries}\n"
              "\\setbeamertemplate{footline}[frame number]")
    else:
        tdir = TPL_ROOT / theme
        if not (tdir / "template.yaml").exists():
            print(f"ERRO: tema/template Beamer '{theme}' não registrado", file=sys.stderr)
            return 2
        shutil.copytree(tdir / "original", out, dirs_exist_ok=True)
        t = load_yaml(tdir / "template.yaml")
        th = f"\\input{{{t.get('beamer_preamble', 'preamble.tex')}}}"
    first = next((s for s in slides if s["archetype"] == "title"), {})
    pre = (BEAMER_PRE.replace("@@COLORS@@", colors).replace("@@THEME@@", th)
           .replace("@@TITLE@@", tx(first.get("title") or brief.get("title", ""))))
    pre = (pre.replace("@@SUBTITLE@@", tx(first.get("subtitle", "")))
           .replace("@@AUTHOR@@", tx(first.get("author") or brief.get("author", "")))
           .replace("@@EVENT@@", tx(first.get("event") or brief.get("event", "")))
           .replace("@@DATE@@", tx(first.get("date") or brief.get("date", ""))))
    auto_sec = "metropolis" in th
    frames = [beamer_frame(s, {"asset": asset, "auto_section_page": auto_sec}) for s in slides]
    (out / "deck.tex").write_text(pre + "\n\n".join(frames) + "\n\\end{document}\n", encoding="utf-8")
    ok, pdf, log = compile_tex(out, "deck.tex", a.engine)
    rep = parse_log(log)
    for e in rep["errors"]:
        iss.err(f"deck.tex:{e['line']}", f"{e['msg']} {e['ctx']}".strip())
    for m in rep["missing_files"]:
        iss.err("arquivos", f"não encontrado: {m}")
    if pdf:
        shutil.copy2(pdf, job / "build" / "deck_beamer.pdf")
    iss.print(f"Beamer {'OK' if ok else 'FALHOU'}:")
    if pdf:
        print(f"PDF: {job / 'build' / 'deck_beamer.pdf'} ({_pages(pdf)} págs.) · fonte: {out / 'deck.tex'}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("inspect"); p.add_argument("path", nargs="?"); p.add_argument("--id")
    p.add_argument("--builtin"); p.add_argument("--kind", default="document", choices=["document", "beamer", "exam"])
    p.add_argument("--engine", choices=["pdflatex", "xelatex", "lualatex"]); p.add_argument("--url")
    p.add_argument("--license"); p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_inspect)
    p = sub.add_parser("smoke"); p.add_argument("id"); p.set_defaults(fn=cmd_smoke)
    p = sub.add_parser("list"); p.set_defaults(fn=cmd_list)
    p = sub.add_parser("new"); p.add_argument("id"); p.add_argument("job"); p.set_defaults(fn=cmd_new)
    p = sub.add_parser("plan"); p.add_argument("job"); p.add_argument("--words", type=int, default=900)
    p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("lint"); p.add_argument("job"); p.add_argument("--unit"); p.set_defaults(fn=cmd_lint)
    p = sub.add_parser("build"); p.add_argument("job"); p.set_defaults(fn=cmd_build)
    p = sub.add_parser("beamer"); p.add_argument("job"); p.add_argument("--theme"); p.add_argument("--kit")
    p.add_argument("--engine", default="pdflatex"); p.set_defaults(fn=cmd_beamer)
    a = ap.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
