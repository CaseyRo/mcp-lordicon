## Context

`mcp-lordicon` will be the 14th server in the CDIT MCP fleet (inventory last synced 2026-04-19 at `/CDIT/Engineering/MCP Fleet Inventory`). It wraps the Lordicon REST API (`api.lordicon.com`) so that LLM clients (Claude Code via Tailscale, claude.ai via Cloudflare Portal) can discover icons by concept and receive paste-ready embed snippets without round-tripping through the Lordicon web UI.

Authoritative build/deploy conventions live in `/CDIT/Engineering/MCP Server Standards` (SiYuan id `20260412124804-e6idjg9`). The reference implementation the team aligns to is `mcp-readwise`. Fleet SPOF is `nebula-1` (9 of 13 Portal servers); the decision to reduce that concentration is an open inventory item.

Upstream characteristics: Bearer-token auth; responses include JWT-signed download URLs for Lottie JSON / SVG variants; the Pro plan bills per premium-icon download and requires clients to self-report download events via a tracking endpoint.

## Goals / Non-Goals

**Goals:**

- LLMs can search Lordicon by concept and receive embed snippets in the same response (no follow-up "get embed" round-trip).
- Two distinct `SecretStr` credentials enforce a clean security boundary: `LORDICON_TOKEN` outbound, `MCP_API_KEY` inbound.
- Full conformance to CDIT MCP Server Standards §1–§13 with zero project-specific deviations.
- Deploy to `ubuntu-smurf-mirror` to spread load away from the nebula-1 SPOF.
- `/health` reports semver + git commit (to an authenticated caller) for reliable deploy verification.

**Non-Goals:**

- Caching Lordicon JSON/SVG. The Lordicon CDN is the source of truth; this server is a thin wrapper.
- Icon color/stroke customization. That is a client-side concern handled by `<lord-icon>` player props.
- A separate `get_embed_code(...)` tool. Embeds are returned inline with search results per §7.3.
- Multi-tenancy. One Lordicon Pro API project backs this server; there is no per-user billing split.

## Decisions

### D1. Embed code is pre-joined onto each search result, not a separate tool

**Why:** Standards §7.3 mandates joining related context into responses. The LLM's most predictable follow-up after a successful search is "give me the snippet I can paste" — serving it inline eliminates the extra call, the extra state carry, and the risk of the LLM losing the `family/style/index` tuple between calls.

**Alternatives considered:** A dedicated `get_embed(family, style, index)` tool. Rejected — doubles the call graph and adds no capability.

### D2. Start with signed API URLs in embed snippets; defer permanent CDN-hash resolution

**Why:** The Lordicon API returns JWT-signed `api.lordicon.com` URLs (time-limited) rather than the `cdn.lordicon.com/{hash}.json` pattern used in `<lord-icon src="...">`. Signed URLs work immediately but expire. Reversing the signed payload to extract the CDN hash, or maintaining a separate name-to-hash mapping, is meaningful extra surface area without confirmed demand.

**Policy:** v0.1 ships with signed URLs. The `search_icons` docstring calls out the expiry behavior explicitly. If users report expired-URL breakage in production, add a follow-up change that resolves permanent CDN hashes.

**Alternatives considered:** Ship only when permanent CDN hashes are resolved. Rejected — we ship now and iterate.

### D3. `search_icons` leaves `family` and `style` as `Optional[None]`

**Why:** Standards §7.2 — filters should be `Optional[...]` so the LLM isn't forced to guess values. Silent defaults (`family="wired", style="outline"`) hide behavior and create surprise when the LLM expects a broad search. The docstring mentions the common combination ("use `family='wired', style='outline'` for the largest animated set") as a hint rather than a default.

**Alternatives considered:** Default `family="wired", style="outline"`. Rejected — explicit hint > silent default.

### D4. `track_download` is never auto-invoked from `search_icons`

**Why:** Lordicon's billing policy says "track only when an icon is actually embedded, not when previewing." Standards §7.6 mandates a read/write split. Auto-tracking on every search would inflate billing AND violate the split.

**Implementation:** `tools/tracking.py` has no import from `tools/search.py` and vice versa; the LLM calls `track_download` explicitly when the user commits to using an icon.

### D5. Host `ubuntu-smurf-mirror`, host port `8013`, container port `8000`

**Why (host):** Fleet Inventory as of 2026-04-19 shows nebula-1 runs 9 of 13 Portal servers and is the flagged MCP SPOF. Smurf runs 2 (readwise + Zentralwerk BFF). Placing the 14th server on nebula-1 deepens the SPOF; smurf spreads load and sits next to the `mcp-readwise` reference implementation we pattern against.

**Why (port):** 8013 is unused across every host in the inventory. Maintains the 80xx convention shared by siyuan (8006), bildsprache (8007), klartext (8008), writings (8009), read-website (8010), readwise (8010 on smurf). Port 8010 is reused across hosts without conflict because each host's Docker bindings are independent.

