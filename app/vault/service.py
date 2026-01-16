from __future__ import annotations


class VaultService:
    """Service layer for interacting with an Obsidian vault on disk.

    This class will be used by the HTTP API layer.
    """

    def __init__(self, vault_path: str) -> None:
        self.vault_path = vault_path

