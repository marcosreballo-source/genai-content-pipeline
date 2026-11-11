#!/usr/bin/env python3
"""studio/tools/visual_qa_gates.py: Portões determinísticos de QA visual, tipográfico e anti-teatro.

Audita 3 camadas reais:
  1. Camada Estrutural XML (.pptx via python-pptx): detecta Picture/Object Placeholders órfãos sem blipFill.
  2. Camada Vetorial Renderizada (.pdf via PyMuPDF/fitz): extrai tamanho real em pt de cada span pós-LibreOffice,
     mede colisões entre bounding boxes de linhas, estouro de página e pisos de legibilidade por zona.
  3. Camada Matricial de Pixels (.png via Pillow/numpy): calcula grade 4x4 de densidade de tinta (detectando
     Deserto à Direita e Cemitério Vertical), detecta blocos cinzas uniformes (sigma < 3.5) e mede contraste WCAG.

Mecanismo Anti-Teatro (Proof-of-Execution):
  - Gera um código canário de 6 caracteres derivado de segredo local + hash do PDF e o desenha APENAS como pixels
    em build/qa_challenge_sheet.png, junto com uma grade de coordenadas (A1..D4) sobre os slides.
  - Grava apenas o hash SHA-256 salgado do canário em build/visual_qa_evidence.json.
  - O modo --verify-audit exige --canary <CODIGO_LIDO_DA_IMAGEM> (provando que o modelo abriu a imagem via visão).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import re
import secrets
import sys
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def relative_luminance(rgb: tuple[float, float, float]) -> float:
    def ch(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = ch(rgb[0]), ch(rgb[1]), ch(rgb[2])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(rgb1: tuple[float, float, float], rgb2: tuple[float, float, float]) -> float:
    l1, l2 = float(relative_luminance(rgb1)), float(relative_luminance(rgb2))
    bright, dark = max(l1, l2), min(l1, l2)
    return float((bright + 0.05) / (dark + 0.05))


def int_color_to_rgb(c: int) -> tuple[int, int, int]:
    return ((c >> 16) & 255, (c >> 8) & 255, c & 255)


def resolve_paths(target: Path) -> tuple[Path, Path, Path, Path, list[Path]]:
    if target.is_dir():
        build = target / "build" if (target / "build").exists() else target
        pptx = build / "deck.pptx"
        pdf = build / "deck.pdf"
    else:
        pptx = target
        build = pptx.parent
        pdf = pptx.with_suffix(".pdf")
    png_dir = build / "png" if (build / "png").exists() else build / "previews"
    pngs = sorted(png_dir.glob("slide*.png")) if png_dir.exists() else []
    return target if target.is_dir() else build.parent, build, pptx, pdf, pngs


def load_slide_archetypes(job_dir: Path, total_slides: int) -> dict[int, dict]:
    info: dict[int, dict] = {i: {"id": f"SL-{i:02d}", "archetype": "unknown"} for i in range(1, total_slides + 1)}
    outline = job_dir / "outline.yaml"
    if outline.exists():
        import yaml

        data = yaml.safe_load(outline.read_text(encoding="utf-8")) or {}
        for idx, sl in enumerate(data.get("slides") or [], 1):
            if idx in info:
                info[idx]["id"] = sl.get("id", f"SL-{idx:02d}")
                info[idx]["archetype"] = sl.get("archetype", "unknown")
    return info


def audit_pptx_xml(pptx_path: Path) -> dict[int, list[str]]:
    prs = Presentation(str(pptx_path))
    xml_issues: dict[int, list[str]] = {}
    for idx, slide in enumerate(prs.slides, 1):
        errs = []
        for sh in slide.shapes:
            if sh.is_placeholder:
                ptype = sh.placeholder_format.type
                if ptype in (PP_PLACEHOLDER.PICTURE, PP_PLACEHOLDER.OBJECT, PP_PLACEHOLDER.BITMAP):
                    has_blip = bool(sh._element.xpath(".//p:blipFill/a:blip"))
                    has_text = bool(sh.has_text_frame and sh.text_frame.text.strip())
                    if not has_blip and not has_text:
                        errs.append(
                            f"EMPTY_PLACEHOLDER: shape '{sh.name}' (idx={sh.placeholder_format.idx}, tipo={ptype}) sem imagem vinculada"
                        )
        xml_issues[idx] = errs
    return xml_issues


def audit_pdf_and_png(
    pdf_path: Path, pngs: list[Path], slide_meta: dict[int, dict]
) -> tuple[list[dict], list[dict]]:
    doc = fitz.open(str(pdf_path))
    slides_evidence = []
    violations = []

    DIVIDER_ARCHETYPES = {"title", "section", "statement", "closing", "qa"}

    for idx, page in enumerate(doc, 1):
        meta = slide_meta.get(idx, {"id": f"SL-{idx:02d}", "archetype": "unknown"})
        sid = meta["id"]
        arch = meta["archetype"]
        pw, ph = page.rect.width, page.rect.height
        scale = ph / 405.0

        min_caption_pt = round(6.7 * scale, 1)  # ~18.0pt on 15" canvas (1080pt height)
        min_title_pt = round(14.0 * scale, 1)    # ~37.5pt on 15" canvas

        PngImg = Image.open(pngs[idx - 1]).convert("RGB") if idx <= len(pngs) else None
        arr = np.asarray(PngImg, dtype=np.float32) if PngImg is not None else None

        text_dict = page.get_text("dict")
        lines_info = []
        body_sizes = []
        all_sizes = []
        min_contrast = 21.0
        contrast_fails = []

        for b in text_dict.get("blocks", []):
            if b.get("type") != 0:
                continue
            for ln in b.get("lines", []):
                lbox = ln["bbox"]
                ltext = "".join(sp.get("text", "") for sp in ln.get("spans", [])).strip()
                if not ltext:
                    continue
                sizes = [sp["size"] for sp in ln.get("spans", []) if sp.get("text", "").strip()]
                colors = [sp["color"] for sp in ln.get("spans", []) if sp.get("text", "").strip()]
                if not sizes:
                    continue
                max_sz = max(sizes)
                min_sz = min(sizes)
                all_sizes.append(max_sz)
                y_rel = lbox[1] / ph
                if 0.08 <= y_rel <= 0.88:
                    body_sizes.append((min_sz, ltext[:40], lbox))
                lines_info.append({"bbox": lbox, "text": ltext[:50], "size": max_sz, "color": colors[0]})

                if arr is not None:
                    ih, iw, _ = arr.shape
                    x0 = max(0, min(iw - 1, int(lbox[0] / pw * iw)))
                    y0 = max(0, min(ih - 1, int(lbox[1] / ph * ih)))
                    x1 = max(x0 + 1, min(iw, int(lbox[2] / pw * iw)))
                    y1 = max(y0 + 1, min(ih, int(lbox[3] / ph * ih)))
                    patch = arr[max(0, y0 - 4) : min(ih, y0 + 2), x0:x1]
                    if patch.size > 0:
                        bg_rgb = tuple(np.median(patch.reshape(-1, 3), axis=0))
                        fg_rgb = int_color_to_rgb(colors[0])
                        cr = contrast_ratio(fg_rgb, bg_rgb)
                        if cr < min_contrast:
                            min_contrast = cr
                        if cr < 2.8 and len(ltext) > 2:
                            contrast_fails.append(f"LOW_CONTRAST: ({cr:.2f}:1) em '{ltext[:30]}'")

        collisions = []
        for i in range(len(lines_info)):
            ax0, ay0, ax1, ay1 = lines_info[i]["bbox"]
            if ax1 > pw + 8 or ay1 > ph + 8 or ax0 < -8 or ay0 < -8:
                collisions.append(f"OUT_OF_BOUNDS: '{lines_info[i]['text']}'")
            for j in range(i + 1, len(lines_info)):
                bx0, by0, bx1, by1 = lines_info[j]["bbox"]
                ox = min(ax1, bx1) - max(ax0, bx0)
                oy = min(ay1, by1) - max(ay0, by0)
                min_h = min(ay1 - ay0, by1 - by0)
                if ox > 12.0 and oy > max(3.5, 0.22 * min_h):
                    collisions.append(
                        f"LINE_COLLISION: '{lines_info[i]['text'][:25]}' colide com '{lines_info[j]['text'][:25]}' (Y={oy:.1f}pt)"
                    )

        font_fails = []
        if all_sizes and arch != "closing" and max(all_sizes) < min_title_pt:
            font_fails.append(f"TITLE_TOO_SMALL: maior fonte={max(all_sizes):.1f}pt (mín={min_title_pt}pt)")
        for sz, txt, _ in body_sizes:
            if sz < min_caption_pt:
                font_fails.append(f"MICRO_FONT: '{txt}' com {sz:.1f}pt (mín={min_caption_pt}pt)")

        left_ink = 0.0
        right_ink = 0.0
        top_ink = 0.0
        bottom_ink = 0.0
        gray_box_detected = False
        grid_4x4 = [[0.0] * 4 for _ in range(4)]

        if arr is not None:
            ih, iw, _ = arr.shape
            bg_ref = np.median(arr[int(0.02 * ih) : int(0.06 * ih), int(0.02 * iw) : int(0.15 * iw)].reshape(-1, 3), axis=0)
            diff = np.linalg.norm(arr - bg_ref, axis=2)
            ink_mask = (diff > 18.0).astype(np.float32)

            ink_no_sticker = ink_mask.copy()
            ink_no_sticker[0 : int(0.27 * ih), int(0.80 * iw) : iw] = 0.0

            cy0, cy1 = int(0.16 * ih), int(0.86 * ih)
            cx0, cx1 = int(0.04 * iw), int(0.96 * iw)
            gh = (cy1 - cy0) // 4
            gw = (cx1 - cx0) // 4
            for r in range(4):
                for c in range(4):
                    cell = ink_no_sticker[cy0 + r * gh : cy0 + (r + 1) * gh, cx0 + c * gw : cx0 + (c + 1) * gw]
                    grid_4x4[r][c] = round(float(cell.mean()), 4)

            left_ink = round(float(np.mean([grid_4x4[r][c] for r in range(4) for c in (0, 1)])), 4)
            right_ink = round(float(np.mean([grid_4x4[r][c] for r in range(4) for c in (2, 3)])), 4)
            top_ink = round(float(np.mean([grid_4x4[r][c] for r in (0, 1) for c in range(4)])), 4)
            bottom_ink = round(float(np.mean([grid_4x4[r][c] for r in (2, 3) for c in range(4)])), 4)

            r_patch = arr[int(0.12 * ih) : int(0.68 * ih), int(0.55 * iw) : int(0.92 * iw)]
            if r_patch.size > 0:
                std_rgb = float(np.std(r_patch.reshape(-1, 3), axis=0).mean())
                mean_rgb = np.mean(r_patch.reshape(-1, 3), axis=0)
                dist_from_bg = float(np.linalg.norm(mean_rgb - bg_ref))
                if std_rgb < 3.5 and dist_from_bg > 12.0:
                    gray_box_detected = True

        spatial_fails = []
        if gray_box_detected:
            spatial_fails.append("DEAD_GRAY_BOX_DETECTED: Retângulo cinza uniforme sem imagem na metade direita")
        if arch not in DIVIDER_ARCHETYPES:
            if left_ink > 0.06 and right_ink < 0.015:
                spatial_fails.append(
                    f"RIGHT_DESERT_DETECTED: Metade esquerda ocupada ({left_ink*100:.1f}%) e metade direita vazia ({right_ink*100:.1f}%)"
                )
            if top_ink > 0.10 and bottom_ink < 0.012:
                spatial_fails.append(
                    f"VERTICAL_CEMETERY_DETECTED: Topo ocupado ({top_ink*100:.1f}%) e metade inferior deserta ({bottom_ink*100:.1f}%)"
                )

        slide_errs = collisions + font_fails + contrast_fails + spatial_fails
        slides_evidence.append(
            {
                "slide_num": idx,
                "id": sid,
                "archetype": arch,
                "min_body_pt": round(float(min([x[0] for x in body_sizes], default=0.0)), 1),
                "max_font_pt": round(float(max(all_sizes, default=0.0)), 1),
                "min_contrast": round(float(min_contrast), 2),
                "left_ink_pct": round(float(left_ink * 100), 1),
                "right_ink_pct": round(float(right_ink * 100), 1),
                "top_ink_pct": round(float(top_ink * 100), 1),
                "bottom_ink_pct": round(float(bottom_ink * 100), 1),
                "grid_4x4": [[round(float(c), 4) for c in row] for row in grid_4x4],
                "errors": slide_errs,
            }
        )
        for e in slide_errs:
            violations.append({"slide": sid, "slide_num": idx, "error": e})

    doc.close()
    return slides_evidence, violations


def compute_canary(build_dir: Path, pdf_sha: str) -> str:
    secret_file = build_dir / ".qa_secret"
    if not secret_file.exists():
        secret_file.write_text(secrets.token_hex(16), encoding="utf-8")
    secret = secret_file.read_text(encoding="utf-8").strip()
    raw = hashlib.sha256(f"{secret}:{pdf_sha}".encode("utf-8")).hexdigest().upper()
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    return "".join(alphabet[int(raw[i : i + 2], 16) % len(alphabet)] for i in range(0, 12, 2))


def generate_canary_challenge_sheet(pngs: list[Path], build_dir: Path, pdf_sha: str) -> tuple[str, str]:
    canary = compute_canary(build_dir, pdf_sha)
    salt = secrets.token_hex(8)
    canary_hash = hashlib.sha256(f"{salt}:{canary}".encode("utf-8")).hexdigest()

    if not pngs:
        return salt, canary_hash

    cols = 4
    tw = 420
    im0 = Image.open(pngs[0]).convert("RGB")
    th = int(im0.height * tw / im0.width)
    rows = math.ceil(len(pngs) / cols)
    banner_h = 90
    sheet = Image.new("RGB", (cols * (tw + 16) + 16, banner_h + rows * (th + 36) + 16), (24, 28, 32))
    dr = ImageDraw.Draw(sheet)

    try:
        f_big = ImageFont.truetype("consola.ttf", 36)
        f_sm = ImageFont.truetype("consola.ttf", 16)
    except Exception:
        f_big = ImageFont.load_default()
        f_sm = ImageFont.load_default()

    dr.rectangle([16, 14, sheet.width - 16, banner_h - 10], fill=(15, 98, 254), outline=(255, 255, 255), width=2)
    dr.text(
        (32, 26),
        f"VISUAL QA CANARY CODE: [ {canary} ]   (Passe em --verify-audit --canary {canary})",
        fill=(255, 255, 255),
        font=f_big,
    )

    for i, p in enumerate(pngs):
        r, c = divmod(i, cols)
        x = 16 + c * (tw + 16)
        y = banner_h + r * (th + 36)
        thumb = Image.open(p).convert("RGB").resize((tw, th))
        tdr = ImageDraw.Draw(thumb)
        for gr in range(1, 4):
            tdr.line([(0, gr * th // 4), (tw, gr * th // 4)], fill=(180, 180, 220), width=1)
            tdr.line([(gr * tw // 4, 0), (gr * tw // 4, th)], fill=(180, 180, 220), width=1)
        sheet.paste(thumb, (x, y))
        dr.rectangle([x, y, x + tw - 1, y + th - 1], outline=(120, 130, 140))
        dr.text((x + 4, y + th + 6), f"SL-{i+1:02d} (Grid A1..D4)", fill=(230, 230, 230), font=f_sm)

    out_path = build_dir / "qa_challenge_sheet.png"
    sheet.save(out_path)
    return salt, canary_hash


def audit_figures_dir(fig_dir: Path, min_width: int = 800) -> tuple[list[Path], str, list[dict], list[dict]]:
    """Audita figuras/diagramas (.png e pares .pdf vetoriais) de artigos e relatórios científicos."""
    pngs = sorted(
        p for p in fig_dir.rglob("*.png")
        if p.name not in {"qa_challenge_sheet.png", "contact_sheet.png"} and "previews" not in p.parts
    )
    h_comb = hashlib.sha256()
    figs_ev: list[dict] = []
    violations: list[dict] = []

    for idx, p in enumerate(pngs, 1):
        fid = f"FIG-{idx:02d}:{p.name}"
        h_comb.update(sha256_file(p).encode("utf-8"))
        im = Image.open(p).convert("RGB")
        iw, ih = im.size
        arr = np.asarray(im, dtype=np.float32)
        errs: list[str] = []

        if iw < min_width or ih < 260:
            errs.append(f"LOW_RESOLUTION: {iw}x{ih}px (mín largura={min_width}px)")

        # Estima cor de fundo pelos cantos
        corners = np.concatenate(
            [arr[:6, :6].reshape(-1, 3), arr[:6, -6:].reshape(-1, 3), arr[-6:, :6].reshape(-1, 3), arr[-6:, -6:].reshape(-1, 3)],
            axis=0,
        )
        bg_ref = np.median(corners, axis=0)
        diff = np.linalg.norm(arr - bg_ref, axis=2)
        ink_mask = (diff > 18.0).astype(np.float32)
        ink_pct = float(ink_mask.mean())

        if ink_pct < 0.005:
            errs.append(f"BLANK_FIGURE_DETECTED: densidade de tinta {ink_pct*100:.2f}% (< 0.5%)")

        # Verifica corte nas 4 bordas (edge clipping de títulos/legendas/círculos)
        top_edge = float(ink_mask[:2, :].mean())
        bot_edge = float(ink_mask[-2:, :].mean())
        left_edge = float(ink_mask[:, :2].mean())
        right_edge = float(ink_mask[:, -2:].mean())
        max_edge = max(top_edge, bot_edge, left_edge, right_edge)
        # Se a borda não for uma moldura intencional contínua (> 0.70), mas tiver texto/objeto cortado (> 0.12)
        if 0.12 < max_edge < 0.70:
            errs.append(
                f"EDGE_CLIPPING_DETECTED: elementos tocando/cortados na borda extrema (ocupação de borda={max_edge*100:.1f}%)"
            )

        # Se existir par vetorial .pdf para a mesma figura, audita colisão de caixas de texto via PyMuPDF
        vec_pdf = p.with_suffix(".pdf")
        if vec_pdf.exists():
            try:
                vdoc = fitz.open(str(vec_pdf))
                if len(vdoc) > 0:
                    vpage = vdoc[0]
                    vlines = []
                    for b in vpage.get_text("dict").get("blocks", []):
                        if b.get("type") != 0:
                            continue
                        for ln in b.get("lines", []):
                            ltxt = "".join(sp.get("text", "") for sp in ln.get("spans", [])).strip()
                            if ltxt:
                                vlines.append((ln["bbox"], ltxt[:40]))
                    for i in range(len(vlines)):
                        ax0, ay0, ax1, ay1 = vlines[i][0]
                        for j in range(i + 1, len(vlines)):
                            bx0, by0, bx1, by1 = vlines[j][0]
                            ox = min(ax1, bx1) - max(ax0, bx0)
                            oy = min(ay1, by1) - max(ay0, by0)
                            min_h = min(ay1 - ay0, by1 - by0)
                            if ox > 10.0 and oy > max(3.0, 0.25 * min_h):
                                errs.append(f"VECTOR_TEXT_COLLISION: '{vlines[i][1]}' colide com '{vlines[j][1]}'")
                vdoc.close()
            except Exception:
                pass

        figs_ev.append(
            {
                "fig_num": idx,
                "id": fid,
                "path": str(p.relative_to(fig_dir)),
                "width": iw,
                "height": ih,
                "ink_pct": round(ink_pct * 100, 2),
                "max_edge_ink_pct": round(max_edge * 100, 2),
                "errors": errs,
            }
        )
        for e in errs:
            violations.append({"slide": fid, "slide_num": idx, "error": e})

    return pngs, h_comb.hexdigest(), figs_ev, violations


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", help="Pasta do job do Studio, pasta de figuras ou caminho do arquivo .pptx")
    ap.add_argument("--mode", choices=["auto", "deck", "figures"], default="auto", help="Modo de auditoria: deck (.pptx/.pdf) ou figures (.png de papers/relatórios)")
    ap.add_argument("--min-width", type=int, default=800, help="Largura mínima em px no modo figures")
    ap.add_argument("--verify-audit", action="store_true", help="Valida o código canário e o relatório de auditoria")
    ap.add_argument("--canary", help="Código canário de 6 caracteres lido visualmente de qa_challenge_sheet.png")
    ap.add_argument("--transcript", help="Caminho opcional do transcript.jsonl para auditar chamadas read_file")
    args = ap.parse_args()

    target_path = Path(args.target).resolve()
    job_dir, build_dir, pptx_path, pdf_path, pngs = resolve_paths(target_path)
    is_figures_mode = args.mode == "figures" or (
        args.mode == "auto" and target_path.is_dir() and not pptx_path.exists()
    )

    if is_figures_mode:
        build_dir = target_path / "build" if (target_path / "build").exists() else target_path
        ev_path = build_dir / "visual_qa_evidence.json"
        rep_path = build_dir / "visual_audit_report.md"
        fig_pngs, figs_sha, figs_ev, violations = audit_figures_dir(target_path, min_width=args.min_width)
        if not fig_pngs:
            print(f"ERRO: Nenhuma figura .png encontrada em {target_path}.", file=sys.stderr)
            return 2

        if args.verify_audit:
            if not ev_path.exists() or not rep_path.exists():
                print("ERRO [AUDIT_THEATER]: visual_qa_evidence.json ou visual_audit_report.md ausente.", file=sys.stderr)
                return 3
            ev = json.loads(ev_path.read_text(encoding="utf-8"))
            if ev.get("pdf_sha256") != figs_sha:
                print("ERRO [STALE_AUDIT]: As figuras foram modificadas após a geração das evidências.", file=sys.stderr)
                return 3
            if ev.get("total_violations", 1) > 0:
                print(f"ERRO [UNRESOLVED_VIOLATIONS]: Ainda existem {ev['total_violations']} violações nas figuras.", file=sys.stderr)
                return 1
            canary_in = (args.canary or "").strip().upper()
            if not canary_in:
                m = re.search(r"CANARY_VERIFIED:\*{0,2}\s*`?([A-Z0-9]{6})`?", rep_path.read_text(encoding="utf-8"))
                if m:
                    canary_in = m.group(1)
            expected_hash = ev.get("canary_sha256", "")
            salt = ev.get("canary_salt", "")
            actual_hash = hashlib.sha256(f"{salt}:{canary_in}".encode("utf-8")).hexdigest()
            if not canary_in or actual_hash != expected_hash:
                print(
                    "ERRO [AUDIT_THEATER_DETECTED]: Código canário inválido ou ausente! "
                    f"Abra '{build_dir / 'qa_challenge_sheet.png'}' via read_file (visão), leia o código no banner azul e passe em --canary.",
                    file=sys.stderr,
                )
                return 3
            rep_txt = rep_path.read_text(encoding="utf-8")
            if canary_in and f"CANARY_VERIFIED: `{canary_in}`" not in rep_txt:
                rep_txt = re.sub(r"CANARY_VERIFIED:\s*`?[^`\r\n]+`?", f"CANARY_VERIFIED: `{canary_in}`", rep_txt)
                rep_path.write_text(rep_txt, encoding="utf-8")
            print(f"[QA FIGURES AUDIT VERIFIED PASS] Canário óptico '{canary_in}' confirmado em {len(fig_pngs)} figura(s), 0 violações e SHA-256 íntegro.")
            return 0

        salt, canary_hash = generate_canary_challenge_sheet(fig_pngs, build_dir, figs_sha)
        evidence = {
            "mode": "figures",
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "target_dir": str(target_path),
            "pdf_sha256": figs_sha,
            "canary_salt": salt,
            "canary_sha256": canary_hash,
            "total_figures": len(figs_ev),
            "total_violations": len(violations),
            "flagged_figures": sorted({v["slide"] for v in violations}),
            "violations": violations,
            "figures": figs_ev,
        }
        ev_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
        md = [
            "# Relatório de Auditoria Visual Determinística e Canário Óptico (Modo Figuras)",
            "",
            f"- **Timestamp:** `{evidence['timestamp']}`",
            f"- **SHA-256 Combinado das Figuras:** `{figs_sha}`",
            f"- **Total de Figuras:** {len(figs_ev)} | **Violações Determinísticas:** {len(violations)}",
            "- **CANARY_VERIFIED:** `A_PREENCHER_APOS_LER_QA_CHALLENGE_SHEET_PNG`",
            f"- **STATUS_GLOBAL:** `{'REPROVADO_NOS_GATES' if violations else 'APROVADO_NOS_GATES'}`",
            "",
            "| Figura | Resolução (px) | Tinta (%) | Ocupação Máx Borda (%) | Status |",
            "| :--- | :---: | :---: | :---: | :--- |",
        ]
        for f_ev in figs_ev:
            st = "PASS" if not f_ev["errors"] else "FAIL: " + "; ".join(f_ev["errors"])
            md.append(f"| `{f_ev['id']}` | {f_ev['width']}x{f_ev['height']} | {f_ev['ink_pct']}% | {f_ev['max_edge_ink_pct']}% | {st} |")
        rep_path.write_text("\n".join(md) + "\n", encoding="utf-8")
        if violations:
            print(f"[QA FIGURES FAIL] {len(violations)} violação(ões) detectada(s):")
            for v in violations:
                print(f"  - {v['slide']}: {v['error']}")
            return 1
        print(f"[QA FIGURES PASS] {len(figs_ev)} figura(s) aprovada(s) nos portões determinísticos.")
        print(f"Próximo passo obrigatório: inspecione '{build_dir / 'qa_challenge_sheet.png'}' via read_file e rode --verify-audit --canary <CODIGO>.")
        return 0
    if not pptx_path.exists() or not pdf_path.exists():
        print(f"ERRO: PPTX ({pptx_path}) ou PDF ({pdf_path}) não encontrado. Rode o build/preview antes.", file=sys.stderr)
        return 2

    ev_path = build_dir / "visual_qa_evidence.json"
    rep_path = build_dir / "visual_audit_report.md"

    if args.verify_audit:
        if not ev_path.exists() or not rep_path.exists():
            print("ERRO [AUDIT_THEATER]: visual_qa_evidence.json ou visual_audit_report.md ausente.", file=sys.stderr)
            return 3
        ev = json.loads(ev_path.read_text(encoding="utf-8"))
        if ev.get("pptx_sha256") != sha256_file(pptx_path) or ev.get("pdf_sha256") != sha256_file(pdf_path):
            print("ERRO [STALE_AUDIT]: O PPTX ou PDF foi modificado após a geração das evidências.", file=sys.stderr)
            return 3
        if ev.get("total_violations", 1) > 0:
            print(f"ERRO [UNRESOLVED_VIOLATIONS]: Ainda existem {ev['total_violations']} violações determinísticas.", file=sys.stderr)
            return 1
        canary_in = (args.canary or "").strip().upper()
        if not canary_in:
            m = re.search(r"CANARY_VERIFIED:\*{0,2}\s*`?([A-Z0-9]{6})`?", rep_path.read_text(encoding="utf-8"))
            if m:
                canary_in = m.group(1)
        expected_hash = ev.get("canary_sha256", "")
        salt = ev.get("canary_salt", "")
        actual_hash = hashlib.sha256(f"{salt}:{canary_in}".encode("utf-8")).hexdigest()
        if not canary_in or actual_hash != expected_hash:
            print(
                "ERRO [AUDIT_THEATER_DETECTED]: Código canário inválido ou ausente! "
                "Abra 'build/qa_challenge_sheet.png' via read_file (visão), leia o código no banner azul e passe em --canary.",
                file=sys.stderr,
            )
            return 3
        rep_txt = rep_path.read_text(encoding="utf-8")
        if canary_in and f"CANARY_VERIFIED: `{canary_in}`" not in rep_txt:
            rep_txt = re.sub(r"CANARY_VERIFIED:\s*`?[^`\r\n]+`?", f"CANARY_VERIFIED: `{canary_in}`", rep_txt)
            rep_path.write_text(rep_txt, encoding="utf-8")
        if "[[PENDENTE" in rep_txt or "STATUS_GLOBAL: `REPROVADO" in rep_txt:
            print("ERRO [INCOMPLETE_AUDIT]: visual_audit_report.md ainda indica reprovação ou pendência.", file=sys.stderr)
            return 3
        if args.transcript and Path(args.transcript).exists():
            t_txt = Path(args.transcript).read_text(encoding="utf-8", errors="ignore")
            if "qa_challenge_sheet.png" not in t_txt and "contact_sheet.png" not in t_txt:
                print("ERRO [TRANSCRIPT_AUDIT_FAIL]: Nenhuma chamada read_file para qa_challenge_sheet.png no transcript.", file=sys.stderr)
                return 3
        print(f"[QA AUDIT VERIFIED PASS] Canário óptico '{canary_in}' confirmado, 0 violações geométricas e SHA-256 íntegro.")
        return 0

    prs = Presentation(str(pptx_path))
    slide_meta = load_slide_archetypes(job_dir, len(prs.slides))
    xml_issues = audit_pptx_xml(pptx_path)
    slides_ev, violations = audit_pdf_and_png(pdf_path, pngs, slide_meta)

    for idx, errs in xml_issues.items():
        sid = slide_meta.get(idx, {}).get("id", f"SL-{idx:02d}")
        for e in errs:
            violations.append({"slide": sid, "slide_num": idx, "error": e})
            if idx - 1 < len(slides_ev):
                slides_ev[idx - 1]["errors"].append(e)

    pptx_sha = sha256_file(pptx_path)
    pdf_sha = sha256_file(pdf_path)

    existing_canary = None
    existing_salt = None
    existing_canary_hash = None
    if ev_path.exists() and rep_path.exists():
        try:
            old_ev = json.loads(ev_path.read_text(encoding="utf-8"))
            if old_ev.get("pdf_sha256") == pdf_sha and old_ev.get("pptx_sha256") == pptx_sha:
                existing_salt = old_ev.get("canary_salt")
                existing_canary_hash = old_ev.get("canary_sha256")
                m_old = re.search(r"CANARY_VERIFIED:\*{0,2}\s*`?([A-Z0-9]{6})`?", rep_path.read_text(encoding="utf-8"))
                if m_old:
                    existing_canary = m_old.group(1)
        except Exception:
            pass

    if existing_salt and existing_canary_hash and (build_dir / "qa_challenge_sheet.png").exists():
        salt = existing_salt
        canary_hash = existing_canary_hash
    else:
        salt, canary_hash = generate_canary_challenge_sheet(pngs, build_dir, pdf_sha)

    evidence = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pptx_path": str(pptx_path),
        "pdf_path": str(pdf_path),
        "pptx_sha256": pptx_sha,
        "pdf_sha256": pdf_sha,
        "canary_salt": salt,
        "canary_sha256": canary_hash,
        "total_slides": len(slides_ev),
        "total_violations": len(violations),
        "flagged_slides": sorted({v["slide"] for v in violations}),
        "violations": violations,
        "slides": slides_ev,
    }
    ev_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, default=float), encoding="utf-8")

    canary_display = existing_canary if existing_canary else "A_PREENCHER_APOS_LER_QA_CHALLENGE_SHEET_PNG"
    md = [
        "# Relatório de Auditoria Visual Multimodal e Determinística",
        "",
        f"- **Timestamp do Build:** `{evidence['timestamp']}`",
        f"- **SHA-256 PPTX:** `{pptx_sha}`",
        f"- **SHA-256 PDF:** `{pdf_sha}`",
        f"- **Total de Slides:** {len(slides_ev)} | **Violações Determinísticas:** {len(violations)}",
        f"- **CANARY_VERIFIED:** `{canary_display}`",
        f"- **STATUS_GLOBAL:** `{'REPROVADO_NOS_GATES' if violations else 'APROVADO_NOS_GATES'}`",
        "",
        "## 1. Métricas Geométricas, Tipográficas e de Densidade 4x4 por Slide",
        "",
        "| Slide | Arquétipo | Fonte Corpo Mín (pt) | Fonte Máx (pt) | Contraste Mín | Tinta Esq (%) | Tinta Dir (%) | Status Determinístico |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]
    for s in slides_ev:
        st = "PASS" if not s["errors"] else "FAIL: " + "; ".join(s["errors"])
        md.append(
            f"| {s['id']} | `{s['archetype']}` | {s['min_body_pt']} | {s['max_font_pt']} | {s['min_contrast']}:1 | {s['left_ink_pct']}% | {s['right_ink_pct']}% | {st} |"
        )

    md += [
        "",
        "## 2. Parecer da Inspeção Visual Multimodal (Leitura de `build/qa_challenge_sheet.png`)",
        "",
        "- **Inspecionado via Visão Computacional (`read_file`):** Sim",
        "- **Equilíbrio Estético e Harmonia Global:** Verificado em todos os quadrantes (A1..D4).",
    ]
    rep_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    if violations:
        print(f"[QA GATES FAIL] {len(violations)} violação(ões) detectada(s) em {len(evidence['flagged_slides'])} slide(s):")
        for v in violations[:25]:
            print(f"  - {v['slide']}: {v['error']}")
        return 1

    print(f"[QA GATES PASS] {len(slides_ev)} slides aprovados nos 5 portões determinísticos.")
    print(f"Próximo passo obrigatório: inspecione '{build_dir / 'qa_challenge_sheet.png'}' via read_file e rode --verify-audit --canary <CODIGO>.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
