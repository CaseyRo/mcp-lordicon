# Deploy runbook — mcp-lordicon

Step-by-step for the 17 tasks in `openspec/changes/bootstrap-lordicon-server/tasks.md` that could not be executed during scaffolding (shell was stranded on the pre-rename path). Follow top-to-bottom. Each step maps to a checkbox in `tasks.md`; tick them as you go.

Canonical context: `CLAUDE.md` in this repo; the [Project Memory doc on Linear](https://linear.app/cdit/document/project-memory-mcp-lordicon-41db719d4532); CDIT MCP Server Standards (SiYuan `20260412124804-e6idjg9`); MCP Fleet Inventory (SiYuan `20260419121049-f9kgp49`).

---

## 0. Prereq check (one minute)

```bash
cd /Users/caseyromkes/dev/mcp-lordicon
which uv openspec gh docker km
uv --version     # expect >= 0.x
openspec --version   # expect 1.3.0
```

If any tool is missing, install it before starting. `km` is the Komodo CLI alias — if you don't have it, use the Komodo web dashboard equivalents where mentioned below.

---

## 1. External prerequisites (tasks 1.2–1.6)

**1.2 — Submit Lordicon API project for Pro verification.** Credential already stored at `op://terminal access/Lordicon API Credentials/credential`. Browse to <https://lordicon.com/account/api>, open the project, submit for Pro verification. Blocks deploy (premium-icon tracking), not dev.

**1.3 — Confirm port 8013 is free on smurf.**

```bash
km list | rg '8013'
# or via dashboard: Komodo → Servers → ubuntu-smurf-mirror → Stacks → search for :8013
```

Expect no hits. Inventory ground-truth was 2026-04-19; re-verify because days have elapsed.

**1.4 — Create the GitHub repo.**

```bash
gh repo create CaseyRo/mcp-lordicon --private --source=. --description "MCP server for Lordicon icon discovery (FastMCP 3.x)"
```

Leave private until the initial commit lands; flip to public after deploy if you want.

**1.5 — Generate the inbound bearer token.**

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Store in 1Password as `MCP_LORDICON_API_KEY` alongside the Lordicon credential. Add the same value as a Komodo variable named `MCP_LORDICON_API_KEY` (dashboard → Variables → New, or `km variable create`).

**1.6 — Register `LORDICON_TOKEN` in Komodo.** Same flow as 1.5. Value comes from 1Password (`op://terminal access/Lordicon API Credentials/credential`) via the service-worker policy — do NOT paste with the `op` CLI. Komodo variable name: `LORDICON_TOKEN`.

---

## 2. Git + uv (tasks 2.1, 2.3)

**2.1 — Init repo, first commit.**

```bash
cd /Users/caseyromkes/dev/mcp-lordicon
git init
git add -A
git commit -m "initial scaffold per bootstrap-lordicon-server

- FastMCP 3.x server with four tools (search_icons, list_variants,
  track_download, get_download_stats)
- Dual-secret auth (LORDICON_TOKEN outbound, MCP_API_KEY inbound)
- Hardened public /health, authenticated /health/detail
- Docker + Komodo (ubuntu-smurf-mirror:8013) wiring
- Full OpenSpec change artifacts under openspec/changes/bootstrap-lordicon-server/"
git branch -M main
git remote add origin git@github.com:CaseyRo/mcp-lordicon.git
```

**2.3 — Lock deps.**

```bash
uv sync
uv lock
git add uv.lock
git commit -m "add uv.lock"
```

Before pushing, run the local verification (section 3). Don't push a broken build.

---

## 3. Local verification (tasks 11.1, 11.2)

**3a — Validate OpenSpec artifacts.**

```bash
openspec validate --change bootstrap-lordicon-server
```

Expect "valid". If not, fix whatever it flags in `openspec/changes/bootstrap-lordicon-server/` before proceeding.

**3b — Run tests.**

```bash
uv run pytest -q
```

Expect six test files (`test_auth`, `test_client`, `test_health`, `test_search`, `test_tracking`, and implicitly the conftest fixtures). If anything fails, the three most likely culprits (called out in scaffolding notes):

- `test_health.py` — `TestClient(app)` may need a `with client:` block to drive FastMCP lifespan; wrap the request in `with TestClient(app) as client:` if so.
- `test_client.py` — `AsyncMock(spec=httpx.Response)` may misbehave for property access on `.content` / `.json`. Switch the resp factory to `Mock(spec=httpx.Response)` if needed.
- `_extract_src_hash` heuristic — if a real Lordicon URL doesn't match the `[a-zA-Z0-9]{4,32}` path segment expectation, the fallback `{family}-{style}-{index}` kicks in and the test still passes; tighten the regex once you see a real URL in production.

**3c — Run the server in stdio mode.**

```bash
export LORDICON_TOKEN="$(op read 'op://terminal access/Lordicon API Credentials/credential')"
# (If you don't want to use `op read` directly per policy, export LORDICON_TOKEN via your shell rc, sourced from the service worker.)
uv run mcp-lordicon
# Expected: FastMCP banner, four tools listed, stdio loop. Ctrl-C to exit.
```

**11.2 — Run the Docker build.**

```bash
export GIT_COMMIT=$(git rev-parse --short HEAD)
export MCP_API_KEY="$(security find-generic-password -s 'MCP_LORDICON_API_KEY' -w)"
# Or use the value you saved in 1Password in step 1.5.
docker compose build --build-arg GIT_COMMIT=$GIT_COMMIT
docker compose up -d
curl -s http://127.0.0.1:8013/health | jq   # expect {"status":"healthy","service":"mcp-lordicon"}
curl -s -H "Authorization: Bearer $MCP_API_KEY" http://127.0.0.1:8013/health/detail | jq
# expect full payload with version/build/git_commit/uptime_seconds/tools=4
docker compose down
```

---

## 4. Push and let Komodo deploy (tasks 12.1, 12.2)

**4a — Push to GitHub.** The Komodo git-deploy stack `git-mcp-lordicon` should already be defined via the committed `komodo.toml`. If Komodo hasn't picked up the new stack (new repo on GitHub), either:

- Apply the resource sync in Komodo (dashboard → Resources → Sync with Git) pointing at the `main` branch, OR
- Run `km resource sync` if you have it.

Then:

```bash
git push -u origin main
```

Watch the Komodo dashboard for the stack to show `Running`. Webhook-driven rebuilds on subsequent pushes.

**4b — Bake the real git commit (Standards §13 known limitation).** Komodo does not forward `--build-arg GIT_COMMIT`, so `/app/.git_commit` will be `"unknown"` until you SSH in and rebuild:

```bash
ssh ubuntu-smurf-mirror
cd /etc/komodo/stacks/git-mcp-lordicon
export GIT_COMMIT=$(git rev-parse --short HEAD)
docker compose build --build-arg GIT_COMMIT=$GIT_COMMIT
docker compose up -d --force-recreate
exit
```

Verify:

```bash
curl -s -H "Authorization: Bearer $MCP_LORDICON_API_KEY" https://mcp-lordicon.cdit-dev.de/health/detail | jq .git_commit
```

Should now match the commit you just rebuilt from.

---

## 5. Cloudflare MCP Portal (tasks 12.3, 12.4)

**5a — Register the upstream.**

Dashboard: <https://mcp.cdit-dev.de/portal> (or wherever the CDIT portal admin lives) → New Upstream:

| Field | Value |
|---|---|
| Name | `mcp-lordicon` |
| Upstream URL | `http://ubuntu-smurf-mirror:8013/mcp` |
| Bearer token | value of `MCP_LORDICON_API_KEY` |
| Enabled | ✅ |

Public URL should resolve to `https://mcp-lordicon.cdit-dev.de`. If a DNS record is missing, add the CNAME.

**5b — Verify from Claude Code (Tailscale path).**

```bash
curl -s -H "Authorization: Bearer $MCP_LORDICON_API_KEY" \
     http://ubuntu-smurf-mirror:8013/health
# expect {"status":"healthy","service":"mcp-lordicon"}
```

Then in Claude Code, add the MCP entry referencing the Tailscale URL + token, and list tools. Expect four: `search_icons`, `list_variants`, `track_download`, `get_download_stats`.

**5c — Verify from claude.ai (Portal path).** In a claude.ai conversation, confirm the four tools appear with namespace `mcp-lordicon_*`, e.g. `mcp-lordicon_search_icons`.

---

## 6. End-to-end smoke (task 12.5)

Run `search_icons(query="trophy")` from both Claude Code and claude.ai. Expect:

- Paginated envelope with `results`, `total`, `page`, `next_page`, `query`
- Each `IconResult` carries `embed.web_component`, `embed.react_player`, `embed.cdn_json_url`, `embed.cdn_src_hash`
- Paste the `web_component` string into a test HTML page with the `<lord-icon>` script loaded — the icon renders.

If it renders, the server is live.

---

## 7. Finalize documentation (task 13.3)

**7a — Add the Fleet Inventory row.** In SiYuan (`/CDIT/Engineering/MCP Fleet Inventory`), add to the "Portal-Enabled Servers" table:

| Server | Host | Komodo stack | Port | Public URL | Namespace |
|---|---|---|---|---|---|
| mcp-lordicon | ubuntu-smurf-mirror | `git-mcp-lordicon` | 8013 | https://mcp-lordicon.cdit-dev.de | `mcp-lordicon_` |

Bump "Portal-Enabled Servers (13)" heading to "(14)". Update the "Last ground-truth sync" date.

**7b — Set the Linear project to Active.** [mcp-lordicon project](https://linear.app/cdit/project/mcp-lordicon-aaf79420d446) → state: Active.

---

## 8. Archive the OpenSpec change (post-deploy wrap)

```bash
openspec validate --change bootstrap-lordicon-server
openspec status --change bootstrap-lordicon-server    # expect 49/49 done
# Then:
openspec archive --change bootstrap-lordicon-server
# or /opsx:archive from Claude Code
```

Archiving promotes deltas from `openspec/changes/bootstrap-lordicon-server/specs/` into the main `openspec/specs/` tree and moves the change into `changes/archive/`. The next change to any of these three capabilities will start from these sealed specs.

---

## Appendix: quick rollback

```bash
# Komodo dashboard → Stacks → git-mcp-lordicon → Stop
# Or:
ssh ubuntu-smurf-mirror "cd /etc/komodo/stacks/git-mcp-lordicon && docker compose down"
# Cloudflare Portal → upstream `mcp-lordicon` → Disable
```

No data to migrate — the server is a thin wrapper over `api.lordicon.com` and carries no state of its own. The `fastmcp-data` Docker volume is safe to leave in place between restarts.
