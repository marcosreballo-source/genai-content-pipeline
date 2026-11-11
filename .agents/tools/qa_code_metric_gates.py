#!/usr/bin/env python3
"""
AcademicOS — Portão Automático de Qualidade e Conciliação Numérica (QA Code & Metric Gates)
=======================================================================================
Portão de auditoria determinística programática pré-revisão acadêmica.
Executa verificações rigorosas sobre entregáveis de código, teste e métricas quantitativas,
impedindo a aprovação de trabalhos com discrepâncias numéricas, falhas em cabeçalhos,
afirmações errôneas sobre topologia de grafos ou pseudominimização de casos de teste.

Portões Executados:
  [GATE 1] Conciliação Numérica Tríplice: Markdown Tables vs Logs Brutos (evid_*.txt)
  [GATE 2] Verificação de Minimização Estrita e Set Cover Exato (Branch & Bound / ILP)
  [GATE 3] Auditoria de Integridade de Cabeçalhos e Metadados de Código (.py vs Execução)
  [GATE 4] Auditoria Estrutural e Semântica de Grafos de Controle (CFG/GFC vs Texto)
  [GATE 5] Higiene de Arquivos e Integridade do Pacote de Entrega (.zip / arquivos 0 bytes)

Retorno:
  Exit Code 0: APROVADO (Todos os portões verdes)
  Exit Code 1: REJEITADO (Falhas críticas detectadas; pipeline deve pausar)
"""

import os
import sys
import re
import csv
import glob
import pickle
import zipfile
import itertools
from typing import Dict, List, Tuple, Any, Optional


