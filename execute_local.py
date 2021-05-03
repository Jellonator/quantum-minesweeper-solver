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
if solver.num_qubits > 16:
    print("(This may take a while on qasm)")
print("Executing circuit...")
res = execute(solver, backend=qasm, shots=num_shots).result()
counts = res.get_counts()
values = list(counts.keys())
values.sort(key=lambda x: counts[x])

print("Result:")
probabilities = [[0, 0] for _ in range(len(qbit_map))]
for key in values:
    value = key[::-1]
    prob = counts[key] / num_shots
    for (i, c) in enumerate(value):
        if c == '0':
            probabilities[i][0] += prob
        else:
            probabilities[i][1] += prob
    if prob > 0.01:
        print(tilemap.get_answer([int(c) for c in value], qbit_map))
        print("Probability: {:.2f}%".format(prob * 100))

print("Composite Result:")
alpha = 0.1
answer = []
for value in probabilities:
    if value[0] > 1.0 - alpha:
        answer.append(0)
    elif value[1] > 1.0 - alpha:
        answer.append(1)
    else:
        answer.append(-1)

print(tilemap.get_answer(answer, qbit_map))