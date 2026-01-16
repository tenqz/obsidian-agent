"""
Obsidian Vault Agent API.

Environment (reserved for next steps):
- VAULT_PATH: absolute path inside the container where the Obsidian vault is mounted.
"""

import os
from pathlib import Path

from fastapi import Body
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Query
from pydantic import BaseModel

from app.vault.service import VaultService


class HealthResponse(BaseModel):
    """Response schema for the health check endpoint."""

    status: str


class VaultListItem(BaseModel):
    """A directory entry returned by /vault/ls."""

    type: str
    name: str
    path: str


class VaultReadResponse(BaseModel):
    """Response schema for /vault/read."""

    content: str


class VaultWriteRequest(BaseModel):
    """Request schema for /vault/write."""

    content: str


class VaultWriteResponse(BaseModel):
    """Response schema for /vault/write."""

    ok: bool


app = FastAPI(
    title="Obsidian Vault Agent",
    version="0.1.0",
    description="HTTP API for an Obsidian vault agent.",
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Health check endpoint used by humans and orchestration."""

    return HealthResponse(status="ok")


@app.get("/vault/ls", response_model=list[VaultListItem], tags=["vault"])
def vault_ls(path: str = Query(default="", description="Relative path inside the vault")) -> list[VaultListItem]:
    """List directories and markdown files inside the vault."""

    # Extra guard: do not allow targeting hidden/system folders via the API.
    # (VaultService already hides entries when listing; this blocks listing a hidden folder directly.)
    if path:
        parts = Path(path).parts
        if any(p.startswith(".") for p in parts if p not in (".", "")):
            raise HTTPException(status_code=400, detail="hidden paths are not allowed")

    vault_path = os.getenv("VAULT_PATH", "/vault")
    if not Path(vault_path).exists():
        raise HTTPException(status_code=500, detail="vault path is not configured or does not exist")

    svc = VaultService(vault_path=vault_path)
    try:
        return [VaultListItem(**item) for item in svc.ls(path=path)]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="path not found") from e
    except NotADirectoryError as e:
        raise HTTPException(status_code=400, detail="path is not a directory") from e


@app.get("/vault/read", response_model=VaultReadResponse, tags=["vault"])
def vault_read(path: str = Query(..., description="Relative path inside the vault")) -> VaultReadResponse:
    """Read a markdown file inside the vault."""

    # Extra guard: do not allow targeting hidden/system files via the API.
    parts = Path(path).parts
    if any(p.startswith(".") for p in parts if p not in (".", "")):
        raise HTTPException(status_code=400, detail="hidden paths are not allowed")

    vault_path = os.getenv("VAULT_PATH", "/vault")
    if not Path(vault_path).exists():
        raise HTTPException(status_code=500, detail="vault path is not configured or does not exist")

    svc = VaultService(vault_path=vault_path)
    try:
        return VaultReadResponse(content=svc.read(path=path))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="path not found") from e
    except IsADirectoryError as e:
        raise HTTPException(status_code=400, detail="path is a directory") from e


@app.put("/vault/write", response_model=VaultWriteResponse, tags=["vault"])
def vault_write(
    path: str = Query(..., description="Relative path inside the vault"),
    body: VaultWriteRequest = Body(...),
) -> VaultWriteResponse:
    """Create or overwrite a markdown file inside the vault."""

    # Extra guard: do not allow targeting hidden/system files via the API.
    parts = Path(path).parts
    if any(p.startswith(".") for p in parts if p not in (".", "")):
        raise HTTPException(status_code=400, detail="hidden paths are not allowed")

    vault_path = os.getenv("VAULT_PATH", "/vault")
    if not Path(vault_path).exists():
        raise HTTPException(status_code=500, detail="vault path is not configured or does not exist")

    svc = VaultService(vault_path=vault_path)
    try:
        svc.write(path=path, content=body.content)
        return VaultWriteResponse(ok=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except IsADirectoryError as e:
        raise HTTPException(status_code=400, detail="path is a directory") from e
