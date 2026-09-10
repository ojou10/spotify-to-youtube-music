import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


class AtomicSecretStore:
    def __init__(self, path: Path):
        self.path = path

    def read(self, key: str) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        data = json.loads(self.path.read_text(encoding="utf-8"))
        value = data.get(key)
        return value if isinstance(value, dict) else None

    def write(self, key: str, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {}
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
        data[key] = value
        with NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent, delete=False) as temp:
            json.dump(data, temp)
            temp.flush()
            os.fsync(temp.fileno())
            temporary_path = Path(temp.name)
        os.replace(temporary_path, self.path)

    def delete(self, key: str) -> None:
        data: dict[str, Any] = {}
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
        data.pop(key, None)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def keys(self, prefix: str = "") -> list[str]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [key for key in data if key.startswith(prefix)]
