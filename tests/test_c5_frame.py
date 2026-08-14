"""Check 5 — generator-legal frame, against the EFFECTIVE frame.

The headline leg is `test_the_recorded_1066_defect_is_caught`: the check as originally specified
read graph literals and could not have caught the incident that motivates it, because the frame
was derived from a mesh and arrived inside the uploaded image. Against the input's dimensions it
fires.
"""

from __future__ import annotations

import pytest
from conftest import ADAPTER_15, all_graph_names, load_graph, mutate

from comfy_preflight.checks.c5_frame import (
    CHECK_NAME,
    DECLARED_ABSENT_FAMILIES,
    FAMILIES,
    check_generator_legal_frame,
    declared_dimensions,
)
from comfy_preflight.errors import Defect, PreflightHalt, Verdict

# Frames from the record. 1066 is the defect; 1072 the re-ruled replacement; 752 is W3's;
# 1024 the pair's. 1064 is what 1066 decoded to - legal by /8, short of the preferred /16.
RECORDED_ILLEGAL = 1066
RECORDED_RULED = 1072
RECORDED_W3 = 752
RECORDED_PAIR = 1024
RECORDED_DECODED = 1064


# --------------------------------------------------------------------------- #
# The premise: no operand in the graph, on all 70.
# --------------------------------------------------------------------------- #


def test_no_recorded_graph_declares_a_dimension():
    """Zero width/height literals across the corpus - the measurement that re-specified this check."""
    for name in all_graph_names():
        found = declared_dimensions(load_graph(name))
        if found:
            raise AssertionError(f"{name} declares dimensions: {found}")


def test_returns_not_applicable_on_an_img2img_graph_with_no_input_dimensions():
    """A check that finds no operand must NOT return PASS.

    NOT_APPLICABLE names what it could not see. This is the whole reason that verdict exists.
    """
    result = check_generator_legal_frame(load_graph(ADAPTER_15))
    assert result.verdict is Verdict.NOT_APPLICABLE
    assert result.verdict is not Verdict.PASS
    assert result.operand == "none"
    assert result.dimensions_checked == ()
    declined = dict(result.clauses_declined)
    assert "frame_divisibility" in declined
    assert "img2img" in declined["frame_divisibility"]
    assert "inherited from the uploaded image" in declined["frame_divisibility"]


def test_the_whole_corpus_returns_not_applicable_without_input_dimensions():
    """The honest result on 70 of 70, stated as a measurement rather than a gap."""
    for name in all_graph_names():
        result = check_generator_legal_frame(load_graph(name))
        if result.verdict is not Verdict.NOT_APPLICABLE:
            raise AssertionError(f"{name}: verdict {result.verdict}, expected NOT_APPLICABLE")


# --------------------------------------------------------------------------- #
# THE HEADLINE LEG — the effective frame catches the recorded defect.
# --------------------------------------------------------------------------- #


def test_the_recorded_1066_defect_is_caught():
    """1066 was derived correctly from the mesh, rendered, and uploaded. The graph never saw it.

    Against the input image's dimensions the check fires, and the message carries the mechanism:
    1066/8 = 133.25 -> 133 latent columns -> decodes 1064, so every output is 2 px off its
    control.
    """
    with pytest.raises(PreflightHalt) as exc:
        check_generator_legal_frame(
            load_graph(ADAPTER_15), input_dimensions=(RECORDED_ILLEGAL, 1024)
        )
    assert exc.value.check == CHECK_NAME
    defect = next(d for d in exc.value.defects if d.code == "FRAME_NOT_GENERATOR_LEGAL")
    assert "1066" in defect.message
    assert "1064" in defect.message  # the decoded width
    assert "2 px off" in defect.message


def test_the_ruled_replacement_frame_passes():
    """1072: divisible by 16, the frame the record re-ruled."""
    result = check_generator_legal_frame(
        load_graph(ADAPTER_15), input_dimensions=(RECORDED_RULED, 1024)
    )
    assert result.verdict is Verdict.PASS
    assert result.operand == "input_dimensions"
    assert result.dimensions_checked == (("input width", 1072), ("input height", 1024))
    assert result.notes  # names where the frame came from


