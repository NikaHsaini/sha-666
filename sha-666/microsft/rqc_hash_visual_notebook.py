
# rqc_hash_visual_notebook.py
# Notebook-like script to build RQC-Hash with Qiskit, visualize circuit and histogram.
# Run: python rqc_hash_visual_notebook.py
from qiskit import QuantumCircuit, Aer, transpile
from qiskit.visualization import plot_histogram, circuit_drawer
import matplotlib.pyplot as plt
import numpy as np
import math
import argparse

def build_random_circuit(n_qubits, depth, seed):
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n_qubits, n_qubits)
    for layer in range(depth):
        for q in range(n_qubits):
            theta = float(rng.random() * 2 * math.pi)
            phi = float(rng.random() * 2 * math.pi)
            qc.rz(phi, q)
            qc.rx(theta, q)
        for q in range(0, n_qubits-1, 2):
            qc.cx(q, q+1)
        for q in range(1, n_qubits-1, 2):
            qc.cx(q, q+1)
        if n_qubits > 2:
            qc.cx(n_qubits-1, 0)
    return qc

def encode_message(msg_bytes, n_qubits):
    qc = QuantumCircuit(n_qubits, n_qubits)
    bits = []
    for b in msg_bytes:
        for i in range(8):
            bits.append((b >> i) & 1)
    for i, bit in enumerate(bits):
        if i >= n_qubits: break
        if bit:
            qc.x(i)
    return qc

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", "-m", default="hello")
    parser.add_argument("--n", type=int, default=12)
    parser.add_argument("--d", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--shots", type=int, default=1024)
    args = parser.parse_args()

    msg = args.message.encode("utf-8")
    n = args.n; d = args.d; s = args.seed; shots = args.shots

    enc = encode_message(msg, n)
    rqc = build_random_circuit(n, d, s)
    qc = QuantumCircuit(n, n)
    qc.compose(enc, inplace=True)
    qc.compose(rqc, inplace=True)
    qc.measure(range(n), range(n))

    # draw circuit to file
    drawer = circuit_drawer(qc, output='mpl', fold=100)
    drawer.savefig("/mnt/data/rqc_circuit.png", bbox_inches='tight')
    print("Saved circuit diagram to /mnt/data/rqc_circuit.png")

    backend = Aer.get_backend("aer_simulator")
    tqc = transpile(qc, backend, optimization_level=1)
    job = backend.run(tqc, shots=shots)
    result = job.result()
    counts = result.get_counts()
    # plot histogram and save
    fig = plot_histogram(counts)
    fig.savefig("/mnt/data/rqc_histogram.png", bbox_inches='tight')
    print("Saved histogram to /mnt/data/rqc_histogram.png")
    # Also print top 8 results
    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:8]
    print("Top results:")
    for k,v in top:
        print(k, v)

if __name__ == '__main__':
    main()
