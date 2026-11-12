"""
build_notebook.py - Gera e pré-executa o Jupyter Notebook pedagógico da Aula 02.
Garante correspondência 1:1 com os 46 slides, Qiskit 2.x Primitives V2 e pré-renderização de outputs.
"""
import os
import sys
import json
import io
import base64
import contextlib
import numpy as np

# Configura matplotlib para backend headless não-bloqueante
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def make_cell_markdown(source, cell_id):
    lines = [l + "\n" for l in source.strip().split("\n")]
    if lines:
        lines[-1] = lines[-1].rstrip("\n")
    return {
        "cell_type": "markdown",
        "id": cell_id,
        "metadata": {},
        "source": lines,
    }

def make_cell_code(source, cell_id, outputs=None, exec_count=None):
    lines = [l + "\n" for l in source.strip().split("\n")]
    if lines:
        lines[-1] = lines[-1].rstrip("\n")
    return {
        "cell_type": "code",
        "execution_count": exec_count,
        "id": cell_id,
        "metadata": {},
        "outputs": outputs or [],
        "source": lines,
    }

def main():
    print("=== CONSTRUINDO E PRÉ-EXECUTANDO JUPYTER NOTEBOOK DA AULA 02 ===")
    
    cells_spec = [
        # 0
        ("md", """# Qiskit Fall Fest 2026 · Aula 02: Introdução a Circuitos Quânticos
### **Instrutor:** <NOME_DO_ESTUDANTE>
*Pesquisador em Quantum Machine Learning & IA Aplicada | Deep Learning · Otimização Combinatória · HPC & Cloud*

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/)

---

> **Bem-vindo(a) ao laboratório prático da Aula 02!**  
> Este notebook acompanha passo a passo os slides da apresentação. Aqui você construirá, visualizará e simulará circuitos quânticos no **Qiskit 2.x**, explorará algoritmos clássicos, simulará ruído de hardware real e resolverá problemas de otimização combinatória com **VQE** e **QAOA**.
>
> 🌐 **Conecte-se e acompanhe pesquisas:**
> - [LinkedIn: linkedin.com/in/marcos-vinicius-reballo](https://www.linkedin.com/in/marcos-vinicius-reballo/)
> - Aplicações práticas em **Otimização de Portfólio, Detecção de Fraudes, Logística e Algoritmos Quânticos Híbridos**.

---

### Sumário da Aula Prática:
1. **Instalação e Ambiente**
2. **Portas Lógicas de 1 e 2 Qubits e Convenção Little-Endian**
3. **Anatomia do Circuito e Primitives V2 (Sampler e Estimator)**
4. **Circuitos Clássicos da Literatura (Bell, GHZ, Teletransporte, Bernstein-Vazirani, Grover)**
5. **Hardware Real e QEC: Transpilação, Ruído e Código de Repetição**
6. **Circuitos Variacionais: ParameterVector, VQE e QAOA na Prática**"""),

        # 1
        ("code", """# [Passo 0] Instalação do Qiskit 2.x e pacotes auxiliares no Colab
!pip install -q "qiskit>=2.0" "qiskit[visualization]" qiskit-ibm-runtime qiskit-aer pylatexenc matplotlib scipy networkx

import qiskit
print(f"Versão do Qiskit SDK instalada: {qiskit.__version__}")"""),

        # 2
        ("md", """## 1. Portas Lógicas de 1 e 2 Qubits e a Convenção Little-Endian (Slides 06 a 11)

Relembrando a fundamentação teórica:
- Portas de 1 qubit ($X, Y, Z, H, R_Y$) são matrizes unitárias $2 \\times 2$ que preservam a norma ($U^\\dagger U = I$).
- A porta **Hadamard ($H$)** cria superposição simétrica a partir da base computacional:
  $$H|0\\rangle = |+\\rangle = \\frac{|0\\rangle + |1\\rangle}{\\sqrt{2}}, \\quad H|1\\rangle = |-\\rangle = \\frac{|0\\rangle - |1\\rangle}{\\sqrt{2}}$$
- A porta **CNOT ($CX$)** aplica $X$ no alvo se o controle estiver em $|1\\rangle$.
- **Atenção à convenção Little-Endian do Qiskit:** o qubit 0 é o bit menos significativo (mais à direita): $|q_1 q_0\\rangle$."""),

        # 3
        ("code", """import numpy as np
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit
from qiskit.visualization import plot_bloch_multivector
from qiskit.quantum_info import Statevector

# [Slide 06 & 08] Criando superposição com a porta Hadamard
qc_h = QuantumCircuit(1)
qc_h.h(0)

# Vetor de estado exato |+>
sv_plus = Statevector(qc_h)
print("Vetor de estado |+>:")
print(sv_plus)

# Visualização na Esfera de Bloch (apontando para o eixo +X)
plot_bloch_multivector(sv_plus)"""),

        # 4
        ("code", """# [Slide 10] A pegadinha do Little-Endian no Qiskit: ordem |q1 q0>
qc_le = QuantumCircuit(2)
qc_le.x(0)  # Coloca q0 em |1> (estado global |01>)
qc_le.cx(0, 1)  # Controle em q0, alvo em q1 -> inverte q1 -> vira |11>

sv_le = Statevector(qc_le)
print("Circuito com q0=1 controlando q1:")
print("Estado final:", sv_le.to_dict())
print(qc_le.draw("text"))"""),

        # 5
        ("md", """## 2. Anatomia de um Circuito no Qiskit 2.x e Primitives V2 (Slides 13 a 15)

No Qiskit 2.x, a API antiga `execute()` foi substituída pela arquitetura de **Primitives V2**:
- `StatevectorSampler`: para obter distribuições probabilísticas e contagens de disparos (*shots*);
- `StatevectorEstimator`: para calcular valores médios de observáveis físicos $\\langle H \\rangle$."""),

        # 6
        ("code", """# [Slide 14 & 15] Nosso primeiro circuito medido com Primitives V2
from qiskit.primitives import StatevectorSampler
from qiskit.visualization import plot_histogram

qc_primeiro = QuantumCircuit(1)
qc_primeiro.h(0)
qc_primeiro.measure_all()

# Executando 1000 shots com StatevectorSampler V2
sampler = StatevectorSampler()
job = sampler.run([(qc_primeiro,)], shots=1000)
result = job.result()[0]

counts = result.data.meas.get_counts()
print("Contagens empíricas (1000 shots):", counts)
plot_histogram(counts, title="Hadamard: 1000 shots no Sampler V2")"""),

        # 7
        ("md", """## 3. Circuitos Clássicos da Literatura Quântica (Slides 16 a 22)

Vamos construir e executar os circuitos fundamentais que formam a espinha dorsal da informação quântica:
1. **Estado de Bell ($|\\Phi^+\\rangle$):** entrelaçamento máximo de 2 qubits;
2. **Estado GHZ:** generalização para $n$ qubits e análise de profundidade;
3. **Teletransporte Quântico:** transmissão de estado quântico via entrelaçamento e medições dinâmicas;
4. **Algoritmo de Bernstein-Vazirani:** vantagem quântica em consultas ao oráculo;
5. **Algoritmo de Grover:** aceleração quadrática de busca desestruturada ($\mathcal{O}(\\sqrt{N})$)."""),

        # 8
        ("code", """# [Slide 17] Estado de Bell |Phi+> = (|00> + |11>) / sqrt(2)
qc_bell = QuantumCircuit(2)
qc_bell.h(0)
qc_bell.cx(0, 1)
qc_bell.measure_all()

job_bell = sampler.run([(qc_bell,)], shots=1024)
counts_bell = job_bell.result()[0].data.meas.get_counts()

print("Estado de Bell (1024 shots):", counts_bell)
print(qc_bell.draw("text"))
plot_histogram(counts_bell, title="Estado de Bell Ideal: apenas '00' e '11'")"""),

        # 9
        ("code", """# [Slide 18] Estado GHZ de 3 qubits: (|000> + |111>) / sqrt(2)
qc_ghz = QuantumCircuit(3)
qc_ghz.h(0)
qc_ghz.cx(0, 1)
qc_ghz.cx(1, 2)
qc_ghz.measure_all()

job_ghz = sampler.run([(qc_ghz,)], shots=1000)
counts_ghz = job_ghz.result()[0].data.meas.get_counts()

print("Estado GHZ de 3 qubits (1000 shots):", counts_ghz)
print(qc_ghz.draw("text"))
plot_histogram(counts_ghz, title="Estado GHZ: correlação perfeita entre 3 qubits")"""),

        # 10
        ("code", """# [Slide 19] Teletransporte Quântico com Circuitos Dinâmicos
qc_teleport = QuantumCircuit(3, 2)
# 1. Prepara estado a enviar no qubit 0 (rotação parametrizada)
qc_teleport.ry(1.2, 0)
qc_teleport.barrier()

# 2. Cria par de Bell entre Alice (q1) e Bob (q2)
qc_teleport.h(1)
qc_teleport.cx(1, 2)
qc_teleport.barrier()

# 3. Alice realiza medição na base de Bell (q0 e q1)
qc_teleport.cx(0, 1)
qc_teleport.h(0)
qc_teleport.measure(0, 0)
qc_teleport.measure(1, 1)
qc_teleport.barrier()

# 4. Bob aplica correções clássicas condicionadas (X e Z)
qc_teleport.cx(1, 2)
qc_teleport.cz(0, 2)

print("Circuito de Teletransporte Quântico:")
print(qc_teleport.draw("text"))"""),

        # 11
        ("code", """# [Slide 20] Algoritmo de Bernstein-Vazirani: decodificando string s em 1 consulta
segredo = "1011"
n = len(segredo)

qc_bv = QuantumCircuit(n + 1, n)
# Prepara ancilla no estado |->
qc_bv.x(n)
qc_bv.h(range(n + 1))
qc_bv.barrier()

# Oráculo linear f(x) = s · x mod 2
for idx, bit in enumerate(reversed(segredo)):
    if bit == "1":
        qc_bv.cx(idx, n)
qc_bv.barrier()

# Interferência e medição
qc_bv.h(range(n))
qc_bv.measure(range(n), range(n))

job_bv = sampler.run([(qc_bv,)], shots=100)
counts_bv = job_bv.result()[0].data.c.get_counts()
decodificado = list(counts_bv.keys())[0]

print(f"Chave secreta configurada: {segredo}")
print(f"Chave decodificada pelo algoritmo: {decodificado}")
assert decodificado == segredo, "A chave decodificada deve coincidir com o segredo!"
print(qc_bv.draw("text"))"""),

        # 12
        ("code", """# [Slide 21] Algoritmo de Grover (2 Qubits): localizando o estado marcado |11>
qc_grover = QuantumCircuit(2)
qc_grover.h([0, 1])

# Oráculo de fase que inverte o sinal do estado |11>
qc_grover.cz(0, 1)

# Operador Difusor de Grover (inversão em torno da média)
qc_grover.h([0, 1])
qc_grover.x([0, 1])
qc_grover.cz(0, 1)
qc_grover.x([0, 1])
qc_grover.h([0, 1])
qc_grover.measure_all()

job_gr = sampler.run([(qc_grover,)], shots=1024)
counts_gr = job_gr.result()[0].data.meas.get_counts()

print("Contagens de Grover (1024 shots):", counts_gr)
print(qc_grover.draw("text"))
plot_histogram(counts_gr, title="Grover: 100% de probabilidade no alvo |11> com 1 iteração")"""),

        # 13
        ("md", """## 4. Choque de Realidade: Hardware Ruidoso (NISQ) e Código de Repetição (Slides 24 a 30)

No mundo real dos supercondutores (ex.: IBM Heron):
- Qubits físicos sofrem relaxação energética ($T_1 \\sim 100\\,\\mu\\text{s}$) e desfasamento ($T_2 \\sim 80\\,\\mu\\text{s}$).
- Erros de porta de 2 qubits ($CX$) acumulam-se rapidamente.
- O compilador (`generate_preset_pass_manager`) adapta o circuito à topologia real do chip."""),

        # 14
        ("code", """# [Slide 26] Simulando o Estado de Bell com ruído realístico calibrado
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

# Instancia backend simulador ruidoso de 5 qubits
backend_ruidoso = GenericBackendV2(num_qubits=5, seed=42)

# Transpilação do circuito para as portas nativas e acoplamento do chip
pm = generate_preset_pass_manager(optimization_level=1, backend=backend_ruidoso)
qc_transpilado = pm.run(qc_bell)

# Execução no backend ruidoso
job_ruidoso = backend_ruidoso.run(qc_transpilado, shots=1024)
counts_ruidoso = job_ruidoso.result().get_counts()

print("Ideal:", counts_bell)
print("Com ruído físico realístico:", counts_ruidoso)
plot_histogram([counts_bell, counts_ruidoso], legend=["Ideal (Statevector)", "Hardware Ruidoso (GenericBackendV2)"],
               title="Comparativo: Ideal vs Hardware Ruidoso")"""),

        # 15
        ("code", """# [Slide 27] Template para execução em QPU Real da IBM Quantum
# Defina RODAR_NA_QPU_REAL = True e insira seu token caso possua acesso
RODAR_NA_QPU_REAL = False

if RODAR_NA_QPU_REAL:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    service = QiskitRuntimeService(channel="ibm_quantum", token="SEU_TOKEN_AQUI")
    backend_real = service.least_busy(operational=True, simulator=False)
    print(f"Backend real selecionado: {backend_real.name}")
    
    pm_real = generate_preset_pass_manager(optimization_level=1, backend=backend_real)
    qc_hw = pm_real.run(qc_bell)
    sampler_hw = SamplerV2(backend=backend_real)
    job_hw = sampler_hw.run([(qc_hw,)], shots=1024)
    print(f"Job enviado com sucesso! ID: {job_hw.job_id()}")
else:
    print("Modo de segurança ativo: utilize simulação ruidosa local para evitar filas na transmissão ao vivo.")"""),

        # 16
        ("code", """# [Slide 28] Protegendo a Informação: Código de Repetição de 3 Qubits
# Demonstração: injetamos um erro de bit-flip no qubit 1 e detectamos via ancillas!
qc_qec = QuantumCircuit(5, 2)
# q0, q1, q2: qubits de dados | q3, q4: ancillas de síndrome

# 1. Codificação do qubit lógico: |0_L> = |000>
# 2. Injeção de erro simulado (bit-flip no qubit 1):
qc_qec.x(1)
qc_qec.barrier()

# 3. Medição de síndrome de paridade: Z0 Z1 e Z1 Z2
qc_qec.cx(0, 3)
qc_qec.cx(1, 3)
qc_qec.cx(1, 4)
qc_qec.cx(2, 4)
qc_qec.measure(3, 0)
qc_qec.measure(4, 1)

# Simulação da síndrome
res_qec = sampler.run([(qc_qec,)], shots=100).result()[0].data.c.get_counts()
print("Síndrome medida (bits clássicos c1 c0):", res_qec)
print("Interpretação: síndrome '11' aponta erro no qubit 1!")
print(qc_qec.draw("text"))"""),

        # 17
        ("md", """## 5. Circuitos Variacionais e Otimização Híbrida HPC (Slides 32 a 40)

Algoritmos Quânticos Variacionais (**VQAs**) combinam circuitos quânticos curtos e parametrizados na QPU com laços de descida de gradiente em computadores clássicos (HPC/CPUs).
- **VQE (Variational Quantum Eigensolver):** minimiza o valor esperado da energia $\\langle \\psi(\\theta) | H | \\psi(\\theta) \\rangle \\geq E_0$;
- **QAOA (Quantum Approximate Optimization Algorithm):** resolve problemas de otimização combinatória (MaxCut/QUBO) mapeados para Hamiltonianos de Ising."""),

        # 18
        ("code", """# [Slide 34] Circuitos Parametrizados no Qiskit com ParameterVector
from qiskit.circuit import ParameterVector

# Criando 4 parâmetros treináveis θ
theta = ParameterVector("θ", 4)
ansatz_demo = QuantumCircuit(2)
ansatz_demo.ry(theta[0], 0)
ansatz_demo.ry(theta[1], 1)
ansatz_demo.cx(0, 1)
ansatz_demo.ry(theta[2], 0)
ansatz_demo.ry(theta[3], 1)

print("Circuito Parametrizado (Ansatz):")
print(ansatz_demo.draw("text"))

# Atribuição numérica de valores reais
valores = [np.pi/4, np.pi/2, 0.0, np.pi]
circuito_atribuido = ansatz_demo.assign_parameters(valores)
print("\\nCircuito após assign_parameters:")
print(circuito_atribuido.draw("text"))"""),

        # 19
        ("code", """# [Slide 36] VQE Completo no Qiskit 2.x com EstimatorV2 e COBYLA
from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp
from scipy.optimize import minimize

# Hamiltoniano da molécula H2 (distância de ligação interatômica 0.735 Å)
H_mol = SparsePauliOp.from_list([
    ("II", -1.05),
    ("IZ", 0.39),
    ("ZI", -0.39),
    ("ZZ", -0.01),
    ("XX", 0.18)
])
E0_exato = float(np.min(np.linalg.eigvalsh(H_mol.to_matrix())))
print(f"Autovalor exato do estado fundamental (FCI): {E0_exato:.4f} Hartree")

estimator = StatevectorEstimator()
historico_vqe = []

def custo_vqe(params):
    job = estimator.run([(ansatz_demo, H_mol, params)])
    val = float(job.result()[0].data.evs)
    historico_vqe.append(val)
    return val

# Otimização com algoritmo clássico COBYLA
p0 = [0.1, 0.2, 0.3, 0.4]
res_vqe = minimize(custo_vqe, p0, method="COBYLA", options={"maxiter": 40})

print(f"Energia convergida pelo VQE: {res_vqe.fun:.4f} Hartree")
print(f"Erro em relação ao exato: {abs(res_vqe.fun - E0_exato):.6f} Hartree")

# Gráfico de Convergência
plt.figure(figsize=(8, 4.5))
plt.plot(historico_vqe, "o-", color="#0F62FE", lw=2, label="VQE (COBYLA)")
plt.axhline(E0_exato, color="#D02670", ls="--", lw=2, label=f"Exato: {E0_exato:.4f} Ha")
plt.title("Convergência do VQE - Molécula H₂ (Qiskit 2.x)", fontsize=13, fontweight="bold")
plt.xlabel("Iteração Clássica", fontsize=11)
plt.ylabel("Energia ⟨H⟩ (Hartree)", fontsize=11)
plt.grid(True, alpha=0.3)
plt.legend(frameon=False)
plt.show()"""),

        # 20
        ("code", """# [Slide 38] QAOA Aplicado a Problemas Reais de Logística e Alocação de Risco
import networkx as nx
from qiskit.circuit.library import QAOAAnsatz

# Grafo de 4 nós representando nós de distribuição ou ativos financeiros
G = nx.cycle_graph(4)
pesos = {(0, 1): 1.0, (1, 2): 2.0, (2, 3): 1.0, (3, 0): 2.0}

# Mapeamento QUBO -> Hamiltoniano de Ising: 0.5 * w_ij * (I - Zi Zj)
termos_pauli = []
for (u, v), w in pesos.items():
    z_str = ["I"] * 4
    z_str[u] = "Z"
    z_str[v] = "Z"
    termos_pauli.append(("".join(z_str), 0.5 * w))
H_custo = SparsePauliOp.from_list(termos_pauli)

# Criação do ansatz QAOA com profundidade p=2
qaoa_circ = QAOAAnsatz(cost_operator=H_custo, reps=2)
qaoa_circ.measure_all()

def perda_qaoa(params):
    job = sampler.run([(qaoa_circ.assign_parameters(params),)], shots=1024)
    counts = job.result()[0].data.meas.get_counts()
    corte_medio = sum((n / 1024.0) * sum(w for (u, v), w in pesos.items() if b[3-u] != b[3-v])
                      for b, n in counts.items())
    return -corte_medio  # Minimizar negativo = Maximizar o corte

res_qaoa = minimize(perda_qaoa, [0.5]*4, method="COBYLA", options={"maxiter": 35})
circ_otimo = qaoa_circ.assign_parameters(res_qaoa.x)

contagens_qaoa = sampler.run([(circ_otimo,)], shots=1024).result()[0].data.meas.get_counts()
top_solucoes = sorted(contagens_qaoa.items(), key=lambda kv: kv[1], reverse=True)[:6]
print("Top 6 partições mais prováveis encontradas pelo QAOA:", top_solucoes)
print("Partições ótimas esperadas (MaxCut): '0101' e '1010'!")

plot_histogram(contagens_qaoa, title="QAOA (p=2): Amostragem das Partições da Rede Logística")"""),

        # 21
        ("md", """---
## 6. Próximos Passos & Hackathon (Slides 42 a 46)

Parabéns por concluir o laboratório prático da Aula 02!

### 💡 4 Recomendações para o seu Projeto no Hackathon:
1. **Use Primitives V2:** `StatevectorSampler` e `StatevectorEstimator` para prototipagem rápida e `SamplerV2`/`EstimatorV2` para hardware real.
2. **Considere o Ruído:** Sempre transpile seus circuitos com `generate_preset_pass_manager` e teste em simulador ruidoso antes de enviar para fila de hardware.
3. **Mantenha Circuitos Curtos:** Em chips NISQ, profundidade é o recurso mais escasso.
4. **Modele Problemas Reais:** Use QUBO/Ising para logística, finanças e otimização de portfólio.

---

### 📝 Check-in Final:
- Não se esqueça de preencher o **Forms Pós-Aula** para computar sua presença e mensurar seu ganho de aprendizado!
- **Conecte-se com o instrutor:** [linkedin.com/in/marcos-vinicius-reballo](https://www.linkedin.com/in/marcos-vinicius-reballo/)""")
    ]

    exec_globals = {"plt": plt}
    cells_json = []
    cell_counter = 0

    # Sobrescreve plt.show para não travar
    def mock_show():
        pass
    plt.show = mock_show

    for kind, content in cells_spec:
        cell_id = f"cell_{cell_counter:03d}"
        cell_counter += 1
        if kind == "md":
            cells_json.append(make_cell_markdown(content, cell_id))
        else:
            # Executa código e captura stdout
            lines = [l for l in content.split("\n") if not l.strip().startswith("!")]
            code = "\n".join(lines)
            
            buf_out = io.StringIO()
            outputs = []
            
            # Limpa figuras anteriores
            plt.close("all")
            
            with contextlib.redirect_stdout(buf_out):
                try:
                    exec(code, exec_globals)
                except Exception as e:
                    print(f"ERRO na execução da célula {cell_id}:\n{e}")
                    raise e
                    
            stdout_text = buf_out.getvalue()
            if stdout_text:
                outputs.append({
                    "name": "stdout",
                    "output_type": "stream",
                    "text": [l + "\n" for l in stdout_text.rstrip("\n").split("\n")]
                })
                
            # Captura figuras matplotlib geradas pela célula se houver
            figs = [plt.figure(n) for n in plt.get_fignums()]
            for f in figs:
                img_buf = io.BytesIO()
                f.savefig(img_buf, format="png", bbox_inches="tight", dpi=130)
                img_buf.seek(0)
                b64 = base64.b64encode(img_buf.read()).decode("utf-8")
                outputs.append({
                    "data": {
                        "image/png": b64,
                        "text/plain": ["<Figure size ...>"]
                    },
                    "metadata": {},
                    "output_type": "display_data"
                })
                plt.close(f)
                
            cells_json.append(make_cell_code(content, cell_id, outputs=outputs, exec_count=cell_counter))
            print(f"  [OK] Executada {cell_id} ({len(outputs)} outputs)")

    notebook = {
        "cells": cells_json,
        "metadata": {
            "colab": {
                "name": "Aula 02 - Introdução a Circuitos Quânticos - Qiskit Fall Fest 2026",
                "provenance": [],
                "toc_visible": True,
            },
            "language_info": {
                "name": "python",
                "version": sys.version.split()[0],
            },
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    out_paths = [
        "AULAS_SEMANA_1/aula02/aula02_codigo.ipynb",
        "studio/jobs/2026-11-05_qff-aula02-circuitos/build/aula02_codigo.ipynb",
    ]
    for p in out_paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(notebook, f, ensure_ascii=False, indent=1)
        print(f"-> Salvo com sucesso: {p} ({os.path.getsize(p)} bytes)")

    print("=== NOTEBOOK DA AULA 02 GERADO E VALIDADO COM SUCESSO! ===")

if __name__ == "__main__":
    main()