@pytest.mark.parametrize("width", [RECORDED_W3, RECORDED_PAIR, RECORDED_RULED])
def test_frames_that_the_record_used_without_incident_pass(width):
    result = check_generator_legal_frame(load_graph(ADAPTER_15), input_dimensions=(width, 1024))
    assert result.verdict is Verdict.PASS


def test_a_legal_but_dispreferred_frame_advises_and_does_not_halt():
    """1064 is divisible by 8 (legal) and not by 16 (dispreferred).

    The standing constraint reads "/8 is the floor, prefer /16" - a floor and a preference, not
    two floors. Promoting the preference to a halt would fire on every legal /8 frame, and a gate
    that halts correct work gets disabled by the third person who hits it.

    Amendment 3 re-labels this ADVISORY. Amendment 1a's "PASSES with a note" predates the verdict
    vocabulary; once ADVISORY exists in the merge order, this IS one.
    """
    result = check_generator_legal_frame(
        load_graph(ADAPTER_15), input_dimensions=(RECORDED_DECODED, 1024)
    )
    assert result.verdict is Verdict.ADVISORY
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "FRAME_BELOW_PREFERRED_DIVISOR"
    assert "not by 16" in finding.message
    assert "ADVISORY, not a halt" in finding.hint


def test_the_advisory_is_a_relabeling_and_not_a_new_halt():
    """The load-bearing half of Amendment 3: WHEN this check halts did not change.

    /8 still halts, /16 still never does. If a later edit made the preference halt, this fires.
    """
    # /16-short: advisory, returns rather than raises.
    check_generator_legal_frame(load_graph(ADAPTER_15), input_dimensions=(RECORDED_DECODED, 1024))
    # /8-short: still halts.
    with pytest.raises(PreflightHalt):
        check_generator_legal_frame(load_graph(ADAPTER_15), input_dimensions=(RECORDED_ILLEGAL, 1024))
    # /16-clean: still a plain PASS with no finding at all.
    clean = check_generator_legal_frame(load_graph(ADAPTER_15), input_dimensions=(1072, 1024))
    assert clean.verdict is Verdict.PASS
    assert clean.findings == ()


def test_the_advisory_travels_as_findings_so_the_aggregator_sees_it():
    """Named `findings` to match check 8, because the aggregator reads that one field.

    An advisory under a differently-named field would be silently dropped from the merged report -
    present in this check's result and absent from the run's.
    """
    result = check_generator_legal_frame(
        load_graph(ADAPTER_15), input_dimensions=(RECORDED_DECODED, 1024)
    )
    assert hasattr(result, "findings")
    assert all(isinstance(f, Defect) for f in result.findings)


def test_height_is_checked_not_only_width():
    with pytest.raises(PreflightHalt) as exc:
        check_generator_legal_frame(load_graph(ADAPTER_15), input_dimensions=(1024, 1066))
    defect = next(d for d in exc.value.defects if d.code == "FRAME_NOT_GENERATOR_LEGAL")
    assert "input height" in defect.message


def test_both_dimensions_are_reported_when_both_are_illegal():
    """Every defect, not just the first."""
    with pytest.raises(PreflightHalt) as exc:
        check_generator_legal_frame(load_graph(ADAPTER_15), input_dimensions=(1066, 1030))
    assert len(exc.value.defects) == 2


def test_a_non_positive_dimension_fires():
    with pytest.raises(PreflightHalt) as exc:
        check_generator_legal_frame(load_graph(ADAPTER_15), input_dimensions=(0, 1024))
    assert "FRAME_NOT_POSITIVE" in {d.code for d in exc.value.defects}


# --------------------------------------------------------------------------- #
# The graph-literal path keeps full force where a dimension IS declared.
# --------------------------------------------------------------------------- #


def test_graph_literals_are_preferred_when_the_graph_declares_a_dimension():
    """A txt2img-shaped graph. This corpus has none, so the node is added by one edit."""

    def add_latent(raw):
        raw["100"] = {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 1072, "height": 1024, "batch_size": 1},
        }

    result = check_generator_legal_frame(mutate(ADAPTER_15, add_latent))
    assert result.verdict is Verdict.PASS
    assert result.operand == "graph_literals"
    assert ("node 100.width", 1072) in result.dimensions_checked


