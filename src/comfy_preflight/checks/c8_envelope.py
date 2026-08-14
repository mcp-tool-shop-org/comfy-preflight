"""Check 8 — the declared-envelope advisory. It advises; it never halts.

For each checkpoint the graph loads, compare the graph's parameter values against a **cited**
envelope table. Out of band is an ADVISORY quoting the value, the band and the citation. No
entry for the checkpoint is NOT_APPLICABLE **naming the checkpoint it could not see**.

## Provenance

Measured (E33→E35): a performer's twins were generated at img2img denoise 0.92 through a
control checkpoint, and nothing on the submit path said whether that sat inside or outside the
checkpoint's documented operating range. The speck class that followed cost an acceptance, a
consult, a five-agent research swarm and a repair arc. The fact was knowable at submit time.

## Why it is an advisory, and why that is a ruling rather than a softness

The studio ran 0.92 deliberately and the Director approved the register produced at it. A
documented band is documentation, not a gate. A check that halted on it would refuse correct
work, and a gate that halts correct work gets disabled by the third person who hits it — check
3's exclusion law arriving at check 8. **This check never raises `PreflightHalt`, and a test
runs it over every recorded graph and over deliberately out-of-band mutations to prove it.**

## What it reports when it cannot judge

An entry may declare a parameter its card is known **not** to document. For those the check
reads the graph's value, reports it, and says plainly that it cannot judge it and why. That
is the whole point of the day-one entry: the recorded 0.92 is surfaced at the moment it is
cheap, and no band is invented to surface it. See `envelope.py` for what the live card was
measured to contain, which is not what the research grounding attributed to it.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping

from comfy_preflight.envelope import (
    CHECKPOINT_INPUT_NAMES,
    ENVELOPE,
    Band,
    EnvelopeEntry,
    basename,
)
from comfy_preflight.errors import Defect, Verdict
from comfy_preflight.graph import Graph

CHECK_NAME = "check_8_declared_envelope"


@dataclasses.dataclass(frozen=True)
class LoadedCheckpoint:
    """One checkpoint reference found in the graph, located."""

    node_id: str
    input_name: str
    value: str


@dataclasses.dataclass(frozen=True)
class CheckResult:
    verdict: Verdict
    clauses_evaluated: tuple[str, ...]
    clauses_declined: tuple[tuple[str, str], ...]
    findings: tuple[Defect, ...]
    checkpoints_found: tuple[str, ...]
    checkpoints_covered: tuple[str, ...]
    checkpoints_not_in_table: tuple[str, ...]
    parameters_checked: tuple[tuple[str, str, float], ...]  # (node_id, parameter, value)
    notes: tuple[str, ...] = ()


def loaded_checkpoints(graph: Graph) -> list[LoadedCheckpoint]:
    """Every checkpoint-bearing literal in the graph, as (node, input, value)."""
    found: list[LoadedCheckpoint] = []
    for node_id, input_name, value in graph.literals():
        if input_name in CHECKPOINT_INPUT_NAMES and isinstance(value, str) and value:
            found.append(LoadedCheckpoint(node_id=node_id, input_name=input_name, value=value))
    return found


def _numeric(value: object) -> float | None:
    if isinstance(value, bool):  # bool is an int subclass; a strength is not a bool
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def check_declared_envelope(
    graph: Graph,
    *,
    table: Mapping[str, EnvelopeEntry] = ENVELOPE,
) -> CheckResult:
    """Run check 8. Always returns a CheckResult; **never raises PreflightHalt**.

    There is no skip parameter. `table` is the envelope table, injected so a caller can extend
    it — every entry it contains is validated by `EnvelopeEntry`'s own constructor, which
    refuses an uncited row.
    """
    evaluated: list[str] = []
    declined: list[tuple[str, str]] = []
    findings: list[Defect] = []
    notes: list[str] = []
    checked: list[tuple[str, str, float]] = []

    found = loaded_checkpoints(graph)
    if not found:
        declined.append(
            (
                "envelope_bands",
                "the graph loads no named checkpoint on any of "
                f"{sorted(CHECKPOINT_INPUT_NAMES)}, so there is nothing to resolve against an "
                "envelope. This check reads declared knowledge about a checkpoint; with no "
                "checkpoint named it has no subject",
            )
        )
        return CheckResult(
            verdict=Verdict.NOT_APPLICABLE,
            clauses_evaluated=(),
            clauses_declined=tuple(declined),
            findings=(),
            checkpoints_found=(),
            checkpoints_covered=(),
            checkpoints_not_in_table=(),
            parameters_checked=(),
        )

    covered: list[tuple[LoadedCheckpoint, EnvelopeEntry]] = []
    uncovered: list[LoadedCheckpoint] = []
    for loaded in found:
        entry = table.get(basename(loaded.value).lower())
        if entry is None:
            uncovered.append(loaded)
        else:
            covered.append((loaded, entry))

    if uncovered:
        names = sorted({basename(c.value) for c in uncovered})
        declined.append(
            (
                "envelope_bands",
                # Naming the checkpoint it could not see is the whole shape of this refusal.
                f"no envelope entry for {names}. The table ships only entries verified against "
                "a live model card, so an absent checkpoint means its operating range was not "
                "read - not that its parameters are in range. Add an entry with its parameter, "
                "band, source URL and retrieval date",
            )
        )

    if not covered:
        return CheckResult(
            verdict=Verdict.NOT_APPLICABLE,
            clauses_evaluated=(),
            clauses_declined=tuple(declined),
            findings=(),
            checkpoints_found=tuple(sorted({basename(c.value) for c in found})),
            checkpoints_covered=(),
            checkpoints_not_in_table=tuple(sorted({basename(c.value) for c in uncovered})),
            parameters_checked=(),
        )

    evaluated.append("envelope_bands")

    for loaded, entry in covered:
        # The entry renders its own authority, because a vendor citation and a studio measurement
        # are different things and a finding must not blur them into "the source says".
        citation = entry.citation

        # -- the bands the card DOES document --------------------------------------
        for band in entry.bands:
            operands = _resolve_band_operands(graph, loaded, band)
            if not operands:
                where = "reading from" if band.linked else "of class"
                declined.append(
                    (
                        f"envelope_bands.{band.parameter}",
                        f"{entry.checkpoint} declares a band for {band.parameter!r} on "
                        f"{sorted(band.node_classes)}, but the graph has no such node {where} "
                        f"node {loaded.node_id} carrying that input. The band was not applied to "
                        "anything rather than applied to a guess",
                    )
                )
                continue
            for node_id, value in operands:
                checked.append((node_id, band.parameter, value))
                if band.contains(value):
                    continue
                findings.append(
                    Defect(
                        code="PARAMETER_OUTSIDE_DECLARED_ENVELOPE",
                        message=(
                            f"{band.parameter} is {value:g}, outside the band "
                            f"[{band.low:g}, {band.high:g}] documented for "
                            f"{entry.checkpoint}. The card says: {band.quote}. "
                            f"Source: {citation}"
                        ),
                        hint=(
                            "ADVISORY, not a halt - a documented band is documentation and "
                            "running outside it may be exactly what was intended. This exists "
                            "so the fact is visible before the credits are spent rather than "
                            "after the output is judged. If it is intended, proceed"
                        ),
                        node_id=node_id,
                        input_name=band.parameter,
                    )
                )

        # -- the parameters the card is known NOT to document ----------------------
        for absence in entry.documented_absent:
            operands = _nodes_of_classes(graph, absence.node_classes, absence.parameter)
            if not operands:
                declined.append(
                    (
                        f"envelope_bands.{absence.parameter}",
                        f"{entry.checkpoint}'s card documents no band for "
                        f"{absence.parameter!r}, and the graph carries no "
                        f"{sorted(absence.node_classes)} node with that input either. "
                        f"{absence.reason}",
                    )
                )
                continue
            values = ", ".join(f"node {nid} = {val:g}" for nid, val in operands)
            declined.append(
                (
                    f"envelope_bands.{absence.parameter}",
                    # Report the value it cannot judge. That is the honest half of the finding;
                    # inventing a band to judge it against would be the dishonest half.
                    f"this graph runs {absence.parameter} at {values}, and this check CANNOT "
                    f"say whether that is in or out of band for {entry.checkpoint}: "
                    f"{absence.reason}. Source consulted: {citation}",
                )
            )

        notes.extend(entry.notes)

    # Findings are advisory by construction: this check has no raise path at all.
    verdict = Verdict.ADVISORY if findings else Verdict.PASS
    return CheckResult(
        verdict=verdict,
        clauses_evaluated=tuple(evaluated),
        clauses_declined=tuple(declined),
        findings=tuple(findings),
        checkpoints_found=tuple(sorted({basename(c.value) for c in found})),
        checkpoints_covered=tuple(sorted({basename(c.value) for c, _ in covered})),
        checkpoints_not_in_table=tuple(sorted({basename(c.value) for c in uncovered})),
        parameters_checked=tuple(checked),
        notes=tuple(notes),
    )


def _resolve_band_operands(
    graph: Graph, loaded: LoadedCheckpoint, band: Band
) -> list[tuple[str, float]]:
    """Find the nodes carrying this band's parameter, tied to THIS checkpoint where linked.

    Linked resolution follows the graph's wires from the loader node that named the checkpoint,
    so a graph carrying two control checkpoints does not have one entry's band applied to the
    other's apply node. Unlinked resolution falls back to class lookup across the graph.
    """
    if not band.linked:
        return _nodes_of_classes(graph, band.node_classes, band.parameter)

    out: list[tuple[str, float]] = []
    for link in graph.consumers_of(loaded.node_id):
        node = graph.get(link.node_id)
        if node is None or node.class_type not in band.node_classes:
            continue
        value = _numeric(node.inputs.get(band.parameter))
        if value is not None and all(nid != node.node_id for nid, _ in out):
            out.append((node.node_id, value))
    return sorted(out)


def _nodes_of_classes(
    graph: Graph, classes: frozenset[str], parameter: str
) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    for node in graph.nodes_of_class(*sorted(classes)):
        value = _numeric(node.inputs.get(parameter))
        if value is not None:
            out.append((node.node_id, value))
    return sorted(out)
