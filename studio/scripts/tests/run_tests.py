#!/usr/bin/env python3
"""run_tests.py: testes do Studio. Copia studio/ para uma pasta temporária e roda tudo lá (nada do workspace muda).

Uso: python studio/scripts/tests/run_tests.py [--fast]   (--fast pula testes que compilam LaTeX ou usam LibreOffice)
"""
import shutil
import subprocess
import sys
import tempfile
import traceback
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=".*ARC4.*")

SRC = Path(__file__).resolve().parents[2]          # .../studio
FAST = "--fast" in sys.argv
HAS_TEX = shutil.which("pdflatex") is not None
HAS_SOFFICE = shutil.which("soffice") is not None or shutil.which("libreoffice") is not None


def env():
    tmp = Path(tempfile.mkdtemp(prefix="studio_test_"))
    shutil.copytree(SRC, tmp / "studio", ignore=shutil.ignore_patterns("_snapshots", "__pycache__", "jobs", "_smoke"))
    for d in (tmp / "studio/sources").glob("SRC-*"):
        shutil.rmtree(d)
    (tmp / "studio/sources/ledger.yaml").unlink(missing_ok=True)
    return tmp


def run(tmp, script, *args, ok=True):
    r = subprocess.run([sys.executable, str(tmp / "studio/scripts" / script), *map(str, args)], cwd=tmp,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if ok is True and r.returncode != 0:
        raise AssertionError(f"{script} {args} falhou ({r.returncode}):\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    if ok is False and r.returncode == 0:
        raise AssertionError(f"{script} {args} deveria falhar:\n{r.stdout[-800:]}")
    return r


def w(p, text):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def deck_job(tmp, name="job"):
    j = tmp / name
    run(tmp, "mf_deck.py", "new", j, "--blueprint", "business-results")
    w(j / "brief.yaml", "title: Teste\nblueprint: business-results\naudience: gestores\ngoal: decidir\n"
                        "duration_min: 8\nstyle: {kit: default}\n")
    w(j / "outline.yaml", """slides:
- {id: SL-01, section: abertura, archetype: title, message: "Capa"}
- {id: SL-02, section: mensagem, archetype: statement, message: "A conclusão"}
- {id: SL-03, section: impacto, archetype: kpis, message: "Impacto"}
- {id: SL-04, section: evidencia, archetype: chart, message: "Evidência"}
- {id: SL-05, section: riscos, archetype: two_column, message: "Riscos"}
- {id: SL-06, section: decisao, archetype: closing, message: "Decisão"}
""")
    w(j / "spec/U01.yaml", """slides:
- {id: SL-01, archetype: title, title: "Projeto X", subtitle: "Resultados do trimestre"}
- {id: SL-02, archetype: statement, statement: "O piloto reduziu o retrabalho em 30%."}
- id: SL-03
  archetype: kpis
  title: "Três indicadores melhoraram"
  items: [{value: "30%", label: "menos retrabalho"}, {value: "2 h", label: "economia diária"}]
  sources: [SRC-teste#C0001]
- id: SL-04
  archetype: chart
  title: "O ganho aparece em todas as linhas"
  chart: {type: column, categories: [A, B, C], series: [{name: Ganho, values: [0.2, 0.3, 0.4]}], number_format: "0%", highlight: C}
  source: "Medição interna"
- id: SL-05
  archetype: two_column
  title: "Riscos têm mitigação"
  left: {heading: Riscos, bullets: ["Atraso de fornecedor"]}
  right: {heading: Mitigação, bullets: ["Fornecedor alternativo"]}
- {id: SL-06, archetype: closing, title: "Decisão hoje", message: "Aprovar a fase 2"}
""")
    return j


# ------------------------------------------------------------------ deck
def test_deck_plan_validate_build(tmp):
    j = deck_job(tmp)
    run(tmp, "mf_deck.py", "plan", j)
    run(tmp, "mf_deck.py", "validate", j, "--unit", "U01")
    run(tmp, "mf_deck.py", "build", j)
    assert (j / "build/deck.pptx").exists() and (j / "build/slides_index.md").exists()
    from pptx import Presentation
    assert len(Presentation(str(j / "build/deck.pptx")).slides) == 6


def test_deck_limits_detected(tmp):
    j = deck_job(tmp)
    w(j / "spec/U02.yaml", "slides:\n- {id: SL-07, archetype: bullets, title: '" + "x" * 120 + "', bullets: [a,b,c,d,e,f,g]}\n"
                           "- {id: SL-08, archetype: nao_existe}\n")
    r = run(tmp, "mf_deck.py", "validate", j, "--unit", "U02", ok=False)
    assert "90" in r.stdout and "7 itens" in r.stdout and "inexistente" in r.stdout


def test_deck_pending_blocks_qa(tmp):
    j = deck_job(tmp)
    t = (j / "spec/U01.yaml").read_text(encoding="utf-8").replace("O piloto reduziu o retrabalho em 30%.",
                                                                  "O piloto reduziu o retrabalho em [[PENDENTE: %]].")
    w(j / "spec/U01.yaml", t)
    run(tmp, "mf_deck.py", "build", j)
    r = run(tmp, "mf_deck.py", "qa", j, ok=False)
    assert "PENDENTE" in r.stdout


def test_deck_template_mode(tmp):
    from pptx import Presentation
    from pptx.util import Inches
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    prs.save(tmp / "corp.pptx")
    run(tmp, "mf_deck.py", "inspect-template", tmp / "corp.pptx", "--id", "corp", "--kit", "default")
    assert (tmp / "studio/templates/pptx/corp/template.yaml").exists()
    j = deck_job(tmp)
    run(tmp, "mf_deck.py", "build", j, "--template", "corp")
    assert len(Presentation(str(j / "build/deck.pptx")).slides) == 6


def test_deck_preview(tmp):
    if FAST or not HAS_SOFFICE:
        return "pulado"
    j = deck_job(tmp)
    run(tmp, "mf_deck.py", "build", j)
    run(tmp, "mf_deck.py", "preview", j)
    assert (j / "build/deck.pdf").exists()


def test_kit_check(tmp):
    run(tmp, "mf_deck.py", "kit-check", "default")


# ------------------------------------------------------------------ latex
def test_beamer(tmp):
    if FAST or not HAS_TEX:
        return "pulado"
    j = deck_job(tmp)
    run(tmp, "mf_latex.py", "beamer", j, "--theme", "default")
    assert (j / "build/deck_beamer.pdf").exists()


def test_latex_inspect_lint_build(tmp):
    run(tmp, "mf_latex.py", "inspect", "--builtin", "studio-article", "--force")
    j = tmp / "doc"
    run(tmp, "mf_latex.py", "new", "studio-article", j)
    w(j / "doc.yaml", "template: studio-article\nmetadata: {title: T, author: A, date: D}\nfront: {abstract: Resumo.}\n"
                      "sections:\n  - {id: S01, title: Intro, level: 1, target_words: 300}\nappendix: []\n"
                      "bibliography: references.bib\n")
    w(j / "references.bib", "@book{k2020,\n author={A},\n title={T},\n year={2020}\n}\n")
    run(tmp, "mf_latex.py", "plan", j)
    w(j / "content/sections/S01.p1.tex", "Texto com 50% de erro \\cite{nao_existe}.\n")
    r = run(tmp, "mf_latex.py", "lint", j, "--unit", "S01.p1", ok=False)
    assert "sem escape" in r.stdout and "nao_existe" in r.stdout
    w(j / "content/sections/S01.p1.tex", "Texto correto com 50\\% e citação \\cite{k2020}. $x^2$.\n")
    run(tmp, "mf_latex.py", "lint", j, "--unit", "S01.p1")
    if not FAST and HAS_TEX:
        run(tmp, "mf_latex.py", "build", j)
        assert (j / "build/document.pdf").exists()


# ------------------------------------------------------------------ sources
def _pdf(tmp):
    from pypdf import PdfWriter
    wr = PdfWriter()
    for _ in range(8):
        wr.add_blank_page(width=200, height=200)
    p = tmp / "livro.pdf"
    with open(p, "wb") as fh:
        wr.write(fh)
    return p


def test_sources_flow_and_coverage(tmp):
    p = _pdf(tmp)
    run(tmp, "sl_sources.py", "add", p, "--type", "book", "--title", "Livro", "--authors", "Silva, Ana", "--year", "2020",
        "--id", "SRC-silva-2020")
    run(tmp, "sl_sources.py", "chunk", "SRC-silva-2020", "--pages", "4")
    chunks = sorted((tmp / "studio/sources/SRC-silva-2020/chunks").glob("C*.pdf"))
    assert len(chunks) == 2
    w(tmp / "studio/sources/SRC-silva-2020/chunks/C0001.txt",
      "Definição 1.1 Um grafo é um par de conjuntos. Teorema 1.2 Todo grafo finito tem um vértice. "
      "Algoritmo 1.3 BFS visita em largura.")
    w(tmp / "studio/sources/SRC-silva-2020/cards/C0001.yaml",
      "source: SRC-silva-2020\nchunk: C0001\nloc: [1, 4]\nstatus: done\nsummary: Grafos.\n"
      "concepts: [{name: Grafo, loc: 1, definition: ''}]\n"
      "items: [{type: definition, label: Def 1.1, loc: 1, text: 'Um grafo é um par de conjuntos.'}]\n")
    r = run(tmp, "sl_sources.py", "validate", "SRC-silva-2020", "--chunk", "C0001", ok=False)
    assert "sumariza" in r.stdout
    w(tmp / "studio/sources/SRC-silva-2020/cards/C0001.yaml",
      "source: SRC-silva-2020\nchunk: C0001\nloc: [1, 4]\nstatus: done\nsummary: Grafos e BFS.\n"
      "concepts: [{name: Grafo, loc: 1, definition: 'Um grafo é um par de conjuntos.'}, {name: Busca em largura, "
      "aliases: [BFS], loc: 2, definition: ''}]\n"
      "items:\n - {type: definition, label: Definição 1.1, loc: 1, text: 'Um grafo é um par de conjuntos.'}\n"
      " - {type: theorem, label: Teorema 1.2, loc: 1, text: 'Todo grafo finito tem um vértice.'}\n"
      " - {type: algorithm, label: Algoritmo 1.3, loc: 2, text: 'BFS visita em largura.'}\n")
    run(tmp, "sl_sources.py", "validate", "SRC-silva-2020", "--chunk", "C0001")
    w(tmp / "kg.md", "```yaml\nnodes:\n  - {id: K-01, name: Grafo, level: foundation, criticality: essential, "
                     "outcomes: [O-01], effort_minutes: 30}\n  - {id: K-02, name: Fluxo máximo, level: core, "
                     "criticality: essential, outcomes: [O-02], effort_minutes: 60}\n```\n")
    r = run(tmp, "sl_sources.py", "coverage", "--graph", tmp / "kg.md", "--policy", "strict", ok=False)
    assert "K-02" in r.stdout and (tmp / "coverage_report.md").exists()
    r = run(tmp, "sl_sources.py", "requests", "--open")
    assert "Fluxo m" in r.stdout
    r = run(tmp, "sl_sources.py", "pack", "--concepts", "Grafo; Fluxo máximo")
    assert "Um grafo" in r.stdout and "SEM FONTE" in r.stdout
    r = run(tmp, "sl_sources.py", "bib")
    assert "@book{silva2020" in r.stdout


# ------------------------------------------------------------------ review
def test_review_flow(tmp):
    j = deck_job(tmp)
    run(tmp, "rep_review.py", "plan", j, "--panel", "eldorado-negocios", "--slice", "8")
    r = run(tmp, "rep_review.py", "brief", j, "R02")
    assert "Rubrica" in r.stdout and "SL-02" in r.stdout
    w(j / "review/R02.yaml", """unit: R02
persona: gestor-negocios
lenses: [audience, persuasion, narrative]
scores: [{criterion: R1, score: 4, why: "conclusão no início"}]
findings:
  - {id: F-R02-01, lens: narrative, criterion: NAR-4, severity: major, location: SL-06, evidence: "Aprovar a fase 2",
     problem: "Não diz custo nem prazo da fase 2", suggested_fix: "Incluir custo e prazo"}
  - {id: F-R02-02, lens: audience, criterion: AUD-1, severity: minor, location: SL-99, evidence: "x",
     problem: "p", suggested_fix: "f"}
questions: [{q: "Quanto custa a fase 2?", location: SL-06, difficulty: alta}]
""")
    r = run(tmp, "rep_review.py", "validate", j, "--unit", "R02", ok=False)
    assert "SL-99" in r.stdout
    t = (j / "review/R02.yaml").read_text(encoding="utf-8").replace("SL-99", "SL-05")
    w(j / "review/R02.yaml", t)
    run(tmp, "rep_review.py", "validate", j, "--unit", "R02")
    run(tmp, "rep_review.py", "consolidate", j)
    assert "Quanto custa" in (j / "review/qa_bank.md").read_text(encoding="utf-8")
    assert "C-001" in (j / "review/report.md").read_text(encoding="utf-8")


def test_snapshot(tmp):
    (tmp / ".agents/skills/kf-x").mkdir(parents=True)
    w(tmp / ".agents/skills/kf-x/SKILL.md", "---\nname: kf-x\ndescription: x\n---\ntoken: abcdefghijklmnopqrst\n")
    w(tmp / ".agents/skills/outra/SKILL.md", "---\nname: outra\ndescription: outra frente\n---\n")
    r = run(tmp, "studio_snapshot.py", "--root", tmp)
    assert "1 segredo" in r.stdout


def main():
    tests = [(k, v) for k, v in globals().items() if k.startswith("test_") and callable(v)]
    failed = 0
    for name, fn in tests:
        tmp = env()
        try:
            res = fn(tmp)
            print(f"{'SKIP' if res == 'pulado' else 'PASS'}  {name}")
        except Exception:
            failed += 1
            print(f"FAIL  {name}\n{traceback.format_exc()}".encode('cp1252', 'replace').decode('cp1252'))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{len(tests) - failed}/{len(tests)} testes passaram.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
