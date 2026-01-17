<h1 align="center">Obsidian MCP Server</h1>

<p align="center">
Connect your Obsidian vault to any LLM via MCP - read, write, and manage notes with AI assistance.
</p>

<p align="center">
  <a href="https://github.com/tenqz/obsidian-agent/actions/workflows/lint.yml"><img src="https://github.com/tenqz/obsidian-agent/actions/workflows/lint.yml/badge.svg" alt="Lint Status"></a>
  <a href="https://github.com/tenqz/obsidian-agent/actions/workflows/tests.yml"><img src="https://github.com/tenqz/obsidian-agent/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://github.com/tenqz/obsidian-agent/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12%2B-blue" alt="Python Version"></a>
</p>

---

## ✨ Features

- 📝 **Read & Write** - Access and modify your Obsidian notes from any LLM
- 🗂️ **Navigate** - Browse folders and files in your vault
- 🤖 **AI-Powered** - Let AI help you organize and create notes
- 🔌 **MCP Protocol** - Compatible with any MCP-supported LLM client
- 🐳 **Docker Ready** - Simple setup with Docker
- 🔒 **OAuth 2.0** - Secure authentication for network access
- ⚡ **Two Modes** - stdio for direct connection, SSE for network access

---

## 🚀 Quick Start

### Prerequisites

- Docker installed on your system
- Any MCP-compatible LLM client (Cursor, Claude Desktop, ChatGPT, etc.)

### Two Connection Modes

**stdio mode** - Direct connection for desktop clients (Cursor, Claude Desktop)
- Best for: Local development, direct LLM client integration
- Security: No network exposure, runs in isolated container

**SSE mode** - Network access via Server-Sent Events
- Best for: ChatGPT MCP, remote access, web applications
- Security: OAuth 2.0 authentication required

---

### 📟 stdio Mode Setup (Cursor, Claude Desktop)

### 1️⃣ Build the Docker Image

```bash
git clone https://github.com/tenqz/obsidian-agent.git
cd obsidian-agent
docker build -t obsidian-agent-mcp .
```

### 2️⃣ Configure Your MCP Client

Add MCP server configuration to your client's settings file.

**For Cursor:** `Settings → Features → Model Context Protocol`

**For Claude Desktop:** `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)

Example configuration (replace `/path/to/your/vault` with your actual vault path):

```json
{
  "mcpServers": {
    "obsidian-vault": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-e", "MCP_TRANSPORT=stdio",
        "-v", "/path/to/your/vault:/vault",
        "obsidian-agent-mcp"
      ]
    }
  }
}
```

**Platform-specific paths:**

| Platform | Example Path |
|----------|-------------|
| **Windows (WSL)** | `/mnt/c/Users/YourName/Documents/ObsidianVault` |
| **macOS** | `/Users/YourName/Documents/ObsidianVault` |
| **Linux** | `/home/yourname/Documents/ObsidianVault` |

### 3️⃣ Restart Your Client

Restart your MCP client to activate the server. You're ready! 🎉

---

### 🌐 SSE Mode Setup (ChatGPT, Remote Access)

Perfect for ChatGPT MCP integration or when you need network access to your vault.

### 1️⃣ Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit .env file
nano .env
```

Minimal `.env` configuration:
```bash
OBSIDIAN_VAULT_PATH=/path/to/your/vault
MCP_TRANSPORT=sse
MCP_PORT=8001

# OAuth 2.0 authentication (required for network security)
MCP_OAUTH_ENABLED=true
MCP_OAUTH_CLIENT_ID=chatgpt-mcp-client
MCP_OAUTH_CLIENT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
MCP_OAUTH_ISSUER=http://localhost:8001
```

### 2️⃣ Start Server

```bash
docker compose up -d

# Check logs
docker compose logs -f
```

Server is now running at `http://localhost:8001`

### 3️⃣ Configure ChatGPT (or other MCP client)

In your ChatGPT MCP settings:
- **Server URL:** `http://localhost:8001`
- **OAuth Token Endpoint:** `http://localhost:8001/oauth/token`
- **OAuth Metadata:** `http://localhost:8001/.well-known/oauth-authorization-server`
- **Client ID:** `chatgpt-mcp-client` (from your .env)
- **Client Secret:** Your generated secret (from .env)

ChatGPT will automatically:
1. Request access token using client credentials
2. Use token to connect to SSE endpoint
3. Refresh token when it expires (after 1 hour)

### 4️⃣ Test Connection

```bash
# Get access token
TOKEN_RESPONSE=$(curl -s -X POST http://localhost:8001/oauth/token \
  -d "grant_type=client_credentials" \
  -d "client_id=chatgpt-mcp-client" \
  -d "client_secret=your_secret_here")

echo $TOKEN_RESPONSE
# {"access_token":"...","token_type":"Bearer","expires_in":3600}

# Test SSE connection
ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -H "Authorization: Bearer $ACCESS_TOKEN" http://localhost:8001/sse
```

---

## 💡 Usage Examples

Try these commands in your LLM client:

- `"Show all notes in my vault"`
- `"Read my daily note for today"`
- `"Create a new note about project ideas"`
- `"List all notes in the Projects folder"`
- `"Update my daily template with a new section"`

---

## 🛠️ Available Tools

| Tool | Description | Example |
|------|-------------|---------|
| `vault_ls` | List folders and markdown files | List all notes in a directory |
| `vault_read` | Read note content | Read specific note |
| `vault_write` | Create or update notes | Create new note or update existing |