**Alternatives considered:** `werkstatt-1` (1 server, lexoffice using host networking). Rejected — host-networking is a lexoffice special case; don't spread it.

### D6. Public `/health` returns only `{status, service}`; version/build behind auth

**Why:** Standards §13 recommends hardening public `/health` on Portal-exposed servers to reduce the fingerprinting surface (version disclosure is a reconnaissance aid). mcp-lordicon is new — starting hardened avoids a later tightening migration.

**Implementation:** Unauth GET `/health` returns `{"status": "healthy", "service": "mcp-lordicon"}`. An authenticated variant (inside the FastMCP `/mcp` surface or a bearer-protected custom route) returns the detailed payload with `version`, `build`, `git_commit`, `uptime_seconds`, and `tools`.

**Alternatives considered:** Full unauth payload (matches older reference servers). Rejected for new greenfield server.

### D7. Retry + backoff centralized in `client.py`

**Why:** Standards §5 mandates exponential backoff on HTTP 429 and up to 3 retries on 5xx/timeouts. Implementing centrally in `LordiconClient` avoids per-tool duplication and gives a single tuning point when real Lordicon rate-limit responses are observed.

**Shape:** `httpx.AsyncClient` with an explicit retry loop (exponential backoff with jitter) rather than a generic httpx transport plugin, so the backoff curve can be tuned per-endpoint if needed.

### D8. Three capability specs, not one

**Why:** `icon-discovery` and `download-tracking` are independent user-visible surfaces. `mcp-server-runtime` captures the "this server conforms to the Standards" contract as a thin pointer to the SiYuan doc so the project spec isn't a duplicate of the Standards doc. This mirrors what future CDIT MCP servers will do.

### D9. compose.yaml binds port 8013 on all interfaces, not `127.0.0.1` (deviation from Standards §9)

**Why:** Standards §9 shows `127.0.0.1:<port>:8000` as the localhost-only binding example, assuming a Cloudflare tunnel colocated with the container. CDIT's actual Portal pattern registers the **Tailscale hostname** (`http://ubuntu-smurf-mirror:8013/mcp`) as the upstream — that reach requires the container to listen on the Tailscale-visible interface, not localhost. Binding on all interfaces is what the reference implementation `mcp-readwise` does for the same reason. Inbound authentication is enforced at the application layer (`MCP_API_KEY` bearer), so all-interface binding does not weaken auth posture.

**Implication:** The Standards §9 text should be updated to reflect the Portal-via-Tailscale reality. Flagged for a follow-up to the Standards doc; this change notes the deviation in `mcp-server-runtime` spec scenario.

**Alternative considered:** Bind to 127.0.0.1 per Standards §9 and run a local cloudflared-to-container proxy. Rejected — adds an extra process per server and departs from the existing fleet's working pattern.

## Risks / Trade-offs

- **[Signed URLs expire]** → v0.1 docstring documents the behavior; follow-up change if reports come in (D2).
- **[Lordicon API rate limits are undocumented]** → Client-layer retry/backoff per §5; add 429 telemetry and tune the backoff curve after observing production behavior.
- **[Billing drift on premium icons]** → `get_download_stats` exposes daily counts; add a threshold alert post-deploy if daily premium count exceeds expected.
- **[Port 8013 could be taken in the 48h since inventory sync]** → First task in `tasks.md` re-verifies via `km list` before the first deploy.
- **[Lordicon API project demo→Pro transition is manual]** → Blocks production but not development. Dev proceeds against the demo token; swap at deploy time.
- **[Komodo git-deploy doesn't pass `--build-arg GIT_COMMIT`]** → Known Standards §13 limitation. The semver bump in `__init__.py` is the primary deploy identifier; `git_commit` resolves to `"unknown"` until the post-deploy SSH rebuild ritual runs. Accepted.
- **[Adding an internal-only tool surface to a new icon use surfaces a claude.ai dependency]** → If the Portal upstream is down, claude.ai loses icon search but Claude Code via Tailscale still works. Acceptable.

## Migration Plan

N/A — new server, no prior state. Deployment ordering:

1. Register the Lordicon API project, obtain Bearer token, submit for Pro verification.
2. Create `CaseyRo/mcp-lordicon` on GitHub.
3. Land the scaffold; validate locally via `uv run mcp-lordicon` (stdio transport).
4. Provision Komodo variables `LORDICON_TOKEN` and `MCP_LORDICON_API_KEY`.
5. Commit `komodo.toml`; push to main → Komodo webhook triggers build.
6. Register upstream in Cloudflare MCP Portal at `https://mcp-lordicon.cdit-dev.de`.
7. Verify `/health` via Tailscale; verify Portal surface from claude.ai.
8. Add the row to the MCP Fleet Inventory SiYuan doc.

Rollback: disable the Komodo stack. No data to migrate or reverse.

## Open Questions

None that block implementation. D2 / D3 / D4 / D6 are decided with explicit rationale. Operational tuning (exact retry backoff curve, premium-download alert threshold, eventual CDN-hash resolution) can be addressed post-deploy via small follow-up changes.
