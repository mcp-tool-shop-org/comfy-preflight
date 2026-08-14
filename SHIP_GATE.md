# Ship Gate

> No repo is "done" until every applicable line is checked.
> Copy this into your repo root. Check items off per-release.

**Tags:** `[all]` every repo · `[npm]` `[pypi]` `[vsix]` `[desktop]` `[container]` published artifacts · `[mcp]` MCP servers · `[cli]` CLI tools

**This repo's tags:** `[all]` `[pypi]` `[npm]` `[cli]` `[mcp]`.
Detected as `[all] [pypi]`; `[npm]`, `[cli]` and `[mcp]` are added by hand because the detector
reads `pyproject.toml` and cannot see that this package also ships an npm launcher
(`package.json` + `bin/`), a console script, and a stdio MCP server. Under-tagging would have
skipped nine applicable lines.

---

## A. Security Baseline

- [x] `[all]` SECURITY.md exists (report email, supported versions, response timeline) (2026-08-14 — private advisory link, 1.0.x supported, 7-day ack / 30-day assessment)
- [x] `[all]` README includes threat model paragraph (data touched, data NOT touched, permissions required) (2026-08-14 — README "Security" + SECURITY.md "Threat model")
- [x] `[all]` No secrets, tokens, or credentials in source or diagnostics output (2026-08-14 — the package reads no credential of any kind; both registry publishes are OIDC trusted publishing and the repo has NO secrets configured, verified with `gh secret list`)
- [x] `[all]` No telemetry by default — state it explicitly even if obvious (2026-08-14 — stated in SECURITY.md; the zero-runtime-dependency rule, pinned by a test, is what makes it checkable rather than asserted)

### Default safety posture

- [ ] `[cli|mcp|desktop]` SKIP: there is no dangerous action to gate. This package is read-only on its inputs, writes nothing anywhere, and cannot submit — an `--allow-*` flag would advertise a destructive capability it does not have. The irreversible act this tool exists for is the *caller's* submission, which happens outside it.
- [x] `[cli|mcp|desktop]` File operations constrained to known directories (2026-08-14 — the CLI opens only paths named on the command line; the MCP tool takes graph JSON inline and opens no path at all, deliberately, so the server adds no filesystem-read surface)
- [x] `[mcp]` Network egress off by default (2026-08-14 — off by *construction*: no HTTP client is imported and there are zero runtime dependencies; there is no flag that turns it on)
- [x] `[mcp]` Stack traces never exposed — structured error results only (2026-08-14 — bad input raises ValueError, which the SDK returns as a structured tool error; `test_mcp_surface.py` pins that the server does not crash on it)

## B. Error Handling

- [x] `[all]` Errors follow the Structured Error Shape: `code`, `message`, `hint`, `cause?`, `retryable?` (2026-08-14 — `Defect(code, message, hint, node_id, input_name)`; `cause`/`retryable` are optional in the shape and omitted deliberately: nothing here wraps a lower error, and no defect is retryable — a graph defect does not become correct on a second run)
- [x] `[cli]` Exit codes: 0 ok · 1 user error · 2 runtime error · 3 partial success (2026-08-14 — **documented deviation, ratified**: this CLI uses 0 = nothing halted, 1 = HALT, 2 = nothing was examined. ADVISORY and NOT_APPLICABLE exit 0 because a nonzero status stops a `&&` chain and would turn an advisory into a halt; usage errors and internal errors share exit 2 because they differ in whose fault they are but not in what the caller may conclude. There is no partial success — a preflight either examined the graph or did not. Ratified by spec Amendment 3; documented in `--help`, the README and the handbook)
- [x] `[cli]` No raw stack traces without `--debug` (2026-08-14 — the outermost guard converts any unexpected exception to a structured `INTERNAL_ERROR` with a hint; `--debug` re-raises with the traceback. Two tests inject a failure at the aggregator and pin both directions)
- [x] `[mcp]` Tool errors return structured results — server never crashes on bad input (2026-08-14 — unparseable graph, malformed dims, bad consumer string and unknown register key each raise ValueError and surface as a structured tool error; tested)
- [ ] `[mcp]` SKIP: no state or config to corrupt. The server holds no state between calls, reads no config file, and writes nothing — every call is a pure function of its arguments, so there is no stale-vs-crash tradeoff to make.
- [ ] `[desktop]` SKIP: not a desktop app.
- [ ] `[vscode]` SKIP: not a VS Code extension.

## C. Operator Docs