---

## 📦 Development

### Setup Development Environment

All development commands run inside Docker containers, so you only need Docker installed:

```bash
# Check available commands
make help
```

### Run Tests

```bash
# Run all tests with coverage
make test

# Run tests without coverage (faster)
make test-quick
```

### Run Linters

```bash
# Run all linters (ruff + mypy)
make lint

# Auto-fix and format code
make format
```

### Run All Checks

```bash
# Run linters + tests in one command
make check
```

### Docker Commands

```bash
# Build production image
make docker-build

# Start services
make docker-up

# Stop services
make docker-down

# View logs
make docker-logs
```

### Project Structure

```
obsidian-agent/
├── app/
│   ├── mcp/
│   │   └── server.py      # MCP server implementation
│   └── vault/
│       └── service.py     # Vault operations
├── tests/
│   └── test_vault_service.py
├── .github/
│   └── workflows/         # CI/CD pipelines
├── pyproject.toml         # Poetry configuration
├── Dockerfile
└── README.md
```

---

## 🔧 Configuration

### Transport Modes

| Mode | Use Case | Authentication | Connection |
|------|----------|---------------|------------|
| **stdio** | Cursor, Claude Desktop | None (isolated) | Direct stdin/stdout |
| **SSE** | ChatGPT, Remote access | OAuth 2.0 | HTTP/SSE stream |

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VAULT_PATH` | Path to Obsidian vault | `/vault` |
| `MCP_TRANSPORT` | Transport mode (stdio/sse) | `stdio` |
| `MCP_PORT` | Port for SSE mode | `8001` |
| `MCP_OAUTH_ENABLED` | Enable OAuth 2.0 authentication | `false` |
| `MCP_OAUTH_CLIENT_ID` | OAuth client ID (required if OAuth enabled) | - |
| `MCP_OAUTH_CLIENT_SECRET` | OAuth client secret (required if OAuth enabled) | - |
| `MCP_OAUTH_ISSUER` | OAuth issuer URL (your server address) | `http://localhost:8001` |

### OAuth 2.0 Details

**Authentication Flow:**
1. Client sends `client_id` and `client_secret` to `/oauth/token`
2. Server returns `access_token` (valid for 1 hour)
3. Client uses token in `Authorization: Bearer <token>` header
4. Server validates token before allowing SSE connection

**OAuth Endpoints:**
- Token endpoint: `POST /oauth/token`
- Metadata: `GET /.well-known/oauth-authorization-server`
- Protected: `GET /sse` (requires valid access token)

**Generate secure client secret:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Security notes:**
- Tokens expire after 3600 seconds (1 hour)
- Expired tokens are automatically cleaned from memory
- For production, use HTTPS and keep secrets secure
- Without OAuth enabled, SSE server runs without authentication (not recommended)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 🐛 Troubleshooting

<details>
<summary><b>Docker image not found</b></summary>

Make sure you've built the image:
```bash
docker build -t obsidian-agent-mcp .
```
</details>

<details>
<summary><b>Permission denied on vault</b></summary>

Check that Docker has access to the vault directory. On Windows/Mac, ensure the path is shared in Docker Desktop settings.
</details>

<details>
<summary><b>MCP server not appearing in your client</b></summary>

1. Verify the configuration in your MCP client settings
2. Restart your client completely
3. Check Docker is running: `docker ps`
4. Check server logs: `docker logs <container-name>`
</details>

<details>
<summary><b>401 Unauthorized error in SSE mode</b></summary>

Make sure OAuth is enabled and you're using a valid access token:

```bash
# Check OAuth configuration
docker compose exec mcp printenv | grep MCP_OAUTH

# Get access token
curl -X POST http://localhost:8001/oauth/token \
  -d "grant_type=client_credentials" \
  -d "client_id=your_client_id" \
  -d "client_secret=your_secret"

# Test with token
curl -H "Authorization: Bearer <access_token>" http://localhost:8001/sse
```
</details>

<details>
<summary><b>SSE connection timeout or drops</b></summary>

This is normal for Server-Sent Events connections:
- SSE maintains long-lived HTTP connections
- Connection may timeout after inactivity (configure in your proxy/firewall)
- Client will automatically reconnect when needed
- Check that no firewall is blocking the connection
</details>

<details>
<summary><b>OAuth token expired</b></summary>

Access tokens expire after 1 hour (3600 seconds). Solutions:

1. **For manual testing:** Get a new token:
```bash
curl -X POST http://localhost:8001/oauth/token \
  -d "grant_type=client_credentials" \
  -d "client_id=your_client_id" \
  -d "client_secret=your_secret"
```

2. **For ChatGPT/automated clients:** They automatically refresh tokens
3. **Check token expiration:** Tokens include `expires_in` field in response
</details>

<details>
<summary><b>Server not starting or crashes</b></summary>

Check the logs for specific errors:

```bash
# Docker compose logs
docker compose logs mcp

# Check if port is already in use
lsof -i :8001  # Linux/Mac
netstat -ano | findstr :8001  # Windows

# Rebuild image if code changed
docker compose down
docker compose up -d --build
```

Common issues:
- Port 8001 already in use (change `MCP_PORT` in .env)
- Invalid vault path (check `OBSIDIAN_VAULT_PATH`)
- Missing OAuth credentials when `MCP_OAUTH_ENABLED=true`
</details>

---

<p align="center">Made with ❤️ for the Obsidian community by Oleg Patsay</p>
