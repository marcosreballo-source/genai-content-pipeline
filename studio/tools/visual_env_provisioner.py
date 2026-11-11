#!/usr/bin/env python3
"""studio/tools/visual_env_provisioner.py: Provisionador automático multi-runtime (Python, JS/Node, R, Graphviz, LaTeX)
com descoberta multi-caminho no Windows e bypass automático de proxy Zscaler.

Uso:
  python studio/tools/visual_env_provisioner.py --status
  python studio/tools/visual_env_provisioner.py --ensure <biblioteca>
  python studio/tools/visual_env_provisioner.py --render-html <input.html> <output.png> [--width 2000] [--height 1200]
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from visual_sota_auditor import load_registry  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
JS_ENV = Path(__file__).resolve().parent / ".js_env"

ZSCALER_PIP_FLAGS = [
    "--native-tls",
    "--trusted-host", "pypi.org",
    "--trusted-host", "pypi.python.org",
    "--trusted-host", "files.pythonhosted.org",
]

SEARCH_PATHS = {
    "uv": [
        os.path.expandvars(r"%USERPROFILE%\.local\bin\uv.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\uv\uv.exe"),
        os.path.expandvars(r"%APPDATA%\Python\Scripts\uv.exe"),
    ],
    "node": [
        r"C:\Program Files\nodejs\node.exe",
        r"C:\Program Files (x86)\nodejs\node.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\nodejs\node.exe"),
        os.path.expandvars(r"%APPDATA%\nvm\*\node.exe"),
    ],
    "npm": [
        r"C:\Program Files\nodejs\npm.cmd",
        r"C:\Program Files (x86)\nodejs\npm.cmd",
        os.path.expandvars(r"%APPDATA%\nvm\*\npm.cmd"),
    ],
    "browser": [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ],
    "rscript": [
        r"C:\Program Files\R\R-*\bin\x64\Rscript.exe",
        r"C:\Program Files\R\R-*\bin\Rscript.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\R\R-*\bin\x64\Rscript.exe"),
    ],
    "dot": [
        r"C:\Program Files\Graphviz\bin\dot.exe",
        r"C:\Program Files (x86)\Graphviz\bin\dot.exe",
        os.path.expandvars(r"%USERPROFILE%\scoop\apps\graphviz\current\bin\dot.exe"),
    ],
    "pdflatex": [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"),
        r"C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe",
        r"C:\texlive\*\bin\windows\pdflatex.exe",
    ],
}


def find_binary(key: str, exe_names: list[str]) -> str | None:
    for name in exe_names:
        found = shutil.which(name)
        if found:
            return found
    for pattern in SEARCH_PATHS.get(key, []):
        matches = sorted(glob.glob(pattern), reverse=True)
        for m in matches:
            if os.path.isfile(m):
                return m
    return None


def ensure_python_pkg(pkg: str) -> bool:
    import_map = {
        "pillow": "PIL",
        "plotly": "plotly",
        "matplotlib": "matplotlib",
        "seaborn": "seaborn",
        "networkx": "networkx",
        "altair": "altair",
        "bokeh": "bokeh",
        "dash": "dash",
        "mpld3": "mpld3",
        "chaco": "chaco",
    }
    mod = import_map.get(pkg.lower(), pkg.lower())
    r = subprocess.run([str(VENV_PY), "-c", f"import {mod}"], capture_output=True)
    if r.returncode == 0:
        print(f"[PYTHON OK] Pacote '{pkg}' ({mod}) já está ativo em {VENV_PY}.")
        return True
    uv = find_binary("uv", ["uv", "uv.exe"])
    if not uv:
        print(
            "ERRO: 'uv' não encontrado. Instale com:\n"
            "  powershell -ExecutionPolicy ByPass -c \"irm https://astral.sh/uv/install.ps1 | iex\"",
            file=sys.stderr,
        )
        return False
    cmd = [uv, "pip", "install", "--python", str(VENV_PY), pkg] + ZSCALER_PIP_FLAGS
    print(f"[PROVISIONANDO PYTHON] Executando: {' '.join(cmd)}")
    res = subprocess.run(cmd)
    return res.returncode == 0


def ensure_js_pkg(pkg: str) -> bool:
    node = find_binary("node", ["node", "node.exe"])
    npm = find_binary("npm", ["npm.cmd", "npm"])
    browser = find_binary("browser", ["msedge.exe", "chrome.exe"])
    if not node or not npm:
        print(
            "[AÇÃO REQUERIDA - NODE.JS] Node.js não encontrado nos caminhos padrão.\n"
            "Execute no PowerShell:\n  winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements",
            file=sys.stderr,
        )
        return False
    JS_ENV.mkdir(parents=True, exist_ok=True)
    pkg_json = JS_ENV / "package.json"
    if not pkg_json.exists():
        pkg_json.write_text('{"name": "studio-js-visual-env", "private": true}\n', encoding="utf-8")
    target_dir = JS_ENV / "node_modules" / pkg.split("/")[0]
    if target_dir.exists():
        print(f"[JS OK] Pacote '{pkg}' ativo em {JS_ENV / 'node_modules'} (Browser Headless: {browser or 'ausente'}).")
        return True
    env = os.environ.copy()
    env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
    cmd = [npm, "install", "--prefix", str(JS_ENV), "--strict-ssl=false", pkg]
    print(f"[PROVISIONANDO JS] Executando: {' '.join(cmd)}")
    res = subprocess.run(cmd, env=env)
    return res.returncode == 0


def ensure_r_pkg(pkg: str) -> bool:
    rscript = find_binary("rscript", ["Rscript.exe", "Rscript"])
    if not rscript:
        print(
            "[AÇÃO REQUERIDA - R / GGPLOT2] Rscript.exe não encontrado.\n"
            "Execute no PowerShell:\n  winget install RProject.R --accept-source-agreements --accept-package-agreements",
            file=sys.stderr,
        )
        return False
    chk = subprocess.run(
        [rscript, "-e", f"if (!requireNamespace('{pkg}', quietly=TRUE)) quit(status=1)"],
        capture_output=True,
    )
    if chk.returncode == 0:
        print(f"[R OK] Pacote '{pkg}' ativo via {rscript}.")
        return True
    cmd = [
        rscript,
        "-e",
        f"options(download.file.method='wininet'); install.packages('{pkg}', repos='https://cloud.r-project.org')",
    ]
    print(f"[PROVISIONANDO R] Instalando '{pkg}' com wininet (bypass Zscaler)...")
    return subprocess.run(cmd).returncode == 0


def render_html_to_png(html_path: Path, png_path: Path, width: int = 2000, height: int = 1200) -> int:
    browser = find_binary("browser", ["msedge.exe", "chrome.exe"])
    if not browser:
        print("ERRO: Navegador Chromium (Edge/Chrome) não encontrado para renderização headless.", file=sys.stderr)
        return 1
    png_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        browser,
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--window-size={width},{height}",
        f"--screenshot={png_path.resolve()}",
        html_path.resolve().as_uri(),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if not png_path.exists():
        print(f"ERRO ao renderizar HTML para PNG: {res.stderr}", file=sys.stderr)
        return 1
    print(f"[HTML->PNG OK] {png_path} ({width}x{height}px)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--status", action="store_true", help="Mostra status dos runtimes descobertos no Windows")
    ap.add_argument("--ensure", help="Nome da biblioteca do catálogo SOTA para garantir instalação")
    ap.add_argument("--render-html", nargs=2, metavar=("IN_HTML", "OUT_PNG"), help="Renderiza HTML/JS em PNG")
    ap.add_argument("--width", type=int, default=2000)
    ap.add_argument("--height", type=int, default=1200)
    args = ap.parse_args()

    if args.status:
        print("=== STATUS DOS RUNTIMES VISUAIS DESCOBERTOS ===")
        print(f"  Python (.venv): {VENV_PY if VENV_PY.exists() else 'AUSENTE'}")
        for k, names in [
            ("uv", ["uv.exe"]),
            ("node", ["node.exe"]),
            ("npm", ["npm.cmd"]),
            ("browser", ["msedge.exe", "chrome.exe"]),
            ("rscript", ["Rscript.exe"]),
            ("dot", ["dot.exe"]),
            ("pdflatex", ["pdflatex.exe"]),
        ]:
            print(f"  {k:14s}: {find_binary(k, names) or 'NÃO ENCONTRADO'}")
        return 0

    if args.render_html:
        return render_html_to_png(Path(args.render_html[0]), Path(args.render_html[1]), args.width, args.height)

    if args.ensure:
        reg = load_registry()
        libs = reg.get("libraries", {})
        match = next((k for k in libs if k.lower() == args.ensure.lower()), None)
        if not match:
            print(f"ERRO: Biblioteca '{args.ensure}' desconhecida.", file=sys.stderr)
            return 1
        info = libs[match]
        eco = info["ecosystem"]
        pkg = info["pkg"]
        if eco == "python":
            return 0 if ensure_python_pkg(pkg) else 1
        if eco == "js":
            return 0 if ensure_js_pkg(pkg) else 1
        if eco == "r":
            return 0 if ensure_r_pkg(pkg) else 1
        if eco == "system":
            dot = find_binary("dot", ["dot.exe", "dot"])
            if dot:
                print(f"[SYSTEM OK] Graphviz encontrado em: {dot}")
                return 0
            print("Instale Graphviz com: winget install Graphviz.Graphviz", file=sys.stderr)
            return 1
        if eco == "tex":
            tex = find_binary("pdflatex", ["pdflatex.exe", "pdflatex"])
            if tex:
                print(f"[TEX OK] pdflatex encontrado em: {tex}")
                return 0
            print("Instale MiKTeX com: winget install MiKTeX.MiKTeX", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

