"""Tests for VaultService."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from app.vault.service import VaultService

if TYPE_CHECKING:
    from pytest import TempPathFactory


@pytest.fixture
def vault_path(tmp_path_factory: TempPathFactory) -> Path:
    """Create a temporary vault directory for testing."""
    vault = tmp_path_factory.mktemp("vault")
    (vault / "note.md").write_text("# Test Note\n\nContent here.")
    (vault / "Daily").mkdir()
    (vault / "Daily" / "2026-01-17.md").write_text("# Daily Note")
    (vault / ".hidden").mkdir()
    (vault / ".hidden" / "secret.md").write_text("Hidden content")
    return vault


@pytest.fixture
def service(vault_path: Path) -> VaultService:
    """Create a VaultService instance with a temporary vault."""
    return VaultService(vault_path=str(vault_path))


def test_ls_root(service: VaultService) -> None:
    """Test listing root directory."""
    items = service.ls("")
    assert len(items) == 2
    assert {"type": "dir", "name": "Daily", "path": "Daily"} in items
    assert {"type": "file", "name": "note.md", "path": "note.md"} in items


def test_ls_subdirectory(service: VaultService) -> None:
    """Test listing subdirectory."""
    items = service.ls("Daily")
    assert len(items) == 1
    assert items[0]["type"] == "file"
    assert items[0]["name"] == "2026-01-17.md"


def test_ls_hidden_excluded(service: VaultService) -> None:
    """Test that hidden directories are excluded from listing."""
    items = service.ls("")
    hidden_items = [item for item in items if item["name"].startswith(".")]
    assert len(hidden_items) == 0


def test_read_file(service: VaultService) -> None:
    """Test reading a markdown file."""
    content = service.read("note.md")
    assert content == "# Test Note\n\nContent here."


def test_read_subdirectory_file(service: VaultService) -> None:
    """Test reading a file in subdirectory."""
    content = service.read("Daily/2026-01-17.md")
    assert content == "# Daily Note"


def test_read_hidden_path_raises(service: VaultService) -> None:
    """Test that reading hidden paths raises an error."""
    with pytest.raises(ValueError, match="hidden paths are not allowed"):
        service.read(".hidden/secret.md")


def test_read_nonexistent_file_raises(service: VaultService) -> None:
    """Test that reading nonexistent file raises an error."""
    with pytest.raises(FileNotFoundError):
        service.read("nonexistent.md")


def test_write_new_file(service: VaultService, vault_path: Path) -> None:
    """Test writing a new file."""
    service.write("new-note.md", "# New Note\n\nNew content.")
    assert (vault_path / "new-note.md").read_text() == "# New Note\n\nNew content."


def test_write_creates_parent_dirs(service: VaultService, vault_path: Path) -> None:
    """Test that writing creates parent directories."""
    service.write("Projects/idea.md", "# Project Idea")
    assert (vault_path / "Projects" / "idea.md").read_text() == "# Project Idea"


def test_write_overwrites_existing(service: VaultService, vault_path: Path) -> None:
    """Test that writing overwrites existing files."""
    service.write("note.md", "Updated content")
    assert (vault_path / "note.md").read_text() == "Updated content"


def test_write_hidden_path_raises(service: VaultService) -> None:
    """Test that writing to hidden paths raises an error."""
    with pytest.raises(ValueError, match="hidden paths are not allowed"):
        service.write(".hidden/note.md", "Content")


def test_write_non_markdown_raises(service: VaultService) -> None:
    """Test that writing non-markdown files raises an error."""
    with pytest.raises(ValueError, match="only .md files are allowed"):
        service.write("file.txt", "Content")


def test_path_traversal_prevented(service: VaultService) -> None:
    """Test that path traversal attacks are prevented."""
    with pytest.raises(ValueError):
        service.read("../../../../etc/passwd")
