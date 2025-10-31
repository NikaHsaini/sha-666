
// Driver.cs - C# host to run the Q# SampleRQCHash operation deterministically.
// Requires Microsoft.Quantum.Sdk and a Q# project setup (dotnet new console -lang C# + qsharp).
using System;
using System.Linq;
using System.Numerics;
using System.Threading.Tasks;
using System.Collections.Generic;
using Microsoft.Quantum.Simulation.Core;
using Microsoft.Quantum.Simulation.Simulators;

namespace RQCHashHost {
    class Driver {
        static double RandomAngle(Random rng) => rng.NextDouble() * 2.0 * Math.PI;

        static List<double[]> BuildLayerAngles(int nQubits, Random rng) {
            var rz = new double[nQubits];
            var rx = new double[nQubits];
            for (int i = 0; i < nQubits; i++) {
                rz[i] = RandomAngle(rng);
                rx[i] = RandomAngle(rng);
            }
            return new List<double[]>{ rz, rx };
        }

        static double[][] BuildAnglesArray(int depth, int nQubits, int seed, bool isRz) {
            var rng = new Random(seed + (isRz ? 1 : 1000));
            double[][] arr = new double[depth][];
            for (int d = 0; d < depth; d++) {
                arr[d] = new double[nQubits];
                for (int q = 0; q < nQubits; q++) {
                    arr[d][q] = rng.NextDouble() * 2.0 * Math.PI;
                }
            }
            return arr;
        }

        static bool[] BitsFromMessage(byte[] msg, int nQubits) {
            var bits = new bool[nQubits];
            int idx = 0;
            foreach (var b in msg) {
                for (int i = 0; i < 8 && idx < nQubits; i++, idx++) {
                    bits[idx] = ((b >> i) & 1) == 1;
                }
            }
            // remaining bits are false (0)
            return bits;
        }

        static string BoolArrayToBitstring(bool[] arr) {
            // LSB-first to string MSB..LSB for human readable: reverse
            return string.Join("", arr.Reverse().Select(b => b ? '1' : '0'));
        }

        static async Task Main(string[] args) {
            var message = System.Text.Encoding.UTF8.GetBytes("hello");
            int nQubits = 16;
            int depth = 12;
            int seed = 12345;
            int shots = 1024;

            var rzAngles = BuildAnglesArray(depth, nQubits, seed, true);
            var rxAngles = BuildAnglesArray(depth, nQubits, seed, false);

            using var sim = new QuantumSimulator();
            var counts = new Dictionary<string,int>();
            for (int s = 0; s < shots; s++) {
                var result = await RQCHash.SampleRQCHash.Run(sim, BitsFromMessage(message, nQubits),
                    new QArray<QArray<double>>(rzAngles.Select(a => new QArray<double>(a)).ToArray()),
                    new QArray<QArray<double>>(rxAngles.Select(a => new QArray<double>(a)).ToArray()));
                var bitstr = BoolArrayToBitstring(result.ToArray());
                if (!counts.ContainsKey(bitstr)) counts[bitstr] = 0;
                counts[bitstr] += 1;
            }

            var top = counts.OrderByDescending(kv => kv.Value).First();
            Console.WriteLine($"Top bitstring: {top.Key} count={top.Value}");
            Console.WriteLine("Top 10 results:");
            foreach (var kv in counts.OrderByDescending(kv => kv.Value).Take(10)) {
                Console.WriteLine($"{kv.Key} : {kv.Value}");
            }
        }
    }
}
