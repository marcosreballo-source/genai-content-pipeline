#!/usr/bin/env python3
"""studio_doctor.py: verifica as ferramentas que o Studio usa e diz como instalar o que falta (por sistema).

Uso: python studio/scripts/studio_doctor.py [--json]
Exit 0 = essenciais OK (opcionais podem faltar); 1 = falta algo essencial.
"""
import importlib
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from studio_common import SOFFICE_PATHS, find_exe  # noqa: E402

OS = platform.system()  # Windows | Darwin | Linux
PY = [("yaml", "pyyaml", True, "ler/escrever YAML"), ("pptx", "python-pptx", True, "gerar .pptx"),
      ("PIL", "pillow", True, "imagens e contact sheet"), ("jinja2", "jinja2", False, "templates"),
      ("matplotlib", "matplotlib", True, "equações e gráficos (Beamer/documentos)"),
      ("pypdf", "pypdf", True, "dividir PDFs em trechos (Source Library)"),
      ("fitz", "pymupdf", False, "PNG de PDF sem poppler (alternativa)")]
INSTALL = {
    "soffice": {"Windows": "winget install TheDocumentFoundation.LibreOffice", "Darwin": "brew install --cask libreoffice",
                "Linux": "sudo apt install libreoffice-impress"},
    "latexmk": {"Windows": "instale MiKTeX (miktex.org) ou TeX Live; latexmk precisa de Perl (Strawberry Perl)",
                "Darwin": "brew install --cask mactex-no-gui", "Linux": "sudo apt install texlive-full latexmk"},
    "pdflatex": {"Windows": "MiKTeX ou TeX Live", "Darwin": "brew install --cask mactex-no-gui",
                 "Linux": "sudo apt install texlive-latex-extra texlive-lang-portuguese"},
    "pdftoppm": {"Windows": "winget install oschwartz10612.Poppler  (ou: pip install pymupdf)",
                 "Darwin": "brew install poppler", "Linux": "sudo apt install poppler-utils"},
    "mmdc": {"Windows": "npm install -g @mermaid-js/mermaid-cli", "Darwin": "npm install -g @mermaid-js/mermaid-cli",
             "Linux": "npm install -g @mermaid-js/mermaid-cli"},
    "pandoc": {"Windows": "winget install JohnMacFarlane.Pandoc", "Darwin": "brew install pandoc",
               "Linux": "sudo apt install pandoc"},
}
EXES = [("soffice", ["soffice", "libreoffice"], True, "prévia PNG/PDF dos .pptx (QA visual)"),
        ("pdflatex", ["pdflatex"], True, "documentos LaTeX e Beamer"),
        ("latexmk", ["latexmk"], False, "compilação LaTeX automática (bib, referências)"),
        ("pdftoppm", ["pdftoppm"], False, "PDF -> PNG (ou pymupdf)"),
        ("mmdc", ["mmdc", "mmdc.cmd"], False, "diagramas Mermaid"),
        ("pandoc", ["pandoc"], False, "conversões futuras (docx/html)")]
LATEX_PKGS = ["beamer.cls", "beamerthememetropolis.sty", "portuges.ldf", "booktabs.sty", "listings.sty", "tcolorbox.sty",
              "tikz.sty", "lmodern.sty", "exam.cls", "abntex2.cls", "biblatex.sty"]


def main():
    res = {"os": OS, "python": sys.version.split()[0], "python_pkgs": {}, "exes": {}, "latex_pkgs": {}, "missing": []}
    essential_missing = False
    print(f"Sistema: {OS} · Python {res['python']}")
    print("\nBibliotecas Python:")
    for mod, pipname, ess, why in PY:
        try:
            importlib.import_module(mod)
            ok = True
        except ImportError:
            ok = False
        res["python_pkgs"][pipname] = ok
        print(f"  {'OK ' if ok else 'FALTA'} {pipname:14s} {'(essencial)' if ess else '(opcional) '} {why}")
        if not ok:
            res["missing"].append(f"pip install {pipname}")
            essential_missing |= ess
    print("\nProgramas:")
    for key, names, ess, why in EXES:
        p = find_exe(names, SOFFICE_PATHS if key == "soffice" else ())
        res["exes"][key] = p
        print(f"  {'OK ' if p else 'FALTA'} {key:10s} {'(essencial)' if ess else '(opcional) '} {why}" +
              (f"  -> {p}" if p else ""))
        if not p:
            res["missing"].append(INSTALL.get(key, {}).get(OS, f"instale {key}"))
            essential_missing |= ess
    kp = find_exe(["kpsewhich"])
    if kp:
        print("\nPacotes LaTeX (opcionais, mas recomendados):")
        for f in LATEX_PKGS:
            r = subprocess.run([kp, f], capture_output=True, text=True).stdout.strip()
            res["latex_pkgs"][f] = bool(r)
            print(f"  {'OK ' if r else 'FALTA'} {f}")
        if not res["latex_pkgs"].get("portuges.ldf"):
            res["missing"].append("pacote LaTeX babel-portuges (hifenização e títulos em português)")
        if not res["latex_pkgs"].get("abntex2.cls"):
            res["missing"].append("pacote LaTeX abntex2 (modelos ABNT/USP)")
    if res["exes"].get("mmdc"):
        print("\nDica Mermaid: se o mmdc não achar o Chrome, defina STUDIO_CHROME com o caminho do Chrome/Chromium.")
    if res["missing"]:
        print("\nPara instalar o que falta:")
        for m in dict.fromkeys(res["missing"]):
            print(f"  - {m}")
    print("\nResultado: " + ("FALTA ALGO ESSENCIAL" if essential_missing else "essenciais OK"))
    if "--json" in sys.argv:
        print(json.dumps(res, indent=1))
    return 1 if essential_missing else 0


if __name__ == "__main__":
    sys.exit(main())
