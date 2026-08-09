"""A probe that measures whether a bare `assert` gates LIBRARY code in this interpreter.

Why this module exists, and why it is in `src/` rather than in `tests/`:

**pytest rewrites `assert` statements in test modules.** Its import hook transforms them into
explicit code that raises `AssertionError`, so a bare `assert False` written in a test file
still fires under `python -O` — not because the interpreter kept it, but because pytest
replaced it before the interpreter saw it. pytest says so itself when run under -O:

    PytestConfigWarning: assertions not in test modules or plugins will be ignored because
    assert statements are not executed by the underlying Python interpreter

Library code is **not** rewritten. So an assert in `comfy_preflight/*.py` really is deleted
under `-O`, while an assert in `tests/*.py` is not. A test that probes assert-stripping with
its own assert therefore measures a proxy — pytest's rewriting — instead of the property, and
reports the opposite of the truth. That mistake was made once here and caught by the -O CI
leg failing.

This module is the honest instrument: it lives where the gates live, so it is subject to the
same treatment they are.
"""

from __future__ import annotations


def bare_assert_fires() -> bool:
    """True if a bare `assert` raises in library code under the running interpreter.

    Returns False when assertions are stripped (`python -O`, `PYTHONOPTIMIZE`), which is
    exactly the condition under which a gate written as an `assert` would silently vanish and
    let execution continue past it.
    """
    try:
        assert False  # noqa: B011 - deliberately bare; this is the measurement
        return False
    except AssertionError:
        return True


def asserts_are_stripped() -> bool:
    """True when this interpreter is discarding assertions.

    Read from the interpreter rather than inferred, so it can be cross-checked against
    `bare_assert_fires()`. If the two ever disagree, something is rewriting library code and
    the gates' guarantee needs re-examining.
    """
    return not __debug__
