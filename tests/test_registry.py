"""The check registry — the composition surface, not a hardcoded list.

The property this file exists to pin: **`preflight()` runs what is registered**, so a check
added to the registry runs without editing the aggregator, and a check dropped from it is
visible in the result rather than looking like a check that passed.
"""

from __future__ import annotations

import inspect

import pytest
from conftest import ADAPTER_15, CONSUMER, CORPUS_CARDS, NO_ADAPTER_14, load_graph, mutate

from comfy_preflight import aggregate
from comfy_preflight.errors import Defect, PreflightHalt, Verdict
from comfy_preflight.register import AdapterRegister
from comfy_preflight.registry import (
    NOT_REGISTERED,
    REGISTRY,
    CheckInputs,
    CheckOutcome,
    RegisteredCheck,
    registered_numbers,
)

# Two Union-checkpoint fixtures, one per register condition. Pairing a declared=False
# register with a graph that carries the adapter is a correct HALT, not a test bed — the
# register condition and the graph must agree or check 2 fires before anything else is
# measured.
WITH_ADAPTER = ADAPTER_15
WITHOUT_ADAPTER = NO_ADAPTER_14

NO_ADAPTER = AdapterRegister(declared=False, known_cards=CORPUS_CARDS)


def _self_link_the_decoder(raw: dict) -> None:
    """Repoint VAEDecode.samples at its own node — the recorded incident, one edit.

    The node is located by CLASS, never by an assumed id: this corpus carries the decoder at
    different numbers in different branches, and an assumed id is a fixture that breaks
    silently the moment the pair changes."""
    node_id = next(
        nid for nid, node in raw.items() if node["class_type"] == "VAEDecode"
    )
    raw[node_id]["inputs"]["samples"] = [node_id, 0]


def test_the_registry_carries_the_five_checks_the_amendment_composes():
    assert registered_numbers() == (1, 2, 4, 5, 8)


def test_the_registry_is_ordered_by_check_number():
    """A report reads in the order the spec's table does, rather than in definition order."""
    numbers = registered_numbers()
    assert list(numbers) == sorted(numbers)


def test_every_registered_check_has_a_distinct_id_and_a_title():
    ids = [spec.check_id for spec in REGISTRY]
    assert len(set(ids)) == len(ids)
    for spec in REGISTRY:
        assert spec.title and spec.check_id.startswith(f"check_{spec.number}_")


def test_the_unregistered_checks_are_named_with_their_reasons():
    """The spec lists seven. The three that are out are named in code, not only in the README."""
    assert sorted(NOT_REGISTERED) == [3, 6, 7]
    for number, reason in NOT_REGISTERED.items():
        assert reason.strip(), f"check {number} is excluded without a stated reason"
    assert not set(NOT_REGISTERED) & set(registered_numbers())


def test_a_check_added_to_the_registry_runs_without_editing_the_aggregator():
    """The load-bearing property of a registry, proven rather than asserted.

    This is how check 8 landed: one RegisteredCheck plus one adapter, no edit to preflight().
    """
    seen: list[CheckInputs] = []

    def call(spec: RegisteredCheck, inputs: CheckInputs) -> CheckOutcome:
        seen.append(inputs)
        return CheckOutcome(
            check_id=spec.check_id,
            number=spec.number,
            title=spec.title,
            verdict=Verdict.PASS,
            clauses_evaluated=("synthetic",),
        )

    extra = RegisteredCheck("check_99_synthetic", 99, "Synthetic", call)
    result = aggregate.preflight(
        load_graph(WITHOUT_ADAPTER), NO_ADAPTER, checks=(*REGISTRY, extra)
    )

    assert len(seen) == 1, "the added check was not invoked"
    assert 99 in result.checks_run
    assert result.outcome_for(99).clauses_evaluated == ("synthetic",)


def test_a_check_removed_from_the_registry_is_visible_in_the_result():
    """The other direction. Coverage is reported, so a missing check cannot read as a pass."""
    without_c8 = tuple(spec for spec in REGISTRY if spec.number != 8)
    result = aggregate.preflight(load_graph(WITHOUT_ADAPTER), NO_ADAPTER, checks=without_c8)
    assert 8 not in result.checks_run
    assert result.outcome_for(8) is None


def test_an_adapter_catches_its_own_checks_halt_so_later_checks_still_run():
    """One check halting must not deny the caller the other four checks' findings.

    Without this, a graph with a self-link would report the self-link and nothing else, and the
    caller would fix it, rerun, and discover the next defect — a gate run five times before an
    act it exists to gate once.
    """
    broken = mutate(WITHOUT_ADAPTER, _self_link_the_decoder)
    with pytest.raises(PreflightHalt) as exc:
        aggregate.preflight(broken, NO_ADAPTER)

    report = exc.value.report
    assert report.outcome_for(1).verdict is Verdict.HALT
    # ...and every other check still produced an outcome.
    assert {o.number for o in report.outcomes} == {1, 2, 4, 5, 8}


