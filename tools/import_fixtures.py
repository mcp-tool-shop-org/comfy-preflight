"""ONE-TIME, RIG-LOCAL fixture import. Not invoked by the test suite, ever.

Copies recorded ComfyUI workflow graphs into `tests/fixtures/graphs/` and writes a manifest
recording each file's origin and sha256.

**Why the copy exists at all.** The source trees are not in git and have no revert. A test
suite that read them directly would (a) depend on one rig's directory layout, and (b) put a
read path into trees that three consecutive rulings had executors sha256-manifest to protect.
Copies are ~3 KB each; the whole set is under 250 KB. Reading the source at test time is
forbidden, and `tests/test_fixtures_are_self_contained.py` fails if any test references an
absolute source path.

**Read-only on the source, by construction.** This script opens source files with mode 'rb'
and writes only under `tests/fixtures/`. Nothing here creates, moves or deletes anything in
the source trees.

**Self-reference.** The importer's own output lives in `tests/fixtures/`, and its scan roots
are outside that directory — so a second run cannot ingest the first run's output. That
exclusion is by construction rather than by filter, because a filter is a thing someone edits.

Usage (rig-local):
    python tools/import_fixtures.py --check      # report what would change, write nothing
    python tools/import_fixtures.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
DEST = REPO / "tests" / "fixtures" / "graphs"
MANIFEST = REPO / "tests" / "fixtures" / "MANIFEST.json"

# Rig-local sources. Absent on any other machine, which is why this is a one-time tool.
SOURCES = [
    pathlib.Path(r"E:\AI\training"),
    pathlib.Path(r"E:\AI\facet\docs\experiments"),
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def flat_name(path: pathlib.Path, root: pathlib.Path) -> str:
    """A unique, filesystem-safe name that keeps the origin readable.

    Basenames collide across source directories (several `workflow_1.json`), so the relative
    path is flattened rather than the basename taken.
    """
    rel = path.relative_to(root)
    return "__".join(rel.parts).replace(" ", "_")


def discover() -> list[tuple[pathlib.Path, pathlib.Path]]:
    found: list[tuple[pathlib.Path, pathlib.Path]] = []
    for root in SOURCES:
        if not root.exists():
            print(f"  SKIP (absent on this machine): {root}")
            continue
        for path in sorted(root.rglob("*.json")):
            name = path.name.lower()
            if "workflow" not in name:
                continue
            found.append((path, root))
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="report only; write nothing")
    args = ap.parse_args()

    pairs = discover()
    if not pairs:
        print("no source graphs found - nothing to do")
        return 1

    entries = []
    skipped_non_api = []
    for path, root in pairs:
        raw = path.read_bytes()
        try:
            graph = json.loads(raw)
        except json.JSONDecodeError as exc:
            skipped_non_api.append((str(path), f"unparseable: {exc}"))
            continue
        # API format only: {node_id: {class_type, inputs}}. A UI-export graph has a different
        # shape and would silently become a fixture that tests the wrong schema.
        if not isinstance(graph, dict) or not graph or not all(
            isinstance(v, dict) and "class_type" in v for v in graph.values()
        ):
            skipped_non_api.append((str(path), "not API format (no class_type on every node)"))
            continue

        entries.append(
            {
                "fixture": flat_name(path, root),
                "source": str(path),
                "sha256": sha256(raw),
                "bytes": len(raw),
                "nodes": len(graph),
            }
        )

    print(f"discovered {len(pairs)} candidate(s); {len(entries)} API-format; "
          f"{len(skipped_non_api)} skipped")
    for src, why in skipped_non_api:
        print(f"  skipped {src}: {why}")

    names = [e["fixture"] for e in entries]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        print(f"ERROR: flattened names collide: {dupes}", file=sys.stderr)
        return 2

    if args.check:
        print("--check: nothing written")
        return 0

    DEST.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        raw = pathlib.Path(entry["source"]).read_bytes()
        out = DEST / entry["fixture"]
        out.write_bytes(raw)
        # Re-hash after the copy. A copy that changed bytes is a defect, not a fixture.
        after = sha256(out.read_bytes())
        if after != entry["sha256"]:
            print(f"ERROR: hash changed on copy for {entry['fixture']}", file=sys.stderr)
            return 3

    MANIFEST.write_text(
        json.dumps(
            {
                "note": (
                    "Recorded ComfyUI API-format workflow graphs, copied from rig-local trees "
                    "by tools/import_fixtures.py. The test suite reads ONLY the copies in "
                    "graphs/. The source paths are provenance, not a runtime dependency."
                ),
                "count": len(entries),
                "graphs": sorted(entries, key=lambda e: e["fixture"]),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(entries)} fixture(s) to {DEST}")
    print(f"wrote manifest {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
