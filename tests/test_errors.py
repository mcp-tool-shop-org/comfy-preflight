"""Tests for the halt surface. These ride the commit that adds errors.py."""

import pathlib
import sys
import tomllib

import pytest

import comfy_preflight
from comfy_preflight._assert_probe import asserts_are_stripped, bare_assert_fires
from comfy_preflight.errors import Defect, PreflightHalt, Verdict, merge_verdicts


def test_version_matches_pyproject():
    """__version__ and the packaging metadata must not drift."""
    root = pathlib.Path(__file__).resolve().parent.parent
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == comfy_preflight.__version__


def test_verdict_distinguishes_not_applicable_from_pass():
    """NOT_APPLICABLE is not a synonym for PASS.

    A check that found nothing to examine has declined to answer. Collapsing that into PASS
    is what makes a check unable to fail.
    """
    assert Verdict.NOT_APPLICABLE is not Verdict.PASS
    assert Verdict.NOT_APPLICABLE.value == "not_applicable"


def test_advisory_is_distinct_from_pass_and_from_halt():
    """ADVISORY is a third thing, not a soft HALT and not a decorated PASS.

    Check 8 exists in this state: a documented band is documentation, not a gate, and the
    studio ran an out-of-band value deliberately. Collapsing it into HALT would fire on
    correct work; collapsing it into PASS would hide the fact it was added to surface.
    """
    assert Verdict.ADVISORY is not Verdict.PASS
    assert Verdict.ADVISORY is not Verdict.HALT
    assert Verdict.ADVISORY.value == "advisory"


def test_the_merge_order_is_the_ratified_one():
    """HALT > ADVISORY > NOT_APPLICABLE > PASS, each rung pinned against the one below it."""
    assert merge_verdicts([Verdict.PASS, Verdict.NOT_APPLICABLE]) is Verdict.NOT_APPLICABLE
    assert merge_verdicts([Verdict.NOT_APPLICABLE, Verdict.ADVISORY]) is Verdict.ADVISORY
    assert merge_verdicts([Verdict.ADVISORY, Verdict.HALT]) is Verdict.HALT
    # and the full set reduces to the top rung regardless of the order it arrives in
    every = [Verdict.PASS, Verdict.HALT, Verdict.NOT_APPLICABLE, Verdict.ADVISORY]
    assert merge_verdicts(every) is Verdict.HALT
    assert merge_verdicts(list(reversed(every))) is Verdict.HALT


def test_not_applicable_outranks_pass_which_is_the_surprising_rung():
    """A declined clause must not disappear behind passing ones.

    This is the rung a reader would most likely "fix" to PASS, so it is pinned with its
    reason: a run where something declined has not checked everything.
    """
    assert merge_verdicts([Verdict.PASS, Verdict.PASS, Verdict.NOT_APPLICABLE]) is (
        Verdict.NOT_APPLICABLE
    )


def test_merging_nothing_is_not_a_pass():
    """Running no checks at all is the cheapest possible way to build a gate that cannot fail."""
    assert merge_verdicts([]) is Verdict.NOT_APPLICABLE


def test_halt_carries_no_report_when_a_single_check_raises():
    """A lone check has no aggregate to carry, and says so with None rather than an empty shape."""
    exc = PreflightHalt("check_1_link_topology", [Defect(code="A", message="m", hint="h")])
    assert exc.report is None


def test_halt_can_carry_the_aggregate_report():
    """The halt is the ONLY way out of a failed aggregate run, so it must carry the report.

    A second non-raising entry point for the CLI and MCP to call would be a skip flag under
    another name. Instead the renderers catch this and read `report`.
    """
    sentinel = object()
    exc = PreflightHalt(
        "preflight", [Defect(code="A", message="m", hint="h")], report=sentinel
    )
    assert exc.report is sentinel


def test_the_report_carrier_is_keyword_only_and_not_skip_shaped():
    """`report` must not be positionally confusable with `defects`, and must not gate anything."""
    import inspect

    params = inspect.signature(PreflightHalt.__init__).parameters
    assert params["report"].kind is inspect.Parameter.KEYWORD_ONLY
    forbidden = {"skip", "force", "ignore", "warn_only", "soft", "strict", "enabled"}
    assert not (set(params) & forbidden)


def test_defect_locates_itself():
    d = Defect(
        code="SELF_LINK",
        message="input reads from its own node",
        hint="repoint it at the producing node",
        node_id="14",
        input_name="samples",
    )
    rendered = str(d)
    assert "SELF_LINK" in rendered
    assert "[node 14.samples]" in rendered
    assert "hint:" in rendered


