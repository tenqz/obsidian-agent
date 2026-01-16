"""
Obsidian Vault Agent API.

Environment (reserved for next steps):
- VAULT_PATH: absolute path inside the container where the Obsidian vault is mounted.
"""

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response schema for the health check endpoint."""

    status: str


app = FastAPI(
    title="Obsidian Vault Agent",
    version="0.0.0",
    description="HTTP API for an Obsidian vault agent.",
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Health check endpoint used by humans and orchestration."""

    return HealthResponse(status="ok")

