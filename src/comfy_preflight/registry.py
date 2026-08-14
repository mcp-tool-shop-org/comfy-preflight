"""The check registry — the aggregator's composition surface.

`preflight()` runs **whatever is registered here**, in order. It does not carry a hardcoded
list of five calls, and the difference is not tidiness:

- **A hardcoded list makes "which checks ran" unanswerable from the result.** A report that
  cannot enumerate its own coverage is one where a check silently dropping out of the
  aggregator looks exactly like a check that passed.
- **Check 8 landed through this surface as the proof it extends.** It was specified after the
  aggregator was, and adding it required one `RegisteredCheck` and one adapter — no edit to
  `preflight()` at all.

## Why each check needs an adapter rather than a common signature

The checks decompose by what they know, and their signatures say so: 1, 4 and 5 are
graph-structural and know nothing about subjects; 2 and 8 resolve against declared knowledge;
4 needs a *pair* of graphs. Forcing one signature on all of them would push every check's
requirements into every other check's argument list, which is exactly the coupling
decompose-by-secrets exists to prevent. So the registry defines the uniform call and each
adapter knows one check's real signature. The seam is here, in one file, rather than smeared.

## Why an adapter catches the halt

Checks raise. An aggregator that let the first raise propagate would report one check's defects
and never run the rest — the fix-one, rerun, find-the-next treadmill, on a gate whose whole job
is to be run once before an irreversible act. So each adapter catches its own check's
`PreflightHalt`, records it as a HALT outcome, and the aggregator re-raises **once** with
everything. The gate still fires; it fires with the whole picture.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping
from typing import Any

from comfy_preflight.checks.c1_link_topology import NodeSchema, check_link_topology
from comfy_preflight.checks.c2_register import check_register_scan
from comfy_preflight.checks.c4_saved_is_submitted import check_saved_is_submitted
from comfy_preflight.checks.c5_frame import check_generator_legal_frame
from comfy_preflight.checks.c8_envelope import check_declared_envelope
from comfy_preflight.envelope import ENVELOPE, EnvelopeEntry
from comfy_preflight.errors import Defect, PreflightHalt, Verdict
from comfy_preflight.graph import Graph
from comfy_preflight.register import AdapterRegister


@dataclasses.dataclass(frozen=True)
class CheckInputs:
    """Everything any registered check might need, gathered once.

    The optional fields are **the askability parameters**, and every one of them follows the
    rule Amendment 1 set for check 5: supplying it makes a clause askable, and omitting it makes
    the check decline and name what it could not see. None of them is a skip flag — omitting one
    never turns a firing check off, it turns a clause into a stated blind spot.
    """

    graph: Graph
    register: AdapterRegister | None = None
    input_dims: tuple[int, int] | None = None
    saved_graph: Graph | None = None
    schema: NodeSchema | None = None
    consumer_input: tuple[str, str] | None = None
    family: str = "qwen"
    envelope_table: Mapping[str, EnvelopeEntry] = dataclasses.field(default_factory=lambda: ENVELOPE)


@dataclasses.dataclass(frozen=True)
class CheckOutcome:
    """One check's result, in the uniform shape the aggregator merges.

    `detail` is the check's own `CheckResult`, carried verbatim so nothing a check measured is
    lost in translation. It is `None` when the check halted: a check that raised never returned
    its clause accounting, and inventing an empty one would report "no clauses evaluated" for a
    check that evaluated enough to find a defect.
    """

    check_id: str
    number: int
    title: str
    verdict: Verdict
    defects: tuple[Defect, ...] = ()
    clauses_evaluated: tuple[str, ...] = ()
    clauses_declined: tuple[tuple[str, str], ...] = ()
    notes: tuple[str, ...] = ()
    detail: Any = None


@dataclasses.dataclass(frozen=True)
class RegisteredCheck:
    """One check's place in the composition surface.

    `run` catches this check's own `PreflightHalt` and converts it to a HALT outcome, so one
    check halting never denies the caller the other four checks' findings. The gate is not
    weakened by that — the aggregator re-raises once, carrying everything.
    """

    check_id: str
    number: int
    title: str
    call: Callable[["RegisteredCheck", CheckInputs], CheckOutcome]

    def run(self, inputs: CheckInputs) -> CheckOutcome:
        try:
            return self.call(self, inputs)
        except PreflightHalt as halt:
            return _from_halt(self, halt)


def _from_result(spec: "RegisteredCheck", result: Any) -> CheckOutcome:
    """Wrap a check's own CheckResult in the uniform outcome shape."""
    return CheckOutcome(
        check_id=spec.check_id,
        number=spec.number,
        title=spec.title,
        verdict=result.verdict,
        # Check 8 reports advisories as `findings` rather than raising them; every other check
        # returns none, because their non-halting findings do not exist.
        defects=tuple(getattr(result, "findings", ())),
        clauses_evaluated=tuple(result.clauses_evaluated),
        clauses_declined=tuple(result.clauses_declined),
        notes=tuple(getattr(result, "notes", ())),
        detail=result,
    )


