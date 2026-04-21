## 1. External prerequisites

- [x] 1.1 Register a Lordicon API project at https://lordicon.com/account/api; capture the demo Bearer token in 1Password via the service-worker policy (credential reference: `op://terminal access/Lordicon API Credentials/credential`)
- [ ] 1.2 Submit the API project for Pro verification (linked to the existing Lordicon Pro subscription)
- [ ] 1.3 Re-verify port 8013 has not been claimed on `ubuntu-smurf-mirror` since 2026-04-19 (e.g., `km list`, or query the Komodo API)
- [ ] 1.4 Create the GitHub repo `CaseyRo/mcp-lordicon`
- [ ] 1.5 Generate `MCP_LORDICON_API_KEY` (32-byte random) and register it as a Komodo variable
- [ ] 1.6 Register `LORDICON_TOKEN` as a Komodo variable (value from 1Password per policy)

## 2. Repo scaffold

- [ ] 2.1 `git init`; first commit with `.gitignore`, MIT `LICENSE`, empty `README.md`, `CHANGELOG.md`
- [x] 2.2 Write `pyproject.toml` per Standards §3 (hatchling, Python 3.12+, FastMCP ≥3.2.2, httpx, Pydantic, pydantic-settings; dev group with pytest + pytest-asyncio + pytest-httpx + ruff)
- [ ] 2.3 Run `uv lock`; commit `uv.lock`
- [x] 2.4 Create package layout `mcp_lordicon/` with `__init__.py` (`__version__ = "0.1.0"`), `__main__.py` (`from mcp_lordicon.server import main; main()`), and `py.typed`
- [x] 2.5 Create empty `mcp_lordicon/models/` and `mcp_lordicon/tools/` sub-packages

## 3. Configuration and auth

- [x] 3.1 Implement `config.py`: `Settings` with `SecretStr` for `lordicon_token` and `mcp_api_key`; `Literal["stdio","http"]` transport; `host`, `port` (default 8000), `lordicon_url`; `require_api_key_for_http` model validator
- [x] 3.2 Implement `auth.py`: `BearerTokenVerifier` subclassing `TokenVerifier`, using `hmac.compare_digest`

## 4. HTTP client

- [x] 4.1 Implement `client.py`: `LordiconClient` wrapping `httpx.AsyncClient` with base URL, Bearer header injection, request timeout
- [x] 4.2 Add retry and backoff: exponential backoff on 429, up to 3 retries on 5xx/timeouts (Standards §5)
- [x] 4.3 Centralize error translation: catch `httpx.HTTPStatusError`, raise `ValueError` with status code + truncated body; never leak stack traces

## 5. Response models

- [x] 5.1 Define `models/icons.py`: `IconEmbed`, `IconResult`, `IconSearchResult`, `VariantInfo`
- [x] 5.2 Define `models/tracking.py`: `DownloadTrackResult`, `DownloadStatsDay`, `DownloadStatsResult`

## 6. Tool: search

- [x] 6.1 Implement `tools/search.py::search_icons` with `Optional[Literal[...]]` filters, `limit: Annotated[int, Field(ge=1, le=50)] = 10`, `page: Annotated[int, Field(ge=1)] = 1`, and the pre-joined `embed` field populated on every result
- [x] 6.2 Implement `tools/search.py::list_variants` returning a plain list (bounded-collection exception, §7.3)
- [x] 6.3 Write tool docstrings: mention `family='wired', style='outline'` as the common combination, note signed-URL expiry behavior, do not set silent defaults

## 7. Tool: tracking

- [x] 7.1 Implement `tools/tracking.py::track_download` as an explicit user-driven tool (never auto-invoked)
- [x] 7.2 Implement `tools/tracking.py::get_download_stats` with pagination envelope
- [x] 7.3 Verify read/write split: no import between `tools/search.py` and `tools/tracking.py` (enforced by `test_tracking.py` source inspection)

## 8. Server assembly and health

- [x] 8.1 Implement `server.py`: construct `mcp = FastMCP("mcp-lordicon", auth=_auth)`, register four tools imperatively, implement `main()` transport switch
- [x] 8.2 Add `@mcp.custom_route("/health")` returning only `{status, service}` (design D6)
- [x] 8.3 Add authenticated detailed health path (`/health/detail`) returning `version`, `build`, `git_commit`, `uptime_seconds`, `tools=4`
- [x] 8.4 Implement git-commit resolution chain (`GIT_COMMIT` env → `/app/.git_commit` → `git rev-parse` → `"unknown"`)

