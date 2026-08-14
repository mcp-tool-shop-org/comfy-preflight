"""Check 5 — generator-legal frame. Re-specified: the operand is the EFFECTIVE frame.

A Qwen VAE downsamples by 8. `1066 / 8 = 133.25` encodes to 133 latent columns and decodes to
**1064** — so every image came back 1064 wide against 1066-wide controls, and the pairing stage
was refused downstream.

## Why this check is not about graph literals

**The defect happened upstream of the graph.** The record is explicit that *"the 1066 was
derived correctly from the mesh"* — the frame was computed from a mesh bounding box, the image
was *rendered at that width and uploaded*, and the graph never declared 1066 anywhere. Across 70
recorded graphs there are zero `width`/`height`/`resolution`/`batch_size` inputs and no
`EmptyLatentImage` node: every one is img2img, and the frame arrives inside the uploaded image.

So a check that reads graph literals could not have caught the incident that motivates it. The
operand is the frame the run will actually produce:

| case | operand | verdict |
|---|---|---|
| the graph declares dimensions | the literals | PASS / HALT |
| img2img and the caller has the input | **the input image's dimensions** | PASS / HALT |
| neither | — | NOT_APPLICABLE, naming what it could not see |

`input_dimensions` is a **parameter, not an architecture**. The production gate runs in-process
on the submit path, where the image is in hand by construction; the standalone CLI degrades to
NOT_APPLICABLE. This package does not decode images — dimensions in, verdict out — so it grows
no image dependency to satisfy a check.

## The family table carries only what was measured

**Qwen's ÷8 is measured here.** Every other family is *declared absent* rather than guessed:
an unmeasured entry in this table is worse than a missing one, because a wrong divisor either
halts correct work or passes the defect it was added for. An unknown family returns
NOT_APPLICABLE and names itself.

## ÷8 halts; ÷16 advises

The standing constraint reads *"÷8 is the floor, prefer ÷16"* — a floor and a preference, not two
floors. A width indivisible by 8 decodes short and corrupts the pairing: that HALTS. A width
divisible by 8 but not 16 is legal and dispreferred (deeper stacks patch at 16): that is an
**ADVISORY**. Promoting the preference to a halt would fire on 1064 and on every other legal ÷8
frame — a gate halting correct work, which is how a gate gets disabled.

**The ÷16 case returns `Verdict.ADVISORY`, not `PASS` with a note (Amendment 3).** Amendment 1a's
original wording — *"it PASSES with a note"* — predates the verdict vocabulary; once `ADVISORY`
exists in the merge order, the ÷16 note *is* an advisory and carrying it as one is a re-labeling
rather than a re-specification. Nothing about when this check halts changed: ÷8 still halts, ÷16
still never does. What changed is that the advisory now travels as a located finding a caller can
see beside check 8's, instead of as prose in a field that merges into a green verdict.
"""

from __future__ import annotations

import dataclasses

from comfy_preflight.errors import Defect, PreflightHalt, Verdict
from comfy_preflight.graph import Graph

CHECK_NAME = "check_5_generator_legal_frame"

# Input names that carry a frame dimension when a graph declares one at all.
DIMENSION_INPUT_NAMES = ("width", "height")


@dataclasses.dataclass(frozen=True)
class FrameConstraint:
    """One model family's frame rule.

    `divisor` is the hard floor - a dimension indivisible by it decodes short.
    `preferred_divisor` is a preference and never halts.
    """

    family: str
    divisor: int
    preferred_divisor: int | None
    source: str


# MEASURED families only. Adding a row requires a measurement or a citation, not recall.
QWEN = FrameConstraint(
    family="qwen",
    divisor=8,
    preferred_divisor=16,
    source=(
        "measured: 1066/8 = 133.25 encodes to 133 latent columns and decodes to 1064; the "
        "re-ruled frame 1072 is divisible by 16 against stacks that patch at 16"
    ),
)

FAMILIES: dict[str, FrameConstraint] = {"qwen": QWEN}

# Named so a caller can see the boundary rather than infer it from a KeyError. These are NOT
# unsupported-forever; they are unmeasured, and each needs its own measurement or citation.
DECLARED_ABSENT_FAMILIES = ("sdxl", "sd15", "flux", "wan", "hunyuan", "chroma")


@dataclasses.dataclass(frozen=True)
class CheckResult:
    verdict: Verdict
    clauses_evaluated: tuple[str, ...]
    clauses_declined: tuple[tuple[str, str], ...]
    operand: str  # "graph_literals" | "input_dimensions" | "none"
    dimensions_checked: tuple[tuple[str, int], ...]
    family: str
    # Non-halting findings — the ÷16 advisory. Named `findings` to match check 8, because the
    # aggregator reads that one field across every check; a check whose advisories lived under a
    # different name would have them silently dropped from the merged report.
    findings: tuple[Defect, ...] = ()
    notes: tuple[str, ...] = ()


def declared_dimensions(graph: Graph) -> list[tuple[str, str, int]]:
    """Every literal frame dimension the graph declares, as (node_id, input_name, value)."""
    found: list[tuple[str, str, int]] = []
    for node_id, input_name, value in graph.literals():
        if input_name in DIMENSION_INPUT_NAMES and isinstance(value, int) and not isinstance(
            value, bool
        ):
            found.append((node_id, input_name, value))
    return found