def test_fires_on_an_illegal_declared_dimension():
    def add_bad_latent(raw):
        raw["100"] = {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 1066, "height": 1024, "batch_size": 1},
        }

    with pytest.raises(PreflightHalt) as exc:
        check_generator_legal_frame(mutate(ADAPTER_15, add_bad_latent))
    defect = next(d for d in exc.value.defects if d.code == "FRAME_NOT_GENERATOR_LEGAL")
    assert "node 100.width" in defect.message


def test_declared_dimensions_win_over_supplied_input_dimensions():
    """When the graph states the frame, that is the frame - the input is not the operand."""

    def add_latent(raw):
        raw["100"] = {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 1072, "height": 1024},
        }

    result = check_generator_legal_frame(
        mutate(ADAPTER_15, add_latent), input_dimensions=(1066, 1066)
    )
    assert result.verdict is Verdict.PASS
    assert result.operand == "graph_literals"


def test_batch_size_is_not_treated_as_a_dimension():
    """batch_size=1 is not a frame width; reading it as one would fire on every txt2img graph."""

    def add_latent(raw):
        raw["100"] = {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 1072, "height": 1024, "batch_size": 3},
        }

    result = check_generator_legal_frame(mutate(ADAPTER_15, add_latent))
    assert result.verdict is Verdict.PASS
    assert all("batch_size" not in label for label, _ in result.dimensions_checked)


# --------------------------------------------------------------------------- #
# The family table carries only what was measured.
# --------------------------------------------------------------------------- #


def test_only_qwen_is_measured():
    """An unmeasured divisor either halts correct work or passes the defect it was added for."""
    assert set(FAMILIES) == {"qwen"}
    assert FAMILIES["qwen"].divisor == 8
    assert FAMILIES["qwen"].preferred_divisor == 16
    assert "1066" in FAMILIES["qwen"].source


def test_an_unmeasured_family_returns_not_applicable_rather_than_guessing():
    for family in DECLARED_ABSENT_FAMILIES:
        result = check_generator_legal_frame(
            load_graph(ADAPTER_15), family=family, input_dimensions=(1066, 1066)
        )
        if result.verdict is not Verdict.NOT_APPLICABLE:
            raise AssertionError(f"family {family}: verdict {result.verdict}")
        declined = dict(result.clauses_declined)
        if "no measured frame constraint" not in declined["frame_divisibility"]:
            raise AssertionError(f"family {family}: declined reason does not name the gap")


def test_an_unmeasured_family_does_not_halt_on_an_illegal_frame():
    """It cannot know the frame is illegal, so it must not claim to.

    1066 is illegal for Qwen. For a family with no measured divisor the honest answer is
    NOT_APPLICABLE, not a halt borrowed from another family's constraint.
    """
    result = check_generator_legal_frame(
        load_graph(ADAPTER_15), family="flux", input_dimensions=(1066, 1066)
    )
    assert result.verdict is Verdict.NOT_APPLICABLE


def test_family_lookup_is_case_insensitive():
    result = check_generator_legal_frame(
        load_graph(ADAPTER_15), family="QWEN", input_dimensions=(1072, 1024)
    )
    assert result.verdict is Verdict.PASS


def test_check_has_no_skip_parameter():
    import inspect

    params = set(inspect.signature(check_generator_legal_frame).parameters)
    forbidden = {"skip", "force", "ignore", "warn_only", "soft", "disable", "enabled"}
    assert not (params & forbidden), f"check exposes a skip-shaped parameter: {params & forbidden}"


def test_the_check_never_repairs_a_frame():
    """The hint names the legal sizes; it does not round for you.

    A graph a gate repaired is a graph nobody reviewed.
    """
    with pytest.raises(PreflightHalt) as exc:
        check_generator_legal_frame(load_graph(ADAPTER_15), input_dimensions=(1066, 1024))
    defect = next(d for d in exc.value.defects if d.code == "FRAME_NOT_GENERATOR_LEGAL")
    assert "1064 or 1072" in defect.hint
    assert "do not let the check round for you" in defect.hint
