# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

### Not yet built
- Checks 1, 3, 4, 6, 7. See the build-state table in [README.md](README.md) — it is the honest
  state of the repo, not a roadmap.
- Check 1's third clause (*an input the class does not declare*) needs a node-schema source.
  ComfyUI serves one at `/object_info`, and this package makes no network calls by design, so
  the schema has to be injected by the caller. Unresolved, and named rather than guessed at.
- Check 5 (generator-legal frame) is **specification open**, not merely unbuilt: across 70
  recorded workflow graphs there is no dimension input to read, because every one is an
  img2img topology whose frame is inherited from the input image.
