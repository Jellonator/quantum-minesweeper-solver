#!/usr/bin/python3
from qiskit import QuantumCircuit, execute, Aer
import mines
import sys
import argparse

# Get arguments
parser = argparse.ArgumentParser()
parser.add_argument('input', metavar="INPUT", type=argparse.FileType('r'), nargs='?')
parser.add_argument('-s', '--shots', type=lambda x: int(x, base=0), default=1000)
group = parser.add_mutually_exclusive_group()
group.add_argument('-a', '--num-answers', type=lambda x: int(x, base=0), default=None)
group.add_argument('-i', '--num-iterations', type=lambda x: int(x, base=0), default=None)
args = parser.parse_args()
# print(args.num_answers, )

fh_input = args.input
if fh_input is None:
    print("? for each unknown tile")
    print("1-8 for each hint")
    print("0 for empty spaces")
    print("All lines must be the same length")
    print("Input a Minesweeper grid:")
    fh_input = sys.stdin

s = fh_input.read()
tilemap = mines.parse_tiles(s)

# tilemap = mines.parse_tiles(
#     """
# ???
# ?31
# ?10
#     """
# )

num_shots = 1000

print()
print("Input tilemap:")
print(tilemap)
print("Generating Circuit...")
num_cells = tilemap.num_cells()
# num_iterations = mines.get_num_iterations(num_cells, 1)
num_iterations = args.num_iterations
if num_iterations == None:
    num_answers = args.num_answers
    if num_answers == None:
        num_answers = 1
    num_iterations = mines.get_num_iterations(num_cells, num_answers)
(solver, qbit_map) = mines.make_solver_circuit(tilemap, num_iterations)
print()
print("Required qubits: ", solver.num_qubits)
if solver.num_qubits > 16:
    print("(This may take a while on qasm)")
print("Executing circuit...")
qasm = Aer.get_backend("qasm_simulator")
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