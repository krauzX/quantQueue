"""Quantum edge detection via the Draper QFT adder."""

from __future__ import annotations

from typing import Sequence

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit
from qiskit.circuit import Qubit
from qiskit.circuit.library import QFTGate

from frqi import frqi_state_preparation


def draper_adder(
    circuit: QuantumCircuit,
    register: Sequence[Qubit],
    constant: int,
    control: Qubit | None = None,
) -> None:
    """Conditional shift |x> -> |x + constant mod 2^n> via QFT phases."""
    num_qubits = len(register)
    circuit.compose(QFTGate(num_qubits).definition, register, inplace=True)
    for index, qubit in enumerate(register):
        phase = 2.0 * np.pi * constant / (2 ** (num_qubits - index))
        if control is None:
            circuit.p(phase, qubit)
        else:
            circuit.cp(phase, control, qubit)
    circuit.compose(QFTGate(num_qubits).inverse().definition, register, inplace=True)


def qhed_operator(
    circuit: QuantumCircuit,
    register: Sequence[Qubit],
    control: Qubit,
) -> None:
    """Hadamard edge detection operator H . S_1 . H on one axis."""
    circuit.h(control)
    draper_adder(circuit, register, 1, control=control)
    circuit.h(control)


def differential_edge_circuit(
    angles: np.ndarray,
    num_axis_qubits: int,
    axis: str,
    include_measurements: bool = True,
) -> tuple[QuantumCircuit, dict]:
    """Build the edge detection circuit for one spatial axis."""
    if axis not in ("x", "y"):
        raise ValueError("axis must be 'x' or 'y'")
    circuit, register_map = frqi_state_preparation(
        angles, num_axis_qubits, num_auxiliary_qubits=1
    )
    shift_register = (
        register_map["x_register"] if axis == "x" else register_map["y_register"]
    )
    shift_qubits = [circuit.qubits[index] for index in shift_register]
    test_ancilla = circuit.qubits[register_map["auxiliary_qubits"][0]]
    qhed_operator(circuit, shift_qubits, test_ancilla)
    if include_measurements:
        num_position_qubits = register_map["num_position_qubits"]
        readout = ClassicalRegister(num_position_qubits + 1, f"edge_readout_{axis}")
        circuit.add_register(readout)
        position_qubits = [
            circuit.qubits[index] for index in register_map["position_qubits"]
        ]
        circuit.measure(position_qubits, readout[:num_position_qubits])
        circuit.measure(test_ancilla, readout[num_position_qubits])
    return circuit, register_map
