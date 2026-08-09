"""The suite must not reach the recorded source trees. Ever.

Those trees are not in git and have no revert; three consecutive rulings had executors
sha256-manifest them to protect them. A test that read them directly would also make this
repo depend on one rig's directory layout, so the fixtures are copies and the copies are the
only thing the suite may open.

`tools/import_fixtures.py` is deliberately out of scope here — it is the one-time rig-local
importer and naming absolute source paths is its whole job.
"""

from __future__ import annotations

import ast
import json
import pathlib
import re

from conftest import GRAPHS, all_graph_names, load_graph

TESTS = pathlib.Path(__file__).resolve().parent
MANIFEST = TESTS / "fixtures" / "MANIFEST.json"

# A drive-letter absolute path: a letter, a colon, a separator. Note this pattern does not
# match its own source text (the character before the colon here is ']', not a letter), so the
# scanner does not flag itself and needs no self-exemption.
ABSOLUTE_PATH = re.compile(r"[A-Za-z]:[\\/]")


def _string_constants(path: pathlib.Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append((node.lineno, node.value))
    return out


def test_no_test_file_names_an_absolute_path():
    offenders = []
    scanned = 0
    for path in sorted(TESTS.rglob("*.py")):
        scanned += 1
        for lineno, value in _string_constants(path):
            if ABSOLUTE_PATH.search(value):
                offenders.append(f"{path.name}:{lineno}: {value[:80]!r}")

    if offenders:
        raise AssertionError(
            "a test file names an absolute path; the suite must read only tests/fixtures:\n"
            + "\n".join(f"  {o}" for o in offenders)
        )
    if scanned == 0:
        raise RuntimeError("the scan found no test files - it measured nothing")


def test_the_scan_fires_on_an_absolute_path(tmp_path):
    """Can-fail leg, against a synthetic file so no real module moves the count."""
    bad = tmp_path / "zz_synthetic_test.py"
    # Raw-string literal in the generated file, so parsing it raises no invalid-escape warning.
    bad.write_text('SOURCE = r"E:' + chr(92) + 'AI' + chr(92) + 'training"\n', encoding="utf-8")
    hits = [v for _, v in _string_constants(bad) if ABSOLUTE_PATH.search(v)]
    if not hits:
        raise RuntimeError("the scan missed a synthetic absolute path")


def test_manifest_matches_the_fixtures_on_disk():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    declared = {entry["fixture"] for entry in data["graphs"]}
    on_disk = set(all_graph_names())

    if declared != on_disk:
        missing = sorted(declared - on_disk)
        extra = sorted(on_disk - declared)
        raise AssertionError(
            f"manifest and fixtures disagree; missing from disk: {missing}; "
            f"not in manifest: {extra}"
        )
    if data["count"] != len(on_disk):
        raise AssertionError(f"manifest count {data['count']} != {len(on_disk)} files on disk")


def test_every_fixture_parses_as_an_api_graph():
    """A fixture that no longer parses is a broken fixture, not a passing test."""
    for name in all_graph_names():
        graph = load_graph(name)
        if len(graph) == 0:
            raise AssertionError(f"{name} parsed to an empty graph")


def test_fixture_bytes_match_the_manifest_hashes():
    """The copies must still be the bytes that were recorded.

    Compares artifact bytes to the recorded digest - the manifest is the provenance record, so
    a fixture edited in place is caught here rather than silently changing a check's inputs.
    """
    import hashlib

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for entry in data["graphs"]:
        actual = hashlib.sha256((GRAPHS / entry["fixture"]).read_bytes()).hexdigest()
        if actual != entry["sha256"]:
            raise AssertionError(
                f"{entry['fixture']}: bytes changed since import "
                f"(manifest {entry['sha256'][:12]}, disk {actual[:12]})"
            )
