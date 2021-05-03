#!/usr/bin/env python3

# Making the following assumptions:
# * There is no flagging (locations of mines are always unknown)
# * There are no unknown tiles next to constraints with the value '0'
# * There are no 8's

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

import numpy as np
import math

CELL_UNKNOWN = -1
RESULT_CHARS = {
    0: '.',
    1: '*',
    -1: '?'
}

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

def make_count_circuit(num_mines, num_cells):
    x = QuantumRegister(num_cells, 'x')
    c = QuantumRegister(3, 'c')
    circuit = QuantumCircuit(x, c)
    # count
    for i in range(num_cells):
        circuit.mcx([x[i], c[0], c[1]], c[2])
        circuit.ccx(x[i], c[0], c[1])
        circuit.cx(x[i], c[0])
    if num_mines & 1 == 0:
        circuit.x(c[0])
    if num_mines & 2 == 0:
        circuit.x(c[1])
    if num_mines & 4 == 0:
        circuit.x(c[2])
    return circuit

constraints = {}
def make_constraint(num_mines, num_cells):
    assert num_mines <= num_cells
    assert num_mines < 8
    assert num_mines > 0
    key = (num_mines, num_cells)
    if key in constraints:
        return constraints[key]
    x = QuantumRegister(num_cells, 'x')
    y = QuantumRegister(1, 'y')
    c = QuantumRegister(3, 'c')
    circuit = QuantumCircuit(x, y, c)
    # count
    if num_mines == 1 and num_cells == 1:
        circuit.cx(x[0], y)
    elif num_mines == 1 and num_cells == 2:
        circuit.cx(x[0], y)
        circuit.cx(x[1], y)
    elif num_mines == 2 and num_cells == 2:
        circuit.ccx(x[0], x[1], y)
    elif num_mines == num_cells:
        circuit.mcx(x, y)
    elif num_mines == 1 and num_cells == 3:
        circuit.mcx(x, y)
        circuit.cx(x[0], y)
        circuit.cx(x[1], y)
        circuit.cx(x[2], y)
    elif num_mines == 2 and num_cells == 3:
        circuit.ccx(x[0], x[1], y)
        circuit.ccx(x[0], x[2], y)
        circuit.ccx(x[1], x[2], y)
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
    elif num_mines == 3 and num_cells == 4:
        circuit.mct([x[0], x[1], x[2]], y)
        circuit.mct([x[0], x[1], x[3]], y)
        circuit.mct([x[0], x[2], x[3]], y)
        circuit.mct([x[1], x[2], x[3]], y)
    # elif num_cells > 4 and num_mines > math.ceil(num_cells/2):
    #     for i in range(num_mines):
    #         circuit.x(x[i])
    #     circuit.append(make_constraint(num_cells-num_mines, num_cells))
    #     for i in range(num_mines):
    #         circuit.x(x[i])
    else:
        c_count = make_count_circuit(num_mines, num_cells)
        circuit.append(c_count, x[:] + c[:])
        circuit.mcx(c[:], y)
        circuit.append(c_count.inverse(), x[:] + c[:])
    # TODO: add more specific handlers for different mine counts
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
    c = QuantumRegister(3, 'c')
    circuit = QuantumCircuit(cells, t, z, c)
    # Perform constraint check
    for i, (col, row) in enumerate(tilemap.iterate_constraints()):
        value = tilemap.get_cell(col, row)
        c_regs = [qbit_map[pos] for pos in tilemap.iterate_nearby_unknowns(col, row)]
        c_regs.append(t[i])
        circuit.append(make_constraint(value, len(c_regs)-1), c_regs + c[:])
    circuit.mct(t, z)
    # Undo constraint check
    for i, (col, row) in enumerate(tilemap.iterate_constraints()):
        value = tilemap.get_cell(col, row)
        c_regs = [qbit_map[pos] for pos in tilemap.iterate_nearby_unknowns(col, row)]
        c_regs.append(t[i])
        circuit.append(make_constraint(value, len(c_regs)-1), c_regs + c[:])
    return (circuit, qbit_map)

def make_solver_circuit(tilemap):
    num_cells = tilemap.num_cells()
    num_constraints = tilemap.num_constraints()
    # Make circuit
    cells = QuantumRegister(num_cells, 'cells')
    t = QuantumRegister(num_constraints, 't')
    z = QuantumRegister(1, 'z')
    c = QuantumRegister(3, 'c')
    c_cells = ClassicalRegister(num_cells, 'c_cells')
    circuit = QuantumCircuit(cells, t, z, c, c_cells)
    # Initialize cells
    for i in range(num_cells):
        circuit.reset(cells[i])
        circuit.h(cells[i])
    # Initialize Z
    circuit.initialize([1, -1]/np.sqrt(2), z)
    # perform grover iterations
    num_iter = math.ceil(math.sqrt(2**num_cells))# * (math.pi / 4.0))
    print("Performing {} iterations".format(num_iter))
    (c_oracle, qbit_map) = make_oracle(tilemap)
    c_diffuser = make_diffuser(num_cells)
    # unfortunately, there's no way of knowing how many results M there are
    # out of N possibilities. Also, too many iterations will give bad results,
    # so we can't overestimate, either.
    for i in range(num_iter):
        circuit.append(c_oracle, cells[:] + t[:] + z[:] + c[:])
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
                    s += RESULT_CHARS[values[qbit_map[(col, row)]]]
                    # if values[qbit_map[(col, row)]] == 0:
                    #     s += "."
                    # else:
                    #     s += "*"
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