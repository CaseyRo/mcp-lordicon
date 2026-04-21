# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository

`mcp-lordicon` — MCP server that wraps the [Lordicon](https://lordicon.com) REST API (`api.lordicon.com`) so LLM clients can search animated icons by concept and receive paste-ready embed snippets in the same response. Part of the CDIT MCP fleet; FastMCP 3.x + Python 3.12; conforms to the **CDIT MCP Server Standards** (SiYuan doc id `20260412124804-e6idjg9`). Authoritative stack/layout/auth/Docker/Komodo/`/health` conventions live in that doc — do not re-derive them here.

## Status

- **Code**: scaffolded per OpenSpec change `bootstrap-lordicon-server` (all file-based tasks complete; shell-dependent tasks pending — see `openspec/changes/bootstrap-lordicon-server/tasks.md`)
- **Git**: not yet initialized (`git init` + first commit is task 2.1)
- **Deploy**: not yet shipped. Target is Komodo stack `git-mcp-lordicon` on `ubuntu-smurf-mirror`, host port **8013** → container 8000, Cloudflare MCP Portal at `https://mcp-lordicon.cdit-dev.de`

## Tool surface (4 tools)

| Tool | Module | Purpose |
|---|---|---|
| `search_icons` | `mcp_lordicon/tools/search.py` | Keyword + filter search; returns icons with pre-joined `embed` (web-component + React Player snippets) |
| `list_variants` | `mcp_lordicon/tools/search.py` | Discover valid `family` / `style` combinations + free/premium counts |
| `track_download` | `mcp_lordicon/tools/tracking.py` | Report an icon use to Lordicon's billing API — explicit, never auto-invoked |
| `get_download_stats` | `mcp_lordicon/tools/tracking.py` | Daily free/premium download counts for billing visibility |

## Architectural invariants (enforce when editing)

- **Dual SecretStr auth**: `LORDICON_TOKEN` (outbound → `api.lordicon.com`) and `MCP_API_KEY` (inbound bearer). Both in `config.py`. HTTP mode fails startup if `MCP_API_KEY` is empty.
- **Read/write module split**: `tools/search.py` and `tools/tracking.py` must not import each other. Asserted by `tests/test_tracking.py` via source inspection (CDIT Standards §7.6, design D4).
- **Embed code is pre-joined inline in search results** — do not add a separate `get_embed_code` tool (design D1, Standards §7.3).
- **`/health` is hardened**: public `/health` returns only `{status, service}`; full payload (`version`, `build`, `git_commit`, `uptime_seconds`, `tools`) is behind bearer auth at `/health/detail` (design D6).
- **compose.yaml binds all interfaces** (`8013:8000`), NOT `127.0.0.1`. This is an intentional deviation from Standards §9 — the Cloudflare MCP Portal upstream reaches via the Tailscale hostname, so localhost-only binding would break Portal access. Rationale: design D9. Matches `mcp-readwise` reference.
- **Retry + backoff** is centralized in `client.py::_request` (exponential on 429, 3 retries on 5xx/timeouts — Standards §5). Tools must call `client.get_json` / `client.get_with_meta` / `client.post_json`, never raw `httpx`.
- **Pagination via response headers**: Lordicon returns `X-Total-Count`, `X-Page`, `X-Per-Page`. `client.get_with_meta` surfaces headers so tools can build the pagination envelope. Do not expect a JSON pagination envelope from upstream.

## Reference implementation

`/Users/caseyromkes/dev/mcp-readwise/` is the CDIT reference for pattern-matching. When in doubt about server assembly, auth construction, client retry shape, or Dockerfile/compose/komodo.toml format, look there first.

## Active change

`openspec/changes/bootstrap-lordicon-server/` — contains proposal, design, three specs (`icon-discovery`, `download-tracking`, `mcp-server-runtime`), and tasks. `/opsx:verify bootstrap-lordicon-server` to validate implementation against spec scenarios; `/opsx:archive bootstrap-lordicon-server` once done.

## Linear

- **Project:** [mcp-lordicon](https://linear.app/cdit/project/mcp-lordicon-aaf79420d446) — in team `Cdit-works`, initiative `CDiT Betrieb`, state `Planned` until deploy
- **Project Memory doc:** [Project Memory: mcp-lordicon](https://linear.app/cdit/document/project-memory-mcp-lordicon-41db719d4532) — captures D1–D9 rationale, open risks, and the "things that will surprise a future reader" list

## Outstanding work (shell / external)

These tasks require a fresh Claude Code session (the current session's Bash shell has a stranded cwd from an earlier external rename), or explicit user action:

1. **Task 1.2–1.6** — external ops: Pro verification, port re-check on smurf, `gh repo create`, Komodo variables
2. **Task 2.1** — `git init` + first commit
3. **Task 2.3** — `uv lock`, commit `uv.lock`
4. **Task 11.1–11.3** — local stdio run, `docker compose up`, Tailscale `/health` verification
5. **Task 12.1–12.5** — push to main, Komodo SSH rebuild ritual for `GIT_COMMIT`, register Cloudflare Portal upstream, end-to-end smoke via claude.ai
6. **Task 13.3–13.4** — update Fleet Inventory in SiYuan, create Linear project-memory doc

## Workflow reminders

- `/deploy` in this repo (once `git init` happens) means **stage + commit + push** — the repo is the deliverable; Komodo webhook picks up the push.
- All non-trivial changes go through OpenSpec (`/opsx:new`, `/opsx:continue`, `/opsx:apply`, `/opsx:verify`, `/opsx:archive`).
- **Never use the `op` CLI directly for 1Password CRUD** — use the 1Password service worker / service-account token. Code should reference env vars like `LORDICON_TOKEN`, not 1Password paths.
- **Never use TaskCreate for user todos** — use the Things 3 MCP (`gtd` server) for any user-facing reminder/todo.

## Context sources to pull when drafting further artifacts

- **MCP Server Standards** (SiYuan id `20260412124804-e6idjg9`)
- **MCP Fleet Inventory** (SiYuan id `20260419121049-f9kgp49`)
- **Lordicon API docs** via Context7 or `https://lordicon.com/docs/api/documentation` — training data may lag
