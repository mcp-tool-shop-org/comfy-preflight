"""Check 4 — the saved graph is the submitted graph, compared as parsed graphs.

Three real saved/submitted pairs exist in the corpus. **They are byte-identical**, measured
below — which makes them sound PASS fixtures and useless for demonstrating the check's
distinguishing property, because a byte comparison would also pass them. The re-dump leg is
therefore constructed: same values, different formatting and key order.
"""

from __future__ import annotations

import json

import pytest
from conftest import GRAPHS, all_graph_names, load_graph, load_raw

from comfy_preflight.checks.c4_saved_is_submitted import CHECK_NAME, check_saved_is_submitted
from comfy_preflight.errors import PreflightHalt, Verdict
from comfy_preflight.graph import Graph

PAIRS = [
    pytest.param(
        f"facet_next__E04_stroke__e10_layer__{tag}_y+000_e+00_workflow.json",
        f"facet_next__E04_stroke__e10_layer__{tag}_record__{tag}_y+000_e+00_workflow.json",
        id=tag,
    )
    for tag in ("W2", "W2b", "W2c")
]


# --------------------------------------------------------------------------- #
# The real pairs.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("saved_name,submitted_name", PAIRS)
def test_recorded_pairs_compare_equal(saved_name, submitted_name):
    result = check_saved_is_submitted(load_graph(saved_name), load_graph(submitted_name))
    assert result.verdict is Verdict.PASS
    assert result.nodes_compared == 17
    assert result.inputs_compared > 0


@pytest.mark.parametrize("saved_name,submitted_name", PAIRS)
def test_the_recorded_pairs_are_byte_identical_so_they_cannot_prove_the_value_property(
    saved_name, submitted_name
):
    """Measured, and it is the reason the re-dump leg below is constructed.

    If these ever stop being byte-identical they become a stronger fixture, and this test failing
    is the notification that the corpus changed - not a defect in the check.
    """
    a = (GRAPHS / saved_name).read_bytes()
    b = (GRAPHS / submitted_name).read_bytes()
    if a != b:
        raise AssertionError(
            f"{saved_name} and {submitted_name} now differ in bytes; they were byte-identical "
            "when this fixture pair was adopted, so the re-dump leg may be able to use them "
            "directly"
        )


# --------------------------------------------------------------------------- #
# The FALSE-HALT leg: formatting must not register as a change.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("saved_name,submitted_name", PAIRS)
def test_a_whitespace_and_key_order_redump_compares_equal(saved_name, submitted_name):
    """The property that makes this a graph comparison rather than a text one.

    The submitted side is re-serialised with different indentation, different separators and
    sorted keys, then re-parsed. Not one value moves. A text comparison halts here; this must
    not.
    """
    raw = load_raw(submitted_name)
    redumped = json.loads(json.dumps(raw, indent=4, sort_keys=True, separators=(",", ": ")))

    # The bytes really did change - otherwise this leg proves nothing.
    original_bytes = (GRAPHS / submitted_name).read_bytes()
    redumped_bytes = json.dumps(redumped, indent=4, sort_keys=True).encode()
    if original_bytes == redumped_bytes:
        raise AssertionError("the re-dump produced identical bytes; the leg cannot fail")

    result = check_saved_is_submitted(load_graph(saved_name), Graph.from_api_dict(redumped))
    assert result.verdict is Verdict.PASS


def test_an_int_and_float_rendering_of_the_same_number_compare_equal():
    """A seed rendered 770700 or 770700.0 has not moved.

    Strict int-vs-float comparison would report a difference where no value changed.
    """
    saved_name, submitted_name = PAIRS[0].values[0], PAIRS[0].values[1]
    raw = load_raw(submitted_name)
    moved = False
    for node in raw.values():
        for name, value in list((node.get("inputs") or {}).items()):
            if isinstance(value, int) and not isinstance(value, bool):
                node["inputs"][name] = float(value)
                moved = True
    if not moved:
        raise AssertionError("no integer literal found to re-render; the leg cannot fail")

    result = check_saved_is_submitted(load_graph(saved_name), Graph.from_api_dict(raw))
    assert result.verdict is Verdict.PASS


# --------------------------------------------------------------------------- #
# FIRE legs — one edit each.
# --------------------------------------------------------------------------- #


def _pair():
    return PAIRS[0].values[0], PAIRS[0].values[1]


def test_fires_on_a_single_changed_value():
    saved_name, submitted_name = _pair()
    raw = load_raw(submitted_name)
    seed_node = next(
        nid for nid, n in raw.items() if "seed" in (n.get("inputs") or {})
    )
    raw[seed_node]["inputs"]["seed"] += 1

    with pytest.raises(PreflightHalt) as exc:
        check_saved_is_submitted(load_graph(saved_name), Graph.from_api_dict(raw))
    defect = next(d for d in exc.value.defects if d.code == "VALUE_CHANGED")
    assert defect.node_id == seed_node
    assert defect.input_name == "seed"
    assert exc.value.check == CHECK_NAME


