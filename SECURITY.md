# Security

## Reporting

Open a private security advisory on
[the repository](https://github.com/mcp-tool-shop-org/comfy-preflight/security/advisories/new).
Please do not open a public issue for a vulnerability.

## Threat model

`comfy-preflight` reads two untrusted-ish inputs — a **workflow graph** (JSON) and a
**subject profile** (JSON) — and returns a verdict. That is the whole surface.

**What it does:**

- Parses JSON with the standard library.
- Walks the parsed structure and compares values.
- Raises a structured halt, or returns a PASS verdict.

**What it does not do, by construction:**

| | |
|---|---|
| network calls | none — no HTTP client is imported, and the package has zero runtime dependencies |
| credentials | never read. No API key, token, or `.env` is looked at |
| submission | it cannot submit. Nothing here spends a credit or contacts a provider |
| code execution | no `eval`, no `exec`, no `pickle`, no dynamic import of graph content |
| writes | the core checks are read-only on their inputs. Only check 4's sidecar helper writes, and only to a path the caller names |
| telemetry | none |

**Trust boundary.** A workflow graph is *data*, and this package treats it as data. Node
`class_type` strings and input values are compared, never dispatched on as code. A malicious
graph can at worst cause a halt or an unhelpful verdict; it cannot reach the filesystem or
the network through this package.

**Denial of service.** Graph traversal is linear in nodes × inputs on a structure already
resident in memory. Callers submitting attacker-supplied graphs of unbounded size should
bound the JSON size before parsing, as they would for any JSON input.

**What this package does not protect you from.** It is not a substitute for the provider's
own validation and does not claim to catch every wrong graph — it catches a specific set of
defects that a provider's `dry_run` demonstrably does not. See the README's build-state table
for exactly which checks exist today.
