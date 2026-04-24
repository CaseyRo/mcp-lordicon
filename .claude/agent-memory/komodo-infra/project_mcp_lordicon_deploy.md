---
name: mcp-lordicon deploy state
description: Deployment status and key facts for the mcp-lordicon stack on ubuntu-smurf-mirror as of 2026-04-24
type: project
---

Stack `git-mcp-lordicon` is live on `ubuntu-smurf-mirror` (Komodo stack ID: `69eb1cdec954d541ad01d5e4`).

**Why:** MCP server for Lordicon icon discovery; part of CDIT MCP fleet. Deployed 2026-04-24.

**How to apply:** When picking up future work on mcp-lordicon infra, the stack exists and is running. The git_commit is baked as `34d02dd` (SHA `34d02dd7f3aabf053b35441751e6bcc491adbab2`). Any subsequent `git push` triggers Komodo auto-pull/rebuild via webhook, but will reset git_commit to "unknown" — SSH rebuild ritual needed again after pushes.

Key facts:
- Host port: 8013, container port: 8000
- Health URL: `http://ubuntu-smurf-mirror:8013/health` → `{"status":"healthy","service":"mcp-lordicon"}`
- Detailed health (bearer): `http://ubuntu-smurf-mirror:8013/health/detail` → includes `git_commit`, `tools=4`
- Komodo variables registered: `LORDICON_TOKEN` (secret), `MCP_LORDICON_API_KEY` (secret)
- Stack compose dir on smurf: `/etc/komodo/stacks/git-mcp-lordicon/`
- SSH rebuild command: `sudo docker compose -f /etc/komodo/stacks/git-mcp-lordicon/compose.yaml --env-file /etc/komodo/stacks/git-mcp-lordicon/.env build --no-cache --build-arg GIT_COMMIT=<sha> && sudo docker compose ... up -d`
- Cloudflare Portal registration (task 12.3): NOT YET DONE — requires user to auth `claude.ai CloudFlare` MCP via `/mcp` in claude.ai, then tool call to register upstream `http://ubuntu-smurf-mirror:8013/mcp`
- ResourceSync `sync-mcp-lordicon` exists in Komodo (ID: `69eb1c91c954d541ad01d5bd`) but is in Failed state due to git clone fork error on Core host — not needed now that stack is created directly