def _from_halt(spec: "RegisteredCheck", halt: PreflightHalt) -> CheckOutcome:
    return CheckOutcome(
        check_id=spec.check_id,
        number=spec.number,
        title=spec.title,
        verdict=Verdict.HALT,
        defects=tuple(halt.defects),
    )


def _declined(spec: "RegisteredCheck", clause: str, why: str) -> CheckOutcome:
    """A check the caller did not supply the operand for. NOT_APPLICABLE, naming what it needs."""
    return CheckOutcome(
        check_id=spec.check_id,
        number=spec.number,
        title=spec.title,
        verdict=Verdict.NOT_APPLICABLE,
        clauses_declined=((clause, why),),
    )


# ---- the adapters. Each knows exactly one check's real signature. -------------------------


def _c1(spec: RegisteredCheck, inputs: CheckInputs) -> CheckOutcome:
    """Check 1 is graph-structural: it needs nothing but the graph, and declines its third
    clause on its own when no node schema is supplied."""
    return _from_result(spec, check_link_topology(inputs.graph, schema=inputs.schema))


def _c2(spec: RegisteredCheck, inputs: CheckInputs) -> CheckOutcome:
    if inputs.register is None:
        return _declined(
            spec,
            "register_scan",
            "no register profile was supplied, so 'does the declared register match the "
            "graph's actual construction' is not askable. The register is this gate's "
            "reference and it comes from the subject's profile - taking it from the graph "
            "being checked would make the check a tautology",
        )
    return _from_result(
        spec,
        check_register_scan(inputs.graph, inputs.register, consumer_input=inputs.consumer_input),
    )


def _c4(spec: RegisteredCheck, inputs: CheckInputs) -> CheckOutcome:
    if inputs.saved_graph is None:
        return _declined(
            spec,
            "saved_is_submitted",
            "no saved sidecar graph was supplied, so 'did a value move between save and "
            "submit' is not askable. Save the exact JSON before submission and pass it as "
            "saved_graph; this check compares the two as parsed graphs, never as text",
        )
    return _from_result(spec, check_saved_is_submitted(inputs.saved_graph, inputs.graph))


def _c5(spec: RegisteredCheck, inputs: CheckInputs) -> CheckOutcome:
    return _from_result(
        spec,
        check_generator_legal_frame(
            inputs.graph, family=inputs.family, input_dimensions=inputs.input_dims
        ),
    )


def _c8(spec: RegisteredCheck, inputs: CheckInputs) -> CheckOutcome:
    return _from_result(spec, check_declared_envelope(inputs.graph, table=inputs.envelope_table))


REGISTRY: tuple[RegisteredCheck, ...] = (
    RegisteredCheck("check_1_link_topology", 1, "Link topology", _c1),
    RegisteredCheck("check_2_inverted_register_scan", 2, "Inverted register scan", _c2),
    RegisteredCheck("check_4_saved_is_graph_submitted", 4, "Graph-saved-is-graph-submitted", _c4),
    RegisteredCheck("check_5_generator_legal_frame", 5, "Generator-legal frame", _c5),
    # Check 8 was specified after the aggregator was, and landing it took exactly this line plus
    # its adapter above. No edit to `preflight()` — which is the proof the surface extends.
    RegisteredCheck("check_8_declared_envelope", 8, "Declared-envelope advisory", _c8),
)

# The spec's table lists seven checks; three are deliberately out of this registry, and naming
# them here keeps the boundary visible in the code rather than only in the README.
#
#   3 — recipe-vs-profile agreement: no subject-profile fixture exists in this repo, and
#       constructing one from the graphs it would check reproduces the tautology problem.
#   6 — estimate before submit: transport-side by the spec's own decomposition; it has no
#       graph-structural operand at all.
#   7 — anchor reproduction: needs the graph BUILDER, and the corpus holds outputs rather than
#       the scripts that made them. Whether a builder is reachable is unresolved.
# ASCII only, like every other runtime-emitted string in this package: these reach a Windows
# console, where a cp1252 encoder renders an em dash as a replacement character. Prose in
# docstrings and comments is free to use them; anything a user sees printed is not.
NOT_REGISTERED: dict[int, str] = {
    3: "recipe-vs-profile agreement - no subject-profile fixture in this repo",
    6: "estimate before submit - transport-side; no graph-structural operand",
    7: "anchor reproduction - needs the builder; the corpus holds outputs, not builders",
}


def registered_numbers() -> tuple[int, ...]:
    return tuple(spec.number for spec in REGISTRY)
