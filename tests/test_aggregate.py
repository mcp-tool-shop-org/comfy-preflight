"""`preflight()` — the aggregator.

Three properties carry this file:

1. **One entry point.** There is no non-raising twin, because that would be a skip flag under
   another name. The halt carries the report instead, and a test reads the module for a second
   entry point rather than trusting that nobody added one.
2. **One raise, carrying everything.** A caller must not have to fix defects one rerun at a
   time on a gate whose whole job is to run once before an irreversible act.
3. **The merge order is the ratified one**, including the rung that surprises people.
"""

from __future__ import annotations

import ast
import inspect
import json
import pathlib

import pytest
from conftest import (
    ADAPTER_15,
    CONSUMER,
    CORPUS_CARDS,
    NO_ADAPTER_14,
    all_graph_names,
    load_graph,
    load_raw,
    mutate,
)

from comfy_preflight import PreflightResult, preflight
from comfy_preflight.aggregate import AGGREGATE_NAME
from comfy_preflight.checks import NodeSchema
from comfy_preflight.errors import PreflightHalt, Verdict
from comfy_preflight.graph import Graph
from comfy_preflight.register import AdapterRegister

WITH_ADAPTER = ADAPTER_15
WITHOUT_ADAPTER = NO_ADAPTER_14

NO_ADAPTER = AdapterRegister(declared=False, known_cards=CORPUS_CARDS)
DECLARED = AdapterRegister(
    declared=True,
    card=sorted(CORPUS_CARDS)[0],
    weight=0.75,
    card_aliases=frozenset(CORPUS_CARDS),
)


def _self_link_the_decoder(raw: dict) -> None:
    """The recorded incident, reproduced by one edit. Node located by class, never by id."""
    node_id = next(nid for nid, node in raw.items() if node["class_type"] == "VAEDecode")
    raw[node_id]["inputs"]["samples"] = [node_id, 0]


# ---------------------------------------------------------------------------------------------
# The signature Amendment 2 names.
# ---------------------------------------------------------------------------------------------


def test_the_signature_is_the_one_the_amendment_specifies():
    params = list(inspect.signature(preflight).parameters)
    assert params[:3] == ["graph", "register_profile", "input_dims"]


def test_the_register_profile_is_required_and_may_be_none():
    """Passing None is a caller SAYING it has no profile. A default would let the same
    situation arrive by omission, and those two are different facts."""
    sig = inspect.signature(preflight)
    assert sig.parameters["register_profile"].default is inspect.Parameter.empty
    result = preflight(load_graph(WITH_ADAPTER), None)  # must not raise
    assert result.outcome_for(2).verdict is Verdict.NOT_APPLICABLE


def test_the_aggregator_has_no_skip_parameter():
    params = set(inspect.signature(preflight).parameters)
    forbidden = {"skip", "force", "ignore", "warn_only", "soft", "disable", "enabled"}
    assert not (params & forbidden), f"aggregator exposes a skip-shaped parameter: {params & forbidden}"


def test_there_is_exactly_one_entry_point_into_a_preflight_run():
    """A non-raising twin would be a skip flag under another name.

    Read the module rather than trust the convention: a public function whose name contains
    'preflight' and which is not `preflight` itself is the shape this refuses.
    """
    import comfy_preflight.aggregate as module

    tree = ast.parse(pathlib.Path(module.__file__).read_text(encoding="utf-8"))
    public = [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    ]
    assert public == ["preflight"], (
        f"aggregate.py exposes {public}. A second entry point into a preflight run is a skip "
        "flag with a different name — the halt carries the report instead"
    )


# ---------------------------------------------------------------------------------------------
# One raise, carrying everything.
# ---------------------------------------------------------------------------------------------


