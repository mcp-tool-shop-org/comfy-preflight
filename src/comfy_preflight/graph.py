"""Parsing a ComfyUI API-format workflow graph into something checkable.

The API format is `{node_id: {"class_type": str, "inputs": {...}}}`. An input value is either
a **link** — a two-element list `[source_node_id, source_slot]` — or a **literal** (a string,
number, or boolean).

Two decisions worth stating, because both are places a naive parser goes wrong:

1. **Links are distinguished structurally, not by guessing.** `["14", 0]` is a link;
   `["a", "b"]` and `[1, 2]` and `["14", 0, 0]` are not. A literal list value that happens to
   be two elements long is only treated as a link when its first element is a string and its
   second an int, which is the format ComfyUI actually emits.

2. **Nothing here validates against node class schemas**, because that requires a live
   ComfyUI instance's `/object_info` and this package has no network access by design. A check
   that wants "an input the class does not declare" needs a schema source injected; the parser
   deliberately does not pretend to know.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator
from typing import Any

from comfy_preflight.errors import Defect, PreflightHalt


@dataclasses.dataclass(frozen=True)
class Link:
    """One resolved edge: `node_id.input_name` reads slot `source_slot` of `source_id`."""

    node_id: str
    input_name: str
    source_id: str
    source_slot: int


@dataclasses.dataclass(frozen=True)
class Node:
    node_id: str
    class_type: str
    inputs: dict[str, Any]

    def links(self) -> Iterator[Link]:
        for name, value in self.inputs.items():
            if is_link(value):
                yield Link(self.node_id, name, str(value[0]), int(value[1]))

    def literals(self) -> Iterator[tuple[str, Any]]:
        for name, value in self.inputs.items():
            if not is_link(value):
                yield name, value


def is_link(value: Any) -> bool:
    """True for ComfyUI's `[source_node_id, source_slot]` link shape, and nothing else."""
    return (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[0], str)
        and isinstance(value[1], int)
        and not isinstance(value[1], bool)  # bool is an int subclass; a slot is not a bool
    )


class Graph:
    """A parsed API-format workflow graph."""

    def __init__(self, nodes: dict[str, Node]) -> None:
        self._nodes = nodes

    @classmethod
    def from_api_dict(cls, data: Any) -> Graph:
        """Parse, or halt with a located defect. Never returns a partially-parsed graph."""
        defects: list[Defect] = []

        if not isinstance(data, dict):
            defects.append(
                Defect(
                    code="GRAPH_NOT_OBJECT",
                    message=f"expected a JSON object of nodes, got {type(data).__name__}",
                    hint="pass an API-format graph: {node_id: {class_type, inputs}}. "
                    "A UI-export graph (with 'nodes' and 'links' arrays) is a different "
                    "format and must be converted first.",
                )
            )
            raise PreflightHalt("graph_parse", defects)

        if not data:
            defects.append(
                Defect(
                    code="GRAPH_EMPTY",
                    message="the graph has no nodes",
                    hint="an empty graph cannot be checked; confirm the builder produced output",
                )
            )
            raise PreflightHalt("graph_parse", defects)

        nodes: dict[str, Node] = {}
        for raw_id, raw_node in data.items():
            node_id = str(raw_id)
            if not isinstance(raw_node, dict):
                defects.append(
                    Defect(
                        code="NODE_NOT_OBJECT",
                        message=f"node is {type(raw_node).__name__}, not an object",
                        hint="each node must be an object with class_type and inputs",
                        node_id=node_id,
                    )
                )
                continue
            class_type = raw_node.get("class_type")
            if not isinstance(class_type, str) or not class_type:
                defects.append(
                    Defect(
                        code="NODE_NO_CLASS_TYPE",
                        message="node has no class_type",
                        hint="an API-format node declares its class_type; a UI-export graph "
                        "uses 'type' instead and needs converting",
                        node_id=node_id,
                    )
                )
                continue
            raw_inputs = raw_node.get("inputs", {})
            if not isinstance(raw_inputs, dict):
                defects.append(
                    Defect(
                        code="NODE_INPUTS_NOT_OBJECT",
                        message=f"inputs is {type(raw_inputs).__name__}, not an object",
                        hint="inputs must be an object mapping input names to values",
                        node_id=node_id,
                    )
                )
                continue
            nodes[node_id] = Node(node_id=node_id, class_type=class_type, inputs=dict(raw_inputs))

        if defects:
            raise PreflightHalt("graph_parse", defects)
        return cls(nodes)

    # -- accessors -------------------------------------------------------------

    @property
    def nodes(self) -> dict[str, Node]:
        return dict(self._nodes)

    @property
    def node_ids(self) -> set[str]:
        return set(self._nodes)

    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, node_id: object) -> bool:
        return str(node_id) in self._nodes

    def __getitem__(self, node_id: str) -> Node:
        return self._nodes[str(node_id)]

    def get(self, node_id: str) -> Node | None:
        return self._nodes.get(str(node_id))

    def links(self) -> Iterator[Link]:
        for node in self._nodes.values():
            yield from node.links()

    def literals(self) -> Iterator[tuple[str, str, Any]]:
        for node in self._nodes.values():
            for name, value in node.literals():
                yield node.node_id, name, value

    def nodes_of_class(self, *class_types: str) -> list[Node]:
        wanted = set(class_types)
        return [n for n in self._nodes.values() if n.class_type in wanted]

    def consumers_of(self, node_id: str) -> list[Link]:
        """Every link reading from `node_id`."""
        return [ln for ln in self.links() if ln.source_id == str(node_id)]
