#!/usr/bin/python3
import argparse
import sys

# Get arguments
parser = argparse.ArgumentParser()
parser.add_argument('input', metavar="INPUT", type=argparse.FileType('r'), nargs='?', help="Minesweeper grid input")
parser.add_argument('-s', '--shots', type=lambda x: int(x, base=0), default=1000, help="The number of shots to perform")
group = parser.add_mutually_exclusive_group()
group.add_argument('-a', '--num-answers', type=lambda x: int(x, base=0), default=None, help="The number of answers to estimate the iteration count with")
group.add_argument('-i', '--num-iterations', type=lambda x: int(x, base=0), default=None, help="The number of iterations to perform")
args = parser.parse_args()

if args.input is None:
    print("? for each unknown tile")
    print("1-8 for each hint")
    print("0 for empty spaces")
    print("> for flags")
    print("X to ignore a given tile (e.g. as a pre-applied flag or grid border)")
    print("All lines must be the same length")
    print("Input a Minesweeper grid:")
    s = ""
    while True:
        line = sys.stdin.readline()
        if line.strip() == "":
            break
        s += line
else:
    s = args.input.read()

# Import here because qiskit takes time to import
from qiskit import QuantumCircuit, execute, Aer
import mines

tilemap = mines.parse_tiles(s)

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
res = execute(solver, backend=qasm, shots=args.shots).result()
counts = res.get_counts()
values = list(counts.keys())
values.sort(key=lambda x: counts[x])

print("Result:")
probabilities = [[0, 0] for _ in range(len(qbit_map))]
for key in values:
    value = key[::-1]
    prob = counts[key] / args.shots
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