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

    def _candidate_paths(self) -> list[Path]:
        return [
            self._key_store_path / f'{self._active_version}.key',
            self._key_store_path / 'primary' / f'{self._active_version}.key',
        ]

    def get_active_key(self) -> KeyMaterial:
        for path in self._candidate_paths():
            if path.exists():
                raw = path.read_bytes()
                if not raw:
                    raise RuntimeError(f'Key file is empty: {path}')
                return KeyMaterial(version_id=self._active_version, key_bytes=raw)
        raise RuntimeError(
            'Active key material not found for version '
            f'{self._active_version} in {self._key_store_path}',
        )
