#!/usr/bin/env python3
r"""studio/tools/verify_agent_implementation.py: Suíte de testes independente para o usuário auditar
as modificações realizadas pelo agente nas regras, skills, ferramentas SOTA/QA e no deck final.

Como o usuário deve rodar no PowerShell:
  $env:PYTHONIOENCODING="utf-8"
  .\.venv\Scripts\python.exe studio\tools\verify_agent_implementation.py
  .\.venv\Scripts\python.exe studio\tools\verify_agent_implementation.py --check-aula02
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageDraw
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[2]
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
TOOLS_DIR = ROOT / "studio" / "tools"
EXPECTED_TEMPLATE_SHA256 = "79F2B3E3F372974740DBB13A7066CCB82F7224DFEB2A85987FDA283F0EB07DBE"

REQUIRED_26_LIBS = [
    "D3", "plotly.js", "Vega", "Vega-Lite", "nivo", "Victory", "Chart.js", "vis.js",
    "Highcharts", "Google Charts", "Leaflet", "ECharts", "Mermaid", "Bokeh", "Dash",
    "plotly.py", "Altair", "mpld3", "Matplotlib", "Seaborn", "NetworkX", "Pillow",
    "Chaco", "ggplot2", "Graphviz", "TikZ",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class TestAgentImplementation(unittest.TestCase):
    """Auditoria independente das regras, skills, scripts e testes de mutação."""

    def test_01_protected_files_untouched(self):
        """Verifica se TEMPLATE_SLIDES.pptx e studio/scripts/tests/run_tests.py permanecem íntegros."""
        tpl = ROOT / "AULAS_SEMANA_1" / "TEMPLATE_SLIDES.pptx"
        self.assertTrue(tpl.exists(), "TEMPLATE_SLIDES.pptx não encontrado!")
        self.assertEqual(
            sha256_file(tpl).upper(),
            EXPECTED_TEMPLATE_SHA256,
            "VIOLAÇÃO CRÍTICA (Regra 9): TEMPLATE_SLIDES.pptx foi modificado!",
        )
        res = subprocess.run(
            [str(VENV_PY), str(ROOT / "studio" / "scripts" / "tests" / "run_tests.py")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Testes originais do Studio falharam:\n{res.stdout}\n{res.stderr}")

    def test_02_rules_and_skills_updated(self):
        """Verifica se todas as regras e skills receberam os trechos obrigatórios."""
        checks = [
            (ROOT / ".agents" / "rules" / "studio-core.md", ["visual_qa_gates.py", "visual_sota_auditor.py", "visual_env_provisioner.py", "--verify-audit"]),
            (ROOT / ".agents" / "rules" / "academic-os-rules.md", ["P12", "visual_qa_gates.py", "visual_sota_auditor.py", "60 Dias"]),
            (ROOT / ".agents" / "skills" / "mf-visual-qa" / "SKILL.md", ["visual_qa_gates.py", "qa_challenge_sheet.png", "--verify-audit", "--canary"]),
            (ROOT / "studio" / "review" / "lenses" / "visual.yaml", ["VIS-7", "VIS-8", "blocker"]),
            (ROOT / ".agents" / "skills" / "format-reviewer" / "SKILL.md", ["visual_qa_gates.py", "--verify-audit", "P12"]),
            (ROOT / ".agents" / "skills" / "diagram-reviewer" / "SKILL.md", ["visual_sota_auditor.py", "P12"]),
        ]
        for path, tokens in checks:
            self.assertTrue(path.exists(), f"Arquivo ausente: {path}")
            content = path.read_text(encoding="utf-8")
            for tok in tokens:
                self.assertIn(tok, content, f"Token obrigatório '{tok}' ausente em {path.relative_to(ROOT)}")

    def test_03_sota_60_day_lifecycle_and_26_libraries(self):
        """Testa se as 26 bibliotecas existem e se o bloqueio de >= 60 dias corridos funciona."""
        auditor = TOOLS_DIR / "visual_sota_auditor.py"
        self.assertTrue(auditor.exists(), "visual_sota_auditor.py não existe!")

        with tempfile.TemporaryDirectory() as tmp:
            reg_file = Path(tmp) / "test_reg.yaml"
            res_all = subprocess.run(
                [str(VENV_PY), str(auditor), "--registry", str(reg_file), "check-all"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(res_all.returncode, 0, f"check-all falhou:\n{res_all.stderr}")
            reg_txt = reg_file.read_text(encoding="utf-8")
            for lib in REQUIRED_26_LIBS:
                self.assertIn(lib, reg_txt, f"Biblioteca '{lib}' ausente do catálogo SOTA!")

            expired_date = str(dt.date.today() - dt.timedelta(days=65))
            subprocess.run(
                [str(VENV_PY), str(auditor), "--registry", str(reg_file), "update", "--library", "D3", "--version", "7.9.0", "--date", expired_date],
                check=True,
                capture_output=True,
            )
            res_exp = subprocess.run(
                [str(VENV_PY), str(auditor), "--registry", str(reg_file), "check", "--library", "D3"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(res_exp.returncode, 2, "FALHA: visual_sota_auditor.py NÃO bloqueou biblioteca com 65 dias (> 60d)!")

            subprocess.run(
                [str(VENV_PY), str(auditor), "--registry", str(reg_file), "update", "--library", "D3", "--version", "7.9.0"],
                check=True,
                capture_output=True,
            )
            res_ok = subprocess.run(
                [str(VENV_PY), str(auditor), "--registry", str(reg_file), "check", "--library", "D3"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(res_ok.returncode, 0, "FALHA: visual_sota_auditor.py rejeitou biblioteca recém-atualizada!")

    def test_04_provisioner_and_headless_html_render(self):
        """Testa o provisionador de pacotes e a renderização HTML -> PNG via browser headless."""
        prov = TOOLS_DIR / "visual_env_provisioner.py"
        self.assertTrue(prov.exists(), "visual_env_provisioner.py não existe!")
        res = subprocess.run([str(VENV_PY), str(prov), "--ensure", "Matplotlib"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Falha ao validar Matplotlib:\n{res.stderr}")

        with tempfile.TemporaryDirectory() as tmp:
            html = Path(tmp) / "test.html"
            png = Path(tmp) / "out.png"
            html.write_text(
                "<html><body style='background:#F4F4F4;font-family:sans-serif;padding:40px'>"
                "<h1 style='color:#0F62FE;font-size:48px'>Teste SOTA Headless Render</h1></body></html>",
                encoding="utf-8",
            )
            r_render = subprocess.run(
                [str(VENV_PY), str(prov), "--render-html", str(html), str(png), "--width", "800", "--height", "600"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r_render.returncode, 0, f"Renderização HTML->PNG falhou:\n{r_render.stderr}")
            self.assertTrue(png.exists() and png.stat().st_size > 1000, "PNG gerado pelo browser headless está vazio!")

    def test_05_mutation_injection_on_visual_qa_gates(self):
        """Teste de Mutação: injeta defeitos visuais sintéticos e prova que visual_qa_gates.py REJEITA todos."""
        gates = TOOLS_DIR / "visual_qa_gates.py"
        self.assertTrue(gates.exists(), "visual_qa_gates.py não existe!")
        sys.path.insert(0, str(TOOLS_DIR))
        import visual_qa_gates as vqg

        with tempfile.TemporaryDirectory() as tmp:
            build = Path(tmp) / "build"
            png_dir = build / "png"
            png_dir.mkdir(parents=True)
            pptx_path = build / "deck.pptx"
            pdf_path = build / "deck.pdf"

            prs = Presentation()
            prs.slide_width = 26 * 914400
            prs.slide_height = 15 * 914400
            prs.slides.add_slide(prs.slide_layouts[6])
            prs.save(str(pptx_path))

            # --- MUTAÇÃO A: Slide com Deserto à Direita + Bloco Cinza + Micro-fonte ---
            doc = fitz.open()
            page = doc.new_page(width=1920, height=1080)
            page.insert_text((80, 120), "Título do Slide de Teste", fontsize=48, color=(0.1, 0.1, 0.1))
            page.insert_text((80, 300), "Texto microscópico ilegível na zona de corpo", fontsize=11, color=(0.1, 0.1, 0.1))
            doc.save(str(pdf_path))
            doc.close()

            im_bad = Image.new("RGB", (1920, 1080), (244, 244, 244))
            dr = ImageDraw.Draw(im_bad)
            dr.rectangle([100, 200, 700, 800], fill=(20, 20, 20))
            dr.rectangle([1050, 130, 1800, 900], fill=(224, 224, 224))
            im_bad.save(png_dir / "slide_01.png")

            res_bad = subprocess.run([str(VENV_PY), str(gates), str(Path(tmp))], capture_output=True, text=True)
            self.assertNotEqual(res_bad.returncode, 0, "FALHA GRAVE: visual_qa_gates.py APROVOU um slide com bloco cinza e micro-fonte!")
            self.assertIn("MICRO_FONT", res_bad.stdout)
            self.assertIn("DEAD_GRAY_BOX_DETECTED", res_bad.stdout)

            # --- MUTAÇÃO B: Slide Perfeito + Teste de Canário Falso vs Canário Real ---
            doc2 = fitz.open()
            page2 = doc2.new_page(width=1920, height=1080)
            page2.insert_text((80, 120), "Título Adequado e Proporcional", fontsize=54, color=(0.08, 0.08, 0.08))
            page2.insert_text((80, 320), "Corpo de texto com fonte legível e sem colisão", fontsize=28, color=(0.1, 0.1, 0.1))
            doc2.save(str(pdf_path))
            doc2.close()

            im_good = Image.new("RGB", (1920, 1080), (244, 244, 244))
            dr2 = ImageDraw.Draw(im_good)
            for rx in (150, 550, 1100, 1500):
                for ry in (220, 420, 620, 820):
                    dr2.rectangle([rx, ry, rx + 220, ry + 90], fill=(15, 98, 254), outline=(20, 20, 20), width=3)
            im_good.save(png_dir / "slide_01.png")

            res_good = subprocess.run([str(VENV_PY), str(gates), str(Path(tmp))], capture_output=True, text=True)
            self.assertEqual(res_good.returncode, 0, f"visual_qa_gates.py reprovou slide equilibrado:\n{res_good.stdout}")

            res_fake_canary = subprocess.run(
                [str(VENV_PY), str(gates), str(Path(tmp)), "--verify-audit", "--canary", "000000"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(res_fake_canary.returncode, 3, "FALHA ANTI-TEATRO: --verify-audit aceitou canário falso!")

            real_canary = vqg.compute_canary(build, sha256_file(pdf_path))
            rep_md = build / "visual_audit_report.md"
            rep_md.write_text(
                rep_md.read_text(encoding="utf-8").replace("A_PREENCHER_APOS_LER_QA_CHALLENGE_SHEET_PNG", real_canary),
                encoding="utf-8",
            )
            res_true_canary = subprocess.run(
                [str(VENV_PY), str(gates), str(Path(tmp)), "--verify-audit", "--canary", real_canary],
                capture_output=True,
                text=True,
            )
            self.assertEqual(res_true_canary.returncode, 0, f"Falha ao validar canário verdadeiro:\n{res_true_canary.stderr}")

    def test_06_no_kahoot(self):
        """Nenhum vestígio de Kahoot em specs, outline, brief, notebook, roteiro, assets ou deck."""
        sys.path.insert(0, str(TOOLS_DIR))
        import verify_aula02_v2 as v2
        t = v2.TestAula02V2()
        t.slides = v2.load_slides()
        t.test_06_no_kahoot()
        t.test_06b_forms_urls_intact()

    def test_07_mode_markers(self):
        """Todo slide de código tem modo=colab e uma célula existente; toda célula do notebook é usada por um slide."""
        sys.path.insert(0, str(TOOLS_DIR))
        import verify_aula02_v2 as v2
        t = v2.TestAula02V2()
        t.slides = v2.load_slides()
        t.test_07_mode_markers()

    def test_08_flow(self):
        """Gancho em todo slide de conteúdo, 3 'pause e preveja' e síntese ao fim de cada bloco."""
        sys.path.insert(0, str(TOOLS_DIR))
        import verify_aula02_v2 as v2
        t = v2.TestAula02V2()
        t.slides = v2.load_slides()
        t.test_08_flow()

    def test_09_sections(self):
        """4 divisores 'Bloco N de 4' em ordem; contagens de spec, outline e deck coerentes; roteiro com notas."""
        sys.path.insert(0, str(TOOLS_DIR))
        import verify_aula02_v2 as v2
        t = v2.TestAula02V2()
        t.slides = v2.load_slides()
        t.test_09_sections()



def check_aula02() -> int:
    job = ROOT / "studio" / "jobs" / "2026-11-05_qff-aula02-circuitos"
    gates = TOOLS_DIR / "visual_qa_gates.py"
    print("\n=== AUDITANDO DECK FINAL DA AULA 02 ===")
    r1 = subprocess.run([str(VENV_PY), str(gates), str(job)])
    if r1.returncode != 0:
        return r1.returncode
    r2 = subprocess.run([str(VENV_PY), str(gates), str(job), "--verify-audit"])
    return r2.returncode


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-aula02", action="store_true", help="Audita também o deck final da Aula 02")
    args, remaining = ap.parse_known_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestAgentImplementation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
    if args.check_aula02:
        sys.exit(check_aula02())
    sys.exit(0)
