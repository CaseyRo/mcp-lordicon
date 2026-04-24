---
name: stack creation pattern
description: How to create Komodo stacks when km create doesn't support stacks — use the REST API directly
type: reference
---

`km create` only supports `api-key` and `onboarding-key`. To create a Stack programmatically:

1. Get server ID: POST `{host}/read/GetServer` with `{"server": "ubuntu-smurf-mirror"}`
2. Create stack: POST `{host}/write/CreateStack` with the stack config payload
3. Credentials from `~/.config/komodo/komodo.cli.toml` — `x-api-key` and `x-api-secret` headers

The ResourceSync approach (komodo.toml → `km execute run-sync`) also works but can fail with "cannot fork() for remote-https" transient errors on the Komodo Core host (werkstatt-1).

**Why:** Discovered during mcp-lordicon deploy 2026-04-24 when `km create --help` showed no stack subcommand.

**How to apply:** When tasked with creating a new Komodo stack via CLI/automation, skip km create and go straight to the REST API pattern above.
