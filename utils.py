"""Image preprocessing, classical Sobel baseline, and QIP metrics."""

from __future__ import annotations

import numpy as np
from PIL import Image
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

SOBEL_X = np.array([[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]])
SOBEL_Y = np.array([[1.0, 2.0, 1.0], [0.0, 0.0, 0.0], [-1.0, -2.0, -1.0]])


def load_grayscale_image(image_path: str, size: int) -> np.ndarray:
    image = Image.open(image_path).convert("L")
    image = image.resize((size, size), Image.Resampling.LANCZOS)
    return np.asarray(image, dtype=np.float64) / 255.0


def frqi_normalization(pixels: np.ndarray) -> np.ndarray:
    return np.arcsin(np.clip(pixels, 0.0, 1.0))


def sobel_edge_magnitude(pixels: np.ndarray) -> np.ndarray:
    gradient_x = _convolve(pixels, SOBEL_X)
    gradient_y = _convolve(pixels, SOBEL_Y)
    magnitude = np.hypot(gradient_x, gradient_y)
    peak = np.max(magnitude)
    if peak > 0.0:
        magnitude = magnitude / peak
    return magnitude


def _convolve(pixels: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    side = kernel.shape[0]
    offset = side // 2
    padded = np.pad(pixels, offset, mode="edge")
    output = np.zeros_like(pixels)
    for row in range(side):
        for column in range(side):
            output += (
                kernel[row, column]
                * padded[
                    row : row + pixels.shape[0],
                    column : column + pixels.shape[1],
                ]
            )
    return output


def mean_squared_error(reference: np.ndarray, candidate: np.ndarray) -> float:
    reference_map = np.asarray(reference, dtype=np.float64)
    candidate_map = np.asarray(candidate, dtype=np.float64)
    return float(np.mean((reference_map - candidate_map) ** 2))


def edge_statistics(edge_map: np.ndarray, threshold: float = 0.5) -> dict:
    """Compute usable edge measurements from a gradient magnitude map."""
    binary = (edge_map >= threshold).astype(np.uint8)
    edge_pixels = int(np.count_nonzero(binary))
    mean_strength = float(np.mean(edge_map[edge_map > 0])) if edge_pixels > 0 else 0.0
    edge_density = float(edge_pixels / edge_map.size)
    return {
        "edge_pixels": edge_pixels,
        "mean_strength": mean_strength,
        "edge_density": edge_density,
        "binary_mask": binary,
    }


def save_binary_mask(binary_mask: np.ndarray, output_path: str) -> None:
    """Save a binary edge mask as a PNG image."""
    image = (binary_mask * 255).astype(np.uint8)
    Image.fromarray(image, mode="L").save(output_path)


def peak_signal_noise_ratio(
    reference: np.ndarray, candidate: np.ndarray, data_range: float = 1.0
) -> float:
    mse = mean_squared_error(reference, candidate)
    if mse == 0.0:
        return float("inf")
    return float(10.0 * np.log10(data_range ** 2 / mse))


def analytical_statevector(circuit: QuantumCircuit, seed: int = 0) -> Statevector:
    if any(
        instruction.operation.name == "measure" for instruction in circuit.data
    ):
        raise ValueError("analytical_statevector requires a circuit without measures")
    simulator = AerSimulator(method="statevector")
    readout = circuit.copy()
    readout.save_statevector()
    result = simulator.run(readout, shots=1, seed_simulator=seed).result()
    return Statevector(result.get_statevector())


def statistical_sampling(circuit: QuantumCircuit, shots: int, seed: int) -> dict:
    simulator = AerSimulator(method="statevector")
    result = simulator.run(circuit, shots=shots, seed_simulator=seed).result()
    return result.get_counts()


def extract_frqi_probabilities(
    statevector: Statevector, register_map: dict
) -> np.ndarray:
    num_pixels = 2 ** register_map["num_position_qubits"]
    marginal_qubits = register_map["position_qubits"] + [
        register_map["color_qubit"]
    ]
    marginal = np.asarray(
        statevector.probabilities(marginal_qubits), dtype=np.float64
    )
    return marginal[num_pixels:]


def extract_edge_probabilities(
    statevector: Statevector, register_map: dict
) -> np.ndarray:
    num_pixels = 2 ** register_map["num_position_qubits"]
    test_ancilla = register_map["auxiliary_qubits"][0]
    marginal_qubits = register_map["position_qubits"] + [test_ancilla]
    marginal = np.asarray(
        statevector.probabilities(marginal_qubits), dtype=np.float64
    )
    return marginal[num_pixels:]


def parse_readout_counts(counts: dict, num_position_qubits: int) -> np.ndarray:
    width = 2 * num_position_qubits
    total_shots = sum(counts.values())
    readout_table = np.zeros((2, 2**width), dtype=np.float64)
    for key, shots in counts.items():
        flag = int(key[0])
        position = 0
        for bit_index in range(width):
            position += int(key[width - bit_index]) * (2**bit_index)
        readout_table[flag, position] += shots / total_shots
    return readout_table


def reconstruct_spatial_domain(
    color_one_probabilities: np.ndarray, num_axis_qubits: int
) -> np.ndarray:
    num_pixels = 2 ** (2 * num_axis_qubits)
    sin_squared = np.clip(
        np.asarray(color_one_probabilities, dtype=np.float64) * num_pixels,
        0.0,
        1.0,
    )
    return np.sqrt(sin_squared)


def reconstruct_edge_magnitude(
    edge_probabilities: np.ndarray, num_axis_qubits: int
) -> np.ndarray:
    num_pixels = 2 ** (2 * num_axis_qubits)
    sin_half_angle = np.clip(
        np.asarray(edge_probabilities, dtype=np.float64) * num_pixels,
        0.0,
        1.0,
    )
    return 2.0 * np.arcsin(np.sqrt(sin_half_angle))
