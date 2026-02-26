from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KeyMaterial:
    version_id: str
    key_bytes: bytes


class FileSystemKeyStore:
    def __init__(self, key_store_path: str = './keys', active_version: str = 'P-001') -> None:
        self._key_store_path = Path(key_store_path)
        self._active_version = active_version

    def _candidate_paths(self, version_id: str) -> list[Path]:
        return [
            self._key_store_path / f'{version_id}.key',
            self._key_store_path / 'primary' / f'{version_id}.key',
        ]

    def get_key(self, version_id: str) -> KeyMaterial:
        for path in self._candidate_paths(version_id):
            if path.exists():
                raw = path.read_bytes()
                if not raw:
                    raise RuntimeError(f'Key file is empty: {path}')
                return KeyMaterial(version_id=version_id, key_bytes=raw)
        raise RuntimeError(
            'Key material not found for version '
            f'{version_id} in {self._key_store_path}',
        )

    def get_active_key(self) -> KeyMaterial:
        return self.get_key(self._active_version)
