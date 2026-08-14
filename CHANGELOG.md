# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-08-14

First release. The checks, the aggregator, three surfaces over one in-process function, and the
full ship gate.

### Added
- Repo scaffold: packaging (zero runtime dependencies), MIT license, CI on `ubuntu-latest`
  across Python 3.11 and 3.12, `SECURITY.md` with the threat model.
- The halt surface — `PreflightHalt`, `Defect`, `Verdict` — carrying two laws in code rather
  than in prose: a gate `raise`s (never a bare `assert`, which `-O` deletes silently), and
  there is no skip flag. CI runs the suite three times: normally, under `python -O`, and
  under `PYTHONOPTIMIZE=1`.
- `Verdict.NOT_APPLICABLE` as a first-class result distinct from `PASS`, so a check that
  found nothing to examine cannot report that it examined something.

- **Check 2 — the inverted register scan**, in both directions. `Graph` (API-format parser),
  `AdapterRegister` (the declared reference), and `check_register_scan` with three clauses that
  report themselves: `loader_nodes`, `consumer_link`, `card_vocabulary`. A clause that cannot be
  evaluated is named as declined rather than passed.
- 70 recorded workflow graphs imported as fixtures with a provenance manifest
  (`tools/import_fixtures.py`, one-time and rig-local). The suite reads only the copies; a test
  fails if any test file names an absolute path, and another compares fixture bytes to the
  manifest digests.
- `card_aliases` on the register, because the corpus carries **two names for one adapter** — the
  same weights under a different cloud-side namespace, differing in the whole basename.
  Equivalence is declared rather than inferred: a prefix-stripping heuristic would also accept a
  wrong card whose name shared a tail.

- **Check 1 — link topology.** `self_link` and `dangling_link` build fully. `undeclared_input`
  takes an optional injected `NodeSchema` and returns NOT_APPLICABLE naming itself when none is
  supplied; a class absent from a supplied schema is reported as unknown rather than assumed to
  pass. The schema is never inferred from the corpus.
- **Check 4 — graph-saved-is-graph-submitted**, compared as parsed graphs: node sets, class
  types, input names, link targets, literal values. Numbers compare numerically, so a seed
  rendered `770700` or `770700.0` is not a change.
- **Check 5 — generator-legal frame**, against the **effective** frame per the spec's Amendment 1:
  graph literals where declared, the caller-supplied input dimensions on img2img, and
  NOT_APPLICABLE naming what it could not see otherwise. Qwen's ÷8 is the only measured family;
  six others are declared absent and return NOT_APPLICABLE rather than borrowing a divisor. ÷8
  halts, ÷16 advises.

- **`Verdict.ADVISORY`** and `merge_verdicts`, encoding Amendment 2's order
  `HALT > ADVISORY > NOT_APPLICABLE > PASS`. ADVISORY is a third thing: not a soft HALT (that
  would fire on correct work) and not a decorated PASS (that would hide what it exists to
  surface). Merging an empty sequence returns NOT_APPLICABLE, because running no checks is the
  cheapest way to build a gate that cannot fail.
- **Check 8 — the declared-envelope advisory.** Compares a graph's parameters against a cited
  envelope table per loaded checkpoint. **ADVISORY only, never HALT** — proven over all 70
  recorded graphs, over a far-out-of-band mutation, and by an AST scan proving the module
  contains no `PreflightHalt` raise at all. `EnvelopeEntry` refuses to construct an uncited row.
  Day one ships one checkpoint, `Qwen-Image-InstantX-ControlNet-Union`, verified against its live
  card on 2026-08-14.
- **The `preflight()` aggregator**, composing checks 1/2/4/5/8 through a **check registry** rather
  than a hardcoded list, so a result can enumerate its own coverage. Raises once with every defect
  from every check, carrying the full report on the exception — so there is exactly one entry
  point and no non-raising twin to reach for from a submit path.
- **The CLI verb** `comfy-preflight check`, with the repo's first exit-code contract: `0` nothing
  halted, `1` HALT, `2` usage or input error. ADVISORY and NOT_APPLICABLE exit `0` deliberately —
  a nonzero status stops a `&&` chain and would turn an advisory into a halt.
- **The MCP surface** (`python -m comfy_preflight.mcp_server`, stdio), a transport over the same
  in-process function returning its structured result verbatim. `mcp` stays an optional extra.
- **Check 5's ÷16 preference is an `ADVISORY`**, not a note on a PASS. ÷8 still halts and ÷16
  still never does — what changed is that the finding now travels as a located `Defect` a caller
  can act on instead of as prose in a field that merges into a green verdict.
- **`EntryKind.STUDIO_MEASURED`** on the envelope table: an entry may justify itself with a
  studio measurement (experiment id, record locator, measured date, finding) instead of a vendor
  citation. The two authorities are mutually exclusive by construction. **The kind ships with no
  data**, and a test asserts it stays empty.
- **`comfy-preflight check`**, the CLI verb, plus a **`comfy-preflight mcp`** verb so one frozen
  binary serves both doors with no Python on the machine.
- **`--debug`**, and an outermost guard that converts any unexpected exception into a structured
  `INTERNAL_ERROR` naming whose fault it is and what the caller may conclude. A stack trace is
  not an error message.
- **`verify.py`** — one gate: the suite in three interpreter modes, sdist + wheel, then the wheel
  installed into a clean venv running a real verb **from outside the checkout**. CI and the
  release workflow run this same command.
- **Publishing to both registries from one workflow** via OIDC trusted publishing (no tokens),
  with SHA256-verified PyInstaller binaries behind an `npx` launcher, and a version gate across
  four declaring sites.
- **Dependency auditing in CI** (`pip-audit --strict`) over the declared dependency surface.
- Logo, favicons, landing page and a five-page Starlight handbook.

### Fixed
- The `mcp` optional dependency bound was `>=1.0`, but the surface is built on
  `mcp.server.MCPServer` and 2.0 removed the 1.x `FastMCP`. A `>=1.0` bound resolves to a version
  that `ImportError`s on first use. Corrected to `>=2.0`, verified against the installed SDK.
- The absolute-path guard matched every URL scheme — `https://` ends in `s:/`, and `s` is a
  letter — so the first test file to cite a source URL failed a guard meant to catch leaked local
  paths. A drive letter is exactly one letter; the pattern now requires no letter before it.
- Printed output used em dashes, which a Windows console encodes with cp1252 and renders as
  replacement characters. Runtime strings are ASCII, checked by encoding the whole CLI rendering.
- `errors.py` pointed at `tests/test_gates_survive_O.py`, which does not exist. The guard is
  `tests/test_no_assert_in_library.py`.

### Known limits
- **Check 8's day-one entry does not carry a denoise band, and that is the arc's headline
  finding.** The band it was commissioned for — ~0.10–0.50 img2img denoise for the Qwen
  ControlNet-Union checkpoint — **is not on the model card that a research grounding attributes
  it to**, verified live on 2026-08-14 by two independent fetches. It ships as a *declared
  absence* that reports the value it cannot judge (the recorded 0.92) rather than as a band
  populated from memory. See [the build report](docs/build-report-aggregator-and-check-8.md).
- Checks 3, 6, 7. See the build-state table in [README.md](README.md) — it is the honest state of
  the repo, not a roadmap.
- Check 1 does not detect orphans (a node whose output nothing reads). A candidate clause, named
  rather than silently absent — a graph may legitimately carry one.
- Check 5 returns NOT_APPLICABLE on all 70 recorded graphs unless the caller supplies the input
  image's dimensions. Every recorded graph is an img2img topology whose frame is inherited from
  the input image, so that is the honest result rather than a gap.