def check_generator_legal_frame(
    graph: Graph,
    *,
    family: str = "qwen",
    input_dimensions: tuple[int, int] | None = None,
) -> CheckResult:
    """Run check 5 against the effective frame.

    `input_dimensions` is `(width, height)` of the image the graph will consume — supplied by the
    caller, because this package does not decode images. Omit it and, on an img2img graph, the
    check returns NOT_APPLICABLE naming what it could not see.

    There is no skip parameter.
    """
    defects: list[Defect] = []
    findings: list[Defect] = []
    evaluated: list[str] = []
    declined: list[tuple[str, str]] = []
    notes: list[str] = []

    constraint = FAMILIES.get(family.lower())
    if constraint is None:
        declined.append(
            (
                "frame_divisibility",
                f"family {family!r} has no measured frame constraint, so legality is not "
                f"askable. Measured families: {sorted(FAMILIES)}. Declared absent (unmeasured, "
                f"each needs its own measurement or citation): {list(DECLARED_ABSENT_FAMILIES)}. "
                "An unmeasured divisor either halts correct work or passes the defect it was "
                "added for",
            )
        )
        return CheckResult(
            verdict=Verdict.NOT_APPLICABLE,
            clauses_evaluated=(),
            clauses_declined=tuple(declined),
            operand="none",
            dimensions_checked=(),
            family=family,
        )

    declared = declared_dimensions(graph)

    # Each subject is (label, value, node_id, input_name). The last two are None only on the
    # input-dimensions path, where the operand is the uploaded image and there is genuinely no
    # node to name — the one documented exception to "every finding names its node".
    if declared:
        operand = "graph_literals"
        subjects = [(f"node {nid}.{name}", value, nid, name) for nid, name, value in declared]
    elif input_dimensions is not None:
        operand = "input_dimensions"
        width, height = input_dimensions
        subjects = [
            ("input width", int(width), None, None),
            ("input height", int(height), None, None),
        ]
        notes.append(
            "the graph declares no dimension; the frame was taken from the input image's "
            "dimensions as supplied by the caller"
        )
    else:
        operand = "none"
        declined.append(
            (
                "frame_divisibility",
                "the graph declares no width or height, and no input_dimensions were supplied, "
                "so the effective frame is not visible. This is an img2img graph: the frame is "
                "inherited from the uploaded image. Pass input_dimensions to check it - the "
                "in-process caller has the image by construction",
            )
        )
        return CheckResult(
            verdict=Verdict.NOT_APPLICABLE,
            clauses_evaluated=(),
            clauses_declined=tuple(declined),
            operand=operand,
            dimensions_checked=(),
            family=constraint.family,
        )

    evaluated.append("frame_divisibility")
    for label, value, node_id, input_name in subjects:
        if value <= 0:
            defects.append(
                Defect(
                    code="FRAME_NOT_POSITIVE",
                    message=f"{label} is {value}",
                    hint="a frame dimension must be a positive number of pixels",
                    node_id=node_id,
                    input_name=input_name,
                )
            )
            continue
        if value % constraint.divisor != 0:
            decoded = (value // constraint.divisor) * constraint.divisor
            defects.append(
                Defect(
                    code="FRAME_NOT_GENERATOR_LEGAL",
                    message=(
                        f"{label} is {value}, which is not divisible by "
                        f"{constraint.divisor} for family {constraint.family!r}. "
                        f"{value}/{constraint.divisor} = {value / constraint.divisor:g}, so it "
                        f"encodes to {value // constraint.divisor} latent units and decodes to "
                        f"{decoded} - every output would be {value - decoded} px off its control "
                        "image and every downstream pairing would break"
                    ),
                    hint=(
                        f"round to the nearest legal size: {_nearest_legal(value, constraint)}. "
                        "Derive the frame from the subject, then round - do not let the check "
                        "round for you, because a graph a gate repaired is a graph nobody "
                        "reviewed"
                    ),
                    node_id=node_id,
                    input_name=input_name,
                )
            )
        elif (
            constraint.preferred_divisor is not None
            and value % constraint.preferred_divisor != 0
        ):
            findings.append(
                Defect(
                    code="FRAME_BELOW_PREFERRED_DIVISOR",
                    message=(
                        f"{label} is {value}: divisible by {constraint.divisor} (legal) but not "
                        f"by {constraint.preferred_divisor} (preferred, against stacks that patch "
                        f"at {constraint.preferred_divisor})"
                    ),
                    hint=(
                        f"ADVISORY, not a halt - {constraint.divisor} is the floor and this frame "
                        f"clears it. {constraint.preferred_divisor} is a preference, and the "
                        "record classifies this exact width as legal-but-not-preferred. If the "
                        f"frame was derived from the subject, proceed; "
                        f"{_nearest_legal(value, constraint)}"
                    ),
                    node_id=node_id,
                    input_name=input_name,
                )
            )

    if defects:
        raise PreflightHalt(CHECK_NAME, defects)

    return CheckResult(
        # ADVISORY, not PASS-with-a-note (Amendment 3). Nothing about when this check HALTS
        # changed - only how the non-halting finding travels.
        verdict=Verdict.ADVISORY if findings else Verdict.PASS,
        clauses_evaluated=tuple(evaluated),
        clauses_declined=tuple(declined),
        operand=operand,
        dimensions_checked=tuple((label, value) for label, value, _, _ in subjects),
        family=constraint.family,
        findings=tuple(findings),
        notes=tuple(notes),
    )


def _nearest_legal(value: int, constraint: FrameConstraint) -> str:
    """Describe the legal sizes either side, preferring the deeper divisor where it is close.

    Returns text for a hint. It does NOT modify anything - this check never repairs a graph.
    """
    down = (value // constraint.divisor) * constraint.divisor
    up = down + constraint.divisor
    parts = [f"{down} or {up} (divisible by {constraint.divisor})"]
    if constraint.preferred_divisor:
        p = constraint.preferred_divisor
        pdown = (value // p) * p
        pup = pdown + p
        parts.append(f"or {pdown} / {pup} for the preferred multiple of {p}")
    return ", ".join(parts)
