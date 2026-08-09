"""Check 4 — the graph that was saved is the graph that was submitted.

**The recipe for a generative step is the submitted workflow JSON** — graph, model names, seed,
sampler values, prompt, inputs. Not the script that built it: a script pins a local invocation
while the parameters that matter live in its source. So the exact JSON is saved before
submission, and this check compares saved against submitted.

## Compared AS PARSED GRAPHS, never as text

*A JSON re-dump can differ in whitespace without a value moving.* Comparing text produces false
halts; comparing parsed graphs produces true ones. This check compares node id sets, class
types, input name sets, link targets and literal values — and nothing about formatting.

**This repo holds both questions and they are not the same question.** The fixture manifest asks
the BYTE question — *is this file the artifact it was copied from* — and it is right to, because
provenance is byte-identity and a reformatted fixture should be caught. Check 4 asks the VALUE
question — *did a parameter move between save and submit* — and a byte comparison answers it
wrongly in both directions. Keeping them separate is deliberate; the distinction cost this repo
a red CI leg when git's line-ending conversion made a byte claim true on one platform only.

## Numeric comparison

Values are compared with `==`, which in Python makes `1 == 1.0` true. That is the intended
reading: a re-dump that renders a seed as `770700` or `770700.0` has not moved the seed. A
comparison strict about int-versus-float would report a difference where no value changed, which
is the false-halt this check exists to avoid.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from comfy_preflight.errors import Defect, PreflightHalt, Verdict
from comfy_preflight.graph import Graph, is_link

CHECK_NAME = "check_4_saved_is_graph_submitted"


@dataclasses.dataclass(frozen=True)
class CheckResult:
    verdict: Verdict
    clauses_evaluated: tuple[str, ...]
    clauses_declined: tuple[tuple[str, str], ...]
    nodes_compared: int
    inputs_compared: int
    notes: tuple[str, ...] = ()


def _render(value: Any) -> str:
    if is_link(value):
        return f"link -> node {value[0]} slot {value[1]}"
    return repr(value)


def check_saved_is_submitted(saved: Graph, submitted: Graph) -> CheckResult:
    """Compare two parsed graphs. Returns a CheckResult on PASS; raises PreflightHalt on any
    difference in structure or value.

    Argument order matters only for the wording of a defect: `saved` is the sidecar written
    before submission, `submitted` is the payload actually sent.
    """
    defects: list[Defect] = []
    evaluated = ["node_set", "class_types", "input_names", "input_values"]
    inputs_compared = 0

    saved_ids, submitted_ids = saved.node_ids, submitted.node_ids

    # ---- the node set --------------------------------------------------------
    for node_id in sorted(saved_ids - submitted_ids, key=_sort_key):
        defects.append(
            Defect(
                code="NODE_MISSING_FROM_SUBMITTED",
                message=(
                    f"node {node_id} ({saved[node_id].class_type}) is in the saved graph but "
                    "not in the submitted payload"
                ),
                hint="the payload was rebuilt or edited after saving; submit the saved file",
                node_id=node_id,
            )
        )
    for node_id in sorted(submitted_ids - saved_ids, key=_sort_key):
        defects.append(
            Defect(
                code="NODE_ADDED_IN_SUBMITTED",
                message=(
                    f"node {node_id} ({submitted[node_id].class_type}) is in the submitted "
                    "payload but not in the saved graph"
                ),
                hint="the payload gained a node after saving; save the graph you submit",
                node_id=node_id,
            )
        )

    # ---- per-node comparison, over the shared ids ----------------------------
    for node_id in sorted(saved_ids & submitted_ids, key=_sort_key):
        a, b = saved[node_id], submitted[node_id]

        if a.class_type != b.class_type:
            defects.append(
                Defect(
                    code="CLASS_TYPE_CHANGED",
                    message=f"saved {a.class_type!r}; submitted {b.class_type!r}",
                    hint="the node was replaced with a different class after saving",
                    node_id=node_id,
                )
            )

        a_names, b_names = set(a.inputs), set(b.inputs)
        for name in sorted(a_names - b_names):
            defects.append(
                Defect(
                    code="INPUT_MISSING_FROM_SUBMITTED",
                    message=f"input {name!r} is in the saved node but not in the submitted one",
                    hint="an input was dropped after saving; its value falls back to a default",
                    node_id=node_id,
                    input_name=name,
                )
            )
        for name in sorted(b_names - a_names):
            defects.append(
                Defect(
                    code="INPUT_ADDED_IN_SUBMITTED",
                    message=f"input {name!r} is in the submitted node but not in the saved one",
                    hint="an input appeared after saving; save the graph you submit",
                    node_id=node_id,
                    input_name=name,
                )
            )

        for name in sorted(a_names & b_names):
            inputs_compared += 1
            av, bv = a.inputs[name], b.inputs[name]
            if is_link(av) != is_link(bv):
                defects.append(
                    Defect(
                        code="INPUT_KIND_CHANGED",
                        message=(
                            f"saved {_render(av)}; submitted {_render(bv)} - one is a link and "
                            "the other a literal"
                        ),
                        hint="a wire was replaced by a constant or vice versa after saving",
                        node_id=node_id,
                        input_name=name,
                    )
                )
            elif is_link(av):
                if str(av[0]) != str(bv[0]) or int(av[1]) != int(bv[1]):
                    defects.append(
                        Defect(
                            code="LINK_RETARGETED",
                            message=f"saved {_render(av)}; submitted {_render(bv)}",
                            hint="the wire moved after saving; submit the saved file",
                            node_id=node_id,
                            input_name=name,
                        )
                    )
            elif av != bv:
                defects.append(
                    Defect(
                        code="VALUE_CHANGED",
                        message=f"saved {av!r}; submitted {bv!r}",
                        hint=(
                            "a parameter moved between save and submit. The saved sidecar is "
                            "the recipe; if the new value is intended, save it and resubmit"
                        ),
                        node_id=node_id,
                        input_name=name,
                    )
                )

    if defects:
        raise PreflightHalt(CHECK_NAME, defects)

    return CheckResult(
        verdict=Verdict.PASS,
        clauses_evaluated=tuple(evaluated),
        clauses_declined=(),
        nodes_compared=len(saved_ids & submitted_ids),
        inputs_compared=inputs_compared,
    )


def _sort_key(node_id: str) -> tuple[int, int | str]:
    """Numeric order where ids are numeric, lexical otherwise, so defects list predictably."""
    return (0, int(node_id)) if node_id.isdigit() else (1, node_id)
