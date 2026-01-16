# Obsidian Vault MCP Server

MCP server for Obsidian notes in Cursor AI.

## Quick Start

1. Build Docker image:
```bash
docker build -t obsidian-agent-mcp .
```

2. Add to Cursor MCP settings (`Settings → Features → Model Context Protocol`):

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

Example for Windows WSL:
```json
"-v", "/mnt/c/Users/username/Documents/obsidian/vault:/vault",
```

3. Restart Cursor to load the MCP server.

## Available Tools

- **vault_ls** - list folders and notes in vault
- **vault_read** - read note content
- **vault_write** - create or update notes

## Usage Example

Ask Cursor AI:
- "Show me all notes in my vault"
- "Read the contents of Daily/2026-01-17.md"
- "Create a new note called Ideas/new-project.md"