def test_fires_on_a_retargeted_link():
    saved_name, submitted_name = _pair()
    raw = load_raw(submitted_name)
    raw["6"]["inputs"]["model"] = ["1", 0]  # was the loader

    with pytest.raises(PreflightHalt) as exc:
        check_saved_is_submitted(load_graph(saved_name), Graph.from_api_dict(raw))
    assert "LINK_RETARGETED" in {d.code for d in exc.value.defects}


def test_fires_on_a_node_added_after_saving():
    saved_name, submitted_name = _pair()
    raw = load_raw(submitted_name)
    raw["999"] = {"class_type": "SaveImage", "inputs": {"images": ["14", 0]}}

    with pytest.raises(PreflightHalt) as exc:
        check_saved_is_submitted(load_graph(saved_name), Graph.from_api_dict(raw))
    defect = next(d for d in exc.value.defects if d.code == "NODE_ADDED_IN_SUBMITTED")
    assert defect.node_id == "999"


def test_fires_on_a_node_dropped_before_submitting():
    saved_name, submitted_name = _pair()
    raw = load_raw(submitted_name)
    del raw["15"]

    with pytest.raises(PreflightHalt) as exc:
        check_saved_is_submitted(load_graph(saved_name), Graph.from_api_dict(raw))
    assert "NODE_MISSING_FROM_SUBMITTED" in {d.code for d in exc.value.defects}


def test_fires_on_a_class_type_swap():
    saved_name, submitted_name = _pair()
    raw = load_raw(submitted_name)
    raw["5"]["class_type"] = "LoraLoader"

    with pytest.raises(PreflightHalt) as exc:
        check_saved_is_submitted(load_graph(saved_name), Graph.from_api_dict(raw))
    assert "CLASS_TYPE_CHANGED" in {d.code for d in exc.value.defects}


def test_fires_on_a_dropped_input():
    saved_name, submitted_name = _pair()
    raw = load_raw(submitted_name)
    # Locate the sampler by its inputs rather than by node id: this 17-node graph does not use
    # the same numbering as the 15-node one, and an assumed id is a fixture that breaks silently
    # when the pair changes.
    sampler = next(nid for nid, n in raw.items() if "steps" in (n.get("inputs") or {}))
    del raw[sampler]["inputs"]["steps"]

    with pytest.raises(PreflightHalt) as exc:
        check_saved_is_submitted(load_graph(saved_name), Graph.from_api_dict(raw))
    defect = next(d for d in exc.value.defects if d.code == "INPUT_MISSING_FROM_SUBMITTED")
    assert defect.input_name == "steps"
    assert defect.node_id == sampler


def test_fires_when_a_wire_becomes_a_literal():
    saved_name, submitted_name = _pair()
    raw = load_raw(submitted_name)
    raw["14"]["inputs"]["samples"] = "not a wire"

    with pytest.raises(PreflightHalt) as exc:
        check_saved_is_submitted(load_graph(saved_name), Graph.from_api_dict(raw))
    assert "INPUT_KIND_CHANGED" in {d.code for d in exc.value.defects}


# --------------------------------------------------------------------------- #
# No-false-halt leg over the whole corpus.
# --------------------------------------------------------------------------- #


def test_every_graph_compares_equal_to_itself():
    """70 fixtures, each against a re-dump of itself with sorted keys.

    Reflexivity through a round-trip: if any graph failed to equal its own re-serialisation, the
    comparison is reading formatting somewhere.
    """
    for name in all_graph_names():
        raw = load_raw(name)
        redumped = json.loads(json.dumps(raw, indent=1, sort_keys=True))
        result = check_saved_is_submitted(load_graph(name), Graph.from_api_dict(redumped))
        if result.verdict is not Verdict.PASS:
            raise AssertionError(f"{name}: verdict {result.verdict}")


def test_distinct_graphs_do_not_compare_equal():
    """Before trusting a PASS, ask what a difference would have required."""
    names = all_graph_names()
    a = load_graph("facet_next__E04_g7__workflow_7_G7_headnoun.json")
    b = load_graph("facet_next__E12_twins__graphs__workflow_twin_0.json")
    with pytest.raises(PreflightHalt):
        check_saved_is_submitted(a, b)
    assert len(names) == 70


def test_check_has_no_skip_parameter():
    import inspect

    params = set(inspect.signature(check_saved_is_submitted).parameters)
    forbidden = {"skip", "force", "ignore", "warn_only", "soft", "disable", "enabled"}
    assert not (params & forbidden), f"check exposes a skip-shaped parameter: {params & forbidden}"
