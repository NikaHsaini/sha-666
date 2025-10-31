
# rqc_hash_ibm.py
# Final IBM-ready RQC-Hash (Random Quantum Circuit Hash)
# -----------------------------------------------
# Features:
# - Works with IBM Quantum hardware (via qiskit-ibm-provider or qiskit-ibm-runtime)
# - Also works with Aer simulator as fallback
# - Deterministic random circuit from --seed
# - Message encoding into first qubits
# - Returns most frequent bitstring and its hex form (LSB-first integer)
#
# Usage examples:
#   Aer simulator:
#     python rqc_hash_ibm.py --message "hello" --n 8 --d 6 --seed 42 --shots 2048
#
#   IBM hardware (Provider):
#     export QISKIT_IBM_TOKEN=<your_token>  # or IBMProvider.save_account() once
#     python rqc_hash_ibm.py --backend ibm_osaka --message "hello" --n 5 --d 6 --shots 2048
#
#   IBM Runtime (Cloud):
#     export QISKIT_IBM_TOKEN=<your_token>
#     python rqc_hash_ibm.py --backend ibm_brisbane --runtime cloud --n 5 --d 6 --shots 4096 --resilience 1
#
# Notes:
# - For real hardware, keep n and d modest (e.g., n<=5..7, d<=6..12) to fit depth and error rates.
# - Increase --shots for more stable statistics. Use --resilience 1..3 for runtime error mitigation (if using runtime).
#
import argparse
import math
import json
from typing import Dict, Tuple

import numpy as np

from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import RXGate, RZGate
from qiskit.quantum_info import Statevector

# Optional backends
_backend_mode = None
try:
    from qiskit_ibm_provider import IBMProvider  # Legacy/Provider path
    _backend_mode = "provider"
except Exception:
    pass

_runtime_available = False
try:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler, Session, Options
    _runtime_available = True
except Exception:
    pass

# Aer fallback
try:
    from qiskit_aer import Aer
    _aer_available = True
except Exception:
    _aer_available = False


def build_random_circuit(n_qubits: int, depth: int, seed: int, message: bytes) -> QuantumCircuit:
    """
    Build an RQC-Hash circuit:
      1) Encode message bits into first qubits (X if bit==1)
      2) Depth layers: [RZ, RX random angles] + entangling CX pattern
      3) Measure all
    """
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n_qubits, n_qubits, name=f"RQC(n={n_qubits},d={depth},seed={seed})")

    # 1) Encode message (LSB-first per byte)
    bit_idx = 0
    for b in message:
        for i in range(8):
            if bit_idx >= n_qubits:
                break
            if ((b >> i) & 1) == 1:
                qc.x(bit_idx)
            bit_idx += 1

    # 2) Random layers
    for _ in range(depth):
        # single-qubit random rotations
        for q in range(n_qubits):
            theta = float(rng.random() * 2 * math.pi)
            phi   = float(rng.random() * 2 * math.pi)
            qc.rz(phi, q)
            qc.rx(theta, q)
        # entangling CX: even pairs then odd pairs + wrap-around
        for q in range(0, n_qubits - 1, 2):
            qc.cx(q, q + 1)
        for q in range(1, n_qubits - 1, 2):
            qc.cx(q, q + 1)
        if n_qubits > 2:
            qc.cx(n_qubits - 1, 0)

    # 3) Measure all
    qc.measure(range(n_qubits), range(n_qubits))
    return qc


def most_frequent_bitstring(counts: Dict[str, int]) -> str:
    return max(counts.items(), key=lambda kv: kv[1])[0] if counts else ""


def to_hash_hex(bitstr_msb_lsb: str, n_qubits: int) -> str:
    # Convert Qiskit-format bitstring (MSB..LSB) to integer interpreting LSB-first.
    if not bitstr_msb_lsb:
        return ""
    val = int(bitstr_msb_lsb[::-1], 2)
    return f"{val:0{math.ceil(n_qubits/4)}x}"


def run_on_aer(qc: QuantumCircuit, shots: int) -> Dict[str, int]:
    if not _aer_available:
        raise RuntimeError("Aer not available. Install with: pip install qiskit-aer")
    backend = Aer.get_backend("aer_simulator")
    tqc = transpile(qc, backend, optimization_level=1)
    result = backend.run(tqc, shots=shots).result()
    return result.get_counts()


def run_on_ibm_provider(qc: QuantumCircuit, backend_name: str, shots: int) -> Dict[str, int]:
    provider = IBMProvider()
    backend = provider.get_backend(backend_name)
    tqc = transpile(qc, backend, optimization_level=3)
    job = backend.run(tqc, shots=shots)
    res = job.result()
    return res.get_counts()


