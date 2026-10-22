"""Benchmark: quantum edge detection versus classical Sobel filtering."""

from __future__ import annotations

import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from qiskit.transpiler import preset_passmanagers

from edge_detection import differential_edge_circuit
from frqi import frqi_measurement_circuit, frqi_state_preparation
from utils import (
    analytical_statevector,
    edge_statistics,
    extract_edge_probabilities,
    extract_frqi_probabilities,
    frqi_normalization,
    load_grayscale_image,
    mean_squared_error,
    parse_readout_counts,
    peak_signal_noise_ratio,
    reconstruct_edge_magnitude,
    reconstruct_spatial_domain,
    save_binary_mask,
    sobel_edge_magnitude,
    statistical_sampling,
)

METRICS_BASIS_GATES = ["cx", "p", "ry", "h", "x", "t", "tdg"]


def evaluate_circuit_metrics(circuit) -> dict:
    pass_manager = preset_passmanagers.generate_preset_pass_manager(
        optimization_level=1,
        basis_gates=METRICS_BASIS_GATES,
    )
    transpiled = pass_manager.run(circuit)
    return {
        "depth": transpiled.depth(),
        "gate_count": transpiled.size(),
        "cnot_count": int(transpiled.count_ops().get("cx", 0)),
    }


def _normalize_map(magnitude: np.ndarray) -> np.ndarray:
    peak = np.max(magnitude)
    if peak > 0.0:
        return magnitude / peak
    return magnitude


def run_benchmark(
    image_path: str = "cat.png",
    size: int = 8,
    mode: str = "statevector",
    shots: int = 10000,
    seed: int = 42,
    output_path: str = "qip_comparison.png",
) -> dict:
    num_axis_qubits = int(np.log2(size))
    if 2**num_axis_qubits != size:
        raise ValueError("size must be a power of two (8, 16, or 32)")
    if mode not in ("statevector", "sampling"):
        raise ValueError("mode must be 'statevector' or 'sampling'")
    if not 10_000 <= shots <= 100_000:
        raise ValueError("shots must lie in the range 10^4 to 10^5")

    image_2d = load_grayscale_image(image_path, size)
    pixels = image_2d.flatten()
    angles = frqi_normalization(pixels)

    classical_start = time.perf_counter()
    sobel_map = sobel_edge_magnitude(image_2d)
    classical_time = time.perf_counter() - classical_start

    quantum_start = time.perf_counter()
    if mode == "statevector":
        preparation_circuit, preparation_map = frqi_state_preparation(
            angles, num_axis_qubits
        )
        statevector = analytical_statevector(preparation_circuit, seed)
        color_one = extract_frqi_probabilities(statevector, preparation_map)
        reconstructed = reconstruct_spatial_domain(
            color_one, num_axis_qubits
        )
        edge_probabilities = {}
        edge_circuits = {}
        for axis in ("x", "y"):
            circuit, register_map = differential_edge_circuit(
                angles, num_axis_qubits, axis, include_measurements=False
            )
            statevector = analytical_statevector(circuit, seed)
            edge_probabilities[axis] = extract_edge_probabilities(
                statevector, register_map
            )
            edge_circuits[axis] = circuit
    else:
        measurement_circuit, preparation_map = frqi_measurement_circuit(
            angles, num_axis_qubits
        )
        counts = statistical_sampling(measurement_circuit, shots, seed)
        readout = parse_readout_counts(counts, num_axis_qubits)
        reconstructed = reconstruct_spatial_domain(readout[1, :], num_axis_qubits)
        edge_probabilities = {}
        edge_circuits = {}
        for axis in ("x", "y"):
            circuit, register_map = differential_edge_circuit(
                angles, num_axis_qubits, axis, include_measurements=True
            )
            counts = statistical_sampling(circuit, shots, seed)
            readout = parse_readout_counts(counts, num_axis_qubits)
            edge_probabilities[axis] = readout[1, :]
            edge_circuits[axis] = circuit
    quantum_time = time.perf_counter() - quantum_start

    gradient_x = reconstruct_edge_magnitude(
        edge_probabilities["x"], num_axis_qubits
    )
    gradient_y = reconstruct_edge_magnitude(
        edge_probabilities["y"], num_axis_qubits
    )
    quantum_edge = _normalize_map(np.hypot(gradient_x, gradient_y)).reshape(
        size, size
    )
    reconstructed_2d = reconstructed.reshape(size, size)

    sobel_stats = edge_statistics(sobel_map)
    quantum_stats = edge_statistics(quantum_edge)

    sobel_mask_path = output_path.replace(".png", "_sobel_edge.png")
    quantum_mask_path = output_path.replace(".png", "_quantum_edge.png")
    save_binary_mask(sobel_stats["binary_mask"], sobel_mask_path)
    save_binary_mask(quantum_stats["binary_mask"], quantum_mask_path)

    reconstruction_metrics = {
        "mse": mean_squared_error(image_2d, reconstructed_2d),
        "psnr": peak_signal_noise_ratio(image_2d, reconstructed_2d),
    }
    edge_metrics = {
        "mse": mean_squared_error(sobel_map, quantum_edge),
        "psnr": peak_signal_noise_ratio(sobel_map, quantum_edge),
    }
    circuit_metrics = {
        "frqi_state_preparation": evaluate_circuit_metrics(
            frqi_state_preparation(angles, num_axis_qubits)[0]
        ),
        "edge_detection_x": evaluate_circuit_metrics(edge_circuits["x"]),
        "edge_detection_y": evaluate_circuit_metrics(edge_circuits["y"]),
    }

    figure, axes = plt.subplots(1, 4, figsize=(16, 4))
    panels = (
        (image_2d, "Original Image"),
        (sobel_map, "Classical Sobel"),
        (quantum_edge, "Quantum Edge Detection"),
        (reconstructed_2d, "Reconstructed Output"),
    )
    for axis, (data, title) in zip(axes, panels):
        axis.imshow(data, cmap="gray", vmin=0.0, vmax=1.0, interpolation="nearest")
        axis.set_title(title)
        axis.axis("off")
    figure.suptitle("FRQI Quantum Image Processing Pipeline")
    figure.tight_layout()
    figure.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(figure)

    return {
        "image_source": image_path,
        "size": size,
        "mode": mode,
        "shots": shots,
        "seed": seed,
        "output_path": output_path,
        "sobel_mask_path": sobel_mask_path,
        "quantum_mask_path": quantum_mask_path,
        "classical_time": classical_time,
        "quantum_time": quantum_time,
        "reconstruction_metrics": reconstruction_metrics,
        "edge_metrics": edge_metrics,
        "sobel_statistics": sobel_stats,
        "quantum_statistics": quantum_stats,
        "circuit_metrics": circuit_metrics,
        "original": image_2d,
        "sobel": sobel_map,
        "quantum_edge": quantum_edge,
        "reconstructed": reconstructed_2d,
    }
