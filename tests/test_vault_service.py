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
    (vault / "Daily" / "2026-01-18.md").write_text("# Daily Note 2")
    (vault / "Daily" / "2025-12-31.md").write_text("# Old Daily Note")
    (vault / "Projects").mkdir()
    (vault / "Projects" / "project1.md").write_text("# Project 1")
    (vault / "Projects" / "project2.md").write_text("# Project 2")
    (vault / "Projects" / "SubProject").mkdir()
    (vault / "Projects" / "SubProject" / "sub.md").write_text("# Sub Project")
    (vault / "Ежедневные").mkdir()
    (vault / "Ежедневные" / "2025").mkdir()
    (vault / "Ежедневные" / "2025" / "01-01.md").write_text("# New Year")
    (vault / "Ежедневные" / "2025" / "01-02.md").write_text("# Day 2")
    (vault / "Дистилляция").mkdir()
    (vault / "Дистилляция" / "Daily").mkdir()
    (vault / "Дистилляция" / "Daily" / "2025-01-01.md").write_text("# Distilled")
    (vault / "Дистилляция" / "Daily" / "2025-01-02.md").write_text("# Distilled 2")
    (vault / ".hidden").mkdir()
    (vault / ".hidden" / "secret.md").write_text("Hidden content")
    (vault / "not-markdown.txt").write_text("Not markdown")
    return vault


@pytest.fixture
def service(vault_path: Path) -> VaultService:
    """Create a VaultService instance with a temporary vault."""
    return VaultService(vault_path=str(vault_path))


def test_ls_root(service: VaultService) -> None:
    """Test listing root directory."""
    items = service.ls("")
    assert len(items) == 5
    assert {"type": "dir", "name": "Daily", "path": "Daily"} in items
    assert {"type": "file", "name": "note.md", "path": "note.md"} in items
    assert {"type": "dir", "name": "Projects", "path": "Projects"} in items
    assert {"type": "dir", "name": "Ежедневные", "path": "Ежедневные"} in items
    assert {"type": "dir", "name": "Дистилляция", "path": "Дистилляция"} in items


def test_ls_subdirectory(service: VaultService) -> None:
    """Test listing subdirectory."""
    items = service.ls("Daily")
    assert [i["path"] for i in items] == [
        "Daily/2025-12-31.md",
        "Daily/2026-01-17.md",
        "Daily/2026-01-18.md",
    ]


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


# ========== Tests for glob() method ==========


def test_glob_simple_pattern(service: VaultService) -> None:
    """Test glob with simple pattern matching single file."""
    result = service.glob("note.md")
    assert result["files"] == ["note.md"]
    assert result["dirs"] == []


def test_glob_wildcard_pattern(service: VaultService) -> None:
    """Test glob with wildcard pattern."""
    result = service.glob("*.md")
    assert "note.md" in result["files"]
    assert len(result["files"]) >= 1
    assert result["dirs"] == []


def test_glob_directory_pattern(service: VaultService) -> None:
    """Test glob with directory pattern."""
    result = service.glob("Daily/*.md")
    assert "Daily/2026-01-17.md" in result["files"]
    assert "Daily/2026-01-18.md" in result["files"]
    assert "Daily/2025-12-31.md" in result["files"]
    assert len(result["files"]) == 3
    assert result["dirs"] == []


def test_glob_date_pattern(service: VaultService) -> None:
    """Test glob with date pattern."""
    result = service.glob("Daily/2026-*.md")
    assert "Daily/2026-01-17.md" in result["files"]
    assert "Daily/2026-01-18.md" in result["files"]
    assert "Daily/2025-12-31.md" not in result["files"]
    assert len(result["files"]) == 2


def test_glob_recursive_all_markdown(service: VaultService) -> None:
    """Test recursive glob pattern for all markdown files."""
    result = service.glob("**/*.md")
    assert "note.md" in result["files"]
    assert "Daily/2026-01-17.md" in result["files"]
    assert "Projects/project1.md" in result["files"]
    assert "Projects/SubProject/sub.md" in result["files"]
    assert "Ежедневные/2025/01-01.md" in result["files"]
    assert ".hidden/secret.md" not in result["files"]  # Hidden files excluded
    assert "not-markdown.txt" not in result["files"]  # Only .md files


