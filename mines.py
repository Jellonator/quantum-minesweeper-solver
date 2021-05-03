#!/usr/bin/env python3

# Making the following assumptions:
# * There is no flagging (locations of mines are always unknown)
# * There are no unknown tiles next to constraints with the value '0'

from qiskit import (
    QuantumCircuit,
    ClassicalRegister,
    QuantumRegister,
    AncillaRegister,
    execute,
    Aer)
from qiskit.circuit.library import (
    OR,
    AND
)
from qiskit import QuantumCircuit, execute
qasm = Aer.get_backend("qasm_simulator")

import numpy as np
import math

CELL_UNKNOWN = -1

def make_diffuser(nqubits):
    # from https://qiskit.org/textbook/ch-algorithms/grover.html
    qc = QuantumCircuit(nqubits)
    # Apply transformation |s> -> |00..0> (H-gates)
    for qubit in range(nqubits):
        qc.h(qubit)
    # Apply transformation |00..0> -> |11..1> (X-gates)
    for qubit in range(nqubits):
        qc.x(qubit)
    # Do multi-controlled-Z gate
    qc.h(nqubits-1)
    qc.mct(list(range(nqubits-1)), nqubits-1)  # multi-controlled-toffoli
    qc.h(nqubits-1)
    # Apply transformation |11..1> -> |00..0>
    for qubit in range(nqubits):
        qc.x(qubit)
    # Apply transformation |00..0> -> |s>
    for qubit in range(nqubits):
        qc.h(qubit)
    # We will return the diffuser as a gate
    U_s = qc.to_gate()
    U_s.name = "U$_s$"
    return U_s

constraints = {}
def make_constraint(num_mines, num_cells):
    assert num_mines <= num_cells
    key = (num_mines, num_cells)
    if key in constraints:
        return constraints[key]
    x = QuantumRegister(num_cells, 'x')
    y = QuantumRegister(1, 'y')
    circuit = QuantumCircuit(x, y)
    if num_mines == 1 and num_cells == 1:
        circuit.cx(x[0], y)
    elif num_mines == 1 and num_cells == 2:
        circuit.cx(x[0], y)
        circuit.cx(x[1], y)
    elif num_mines == 2 and num_cells == 2:
        circuit.ccx(x[0], x[1], y)
    elif num_mines == 1 and num_cells == 3:
        circuit.mcx(x, y)
        circuit.cx(x[0], y)
        circuit.cx(x[1], y)
        circuit.cx(x[2], y)
    elif num_mines == 2 and num_cells == 3:
        circuit.ccx(x[0], x[1], y)
        circuit.ccx(x[0], x[2], y)
        circuit.ccx(x[1], x[2], y)
    elif num_mines == 3 and num_cells == 3:
        circuit.mcx(x, y)
    elif num_mines == 1 and num_cells == 4:
        circuit.mct([x[0], x[1], x[2]], y)
        circuit.mct([x[0], x[1], x[3]], y)
        circuit.mct([x[0], x[2], x[3]], y)
        circuit.mct([x[1], x[2], x[3]], y)
        circuit.cx(x[0], y)
        circuit.cx(x[1], y)
        circuit.cx(x[2], y)
        circuit.cx(x[3], y)
    elif num_mines == 2 and num_cells == 4:
        circuit.ccx(x[0], x[1], y)
        circuit.ccx(x[0], x[2], y)
        circuit.ccx(x[0], x[3], y)
        circuit.ccx(x[1], x[2], y)
        circuit.ccx(x[1], x[3], y)
        circuit.ccx(x[2], x[3], y)
        circuit.mct([x[0], x[1], x[2]], y)
        circuit.mct([x[0], x[1], x[3]], y)
        circuit.mct([x[0], x[2], x[3]], y)
        circuit.mct([x[1], x[2], x[3]], y)
    # TODO: handle more mines
    else:
        raise RuntimeError("Unhandled constraint {}/{}".format(num_mines, num_cells))
    constraints[key] = circuit
    return circuit

def make_oracle(tilemap):
    # Get tilemap info
    qbit_map = {}
    for pos in tilemap.iterate_unknowns():
        qbit_map[pos] = len(qbit_map)
    num_cells = len(qbit_map)
    num_constraints = tilemap.num_constraints()
    # Make circuit
    cells = QuantumRegister(num_cells, 'cells')
    t = QuantumRegister(num_constraints, 't')
    z = QuantumRegister(1, 'z')
    circuit = QuantumCircuit(cells, t, z)
    # Perform constraint check
    for i, (col, row) in enumerate(tilemap.iterate_constraints()):
        value = tilemap.get_cell(col, row)
        c_regs = [qbit_map[pos] for pos in tilemap.iterate_nearby_unknowns(col, row)]
        c_regs.append(t[i])
        circuit.append(make_constraint(value, len(c_regs)-1), c_regs)
    circuit.mct(t, z)
    # Undo constraint check
    for i, (col, row) in enumerate(tilemap.iterate_constraints()):
        value = tilemap.get_cell(col, row)
        c_regs = [qbit_map[pos] for pos in tilemap.iterate_nearby_unknowns(col, row)]
        c_regs.append(t[i])
        circuit.append(make_constraint(value, len(c_regs)-1), c_regs)
    return (circuit, qbit_map)

