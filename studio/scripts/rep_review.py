#!/usr/bin/env python3
"""rep_review.py: Review Engine do Studio (REP generalizado): revisão particionada por PERSONA x LENTE x FATIA.

- Lente  = um tipo de cobrança (técnica, pedagógica, narrativa, visual, conformidade, persuasão...): critérios fixos.
- Persona = quem cobra (professor da disciplina, banca, revisor de journal, investidor, gestor, morador...):
            prioridades, rubrica, perguntas típicas, sinais de alerta. Calibrável com feedback real.
- Painel  = conjunto de personas + lentes para um contexto (defesa, simpósio, pitch, disciplina, manual de imóvel...).
Cada unidade de revisão é pequena (1 persona, até 3 lentes, uma fatia do material) para caber numa rodada.

Comandos:
  plan <job> --panel <id> [--slice 8] [--file <arquivo>]   cria review/plan.yaml
  brief <job> <unidade>                                     imprime TUDO que o revisor precisa ler naquela unidade
  validate <job> [--unit R03]                               confere review/R03.yaml
  consolidate <job>                                         une, deduplica, pontua -> report.md, revision_plan.yaml, qa_bank.md
  delta <job>                                               re-revisão só do que foi corrigido
  calibrate <persona> --record <arquivo.yaml>               registra comparação com feedback REAL e atualiza a persona
  list                                                      lentes, personas e painéis disponíveis
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from studio_common import STUDIO, UNIT_MAX_WORDS, Issues, dump_yaml, load_yaml, words  # noqa: E402

REV = STUDIO / "review"
SEV = {"blocker": 3, "major": 2, "minor": 1}


def lens(lid):
    return load_yaml(REV / "lenses" / f"{lid}.yaml")


def persona(pid):
    return load_yaml(REV / "personas" / f"{pid}.yaml")


def panel(pid):
    return load_yaml(REV / "panels" / f"{pid}.yaml")


def material(job, file=None):
    """Descobre o tipo de material e suas localizações revisáveis."""
    job = Path(job)
    if file:
        f = Path(file)
        text = f.read_text(encoding="utf-8", errors="replace")
        heads = re.findall(r"^#{1,3}\s+(.+)$", text, re.M)
        return {"kind": "file", "locs": [f"H{i + 1:02d}" for i in range(len(heads))] or ["ALL"], "file": str(f),
                "titles": heads}
    if (job / "outline.yaml").exists():
        o = load_yaml(job / "outline.yaml", {"slides": []})
        return {"kind": "deck", "locs": [s["id"] for s in o.get("slides", [])],
                "titles": [s.get("message", "") for s in o.get("slides", [])]}
    if (job / "doc.yaml").exists():
        d = load_yaml(job / "doc.yaml")
        secs = (d.get("sections") or []) + (d.get("appendix") or [])
        return {"kind": "document", "locs": [s["id"] for s in secs], "titles": [s.get("title", "") for s in secs]}
    raise SystemExit("ERRO: não reconheci o material (outline.yaml, doc.yaml ou --file).")


def cmd_list(a):
    for kind in ("lenses", "personas", "panels"):
        print(f"\n{kind.upper()}")
        for f in sorted((REV / kind).glob("*.yaml")):
            d = load_yaml(f, {})
            extra = ""
            if kind == "personas":
                extra = f"[{(d.get('calibration') or {}).get('status', 'generic')}]"
            print(f"  {f.stem:34s} {extra:12s} {d.get('name', '')}")
    return 0


def cmd_plan(a):
    job = Path(a.job)
    pn = panel(a.panel)
    mat = material(job, a.file)
    locs = mat["locs"]
    slices = [locs[i:i + a.slice] for i in range(0, len(locs), a.slice)] if mat["kind"] == "deck" else \
        ([locs[i:i + max(1, a.slice // 4)] for i in range(0, len(locs), max(1, a.slice // 4))]
         if mat["kind"] == "document" else [locs])
    units = []
    n = 1
    lead = pn["personas"][0]["id"]
    units.append({"id": f"R{n:02d}", "persona": lead, "lenses": pn.get("overview_lenses", ["narrative"]),
                  "scope": "overview", "locs": locs, "status": "todo"})
    n += 1
    for p in pn["personas"]:
        pc = persona(p["id"])
        pri = sorted((pc.get("priorities") or {}).items(), key=lambda x: -x[1])
        lens_ids = [l for l, _ in pri if l in pn.get("lenses", [l for l, _ in pri])][:p.get("max_lenses", 3)]
        for sl in slices:
            units.append({"id": f"R{n:02d}", "persona": p["id"], "lenses": lens_ids, "scope": "slice", "locs": sl,
                          "status": "todo"})
            n += 1
    out = {"panel": a.panel, "material": mat["kind"], "file": mat.get("file"), "created": str(datetime.date.today()),
           "units": units}
    dump_yaml(out, job / "review" / "plan.yaml")
    print(f"Plano de revisão ({a.panel}, {mat['kind']}): {len(units)} unidade(s)")
    for u in units:
        span = f"{u['locs'][0]}..{u['locs'][-1]}" if u["locs"] else "-"
        print(f"  {u['id']}: {u['persona']:30s} lentes={','.join(u['lenses'])}  {u['scope']} {span}")
    print("Para cada unidade: 'brief <job> <Rxx>', escreva review/<Rxx>.yaml, 'validate --unit <Rxx>'.")
    return 0


def _material_text(job, mat_kind, locs, file=None, scope="slice"):
    job = Path(job)
    out = []
    if mat_kind == "deck":
        if scope == "overview":
            o = load_yaml(job / "outline.yaml", {"slides": []})
            b = load_yaml(job / "brief.yaml", {})
            out.append(f"Brief: título={b.get('title')} · público={b.get('audience')} · objetivo={b.get('goal')} · "
                       f"duração={b.get('duration_min')} min")
            out += [f"- {s['id']} [{s.get('archetype')}] {s.get('message', '')}" for s in o.get("slides", [])]
            cs = job / "build" / "contact_sheet.png"
            if cs.exists():
                out.append(f"\nOlhe também a prévia: {cs.as_posix()}")
            return "\n".join(out)
        import yaml
        want = set(locs)
        for f in sorted((job / "spec").glob("U*.yaml")):
            for s in (load_yaml(f, {}).get("slides") or []):
                if s.get("id") in want:
                    out.append(yaml.safe_dump(s, allow_unicode=True, sort_keys=False).strip())
        prev = job / "build" / "previews"
        idx = job / "build" / "slides_index.md"
        if prev.exists() and idx.exists():
            nums = {m.group(2): m.group(1) for m in re.finditer(r"\| (\d+) \| (SL-\d+) \|", idx.read_text())}
            imgs = [f"{prev.as_posix()}/slide-{int(nums[i]):02d}.png" for i in locs if i in nums]
            out.append("\nPrévias destes slides: " + ", ".join(imgs))
        return "\n---\n".join(out)
    if mat_kind == "document":
        plan = load_yaml(job / "plan.yaml", {"units": []})
        for u in plan.get("units", []):
            if u["section"] in locs and (job / u["file"]).exists():
                out.append(f"% ===== {u['id']} ({u['file']})\n" + (job / u["file"]).read_text(encoding="utf-8"))
        if scope == "overview":
            d = load_yaml(job / "doc.yaml")
            return "\n".join(f"- {s['id']} {s.get('title')}: {s.get('brief', '')}" for s in d.get("sections", []))
        return "\n".join(out)
    return Path(file).read_text(encoding="utf-8", errors="replace")


def cmd_brief(a):
    job = Path(a.job)
    plan = load_yaml(job / "review" / "plan.yaml")
    u = next((x for x in plan["units"] if x["id"] == a.unit), None)
    if not u:
        raise SystemExit(f"ERRO: unidade {a.unit} não existe no plano")
    pc = persona(u["persona"])
    lines = [f"# Unidade de revisão {u['id']} ({plan['panel']})", "",
             f"## Você é: {pc.get('name')}", pc.get("context", ""), "",
             "Objetivos: " + "; ".join(pc.get("goals") or []),
             "Sinais de alerta: " + "; ".join(pc.get("red_flags") or []),
             f"Tom: {pc.get('tone', 'direto e específico')}", ""]
    if pc.get("learned_preferences"):
        lines += ["Preferências aprendidas com feedback REAL desta pessoa (priorize):"] + \
                 [f"- {x}" for x in pc["learned_preferences"]] + [""]
    cal = pc.get("calibration") or {}
    if cal.get("status") != "calibrated":
        lines.append("Persona GENÉRICA (não calibrada com feedback real): não invente gostos pessoais; cobre só o "
                     "que está nos critérios e na rubrica.")
    if pc.get("rubric"):
        lines += ["", "## Rubrica (dê nota 1-5 a cada critério, com justificativa de 1 frase)"]
        for r in pc["rubric"]:
            lines.append(f"- {r['id']} (peso {r.get('weight', 1)}): {r['text']}")
    lines += ["", "## Lentes desta unidade (só cobre estes critérios)"]
    for lid in u["lenses"]:
        ln = lens(lid)
        lines.append(f"### {ln['id']}: {ln.get('question', '')}")
        for c in ln.get("criteria", []):
            lines.append(f"- {c['id']} [{c.get('severity_hint', 'major')}]: {c['text']}")
    lines += ["", f"## Material ({u['scope']}: {', '.join(u['locs'][:12])}{'...' if len(u['locs']) > 12 else ''})", "",
              _material_text(job, plan["material"], u["locs"], plan.get("file"), u["scope"]), "",
              "## Saída: escreva review/" + u["id"] + ".yaml exatamente neste formato (máx. "
              f"{UNIT_MAX_WORDS} palavras)", "```yaml",
              f"unit: {u['id']}", f"persona: {u['persona']}", f"lenses: {u['lenses']}",
              "scores: []          # [{criterion: R1, score: 1-5, why: \"...\"}] (só se a persona tem rubrica)",
              "findings:", "  - id: F-" + u["id"] + "-01", "    lens: <id da lente>", "    criterion: <id do critério>",
              "    severity: blocker | major | minor", "    location: <SL-07 | S02 | H03>",
              "    evidence: \"<trecho literal do material>\"", "    problem: \"<o que está errado, específico>\"",
              "    suggested_fix: \"<ação concreta>\"",
              "questions: []       # perguntas que ESTA persona faria: [{q, location, difficulty: alta|media|baixa, "
              "suggested_answer}]", "strengths: []       # até 3 pontos fortes concretos", "```",
              "Regras: cada finding precisa de evidência literal e localização existente; nada de achado genérico; "
              "se não há problema, findings: []."]
    text = "\n".join(lines)
    print(text)
    if words(text) > 3500:
        print(f"\nAVISO: contexto grande ({words(text)} palavras); considere --slice menor no plan.")
    return 0


def validate_unit(job, plan, u, iss, mat_locs):
    f = Path(job) / "review" / f"{u['id']}.yaml"
    if not f.exists():
        iss.err(u["id"], "arquivo de revisão ainda não escrito")
        return None
    try:
        r = load_yaml(f, {})
    except ValueError as e:
        iss.err(u["id"], str(e))
        return None
    pc = persona(u["persona"])
    crit = {c["id"] for lid in u["lenses"] for c in lens(lid).get("criteria", [])}
    rub = {x["id"] for x in pc.get("rubric") or []}
    if words(r) > UNIT_MAX_WORDS:
        iss.err(u["id"], f"{words(r)} palavras (máx. {UNIT_MAX_WORDS})")
    for i, fd in enumerate(r.get("findings") or []):
        w = f"{u['id']}.findings[{i}]"
        if fd.get("severity") not in SEV:
            iss.err(w, f"severity '{fd.get('severity')}' inválida")
        if fd.get("lens") not in u["lenses"]:
            iss.warn(w, f"lente '{fd.get('lens')}' fora desta unidade")
        if fd.get("criterion") not in crit:
            iss.warn(w, f"critério '{fd.get('criterion')}' não pertence às lentes da unidade")
        loc = str(fd.get("location", ""))
        if mat_locs and loc.split(".")[0] not in mat_locs and loc not in ("geral", "ALL"):
            iss.err(w, f"location '{loc}' não existe no material")
        if fd.get("severity") in ("blocker", "major") and not str(fd.get("evidence", "")).strip():
            iss.err(w, "blocker/major sem evidência literal")
        for k in ("problem", "suggested_fix"):
            if not str(fd.get(k, "")).strip():
                iss.err(w, f"campo vazio: {k}")
    for i, sc in enumerate(r.get("scores") or []):
        if rub and sc.get("criterion") not in rub:
            iss.warn(f"{u['id']}.scores[{i}]", f"critério '{sc.get('criterion')}' não está na rubrica da persona")
        if not isinstance(sc.get("score"), (int, float)) or not 1 <= sc["score"] <= 5:
            iss.err(f"{u['id']}.scores[{i}]", "score deve ser 1 a 5")
        if not sc.get("why"):
            iss.err(f"{u['id']}.scores[{i}]", "nota sem justificativa")
    if rub and u["scope"] != "overview" and not r.get("scores"):
        iss.warn(u["id"], "persona tem rubrica mas a unidade não deu notas")
    return r


def cmd_validate(a):
    job = Path(a.job)
    plan = load_yaml(job / "review" / "plan.yaml")
    mat = material(job, plan.get("file"))
    iss = Issues()
    for u in plan["units"]:
        if a.unit and u["id"] != a.unit:
            continue
        r = validate_unit(job, plan, u, iss, set(mat["locs"]))
        if r is not None and a.unit and not [i for i in iss.errors if i["where"].startswith(u["id"])]:
            u["status"] = "done"
    dump_yaml(plan, job / "review" / "plan.yaml")
    iss.print("Validação da revisão:")
    return iss.exit_code()


def _sim(a, b):
    sa, sb = set(re.findall(r"\w{4,}", a.lower())), set(re.findall(r"\w{4,}", b.lower()))
    return len(sa & sb) / len(sa | sb) if sa and sb else 0


def cmd_consolidate(a):
    job = Path(a.job)
    plan = load_yaml(job / "review" / "plan.yaml")
    pn = panel(plan["panel"])
    weights = {p["id"]: p.get("weight", 1) for p in pn["personas"]}
    merged, scores, questions, strengths, missing = [], {}, [], [], []
    for u in plan["units"]:
        f = job / "review" / f"{u['id']}.yaml"
        if not f.exists():
            missing.append(u["id"])
            continue
        r = load_yaml(f, {})
        for fd in r.get("findings") or []:
            fd = dict(fd, persona=u["persona"])
            dup = next((m for m in merged if m["location"] == fd.get("location") and
                        (m["criterion"] == fd.get("criterion") or _sim(m["problem"], fd.get("problem", "")) > 0.45)),
                       None)
            if dup:
                dup["raised_by"] = sorted(set(dup["raised_by"]) | {u["persona"]})
                if SEV.get(fd.get("severity"), 0) > SEV.get(dup["severity"], 0):
                    dup["severity"] = fd["severity"]
                dup["ids"].append(fd.get("id"))
            else:
                merged.append({"ids": [fd.get("id")], "location": fd.get("location"), "lens": fd.get("lens"),
                               "criterion": fd.get("criterion"), "severity": fd.get("severity"),
                               "problem": fd.get("problem", ""), "evidence": fd.get("evidence", ""),
                               "suggested_fix": fd.get("suggested_fix", ""), "raised_by": [u["persona"]]})
        for sc in r.get("scores") or []:
            scores.setdefault(u["persona"], {}).setdefault(sc["criterion"], []).append(sc["score"])
        questions += [dict(q, persona=u["persona"]) for q in r.get("questions") or []]
        strengths += [f"{s} ({u['persona']})" for s in r.get("strengths") or []]
    merged.sort(key=lambda m: (-SEV.get(m["severity"], 0), -len(m["raised_by"]), str(m["location"])))
    for i, m in enumerate(merged, 1):
        m["id"] = f"C-{i:03d}"
    per = {}
    for pid, crits in scores.items():
        rub = {x["id"]: x.get("weight", 1) for x in persona(pid).get("rubric") or []}
        tot = sum(rub.get(c, 1) for c in crits)
        per[pid] = round(sum(sum(v) / len(v) * rub.get(c, 1) for c, v in crits.items()) / tot, 2) if tot else None
    valid = {k: v for k, v in per.items() if v is not None}
    overall = round(sum(v * weights.get(k, 1) for k, v in valid.items()) / sum(weights.get(k, 1) for k in valid), 2) \
        if valid else None
    nb = sum(1 for m in merged if m["severity"] == "blocker")
    nm = sum(1 for m in merged if m["severity"] == "major")
    verdict = "BLOQUEADO" if nb else ("REVISAR" if nm > pn.get("max_majors", 3) else "PRONTO")
    seenq, qs = [], []
    for q in questions:
        if all(_sim(q.get("q", ""), s) < 0.5 for s in seenq):
            seenq.append(q.get("q", ""))
            qs.append(q)
    md = [f"# Revisão consolidada: painel {plan['panel']}", "",
          f"**Veredito:** {verdict} · blockers {nb} · majors {nm} · minors {len(merged) - nb - nm}"
          + (f" · nota geral {overall}/5" if overall else ""), ""]
    if missing:
        md += [f"> Unidades sem revisão: {', '.join(missing)} (consolidação parcial)", ""]
    if per:
        md += ["## Notas por persona", "", "| Persona | Nota (1-5) |", "|---|---|"]
        md += [f"| {k} | {v} |" for k, v in per.items()] + [""]
    md += ["## Achados (ordenados por severidade e consenso)", "",
           "| ID | Sev. | Onde | Lente/critério | Problema | Correção sugerida | Quem levantou |", "|---|---|---|---|---|---|---|"]
    md += [f"| {m['id']} | {m['severity']} | {m['location']} | {m['lens']}/{m['criterion']} | "
           f"{m['problem'].replace('|', '/')} | {m['suggested_fix'].replace('|', '/')} | {', '.join(m['raised_by'])} |"
           for m in merged]
    if strengths:
        md += ["", "## Pontos fortes", ""] + [f"- {s}" for s in strengths[:10]]
    (job / "review" / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    by_loc = {}
    for m in merged:
        by_loc.setdefault(str(m["location"]), []).append({"finding": m["id"], "severity": m["severity"],
                                                          "action": m["suggested_fix"], "status": "todo"})
    dump_yaml({"verdict": verdict, "items": [{"location": k, "actions": v} for k, v in by_loc.items()]},
              job / "review" / "revision_plan.yaml")
    dump_yaml({"findings": merged, "scores": per, "overall": overall}, job / "review" / "consolidated.yaml")
    qmd = ["# Banco de perguntas prováveis (prepare respostas)", ""]
    for q in sorted(qs, key=lambda x: {"alta": 0, "media": 1, "média": 1, "baixa": 2}.get(x.get("difficulty"), 1)):
        qmd += [f"- **[{q.get('difficulty', '?')}] {q.get('q')}** ({q.get('persona')}, {q.get('location', 'geral')})",
                f"  - Resposta sugerida: {q.get('suggested_answer', '_preencher_')}"]
    (job / "review" / "qa_bank.md").write_text("\n".join(qmd) + "\n", encoding="utf-8")
    print(f"Veredito: {verdict} ({nb} blocker, {nm} major, {len(merged) - nb - nm} minor; {len(qs)} perguntas)"
          + (f"; nota {overall}/5" if overall else ""))
    print(f"Relatório: {job / 'review' / 'report.md'} · plano de correção: revision_plan.yaml · perguntas: qa_bank.md")
    return 1 if nb else 0


def cmd_delta(a):
    job = Path(a.job)
    rp = load_yaml(job / "review" / "revision_plan.yaml")
    cons = load_yaml(job / "review" / "consolidated.yaml")
    plan = load_yaml(job / "review" / "plan.yaml")
    fixed = {act["finding"] for it in rp["items"] for act in it["actions"] if act.get("status") == "done"}
    pending = [act["finding"] for it in rp["items"] for act in it["actions"] if act.get("status") != "done"
               and act["severity"] in ("blocker", "major")]
    by_p = {}
    for m in cons["findings"]:
        if m["id"] in fixed:
            for p in m["raised_by"]:
                by_p.setdefault(p, {"locs": set(), "lenses": set(), "findings": []})
                by_p[p]["locs"].add(str(m["location"]))
                by_p[p]["lenses"].add(m["lens"])
                by_p[p]["findings"].append(m["id"])
    units = [{"id": f"D{i:02d}", "persona": p, "lenses": sorted(v["lenses"])[:3], "scope": "delta",
              "locs": sorted(v["locs"]), "recheck": v["findings"], "status": "todo"}
             for i, (p, v) in enumerate(sorted(by_p.items()), 1)]
    plan["units"] = [u for u in plan["units"] if not u["id"].startswith("D")] + units
    dump_yaml(plan, job / "review" / "plan.yaml")
    print(f"Delta: {len(units)} unidade(s) de re-revisão para {len(fixed)} correção(ões).")
    for u in units:
        print(f"  {u['id']}: {u['persona']} re-checa {', '.join(u['recheck'])} em {', '.join(u['locs'])}")
    if pending:
        print(f"AVISO: blockers/majors ainda não corrigidos: {', '.join(pending)}")
    return 0


def cmd_calibrate(a):
    rec = load_yaml(a.record)
    pf = REV / "personas" / f"{a.persona}.yaml"
    pc = load_yaml(pf)
    real = rec.get("real_feedback") or []
    matched = sum(1 for r in real if r.get("matched_finding"))
    unmatched_sim = len(rec.get("simulated_not_raised_by_real") or [])
    recall = matched / len(real) if real else 0
    precision = matched / (matched + unmatched_sim) if (matched + unmatched_sim) else 0
    cal = pc.setdefault("calibration", {})
    hist = cal.setdefault("history", [])
    hist.append({"date": str(datetime.date.today()), "job": rec.get("job"), "real_items": len(real),
                 "recall": round(recall, 2), "precision": round(precision, 2)})
    cal["status"] = "calibrated"
    cal["last"] = str(datetime.date.today())
    learned = [r.get("lesson") for r in real if r.get("lesson")]
    if learned:
        pc.setdefault("learned_preferences", [])
        for l in learned:
            if l not in pc["learned_preferences"]:
                pc["learned_preferences"].append(l)
    if rec.get("add_red_flags"):
        pc.setdefault("red_flags", []).extend(x for x in rec["add_red_flags"] if x not in pc["red_flags"])
    dump_yaml(pc, pf)
    print(f"OK: {a.persona} calibrada. Recall {recall:.0%} (o que o real cobrou e a simulação pegou), "
          f"precisão {precision:.0%}. {len(learned)} preferência(s) aprendida(s).")
    if recall < 0.5:
        print("AVISO: a simulação está perdendo mais da metade das cobranças reais; revise prioridades e rubrica.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.set_defaults(fn=cmd_list)
    p = sub.add_parser("plan"); p.add_argument("job"); p.add_argument("--panel", required=True)
    p.add_argument("--slice", type=int, default=8); p.add_argument("--file"); p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("brief"); p.add_argument("job"); p.add_argument("unit"); p.set_defaults(fn=cmd_brief)
    p = sub.add_parser("validate"); p.add_argument("job"); p.add_argument("--unit"); p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("consolidate"); p.add_argument("job"); p.set_defaults(fn=cmd_consolidate)
    p = sub.add_parser("delta"); p.add_argument("job"); p.set_defaults(fn=cmd_delta)
    p = sub.add_parser("calibrate"); p.add_argument("persona"); p.add_argument("--record", required=True)
    p.set_defaults(fn=cmd_calibrate)
    a = ap.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