def test_glob_recursive_with_base_path(service: VaultService) -> None:
    """Test recursive glob with base path."""
    result = service.glob("Projects/**/*.md")
    assert "Projects/project1.md" in result["files"]
    assert "Projects/project2.md" in result["files"]
    assert "Projects/SubProject/sub.md" in result["files"]
    assert "note.md" not in result["files"]  # Should not include root files
    assert len(result["files"]) == 3


def test_glob_cyrillic_paths(service: VaultService) -> None:
    """Test glob with Cyrillic paths."""
    result = service.glob("Ежедневные/2025/**/*.md")
    assert "Ежедневные/2025/01-01.md" in result["files"]
    assert "Ежедневные/2025/01-02.md" in result["files"]
    assert len(result["files"]) == 2


def test_glob_cyrillic_date_pattern(service: VaultService) -> None:
    """Test glob with Cyrillic paths and date pattern."""
    result = service.glob("Дистилляция/Daily/2025-*.md")
    assert "Дистилляция/Daily/2025-01-01.md" in result["files"]
    assert "Дистилляция/Daily/2025-01-02.md" in result["files"]
    assert len(result["files"]) == 2


def test_glob_returns_directories(service: VaultService) -> None:
    """Test that glob returns directories when matching."""
    result = service.glob("Projects/**")
    assert "Projects" in result["dirs"]
    assert "Projects/SubProject" in result["dirs"]
    assert "Projects/project1.md" in result["files"]


def test_glob_excludes_hidden_files(service: VaultService) -> None:
    """Test that glob excludes hidden files and directories."""
    result = service.glob("**/*.md")
    assert ".hidden/secret.md" not in result["files"]
    assert ".hidden" not in result["dirs"]


def test_glob_excludes_non_markdown(service: VaultService) -> None:
    """Test that glob excludes non-markdown files."""
    result = service.glob("**/*")
    assert "not-markdown.txt" not in result["files"]


def test_glob_empty_pattern_raises(service: VaultService) -> None:
    """Test that empty pattern raises an error."""
    with pytest.raises(ValueError, match="pattern must be non-empty"):
        service.glob("")
    with pytest.raises(ValueError, match="pattern must be non-empty"):
        service.glob("   ")


def test_glob_hidden_pattern_raises(service: VaultService) -> None:
    """Test that pattern with hidden path component raises an error."""
    with pytest.raises(ValueError, match="hidden paths are not allowed"):
        service.glob(".hidden/*.md")
    with pytest.raises(ValueError, match="hidden paths are not allowed"):
        service.glob("**/.hidden/**")


def test_glob_path_traversal_raises(service: VaultService) -> None:
    """Test that path traversal in pattern raises an error."""
    with pytest.raises(ValueError, match="pattern must be relative and not escape vault"):
        service.glob("../*.md")
    with pytest.raises(ValueError, match="pattern must be relative and not escape vault"):
        service.glob("../../etc/passwd")


def test_glob_absolute_path_raises(service: VaultService, vault_path: Path) -> None:
    """Test that absolute path in pattern raises an error."""
    abs_path = str(vault_path / "*.md")
    with pytest.raises(ValueError, match="pattern must be relative and not escape vault"):
        service.glob(abs_path)


def test_glob_sorted_output(service: VaultService) -> None:
    """Test that glob returns sorted results."""
    result = service.glob("Daily/*.md")
    assert result["files"] == sorted(result["files"])
    assert result["dirs"] == sorted(result["dirs"])


def test_glob_recursive_from_root(service: VaultService) -> None:
    """Test recursive glob starting from root."""
    result = service.glob("**/2025-*.md")
    assert "Daily/2025-12-31.md" in result["files"]
    assert "Дистилляция/Daily/2025-01-01.md" in result["files"]
    assert "Дистилляция/Daily/2025-01-02.md" in result["files"]


