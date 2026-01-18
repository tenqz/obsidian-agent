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

### 🌐 SSE Mode Setup (ChatGPT MCP)

Perfect for ChatGPT MCP integration with OAuth 2.1 authentication.

### 1️⃣ Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit .env file
nano .env
```

Configuration for ChatGPT:
```bash
OBSIDIAN_VAULT_PATH=/path/to/your/vault
MCP_TRANSPORT=sse
MCP_PORT=8001

# OAuth 2.1 for ChatGPT (required)
MCP_OAUTH_ENABLED=true
MCP_OAUTH_ISSUER=https://your-server.com
```

**Important:**
- **HTTPS is required in production!** Use Let's Encrypt, Cloudflare, etc.
- `MCP_OAUTH_ISSUER` must be your public HTTPS URL (e.g., `https://mcp.yourdomain.com`)
- No client credentials needed - ChatGPT registers dynamically

### 2️⃣ Start Server

```bash
docker compose up -d

# Check logs
docker compose logs -f
```

You should see:
```
OAuth 2.1 (Authorization Code + PKCE) for ChatGPT MCP
OAuth issuer: https://your-server.com
Protected Resource: https://your-server.com/.well-known/oauth-protected-resource
Authorization Server: https://your-server.com/.well-known/oauth-authorization-server
Endpoints: /oauth/authorize, /oauth/token, /oauth/register
```

### 3️⃣ Configure ChatGPT

In ChatGPT MCP settings:
- **Server URL:** `https://your-server.com/sse`

That's it! ChatGPT will automatically:
1. Discover OAuth endpoints via metadata
2. Register as OAuth client (Dynamic Client Registration)
3. Perform Authorization Code flow with PKCE
4. Obtain access token
5. Connect to SSE endpoint

### 4️⃣ Verify OAuth Endpoints

```bash
# Protected Resource Metadata (RFC 9728)
curl https://your-server.com/.well-known/oauth-protected-resource

# Authorization Server Metadata (RFC 8414)
curl https://your-server.com/.well-known/oauth-authorization-server

# Check 401 response with WWW-Authenticate header
curl -i https://your-server.com/sse
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
| `MCP_OAUTH_ENABLED` | Enable OAuth 2.1 for ChatGPT | `false` |
| `MCP_OAUTH_ISSUER` | OAuth issuer (your public HTTPS URL) | `http://localhost:8001` |

### OAuth 2.1 for ChatGPT MCP

**OAuth Flow (Automatic):**
1. **Discovery** - ChatGPT fetches metadata from `/.well-known/oauth-protected-resource`
2. **Registration** - Dynamically registers via `/oauth/register` (RFC 7591)
3. **Authorization** - Authorization Code flow with PKCE (S256)
4. **Token** - Exchanges code for access token at `/oauth/token`
5. **Connect** - Uses token to connect to `/sse`

**OAuth Endpoints:**
- `/.well-known/oauth-protected-resource` - Protected Resource Metadata (RFC 9728)
- `/.well-known/oauth-authorization-server` - Authorization Server Metadata (RFC 8414)
- `/oauth/register` - Dynamic Client Registration (RFC 7591)
- `/oauth/authorize` - Authorization endpoint (OAuth 2.1)
- `/oauth/token` - Token endpoint with PKCE verification

**Security:**
- Authorization Code Flow with PKCE (S256) - industry standard
- Dynamic Client Registration - no pre-shared credentials
- Tokens expire after 1 hour
- WWW-Authenticate headers in 401 responses (RFC 6750)

**Production Requirements:**
- ✅ HTTPS mandatory (Let's Encrypt, Cloudflare)
- ✅ Public domain with valid SSL
- ✅ `MCP_OAUTH_ISSUER` = your HTTPS URL
- ✅ Port 443 open in firewall

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

This means OAuth is working correctly! ChatGPT needs to complete OAuth flow first.

**For ChatGPT:**
- Just enter your server URL: `https://your-server.com/sse`
- ChatGPT will automatically handle OAuth

**For manual testing:**
```bash
# 1. Check OAuth metadata is accessible
curl https://your-server.com/.well-known/oauth-protected-resource
curl https://your-server.com/.well-known/oauth-authorization-server

# 2. Verify 401 includes WWW-Authenticate header
curl -i https://your-server.com/sse

# Should see:
# HTTP/1.1 401 Unauthorized
# WWW-Authenticate: Bearer realm="...", resource_metadata="...", scope="mcp"
```
</details>

<details>
<summary><b>"MCP server does not implement OAuth"</b></summary>

ChatGPT can't find OAuth metadata endpoints.

**Solutions:**
```bash
# 1. Verify OAuth is enabled
docker compose exec mcp printenv | grep MCP_OAUTH

# Should show:
# MCP_OAUTH_ENABLED=true
# MCP_OAUTH_ISSUER=https://your-server.com

# 2. Test metadata endpoint
curl https://your-server.com/.well-known/oauth-protected-resource

# If 404, check:
- Server restarted after config changes
- HTTPS working correctly
- No proxy/CDN blocking .well-known paths
```
</details>

<details>
<summary><b>HTTPS/SSL certificate issues</b></summary>

OAuth 2.1 requires HTTPS in production.

**Solutions:**
1. **Let's Encrypt** (free):
```bash
# Using Certbot
sudo certbot --nginx -d your-server.com
```

2. **Cloudflare** (free):
- Add domain to Cloudflare
- Set SSL/TLS mode to "Full (strict)"
- Point A record to your server IP

3. **Testing locally**:
- For development only: `MCP_OAUTH_ISSUER=http://localhost:8001`
- ChatGPT won't accept HTTP in production!
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
