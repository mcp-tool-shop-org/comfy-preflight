"""Check 1 — link topology.

The FIRE fixture reproduces the founding incident: node 14's `samples` repointed from `['13', 0]`
to `['14', 0]` in the graph that was actually in that incident. The corpus carries 0 self-links
and 0 dangling links across all 70 graphs, so there is no natural failing fixture and the break
is constructed by one documented edit.
"""

from __future__ import annotations

import pytest
from conftest import ADAPTER_15, all_graph_names, load_graph, load_raw, mutate

from comfy_preflight.checks.c1_link_topology import (
    CHECK_NAME,
    NodeSchema,
    check_link_topology,
)
from comfy_preflight.errors import PreflightHalt, Verdict

# The incident graph: node 14 is VAEDecode, whose `samples` correctly reads node 13 (KSampler).
INCIDENT_GRAPH = ADAPTER_15


# --------------------------------------------------------------------------- #
# The premise the FIRE fixture is built on.
# --------------------------------------------------------------------------- #


def test_the_incident_graph_is_the_corrected_one():
    """The recorded payload that got past dry_run was discarded, so disk holds the FIX.

    If node 14 ever reads itself on disk, the fixture is the broken payload and the mutation
    below is no longer a one-edit construction.
    """
    raw = load_raw(INCIDENT_GRAPH)
    if raw["14"]["class_type"] != "VAEDecode":
        raise AssertionError(f"node 14 is {raw['14']['class_type']}, not VAEDecode")
    if raw["14"]["inputs"]["samples"] != ["13", 0]:
        raise AssertionError(
            f"node 14.samples is {raw['14']['inputs']['samples']}, expected ['13', 0]"
        )


def test_the_whole_corpus_has_no_self_links_and_no_dangling_links():
    """70 PASS fixtures, 0 natural FIRE fixtures. Recorded so the absence is a measurement."""
    for name in all_graph_names():
        result = check_link_topology(load_graph(name))
        if result.verdict is not Verdict.PASS:
            raise AssertionError(f"{name}: verdict {result.verdict}")
        if result.links_examined <= 0:
            raise AssertionError(f"{name}: examined {result.links_examined} links")


# --------------------------------------------------------------------------- #
# Clause 1a — the self-link. The founding case.
# --------------------------------------------------------------------------- #


def test_fires_on_the_recorded_self_link():
    """VAEDecode.samples = ['14', 0] — the node pointing at itself.

    Comfy Cloud's dry_run returned `status: validated` on exactly this graph shape.
    """

    def self_link(raw):
        raw["14"]["inputs"]["samples"] = ["14", 0]

    with pytest.raises(PreflightHalt) as exc:
        check_link_topology(mutate(INCIDENT_GRAPH, self_link))

    assert exc.value.check == CHECK_NAME
    defects = exc.value.defects
    assert [d.code for d in defects] == ["SELF_LINK"]
    assert defects[0].node_id == "14"
    assert defects[0].input_name == "samples"


def test_a_self_link_is_reported_once_not_also_as_dangling():
    """One defect per cause.

    A self-link's target IS in the graph, so clause 1b must not also fire on it. Two defects for
    one edit reads as two problems.
    """

    def self_link(raw):
        raw["14"]["inputs"]["samples"] = ["14", 0]

    with pytest.raises(PreflightHalt) as exc:
        check_link_topology(mutate(INCIDENT_GRAPH, self_link))
    assert len(exc.value.defects) == 1


# --------------------------------------------------------------------------- #
# Clause 1b — the dangling link.
# --------------------------------------------------------------------------- #


def test_fires_on_a_link_to_a_node_id_not_in_the_graph():
    def dangling(raw):
        raw["14"]["inputs"]["samples"] = ["99", 0]

    with pytest.raises(PreflightHalt) as exc:
        check_link_topology(mutate(INCIDENT_GRAPH, dangling))
    defect = exc.value.defects[0]
    assert defect.code == "DANGLING_LINK"
    assert defect.node_id == "14"
    assert "'99'" in defect.message


def test_fires_on_a_link_left_behind_by_a_deleted_node():
    """The realistic shape: a node is removed and its consumers still point at it."""

    def delete_producer(raw):
        del raw["13"]  # KSampler; node 14 still reads it

    with pytest.raises(PreflightHalt) as exc:
        check_link_topology(mutate(INCIDENT_GRAPH, delete_producer))
    codes = {d.code for d in exc.value.defects}
    assert codes == {"DANGLING_LINK"}


