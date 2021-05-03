#!/usr/bin/python3
from qiskit import IBMQ
import mines
from qiskit import QuantumCircuit, execute, Aer
qasm = Aer.get_backend("qasm_simulator")

tilemap = mines.parse_tiles(
    """
???
?31
?10
    """
)

num_shots = 1000

print(tilemap)
(solver, qbit_map) = mines.make_solver_circuit(tilemap)
print("Required qubits: ", solver.num_qubits)
print("Executing circuit...")
res = execute(solver, backend=qasm, shots=num_shots).result()
counts = res.get_counts()
values = list(counts.keys())
values.sort(key=lambda x: counts[x])

print("Result:")
for value in values:
    prob = counts[value] / num_shots
    if prob > 0.01:
        print(tilemap.get_answer([int(c) for c in value[::-1]], qbit_map))
        print("Probability: {:.2f}%".format(prob * 100))