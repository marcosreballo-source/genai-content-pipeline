"""studio_common.py: utilitários compartilhados pelos scripts do Studio (Material Factory, Source Library, Review)."""
import os
import re
import warnings
import shutil
import sys
from pathlib import Path

warnings.filterwarnings("ignore", message=".*ARC4.*")
STUDIO = Path(__file__).resolve().parent.parent          # .../studio
WORKSPACE = STUDIO.parent
UNIT_MAX_WORDS = 1200                                     # limite de saída por rodada do Gemini (folga sobre ~1500)

try:
    import yaml
except ImportError:                                       # pragma: no cover
    print("ERRO: PyYAML não instalado. Rode: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


class _Dumper(yaml.SafeDumper):
    pass


def _str_presenter(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_Dumper.add_representer(str, _str_presenter)


def load_yaml(path, default=None):
    p = Path(path)
    if not p.exists():
        if default is not None:
            return default
        raise FileNotFoundError(f"arquivo não encontrado: {p}")
    text = p.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise ValueError(f"YAML inválido em {p}: {e}") from e
    return data if data is not None else (default if default is not None else {})


def dump_yaml(obj, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(yaml.dump(obj, Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=110),
                          encoding="utf-8")


def frontmatter_and_yaml_blocks(text):
    """Retorna (front-matter dict, lista de blocos ```yaml``` parseados) de um artefato .md."""
    fm = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.S)
    if m:
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            fm = {}
    blocks = []
    for b in re.findall(r"```ya?ml\s*\n(.*?)```", text, re.S):
        try:
            blocks.append(yaml.safe_load(b))
        except yaml.YAMLError:
            blocks.append(None)
    return fm, blocks


def words(obj):
    """Conta palavras de qualquer estrutura (str/list/dict)."""
    if obj is None:
        return 0
    if isinstance(obj, str):
        return len(obj.split())
    if isinstance(obj, (int, float, bool)):
        return 1
    if isinstance(obj, dict):
        return sum(words(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return sum(words(v) for v in obj)
    return 0


def slug(text, n=40):
    import unicodedata
    t = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9]+", "-", t).strip("-").lower()
    return t[:n] or "item"


def find_exe(names, extra=()):
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    for e in extra:
        if Path(e).exists():
            return str(e)
    return None


SOFFICE_PATHS = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]


class Issues:
    """Coletor de erros/avisos com localização; imprime em português."""

    def __init__(self):
        self.items = []

    def add(self, level, where, msg, code=""):
        self.items.append({"level": level, "where": where, "msg": msg, "code": code})

    def err(self, where, msg, code=""):
        self.add("ERRO", where, msg, code)

    def warn(self, where, msg, code=""):
        self.add("AVISO", where, msg, code)

    @property
    def errors(self):
        return [i for i in self.items if i["level"] == "ERRO"]

    @property
    def warnings(self):
        return [i for i in self.items if i["level"] == "AVISO"]

    def print(self, title=""):
        if title:
            print(title)
        for i in self.items:
            print(f"  [{i['level']}] {i['where']}: {i['msg']}")
        print(f"Resumo: {len(self.errors)} erro(s), {len(self.warnings)} aviso(s).")

    def markdown(self):
        if not self.items:
            return "Nenhum problema encontrado.\n"
        rows = ["| Nível | Onde | Problema |", "|---|---|---|"]
        rows += [f"| {i['level']} | {i['where']} | {i['msg'].replace('|', '/')} |" for i in self.items]
        return "\n".join(rows) + "\n"

    def exit_code(self):
        return 1 if self.errors else 0


def rel(p, base=None):
    base = Path(base or os.getcwd()).resolve()
    try:
        return Path(p).resolve().relative_to(base).as_posix()
    except ValueError:
        return Path(p).as_posix()