def run_on_ibm_runtime(qc: QuantumCircuit, backend_name: str, shots: int, resilience: int = 0) -> Dict[str, int]:
    """
    Use IBM Runtime SamplerV2 (if available). Requires:
      export QISKIT_IBM_TOKEN=...
    resilience: 0..3  (0 = off; higher adds error mitigation at cost of time)
    """
    service = QiskitRuntimeService()
    with Session(service=service, backend=backend_name) as session:
        # Options: set resilience level for error mitigation, execution shots, etc.
        options = Options()
        options.execution.shots = shots
        options.resilience_level = resilience
        sampler = Sampler(session=session, options=options)
        # SamplerV2 API expects transpiled circuits internally; it handles transpile.
        result = sampler.run([qc]).result()
        # Sampler returns quasi-dists
        quasis = result[0].data.meas.get("quasi_dists", None) or result[0].data.get("quasi_dists", None)
        if quasis is None:
            # try standard "dist" or "counts" fallbacks if API changes
            quasis = result[0].data.get("dist", None) or result[0].data.get("counts", None)
        if quasis is None:
            raise RuntimeError("Could not extract quasi-distributions from Runtime result.")
        # Convert quasi to counts by scaling by shots (best-effort integerization)
        q = quasis[0] if isinstance(quasis, list) else quasis
        counts = {}
        for bitstr, prob in q.items():
            # Keys may be ints or bitstrings depending on runtime version
            if isinstance(bitstr, int):
                key = format(bitstr, f"0{qc.num_clbits}b")
            else:
                key = str(bitstr)
            counts[key] = int(round(prob * shots))
        return counts


def main():
    parser = argparse.ArgumentParser(description="IBM-ready RQC-Hash (Random Quantum Circuit Hash)")
    parser.add_argument("--message", "-m", type=str, default="hello", help="Message to hash (UTF-8 string).")
    parser.add_argument("--n", type=int, default=6, help="Number of qubits (keep small on real HW).")
    parser.add_argument("--d", type=int, default=6, help="Circuit depth (layers).")
    parser.add_argument("--seed", type=int, default=12345, help="Seed for random circuit.")
    parser.add_argument("--shots", type=int, default=2048, help="Number of shots.")
    parser.add_argument("--backend", type=str, default="", help="IBM backend name (e.g., ibm_osaka, ibm_brisbane). If empty, use Aer.")
    parser.add_argument("--runtime", type=str, choices=["auto", "provider", "cloud", ""], default="auto",
                        help="Connection mode: 'provider' (qiskit-ibm-provider), 'cloud' (qiskit-ibm-runtime), 'auto' to auto-detect, empty for Aer.")
    parser.add_argument("--resilience", type=int, default=0, help="Runtime resilience level (0..3) if using Runtime.")
    args = parser.parse_args()

    msg = args.message.encode("utf-8")
    qc = build_random_circuit(args.n, args.d, args.seed, msg)

    # Decide execution path
    backend_name = args.backend.strip()
    runtime_mode = args.runtime

    counts: Dict[str, int]

    if backend_name == "":
        # Aer fallback
        counts = run_on_aer(qc, shots=args.shots)
        mode = "Aer simulator"
    else:
        # IBM path requested
        used = False
        if runtime_mode in ("auto", "cloud") and _runtime_available:
            try:
                counts = run_on_ibm_runtime(qc, backend_name=backend_name, shots=args.shots, resilience=args.resilience)
                mode = f"IBM Runtime (backend={backend_name}, resilience={args.resilience})"
                used = True
            except Exception as e:
                print(f"[Runtime] Failed ({e}). Falling back...")
        if not used and (runtime_mode in ("auto", "provider", "cloud") or runtime_mode == "provider"):
            if _backend_mode == "provider":
                counts = run_on_ibm_provider(qc, backend_name=backend_name, shots=args.shots)
                mode = f"IBM Provider (backend={backend_name})"
                used = True
            else:
                print("[Provider] qiskit-ibm-provider not available.")
        if not used:
            # As last resort, Aer
            print("[Warning] IBM backends unavailable. Using Aer simulator.")
            counts = run_on_aer(qc, shots=args.shots)
            mode = "Aer simulator"

    top = most_frequent_bitstring(counts)
    hhex = to_hash_hex(top, args.n)

    print("=== RQC-Hash Result ===")
    print(f"Mode      : {mode}")
    print(f"Message   : {args.message!r}")
    print(f"n_qubits  : {args.n}, depth: {args.d}, seed: {args.seed}, shots: {args.shots}")
    print(f"Top bitstr: {top}  (Qiskit MSB..LSB)")
    print(f"Hash hex  : {hhex} (LSB-first integer)")

    # Save counts to file
    out_counts = {
        "mode": mode,
        "message": args.message,
        "n_qubits": args.n,
        "depth": args.d,
        "seed": args.seed,
        "shots": args.shots,
        "top_bitstring": top,
        "hash_hex": hhex,
        "counts": counts
    }
    with open("/mnt/data/rqc_counts.json", "w") as f:
        json.dump(out_counts, f, indent=2)
    print("Saved counts to /mnt/data/rqc_counts.json")

if __name__ == "__main__":
    main()
