#!/usr/bin/env python3
"""studio_snapshot.py: empacota a instalação da Knowledge Factory (e, se quiser, das outras frentes)
num .zip para ser anexado numa conversa com o Claude. SOMENTE LEITURA: só escreve o .zip.

Uso (na raiz do workspace):
  python studio/scripts/studio_snapshot.py                       # KF completa + nomes/descrições das outras frentes
  python studio/scripts/studio_snapshot.py --other-fronts full   # inclui o texto das skills/workflows/rules das outras frentes
  python studio/scripts/studio_snapshot.py --projects KT_Aramis  # só esse projeto KF (padrão: todos, só texto)

O que entra:
  - itens kf-* da pasta de agentes (skills, workflows, rules), completos
  - knowledge_factory/ (implementation, mapping, templates, scripts, docs, archive, projects): só arquivos de texto
  - GEMINI.md / AGENTS.md / CLAUDE.md da raiz
  - outras frentes: só nome+descrição (padrão) ou texto completo (--other-fronts full)
  - árvore de pastas da raiz (nomes e contagens, sem conteúdo)
O que NUNCA entra: .git, node_modules, binários, arquivos > 400 KB, .env, chaves; segredos detectados são mascarados.
"""
import argparse
import datetime
import io
import json
import re
import sys
import zipfile
from pathlib import Path

TEXT_EXT = {".md", ".txt", ".yaml", ".yml", ".json", ".py", ".tex", ".bib", ".csv", ".toml", ".sh", ".ps1",
            ".j2", ".html", ".css", ".js", ".mmd", ".puml", ".dot", ".ipynb", ".cfg", ".ini"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".ipynb_checkpoints", "_snapshots"}
SKIP_NAMES = re.compile(r"(^\.env)|(\.key$)|(\.pem$)|(^id_rsa)|(secret)|(credential)", re.I)
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"), re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"), re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"(?i)(api[_-]?key|token|password|senha)\s*[:=]\s*['\"]?[^\s'\"]{8,}"),
]
MAX_FILE = 400 * 1024
MAX_TOTAL = 40 * 1024 * 1024
ROOT_FILES = ["GEMINI.md", "AGENTS.md", "CLAUDE.md"]


def detect_agent_dir(root):
    log = root / "knowledge_factory/implementation/LOG.md"
    if log.exists():
        m = re.search(r"AGENT_DIR:\s*`?([^\s`]+)", log.read_text(encoding="utf-8", errors="replace"))
        if m and (root / m.group(1)).is_dir():
            return root / m.group(1)
    for d in (".agents", ".agent"):
        if (root / d).is_dir():
            return root / d
    return None


def frontmatter_desc(text):
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if not m:
        return ""
    d = re.search(r"^description:\s*(.*)$", m.group(1), re.M)
    return d.group(1).strip().strip("\"'") if d else ""


def redact(text, counter):
    for p in SECRET_PATTERNS:
        text, n = p.subn("[REDACTED]", text)
        counter[0] += n
    return text


class Packer:
    def __init__(self, root, zf):
        self.root, self.zf = root, zf
        self.total, self.files, self.skipped, self.redacted = 0, 0, [], [0]

    def add_file(self, p, arc=None):
        rel = p.relative_to(self.root).as_posix()
        if SKIP_NAMES.search(p.name):
            self.skipped.append(f"{rel} (nome sensível)")
            return
        if p.suffix.lower() not in TEXT_EXT:
            self.skipped.append(f"{rel} (não é texto)")
            return
        size = p.stat().st_size
        if size > MAX_FILE:
            self.skipped.append(f"{rel} ({size // 1024} KB > limite)")
            return
        if self.total + size > MAX_TOTAL:
            self.skipped.append(f"{rel} (limite total atingido)")
            return
        text = redact(p.read_text(encoding="utf-8", errors="replace"), self.redacted)
        self.zf.writestr(arc or rel, text)
        self.total += size
        self.files += 1

    def add_tree(self, base):
        if not base.exists():
            return
        if base.is_file():
            self.add_file(base)
            return
        for p in sorted(base.rglob("*")):
            if p.is_file() and not (set(p.relative_to(self.root).parts) & SKIP_DIRS):
                self.add_file(p)


