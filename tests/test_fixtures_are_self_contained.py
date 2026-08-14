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
#
# The lookbehind is load-bearing and was earned: without it the pattern matches every URL
# scheme, because `https://` ends in `s:/` and `s` is a letter. A drive letter is exactly ONE
# letter, so requiring that no letter precedes it separates `E:\AI\training` from
# `https://huggingface.co/...`. The first test file to cite a source URL made the guard fail on
# a citation, which is the opposite of what it exists to catch.
ABSOLUTE_PATH = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]")


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


def test_the_scan_does_not_fire_on_a_url(tmp_path):
    """The other direction, and the reason the pattern grew a lookbehind.

    A cited source URL is the opposite of a leaked local path — check 8's envelope table exists
    to carry them — and a guard that rejected citations would push a later seat to drop the
    citation rather than the guard.
    """
    ok = tmp_path / "zz_synthetic_urls.py"
    ok.write_text(
        'CARD = "https://huggingface.co/InstantX/Qwen-Image-ControlNet-Union"\n'
        'PLAIN = "http://example.invalid/card"\n'
        'ALSO = "file:///not/a/drive/letter"\n',
        encoding="utf-8",
    )
    hits = [v for _, v in _string_constants(ok) if ABSOLUTE_PATH.search(v)]
    if hits:
        raise RuntimeError(f"the scan fired on a URL, which is not an absolute path: {hits}")


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


def test_gitattributes_pins_the_fixture_bytes():
    """The fixture tree must be marked `-text`, and the rule must be the LAST match.

    Without it, git rewrites line endings in transit and the provenance manifest becomes true
    on one platform only — measured: `git add` stripped 172 CR bytes from a 3,165-byte fixture,
    and CI caught the mismatch on Linux while Windows stayed green.

    Ordering is part of the assertion because the last matching pattern wins. A `-text` rule
    placed above a `* text=auto` line is silently overridden, which is how this was first
    written.
    """
    path = TESTS.parent / ".gitattributes"
    if not path.exists():
        raise AssertionError(
            ".gitattributes is missing; without it git rewrites fixture line endings and the "
            "provenance manifest holds on Windows only"
        )
    lines = [
        ln.strip()
        for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    pin = "tests/fixtures/graphs/** -text"
    if pin not in lines:
        raise AssertionError(f".gitattributes does not contain {pin!r}; rules present: {lines}")

    generic = [i for i, ln in enumerate(lines) if ln.startswith("* ")]
    if generic and max(generic) > lines.index(pin):
        raise AssertionError(
            "a generic '*' rule appears AFTER the fixture pin and overrides it; "
            f"rules in order: {lines}"
        )


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
