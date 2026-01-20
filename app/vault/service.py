from __future__ import annotations

from collections.abc import Iterable
from itertools import chain
from pathlib import Path
from typing import Any


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
        except ValueError as e:
            raise ValueError("path escapes vault root") from e

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

    def glob(self, pattern: str) -> dict[str, list[str]]:
        """Find files and directories matching a glob pattern.

        Rules:
        - `pattern` must be a relative glob pattern inside the vault.
        - Hidden entries (any path component starting with ".") are excluded.
        - Files are limited to `.md`. Directories are included as-is.
        - Results are returned as relative paths from vault root.

        Examples:
        - "Ежедневные/2025/**/*.md" - all markdown files in 2025 subdirectories
        - "Дистилляция/Daily/2025-*.md" - markdown files matching date pattern
        - "**/*.md" - all markdown files recursively

        Returns:
            Dictionary with "files" and "dirs" lists of relative paths.
        """
        if not pattern or not pattern.strip():
            raise ValueError("pattern must be non-empty")

        pattern_path = Path(pattern)

        # Check that pattern doesn't escape the vault.
        if pattern_path.is_absolute() or ".." in pattern_path.parts:
            raise ValueError("pattern must be relative and not escape vault")

        # Check that pattern doesn't contain hidden path components.
        pattern_parts = (p for p in pattern_path.parts if p not in (".", ".."))
        if any(self._is_hidden(part) for part in pattern_parts):
            raise ValueError("hidden paths are not allowed in pattern")

        base = Path(self.vault_path).resolve()

        # Perform glob search from vault root
        files: list[str] = []
        dirs: list[str] = []
        matches: Iterable[Path]

        # For recursive patterns (**), split into base path and suffix pattern
        if "**" in pattern:
            # Split pattern at first **
            parts = pattern.split("**", 1)
            base_pattern = parts[0].rstrip("/")
            suffix_pattern = parts[1].lstrip("/") if len(parts) > 1 else ""

            if base_pattern:
                # Resolve base path and ensure it's inside vault
                _, base_dir = self._resolve_inside_vault(base_pattern)

                # Use rglob with suffix pattern
                if suffix_pattern:
                    matches = base_dir.rglob(suffix_pattern)
                else:
                    # Pattern ends with **, match everything recursively
                    matches = chain([base_dir], base_dir.rglob("*"))
            else:
                # Pattern starts with **, search from vault root
                matches = base.rglob(suffix_pattern if suffix_pattern else "*")
        else:
            # Non-recursive pattern, use regular glob
            matches = base.glob(pattern)

        for match in matches:
            # Ensure result is inside vault (safety check)
            try:
                relative_path = match.relative_to(base)
            except ValueError:
                # Skip if outside vault (shouldn't happen with proper pattern, but safety check)
                continue

            # Skip hidden entries
            if any(self._is_hidden(part) for part in relative_path.parts):
                continue

            # Convert to POSIX-style relative path
            posix_path = relative_path.as_posix()

            if match.is_file() and self._is_markdown(match):
                files.append(posix_path)
            elif match.is_dir():
                dirs.append(posix_path)

        # Sort for stable output
        return {
            "files": sorted(files),
            "dirs": sorted(dirs),
        }

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

    def tree(self) -> dict[str, Any]:
        """Get the complete directory tree of the vault.

        Rules:
        - Returns nested structure starting from vault root.
        - Hidden entries (starting with ".") are excluded.
        - Files are limited to `.md`. Directories are included as-is.
        - Results are sorted by name (case-insensitive).

        Returns:
            Nested dictionary structure with "name", "path", "type", and "children" keys.
            Root node has name "root", path "", and type "dir".
        """
        base = Path(self.vault_path).resolve()
        return self._build_tree(base, base, "")

    def _build_tree(self, base: Path, current: Path, relative_path: str) -> dict[str, Any]:
        """Recursively build tree structure for a directory.

        Args:
            base: Absolute path to vault root.
            current: Current directory being processed.
            relative_path: Relative path from vault root to current directory.

        Returns:
            Dictionary with tree structure for current directory.
        """
        children: list[dict[str, Any]] = []

        # Get all entries in current directory
        entries = sorted(current.iterdir(), key=lambda p: p.name.lower())

        for entry in entries:
            # Skip hidden entries
            if self._is_hidden(entry.name):
                continue

            # Calculate relative path for this entry
            entry_relative = entry.relative_to(base).as_posix()

            if entry.is_dir():
                # Recursively build tree for subdirectory
                child_tree = self._build_tree(base, entry, entry_relative)
                children.append(child_tree)
            elif entry.is_file() and self._is_markdown(entry):
                # Add markdown file
                children.append(
                    {
                        "name": entry.name,
                        "path": entry_relative,
                        "type": "file",
                    }
                )

        # Build current node
        node: dict[str, Any] = {
            "name": current.name if relative_path else "root",
            "path": relative_path,
            "type": "dir",
        }

        if children:
            node["children"] = children

        return node

    def search(self, query: str, case_sensitive: bool = False) -> dict[str, Any]:
        """Search for text in all markdown files within the vault.

        Rules:
        - Searches recursively through all `.md` files.
        - Hidden files and directories are excluded.
        - Returns matches with file path, line number, and line content.
        - Results are sorted by file path and line number.

        Args:
            query: Text to search for.
            case_sensitive: If True, search is case-sensitive (default: False).

        Returns:
            Dictionary with "matches" list and "total_files" count.
            Each match contains "path", "line" (1-based), and "content".
        """
        if not query or not query.strip():
            raise ValueError("query must be non-empty")

        base = Path(self.vault_path).resolve()
        matches: list[dict[str, Any]] = []
        processed_files = 0

        # Recursively find all markdown files
        for file_path in base.rglob("*.md"):
            # Skip hidden files
            relative_path = file_path.relative_to(base)
            if any(self._is_hidden(part) for part in relative_path.parts):
                continue

            try:
                # Read file content
                content = file_path.read_text(encoding="utf-8")
                lines = content.splitlines()
                processed_files += 1

                # Search in each line
                for line_num, line in enumerate(lines, start=1):
                    if case_sensitive:
                        found = query in line
                    else:
                        found = query.lower() in line.lower()

                    if found:
                        matches.append(
                            {
                                "path": relative_path.as_posix(),
                                "line": line_num,
                                "content": line.strip(),
                            }
                        )
            except (UnicodeDecodeError, PermissionError):
                # Skip files that can't be read
                continue

        # Sort by path and line number
        matches.sort(key=lambda m: (m["path"], m["line"]))

        return {
            "matches": matches,
            "total_files": processed_files,
        }

