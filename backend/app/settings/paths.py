from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_path


@dataclass(frozen=True)
class AppPaths:
    root: Path

    @classmethod
    def from_platform(cls) -> "AppPaths":
        return cls(user_data_path("PlaylistBridge", "PlaylistBridge"))

    @property
    def secrets_file(self) -> Path:
        return self.root / "secrets.json"
