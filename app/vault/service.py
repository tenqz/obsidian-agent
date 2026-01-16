from __future__ import annotations

from pathlib import Path


class VaultService:
    """Service layer for interacting with an Obsidian vault on disk.

    This class will be used by the HTTP API layer.
    """

    def __init__(self, vault_path: str) -> None:
        self.vault_path = vault_path

    def ls(self, path: str = "") -> list[dict[str, str]]:
        """List directories and markdown files inside the vault.

        Rules:
        - `path` must be a relative path inside the vault.
        - Hidden entries (starting with ".") are excluded.
        - Files are limited to `.md`. Directories are always included.

        Returns a list of items like:
        - {"type": "dir", "name": "Daily", "path": "Daily"}
        - {"type": "file", "name": "note.md", "path": "Daily/note.md"}
        """
        base, target = self._resolve_inside_vault(path)
        self._ensure_dir(target)
        return self._list_dir(base=base, target=target)

    def _resolve_inside_vault(self, path: str) -> tuple[Path, Path]:
        """Resolve a relative path safely within the vault root.

        Returns `(base, target)` where both are absolute `Path` objects and
        `target` is guaranteed to be inside `base`.

        Raises:
        - ValueError: if `path` is absolute or escapes the vault root.
        """
        if Path(path).is_absolute():
            raise ValueError("path must be relative")

        base = Path(self.vault_path).resolve()
        target = (base / path).resolve()

        if target != base and base not in target.parents:
            raise ValueError("path escapes vault root")

        return base, target

    def _ensure_dir(self, path: Path) -> None:
        """Ensure `path` exists and is a directory.

        Raises:
        - FileNotFoundError: if the path does not exist.
        - NotADirectoryError: if the path exists but is not a directory.
        """
        if not path.exists():
            raise FileNotFoundError(str(path))
        if not path.is_dir():
            raise NotADirectoryError(str(path))

    def _ensure_file(self, path: Path) -> None:
        """Ensure `path` exists and is a file.

        Raises:
        - FileNotFoundError: if the path does not exist.
        - IsADirectoryError: if the path exists but is not a file.
        """
        if not path.exists():
            raise FileNotFoundError(str(path))
        if not path.is_file():
            raise IsADirectoryError(str(path))

    def _is_hidden(self, name: str) -> bool:
        """Return True if an entry name is considered hidden."""
        return name.startswith(".")

    def _is_markdown(self, path: Path) -> bool:
        """Return True if a filesystem path has a `.md` extension."""
        return path.suffix.lower() == ".md"

    def _to_item(self, base: Path, entry: Path, type_: str) -> dict[str, str]:
        """Convert a filesystem entry to a serializable list item.

        `path` in the result is always POSIX-like and relative to the vault root.
        """
        return {"type": type_, "name": entry.name, "path": entry.relative_to(base).as_posix()}

    def _list_dir(self, *, base: Path, target: Path) -> list[dict[str, str]]:
        """List non-hidden subdirectories and markdown files in `target`.

        - Directories are included as-is.
        - Files are included only when they have a `.md` extension.
        - Entries are sorted by case-insensitive name for stable output.
        """
        items: list[dict[str, str]] = []

        for entry in sorted(target.iterdir(), key=lambda p: p.name.lower()):
            name = entry.name
            if self._is_hidden(name):
                continue

            if entry.is_dir():
                items.append(self._to_item(base, entry, "dir"))
                continue

            if entry.is_file() and self._is_markdown(entry):
                items.append(self._to_item(base, entry, "file"))

        return items

