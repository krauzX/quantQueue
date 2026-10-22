"""FRQI state preparation and multi-controlled rotation gates."""

from __future__ import annotations

from typing import Sequence

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit
from qiskit.circuit import Qubit
from qiskit.synthesis import synth_mcx_1_clean_b95


def _polarize_controls(
    circuit: QuantumCircuit,
    num_position_qubits: int,
    pixel_index: int,
) -> tuple[list[Qubit], list[Qubit]]:
    """Set X gates on controls that must read |0> for this pixel address."""
    qubits = circuit.qubits
    pattern = format(pixel_index, f"0{num_position_qubits}b")
    controls: list[Qubit] = []
    zero_controls: list[Qubit] = []
    for bit_pos, bit_value in enumerate(pattern):
        qubit = qubits[num_position_qubits - 1 - bit_pos]
        controls.append(qubit)
        if bit_value == "0":
            circuit.x(qubit)
            zero_controls.append(qubit)
    return controls, zero_controls


def multi_controlled_ry(
    circuit: QuantumCircuit,
    angle: float,
    controls: Sequence[Qubit],
    target: Qubit,
    ancillas: Sequence[Qubit],
) -> None:
    """RY(angle) conditioned on all controls reading |1>."""
    if angle == 0:
        return
    if len(controls) == 1:
        circuit.ry(angle / 2, target)
        circuit.cx(controls[0], target)
        circuit.ry(-angle / 2, target)
        circuit.cx(controls[0], target)
        return
    if len(controls) == 2:
        circuit.cry(angle / 2, controls[1], target)
        circuit.cx(controls[1], controls[0])
        circuit.cry(-angle / 2, controls[0], target)
        circuit.cx(controls[1], controls[0])
        circuit.cry(angle / 2, controls[0], target)
        return
    mcx = synth_mcx_1_clean_b95(len(controls))
    required = mcx.num_qubits - len(controls) - 1
    if len(ancillas) < required:
        raise ValueError(
            f"need {required} clean ancillas for {len(controls)} controls"
        )
    ancilla_qubits = list(ancillas)[:required]
    mcx_qubits = list(controls) + [target] + ancilla_qubits
    circuit.ry(angle / 2, target)
    circuit.compose(mcx, mcx_qubits, inplace=True)
    circuit.ry(-angle / 2, target)
    circuit.compose(mcx, mcx_qubits, inplace=True)


def frqi_state_preparation(
    angles: np.ndarray,
    num_axis_qubits: int,
    num_auxiliary_qubits: int = 0,
) -> tuple[QuantumCircuit, dict]:
    """Build the FRQI preparation circuit and return its register map."""
    num_pixels = len(angles)
    expected = 2 ** (2 * num_axis_qubits)
    if num_pixels != expected:
        raise ValueError(
            f"expected {expected} angles, received {num_pixels}"
        )
    num_position_qubits = 2 * num_axis_qubits
    color_qubit = num_position_qubits
    mcx = synth_mcx_1_clean_b95(num_position_qubits)
    num_ancillas = max(mcx.num_qubits - num_position_qubits - 1, 0)
    circuit = QuantumCircuit(
        num_position_qubits + 1 + num_ancillas + num_auxiliary_qubits,
        name="frqi_state_preparation",
    )
    circuit.h(range(num_position_qubits))
    ancilla_qubits = circuit.qubits[
        num_position_qubits + 1 : num_position_qubits + 1 + num_ancillas
    ]
    for pixel_index, angle in enumerate(angles):
        if angle == 0:
            continue
        controls, zero_controls = _polarize_controls(
            circuit, num_position_qubits, pixel_index
        )
        multi_controlled_ry(
            circuit, 2.0 * angle, controls, circuit.qubits[color_qubit], ancilla_qubits
        )
        for qubit in zero_controls:
            circuit.x(qubit)
    register_map = {
        "num_axis_qubits": num_axis_qubits,
        "num_position_qubits": num_position_qubits,
        "position_qubits": list(range(num_position_qubits)),
        "x_register": list(range(num_axis_qubits)),
        "y_register": list(range(num_axis_qubits, num_position_qubits)),
        "color_qubit": color_qubit,
        "ancilla_qubits": list(
            range(num_position_qubits + 1, num_position_qubits + 1 + num_ancillas)
        ),
        "auxiliary_qubits": list(
            range(
                num_position_qubits + 1 + num_ancillas,
                num_position_qubits + 1 + num_ancillas + num_auxiliary_qubits,
            )
        ),
    }
    return circuit, register_map


def frqi_measurement_circuit(
    angles: np.ndarray,
    num_axis_qubits: int,
) -> tuple[QuantumCircuit, dict]:
    """FRQI preparation circuit with position and color measured."""
    circuit, register_map = frqi_state_preparation(angles, num_axis_qubits)
    num_position_qubits = register_map["num_position_qubits"]
    readout = ClassicalRegister(num_position_qubits + 1, "frqi_readout")
    circuit.add_register(readout)
    circuit.measure(
        register_map["position_qubits"], readout[:num_position_qubits]
    )
    circuit.measure(register_map["color_qubit"], readout[num_position_qubits])
    return circuit, register_map
