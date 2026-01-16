<h1 align="center">Obsidian MCP Server</h1>

<p align="center">
Connect your Obsidian vault to Cursor AI - read, write, and manage notes with AI assistance.
</p>

<p align="center">
  <a href="https://github.com/tenqz/obsidian-agent/actions/workflows/lint.yml"><img src="https://github.com/tenqz/obsidian-agent/actions/workflows/lint.yml/badge.svg" alt="Lint Status"></a>
  <a href="https://github.com/tenqz/obsidian-agent/actions/workflows/tests.yml"><img src="https://github.com/tenqz/obsidian-agent/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://github.com/tenqz/obsidian-agent/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12%2B-blue" alt="Python Version"></a>
</p>

---

## ✨ Features

- 📝 **Read & Write** - Access and modify your Obsidian notes from Cursor
- 🗂️ **Navigate** - Browse folders and files in your vault
- 🤖 **AI-Powered** - Let Cursor AI help you organize and create notes
- 🐳 **Docker Ready** - Simple setup with Docker
- 🔒 **Safe** - Secure file system operations with path validation

---

## 🚀 Quick Start

### Prerequisites

- Docker installed on your system
- [Cursor](https://cursor.sh/) editor installed

### 1️⃣ Build the Docker Image

```bash
git clone https://github.com/tenqz/obsidian-agent.git
cd obsidian-agent
docker build -t obsidian-agent-mcp .
```

### 2️⃣ Configure Cursor

Open Cursor settings: **Settings → Features → Model Context Protocol**

Add this configuration (replace `/path/to/your/vault` with your actual vault path):

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

### 3️⃣ Restart Cursor

Restart Cursor to activate the MCP server. You're ready! 🎉

---

## 💡 Usage Examples

Try these commands in Cursor:

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

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Run Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov

# Run specific test file
poetry run pytest tests/test_vault_service.py
```

### Run Linters

```bash
# Check code style
poetry run ruff check .

# Auto-fix issues
poetry run ruff check --fix .

# Type checking
poetry run mypy app/
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

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VAULT_PATH` | Path to Obsidian vault | `/vault` |
| `MCP_TRANSPORT` | Transport mode (stdio/sse) | `stdio` |
| `MCP_PORT` | Port for SSE mode | `8001` |

### Docker Compose (Alternative)

For SSE mode (network access):

```yaml
services:
  mcp:
    build: .
    volumes:
      - /path/to/vault:/vault
    ports:
      - "8001:8001"
    environment:
      - MCP_TRANSPORT=sse
```

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
<summary><b>MCP server not appearing in Cursor</b></summary>

1. Verify the configuration in Cursor settings
2. Restart Cursor completely
3. Check Docker is running: `docker ps`
</details>

---

<p align="center">Made with ❤️ for the Obsidian community by Oleg Patsay</p>
