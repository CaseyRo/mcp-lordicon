## Why

Claude Code and claude.ai cannot resolve Lordicon animated icons by concept. Every use (Tippmeister, Hauswart, and other CDIT projects that ship Lordicon embeds) forces a manual browse → copy-hash → paste-CDN-URL loop in the Lordicon web UI. An MCP server wrapping the Lordicon REST API makes the catalog searchable and embed snippets auto-generated from any MCP client.

## What Changes

- Add a new MCP server `mcp-lordicon` (FastMCP 3.x, Python 3.12, conforming to CDIT MCP Server Standards) in the new GitHub repo `CaseyRo/mcp-lordicon`.
- Expose four tools: `search_icons`, `list_variants`, `track_download`, `get_download_stats`. Search results carry pre-joined embed snippets (web-component + React player) so no follow-up call is needed to obtain paste-ready code.
- Deploy as the Komodo git-deploy stack `git-mcp-lordicon` on `ubuntu-smurf-mirror`, host port `8013` mapped to container port `8000`, with bearer-authenticated inbound and a hardened public `/health`.
- Expose publicly via a dedicated Cloudflare tunnel at `https://mcp-lordicon.cdit-dev.de` (namespace `mcp-lordicon_*`), matching the per-service tunnel pattern used by the rest of the CDIT MCP fleet.
- Introduce two new secrets: `LORDICON_TOKEN` (from a new Lordicon Pro API project) and `MCP_LORDICON_API_KEY` (Komodo-managed 32-byte random key for inbound auth).

## Capabilities

### New Capabilities

- `icon-discovery`: keyword + filter search, variant listing, and pre-joined embed-code generation for Lordicon icons.
- `download-tracking`: report per-icon download events to Lordicon's billing API and retrieve daily usage stats.
- `mcp-server-runtime`: bearer-authenticated FastMCP HTTP server with `/health`, stdio↔HTTP transport switching, and Docker/Komodo deployment conforming to the CDIT MCP Server Standards.

### Modified Capabilities

<!-- None. openspec/specs/ is empty; no prior capabilities to modify. -->

## Impact

- **New repo**: `CaseyRo/mcp-lordicon` (hatchling, uv, Dockerfile, compose.yaml, komodo.toml, tests).
- **New external dependency**: `api.lordicon.com`. Rate-limit behavior is undocumented — the shared HTTP client handles retry/backoff per Standards §5.
- **New infra**: Komodo stack on `ubuntu-smurf-mirror` (+512 MiB memory, +0.5 CPU), new Cloudflare tunnel ingress rule for `mcp-lordicon.cdit-dev.de`, new DNS record for that hostname.
- **SPOF posture**: unaffected. Deploying to smurf (currently 2 MCP servers) rather than nebula-1 (9 MCP servers) avoids worsening the flagged MCP SPOF.
- **New secrets**: `LORDICON_TOKEN` (Lordicon Pro Bearer token), `MCP_LORDICON_API_KEY` (inbound bearer). Both `SecretStr` per Standards §4.
- **Cost**: Pay-per-download on premium icons under the Lordicon Pro plan. `get_download_stats` surfaces daily counts so the spend stays observable.
- **Fleet Inventory**: adds the 14th MCP server. Inventory row to be added post-deploy.
