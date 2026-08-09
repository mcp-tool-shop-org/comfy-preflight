"""Check 2 — the inverted register scan. Both directions.

When a subject's register declares **no style adapter**, the claim being asserted is *not*
"the weight is 0.0". It is that **no loader node and no adapter card reference exist anywhere
in the graph** — asserted by walking every node and every input, plus the link assertion that
the downstream consumer reads directly from the base model.

    A weight of 0.0 is not a weight of zero on a loaded card; it is no card.

**And the mirror image halts too.** A decided positive weight with no loader node is *silently
inert*: the run completes, costs money, and produces base-model output while every log line
says the adapter was requested. That direction produces no signal a human could notice, which
is exactly where a gate earns its place over a person looking.

## Why the result reports its clauses

Three clauses are evaluated, and one of them is not always askable:

| clause | needs | askable when |
|---|---|---|
| `loader_nodes` | nothing — structural | always |
| `consumer_link` | a named consumer input | when the consumer is resolvable |
| `card_vocabulary` | the register's declared card vocabulary | only when `known_cards`/`card` is non-empty |

A check that quietly skips a clause it could not evaluate reports PASS for work it never did.
So `CheckResult` names every clause it evaluated and every one it declined, and the caller can
see the difference. Measured reason this matters: scanning for "any `.safetensors` string"
instead of a declared vocabulary matches the base model, CLIP, VAE and ControlNet on all 70
recorded graphs — including all 43 with no adapter — so the naive form of the vocabulary clause
fires on every correct build.
"""

from __future__ import annotations

import dataclasses

from comfy_preflight.errors import Defect, PreflightHalt, Verdict
from comfy_preflight.graph import Graph, Node
from comfy_preflight.register import (
    CARD_INPUT_NAMES,
    SUSPECTED_LOADER_SUBSTRING,
    WEIGHT_INPUT_NAMES,
    AdapterRegister,
)

CHECK_NAME = "check_2_inverted_register_scan"


@dataclasses.dataclass(frozen=True)
class CheckResult:
    verdict: Verdict
    clauses_evaluated: tuple[str, ...]
    clauses_declined: tuple[tuple[str, str], ...]  # (clause, why)
    loader_nodes: tuple[str, ...]
    card_references: tuple[tuple[str, str, str], ...]  # (node_id, input_name, value)
    notes: tuple[str, ...] = ()


def _find_loaders(graph: Graph, register: AdapterRegister) -> tuple[list[Node], list[Node]]:
    """Return (declared-class loaders, suspected loaders not in the declared classes).

    An unrecognised class that names itself an adapter loader is reported separately rather
    than ignored: it does not satisfy a positive declaration and it does not pass a negative
    one. A gate that fails open on an unknown node is not a gate.
    """
    declared: list[Node] = []
    suspected: list[Node] = []
    for node in graph.nodes.values():
        if node.class_type in register.loader_classes:
            declared.append(node)
            continue
        low = node.class_type.lower()
        if any(token in low for token in SUSPECTED_LOADER_SUBSTRING):
            suspected.append(node)
    return declared, suspected


def _find_card_references(
    graph: Graph, register: AdapterRegister
) -> list[tuple[str, str, str]]:
    """Every input whose literal value names a card in the register's vocabulary.

    Matching is against the declared vocabulary, NOT against a filename extension. Comparison
    is case-insensitive on the basename so a path-prefixed or re-cased reference is still
    found.
    """
    vocab = {c.lower() for c in register.vocabulary}
    if not vocab:
        return []
    hits: list[tuple[str, str, str]] = []
    for node_id, input_name, value in graph.literals():
        if not isinstance(value, str) or not value:
            continue
        candidate = value.replace("\\", "/").rsplit("/", 1)[-1].lower()
        if candidate in vocab or value.lower() in vocab:
            hits.append((node_id, input_name, value))
    return hits


def _weight_of(node: Node) -> float | None:
    for name in WEIGHT_INPUT_NAMES:
        value = node.inputs.get(name)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return None


def _card_of(node: Node) -> str | None:
    for name, value in node.literals():
        if name in CARD_INPUT_NAMES and isinstance(value, str):
            return value
    return None