def test_a_halt_carries_every_defect_from_every_check_not_just_the_first():
    """Two independent defects, in two different checks, in one raise."""
    def two_defects(raw: dict) -> None:
        _self_link_the_decoder(raw)  # check 1
        # ...and an adapter loader the register will not declare (check 2).
        raw["9001"] = {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {"model": ["1", 0], "lora_name": sorted(CORPUS_CARDS)[0],
                       "strength_model": 0.75},
        }

    with pytest.raises(PreflightHalt) as exc:
        preflight(mutate(WITHOUT_ADAPTER, two_defects), NO_ADAPTER)

    codes = {d.code for d in exc.value.defects}
    assert "SELF_LINK" in codes
    assert "ADAPTER_LOADER_PRESENT_BUT_NOT_DECLARED" in codes
    assert exc.value.check == AGGREGATE_NAME


def test_the_halt_carries_the_full_report_so_a_renderer_needs_no_second_call():
    with pytest.raises(PreflightHalt) as exc:
        preflight(mutate(WITHOUT_ADAPTER, _self_link_the_decoder), NO_ADAPTER)
    report = exc.value.report
    assert isinstance(report, PreflightResult)
    assert report.verdict is Verdict.HALT
    assert report.checks_run == (1, 2, 4, 5, 8)


def test_every_finding_names_its_node_and_its_evidence():
    """Amendment 2's requirement on the aggregator's output, for graph-resident defects."""
    with pytest.raises(PreflightHalt) as exc:
        preflight(mutate(WITHOUT_ADAPTER, _self_link_the_decoder), NO_ADAPTER)
    for defect in exc.value.report.defects:
        assert defect.node_id is not None, f"{defect.code} names no node"
        assert defect.message and defect.hint


def test_a_frame_defect_from_the_input_image_names_the_operand_it_actually_has():
    """The one documented exception to 'every finding names its node', with its reason.

    Check 5's effective-frame operand is the *input image's* dimensions, which by construction
    are not in the graph — that is the whole point of Amendment 1's re-specification. So the
    defect has no node to name, and names `input width` instead. Claiming a node here would be
    inventing a location; leaving the message vague would be the defect this repo refuses.
    """
    with pytest.raises(PreflightHalt) as exc:
        preflight(load_graph(WITHOUT_ADAPTER), NO_ADAPTER, (1066, 1024))
    frame = [d for d in exc.value.defects if d.code == "FRAME_NOT_GENERATOR_LEGAL"]
    assert frame, "the recorded 1066 defect did not fire"
    for defect in frame:
        assert defect.node_id is None
        assert "input width" in defect.message
        assert "1064" in defect.message  # what it would actually decode to


# ---------------------------------------------------------------------------------------------
# The merge.
# ---------------------------------------------------------------------------------------------


def test_a_clean_run_with_every_operand_supplied_passes():
    """Every check evaluates at least one clause and finds nothing."""
    raw = load_raw(WITHOUT_ADAPTER)
    result = preflight(
        Graph.from_api_dict(raw),
        NO_ADAPTER,
        (1072, 1024),
        saved_graph=Graph.from_api_dict(raw),
        consumer_input=CONSUMER,
    )
    assert result.verdict is Verdict.PASS
    for outcome in result.outcomes:
        assert outcome.verdict is Verdict.PASS, f"check {outcome.number}: {outcome.verdict}"
        assert outcome.clauses_evaluated, f"check {outcome.number} passed without evaluating a clause"


def test_an_aggregate_pass_does_not_mean_every_clause_was_asked():
    """The honest reading of PASS, pinned so nobody infers the stronger claim.

    A check returns PASS when it evaluated at least one clause and found nothing — the
    convention the shipped checks already follow. Two clauses decline on a clean run no matter
    what the caller supplies: check 1's `undeclared_input` needs a node schema from a live
    ComfyUI, and check 8's denoise is a parameter the model card documents no band for. So PASS
    means *nothing was found by what could be asked*, and the unasked questions stay listed in
    `declined` rather than being folded into the verdict.

    The alternative — any declined clause forcing the aggregate to NOT_APPLICABLE — was
    considered and rejected: it would make PASS unreachable in every environment without a live
    ComfyUI, and a verdict that never occurs carries no information.
    """
    raw = load_raw(WITHOUT_ADAPTER)
    result = preflight(
        Graph.from_api_dict(raw),
        NO_ADAPTER,
        (1072, 1024),
        saved_graph=Graph.from_api_dict(raw),
        consumer_input=CONSUMER,
    )
    assert result.verdict is Verdict.PASS
    clauses = {clause for _, clause, _ in result.declined}
    assert "undeclared_input" in clauses
    assert "envelope_bands.denoise" in clauses
    for _, _, why in result.declined:
        assert len(why) > 20, "a declined clause on a PASSING run must still say why"


