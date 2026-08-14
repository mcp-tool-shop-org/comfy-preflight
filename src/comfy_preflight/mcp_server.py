"""The MCP surface — stdio, and a **transport over the same in-process function**.

    python -m comfy_preflight.mcp_server

The tool calls `preflight()` and returns its structured result verbatim. It is not a second
implementation, it holds no opinion about what matters in a result, and a test pins that its
output is byte-identical to what the library returns.

## ⚠ This is not the production gate either

Neither is the CLI. **A gate reached over a transport is not a guard**: an agent that calls this
tool, reads a HALT, and then submits from somewhere else has a shell chain with a protocol in
the middle. The rule this repo enforces on itself is that *the check lives inside the tool that
performs the irreversible step* — so the production gate is the in-process `preflight()` call on
the submit path, and there is no skip flag.

This surface exists for the third door the spec names: the session hand-driving a graph, where
the graph is in a conversation rather than in a file or a submit function.

## Why a HALT is a successful tool call

The tool returns `{"verdict": "halt", ...}` rather than raising a protocol error. A halt is a
preflight run that worked and found something; reporting it as a tool failure would throw away
the structure the caller needs — which defect, which node, what to do — and leave a client
retrying a call that will keep succeeding at finding the same defect.

## Why the graph arrives inline rather than as a path

This tool takes graph JSON, not filenames. An MCP server that opened arbitrary paths on request
would add a filesystem-read surface to a package whose threat model says it reaches neither the
filesystem nor the network through its inputs. A caller that has a file reads it and passes the
object; a caller hand-driving a graph already has the object.

## Dependency

`mcp` is an **optional** dependency: `pip install comfy-preflight[mcp]`. The core package keeps
zero runtime dependencies, and that is load-bearing rather than tidy — the npm door is only open
to packages whose dependencies are stdlib, sqlite3 and mcp. So nothing here is imported at
module load, and `run_preflight` below works with the SDK absent.
"""

from __future__ import annotations

from typing import Any

from comfy_preflight import __version__
from comfy_preflight.aggregate import preflight
from comfy_preflight.checks.c1_link_topology import NodeSchema
from comfy_preflight.errors import PreflightHalt
from comfy_preflight.graph import Graph
from comfy_preflight.register import AdapterRegister

TOOL_NAME = "preflight"
SERVER_NAME = "comfy-preflight"

# Requires mcp 2.x: the server class is `mcp.server.MCPServer`, and 2.0 removed the 1.x
# `mcp.server.fastmcp.FastMCP` this would otherwise have been written against. Verified against
# the installed SDK at build time rather than recalled, which is the same discipline check 8's
# table is held to.
MCP_REQUIREMENT = "mcp>=2.0"

TOOL_DESCRIPTION = (
    "Run the comfy-preflight checks on a ComfyUI API-format workflow graph before it is "
    "submitted, and return one structured verdict. Composes link topology (1), the inverted "
    "register scan (2), graph-saved-is-graph-submitted (4), the generator-legal frame (5) and "
    "the declared-envelope advisory (8). Submits nothing and contacts no provider. "
    "Verdicts merge HALT > ADVISORY > NOT_APPLICABLE > PASS; a HALT is a successful call that "
    "found defects, not a tool error. NOT THE PRODUCTION GATE: a gate reached over a transport "
    "is not a guard - call preflight() in-process on the submit path."
)


class MissingDependency(RuntimeError):
    """Raised when the MCP surface is used without the optional `mcp` extra installed."""


def _server_class():
    try:
        from mcp.server import MCPServer
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise MissingDependency(
            f"the MCP surface needs the optional dependency '{MCP_REQUIREMENT}'. "
            "Install it with: pip install 'comfy-preflight[mcp]'. The core package keeps zero "
            "runtime dependencies on purpose, so the SDK is not pulled in by default"
        ) from exc
    return MCPServer


def run_preflight(
    graph: dict[str, Any],
    register: dict[str, Any] | None = None,
    input_dims: list[int] | None = None,
    saved_graph: dict[str, Any] | None = None,
    consumer_input: str | None = None,
    schema: dict[str, list[str]] | None = None,
    family: str = "qwen",
) -> dict[str, Any]:
    """The tool body, and deliberately free of any `mcp` import so it is testable without the SDK.

    Every argument beyond `graph` is an askability parameter: supplying it makes a clause
    askable, and omitting it makes the relevant check decline and name what it could not see.
    None of them is a skip flag.

    Returns `PreflightResult.to_dict()` verbatim - including on HALT, which arrives here through
    the report the halt carries rather than through a second, non-raising entry point.
    """
    parsed = _parse_graph(graph, "graph")
    parsed_saved = _parse_graph(saved_graph, "saved_graph") if saved_graph is not None else None
    parsed_register = AdapterRegister.from_dict(register) if register is not None else None

    dims: tuple[int, int] | None = None
    if input_dims is not None:
        if len(input_dims) != 2:
            raise ValueError(
                f"input_dims must be [width, height]; got {len(input_dims)} value(s)"
            )
        dims = (int(input_dims[0]), int(input_dims[1]))

    consumer: tuple[str, str] | None = None
    if consumer_input is not None:
        node_id, _, name = consumer_input.partition(".")
        if not node_id or not name:
            raise ValueError(f"consumer_input must look like '6.model'; got {consumer_input!r}")
        consumer = (node_id, name)

    node_schema = (
        NodeSchema(inputs_by_class={cls: frozenset(names) for cls, names in schema.items()})
        if schema is not None
        else None
    )

    try:
        result = preflight(
            parsed,
            parsed_register,
            dims,
            saved_graph=parsed_saved,
            schema=node_schema,
            consumer_input=consumer,
            family=family,
        )
    except PreflightHalt as halt:
        result = halt.report
    return result.to_dict()


def _parse_graph(data: object, what: str) -> Graph:
    """Parse, converting a parse halt into a ValueError.

    A graph that will not parse is a bad argument, not a preflight finding: nothing was checked,
    and returning a HALT verdict would claim the gate examined a graph it never had.
    """
    try:
        return Graph.from_api_dict(data)
    except PreflightHalt as halt:
        raise ValueError(f"{what} did not parse as an API-format graph: {halt}") from halt


def build_server():
    """Construct the stdio MCP server. Requires the `mcp` extra."""
    server = _server_class()(
        name=SERVER_NAME,
        version=__version__,
        instructions=(
            "Run preflight on a ComfyUI workflow graph before submitting it. This server is a "
            "TRANSPORT over an in-process function, not the production gate: reading a HALT here "
            "and submitting elsewhere is a shell chain with a protocol in the middle. Wire "
            "preflight() into the code that submits."
        ),
    )
    server.add_tool(
        run_preflight,
        name=TOOL_NAME,
        title="Preflight a ComfyUI workflow graph",
        description=TOOL_DESCRIPTION,
        structured_output=True,
    )
    return server


def main() -> int:
    """Serve over stdio. Returns an exit code rather than calling sys.exit."""
    try:
        server = build_server()
    except MissingDependency as exc:
        import sys

        print(f"{SERVER_NAME}: {exc}", file=sys.stderr)
        return 2
    server.run(transport="stdio")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by running the module
    raise SystemExit(main())
