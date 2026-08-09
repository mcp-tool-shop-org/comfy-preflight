"""Check 2 — the inverted register scan, in both directions.

Every FIRE leg mutates a real recorded graph, so the PASS case and the FIRE case differ by
exactly the edit under test. A check whose failing case was hand-authored separately from its
passing case is testing two different graphs, not one edit.
"""

from __future__ import annotations

import pytest
from conftest import (
    ADAPTER_15,
    ADAPTER_17,
    CONSUMER,
    CORPUS_CARD,
    CORPUS_CARD_ALIAS,
    CORPUS_CARDS,
    NO_ADAPTER_14,
    NO_ADAPTER_16,
    all_graph_names,
    load_graph,
    load_raw,
    mutate,
)

from comfy_preflight.checks.c2_register import CHECK_NAME, check_register_scan
from comfy_preflight.errors import PreflightHalt, Verdict
from comfy_preflight.register import AdapterRegister

BRANCH_PAIRS = [
    pytest.param(ADAPTER_17, NO_ADAPTER_16, id="17-vs-16"),
    pytest.param(ADAPTER_15, NO_ADAPTER_14, id="15-vs-14"),
]

# The declared register names one card and its alias — the same adapter under two cloud-side
# namespaces. See test_the_corpus_carries_two_names_for_one_adapter for the measurement.
DECLARED = AdapterRegister(
    declared=True,
    card=CORPUS_CARD,
    weight=0.75,
    card_aliases=frozenset({CORPUS_CARD_ALIAS}),
)
NOT_DECLARED = AdapterRegister(declared=False, known_cards=CORPUS_CARDS)


# --------------------------------------------------------------------------- #
# The premise: the two branches differ by exactly one node.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("with_card,without_card", BRANCH_PAIRS)
def test_branches_differ_by_exactly_one_node(with_card, without_card):
    """The falsifiable statement check 2 produces, on both recorded pairs.

    If this ever stops holding, the fixtures are no longer a with/without pair and every PASS
    below is measuring something else.
    """
    a, b = load_raw(with_card), load_raw(without_card)
    symmetric_difference = set(a) ^ set(b)
    if symmetric_difference != {"5"}:
        raise AssertionError(
            f"expected the branches to differ by exactly node 5; got {symmetric_difference}"
        )
    if a["5"]["class_type"] != "LoraLoaderModelOnly":
        raise AssertionError(f"node 5 is {a['5']['class_type']}, not the adapter loader")
    # The link assertion: with the card the consumer reads the loader; without it, the base.
    if a["6"]["inputs"]["model"] != ["5", 0]:
        raise AssertionError("with-card branch: consumer does not read the loader")
    if b["6"]["inputs"]["model"] != ["1", 0]:
        raise AssertionError("no-card branch: consumer does not read the base model")


# --------------------------------------------------------------------------- #
# PASS legs — real graphs, correct registers.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("with_card,without_card", BRANCH_PAIRS)
def test_pass_when_adapter_declared_and_present(with_card, without_card):
    result = check_register_scan(load_graph(with_card), DECLARED, consumer_input=CONSUMER)
    assert result.verdict is Verdict.PASS
    assert result.loader_nodes == ("5",)
    assert "loader_nodes" in result.clauses_evaluated
    assert "consumer_link" in result.clauses_evaluated


@pytest.mark.parametrize("with_card,without_card", BRANCH_PAIRS)
def test_pass_when_no_adapter_declared_and_none_present(with_card, without_card):
    result = check_register_scan(load_graph(without_card), NOT_DECLARED, consumer_input=CONSUMER)
    assert result.verdict is Verdict.PASS
    assert result.loader_nodes == ()
    assert result.card_references == ()
    assert "card_vocabulary" in result.clauses_evaluated


# --------------------------------------------------------------------------- #
# FIRE leg — DIRECTION 1: declared, but silently inert. The mirror direction.
# --------------------------------------------------------------------------- #