def test_a_declined_clause_outranks_the_passing_ones():
    """The surprising rung, at the aggregate level.

    With no input dimensions and no saved sidecar, checks 5 and 4 decline. Reporting PASS would
    let two unasked questions hide behind three answered ones.
    """
    result = preflight(load_graph(WITHOUT_ADAPTER), NO_ADAPTER, consumer_input=CONSUMER)
    assert result.verdict is Verdict.NOT_APPLICABLE
    assert {check for check, _, _ in result.declined} >= {
        "check_4_saved_is_graph_submitted",
        "check_5_generator_legal_frame",
    }


def test_an_advisory_outranks_a_declined_clause_and_does_not_raise():
    """Check 8 advising must surface above the declines, and must not stop the caller."""
    result = preflight(
        mutate(WITHOUT_ADAPTER, _set_strength_out_of_band), NO_ADAPTER, consumer_input=CONSUMER
    )
    assert result.verdict is Verdict.ADVISORY
    assert result.advisories, "the advisory finding was not surfaced"
    assert result.defects == (), "an advisory must not be reported as a halting defect"


def test_a_halt_outranks_an_advisory():
    def both(raw: dict) -> None:
        _self_link_the_decoder(raw)
        _set_strength_out_of_band(raw)

    with pytest.raises(PreflightHalt) as exc:
        preflight(mutate(WITHOUT_ADAPTER, both), NO_ADAPTER)
    report = exc.value.report
    assert report.verdict is Verdict.HALT
    assert report.advisories, "the advisory is still reported alongside the halt"


def test_an_advisory_never_raises_even_when_it_is_the_top_verdict():
    """The direction Amendment 2 rules on: ADVISORY, never HALT, at the aggregate too."""
    result = preflight(mutate(WITHOUT_ADAPTER, _set_strength_out_of_band), NO_ADAPTER)
    assert result.verdict is Verdict.ADVISORY  # returned, not raised


# ---------------------------------------------------------------------------------------------
# Coverage is reported, not inferred.
# ---------------------------------------------------------------------------------------------


def test_the_result_enumerates_what_it_ran_and_what_it_did_not():
    result = preflight(load_graph(WITHOUT_ADAPTER), NO_ADAPTER)
    assert result.checks_run == (1, 2, 4, 5, 8)
    assert [n for n, _ in result.checks_not_registered] == [3, 6, 7]
    for _, reason in result.checks_not_registered:
        assert reason.strip()


def test_every_declined_clause_says_why():
    result = preflight(load_graph(WITHOUT_ADAPTER), None)
    assert result.declined
    for check_id, clause, why in result.declined:
        assert check_id and clause and len(why) > 20, f"{check_id}.{clause} declines without a reason"


def test_the_whole_recorded_corpus_produces_no_halt_under_a_matching_register():
    """The no-false-halt leg for the AGGREGATE, over all 70.

    Each graph is run under the register condition it was actually built with, resolved from the
    graph rather than assumed — pairing a no-adapter register with an adapter graph would be a
    correct halt and would prove nothing.
    """
    halted = []
    for name in all_graph_names():
        raw = load_raw(name)
        has_loader = any(
            node["class_type"] == "LoraLoaderModelOnly" for node in raw.values()
        )
        register = DECLARED if has_loader else NO_ADAPTER
        try:
            preflight(Graph.from_api_dict(raw), register)
        except PreflightHalt as exc:
            halted.append(f"{name}: {[d.code for d in exc.defects]}")
    assert not halted, "the aggregator halted on recorded work:\n" + "\n".join(halted)


# ---------------------------------------------------------------------------------------------
# The JSON rendering the CLI and the MCP both return.
# ---------------------------------------------------------------------------------------------