def tree_listing(root, depth=2):
    lines = []

    def walk(d, level):
        try:
            entries = sorted(x for x in d.iterdir() if x.name not in SKIP_DIRS)
        except OSError:
            return
        for e in entries:
            if e.is_dir():
                try:
                    n = sum(1 for x in e.rglob("*") if x.is_file() and not (set(x.parts) & SKIP_DIRS))
                except OSError:
                    n = -1
                lines.append(f"{'  ' * level}{e.name}/  ({n} arquivos)")
                if level + 1 < depth:
                    walk(e, level + 1)
    walk(root, 0)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--agent-dir")
    ap.add_argument("--other-fronts", choices=["none", "names", "full"], default="names")
    ap.add_argument("--projects", default="all", help="all | none | nomes separados por vírgula")
    ap.add_argument("--out-dir", default="studio/_snapshots")
    a = ap.parse_args()

    root = Path(a.root).resolve()
    ad = Path(a.agent_dir).resolve() if a.agent_dir else detect_agent_dir(root)
    if not ad:
        print("ERRO: pasta de agentes (.agents/.agent) não encontrada. Use --agent-dir.", file=sys.stderr)
        return 2
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    out = root / a.out_dir / f"studio_snapshot_{stamp}.zip"
    out.parent.mkdir(parents=True, exist_ok=True)

    others = []
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        pk = Packer(root, zf)
        for kind in ("skills", "workflows", "rules"):
            base = ad / kind
            if not base.is_dir():
                continue
            for item in sorted(base.iterdir()):
                is_kf = item.name.startswith(("kf-", "kf_")) or item.stem.startswith(("kf-", "kf_"))
                if is_kf or a.other_fronts == "full":
                    pk.add_tree(item)
                if not is_kf:
                    md = item / "SKILL.md" if item.is_dir() else item
                    desc = frontmatter_desc(md.read_text(encoding="utf-8", errors="replace")) if md.exists() else ""
                    others.append({"type": kind[:-1], "name": item.stem if item.is_file() else item.name,
                                   "path": item.relative_to(root).as_posix(), "description": desc})
        for f in ROOT_FILES:
            if (root / f).is_file():
                pk.add_file(root / f)
        kf = root / "knowledge_factory"
        for sub in ("implementation", "templates", "scripts", "docs", "archive"):
            pk.add_tree(kf / sub)
        projects = kf / "projects"
        if projects.is_dir() and a.projects != "none":
            wanted = None if a.projects == "all" else {x.strip() for x in a.projects.split(",")}
            for p in sorted(x for x in projects.iterdir() if x.is_dir()):
                if wanted is None or p.name in wanted:
                    pk.add_tree(p)
        if (root / "studio").is_dir():
            for sub in ("implementation", "kits", "review", "formats"):
                pk.add_tree(root / "studio" / sub)
        zf.writestr("_snapshot/other_fronts_index.json", json.dumps(others, ensure_ascii=False, indent=1))
        zf.writestr("_snapshot/workspace_tree.txt", tree_listing(root))
        summary = [
            "# Snapshot do workspace",
            f"Gerado em {datetime.datetime.now().isoformat(timespec='seconds')}",
            f"Pasta de agentes: {ad.relative_to(root).as_posix()}",
            f"Outras frentes: {a.other_fronts} ({len(others)} itens não-KF indexados)",
            f"Projetos KF: {a.projects}",
            f"Arquivos incluídos: {pk.files} · {pk.total // 1024} KB · segredos mascarados: {pk.redacted[0]}",
            "", "## Não incluídos", *[f"- {s}" for s in pk.skipped[:300]],
        ]
        zf.writestr("_snapshot/SNAPSHOT_SUMMARY.md", "\n".join(summary) + "\n")
    print(f"OK: {out}")
    print(f"{pk.files} arquivos, {pk.total // 1024} KB, {len(pk.skipped)} ignorados, {pk.redacted[0]} segredo(s) mascarado(s).")
    print("Anexe este .zip na conversa com o Claude.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