def check_register_scan(
    graph: Graph,
    register: AdapterRegister,
    *,
    consumer_input: tuple[str, str] | None = None,
    base_model_classes: frozenset[str] = frozenset({"UNETLoader", "CheckpointLoaderSimple"}),
) -> CheckResult:
    """Run check 2. Returns a CheckResult on PASS; raises PreflightHalt on a defect.

    There is no skip parameter and adding one would defeat the check. `consumer_input` names the
    `(node_id, input_name)` that should read from the base model when no adapter is declared —
    e.g. `("6", "model")`. When omitted, the consumer clause is declined rather than guessed.
    """
    defects: list[Defect] = []
    evaluated: list[str] = []
    declined: list[tuple[str, str]] = []
    notes: list[str] = []

    declared_loaders, suspected_loaders = _find_loaders(graph, register)
    all_loaders = declared_loaders + suspected_loaders
    evaluated.append("loader_nodes")

    for node in suspected_loaders:
        notes.append(
            f"node {node.node_id} class '{node.class_type}' is not a declared loader class "
            f"but names itself one; treated as a loader"
        )

    # -- the card-vocabulary clause, askable only with a declared vocabulary ----
    if register.vocabulary:
        card_refs = _find_card_references(graph, register)
        evaluated.append("card_vocabulary")
    else:
        card_refs = []
        declined.append(
            (
                "card_vocabulary",
                "the register declares no card vocabulary (known_cards is empty), so "
                "'no card reference anywhere' is not askable. Scanning for any "
                "'.safetensors' string instead would match the base model, CLIP, VAE and "
                "ControlNet on every graph",
            )
        )

    if register.declared:
        # ---- DIRECTION 1: an adapter IS declared. The failure is silent inertness. ----
        if not all_loaders:
            defects.append(
                Defect(
                    code="ADAPTER_DECLARED_BUT_NO_LOADER",
                    message=(
                        f"the register declares card {register.card!r} at weight "
                        f"{register.weight}, but the graph contains no adapter loader node. "
                        "The run would complete, spend credits, and produce base-model output "
                        "while every log line says the adapter was requested."
                    ),
                    hint=(
                        "insert the loader and route the downstream consumer through it, or "
                        "change the register to declared=False if base-model output is what "
                        "was intended"
                    ),
                )
            )
        else:
            for node in all_loaders:
                actual_card = _card_of(node)
                if actual_card is None:
                    defects.append(
                        Defect(
                            code="LOADER_WITHOUT_CARD",
                            message=f"loader node has no card input among {sorted(CARD_INPUT_NAMES)}",
                            hint="a loader with no named card cannot be checked against the register",
                            node_id=node.node_id,
                        )
                    )
                    continue
                if not _card_is_acceptable(actual_card, register):
                    acceptable = sorted(register.acceptable_cards)
                    defects.append(
                        Defect(
                            code="ADAPTER_CARD_MISMATCH",
                            message=(
                                f"graph loads {actual_card!r}; the register accepts {acceptable}"
                            ),
                            hint=(
                                "align the graph with the profile, or correct the profile. If "
                                "this is the same adapter re-imported under a different "
                                "namespace, declare the other name in the register's "
                                "card_aliases rather than loosening the comparison"
                            ),
                            node_id=node.node_id,
                            input_name=_card_input_name(node),
                        )
                    )
                actual_weight = _weight_of(node)
                if actual_weight is None:
                    defects.append(
                        Defect(
                            code="LOADER_WITHOUT_WEIGHT",
                            message=f"loader node declares no weight among {list(WEIGHT_INPUT_NAMES)}",
                            hint="a loader with no readable strength cannot be checked",
                            node_id=node.node_id,
                        )
                    )
                elif actual_weight <= 0:
                    defects.append(
                        Defect(
                            code="ADAPTER_LOADED_AT_ZERO_WEIGHT",
                            message=(
                                f"card is loaded but at weight {actual_weight}; the register "
                                f"declares {register.weight}. A loaded card at zero weight is "
                                "the inverse of the no-adapter condition and is not it"
                            ),
                            hint="set the declared weight, or remove the loader entirely",
                            node_id=node.node_id,
                        )
                    )
                elif register.weight is not None and abs(actual_weight - register.weight) > 1e-9:
                    defects.append(
                        Defect(
                            code="ADAPTER_WEIGHT_MISMATCH",
                            message=f"graph loads at {actual_weight}; register declares {register.weight}",
                            hint="align the graph with the profile, or correct the profile",
                            node_id=node.node_id,
                        )
                    )
    else:
        # ---- DIRECTION 2: NO adapter is declared. The claim is absence. ----
        for node in all_loaders:
            defects.append(
                Defect(
                    code="ADAPTER_LOADER_PRESENT_BUT_NOT_DECLARED",
                    message=(
                        f"the register declares no style adapter, but node {node.node_id} is an "
                        f"adapter loader ({node.class_type}). The claim being asserted is that "
                        "no loader node exists - not that its weight is 0.0"
                    ),
                    hint="remove the loader node and route the consumer directly from the base "
                    "model, or declare the adapter in the register",
                    node_id=node.node_id,
                )
            )
        for node_id, input_name, value in card_refs:
            defects.append(
                Defect(
                    code="ADAPTER_CARD_REFERENCED_BUT_NOT_DECLARED",
                    message=(
                        f"the register declares no style adapter, but this input references the "
                        f"known card {value!r}"
                    ),
                    hint="remove the reference, or declare the adapter in the register",
                    node_id=node_id,
                    input_name=input_name,
                )
            )

    # -- the consumer-link clause ----------------------------------------------
    if consumer_input is None:
        declined.append(
            (
                "consumer_link",
                "no consumer_input was named, so 'the consumer reads directly from the base "
                "model' is not askable. Guessing which node is the consumer would make the "
                "clause depend on graph shape rather than on the register",
            )
        )
    else:
        consumer_id, consumer_name = consumer_input
        node = graph.get(consumer_id)
        if node is None:
            defects.append(
                Defect(
                    code="CONSUMER_NODE_ABSENT",
                    message=f"named consumer node {consumer_id!r} is not in the graph",
                    hint="check the consumer_input the caller passed against the graph",
                    node_id=consumer_id,
                )
            )
        else:
            link = next((ln for ln in node.links() if ln.input_name == consumer_name), None)
            if link is None:
                defects.append(
                    Defect(
                        code="CONSUMER_INPUT_NOT_A_LINK",
                        message=f"{consumer_id}.{consumer_name} is not a link to another node",
                        hint="the consumer must read its model from a producing node",
                        node_id=consumer_id,
                        input_name=consumer_name,
                    )
                )
            else:
                evaluated.append("consumer_link")
                source = graph.get(link.source_id)
                source_class = source.class_type if source else "<absent>"
                loader_ids = {n.node_id for n in all_loaders}
                if register.declared:
                    if link.source_id not in loader_ids:
                        defects.append(
                            Defect(
                                code="CONSUMER_BYPASSES_DECLARED_ADAPTER",
                                message=(
                                    f"an adapter is declared and a loader exists, but "
                                    f"{consumer_id}.{consumer_name} reads from node "
                                    f"{link.source_id} ({source_class}) rather than through the "
                                    "loader - the card is loaded and unused"
                                ),
                                hint="route the consumer through the loader node",
                                node_id=consumer_id,
                                input_name=consumer_name,
                            )
                        )
                else:
                    if link.source_id in loader_ids:
                        defects.append(
                            Defect(
                                code="CONSUMER_READS_THROUGH_LOADER",
                                message=(
                                    f"no adapter is declared, but {consumer_id}.{consumer_name} "
                                    f"reads from adapter loader node {link.source_id}"
                                ),
                                hint="route the consumer directly from the base model",
                                node_id=consumer_id,
                                input_name=consumer_name,
                            )
                        )
                    elif source_class not in base_model_classes:
                        defects.append(
                            Defect(
                                code="CONSUMER_NOT_ON_BASE_MODEL",
                                message=(
                                    f"no adapter is declared, so {consumer_id}.{consumer_name} "
                                    f"should read from a base model "
                                    f"{sorted(base_model_classes)}, but it reads node "
                                    f"{link.source_id} ({source_class})"
                                ),
                                hint="route the consumer directly from the base model, or pass "
                                "base_model_classes if this graph's base loader differs",
                                node_id=consumer_id,
                                input_name=consumer_name,
                            )
                        )

    if defects:
        raise PreflightHalt(CHECK_NAME, defects)

    return CheckResult(
        verdict=Verdict.PASS if evaluated else Verdict.NOT_APPLICABLE,
        clauses_evaluated=tuple(evaluated),
        clauses_declined=tuple(declined),
        loader_nodes=tuple(sorted(n.node_id for n in all_loaders)),
        card_references=tuple(card_refs),
        notes=tuple(notes),
    )


def _card_input_name(node: Node) -> str | None:
    for name, value in node.literals():
        if name in CARD_INPUT_NAMES and isinstance(value, str):
            return name
    return None


def _basename(value: str) -> str:
    return value.replace("\\", "/").rsplit("/", 1)[-1]


def _card_is_acceptable(actual: str, register: AdapterRegister) -> bool:
    """Exact match against a DECLARED name or alias, compared on the basename only.

    Basename rather than full path, because a card may be referenced with or without a
    directory prefix. Nothing else is normalised: no prefix stripping, no substring matching,
    no fuzzy compare. An adapter re-imported under another namespace is declared as an alias,
    which keeps a genuinely wrong card from passing because its name shared a tail.
    """
    candidate = _basename(actual)
    return any(candidate == _basename(name) for name in register.acceptable_cards)
