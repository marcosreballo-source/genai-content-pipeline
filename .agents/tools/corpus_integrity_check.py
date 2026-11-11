#!/usr/bin/env python
"""
corpus_integrity_check.py — Portão determinístico de integridade do corpus bibliográfico.

Verifica, para cada item de um `corpus_manifest.json`:
  1. Se o arquivo local existe (PDF/HTM/TXT).
  2. Se o CONTEÚDO do arquivo corresponde à obra esperada (título + 1º autor na(s)
     primeira(s) página(s)) — detecta PDFs errados baixados por engano.
  3. (--online) Se os metadados oficiais (OpenAlex, via DOI) batem com o manifesto e
     com a forma como a obra foi CITADA no documento-base (`cited_as`) — detecta
     referências com autores/ano/veículo incorretos.

Uso (a partir da raiz do workspace):
  .\\.venv\\Scripts\\python.exe .agents/tools/corpus_integrity_check.py <corpus_manifest.json> [--online]

Saída:
  - Relatório Markdown `corpus_integrity_report.md` ao lado do manifesto (ou --report PATH).
  - Exit code 0 = APROVADO | 1 = REPROVADO (erro de conteúdo/citação não reconhecido)
    | 2 = PENDENTE (apenas arquivos ainda não obtidos, sem dispensa).

Esquema do manifesto: ver `.agents/skills/workflow-scientific-research/templates/corpus_manifest.template.json`.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

TITLE_RECALL_MIN = 0.75      # fração mínima dos tokens do título presentes no início do documento
TITLE_CONTIGUITY_MIN = 0.6   # fração mínima do título que deve aparecer como sequência contígua
FIRST_PAGES = 2          # páginas do PDF inspecionadas
HTML_CHARS = 300_000     # caracteres iniciais inspecionados em HTM/TXT

STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "towards", "toward", "using", "via",
    "of", "on", "in", "to", "an", "a", "its", "their", "under", "das", "dos", "uma",
    "para", "com", "por", "sobre",
}


# ----------------------------------------------------------------------------- utilidades
def normalize(text: str) -> str:
    """Minúsculas, sem acentos, com ligaduras e glifos quebrados corrigidos."""
    text = text.replace("/f_i", "fi").replace("/f_l", "fl")
    text = unicodedata.normalize("NFKC", text)
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return text.lower()


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", normalize(text)) if len(t) >= 3 and t not in STOPWORDS]


def find_workspace_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / ".agents").is_dir():
            return p
    return Path.cwd()


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        import pypdf  # disponível no .venv do workspace

        reader = pypdf.PdfReader(str(path))
        pages = reader.pages[: min(FIRST_PAGES, len(reader.pages))]
        return " ".join((pg.extract_text() or "") for pg in pages)
    raw = path.read_text(encoding="utf-8", errors="ignore")[:HTML_CHARS]
    if suffix in {".htm", ".html"}:
        raw = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return raw


def _tok_eq(a: str, b: str) -> bool:
    """Igualdade tolerante a palavras truncadas por hifenização/ligadura na extração do PDF."""
    return a == b or (min(len(a), len(b)) >= 5 and (a.startswith(b) or b.startswith(a)))


def title_recall(title: str, haystack_tokens: set[str]) -> float:
    t = tokens(title)
    if not t:
        return 0.0
    return sum(1 for x in t if any(_tok_eq(x, h) for h in haystack_tokens)) / len(t)


def title_contiguity(title: str, doc_tokens: list[str]) -> float:
    """Maior sequência CONTÍGUA de tokens do título encontrada no documento / nº de tokens do título.
    Distingue 'o título está lá' de 'as palavras do título aparecem espalhadas'."""
    t = tokens(title)
    if not t or not doc_tokens:
        return 0.0
    best = 0
    for i in range(len(doc_tokens)):
        for j in range(len(t)):
            k = 0
            while i + k < len(doc_tokens) and j + k < len(t) and _tok_eq(doc_tokens[i + k], t[j + k]):
                k += 1
            best = max(best, k)
            if best == len(t):
                return 1.0
    return best / len(t)


def similarity(a: str, b: str) -> float:
    ta, tb = set(tokens(a)), set(tokens(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


# ----------------------------------------------------------------------------- OpenAlex
def openalex_by_doi(doi: str) -> dict | None:
    try:
        import truststore  # usa o repositório de certificados do Windows (inclui CA corporativa)

        truststore.inject_into_ssl()
    except ImportError:
        pass
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi.strip(), flags=re.I)
    url = "https://api.openalex.org/works/doi:" + urllib.parse.quote(doi, safe="/")
    req = urllib.request.Request(url, headers={"User-Agent": "AcademicOS-corpus-check/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"_error": str(exc)}


# ----------------------------------------------------------------------------- verificação
def check_item(item: dict, corpus_dir: Path, online: bool) -> dict:
    res = {"id": item.get("id", "?"), "errors": [], "warnings": [], "info": []}
    ack = item.get("acknowledged")  # string com justificativa -> rebaixa erros a avisos
    waived = item.get("waived")     # string com justificativa -> arquivo ausente aceito

    # 1) arquivo
    fname = item.get("file")
    path = (corpus_dir / fname) if fname else None
    if not path or not path.exists():
        status = "AGUARDANDO_LOGIN" if item.get("access") == "institutional" else "AUSENTE"
        if waived:
            res["warnings"].append(f"Arquivo ausente, dispensado: {waived}")
            res["status"] = "DISPENSADO"
        else:
            res["status"] = status
            res["missing"] = True
        file_ok = False
    else:
        file_ok = True
        res["status"] = "OK"

    # 2) conteúdo do arquivo x obra esperada
    if file_ok:
        try:
            text = extract_text(path)
        except Exception as exc:  # noqa: BLE001
            res["errors"].append(f"Falha ao ler arquivo: {exc}")
            text = ""
        doc_toks = tokens(text)
        rec = title_recall(item.get("title", ""), set(doc_toks))
        cont = title_contiguity(item.get("title", ""), doc_toks)
        res["info"].append(f"título no arquivo: recall = {rec:.2f} | contiguidade = {cont:.2f}")
        authors = item.get("authors") or []
        first = normalize(authors[0]) if authors else ""
        author_found = bool(first) and first in normalize(text)
        if rec < TITLE_RECALL_MIN or cont < TITLE_CONTIGUITY_MIN or (first and not author_found):
            snippet = " ".join(text.split())[:160]
            msg = (f"CONTEÚDO NÃO CORRESPONDE: título recall {rec:.2f} (mín {TITLE_RECALL_MIN}) / "
                   f"contiguidade {cont:.2f} (mín {TITLE_CONTIGUITY_MIN}), 1º autor '{authors[0] if authors else '-'}' "
                   f"{'encontrado' if author_found else 'NÃO encontrado'}. Início do arquivo: \"{snippet}\"")
            (res["warnings"] if ack else res["errors"]).append(msg + (f" [RECONHECIDO: {ack}]" if ack else ""))

    # 3) metadados oficiais x manifesto x citação no documento-base
    if online and item.get("doi"):
        oa = openalex_by_doi(item["doi"])
        if not oa or "_error" in oa:
            res["warnings"].append(f"OpenAlex indisponível para DOI {item['doi']}: {oa.get('_error') if oa else '-'}")
        else:
            off_title = oa.get("title") or ""
            off_year = oa.get("publication_year")
            auths = oa.get("authorships") or []
            off_first = (auths[0].get("author", {}).get("display_name", "") if auths else "")
            off_first_surname = normalize(off_first).split()[-1] if off_first else ""
            src = ((oa.get("primary_location") or {}).get("source") or {}).get("display_name", "")
            res["info"].append(f"OpenAlex: \"{off_title}\" | {off_first} | {off_year} | {src}")
            ack_msg = f" [RECONHECIDO: {ack}]" if ack else ""

            if similarity(off_title, item.get("title", "")) < 0.5:
                (res["warnings"] if ack else res["errors"]).append(
                    f"DOI aponta para outra obra: \"{off_title}\"{ack_msg}")
            cited = normalize(item.get("cited_as", ""))
            if cited:
                if off_first_surname and off_first_surname not in cited:
                    (res["warnings"] if ack else res["errors"]).append(
                        f"CITAÇÃO DIVERGENTE: 1º autor oficial '{off_first}' não aparece em cited_as{ack_msg}")
                if off_year and str(off_year) not in cited:
                    res["warnings"].append(
                        f"Ano oficial {off_year} difere do citado (pode ser early access vs. volume impresso)")
                if src and similarity(src, cited) == 0:
                    res["warnings"].append(f"Veículo oficial '{src}' não reconhecido em cited_as")

    if res["errors"]:
        res["status"] = "REPROVADO"
    elif res["status"] == "OK" and res["warnings"]:
        res["status"] = "OK_COM_AVISOS"
    return res


def render_report(manifest: dict, results: list[dict], online: bool, verdict: str) -> str:
    lines = [
        f"# Relatório de Integridade do Corpus — {manifest.get('research_id', '?')}",
        "",
        f"**Data**: {datetime.now():%Y-%m-%d %H:%M} | **Verificação online (OpenAlex)**: {'sim' if online else 'não'}",
        f"**Veredito**: **{verdict}**",
        "",
        "| # | ID | Status | Erros | Avisos |",
        "|---|----|--------|-------|--------|",
    ]
    for i, r in enumerate(results, 1):
        lines.append(f"| {i} | {r['id']} | {r['status']} | {len(r['errors'])} | {len(r['warnings'])} |")
    lines.append("")
    for r in results:
        if r["errors"] or r["warnings"] or r["info"]:
            lines.append(f"## {r['id']} — {r['status']}")
            lines += [f"- ❌ {e}" for e in r["errors"]]
            lines += [f"- ⚠️ {w}" for w in r["warnings"]]
            lines += [f"- ℹ️ {x}" for x in r["info"]]
            lines.append("")
    lines += [
        "## Como resolver",
        "- **CONTEÚDO NÃO CORRESPONDE**: o arquivo é outra obra. Apague-o e obtenha a versão correta.",
        "  Se for um substituto legítimo (ex.: versão de conferência), registre `acknowledged` com a justificativa.",
        "- **CITAÇÃO DIVERGENTE**: a referência no documento-base está errada. Use os metadados oficiais no",
        "  texto novo e registre a divergência em `citation_discrepancies` (para avisar o autor do documento-base).",
        "- **AGUARDANDO_LOGIN / AUSENTE**: obter via VPN USP / Portal CAPES ou registrar `waived` com justificativa.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--online", action="store_true", help="confere metadados oficiais no OpenAlex via DOI")
    ap.add_argument("--report", type=Path, default=None)
    args = ap.parse_args()

    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))  # tolera BOM do PowerShell
    root = find_workspace_root(manifest_path.parent)
    corpus_dir = (root / manifest["corpus_dir"]).resolve()

    results = [check_item(it, corpus_dir, args.online) for it in manifest.get("items", [])]
    if any(r["errors"] for r in results):
        verdict, code = "REPROVADO", 1
    elif any(r.get("missing") for r in results):
        verdict, code = "PENDENTE (arquivos a obter)", 2
    else:
        verdict, code = "APROVADO", 0

    report_path = args.report or manifest_path.with_name("corpus_integrity_report.md")
    report_path.write_text(render_report(manifest, results, args.online, verdict), encoding="utf-8")

    for i, r in enumerate(results, 1):
        print(f"[{i:02d}] {r['status']:<17} {r['id']}")
        for e in r["errors"]:
            print(f"      ERRO : {e}")
        for w in r["warnings"]:
            print(f"      AVISO: {w}")
    print(f"\nVeredito: {verdict} | relatório: {report_path}")
    return code


if __name__ == "__main__":
    sys.exit(main())
