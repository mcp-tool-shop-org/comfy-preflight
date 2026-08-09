"""No `assert` in library code. This is the guard that makes the law enforceable.

A gate that decides whether an irreversible step proceeds must `raise`. `assert` is a
developer's sanity check the interpreter is licensed to delete: `python -O` and
`PYTHONOPTIMIZE=1` remove it silently and execution continues past it. In the repo that
produced this rule, 87 gates were removable by an environment variable — including every one
in the write path — which is worse than a shell chain walking past an exit code, because the
chain at least lets the gate print.

Documenting that rule does not enforce it. This does: an AST scan over `src/`, with exactly
one declared exception.

The scan is AST-based rather than textual on purpose — a regex over source finds the word
`assert` in docstrings, comments and string literals (this very module is full of them) and
would either fire constantly or need escaping rules that themselves become wrong.
"""

import ast
import pathlib

import pytest

SRC = pathlib.Path(__file__).resolve().parent.parent / "src" / "comfy_preflight"

# The single declared exception, with its reason. `_assert_probe` MEASURES assert-stripping,
# so a bare assert is its instrument rather than a gate. Any other file appearing here needs
# an author's stated reason, not a shrug.
ALLOWED = {"_assert_probe.py"}


def _assert_lines(path: pathlib.Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]


def test_library_contains_no_assert_statements():
    offenders = {}
    scanned = 0
    for path in sorted(SRC.rglob("*.py")):
        scanned += 1
        if path.name in ALLOWED:
            continue
        lines = _assert_lines(path)
        if lines:
            offenders[path.name] = lines

    if offenders:
        raise AssertionError(
            "assert found in library code - a gate must raise, because -O deletes assert:\n"
            + "\n".join(f"  {name}: line(s) {lines}" for name, lines in offenders.items())
        )

    # A 0 that could not have been anything else is not a check. Pin that the scan actually
    # walked files, so a broken path never reads as a clean result.
    if scanned == 0:
        raise RuntimeError(f"the scan found no python files under {SRC} - it measured nothing")


def test_the_declared_exception_actually_contains_one():
    """If `_assert_probe` ever stops containing an assert, its exemption is stale.

    An allowlist entry for a file that no longer needs it is how allowlists rot into blanket
    permissions.
    """
    lines = _assert_lines(SRC / "_assert_probe.py")
    if not lines:
        raise RuntimeError(
            "_assert_probe.py contains no assert, so its ALLOWED entry is stale - remove it"
        )


def test_the_scan_fires_on_a_deliberately_broken_module(tmp_path):
    """The can-fail leg: prove the scan detects what it is looking for.

    Written against a synthetic file with a synthetic name in tmp_path, never against a real
    module — a fixture that names a real module moves the count it is verifying.
    """
    bad = tmp_path / "zz_synthetic_gate.py"
    bad.write_text(
        "def gate(value):\n"
        "    assert value > 0, 'this is the failure mode the scan must catch'\n"
        "    return value\n",
        encoding="utf-8",
    )
    found = _assert_lines(bad)
    if found != [2]:
        raise RuntimeError(f"the scan missed a bare assert on line 2; got {found}")


def test_the_scan_does_not_fire_on_the_word_assert_in_prose(tmp_path):
    """The other direction: a docstring mentioning assert is not an assert.

    This is why the scan is AST-based. A textual scan fails this.
    """
    ok = tmp_path / "zz_synthetic_prose.py"
    ok.write_text(
        '"""This module explains why assert is not a gate; the word assert appears here."""\n'
        "MESSAGE = 'assert is deleted by -O'\n"
        "# assert something  <- a comment, not a statement\n"
        "def f():\n"
        "    return MESSAGE\n",
        encoding="utf-8",
    )
    found = _assert_lines(ok)
    if found:
        raise RuntimeError(f"the scan fired on prose mentioning assert: line(s) {found}")


@pytest.mark.parametrize("mode_note", ["runs identically under -O; contains no assert itself"])
def test_this_guard_survives_assert_stripping(mode_note):
    """This file's own checks are `raise`, not `assert`, so -O cannot delete the guard.

    A guard against assert-stripping that is itself made of asserts would be deleted by the
    condition it is watching for.
    """
    tree = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"), filename=__file__)
    asserts = [
        n.lineno
        for n in ast.walk(tree)
        if isinstance(n, ast.Assert)
    ]
    if asserts:
        raise RuntimeError(
            f"this guard uses assert at line(s) {asserts} - -O would delete its own checks"
        )