- [x] `[all]` README is current: what it does, install, usage, supported platforms + runtime versions (2026-08-14 — Python >= 3.11, linux-x64 and win-x64 binaries; macOS explicitly named as not built, with the reason)
- [x] `[all]` CHANGELOG.md (Keep a Changelog format) (2026-08-14)
- [x] `[all]` LICENSE file present and repo states support status (2026-08-14 — MIT; support status in SECURITY.md's supported-versions table)
- [x] `[cli]` `--help` output accurate for all commands and flags (2026-08-14 — verified by running it after the `mcp` verb and `--debug` landed; the epilog carries the exit-code table and the not-the-production-gate sentence, and tests read the parser rather than the prose)
- [ ] `[cli|mcp|desktop]` SKIP: there is no logging subsystem to define levels for. The command emits one report on stdout and errors on stderr, and holds nothing secret to redact — no credential, no token, no path beyond the one the caller named. Adding silent/normal/verbose/debug levels would be inventing a surface to satisfy a checkbox. `--debug` exists for the one thing it is actually needed for: the traceback behind B3.
- [x] `[mcp]` All tools documented with description + parameters (2026-08-14 — one tool, `preflight`; description names what it composes, the merge order and the adoption contract, and the parameter schema is derived from the signature's type hints. Every parameter is documented in the handbook's reference page)
- [ ] `[complex]` SKIP: no daemon, no state file, no operational modes. There is nothing to write a daily-ops handbook about — the Starlight handbook under `site/` is the product documentation (soft gate E3), not an operations manual.

## D. Shipping Hygiene

- [x] `[all]` `verify` script exists (test + build + smoke in one command) (2026-08-14 — `python verify.py`: the suite in all three interpreter modes, sdist + wheel build, then the built wheel installed into a clean venv and run **on a real graph from outside the checkout**, including the recorded 1066 frame having to exit 1. CI and the release workflow run this same command, so none of the three can be green on something the others are not)
- [x] `[all]` Version in manifest matches git tag (2026-08-14 — four sites declare it and the release workflow fails the tag push if any disagrees; a local test catches the drift first, because the npm launcher pins an exact tag and drift ships a wrapper that 404s at a user's `npx` rather than failing loudly)
- [x] `[all]` Dependency scanning runs in CI (ecosystem-appropriate) (2026-08-14 — `pip-audit --strict` as its own CI job. The package has zero runtime dependencies; the audit covers the dev and `[mcp]` extras, which is what a user installing the extra actually gets)
- [ ] `[all]` SKIP: automated dependency updates conflict with a standing org rule. `.claude/rules/github-actions.md` says *"Do NOT add dependabot.yml unless explicitly requested"*, and this line requires one — a real standards contradiction, already recorded in shipcheck's own audit as the reason D4 stays attested. The org rule wins here; with zero runtime dependencies the exposure is the two dev extras, which the `pip-audit` job above scans on every push.
- [x] `[npm]` **Every publishable package** passes `npx @mcptoolshop/shipcheck pack` (2026-08-14 — Gate H green: 1 publishable package, tarball ships README + LICENSE, every `files[]` entry resolves)
- [x] `[npm]` `engines.node` set · `[pypi]` `python_requires` set (2026-08-14 — `engines.node >=18`; `requires-python >=3.11`)
- [x] `[npm]` Lockfile committed · `[pypi]` Clean wheel + sdist build (2026-08-14 — `package-lock.json` committed; `python -m build` produces one wheel and one sdist, verified inside `verify.py` which fails if either is missing)
- [ ] `[vsix]` SKIP: not a VS Code extension.
- [ ] `[desktop]` SKIP: not a desktop app.

## E. Identity (soft gate — does not block ship)

- [ ] `[all]` Logo in README header — in progress this arc
- [ ] `[all]` Translations (polyglot-mcp, 8 languages) — pending the advisor's handback run; translations are the advisor's to execute, not this seat's
- [ ] `[org]` Landing page (@mcptoolshop/site-theme) — in progress this arc
- [ ] `[all]` GitHub repo metadata: description, homepage, topics — in progress this arc

---

## Gate Rules

**Hard gate (A–D):** Must pass before any version is tagged or published.
If a section doesn't apply, mark `SKIP:` with justification — don't leave it unchecked.

**Soft gate (E):** Should be done. Product ships without it, but isn't "whole."

**Checking off:**
```
- [x] `[all]` SECURITY.md exists (2026-02-27)
```

**Skipping:**
```
- [ ] `[pypi]` SKIP: not a Python project
```