## 9. Docker and Komodo

- [x] 9.1 Write `Dockerfile` per §9: `python:3.12-slim`, non-root `mcp` user, `HEALTHCHECK` hitting `/health`, `ARG GIT_COMMIT` baked into `/app/.git_commit`
- [x] 9.2 Write `compose.yaml` per §9: port `8013:8000` (bind all interfaces — see design decision D9 on Portal-via-Tailscale reachability), `FASTMCP_HOME` volume, 512 MiB / 0.5 CPU limits, JSON-file log rotation (10 MB × 3)
- [x] 9.3 Write `komodo.toml` per §10: stack `git-mcp-lordicon` on `ubuntu-smurf-mirror`, webhook + auto-pull enabled, environment with `LORDICON_TOKEN`, `MCP_API_KEY = [[MCP_LORDICON_API_KEY]]`, `MCP_LORDICON_PUBLIC_URL = https://mcp-lordicon.cdit-dev.de`

## 10. Tests

- [x] 10.1 `tests/conftest.py`: shared fixtures (`sample_icon`, `sample_variant`, `sample_stats_day`) and test env var defaults
- [x] 10.2 `tests/test_search.py`: envelope shape; filters narrow results; empty-result envelope; embed fields populated; header-driven next_page calculation; src-hash extraction edge cases
- [x] 10.3 `tests/test_tracking.py`: success echo; upstream error raises `ValueError`; stats pagination envelope; module-boundary import split enforced by source inspection
- [x] 10.4 `tests/test_auth.py`: `BearerTokenVerifier` accept/reject/constant-time; HTTP without key fails `Settings` validation; stdio without key succeeds; URL scheme validation
- [x] 10.5 `tests/test_health.py`: public `/health` returns exactly `{status, service}`; `/health/detail` rejects missing/wrong bearer (401), accepts correct bearer and returns full payload with `tools=4`
- [x] 10.6 `tests/test_client.py`: 4xx translates to `ValueError`; 5xx retries `_MAX_RETRIES` times then raises; 429 retries then raises rate-limit error; transient 5xx recovers on second try; `get_with_meta` surfaces pagination headers; `post_json` handles 201-no-body; connection errors retry (Standards §5)

## 11. Local verification

- [ ] 11.1 Run `uv run mcp-lordicon` (stdio); confirm four tools register via the FastMCP inspector
- [ ] 11.2 Run `docker compose up` locally; `curl http://127.0.0.1:8013/health` returns `{status, service}`; authenticated MCP surface reachable at `http://127.0.0.1:8013/mcp`
- [ ] 11.3 From CC1 via Tailscale: `curl http://ubuntu-smurf-mirror:8013/health` returns healthy (post-deploy check)

## 12. Deploy

- [ ] 12.1 Push to `main`; confirm Komodo webhook picked up the build and the container is running
- [ ] 12.2 Run the SSH rebuild ritual on smurf to bake the real `GIT_COMMIT` (Standards §13 known limitation)
- [ ] 12.3 Register `mcp-lordicon` upstream in the Cloudflare MCP Portal dashboard (upstream `http://ubuntu-smurf-mirror:8013/mcp`, bearer token from `MCP_LORDICON_API_KEY`, enabled)
- [ ] 12.4 Verify from claude.ai: tools appear with namespace `mcp-lordicon_*`
- [ ] 12.5 End-to-end: `search_icons("trophy")` from Claude Code (Tailscale path) and claude.ai (Portal path); confirm the returned `embed.web_component` renders in a `<lord-icon>` test page

## 13. Documentation

- [x] 13.1 Write `README.md` (purpose, endpoints, env vars, local dev flow, deploy flow)
- [x] 13.2 Update the root `CLAUDE.md` to reflect the now-scaffolded service (in-repo CLAUDE.md and root CLAUDE.md are the same file at the repo root)
- [ ] 13.3 Add `mcp-lordicon` row to the MCP Fleet Inventory SiYuan doc (`/CDIT/Engineering/MCP Fleet Inventory`)
- [x] 13.4 Create the "Project Memory: mcp-lordicon" document in Linear — project at https://linear.app/cdit/project/mcp-lordicon-aaf79420d446, doc at https://linear.app/cdit/document/project-memory-mcp-lordicon-41db719d4532