def test_fires_when_adapter_declared_but_loader_absent():
    """The silently-inert case: a decided positive weight with no loader node.

    Produced by removing node 5 from the with-card graph and repointing the consumer at the
    base model — which is precisely the no-card branch — while the register still declares the
    adapter. The run would complete, cost credits, and produce base-model output.
    """

    def strip_loader(raw):
        del raw["5"]
        raw["6"]["inputs"]["model"] = ["1", 0]

    graph = mutate(ADAPTER_17, strip_loader)
    with pytest.raises(PreflightHalt) as exc:
        check_register_scan(graph, DECLARED, consumer_input=CONSUMER)
    codes = {d.code for d in exc.value.defects}
    assert "ADAPTER_DECLARED_BUT_NO_LOADER" in codes
    assert exc.value.check == CHECK_NAME


def test_fires_when_consumer_bypasses_a_present_loader():
    """The card is loaded and unused — a subtler inertness with the loader still in the graph."""

    def bypass(raw):
        raw["6"]["inputs"]["model"] = ["1", 0]  # straight to the base model

    graph = mutate(ADAPTER_17, bypass)
    with pytest.raises(PreflightHalt) as exc:
        check_register_scan(graph, DECLARED, consumer_input=CONSUMER)
    assert "CONSUMER_BYPASSES_DECLARED_ADAPTER" in {d.code for d in exc.value.defects}


def test_fires_when_card_is_loaded_at_zero_weight():
    """A weight of 0.0 on a loaded card is not the no-adapter condition; it is the inverse."""

    def zero(raw):
        raw["5"]["inputs"]["strength_model"] = 0.0

    graph = mutate(ADAPTER_17, zero)
    with pytest.raises(PreflightHalt) as exc:
        check_register_scan(graph, DECLARED, consumer_input=CONSUMER)
    assert "ADAPTER_LOADED_AT_ZERO_WEIGHT" in {d.code for d in exc.value.defects}


def test_fires_on_weight_mismatch():
    def bump(raw):
        raw["5"]["inputs"]["strength_model"] = 1.25

    with pytest.raises(PreflightHalt) as exc:
        check_register_scan(mutate(ADAPTER_17, bump), DECLARED, consumer_input=CONSUMER)
    assert "ADAPTER_WEIGHT_MISMATCH" in {d.code for d in exc.value.defects}


def test_fires_on_card_mismatch():
    def swap(raw):
        raw["5"]["inputs"]["lora_name"] = "some_other_style_v1.safetensors"

    with pytest.raises(PreflightHalt) as exc:
        check_register_scan(mutate(ADAPTER_17, swap), DECLARED, consumer_input=CONSUMER)
    assert "ADAPTER_CARD_MISMATCH" in {d.code for d in exc.value.defects}


# --------------------------------------------------------------------------- #
# FIRE leg — DIRECTION 2: not declared, but present.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("with_card,without_card", BRANCH_PAIRS)
def test_fires_when_loader_present_but_not_declared(with_card, without_card):
    """The no-adapter claim is about ABSENCE of a loader, not about a weight of 0.0."""
    with pytest.raises(PreflightHalt) as exc:
        check_register_scan(load_graph(with_card), NOT_DECLARED, consumer_input=CONSUMER)
    codes = {d.code for d in exc.value.defects}
    assert "ADAPTER_LOADER_PRESENT_BUT_NOT_DECLARED" in codes
    assert "CONSUMER_READS_THROUGH_LOADER" in codes


def test_fires_when_loader_present_at_zero_weight_and_not_declared():
    """The exact confusion the check exists to reject.

    Someone "turns the adapter off" by setting the weight to 0.0 and declares no adapter. The
    card is still loaded. That is not the no-adapter condition.
    """

    def zero(raw):
        raw["5"]["inputs"]["strength_model"] = 0.0

    with pytest.raises(PreflightHalt) as exc:
        check_register_scan(mutate(ADAPTER_17, zero), NOT_DECLARED, consumer_input=CONSUMER)
    assert "ADAPTER_LOADER_PRESENT_BUT_NOT_DECLARED" in {d.code for d in exc.value.defects}


def test_fires_on_a_card_reference_with_no_loader_node():
    """A card named somewhere in the graph with no loader is still not the absence claimed."""

    def plant(raw):
        raw["7"]["inputs"]["text"] = CORPUS_CARD  # a card name in a text input

    with pytest.raises(PreflightHalt) as exc:
        check_register_scan(mutate(NO_ADAPTER_16, plant), NOT_DECLARED, consumer_input=CONSUMER)
    codes = {d.code for d in exc.value.defects}
    assert "ADAPTER_CARD_REFERENCED_BUT_NOT_DECLARED" in codes