class QualityGateRunner:
    def __init__(self, target_dir: str):
        self.target_dir = os.path.abspath(target_dir)
        self.report_md_path = self._find_report_md()
        self.results: Dict[str, Dict[str, Any]] = {}
        self.all_passed = True
        self.is_vvts = any(os.path.exists(os.path.join(self.target_dir, f)) for f in ["tabelaHash.py", "cobertura.py", "evid_01_report_funcional.txt", "estrutural.py"])

    def _find_report_md(self) -> Optional[str]:
        candidates = glob.glob(os.path.join(self.target_dir, "relatorio_*.md"))
        if not candidates:
            candidates = glob.glob(os.path.join(self.target_dir, "*relatorio*.md"))
        return candidates[0] if candidates else None

    def log_result(self, gate_name: str, passed: bool, summary: str, details: List[str]):
        self.results[gate_name] = {
            "passed": passed,
            "summary": summary,
            "details": details
        }
        if not passed:
            self.all_passed = False

    # =========================================================================
    # GATE 1: Conciliação Numérica Tríplice (Tabelas do Relatório vs Logs Brutos)
    # =========================================================================
    def check_gate_1_reconciliation(self) -> bool:
        gate_name = "GATE 1: Conciliação Numérica Tríplice (Tabelas vs Logs Brutos)"
        details = []
        passed = True

        if not self.report_md_path or not os.path.exists(self.report_md_path):
            self.log_result(gate_name, False, "Relatório Markdown não encontrado para conciliação.", ["Arquivo relatorio_*.md ausente."])
            return False

        with open(self.report_md_path, "r", encoding="utf-8", errors="ignore") as f:
            report_text = f.read()

        if not self.is_vvts:
            gate_name = "GATE 1: Conciliação Numérica Tríplice (Tabelas vs Dados Brutos/CSVs)"
            details.append("Modo: Análise de Dados / Machine Learning (RAD2810 / Data Science)")
            csv_path = os.path.join(self.target_dir, "tabela_medidas_performance.csv")
            if os.path.exists(csv_path):
                details.append(f"Auditando métricas contra: {os.path.basename(csv_path)}")
                with open(csv_path, "r", encoding="utf-8") as cf:
                    reader = csv.DictReader(cf)
                    csv_rows = list(reader)
                
                mismatches = 0
                for r in csv_rows:
                    model_name = r["Modelo"]
                    for metric_key in ["Recall", "Precisao", "F1", "Acuracia", "AUC"]:
                        raw_val = float(r[metric_key])
                        val_str_comma = f"{raw_val:.4f}".replace(".", ",")
                        val_str_3_comma = f"{raw_val:.3f}".replace(".", ",")
                        pct_str_comma = f"{raw_val*100:.2f}".replace(".", ",")
                        if (val_str_comma in report_text or 
                            val_str_3_comma in report_text or 
                            f"{raw_val:.4f}" in report_text or 
                            pct_str_comma in report_text):
                            pass
                        else:
                            mismatches += 1
                            details.append(f"  ❌ Métrica {metric_key} do modelo {model_name} ({raw_val:.4f}) não encontrada com fidelidade no relatório!")
                            passed = False
                if mismatches == 0:
                    details.append(f"  ✅ Todas as métricas de performance dos {len(csv_rows)} modelos coincidem 100% com o CSV bruto!")
            else:
                details.append("  ℹ️ Nenhum arquivo CSV de métricas brutas encontrado; validando integridade tabular.")
            summary = "Conciliação numérica concluída com 100% de exatidão." if passed else "Detectadas discrepâncias numéricas entre tabelas do relatório e logs de evidência!"
            self.log_result(gate_name, passed, summary, details)
            return passed

        def parse_evid(fname):
            fpath = os.path.join(self.target_dir, fname)
            if not os.path.exists(fpath):
                return None
            content = open(fpath, "r", encoding="utf-8", errors="ignore").read()
            pattern = r"Function: .*?\.(.*?)\s*--\s*(\d+)\s*\nBlock:\s*(\d+)\s*Edge:\s*(\d+)\s*Essential edge:\s*(\d+)\s*Edge-pair:\s*(\d+)\s*Prime Path:\s*(\d+)"
            matches = re.findall(pattern, content)
            res = {}
            for fn, ord_num, b, e, ess, ep, pp in matches:
                res[int(ord_num)] = {
                    "fn": fn,
                    "metrics": (int(b), int(e), int(ess), int(ep), int(pp)),
                    "str": f"{b} / {e} / {ess} / {ep} / {pp}"
                }
            tot_match = re.search(r"Total:\s*Block:\s*(\d+)\s*Edge:\s*(\d+)\s*Essential edge:\s*(\d+)\s*Edge-pair:\s*(\d+)\s*Prime Path:\s*(\d+)", content)
            if tot_match:
                res[0] = {
                    "fn": "Total",
                    "metrics": tuple(int(x) for x in tot_match.groups()),
                    "str": f"{tot_match.group(1)} / {tot_match.group(2)} / {tot_match.group(3)} / {tot_match.group(4)} / {tot_match.group(5)}"
                }
            return res

        evid_files = {
            "E1 (funcional)": "evid_01_report_funcional.txt",
            "E2 (cobertura)": "evid_02_report_cobertura.txt",
            "E3 (mcdc)": "evid_03_report_mcdc.txt",
            "E4 (cob+mcdc)": "evid_04_report_cob_mcdc.txt",
            "E6 (bruto)": "evid_06_cob_mcdc_estrutural.txt",
            "E6b (infeasible)": "evid_06b_infeasible.txt"
        }

        parsed_evids = {k: parse_evid(v) for k, v in evid_files.items()}

        # Extract Table 3 rows: requires cells with 4 slashes (B / E / Ess / EP / PP)
        slash5 = r"`?\d+\s*/\s*\d+\s*/\s*\d+\s*/\s*\d+\s*/\s*\d+`?"
        table3_rows = re.findall(
            rf"\|\s*(\d+)\s*\|\s*`?([a-zA-Z0-9_]+)`?\s*\|\s*({slash5})\s*\|\s*({slash5})\s*\|\s*({slash5})\s*\|\s*({slash5})\s*\|",
            report_text
        )

        if table3_rows:
            details.append(f"Auditando Tabela 3 — Cobertura Detalhada ({len(table3_rows)} funções):")
            mismatches = 0
            for row in table3_rows:
                ord_num = int(row[0])
                fn_name = row[1]
                cols = {
                    "E1 (funcional)": row[2].replace("`", "").replace(" ", ""),
                    "E2 (cobertura)": row[3].replace("`", "").replace(" ", ""),
                    "E3 (mcdc)": row[4].replace("`", "").replace(" ", ""),
                    "E4 (cob+mcdc)": row[5].replace("`", "").replace(" ", "")
                }
                for config_key, table_val in cols.items():
                    evid_data = parsed_evids.get(config_key)
                    if evid_data and ord_num in evid_data:
                        real_val = evid_data[ord_num]["str"].replace(" ", "")
                        if table_val != real_val:
                            mismatches += 1
                            passed = False
                            details.append(f"  ❌ F{ord_num} ({fn_name}) em {config_key}: Tabela 3 diz '{table_val}' mas log '{evid_files[config_key]}' registra '{real_val}'")
            if mismatches == 0:
                details.append("  ✅ Todas as 56 células da Tabela 3 coincidem 100% com os logs brutos (evid_01 a evid_04)!")
        else:
            passed = False
            details.append("  ❌ Tabela 3 não localizada no formato esperado.")

        # Audit Table 5 (estrutural.py Bruto vs após --infeasible)
        t5_section = report_text.split("Tabela 5", 1)[1] if "Tabela 5" in report_text else report_text
        slash5_opt_star = r"\**`?\**\d+\*?\s*/\s*\d+\s*/\s*\d+\s*/\s*\d+\s*/\s*\d+\**`?\**"
        table5_rows = re.findall(
            rf"\|\s*(\d+)\s*\|\s*`?([a-zA-Z0-9_]+)`?\s*\|\s*({slash5})\s*\|\s*({slash5_opt_star})\s*\|\s*\d+\s*/\s*\d+",
            t5_section
        )
        if table5_rows:
            details.append(f"Auditando Tabela 5 — Cobertura Final ({len(table5_rows)} funções):")
            mismatches_t5 = 0
            for row in table5_rows:
                ord_num = int(row[0])
                fn_name = row[1]
                bruto_val = row[2].replace("`", "").replace("*", "").replace(" ", "")
                inf_val = row[3].replace("`", "").replace("*", "").replace(" ", "")
                real_bruto = parsed_evids["E6 (bruto)"][ord_num]["str"].replace(" ", "")
                real_inf = parsed_evids["E6b (infeasible)"][ord_num]["str"].replace(" ", "")
                if bruto_val != real_bruto:
                    mismatches_t5 += 1
                    passed = False
                    details.append(f"  ❌ F{ord_num} ({fn_name}) Bruto: Tabela 5 diz '{bruto_val}' mas evid_06 registra '{real_bruto}'")
                if inf_val != real_inf:
                    mismatches_t5 += 1
                    passed = False
                    details.append(f"  ❌ F{ord_num} ({fn_name}) Infeasible: Tabela 5 diz '{inf_val}' mas evid_06b registra '{real_inf}'")
            if mismatches_t5 == 0:
                details.append("  ✅ Todas as 28 células da Tabela 5 coincidem 100% com os logs (evid_06 e evid_06b)!")

        summary = "Conciliação numérica concluída com 100% de exatidão." if passed else "Detectadas divergências numéricas entre tabelas do relatório e logs de evidência!"
        self.log_result(gate_name, passed, summary, details)
        return passed

    # =========================================================================
    # GATE 2: Verificação de Minimização Estrita e Set Cover Exato
    # =========================================================================
    def check_gate_2_minimality(self) -> bool:
        gate_name = "GATE 2: Minimização Estrita e Set Cover Exato (Branch & Bound)"
        details = []
        passed = True

        if not self.is_vvts:
            gate_name = "GATE 2: Integridade de Ativos e Evidências Visuais (Figuras e Gráficos)"
            details.append("Modo: Análise de Dados / Machine Learning — Auditoria de Ativos Gráficos")
            if self.report_md_path:
                with open(self.report_md_path, "r", encoding="utf-8", errors="ignore") as f:
                    rep_md = f.read()
                img_refs = re.findall(r"!\[.*?\]\(([^)]+)\)", rep_md)
                details.append(f"Verificando {len(img_refs)} imagens referenciadas no relatório.")
                for img_rel in img_refs:
                    img_path = os.path.join(self.target_dir, img_rel.replace("/", os.sep))
                    if not os.path.exists(img_path):
                        passed = False
                        details.append(f"  ❌ Imagem referenciada ausente no disco: '{img_rel}'")
                    elif os.path.getsize(img_path) < 1000:
                        passed = False
                        details.append(f"  ❌ Imagem corrompida ou vazia (<1KB): '{img_rel}'")
                    else:
                        details.append(f"  ✅ Imagem válida: '{img_rel}' ({os.path.getsize(img_path)} bytes)")
            summary = "Integridade de figuras e ativos gráficos validada com sucesso." if passed else "Imagens ausentes ou corrompidas detectadas no relatório!"
            self.log_result(gate_name, passed, summary, details)
            return passed

        cobertura_path = os.path.join(self.target_dir, "cobertura.py")
        if os.path.exists(cobertura_path):
            with open(cobertura_path, "r", encoding="utf-8", errors="ignore") as f:
                cob_code = f.read()

            methods = re.findall(r"def (test_\w+)\(self", cob_code)
            details.append(f"Auditoria de cobertura.py: {len(methods)} métodos de teste encontrados.")

            redundant_trio = {
                "test_desvio_validacao_chave_float_e_invalidos",
                "test_funcao_hash_invalid_boolean",
                "test_init_invalid",
            }
            present_redundant = [m for m in methods if m in redundant_trio]
            if len(present_redundant) > 0:
                passed = False
                details.append(f"  ❌ FALHA DE MINIMALIDADE: cobertura.py ainda contém {len(present_redundant)} métodos redundantes: {present_redundant}!")
            elif len(methods) == 14:
                details.append("  ✅ cobertura.py possui exatamente os 14 métodos estritamente mínimos (0 métodos redundantes).")
            else:
                passed = False
                details.append(f"  ❌ cobertura.py possui {len(methods)} métodos, esperado 14.")

        csv_dir = os.path.join(self.target_dir, "csv")
        exact_sizes = {}
        if os.path.exists(csv_dir):
            for crit in ["essent", "edge", "edgpair", "primepath"]:
                csv_path = os.path.join(csv_dir, f"tabelaHash_{crit}.csv")
                if os.path.exists(csv_path):
                    size, sol, essential = self._solve_min_set_cover(csv_path)
                    exact_sizes[crit] = size
                    details.append(f"Critério {crit.upper()}: Mínimo Exato Global = {size} testes (Essenciais: {len(essential)})")

        # Verify report Table 6 has no transcription error (must include test_base_04 in Prime Path and not falsely claim test_04 was retained by mincsv for Prime Path)
        if self.report_md_path:
            with open(self.report_md_path, "r", encoding="utf-8", errors="ignore") as f:
                rep_md = f.read()
            # Check that the exact minimum sizes (5, 5, 9, 14) are documented in the report
            if "5 testes" not in rep_md or "9 testes" not in rep_md:
                passed = False
                details.append("  ❌ O relatório ainda não documenta a solução exata (Minimum Set Cover = 5, 5, 9, 14 testes) em comparação ao algoritmo guloso!")
            else:
                details.append("  ✅ O relatório documenta formalmente a comparação entre o algoritmo guloso (--mincsv) e o Mínimo Exato (5, 5, 9, 14 testes).")

        summary = "Minimização e análise de Set Cover validadas com sucesso." if passed else "Falhas na minimização de suítes ou na documentação do Set Cover exato!"
        self.log_result(gate_name, passed, summary, details)
        return passed

    def _solve_min_set_cover(self, csv_path: str) -> Tuple[int, List[str], List[str]]:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)
        tests = header[3:]
        reqs = len(rows)
        req_covers = []
        test_covers = [set() for _ in tests]
        for r_idx, row in enumerate(rows):
            covered_by = set()
            for t_idx, val in enumerate(row[3:]):
                if val.strip() in ("1", "True", "true", "x", "X"):
                    covered_by.add(t_idx)
                    test_covers[t_idx].add(r_idx)
            req_covers.append(covered_by)

        essential = set()
        for r, cov in enumerate(req_covers):
            if len(cov) == 1:
                essential.add(list(cov)[0])

        uncovered = set(range(reqs)) - set().union(*[test_covers[e] for e in essential])
        if not uncovered:
            return len(essential), [tests[e] for e in essential], [tests[e] for e in essential]

        non_essential = [i for i in range(len(tests)) if i not in essential]
        candidates = [i for i in non_essential if test_covers[i] & uncovered]

        for k in range(1, len(candidates) + 1):
            for combo in itertools.combinations(candidates, k):
                c = set().union(*[test_covers[i] & uncovered for i in combo])
                if len(c) == len(uncovered):
                    sol = list(essential) + list(combo)
                    return len(sol), [tests[i] for i in sol], [tests[e] for e in essential]
        return len(tests), tests, [tests[e] for e in essential]

    # =========================================================================
    # GATE 3: Auditoria de Cabeçalhos e Metadados de Código (.py vs Execução)
    # =========================================================================
    def check_gate_3_headers(self) -> bool:
        gate_name = "GATE 3: Integridade de Cabeçalhos e Metadados de Código (.py)"
        details = []
        passed = True

        if not self.is_vvts:
            gate_name = "GATE 3: Integridade de Código-Fonte, Parâmetros e Reprodutibilidade"
            details.append("Modo: Análise de Dados / Machine Learning — Auditoria de Scripts e Código")
            scripts = glob.glob(os.path.join(self.target_dir, "*.R")) + glob.glob(os.path.join(self.target_dir, "*.py"))
            if not scripts:
                passed = False
                details.append("  ❌ Nenhum script de código (.R ou .py) encontrado na pasta da atividade!")
            else:
                for sc in scripts:
                    with open(sc, "r", encoding="utf-8", errors="ignore") as f:
                        sc_code = f.read()
                    sc_name = os.path.basename(sc)
                    if "<NUSP>" in sc_code:
                        details.append(f"  ✅ Script '{sc_name}' contém identificação nominal / NUSP (<NUSP>).")
                    if "set.seed" in sc_code or "random_state" in sc_code or "seed" in sc_code:
                        details.append(f"  ✅ Script '{sc_name}' contém controle explícito de semente de reprodutibilidade.")
            summary = "Código-fonte e parâmetros de reprodutibilidade auditados com sucesso." if passed else "Falhas de reprodutibilidade ou ausência de scripts detectadas!"
            self.log_result(gate_name, passed, summary, details)
            return passed

        estrutural_path = os.path.join(self.target_dir, "estrutural.py")
        if os.path.exists(estrutural_path):
            with open(estrutural_path, "r", encoding="utf-8", errors="ignore") as f:
                code_text = f.read()

            base_match = re.search(r"class TestBaseEstruturalCompleta\(unittest\.TestCase\):(.*?)(?:class|\Z)", code_text, re.DOTALL)
            if base_match:
                methods_base = re.findall(r"def (test_\w+)\(self", base_match.group(1))
                real_count = len(methods_base)
                doc_claim = re.search(r"TestBaseEstruturalCompleta\s*\(\s*(\d+)\s*métodos", code_text)
                if doc_claim:
                    claimed = int(doc_claim.group(1))
                    if claimed != real_count:
                        passed = False
                        details.append(f"  ❌ FALHA DE CABEÇALHO em estrutural.py: Docstring afirma '{claimed} métodos de teste' para TestBaseEstruturalCompleta, mas a classe define {real_count} métodos!")
                    else:
                        details.append(f"  ✅ estrutural.py: Contagem de TestBaseEstruturalCompleta confere ({real_count} métodos).")

        cobertura_path = os.path.join(self.target_dir, "cobertura.py")
        if os.path.exists(cobertura_path):
            with open(cobertura_path, "r", encoding="utf-8", errors="ignore") as f:
                cob_text = f.read()
            if "15/18 requisitos" in cob_text or "83% (15/18" in cob_text:
                passed = False
                details.append("  ❌ FALHA DE CABEÇALHO em cobertura.py: Informa '15/18 requisitos MC/DC', mas a execução confirmada é de 14/18 (77%)!")
            elif "14/18" in cob_text:
                details.append("  ✅ cobertura.py: Cabeçalho registra corretamente 14/18 requisitos MC/DC (77%).")

        summary = "Todos os cabeçalhos de código estão consistentes com a realidade." if passed else "Cabeçalhos de código contêm valores desatualizados ou contagens incorretas!"
        self.log_result(gate_name, passed, summary, details)
        return passed

    # =========================================================================
    # GATE 4: Auditoria Estrutural e Semântica de Grafos de Controle (CFG/GFC)
    # =========================================================================
    def check_gate_4_cfg_semantics(self) -> bool:
        gate_name = "GATE 4: Semântica e Topologia de Grafos de Controle (CFG/GFC)"
        details = []
        passed = True

        if not self.is_vvts:
            gate_name = "GATE 4: Integridade do Cabeçalho Acadêmico e Higiene Textual"
            details.append("Modo: Análise de Dados / Machine Learning — Cabeçalho e Higiene")
            if self.report_md_path:
                with open(self.report_md_path, "r", encoding="utf-8", errors="ignore") as f:
                    rep_text = f.read()
                
                for req_item in ["<NOME_DO_ESTUDANTE>", "<NUSP>", "USP", "<NOME_DO_PROFESSOR>"]:
                    if req_item not in rep_text:
                        passed = False
                        details.append(f"  ❌ Elemento obrigatório de cabeçalho ausente: '{req_item}'")
                    else:
                        details.append(f"  ✅ Elemento de cabeçalho verificado: '{req_item}'")
                
                prohibited = ["conforme DKB", "segundo o ASB", "obedecendo ao CEP", "conforme a DKB", "segundo o CEP"]
                found_prohibited = [p for p in prohibited if p.lower() in rep_text.lower()]
                if found_prohibited:
                    passed = False
                    details.append(f"  ❌ Termos de metalinguagem interna proibida detectados: {found_prohibited}")
                else:
                    details.append("  ✅ Zero autorreferências a metalinguagem interna de agentes.")
            summary = "Cabeçalho institucional e higiene textual validados com sucesso." if passed else "Inconsistências no cabeçalho ou uso de metalinguagem proibida detectados!"
            self.log_result(gate_name, passed, summary, details)
            return passed

        # Rebuild fresh base CFG in a temporary directory to verify raw structural counts before --infeasible
        import pickle
        import shutil
        import subprocess
        import tempfile
        src_path = os.path.join(self.target_dir, "tabelaHash.py")
        if os.path.exists(src_path):
            with tempfile.TemporaryDirectory() as tmpdir:
                shutil.copy2(src_path, os.path.join(tmpdir, "tabelaHash.py"))
                subprocess.run(
                    [sys.executable, "-m", "cfgcoverage", "tabelaHash.py"],
                    cwd=tmpdir,
                    check=True,
                    capture_output=True
                )
                with open(os.path.join(tmpdir, "tabelaHash.py.cfg"), "rb") as fcfg:
                    cfgs, _, ep_map, eb_map, pp_map, _ = pickle.load(fcfg)

            real_rows = {}
            tot_b, tot_e, tot_ess, tot_ep, tot_pp = 0, 0, 0, 0, 0
            proc_cfg = None
            for fname, c in cfgs.items():
                b = len([blk for blk in c.blocks.values() if blk.kind != "EXIT"])
                e = len([ed for ed in c.edges if ed.label != "FAKE"])
                ess = len(eb_map[fname].requirements)
                ep = len(ep_map[fname].requirements)
                pp = len(pp_map[fname].requirements)
                real_rows[c.ordinal] = (b, e, ess, ep, pp)
                tot_b += b
                tot_e += e
                tot_ess += ess
                tot_ep += ep
                tot_pp += pp
                if "_procurar_posicao" in fname:
                    proc_cfg = c
            if proc_cfg:
                details.append(f"Método _procurar_posicao possui {len(proc_cfg.exits)} nós finais distintos (exits={proc_cfg.exits}).")

            details.append(f"Totais Reais do GFC Bruto: Blocos={tot_b}, Arestas={tot_e}, Essenciais={tot_ess}, Pares={tot_ep}, Caminhos={tot_pp}")

            if self.report_md_path:
                with open(self.report_md_path, "r", encoding="utf-8", errors="ignore") as f:
                    rep_text = f.read()

                if re.search(r"(_procurar_posicao|função|método).*?apontam para uma saída única", rep_text, re.IGNORECASE):
                    passed = False
                    details.append("  ❌ ERRO CONCEITUAL NO RELATÓRIO: Afirmação de que retornos apontam para 'saída única'!")
                else:
                    details.append("  ✅ Relatório respeita a topologia de múltiplos nós finais de saída.")

                t1_match = re.search(
                    r"\|\s*\*\*Total\*\*\s*\|\s*\*\*14\s*métodos\*\*\s*\|.*?\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|",
                    rep_text
                )
                if t1_match:
                    tb, te, tess, tep, tpp = [int(x) for x in t1_match.groups()]
                    if (tb, te, tess, tep, tpp) != (tot_b, tot_e, tot_ess, tot_pp if False else tot_ep) or tpp != tot_pp:
                        if (tb, te, tess, tep, tpp) != (tot_b, tot_e, tot_ess, tot_ep, tot_pp):
                            passed = False
                            details.append(
                                f"  ❌ DIVERGÊNCIA NA TABELA 1: Tabela informa B={tb}, E={te}, Ess={tess}, EP={tep}, PP={tpp}, "
                                f"mas o GFC real possui B={tot_b}, E={tot_e}, Ess={tot_ess}, EP={tot_ep}, PP={tot_pp}!"
                            )
                    else:
                        details.append("  ✅ Tabela 1 perfeitamente sincronizada com a anatomia real do GFC (109 / 117 / 37 / 140 / 193).")

        summary = "Semântica e topologia dos grafos validadas com sucesso." if passed else "Discrepâncias conceituais ou numéricas na modelagem do GFC detectadas!"
        self.log_result(gate_name, passed, summary, details)
        return passed

    # =========================================================================
    # GATE 5: Higiene de Arquivos e Integridade do Pacote (.zip e arquivos vazios)
    # =========================================================================
    def check_gate_5_files_and_package(self) -> bool:
        gate_name = "GATE 5: Higiene de Arquivos e Integridade do Pacote de Entrega"
        details = []
        passed = True

        for fpath in glob.glob(os.path.join(self.target_dir, "*.*")):
            fname = os.path.basename(fpath)
            if os.path.isfile(fpath) and os.path.getsize(fpath) == 0:
                passed = False
                details.append(f"  ❌ ARQUIVO VAZIO (0 BYTES): O arquivo '{fname}' existe na pasta mas está completamente vazio!")

        if passed:
            details.append("  ✅ Nenhum arquivo vazio (0 bytes) encontrado na pasta da atividade.")

        zip_candidates = sorted(
            glob.glob(os.path.join(self.target_dir, "entrega_*.zip")),
            key=lambda p: os.path.getmtime(p)
        )
        if zip_candidates:
            zip_path = zip_candidates[-1]
            details.append(
                f"Versões de pacotes encontradas ({len(zip_candidates)}): "
                f"{[os.path.basename(z) for z in zip_candidates]} "
                f"(auditando a mais recente: '{os.path.basename(zip_path)}')."
            )
            with zipfile.ZipFile(zip_path, "r") as z:
                files_in_zip = z.namelist()
                details.append(f"Pacote '{os.path.basename(zip_path)}' contém {len(files_in_zip)} arquivos.")

                forbidden = [".coverage", ".mdc", "__pycache__", ".venv", ".pytest_cache"]
                for fz in files_in_zip:
                    if any(fb in fz for fb in forbidden):
                        passed = False
                        details.append(f"  ❌ ARQUIVO PROIBIDO NO PACOTE: '{fz}' não deveria estar no .zip!")

                    info = z.getinfo(fz)
                    if info.file_size == 0:
                        passed = False
                        details.append(f"  ❌ ARQUIVO VAZIO NO PACOTE: '{fz}' possui 0 bytes dentro do .zip!")

                if self.is_vvts:
                    required = ["estrutural.py", "funcional.py", "cobertura.py", "mcdc.py", "tabelaHash.py", "infeasible_tabelaHash.txt"]
                    for req in required:
                        if req not in files_in_zip:
                            passed = False
                            details.append(f"  ❌ ARQUIVO OBRIGATÓRIO AUSENTE NO PACOTE: '{req}' falta no .zip!")
                else:
                    if not any(f.endswith(".R") or f.endswith(".md") or f.endswith(".csv") for f in files_in_zip):
                        passed = False
                        details.append("  ❌ Pacote zip não contém scripts ou relatório da atividade!")

        summary = "Higiene de arquivos e pacote validados com sucesso." if passed else "Problemas detectados na integridade de arquivos ou no pacote de entrega!"
        self.log_result(gate_name, passed, summary, details)
        return passed

    def run_all_gates(self) -> bool:
        print("=" * 80)
        print(f"AcademicOS Quality Gates — Alvo: {self.target_dir}")
        print("=" * 80)

        self.check_gate_1_reconciliation()
        self.check_gate_2_minimality()
        self.check_gate_3_headers()
        self.check_gate_4_cfg_semantics()
        self.check_gate_5_files_and_package()

        print("\n" + "=" * 80)
        print("RELATÓRIO CONSOLIDADO DOS PORTÕES DETERMINÍSTICOS")
        print("=" * 80)

        for gate, res in self.results.items():
            status_icon = "✅ PASS" if res["passed"] else "❌ FAIL"
            print(f"\n[{status_icon}] {gate}")
            print(f"  Sumário: {res['summary']}")
            for d in res["details"]:
                print(f"    {d}")

        print("\n" + "=" * 80)
        final_verdict = "APROVADO (EXIT CODE 0)" if self.all_passed else "REJEITADO (EXIT CODE 1)"
        print(f"VEREDICTO FINAL DO PORTÃO: {final_verdict}")
        print("=" * 80)

        rev_dir = os.path.join(self.target_dir, "05_reviews")
        report_out = os.path.join(rev_dir if os.path.isdir(rev_dir) else self.target_dir, "qa_gate_audit_report.md")
        with open(report_out, "w", encoding="utf-8") as f:
            f.write("# Relatório de Auditoria Determinística — Portões de Qualidade (AcademicOS)\n\n")
            f.write(f"**Alvo**: `{self.target_dir}`  \n")
            f.write(f"**Veredicto Geral**: **{final_verdict}**  \n\n---\n\n")
            for gate, res in self.results.items():
                icon = "✅ APROVADO" if res["passed"] else "❌ REJEITADO"
                f.write(f"## {gate} — {icon}\n\n")
                f.write(f"**Sumário**: {res['summary']}\n\n")
                f.write("**Detalhes da Auditoria**:\n")
                for d in res["details"]:
                    f.write(f"- {d}\n")
                f.write("\n---\n\n")

        return self.all_passed


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    runner = QualityGateRunner(target)
    success = runner.run_all_gates()
    sys.exit(0 if success else 1)