def test_defect_without_location_renders():
    d = Defect(code="NO_ESTIMATE", message="no credit estimate present", hint="read one first")
    assert "[node" not in str(d)


def test_halt_carries_every_defect_not_just_the_first():
    defects = [
        Defect(code="A", message="m1", hint="h1", node_id="1"),
        Defect(code="B", message="m2", hint="h2", node_id="2"),
    ]
    exc = PreflightHalt("check_1_link_topology", defects)
    assert len(exc.defects) == 2
    assert "2 defect(s)" in str(exc)
    assert "A" in str(exc) and "B" in str(exc)


def test_halt_refuses_to_fire_without_evidence():
    """A gate that fires must name what it found."""
    with pytest.raises(ValueError, match="at least one Defect"):
        PreflightHalt("check_1_link_topology", [])


def test_halt_is_not_an_assertion_error():
    """-O removes `assert`, not `raise`.

    If a halt were ever expressed as an assert (or as an AssertionError subclass that a
    caller might conflate with one), assert-stripping would delete the gate and let
    execution continue. This pins the type.
    """
    assert not issubclass(PreflightHalt, AssertionError)
    assert issubclass(PreflightHalt, Exception)


def test_halt_has_no_skip_parameter():
    """No keyword on the halt suppresses it.

    A gate a caller can disable at the call site is a transport, not a guard. This reads the
    actual signature rather than trusting the docstring.
    """
    import inspect

    params = set(inspect.signature(PreflightHalt.__init__).parameters)
    forbidden = {"skip", "force", "ignore", "warn_only", "soft", "strict", "enabled"}
    assert not (params & forbidden), f"halt exposes a skip-shaped parameter: {params & forbidden}"


def test_a_bare_assert_is_not_a_gate_in_library_code_and_the_halt_is():
    """The load-bearing test, and it must MEAN something in every interpreter mode.

    Written with explicit `raise` rather than `assert`, and probing LIBRARY code rather than
    this file, for a reason that cost a red CI leg to learn: **pytest rewrites asserts in test
    modules**, so a bare `assert False` written here fires even under `python -O`. Probing
    assert-stripping from inside a test file measures pytest's rewriting, not the interpreter
    — and returns the opposite of the truth.

    `_assert_probe` lives in `src/`, where the gates live and where nothing rewrites it.
    """
    stripped = asserts_are_stripped()
    fires_in_library = bare_assert_fires()

    # 1. In library code, a bare assert gates only when assertions are live. That is the
    #    whole reason a gate may not be an assert.
    if stripped and fires_in_library:
        raise RuntimeError(
            "assertions are stripped yet a bare assert still fired in library code - "
            "something is rewriting src/, and the gates' guarantee needs re-examining"
        )
    if not stripped and not fires_in_library:
        raise RuntimeError(
            "assertions are live yet a bare assert did not fire in library code"
        )

    # 2. The halt fires in BOTH modes. This is the property every gate depends on.
    halt_fired = False
    try:
        raise PreflightHalt("probe", [Defect(code="X", message="m", hint="h")])
    except PreflightHalt:
        halt_fired = True
    if not halt_fired:
        raise RuntimeError("PreflightHalt did not raise - the gate surface is broken")

    # 3. The interpreter's own flag must agree with __debug__, so the three CI legs are
    #    genuinely three modes rather than one run repeated three times.
    if (sys.flags.optimize > 0) != stripped:
        raise RuntimeError(
            f"sys.flags.optimize={sys.flags.optimize} disagrees with __debug__={__debug__}"
        )


def test_pytest_rewrites_asserts_in_test_modules_which_is_why_the_probe_is_in_src():
    """Pins the trap itself, so nobody re-derives it.

    A bare assert in THIS file fires regardless of interpreter mode, because pytest rewrote
    it at import. If this ever stops being true, the probe module's rationale changes and its
    docstring is wrong.
    """
    fired_here = False
    try:
        assert False, "rewritten by pytest, so this fires in any mode"
    except AssertionError:
        fired_here = True
    if not fired_here:
        raise RuntimeError(
            "a bare assert in a test module did NOT fire - pytest assertion rewriting is off, "
            "so _assert_probe's stated rationale no longer holds"
        )
    # And the same statement in library code behaves differently under -O. That divergence is
    # the finding.
    if asserts_are_stripped() and bare_assert_fires():
        raise RuntimeError("library asserts and test asserts should diverge under -O")
