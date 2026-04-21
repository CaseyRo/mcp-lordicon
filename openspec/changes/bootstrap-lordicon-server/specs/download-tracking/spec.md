## ADDED Requirements

### Requirement: Explicit download-event reporting

The server SHALL expose a `track_download` tool that reports a single icon use to Lordicon's billing API. The tool SHALL NOT be invoked transitively from other tools — only the calling agent (LLM) decides when a download is real.

#### Scenario: Successful tracking returns a full event echo

- **WHEN** the LLM calls `track_download(family="wired", style="outline", index=42)`
- **THEN** the response is `DownloadTrackResult(tracked=true, family="wired", style="outline", index=42)`

#### Scenario: Never auto-invoked from search

- **WHEN** `search_icons` executes
- **THEN** no call to `track_download` or to the Lordicon download-tracking endpoint occurs as a side effect

#### Scenario: Tracking failures surface as errors, not silent successes

- **WHEN** the Lordicon tracking endpoint returns a non-2xx response after retries exhaust
- **THEN** the tool raises `ValueError` with the upstream status code rather than returning `tracked=false`

### Requirement: Usage-stats retrieval for billing visibility

The server SHALL expose `get_download_stats` to report daily free/premium download counts so that operators can monitor Lordicon Pro billing.

#### Scenario: Paginated stats returned with free/premium counts

- **WHEN** the LLM calls `get_download_stats(limit=30, page=1)`
- **THEN** the response is a pagination envelope with entries that include daily `free` and `premium` counts

#### Scenario: Limit bounds enforced

- **WHEN** the LLM calls `get_download_stats(limit=500)`
- **THEN** FastMCP raises a validation error because `limit` is bounded by `Field(ge=1, le=100)`

### Requirement: Read/write separation preserved at the module boundary

Search tools and tracking tools SHALL NOT share code paths that could cause a search to trigger a tracked event, per CDIT MCP Server Standards §7.6.

#### Scenario: Tracking module does not import search module

- **WHEN** the codebase is inspected
- **THEN** `mcp_lordicon/tools/tracking.py` has no import of `mcp_lordicon/tools/search.py` and the reverse also holds

### Requirement: Parameters validated to match upstream enums

`track_download` SHALL validate `family` and `style` against the same `Literal` types used by `search_icons`, and SHALL validate `index` as `Field(ge=1)`.

#### Scenario: Invalid family is rejected locally

- **WHEN** the LLM calls `track_download(family="unknown", style="outline", index=1)`
- **THEN** FastMCP raises a validation error before any HTTP call