def test_a_halted_outcome_carries_no_invented_clause_accounting():
    """A check that raised never returned its clauses; reporting an empty tuple as if measured
    would say 'no clauses evaluated' about a check that evaluated enough to find a defect."""
    broken = mutate(WITHOUT_ADAPTER, _self_link_the_decoder)
    with pytest.raises(PreflightHalt) as exc:
        aggregate.preflight(broken, NO_ADAPTER)
    outcome = exc.value.report.outcome_for(1)
    assert outcome.detail is None
    assert outcome.defects, "a halt outcome must carry the defects that caused it"


def test_a_passing_outcome_carries_the_checks_own_result_verbatim():
    """Nothing a check measured is lost in translation to the uniform shape."""
    result = aggregate.preflight(load_graph(WITHOUT_ADAPTER), NO_ADAPTER)
    detail = result.outcome_for(8).detail
    assert detail is not None
    assert detail.checkpoints_covered  # a field only check 8 has
    assert detail.verdict is result.outcome_for(8).verdict


def test_check_2_declines_rather_than_crashing_without_a_register():
    result = aggregate.preflight(load_graph(WITH_ADAPTER), None)
    outcome = result.outcome_for(2)
    assert outcome.verdict is Verdict.NOT_APPLICABLE
    why = dict(outcome.clauses_declined)["register_scan"]
    assert "tautology" in why


def test_check_4_declines_rather_than_crashing_without_a_saved_graph():
    result = aggregate.preflight(load_graph(WITHOUT_ADAPTER), NO_ADAPTER)
    outcome = result.outcome_for(4)
    assert outcome.verdict is Verdict.NOT_APPLICABLE
    why = dict(outcome.clauses_declined)["saved_is_submitted"]
    assert "saved_graph" in why


def test_check_inputs_exposes_no_skip_shaped_field():
    """The askability parameters make clauses askable; none of them turns a check off."""
    fields = {f.name for f in CheckInputs.__dataclass_fields__.values()}
    forbidden = {"skip", "force", "ignore", "warn_only", "soft", "disable", "enabled"}
    assert not (fields & forbidden)


def test_registered_check_run_takes_only_inputs():
    """The uniform call the registry defines, pinned so an adapter cannot widen it."""
    params = list(inspect.signature(RegisteredCheck.run).parameters)
    assert params == ["self", "inputs"]


def test_the_default_envelope_table_is_shared_not_copied_per_call():
    """Two CheckInputs must resolve the same table, so an extended table is not silently lost."""
    a, b = CheckInputs(graph=load_graph(WITHOUT_ADAPTER)), CheckInputs(graph=load_graph(WITHOUT_ADAPTER))
    assert a.envelope_table is b.envelope_table


def test_an_unexpected_exception_from_a_check_is_not_swallowed():
    """The adapter catches PreflightHalt, and ONLY PreflightHalt.

    A bare `except Exception` would turn a bug in a check into a quiet non-result — the exact
    shape of a gate that cannot fail. A programming error must reach the caller.
    """

    def boom(spec: RegisteredCheck, inputs: CheckInputs) -> CheckOutcome:
        raise RuntimeError("a bug in a check, not a graph defect")

    exploding = RegisteredCheck("check_98_synthetic", 98, "Synthetic", boom)
    with pytest.raises(RuntimeError, match="a bug in a check"):
        aggregate.preflight(load_graph(WITHOUT_ADAPTER), NO_ADAPTER, checks=(exploding,))


def test_the_adapter_converts_a_halt_without_losing_a_defect():
    def halting(spec: RegisteredCheck, inputs: CheckInputs) -> CheckOutcome:
        raise PreflightHalt(
            spec.check_id,
            [
                Defect(code="A", message="m1", hint="h1", node_id="1"),
                Defect(code="B", message="m2", hint="h2", node_id="2"),
            ],
        )

    spec = RegisteredCheck("check_97_synthetic", 97, "Synthetic", halting)
    outcome = spec.run(CheckInputs(graph=load_graph(WITHOUT_ADAPTER)))
    assert outcome.verdict is Verdict.HALT
    assert [d.code for d in outcome.defects] == ["A", "B"]


def test_the_registry_composition_matches_the_documented_consumer_link():
    """A sanity leg tying the registry to the corpus: the register clause really runs."""
    result = aggregate.preflight(
        load_graph(WITH_ADAPTER),
        AdapterRegister(
            declared=True,
            card=sorted(CORPUS_CARDS)[0],
            weight=0.75,
            card_aliases=frozenset(CORPUS_CARDS),
        ),
        consumer_input=CONSUMER,
    )
    outcome = result.outcome_for(2)
    assert "consumer_link" in outcome.clauses_evaluated
