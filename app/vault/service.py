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

    def read(self, path: str) -> str:
        """Read a markdown file inside the vault and return its content.

        Rules:
        - `path` must be a relative path inside the vault.
        - Hidden entries (any path component starting with ".") are excluded.
        - Only `.md` files are allowed.
        """
        if not path or not path.strip():
            raise ValueError("path must be non-empty")

        relative = Path(path)
        if any(self._is_hidden(part) for part in relative.parts):
            raise ValueError("hidden paths are not allowed")

        base, target = self._resolve_inside_vault(path)
        self._ensure_file(target)

        if not self._is_markdown(target):
            raise ValueError("only .md files are allowed")

        return target.read_text(encoding="utf-8")

    def write(self, path: str, content: str) -> None:
        """Write markdown content to a file inside the vault.

        Rules:
        - `path` must be a relative path inside the vault.
        - Hidden entries (any path component starting with ".") are excluded.
        - Only `.md` files are allowed.
        - Parent directories are created automatically.
        - Existing files are overwritten.
        """
        if not path or not path.strip():
            raise ValueError("path must be non-empty")

        relative = Path(path)
        if any(self._is_hidden(part) for part in relative.parts):
            raise ValueError("hidden paths are not allowed")

        base, target = self._resolve_inside_vault(path)

        if not self._is_markdown(target):
            raise ValueError("only .md files are allowed")

        if target.exists() and target.is_dir():
            raise IsADirectoryError(str(target))

        target.parent.mkdir(parents=True, exist_ok=True)

        # Ensure parent directory stays inside the vault root.
        if target.parent != base and base not in target.parent.parents:
            raise ValueError("path escapes vault root")

        target.write_text(content, encoding="utf-8")

    def _resolve_inside_vault(self, path: str) -> tuple[Path, Path]:
        """Resolve a user-supplied relative path inside the vault.

        This helper intentionally does NOT call `resolve()` on the target path.
        Calling `resolve()` would dereference symlinks / normalize `..` which can
        change the meaning of the path and potentially allow escaping the vault.

        Returns:
            (base, target) where:
            - base is an absolute resolved vault root.
            - target is the joined path (base / path), kept as-is.

        Raises:
            ValueError: if `path` is absolute or would escape the vault root.
        """
        if Path(path).is_absolute():
            raise ValueError("path must be relative")

        base = Path(self.vault_path).resolve()
        target = base / path

        # Проверка на выход за пределы vault
        try:
            target.relative_to(base)
        except ValueError:
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

