# Security

## Reporting

Open a private security advisory on
[the repository](https://github.com/mcp-tool-shop-org/comfy-preflight/security/advisories/new).
Please do not open a public issue for a vulnerability.

**Response timeline.** Acknowledgement within 7 days; an assessment with a fix or a stated
decision not to fix within 30 days. This is a small tool maintained by one studio — the timeline
is what is actually promised, not a corporate SLA copied in.

**Supported versions.**

| version | supported |
|---|---|
| 1.0.x | ✅ current — fixes land here |
| < 1.0 | ❌ never released |

Only the latest minor is supported. There is no long-term-support branch and none is implied.

## The framing that governs this whole package

**Submission is the irreversible act with no real undo, and a preflight is a compensator you
run BEFORE instead of after.**

A completed cloud job is billed. The only compensator afterwards is *cancel it if it is still
queued, otherwise none* — which is not much of a compensator. Everything below follows from
that: this package exists to be run before the irreversible step, so it must not itself do
anything irreversible, reach anything it does not need, or become a thing a caller has to trust
with credentials.

## Threat model

`comfy-preflight` reads two untrusted-ish inputs — a **workflow graph** (JSON) and a **subject
profile** (JSON) — and returns a verdict. That is the whole surface.

**What it does:**

- Parses JSON with the standard library.
- Walks the parsed structure and compares values.
- Raises a structured halt, or returns a PASS / ADVISORY / NOT_APPLICABLE verdict.

**What it does not do, by construction:**

| | |
|---|---|
| network calls | none — no HTTP client is imported, and the package has zero runtime dependencies |
| credentials | never read. No API key, token, or `.env` is looked at |
| submission | it cannot submit. Nothing here spends a credit or contacts a provider |
| code execution | no `eval`, no `exec`, no `pickle`, no dynamic import of graph content |
| writes | every check is read-only on its inputs. The package writes nothing, anywhere |
| telemetry | **none.** No analytics, no phone-home, no usage counter, no crash reporter — stated explicitly because "we didn't add any" is not a guarantee a reader can check, and the zero-dependency rule is what makes it one |

**Data touched.** The graph JSON and profile JSON the caller passes, in memory. On the CLI, the
file paths the caller names on the command line and nothing else. **Data NOT touched:** the
filesystem beyond those named paths, the network, the environment beyond `PYTHONOPTIMIZE`, and
any image — this package never decodes one, which is why check 5 takes dimensions as a parameter
rather than reading a file.

**Permissions required.** Read access to the graph file the caller names. Nothing else. No
elevation, no network capability, no credential store.

**Trust boundary.** A workflow graph is *data*, and this package treats it as data. Node
`class_type` strings and input values are compared, never dispatched on as code. A malicious
graph can at worst cause a halt or an unhelpful verdict; it cannot reach the filesystem or the
network through this package.

**Dangerous actions.** There are none to gate. This package performs no destructive, stateful,
or irreversible operation, so it ships no `--allow-*` flag — an `--allow-` flag on a read-only
tool would suggest a capability it does not have.

**Errors never leak a stack trace.** An unexpected failure is reported as a structured
`INTERNAL_ERROR` with a hint, and exits 2 — the code that means *nothing was examined*. The
traceback is available behind `--debug` for a developer and is never shown to a user by default.
Over MCP, bad input returns a structured tool error; the server does not crash on it.

**Denial of service.** Graph traversal is linear in nodes × inputs on a structure already
resident in memory. Callers submitting attacker-supplied graphs of unbounded size should bound
the JSON size before parsing, as they would for any JSON input.

## The npx launcher

`npx @mcptoolshop/comfy-preflight` downloads a PyInstaller binary from this repository's GitHub
Release and **verifies its SHA256 against the `checksums-<version>.txt` published in that same
release** before executing it. The launcher pins an exact tag, and the release workflow fails if
any of the four version-declaring sites disagrees with it — so the wrapper cannot be pointed at
a release it was not built for. Both registry publishes use OIDC trusted publishing: this
repository holds **no npm or PyPI token**, and none should ever be added to it.

## What this package does not protect you from

It is not a substitute for the provider's own validation and does not claim to catch every wrong
graph — it catches a specific set of defects that a provider's `dry_run` demonstrably does not.
See the README's build-state table for exactly which checks exist today, and note that check 8
is an **advisory** that never halts.