def test_fires_on_an_unrecognised_loader_class():
    """An unknown class naming itself an adapter loader must not evade the scan.

    A gate that fails open on a node it does not recognise is not a gate.
    """

    def rename(raw):
        raw["5"]["class_type"] = "SomeVendorLoraLoaderXL"

    with pytest.raises(PreflightHalt) as exc:
        check_register_scan(mutate(ADAPTER_17, rename), NOT_DECLARED, consumer_input=CONSUMER)
    assert "ADAPTER_LOADER_PRESENT_BUT_NOT_DECLARED" in {d.code for d in exc.value.defects}


# --------------------------------------------------------------------------- #
# Clause accounting — a declined clause must never read as a passed one.
# --------------------------------------------------------------------------- #


def test_card_vocabulary_clause_is_declined_when_the_register_names_no_cards():
    bare = AdapterRegister(declared=False)  # no known_cards
    result = check_register_scan(load_graph(NO_ADAPTER_16), bare, consumer_input=CONSUMER)
    declined = dict(result.clauses_declined)
    assert "card_vocabulary" in declined
    assert "not askable" in declined["card_vocabulary"]
    assert "card_vocabulary" not in result.clauses_evaluated


def test_consumer_clause_is_declined_when_no_consumer_is_named():
    result = check_register_scan(load_graph(NO_ADAPTER_16), NOT_DECLARED)
    declined = dict(result.clauses_declined)
    assert "consumer_link" in declined
    assert "consumer_link" not in result.clauses_evaluated


def test_a_declined_vocabulary_clause_still_catches_the_loader():
    """Declining one clause must not weaken the others."""
    bare = AdapterRegister(declared=False)
    with pytest.raises(PreflightHalt) as exc:
        check_register_scan(load_graph(ADAPTER_17), bare, consumer_input=CONSUMER)
    assert "ADAPTER_LOADER_PRESENT_BUT_NOT_DECLARED" in {d.code for d in exc.value.defects}


# --------------------------------------------------------------------------- #
# The measured reason the vocabulary is declared rather than sniffed.
# --------------------------------------------------------------------------- #


def test_the_corpus_carries_two_names_for_one_adapter():
    """The measurement that forced `card_aliases`, pinned so it cannot be re-derived.

    Both names carry the same underlying LoRA (`saltroad_style_v2_lowlr_000001500`) under
    different cloud-side namespace prefixes. Exact-string comparison against a single declared
    card halts a correct build on whichever graph carries the other name, and the whole
    basename differs so basename comparison does not rescue it either.

    This also records why one walk is not an enumeration: 26 graphs carry the first name and
    exactly ONE carries the second, so a scan that misses a single file reports "one card".
    """
    seen: dict[str, int] = {}
    for name in all_graph_names():
        for node in load_raw(name).values():
            card = (node.get("inputs") or {}).get("lora_name")
            if isinstance(card, str):
                seen[card] = seen.get(card, 0) + 1

    if set(seen) != set(CORPUS_CARDS):
        raise AssertionError(f"expected exactly the two known card names; saw {sorted(seen)}")
    if sorted(seen.values()) != [1, 26]:
        raise AssertionError(f"expected counts 1 and 26; saw {sorted(seen.values())}")
    # Same trained weights, different namespace: the tail is shared, the prefix is not.
    tail = "saltroad_style_v2_lowlr_000001500.safetensors"
    for card in seen:
        if not card.endswith(tail):
            raise AssertionError(f"{card!r} does not share the common tail {tail!r}")