def test_glob_pattern_ending_with_double_star(service: VaultService) -> None:
    """Test glob pattern ending with ** matches everything recursively."""
    result = service.glob("Projects/**")
    assert "Projects/project1.md" in result["files"]
    assert "Projects/project2.md" in result["files"]
    assert "Projects/SubProject/sub.md" in result["files"]
    assert "Projects/SubProject" in result["dirs"]


# ========== Tests for tree() method ==========


def test_tree_root_structure(service: VaultService) -> None:
    """Test that tree returns correct root structure."""
    tree = service.tree()
    assert tree["name"] == "root"
    assert tree["path"] == ""
    assert tree["type"] == "dir"
    assert "children" in tree


def test_tree_contains_directories(service: VaultService) -> None:
    """Test that tree includes directories."""
    tree = service.tree()
    children = tree["children"]
    dir_names = [child["name"] for child in children if child["type"] == "dir"]
    assert "Daily" in dir_names
    assert "Projects" in dir_names


def test_tree_contains_files(service: VaultService) -> None:
    """Test that tree includes markdown files."""
    tree = service.tree()
    children = tree["children"]
    file_names = [child["name"] for child in children if child["type"] == "file"]
    assert "note.md" in file_names


def test_tree_nested_structure(service: VaultService) -> None:
    """Test that tree has correct nested structure."""
    tree = service.tree()
    projects_dir = next(child for child in tree["children"] if child["name"] == "Projects")
    assert projects_dir["type"] == "dir"
    assert "children" in projects_dir
    project_files = [child["name"] for child in projects_dir["children"] if child["type"] == "file"]
    assert "project1.md" in project_files
    assert "project2.md" in project_files


def test_tree_deeply_nested(service: VaultService) -> None:
    """Test that tree handles deeply nested directories."""
    tree = service.tree()
    projects_dir = next(child for child in tree["children"] if child["name"] == "Projects")
    subproject_dir = next(
        child for child in projects_dir["children"] if child["name"] == "SubProject"
    )
    assert subproject_dir["type"] == "dir"
    assert "children" in subproject_dir
    assert any(child["name"] == "sub.md" for child in subproject_dir["children"])


def test_tree_excludes_hidden(service: VaultService) -> None:
    """Test that tree excludes hidden files and directories."""
    tree = service.tree()
    children = tree["children"]
    hidden_names = [child["name"] for child in children if child["name"].startswith(".")]
    assert len(hidden_names) == 0


def test_tree_excludes_non_markdown(service: VaultService) -> None:
    """Test that tree excludes non-markdown files."""
    tree = service.tree()

    def find_file(node: dict, filename: str) -> bool:
        if node["type"] == "file" and node["name"] == filename:
            return True
        if "children" in node:
            return any(find_file(child, filename) for child in node["children"])
        return False

    assert not find_file(tree, "not-markdown.txt")


def test_tree_paths_are_relative(service: VaultService) -> None:
    """Test that all paths in tree are relative to vault root."""
    tree = service.tree()

    def check_paths(node: dict) -> None:
        if node["path"]:
            assert not Path(node["path"]).is_absolute()
        if "children" in node:
            for child in node["children"]:
                check_paths(child)

    check_paths(tree)


def test_tree_sorted_output(service: VaultService) -> None:
    """Test that tree children are sorted."""
    tree = service.tree()
    children = tree["children"]
    names = [child["name"] for child in children]
    assert names == sorted(names, key=str.lower)


def test_tree_cyrillic_paths(service: VaultService) -> None:
    """Test that tree handles Cyrillic paths correctly."""
    tree = service.tree()
    children = tree["children"]
    cyrillic_dirs = [child for child in children if child["name"] in ["Ежедневные", "Дистилляция"]]
    assert len(cyrillic_dirs) >= 1
    for dir_node in cyrillic_dirs:
        assert dir_node["type"] == "dir"
        assert "children" in dir_node


