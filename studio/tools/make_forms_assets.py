"""
make_forms_assets.py - Gera imagens LaTeX em alta resolução para o Google Forms.
Cria tanto imagens individuais para cada alternativa quanto um card completo da questão.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def render_math(text, filename, out_dir, fontsize=28, figsize=(3.5, 1.2), dpi=250, transparent=False, bg="#FFFFFF"):
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)
    ax.text(0.5, 0.5, f"${text}$", fontsize=fontsize, ha="center", va="center", color="#161616")
    ax.axis("off")
    path = os.path.join(out_dir, filename)
    fig.savefig(path, bbox_inches="tight", dpi=dpi, transparent=transparent, facecolor=bg)
    plt.close(fig)
    print(f"   [OK] {filename} -> {path}")
    return path

def main():
    out_dir = os.path.abspath("AULAS_SEMANA_1/aula02/assets_forms")
    os.makedirs(out_dir, exist_ok=True)
    print("=== GERANDO IMAGENS LATEX PARA O GOOGLE FORMS ===")
    
    # 1. Alternativas individuais com raízes e bra-kets (fundo branco para bater com o Forms)
    # Opção B (Correta)
    render_math(r"\frac{|0\rangle + |1\rangle}{\sqrt{2}}", "opcao_B_raiz.png", out_dir, fontsize=28, figsize=(3.2, 1.2))
    render_math(r"|+\rangle = \frac{|0\rangle + |1\rangle}{\sqrt{2}}", "opcao_B_completa.png", out_dir, fontsize=26, figsize=(4.2, 1.2))

    # Opção C
    render_math(r"\frac{|0\rangle - |1\rangle}{\sqrt{2}}", "opcao_C_raiz.png", out_dir, fontsize=28, figsize=(3.2, 1.2))
    render_math(r"|-\rangle = \frac{|0\rangle - |1\rangle}{\sqrt{2}}", "opcao_C_completa.png", out_dir, fontsize=26, figsize=(4.2, 1.2))

    # Opção A
    render_math(r"|1\rangle", "opcao_A_ket1.png", out_dir, fontsize=28, figsize=(2.0, 1.0))

    # Opção D (para quem deseja padronizar imagem em todas as 4 alternativas)
    fig_d, ax_d = plt.subplots(figsize=(6.5, 1.0))
    fig_d.patch.set_facecolor("#FFFFFF")
    ax_d.set_facecolor("#FFFFFF")
    ax_d.text(0.5, 0.5, "Estado clássico aleatório 0 ou 1 (irreversível)", fontsize=18, ha="center", va="center", color="#161616")
    ax_d.axis("off")
    fig_d.savefig(os.path.join(out_dir, "opcao_D_classico.png"), bbox_inches="tight", dpi=250, facecolor="#FFFFFF")
    plt.close(fig_d)
    print(f"   [OK] opcao_D_classico.png -> {os.path.join(out_dir, 'opcao_D_classico.png')}")

    # 2. Card Completo da Questão (caso prefira inserir uma imagem única na pergunta do Forms)
    fig, ax = plt.subplots(figsize=(8.0, 3.2))
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    ax.axis("off")

    ax.text(0.04, 0.90, r"Ao aplicar uma porta Hadamard ($H$) em um qubit no estado inicial $|0\rangle$,",
            fontsize=15, color="#161616", va="top")
    ax.text(0.04, 0.77, r"qual é o estado quântico resultante?", fontsize=15, color="#161616", va="top")

    ax.plot([0.04, 0.96], [0.66, 0.66], color="#E0E0E0", lw=1.5)

    ax.text(0.06, 0.52, r"(A)   $|1\rangle$", fontsize=16, color="#161616", va="center")
    ax.text(0.06, 0.36, r"(B)   $\frac{|0\rangle + |1\rangle}{\sqrt{2}}$   (ou $|+\rangle$)", fontsize=17, color="#0F62FE", fontweight="bold", va="center")
    ax.text(0.06, 0.20, r"(C)   $\frac{|0\rangle - |1\rangle}{\sqrt{2}}$   (ou $|-\rangle$)", fontsize=17, color="#161616", va="center")
    ax.text(0.06, 0.05, r"(D)   Um estado clássico aleatório 0 ou 1 irreversível", fontsize=13.5, color="#525252", va="center")
    
    # Salva o card da questão
    path_card = os.path.join(out_dir, "questao_hadamard_card_completo.png")
    fig.savefig(path_card, bbox_inches="tight", dpi=250, facecolor="#FFFFFF")
    plt.close(fig)
    print(f"   [OK] questao_hadamard_card_completo.png -> {path_card}")
    
    print("\n=== TODAS AS IMAGENS FORAM GERADAS COM SUCESSO! ===")

if __name__ == "__main__":
    main()