def test_an_alias_is_accepted_and_an_unrelated_card_is_not():
    """Aliases must widen acceptance for the declared adapter WITHOUT widening it generally.

    The failure mode of a fuzzy matcher: a wrong card whose name shares a tail passes. This
    leg proves the alias mechanism does not do that.
    """

    def to_alias(raw):
        raw["5"]["inputs"]["lora_name"] = CORPUS_CARD_ALIAS

    # The declared alias is accepted.
    result = check_register_scan(mutate(ADAPTER_17, to_alias), DECLARED, consumer_input=CONSUMER)
    assert result.verdict is Verdict.PASS

    # A different card sharing the same tail is NOT accepted, which a prefix-stripping
    # heuristic would have let through.
    def to_lookalike(raw):
        raw["5"]["inputs"]["lora_name"] = (
            "someoneelse__other-lora__saltroad_style_v2_lowlr_000001500.safetensors"
        )

    with pytest.raises(PreflightHalt) as exc:
        check_register_scan(mutate(ADAPTER_17, to_lookalike), DECLARED, consumer_input=CONSUMER)
    assert "ADAPTER_CARD_MISMATCH" in {d.code for d in exc.value.defects}


def test_declared_vocabulary_does_not_fire_on_base_model_filenames():
    """The finding that shaped this check, pinned as a test.

    Scanning for any '.safetensors' string matches the base UNET, CLIP, VAE and ControlNet on
    every graph in the corpus — including every graph with no adapter. This leg walks the whole
    corpus with the no-adapter register and confirms the vocabulary approach flags only real
    card references, so the check does not halt correct builds.
    """
    naive_hits = 0
    vocab_hits = 0
    for name in all_graph_names():
        raw = load_raw(name)
        strings = [
            v
            for node in raw.values()
            for v in (node.get("inputs") or {}).values()
            if isinstance(v, str)
        ]
        if any(s.endswith(".safetensors") for s in strings):
            naive_hits += 1
        if any(s in CORPUS_CARDS for s in strings):
            vocab_hits += 1

    total = len(all_graph_names())
    # A naive extension scan fires on every graph; that is why it is not the check.
    if naive_hits != total:
        raise AssertionError(
            f"expected a naive '.safetensors' scan to match all {total} graphs; got {naive_hits}"
        )
    # The declared vocabulary matches only the graphs that actually carry the card.
    if not (0 < vocab_hits < total):
        raise AssertionError(
            f"expected the declared card to appear in some but not all graphs; got {vocab_hits}"
        )


def test_whole_corpus_splits_cleanly_under_the_right_register():
    """Every graph in the corpus passes under the register matching its own construction.

    This is the no-false-halt leg. If check 2 fired on a correct build anywhere in 70 recorded
    graphs, it would be disabled by the third person who hit it.
    """
    with_loader, without_loader = [], []
    for name in all_graph_names():
        graph = load_graph(name)
        has_loader = any(
            n.class_type == "LoraLoaderModelOnly" for n in graph.nodes.values()
        )
        register = DECLARED if has_loader else NOT_DECLARED
        result = check_register_scan(graph, register, consumer_input=CONSUMER)
        if result.verdict is not Verdict.PASS:
            raise AssertionError(f"{name}: verdict {result.verdict}")
        (with_loader if has_loader else without_loader).append(name)

    if len(with_loader) + len(without_loader) != 70:
        raise AssertionError(f"expected 70 graphs; saw {len(with_loader) + len(without_loader)}")
    if not with_loader or not without_loader:
        raise AssertionError("the corpus must contain both branches for this leg to mean anything")


# --------------------------------------------------------------------------- #
# The register refuses malformed declarations — and raises, so -O cannot delete it.
# --------------------------------------------------------------------------- #


def test_register_refuses_declared_with_zero_weight():
    """'A weight of 0.0 is not a declaration of an adapter, it is no adapter.'"""
    with pytest.raises(ValueError, match="weight of 0.0 is not a declaration"):
        AdapterRegister(declared=True, card=CORPUS_CARD, weight=0.0)


def test_register_refuses_declared_without_a_card():
    with pytest.raises(ValueError, match="requires `card`"):
        AdapterRegister(declared=True, weight=0.75)


def test_register_refuses_not_declared_carrying_a_weight():
    with pytest.raises(ValueError, match="must not carry a card or weight"):
        AdapterRegister(declared=False, weight=0.0)


def test_check_has_no_skip_parameter():
    """Reads the signature rather than trusting the docstring."""
    import inspect

    params = set(inspect.signature(check_register_scan).parameters)
    forbidden = {"skip", "force", "ignore", "warn_only", "soft", "disable", "enabled"}
    assert not (params & forbidden), f"check exposes a skip-shaped parameter: {params & forbidden}"
