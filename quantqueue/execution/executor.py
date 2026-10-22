from __future__ import annotations
import asyncio
import random
from typing import Any

class MockExecutor:
    """Dependency-free executor useful for demos, tests, and scheduler benchmarks."""
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0)
        qubits = int(payload.get("qubits", 1))
        shots = int(payload.get("shots", 1024))
        rng = random.Random(payload.get("seed", 0))
        return {"backend": "mock", "qubits": qubits, "shots": shots,
                "counts": {"0" * qubits: shots}, "sample": rng.random()}

class AerExecutor:
    """Optional Qiskit Aer adapter for simple QuantumCircuit payloads supplied directly."""
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        def _run():
            try:
                from qiskit import transpile
                from qiskit_aer import AerSimulator
            except ImportError as exc:
                raise RuntimeError("Install optional dependencies: pip install -e '.[qiskit]'") from exc
            circuit = payload.get("circuit")
            if circuit is None:
                raise ValueError("Aer backend requires payload['circuit'] to be a Qiskit QuantumCircuit")
            shots = int(payload.get("shots", 1024))
            backend = AerSimulator()
            compiled = transpile(circuit, backend)
            result = backend.run(compiled, shots=shots).result()
            return {"backend": "aer", "shots": shots, "counts": result.get_counts()}
        return await asyncio.to_thread(_run)