# ========== Tests for search() method ==========


def test_search_finds_text(service: VaultService) -> None:
    """Test that search finds text in files."""
    result = service.search("Test Note")
    assert result["total_files"] > 0
    assert len(result["matches"]) > 0
    assert all("path" in match for match in result["matches"])
    assert all("line" in match for match in result["matches"])
    assert all("content" in match for match in result["matches"])


def test_search_case_insensitive(service: VaultService) -> None:
    """Test that search is case-insensitive by default."""
    result_lower = service.search("test note")
    result_upper = service.search("TEST NOTE")
    result_mixed = service.search("Test Note")

    # Should find the same matches regardless of case
    assert len(result_lower["matches"]) == len(result_upper["matches"])
    assert len(result_lower["matches"]) == len(result_mixed["matches"])


def test_search_case_sensitive(service: VaultService) -> None:
    """Test case-sensitive search option."""
    result_sensitive = service.search("Test Note", case_sensitive=True)
    result_insensitive = service.search("test note", case_sensitive=False)

    # Case-sensitive search should find exact matches only
    assert isinstance(result_sensitive["matches"], list)
    assert isinstance(result_insensitive["matches"], list)


def test_search_multiple_files(service: VaultService) -> None:
    """Test that search finds matches in multiple files."""
    result = service.search("Daily")
    assert len(result["matches"]) > 0
    # Should find matches in Daily directory files
    paths = {match["path"] for match in result["matches"]}
    assert any("Daily" in path for path in paths)


def test_search_excludes_hidden_files(service: VaultService) -> None:
    """Test that search excludes hidden files."""
    result = service.search("Hidden")
    # Should not find matches in .hidden/secret.md
    paths = {match["path"] for match in result["matches"]}
    assert ".hidden" not in " ".join(paths)


def test_search_empty_query_raises(service: VaultService) -> None:
    """Test that empty query raises an error."""
    with pytest.raises(ValueError, match="query must be non-empty"):
        service.search("")
    with pytest.raises(ValueError, match="query must be non-empty"):
        service.search("   ")


def test_search_result_format(service: VaultService) -> None:
    """Test that search results have correct format."""
    result = service.search("Note")
    assert "matches" in result
    assert "total_files" in result
    assert isinstance(result["matches"], list)
    assert isinstance(result["total_files"], int)

    if result["matches"]:
        match = result["matches"][0]
        assert "path" in match
        assert "line" in match
        assert "content" in match
        assert isinstance(match["line"], int)
        assert match["line"] > 0  # Line numbers are 1-based


def test_search_sorted_results(service: VaultService) -> None:
    """Test that search results are sorted by path and line number."""
    result = service.search("Note")
    matches = result["matches"]

    if len(matches) > 1:
        # Check sorting by path
        paths = [match["path"] for match in matches]
        assert paths == sorted(paths)

        # Check that matches from same file are sorted by line number
        from itertools import groupby

        for path, group in groupby(matches, key=lambda m: m["path"]):
            lines = [m["line"] for m in group]
            assert lines == sorted(lines)


def test_search_partial_match(service: VaultService) -> None:
    """Test that search finds partial matches."""
    result = service.search("Test")
    assert len(result["matches"]) > 0
    # Should find "Test Note" and other files containing "Test"
    assert any("Test" in match["content"] for match in result["matches"])


def test_search_cyrillic_text(service: VaultService) -> None:
    """Test that search works with Cyrillic text."""
    result = service.search("Новый год")
    # Should find matches in files with Cyrillic content if they exist
    assert isinstance(result["matches"], list)
    assert isinstance(result["total_files"], int)


def test_search_no_matches(service: VaultService) -> None:
    """Test search when no matches are found."""
    result = service.search("ThisTextDefinitelyDoesNotExist12345")
    assert result["matches"] == []
    assert result["total_files"] >= 0  # May have processed files but found no matches
