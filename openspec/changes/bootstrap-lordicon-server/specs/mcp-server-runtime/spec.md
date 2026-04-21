## ADDED Requirements

### Requirement: Conformance to CDIT MCP Server Standards

The server SHALL conform to CDIT MCP Server Standards (SiYuan doc id `20260412124804-e6idjg9`) §1 (stack), §2 (project layout), §3 (`pyproject.toml`), §4 (config), §5 (HTTP client), §6 (server assembly), §7 (tool design), §8 (auth), §9 (Docker), §10 (Komodo), §11 (Portal), §13 (health/versioning). Any deviation SHALL be documented in `design.md` with rationale.

#### Scenario: Deviations recorded in design

- **WHEN** the implementation diverges from any section of the Standards
- **THEN** `openspec/changes/bootstrap-lordicon-server/design.md` contains a Decision block citing the section and rationale

### Requirement: Dual-secret authentication

The server SHALL use two distinct `SecretStr` credentials: `LORDICON_TOKEN` for outbound calls to `api.lordicon.com`, and `MCP_API_KEY` for inbound bearer verification.

#### Scenario: Missing MCP_API_KEY in HTTP mode fails startup

- **WHEN** `TRANSPORT=http` and `MCP_API_KEY` is empty
- **THEN** `Settings` validation raises a `ValueError` and the server refuses to start

#### Scenario: Stdio mode does not require MCP_API_KEY

- **WHEN** `TRANSPORT=stdio` (local development)
- **THEN** the server starts without `MCP_API_KEY` set

#### Scenario: Bearer verification uses constant-time comparison

- **WHEN** an inbound request carries a Bearer token
- **THEN** `BearerTokenVerifier.verify_token` compares against `MCP_API_KEY` using `hmac.compare_digest`

### Requirement: Public health endpoint is hardened

The server SHALL expose GET `/health` unauthenticated, returning only `{status, service}`. Version, build, git_commit, uptime, and tool count SHALL be available only through an authenticated path.

#### Scenario: Public /health hides version metadata

- **WHEN** an unauthenticated request hits `/health`
- **THEN** the response JSON contains exactly the keys `status` and `service` (values `"healthy"` and `"mcp-lordicon"`) — no `version`, `build`, `git_commit`, `uptime_seconds`, or `tools` keys

#### Scenario: Authenticated detail exposes full payload

- **WHEN** a bearer-authenticated request retrieves the detailed health payload
- **THEN** the response includes `version`, `build`, `git_commit`, `uptime_seconds`, and `tools`

### Requirement: Transport switching between stdio and HTTP

The server SHALL support `stdio` and `http` transports selected by the `TRANSPORT` environment variable.

#### Scenario: stdio for local dev

- **WHEN** `TRANSPORT=stdio` (default)
- **THEN** `main()` invokes `mcp.run()` without HTTP options

#### Scenario: http for Docker and production

- **WHEN** `TRANSPORT=http`
- **THEN** `main()` invokes `mcp.run(transport="http", host=HOST, port=PORT)` and inbound auth is enforced

### Requirement: Deployment target fixed to smurf:8013

The Komodo stack SHALL deploy to server `ubuntu-smurf-mirror` on host port `8013` mapped to container port `8000`, with resource limits of 512 MiB memory and 0.5 CPU.

#### Scenario: Stack descriptor matches target

- **WHEN** `komodo.toml` is inspected
- **THEN** `[[stack]]` contains `name = "git-mcp-lordicon"` and `[stack.config]` contains `server_id = "ubuntu-smurf-mirror"`

#### Scenario: Host port bound on all interfaces for Portal-via-Tailscale access

- **WHEN** `compose.yaml` is inspected
- **THEN** the `ports` mapping is `8013:8000` (binds all interfaces) so the Cloudflare MCP Portal can reach the container via the Tailscale hostname `ubuntu-smurf-mirror:8013`; inbound authentication is enforced at the application layer via `MCP_API_KEY`. This deviates from Standards §9's `127.0.0.1`-only example and matches the reference implementation `mcp-readwise`; the rationale is captured in `design.md` decision D9.

### Requirement: Public URL and Portal registration

The server SHALL be reachable at `https://mcp-lordicon.cdit-dev.de` via the Cloudflare MCP Portal, with namespace prefix `mcp-lordicon_` and bearer token matching `MCP_API_KEY`.

#### Scenario: Portal namespace is applied to tool names

- **WHEN** the Portal exposes tools in claude.ai
- **THEN** every tool name is prefixed with `mcp-lordicon_` (e.g., `mcp-lordicon_search_icons`)

### Requirement: Client-layer retry and backoff

The shared `LordiconClient` SHALL implement exponential backoff on HTTP 429 and up to 3 retries on 5xx and timeout errors, per CDIT MCP Server Standards §5.

#### Scenario: 429 triggers exponential backoff

- **WHEN** Lordicon returns HTTP 429
- **THEN** the client waits with exponential backoff and retries the request

#### Scenario: 5xx retried up to three times

- **WHEN** Lordicon returns HTTP 5xx
- **THEN** the client retries up to three times before raising, and the final error includes the upstream status code

### Requirement: Git-commit resolution chain

The server SHALL resolve the git commit for the detailed health payload in the order: `GIT_COMMIT` environment variable → `/app/.git_commit` file → `git rev-parse --short HEAD` → literal `"unknown"`.

#### Scenario: Environment variable wins

- **WHEN** `GIT_COMMIT=abcdef0` is set and `/app/.git_commit` contains a different value
- **THEN** the detailed health payload reports `git_commit = "abcdef0"`

#### Scenario: Fallback returns literal unknown

- **WHEN** no commit source resolves
- **THEN** the detailed health payload reports `git_commit = "unknown"` and `build` equals `version`