def test_the_result_renders_to_json_safe_data():
    result = preflight(load_graph(WITHOUT_ADAPTER), NO_ADAPTER, (1072, 1024))
    payload = result.to_dict()
    round_tripped = json.loads(json.dumps(payload))
    assert round_tripped == payload


def test_the_rendering_carries_verdict_clauses_and_findings_per_check():
    result = preflight(mutate(WITHOUT_ADAPTER, _set_strength_out_of_band), NO_ADAPTER)
    payload = result.to_dict()
    assert payload["verdict"] == "advisory"
    by_number = {entry["check"]: entry for entry in payload["checks"]}
    assert set(by_number) == {1, 2, 4, 5, 8}
    c8 = by_number[8]
    assert c8["verdict"] == "advisory"
    assert c8["findings"][0]["code"] == "PARAMETER_OUTSIDE_DECLARED_ENVELOPE"
    assert c8["findings"][0]["node_id"]
    assert any(d["clause"].endswith("denoise") for d in c8["clauses_declined"])


def test_a_halted_run_renders_through_the_report_on_the_exception():
    with pytest.raises(PreflightHalt) as exc:
        preflight(mutate(WITHOUT_ADAPTER, _self_link_the_decoder), NO_ADAPTER)
    payload = exc.value.report.to_dict()
    assert payload["verdict"] == "halt"
    by_number = {entry["check"]: entry for entry in payload["checks"]}
    assert by_number[1]["findings"][0]["code"] == "SELF_LINK"


# ---------------------------------------------------------------------------------------------
# The askability parameters reach the checks they belong to.
# ---------------------------------------------------------------------------------------------


def test_input_dims_reaches_check_5_and_halts_on_the_recorded_defect():
    """1066 is the width from the record: it decodes to 1064 and breaks every pairing."""
    with pytest.raises(PreflightHalt) as exc:
        preflight(load_graph(WITHOUT_ADAPTER), NO_ADAPTER, (1066, 1024))
    codes = {d.code for d in exc.value.defects}
    assert "FRAME_NOT_GENERATOR_LEGAL" in codes


def test_input_dims_at_a_legal_frame_passes_check_5():
    result = preflight(load_graph(WITHOUT_ADAPTER), NO_ADAPTER, (1072, 1024))
    assert result.outcome_for(5).verdict is Verdict.PASS


def test_the_family_parameter_reaches_check_5():
    """An unmeasured family declines rather than borrowing Qwen's divisor."""
    result = preflight(load_graph(WITHOUT_ADAPTER), NO_ADAPTER, (1066, 1066), family="flux")
    assert result.outcome_for(5).verdict is Verdict.NOT_APPLICABLE


def test_the_schema_parameter_reaches_check_1():
    schema = NodeSchema(inputs_by_class={"VAEDecode": frozenset({"samples", "vae"})})
    result = preflight(load_graph(WITHOUT_ADAPTER), NO_ADAPTER, schema=schema)
    assert "undeclared_input" in result.outcome_for(1).clauses_evaluated


def test_the_saved_graph_parameter_reaches_check_4_and_catches_a_moved_value():
    raw = load_raw(WITHOUT_ADAPTER)
    submitted = mutate(WITHOUT_ADAPTER, _bump_the_seed)
    with pytest.raises(PreflightHalt) as exc:
        preflight(submitted, NO_ADAPTER, saved_graph=Graph.from_api_dict(raw))
    codes = {d.code for d in exc.value.defects}
    assert "VALUE_CHANGED" in codes


def test_the_envelope_table_parameter_reaches_check_8():
    result = preflight(load_graph(WITHOUT_ADAPTER), NO_ADAPTER, envelope_table={})
    assert result.outcome_for(8).verdict is Verdict.NOT_APPLICABLE


def _set_strength_out_of_band(raw: dict) -> None:
    for node in raw.values():
        if node["class_type"] == "ControlNetApplyAdvanced":
            node["inputs"]["strength"] = 0.4


def _bump_the_seed(raw: dict) -> None:
    """Locate the sampler by HAVING a seed, never by an assumed id."""
    node_id = next(nid for nid, node in raw.items() if "seed" in node["inputs"])
    raw[node_id]["inputs"]["seed"] += 1
