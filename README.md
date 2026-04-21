# mcp-lordicon

MCP server that wraps the [Lordicon](https://lordicon.com) REST API so LLM clients can search animated icons by concept and receive paste-ready embed snippets in the same response.

Part of the CDIT MCP fleet. Built on [FastMCP 3.x](https://gofastmcp.com). Conforms to the CDIT MCP Server Standards.

## Tools

| Tool | Purpose |
|---|---|
| `search_icons` | Keyword + filter search; returns icons with pre-joined embed code (web-component + React Player) |
| `list_variants` | Discover valid `family` / `style` combinations and free/premium counts |
| `track_download` | Report an icon use to Lordicon's billing API (call explicitly when an icon is actually embedded) |
| `get_download_stats` | Retrieve daily free/premium download counts for billing visibility |

## Local development

```bash
export LORDICON_TOKEN="your-api-bearer-token"
uv sync
uv run mcp-lordicon
```

Defaults to `TRANSPORT=stdio`. For HTTP mode (local testing of the Docker-equivalent surface):

```bash
export TRANSPORT=http
export MCP_API_KEY="some-random-string"   # required in HTTP mode
uv run mcp-lordicon
```

## Docker

```bash
docker compose up --build
# /health reachable on http://127.0.0.1:8013/health
# MCP endpoint on http://127.0.0.1:8013/mcp (bearer required)
```

## Deployment

Komodo git-deploy stack `git-mcp-lordicon` on `ubuntu-smurf-mirror`. Cloudflare MCP Portal upstream at `https://mcp-lordicon.cdit-dev.de`. See `komodo.toml` and the change artifacts under `openspec/changes/bootstrap-lordicon-server/` for the full deployment contract.

## Environment

| Variable | Required | Notes |
|---|---|---|
| `LORDICON_TOKEN` | yes | Bearer token from https://lordicon.com/account/api |
| `MCP_API_KEY` | required in HTTP mode | 32-byte random; inbound bearer for the Portal |
| `TRANSPORT` | optional | `stdio` (default) or `http` |
| `HOST` | optional | `127.0.0.1` (default) |
| `PORT` | optional | `8000` (default) — container port; host port is `8013` via compose |
| `LORDICON_URL` | optional | `https://api.lordicon.com` |
