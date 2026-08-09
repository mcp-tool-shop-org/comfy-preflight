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

### Not yet built
- All seven checks. See the build-state table in [README.md](README.md) — it is the honest
  state of the repo, not a roadmap.
- Check 5 (generator-legal frame) is **specification open**, not merely unbuilt: across 70
  recorded workflow graphs there is no dimension input to read, because every one is an
  img2img topology whose frame is inherited from the input image.
