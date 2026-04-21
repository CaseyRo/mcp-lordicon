## ADDED Requirements

### Requirement: Concept-based icon search

The server SHALL expose a `search_icons` tool that returns matching Lordicon icons with pre-joined embed snippets so that the LLM does not need a follow-up call to obtain paste-ready code.

#### Scenario: Keyword search returns results with embed snippets

- **WHEN** the LLM calls `search_icons(query="trophy")`
- **THEN** the response contains a paginated list of `IconResult` entries, each with `family`, `style`, `index`, `name`, `title`, `premium`, `preview_url`, and a populated `embed` object with keys `web_component`, `react_player`, `cdn_json_url`, and `cdn_src_hash`

#### Scenario: Filters narrow the result set

- **WHEN** the LLM calls `search_icons(query="arrow", family="wired", style="outline", premium=false, limit=20)`
- **THEN** every returned icon satisfies the supplied filters and the response contains at most 20 items

#### Scenario: Pagination envelope always present

- **WHEN** `search_icons` returns results
- **THEN** the response uses the pagination envelope `{results, total, page, next_page, query}` per CDIT MCP Server Standards §7.3

#### Scenario: No results returns an empty envelope, not an error

- **WHEN** the query matches no icons
- **THEN** the tool returns `{results: [], total: 0, page: 1, next_page: null, query: <input>}` without raising

#### Scenario: Invalid enum value raises ValueError before any HTTP call

- **WHEN** the LLM supplies a `family` or `style` value not in the Literal type
- **THEN** the tool raises `ValueError` before contacting `api.lordicon.com`

### Requirement: Variant discovery

The server SHALL expose a `list_variants` tool returning the bounded set of family/style combinations so the LLM can pick valid filter values.

#### Scenario: Variants returned as a plain list without pagination envelope

- **WHEN** the LLM calls `list_variants()`
- **THEN** the response is a list of `VariantInfo` objects (`family`, `style`, `free`, `premium`) with no pagination envelope, per the bounded-collection exception in CDIT MCP Server Standards §7.3

#### Scenario: Variant counts are reported per plan tier

- **WHEN** a variant response is returned
- **THEN** each entry reports `free` and `premium` as independent integer counts reflecting the upstream Lordicon response

### Requirement: Parameter bounds enforced by validation

`search_icons` SHALL accept a `limit` parameter bounded by `Field(ge=1, le=50)` and a `page` parameter bounded by `Field(ge=1)`.

#### Scenario: Out-of-range limit fails before execution

- **WHEN** the LLM calls `search_icons(query="x", limit=1000)`
- **THEN** FastMCP raises a validation error before the tool body executes

### Requirement: Upstream errors surfaced as descriptive strings, not stack traces

When the Lordicon API returns an error, the tool SHALL raise a `ValueError` whose message contains the upstream status code and a truncated response body.

#### Scenario: Upstream 5xx is translated

- **WHEN** `api.lordicon.com` returns 502 and the client has exhausted retries
- **THEN** the tool raises `ValueError` with a message beginning `Upstream API error 502:` and including at most the first 200 characters of the upstream body

### Requirement: Embed fields are ready for direct paste

The `embed` object on each `IconResult` SHALL contain a valid `<lord-icon>` web-component snippet and a React `Player` snippet that a developer can paste without further editing.

#### Scenario: Web-component snippet includes src and trigger attributes

- **WHEN** an `IconResult` is returned
- **THEN** `embed.web_component` contains `<lord-icon` and `src="..."` and a `trigger="..."` attribute

#### Scenario: React snippet references a Player component

- **WHEN** an `IconResult` is returned
- **THEN** `embed.react_player` references `Player` (or an equivalent `@lordicon/react` component) and passes an icon data payload
