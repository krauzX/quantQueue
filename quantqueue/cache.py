from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any

class TranspilationCache:
    """JSON-backed cache keyed by circuit representation and target settings."""
    def __init__(self, directory: str | Path = ".quantqueue-cache"):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def make_key(circuit: Any, backend_config: dict[str, Any] | None = None) -> str:
        payload = {"circuit": circuit, "backend_config": backend_config or {}}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=repr).encode()
        return hashlib.sha256(encoded).hexdigest()

    def get(self, key: str):
        path = self.directory / f"{key}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def set(self, key: str, value: Any) -> None:
        path = self.directory / f"{key}.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, sort_keys=True, default=repr), encoding="utf-8")
        temporary.replace(path)
