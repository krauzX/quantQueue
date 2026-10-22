"""Command-line entry point for the FRQI quantum image processing pipeline."""

from __future__ import annotations

import argparse

from benchmark import run_benchmark

SUPPORTED_SIZES = (8, 16, 32)
SUPPORTED_MODES = ("statevector", "sampling")
MIN_SHOTS = 10_000
MAX_SHOTS = 100_000


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "FRQI quantum image processing: quantum edge detection "
            "versus classical Sobel filtering."
        )
    )
    parser.add_argument(
        "--image",
        default="cat.png",
        help="input image path (defaults to cat.png)",
    )
    parser.add_argument(
        "--size",
        type=int,
        choices=SUPPORTED_SIZES,
        default=16,
        help="image side length: 8 (unit test), 16 (default), or 32",
    )
    parser.add_argument(
        "--mode",
        choices=SUPPORTED_MODES,
        default="statevector",
        help="statevector (exact) or sampling (shot noise)",
    )
    parser.add_argument(
        "--shots",
        type=int,
        default=MIN_SHOTS,
        help=f"shots for sampling mode ({MIN_SHOTS} to {MAX_SHOTS})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="reproducible seed",
    )
    parser.add_argument(
        "--output",
        default="qip_comparison.png",
        help="output figure path",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if not MIN_SHOTS <= arguments.shots <= MAX_SHOTS:
        raise SystemExit(
            f"--shots must lie between {MIN_SHOTS} and {MAX_SHOTS}"
        )
    results = run_benchmark(
        image_path=arguments.image,
        size=arguments.size,
        mode=arguments.mode,
        shots=arguments.shots,
        seed=arguments.seed,
        output_path=arguments.output,
    )
    print("FRQI Quantum Image Processing")
    print("=" * 38)
    print(f"image:       {results['image_source']}")
    print(f"scale:       {results['size']} x {results['size']}")
    print(f"mode:        {results['mode']}")
    if results["mode"] == "sampling":
        print(f"shots:       {results['shots']}")
    print(f"seed:        {results['seed']}")
    print()
    print(f"classical Sobel:  {results['classical_time'] * 1000:.2f} ms")
    print(f"quantum pipeline: {results['quantum_time'] * 1000:.2f} ms")
    print()
    print("reconstruction:")
    print(f"  MSE: {results['reconstruction_metrics']['mse']:.6f}")
    print(f"  PSNR: {results['reconstruction_metrics']['psnr']:.2f} dB")
    print("edge agreement vs Sobel:")
    print(f"  MSE: {results['edge_metrics']['mse']:.6f}")
    print(f"  PSNR: {results['edge_metrics']['psnr']:.2f} dB")
    print()
    print("edge measurements:")
    sobel_s = results["sobel_statistics"]
    quantum_s = results["quantum_statistics"]
    print(
        f"  Sobel:         {sobel_s['edge_pixels']} edge pixels, "
        f"mean strength {sobel_s['mean_strength']:.4f}, "
        f"density {sobel_s['edge_density']:.4f}"
    )
    print(
        f"  Quantum:       {quantum_s['edge_pixels']} edge pixels, "
        f"mean strength {quantum_s['mean_strength']:.4f}, "
        f"density {quantum_s['edge_density']:.4f}"
    )
    print()
    print(f"Sobel edge mask:   {results['sobel_mask_path']}")
    print(f"Quantum edge mask: {results['quantum_mask_path']}")
    print()
    print("circuit metrics (basis: cx, p, ry, h, x, t, tdg):")
    for name, metrics in results["circuit_metrics"].items():
        print(
            f"  {name}: depth={metrics['depth']}, "
            f"gates={metrics['gate_count']}, "
            f"cnot={metrics['cnot_count']}"
        )
    print(f"\nfigure saved to: {results['output_path']}")


if __name__ == "__main__":
    main()