def make_solver_circuit(tilemap):
    num_cells = tilemap.num_cells()
    num_constraints = tilemap.num_constraints()
    # Make circuit
    cells = QuantumRegister(num_cells, 'cells')
    t = QuantumRegister(num_constraints, 't')
    z = QuantumRegister(1, 'z')
    c_cells = ClassicalRegister(num_cells, 'c_cells')
    circuit = QuantumCircuit(cells, t, z, c_cells)
    # Initialize cells
    for i in range(num_cells):
        circuit.reset(cells[i])
        circuit.h(cells[i])
    # Initialize Z
    circuit.initialize([1, -1]/np.sqrt(2), z)
    # Apply oracle
    num_iter = math.ceil(math.sqrt(num_cells))
    (c_oracle, qbit_map) = make_oracle(tilemap)
    c_diffuser = make_diffuser(num_cells)
    for i in range(num_iter):
        circuit.append(c_oracle, cells[:] + t[:] + z[:])
        circuit.append(c_diffuser, cells)
    # Measure
    for i in range(num_cells):
        circuit.measure(cells[i], c_cells[i])
    return (circuit, qbit_map)

class Tilemap:
    def __init__(self, tiles):
        self.tiles = tiles
        if len(tiles) == 0:
            self.width = 0
            self.height = 0
        n = len(tiles[0])
        for v in tiles[1:]:
            if len(v) != n:
                raise RuntimeError("Tilemap does not have consistent size")
        self.width = n
        self.height = len(tiles)
        self.tiles = tiles
    def __str__(self):
        s = ""
        is_first = True
        for row in self.tiles:
            if not is_first:
                s += '\n'
            is_first = False
            for value in row:
                if value == -1:
                    s += '?'
                else:
                    s += str(value)
        return s
    def get_width(self):
        return self.width
    def get_height(self):
        return self.height
    def get_cell(self, col, row):
        return self.tiles[row][col]
    def is_in_bounds(self, col, row):
        return row in range(self.get_width()) and col in range(self.get_height())
    def iterate_constraints(self):
        for row in range(self.get_height()):
            for col in range(self.get_width()):
                if self.get_cell(col, row) >= 1:
                    yield (col, row)
    def iterate_unknowns(self):
        for row in range(self.get_height()):
            for col in range(self.get_width()):
                if self.get_cell(col, row) == CELL_UNKNOWN:
                    yield (col, row)
    def iterate_nearby_unknowns(self, col, row):
        for i_row in range(max(0, row-1), min(row+2, self.get_height())):
            for i_col in range(max(0, col-1), min(col+2, self.get_width())):
                if self.get_cell(i_col, i_row) == CELL_UNKNOWN:
                    yield(i_col, i_row)
    def num_cells(self):
        n = 0
        for _ in self.iterate_unknowns():
            n += 1
        return n
    def num_constraints(self):
        n = 0
        for _ in self.iterate_constraints():
            n += 1
        return n
    def get_answer(self, values, qbit_map):
        s = ""
        is_first = True
        for row in range(self.height):
            if not is_first:
                s += '\n'
            is_first = False
            for col in range(self.width):
                value = self.get_cell(col, row)
                if value == 0:
                    s += " "
                elif value > 0:
                    s += str(value)
                elif value == CELL_UNKNOWN:
                    if values[qbit_map[(col, row)]] == 0:
                        s += "."
                    else:
                        s += "*"
        return s

def parse_tiles(s):
    ret = []
    for k in s.splitlines():
        k = k.strip()
        if k != "":
            l = []
            for c in k:
                if c == '?':
                    l.append(CELL_UNKNOWN)
                if c == '.':
                    l.append(0)
                if c >= '0' and c <= '9':
                    l.append(ord(c) - ord('0'))
            ret.append(l)
    return Tilemap(ret)

tilemap = parse_tiles(
    """
?????
11?11
    """
)

num_shots = 1000
print(tilemap)
(solver, qbit_map) = make_solver_circuit(tilemap)
print("Executing circuit...")
res = execute(solver, backend=qasm, shots=num_shots).result()
counts = res.get_counts()
# value = max(counts, key=counts.get)
values = list(counts.keys())
# values.sort(key=lambda x: counts[x])
# print(value)
print("Result:")
for value in values:
    prob = counts[value] / num_shots
    if prob > 0.01:
        print(tilemap.get_answer([int(c) for c in value[::-1]], qbit_map))
        print("Probability:", prob)