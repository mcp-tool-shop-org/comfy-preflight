"""Check 1 — link topology. The product's founding case.

The incident: a hand-retyped payload carried `VAEDecode.samples = ["14", 0]` — node 14's input
reading node 14 — and Comfy Cloud's `dry_run` returned `status: validated`. The provider's
validator answers *is this well-formed enough to run*, not *is this the graph you meant*.

Three clauses, and they are not equally buildable:

| clause | asks | needs |
|---|---|---|
| `self_link` | does any input read its own node? | nothing |
| `dangling_link` | does any link name a node id absent from the graph? | nothing |
| `undeclared_input` | does any node carry an input its class does not declare? | **a node schema** |

**`undeclared_input` takes an injected schema and returns NOT_APPLICABLE without one.** ComfyUI
serves the schema at `/object_info`; this package makes no network calls by design, so the
schema arrives as a parameter or the clause declines. It is not inferred from the corpus:
deriving the reference from the graphs being checked would make the gate a tautology that
passes review because the numbers look fine.

**Out of scope, named rather than silently absent:** orphan detection (a node whose output
nothing reads). The record checks it alongside these three in hand-driven runs, but the spec
lists exactly three clauses for check 1 and a non-terminal orphan is a different property —
a graph may legitimately carry a node whose output is unused. It is a candidate clause, not an
omission.
"""

from __future__ import annotations

import dataclasses

from comfy_preflight.errors import Defect, PreflightHalt, Verdict
from comfy_preflight.graph import Graph

CHECK_NAME = "check_1_link_topology"


@dataclasses.dataclass(frozen=True)
class NodeSchema:
    """The declared input names per class type, as served by ComfyUI's `/object_info`.

    `inputs_by_class` maps a `class_type` to every input name that class declares — required
    and optional together. A class absent from the mapping is reported as unknown rather than
    treated as either passing or failing: a schema that does not cover a node cannot answer for
    it, and guessing in either direction is worse than saying so.
    """

    inputs_by_class: dict[str, frozenset[str]]

    def declares(self, class_type: str) -> frozenset[str] | None:
        return self.inputs_by_class.get(class_type)


@dataclasses.dataclass(frozen=True)
class CheckResult:
    verdict: Verdict
    clauses_evaluated: tuple[str, ...]
    clauses_declined: tuple[tuple[str, str], ...]
    links_examined: int
    nodes_examined: int
    classes_not_in_schema: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


def check_link_topology(
    graph: Graph,
    *,
    schema: NodeSchema | None = None,
) -> CheckResult:
    """Run check 1. Returns a CheckResult on PASS; raises PreflightHalt on a defect.

    There is no skip parameter. `schema` is the injected node schema for the third clause;
    without it that clause declines and says so.
    """
    defects: list[Defect] = []
    evaluated: list[str] = []
    declined: list[tuple[str, str]] = []
    notes: list[str] = []

    node_ids = graph.node_ids
    links = list(graph.links())

    # ---- clause 1a: a node input reading its own node -----------------------
    evaluated.append("self_link")
    for link in links:
        if link.source_id == link.node_id:
            defects.append(
                Defect(
                    code="SELF_LINK",
                    message=(
                        f"input reads slot {link.source_slot} of its own node "
                        f"({link.node_id}); a node cannot be its own producer"
                    ),
                    hint=(
                        "repoint this input at the node that actually produces the value. "
                        "A provider dry_run has returned `validated` on exactly this defect, "
                        "so a passing pre-flight elsewhere is not evidence against it"
                    ),
                    node_id=link.node_id,
                    input_name=link.input_name,
                )
            )

    # ---- clause 1b: a link naming a node id not in the graph ----------------
    evaluated.append("dangling_link")
    for link in links:
        if link.source_id == link.node_id:
            continue  # already reported as a self-link; one defect per cause
        if link.source_id not in node_ids:
            defects.append(
                Defect(
                    code="DANGLING_LINK",
                    message=(
                        f"input reads node {link.source_id!r}, which is not in the graph"
                    ),
                    hint=(
                        "the producing node was renumbered or removed; repoint the input or "
                        "restore the node"
                    ),
                    node_id=link.node_id,
                    input_name=link.input_name,
                )
            )

    # ---- clause 1c: an input the class does not declare ---------------------
    unknown_classes: set[str] = set()
    if schema is None:
        declined.append(
            (
                "undeclared_input",
                "no node schema was supplied, so 'an input the class does not declare' is "
                "not askable. ComfyUI serves one at /object_info; this package makes no "
                "network calls, so the caller injects it. It is deliberately NOT inferred "
                "from the graphs being checked - that would make the gate a tautology",
            )
        )
    else:
        evaluated.append("undeclared_input")
        for node in graph.nodes.values():
            declared = schema.declares(node.class_type)
            if declared is None:
                unknown_classes.add(node.class_type)
                continue
            for input_name in node.inputs:
                if input_name not in declared:
                    defects.append(
                        Defect(
                            code="UNDECLARED_INPUT",
                            message=(
                                f"class {node.class_type!r} does not declare an input named "
                                f"{input_name!r}"
                            ),
                            hint=(
                                "a misspelled or renamed input is silently ignored by the "
                                "runtime, so the value you set never reaches the node. Check "
                                "the input name against the class, or update the schema if the "
                                "node version changed"
                            ),
                            node_id=node.node_id,
                            input_name=input_name,
                        )
                    )
        for class_type in sorted(unknown_classes):
            notes.append(
                f"class {class_type!r} is not in the supplied schema; its inputs were not "
                "checked against a declaration"
            )

    if defects:
        raise PreflightHalt(CHECK_NAME, defects)

    return CheckResult(
        verdict=Verdict.PASS if evaluated else Verdict.NOT_APPLICABLE,
        clauses_evaluated=tuple(evaluated),
        clauses_declined=tuple(declined),
        links_examined=len(links),
        nodes_examined=len(node_ids),
        classes_not_in_schema=tuple(sorted(unknown_classes)),
        notes=tuple(notes),
    )
