"""`preflight()` — the aggregator. One call, every registered check, one structured result.

This is the function the adoption contract names. **Call it in-process on the submit path.**

    from comfy_preflight import preflight

    preflight(graph, register, input_dims=(1072, 1024))   # raises PreflightHalt
    submit(graph)                                         # only reached if nothing raised

## There is exactly one entry point, and that is the design

A second, non-raising `preflight_report()` for the CLI and the MCP to call would be a skip flag
under another name: a caller on the submit path could reach for it and get a value back where
the gate should have stopped them. So `preflight()` raises on HALT and the **halt carries the
whole report** (`PreflightHalt.report`). The renderers catch it and print; the submit path lets
it propagate. Nothing in this module takes a `skip`, `force`, `warn_only` or `enabled`
parameter, and a test reads the signature rather than trusting this paragraph.

## What the optional parameters are, and what they are not

Every optional parameter is an **askability** parameter, in the shape Amendment 1 ruled for
check 5: supplying it makes a clause askable; omitting it makes the check decline and name what
it could not see. None of them turns a firing check off. A run with none of them supplied still
runs checks 1, 5 and 8 in full, and reports precisely which clauses it could not ask.

## The merge

`HALT > ADVISORY > NOT_APPLICABLE > PASS`, per Amendment 2. The rung that surprises people is
NOT_APPLICABLE outranking PASS, and it is deliberate: a run where one check declined has not
checked everything, and reporting PASS would let the declined clause vanish behind the passing
ones. On the recorded corpus, a run with no input dimensions and no saved sidecar aggregates to
NOT_APPLICABLE — which is the honest headline for a run where two checks could not be asked.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from typing import Any

from comfy_preflight.checks.c1_link_topology import NodeSchema
from comfy_preflight.envelope import ENVELOPE, EnvelopeTable
from comfy_preflight.errors import Defect, PreflightHalt, Verdict, merge_verdicts
from comfy_preflight.graph import Graph
from comfy_preflight.register import AdapterRegister
from comfy_preflight.registry import (
    NOT_REGISTERED,
    REGISTRY,
    CheckInputs,
    CheckOutcome,
    RegisteredCheck,
)

AGGREGATE_NAME = "preflight"


@dataclasses.dataclass(frozen=True)
class PreflightResult:
    """Every registered check's outcome, plus the merged verdict.

    `checks_run` and `checks_not_registered` are carried so the report can answer *what did you
    actually check* without the reader inferring it. A report that cannot enumerate its own
    coverage makes a check silently dropping out look exactly like a check that passed.
    """

    verdict: Verdict
    outcomes: tuple[CheckOutcome, ...]
    checks_run: tuple[int, ...]
    checks_not_registered: tuple[tuple[int, str], ...]

    @property
    def defects(self) -> tuple[Defect, ...]:
        """Every halting defect, from every check, in registry order."""
        return tuple(
            d
            for outcome in self.outcomes
            if outcome.verdict is Verdict.HALT
            for d in outcome.defects
        )

    @property
    def advisories(self) -> tuple[Defect, ...]:
        """Every non-halting finding. These are facts to see, not grounds to stop."""
        return tuple(
            d
            for outcome in self.outcomes
            if outcome.verdict is Verdict.ADVISORY
            for d in outcome.defects
        )

    @property
    def declined(self) -> tuple[tuple[str, str, str], ...]:
        """Every clause no check could ask, as (check_id, clause, why)."""
        return tuple(
            (outcome.check_id, clause, why)
            for outcome in self.outcomes
            for clause, why in outcome.clauses_declined
        )

    def outcome_for(self, number: int) -> CheckOutcome | None:
        return next((o for o in self.outcomes if o.number == number), None)

    def to_dict(self) -> dict[str, Any]:
        """A JSON-safe rendering, for the CLI's `--json` and for the MCP tool's return value.

        The MCP returns this **verbatim**. It is a transport over the same in-process function,
        not a second implementation with its own opinion about what matters.
        """
        return {
            "verdict": self.verdict.value,
            "checks_run": list(self.checks_run),
            "checks_not_registered": [
                {"check": number, "reason": reason}
                for number, reason in self.checks_not_registered
            ],
            "checks": [
                {
                    "check": outcome.number,
                    "id": outcome.check_id,
                    "title": outcome.title,
                    "verdict": outcome.verdict.value,
                    "clauses_evaluated": list(outcome.clauses_evaluated),
                    "clauses_declined": [
                        {"clause": clause, "why": why}
                        for clause, why in outcome.clauses_declined
                    ],
                    "findings": [_defect_dict(d) for d in outcome.defects],
                    "notes": list(outcome.notes),
                }
                for outcome in self.outcomes
            ],
        }


def _defect_dict(defect: Defect) -> dict[str, Any]:
    return {
        "code": defect.code,
        "message": defect.message,
        "hint": defect.hint,
        "node_id": defect.node_id,
        "input_name": defect.input_name,
    }


def preflight(
    graph: Graph,
    register_profile: AdapterRegister | None,
    input_dims: tuple[int, int] | None = None,
    *,
    saved_graph: Graph | None = None,
    schema: NodeSchema | None = None,
    consumer_input: tuple[str, str] | None = None,
    family: str = "qwen",
    envelope_table: EnvelopeTable = ENVELOPE,
    checks: Sequence[RegisteredCheck] = REGISTRY,
) -> PreflightResult:
    """Run every registered check and merge their verdicts.

    `register_profile` is **required and may be None** — deliberately not defaulted. The
    signature is Amendment 2's, and the shape earns itself: passing `None` is a caller stating
    that it has no subject profile, which check 2 then reports as a declined clause. A default
    would let the same situation arrive by omission, and the difference between "I have no
    profile" and "I forgot the profile" is exactly what this repo's declined clauses exist to
    keep visible.

    Raises `PreflightHalt` if the merged verdict is HALT, carrying **every defect from every
    check** — not just the first check's — with the full `PreflightResult` attached as
    `.report`. Returns the result otherwise.

    ADVISORY and NOT_APPLICABLE do not raise. An advisory that stopped a submission would be a
    halt wearing a softer name, and the studio ran an out-of-band value deliberately.

    There is no skip parameter. `checks` exists so a caller can supply an extended registry;
    it cannot be used to disable a check without the caller constructing a different registry,
    which is an explicit act in the caller's own code rather than a flag at the call site.
    """
    inputs = CheckInputs(
        graph=graph,
        register=register_profile,
        input_dims=input_dims,
        saved_graph=saved_graph,
        schema=schema,
        consumer_input=consumer_input,
        family=family,
        envelope_table=envelope_table,
    )

    outcomes = tuple(spec.run(inputs) for spec in checks)
    result = PreflightResult(
        verdict=merge_verdicts([o.verdict for o in outcomes]),
        outcomes=outcomes,
        checks_run=tuple(o.number for o in outcomes),
        checks_not_registered=tuple(sorted(NOT_REGISTERED.items())),
    )

    if result.verdict is Verdict.HALT:
        # One raise, carrying everything. A caller fixing defects one rerun at a time is a
        # caller running a gate five times before an act it was meant to gate once.
        raise PreflightHalt(AGGREGATE_NAME, list(result.defects), report=result)
    return result
