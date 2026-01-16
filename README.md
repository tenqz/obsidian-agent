## Obsidian Vault Agent

### Run (Docker Compose)

```bash
cp .env.example .env
docker compose build
docker compose up -d
curl -sS http://localhost:18080/health
docker compose down
```

Expected: `curl` returns **HTTP 200** and JSON like `{"status":"ok"}`.