# --------------------------------------------------------------------------- #
# Clause 1c — undeclared input. NOT_APPLICABLE without an injected schema.
# --------------------------------------------------------------------------- #


def test_undeclared_input_clause_declines_without_a_schema():
    """No schema, no clause — and it says which clause and why.

    The schema is not inferred from the corpus: deriving the reference from the thing being
    checked would make the gate a tautology.
    """
    result = check_link_topology(load_graph(INCIDENT_GRAPH))
    declined = dict(result.clauses_declined)
    assert "undeclared_input" in declined
    assert "not askable" in declined["undeclared_input"]
    assert "undeclared_input" not in result.clauses_evaluated
    # The other two clauses still ran.
    assert "self_link" in result.clauses_evaluated
    assert "dangling_link" in result.clauses_evaluated


def test_undeclared_input_clause_runs_with_a_schema_and_passes_a_matching_graph():
    raw = load_raw(INCIDENT_GRAPH)
    schema = NodeSchema(
        inputs_by_class={
            node["class_type"]: frozenset(node.get("inputs", {})) for node in raw.values()
        }
    )
    result = check_link_topology(load_graph(INCIDENT_GRAPH), schema=schema)
    assert result.verdict is Verdict.PASS
    assert "undeclared_input" in result.clauses_evaluated
    assert result.classes_not_in_schema == ()


def test_fires_on_an_input_the_class_does_not_declare():
    """A misspelled input is silently ignored by the runtime, so the value never arrives."""
    raw = load_raw(INCIDENT_GRAPH)
    schema = NodeSchema(
        inputs_by_class={
            node["class_type"]: frozenset(node.get("inputs", {})) for node in raw.values()
        }
    )

    def misspell(r):
        r["13"]["inputs"]["step"] = r["13"]["inputs"].pop("steps")  # steps -> step

    with pytest.raises(PreflightHalt) as exc:
        check_link_topology(mutate(INCIDENT_GRAPH, misspell), schema=schema)
    codes = {d.code for d in exc.value.defects}
    assert "UNDECLARED_INPUT" in codes
    offender = next(d for d in exc.value.defects if d.code == "UNDECLARED_INPUT")
    assert offender.input_name == "step"
    assert offender.node_id == "13"


def test_a_class_absent_from_the_schema_is_reported_not_assumed():
    """A schema that does not cover a node cannot answer for it, in either direction."""
    schema = NodeSchema(inputs_by_class={"VAEDecode": frozenset({"samples", "vae"})})
    result = check_link_topology(load_graph(INCIDENT_GRAPH), schema=schema)
    assert result.verdict is Verdict.PASS
    assert "KSampler" in result.classes_not_in_schema
    assert any("not in the supplied schema" in n for n in result.notes)


def test_a_partial_schema_still_catches_a_covered_class():
    """Declining part of a clause must not weaken the rest of it."""
    schema = NodeSchema(inputs_by_class={"VAEDecode": frozenset({"samples", "vae"})})

    def add_bogus(raw):
        raw["14"]["inputs"]["sampels"] = ["13", 0]  # typo on a COVERED class

    with pytest.raises(PreflightHalt) as exc:
        check_link_topology(mutate(INCIDENT_GRAPH, add_bogus), schema=schema)
    assert "UNDECLARED_INPUT" in {d.code for d in exc.value.defects}


# --------------------------------------------------------------------------- #
# Shape.
# --------------------------------------------------------------------------- #


def test_check_has_no_skip_parameter():
    import inspect

    params = set(inspect.signature(check_link_topology).parameters)
    forbidden = {"skip", "force", "ignore", "warn_only", "soft", "disable", "enabled"}
    assert not (params & forbidden), f"check exposes a skip-shaped parameter: {params & forbidden}"


def test_a_link_shaped_literal_is_not_treated_as_a_link():
    """`is_link` is structural. A two-element list that is not [str, int] is a literal.

    Without this, a legitimate list value would be misread as a wire and reported dangling.
    """

    def literal_pair(raw):
        raw["13"]["inputs"]["some_pair"] = ["not", "a link"]

    result = check_link_topology(mutate(INCIDENT_GRAPH, literal_pair))
    assert result.verdict is Verdict.PASS
