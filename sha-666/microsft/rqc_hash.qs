
namespace RQCHash {
    open Microsoft.Quantum.Intrinsic;
    open Microsoft.Quantum.Canon;
    open Microsoft.Quantum.Measurement;
    open Microsoft.Quantum.Math;
    open Microsoft.Quantum.Convert;

    // Q# operation: apply a sequence of single-qubit rotations (Rz, Rx) and CNOT entangling layers.
    // The angles are provided by the host as arrays for determinism.
    operation ApplyRandomCircuit(qubits : Qubit[], rzAngles : Double[][], rxAngles : Double[][]) : Unit is Adj+Ctl {
        // rzAngles and rxAngles are arrays of layers -> arrays per qubit
        let n = Length(qubits);
        let depth = Length(rzAngles);
        for (layer in 0 .. depth - 1) {
            // Apply Rz and Rx per qubit for this layer
            for (i in 0 .. n - 1) {
                Rz(rzAngles[layer][i], qubits[i]);
                Rx(rxAngles[layer][i], qubits[i]);
            }
            // Entangling: CNOT chain (0->1,2->3,...) then staggered (1->2,3->4,...)
            for (i in 0 .. 2 .. n - 2) {
                CNOT(qubits[i], qubits[i+1]);
            }
            for (i in 1 .. 2 .. n - 2) {
                CNOT(qubits[i], qubits[i+1]);
            }
            if (n > 2) {
                CNOT(qubits[n-1], qubits[0]);
            }
        }
    }

    // Prepare message by X-ing qubits corresponding to 1 bits of messageBits (LSB-first)
    operation PrepareMessage(qubits : Qubit[], messageBits : Bool[]) : Unit {
        let k = Length(messageBits);
        for (i in 0 .. MinI(Length(qubits)-1, k-1)) {
            if (messageBits[i]) {
                X(qubits[i]);
            }
        }
    }

    // Measure all qubits in Z basis and return array of Bool (LSB-first)
    operation MeasureAll(qubits : Qubit[]) : Bool[] {
        mutable results = new Bool[Length(qubits)];
        for (i in 0 .. Length(qubits) - 1) {
            let r = M(qubits[i]);
            set results w/= i <- (r == One);
        }
        return results;
    }

    // Compute one sample: prepare message, apply random circuit, measure.
    operation SampleRQCHash(messageBits : Bool[], rzAngles : Double[][], rxAngles : Double[][]) : Bool[] {
        use qs = Qubit[Length(rzAngles[0])];
        PrepareMessage(qs, messageBits);
        ApplyRandomCircuit(qs, rzAngles, rxAngles);
        let out = MeasureAll(qs);
        ResetAll(qs);
        return out;
    }
}
