#!/usr/bin/env python3
"""studio_next.py: diz qual é o PRÓXIMO passo de um job do Studio (deck, documento, fonte ou revisão).

É o "piloto automático" para modelos de resposta curta: o agente roda este comando, executa só o passo
indicado (uma unidade por rodada), e roda de novo. Nunca altera arquivos.

Uso:
  python studio/scripts/studio_next.py <pasta-do-job>
  python studio/scripts/studio_next.py --source SRC-x
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from studio_common import STUDIO, load_yaml  # noqa: E402

S = "python studio/scripts/"


def say(step, cmd=None, skill=None, why=""):
    print(f"PRÓXIMO PASSO: {step}")
    if skill:
        print(f"  skill: {skill}")
    if cmd:
        print(f"  comando: {cmd}")
    if why:
        print(f"  motivo: {why}")
    return 0


def review_next(job, final_cmd):
    rv = job / "review"
    plan = load_yaml(rv / "plan.yaml", {})
    if not plan:
        return None
    pend = [u for u in plan.get("units", []) if u.get("status") != "done"]
    if pend:
        u = pend[0]
        return say(f"revisão: unidade {u['id']} ({u['persona']}, {', '.join(u['lenses'])})",
                   f"{S}rep_review.py brief {job} {u['id']}   # depois escreva review/{u['id']}.yaml e: "
                   f"{S}rep_review.py validate {job} --unit {u['id']}", "rep-reviewer",
                   f"{len(pend)} unidade(s) de revisão pendente(s)")
    cons = rv / "consolidated.yaml"
    if not cons.exists() or cons.stat().st_mtime < max((rv / f"{u['id']}.yaml").stat().st_mtime
                                                       for u in plan["units"] if (rv / f"{u['id']}.yaml").exists()):
        return say("consolidar a revisão", f"{S}rep_review.py consolidate {job}")
    rp = load_yaml(rv / "revision_plan.yaml", {"items": []})
    todo = [(it["location"], a) for it in rp.get("items", []) for a in it["actions"]
            if a.get("status") != "done" and a["severity"] in ("blocker", "major")]
    if todo:
        loc, act = todo[0]
        return say(f"corrigir {act['finding']} ({act['severity']}) em {loc}: {act['action']}",
                   None, "mf-deck-writer ou mf-doc-writer (modo correção)",
                   f"{len(todo)} correção(ões) blocker/major pendente(s); marque status: done no revision_plan.yaml")
    fixed = [a for it in rp.get("items", []) for a in it["actions"] if a.get("status") == "done"]
    deltas = [u for u in plan["units"] if u["id"].startswith("D")]
    if fixed and not deltas:
        return say("rebuild e re-revisão do que foi corrigido",
                   f"{final_cmd}  &&  {S}rep_review.py delta {job}")
    return None


def deck_next(job):
    brief = load_yaml(job / "brief.yaml", {})
    for k in ("title", "audience", "goal", "duration_min"):
        if not brief.get(k):
            return say("completar o brief (no máximo 6 perguntas ao usuário)", None, "mf-brief", f"campo vazio: {k}")
    outline = load_yaml(job / "outline.yaml", {"slides": []})
    if not outline.get("slides") or any(str(s.get("message", "")).startswith("<") for s in outline["slides"]):
        return say("escrever o outline (1 linha por slide) a partir do blueprint", f"{S}mf_deck.py plan {job}",
                   "mf-deck-architect", "outline vazio ou com marcadores do esqueleto")
    if not (job / "outline.approved").exists():
        return say("mostrar o outline ao usuário e pedir aprovação; aprovado -> criar o arquivo vazio outline.approved",
                   None, "mf-deck-architect")
    plan = load_yaml(job / "plan.yaml", {})
    if not plan:
        return say("planejar as unidades", f"{S}mf_deck.py plan {job}")
    for u in plan.get("units", []):
        if u.get("status") != "done":
            return say(f"escrever a unidade {u['id']} ({', '.join(u['slides'])})",
                       f"{S}mf_deck.py validate {job} --unit {u['id']}", "mf-deck-writer",
                       "uma unidade por rodada; validate sem erros marca como done")
    pptx = job / "build" / "deck.pptx"
    specs = [f.stat().st_mtime for f in (job / "spec").glob("U*.yaml")]
    if not pptx.exists() or (specs and pptx.stat().st_mtime < max(specs)):
        return say("gerar o deck e a prévia", f"{S}mf_deck.py build {job} && {S}mf_deck.py preview {job} && "
                                              f"{S}mf_deck.py qa {job}", "mf-visual-qa")
    qa = job / "build" / "qa_report.md"
    if not qa.exists() or "| ERRO |" in qa.read_text(encoding="utf-8"):
        return say("resolver o QA (erros em build/qa_report.md) e conferir a prévia", f"{S}mf_deck.py qa {job}",
                   "mf-visual-qa")
    r = review_next(job, f"{S}mf_deck.py build {job} && {S}mf_deck.py preview {job}")
    if r is not None:
        return r
    if not (job / "review" / "plan.yaml").exists():
        panel = brief.get("panel") or "(padrão do blueprint)"
        return say(f"revisão pelo painel {panel}", f"{S}rep_review.py plan {job} --panel <painel>", "rep-reviewer")
    return say("PRONTO para entrega: deck.pptx, deck.pdf, speaker_notes.md e review/qa_bank.md",
               f"{S}mf_deck.py notes {job}")


def doc_next(job):
    doc = load_yaml(job / "doc.yaml", {})
    if not doc.get("sections") or any(s.get("brief") == "o que esta seção precisa cobrir" for s in doc["sections"]):
        return say("definir as seções no doc.yaml (título, nível, palavras, fontes, brief)", None, "mf-doc-architect")
    if not (job / "doc.approved").exists():
        return say("mostrar a estrutura ao usuário e pedir aprovação; aprovado -> criar doc.approved", None,
                   "mf-doc-architect")
    plan = load_yaml(job / "plan.yaml", {})
    if not plan:
        return say("planejar as unidades", f"{S}mf_latex.py plan {job}")
    for u in plan.get("units", []):
        if u.get("status") != "done":
            return say(f"escrever a unidade {u['id']} -> {u['file']} (~{u['target_words']} palavras)",
                       f"{S}mf_latex.py lint {job} --unit {u['id']}", "mf-doc-writer")
    pdf = job / "build" / "document.pdf"
    frags = [f.stat().st_mtime for f in (job / "content").rglob("*.tex")]
    if not pdf.exists() or (frags and pdf.stat().st_mtime < max(frags)):
        return say("compilar", f"{S}mf_latex.py lint {job} && {S}mf_latex.py build {job}", "mf-doc-writer",
                   "leia build/latex_report.md depois")
    rep = job / "build" / "latex_report.md"
    if rep.exists() and "| ERRO |" in rep.read_text(encoding="utf-8"):
        return say("corrigir erros de build (build/latex_report.md aponta o fragmento e a linha)", None, "mf-doc-writer")
    r = review_next(job, f"{S}mf_latex.py build {job}")
    if r is not None:
        return r
    if not (job / "review" / "plan.yaml").exists():
        return say("revisão pelo painel", f"{S}rep_review.py plan {job} --panel <painel>", "rep-reviewer")
    return say("PRONTO para entrega: build/document.pdf")


def source_next(sid):
    lib = Path(os.environ.get("STUDIO_SOURCES") or (STUDIO / "sources"))
    L = load_yaml(lib / "ledger.yaml", {"sources": {}})
    s = L["sources"].get(sid)
    if not s:
        return say(f"registrar a fonte {sid}", f"{S}sl_sources.py add <arquivo> --type ... --id {sid}", "sl-ingest")
    ch = lib / sid / "chunks"
    if not ch.exists() or not any(ch.glob("C*")):
        return say("dividir em trechos (ou importar do seu pipeline)", f"{S}sl_sources.py chunk {sid}", "sl-ingest")
    ids = sorted({p.stem.split(".")[0] for p in ch.glob("C*.*")})
    cards = lib / sid / "cards"
    for c in ids:
        if not list(cards.glob(f"{c}.yaml")) and not list(cards.glob(f"{c}.*.yaml")):
            return say(f"fichar o trecho {c} ({ids.index(c) + 1}/{len(ids)})",
                       f"{S}sl_sources.py next {sid}  # depois: {S}sl_sources.py validate {sid} --chunk {c}",
                       "sl-extract")
    return say("validar tudo e indexar", f"{S}sl_sources.py validate {sid} && {S}sl_sources.py index")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", nargs="?")
    ap.add_argument("--source")
    a = ap.parse_args()
    if a.source:
        return source_next(a.source)
    if not a.job:
        ap.error("informe a pasta do job ou --source")
    job = Path(a.job)
    if (job / "brief.yaml").exists():
        return deck_next(job)
    if (job / "doc.yaml").exists():
        return doc_next(job)
    if (job / "review" / "plan.yaml").exists():
        return review_next(job, "") or say("revisão concluída")
    return say("criar o job", f"{S}mf_deck.py new {job} --blueprint <id>   ou   {S}mf_latex.py new <template> {job}")


if __name__ == "__main__":
    sys.exit(main())
