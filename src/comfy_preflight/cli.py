"""The CLI verb — the development door.

    comfy-preflight check graph.json --input-dims 1072x1024 --register subject.json

**This is not the production gate, and the distinction is load-bearing.** A preflight in a
shell chain before a submit is a *transport, not a guard*: in the incident that produced that
rule, 47,020 texels were committed after a gate had already fired, because a PowerShell chain
walked past a failing exit code. Nobody decided to proceed — the construction was incapable of
stopping. So the production gate is the in-process `preflight()` call on the submit path, and
this command exists for developing a graph by hand.

## Exit codes

This repo had no CLI before, so there was no convention to follow; these are established here
and follow from its laws rather than from taste.

| code | meaning |
|---|---|
| 0 | nothing halted — PASS, ADVISORY or NOT_APPLICABLE, each named in the output |
| 1 | HALT — a defect was found |
| 2 | **nothing was examined** — bad arguments, unreadable file, unparseable graph, or an internal error |

**Exit 2 is one code for two causes on purpose.** A bad path and a bug in this package differ in
whose fault they are, and the message says which — but they do not differ in what the caller may
conclude, which is *nothing about the graph*. Splitting them would invite a caller to treat one
as a soft failure. The distinction that matters to an exit code is examined / not examined.

**ADVISORY exits 0 deliberately.** A nonzero exit stops a `&&` chain, which would make the
advisory a halt in every shell that runs one — and Amendment 2 rules check 8 advisory precisely
so it never stops correct work. **NOT_APPLICABLE exits 0 for the same reason inverted:** every
one of the 70 recorded graphs is img2img, so a run without `--input-dims` declines check 5, and
a gate that exits nonzero on correct work is a gate that gets disabled by the third person who
hits it.

Both are still *named* in the output and carried in `--json`, so a caller that wants to gate on
an advisory reads the verdict rather than the exit status. That is the same split the whole
product rests on: the exit code is a transport signal, and the verdict is the finding.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from comfy_preflight import __version__
from comfy_preflight.aggregate import PreflightResult, preflight
from comfy_preflight.checks.c1_link_topology import NodeSchema
from comfy_preflight.errors import Defect, PreflightHalt, Verdict
from comfy_preflight.graph import Graph
from comfy_preflight.register import AdapterRegister
from comfy_preflight.registry import NOT_REGISTERED

EXIT_OK = 0
EXIT_HALT = 1
EXIT_USAGE = 2

PROGRAM = "comfy-preflight"


class UsageError(Exception):
    """A problem with what the caller passed, not with the graph. Always exits 2.

    Kept distinct from `PreflightHalt` because conflating them would report a typo in a path as
    a defect in a graph — and a caller who sees exit 1 believes the gate examined something.
    """


def _read_json(path: str, what: str) -> Any:
    file = pathlib.Path(path)
    if not file.exists():
        raise UsageError(f"{what} not found: {path}")
    try:
        return json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UsageError(f"{what} is not valid JSON ({path}): {exc}") from exc


def _load_graph(path: str, what: str) -> Graph:
    data = _read_json(path, what)
    try:
        return Graph.from_api_dict(data)
    except PreflightHalt as halt:
        # A graph that will not parse is an input problem, not a preflight finding: nothing was
        # checked, so reporting it as a HALT would claim the gate examined a graph it never had.
        raise UsageError(f"{what} did not parse as an API-format graph ({path}):\n{halt}") from halt


def _parse_dims(value: str) -> tuple[int, int]:
    text = value.lower().replace("*", "x").replace(",", "x")
    parts = [p.strip() for p in text.split("x")]
    if len(parts) != 2:
        raise UsageError(f"--input-dims must look like 1072x1024, got {value!r}")
    try:
        width, height = int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise UsageError(f"--input-dims must be two integers, got {value!r}") from exc
    return width, height


def _parse_consumer(value: str) -> tuple[str, str]:
    node_id, _, input_name = value.partition(".")
    if not node_id or not input_name:
        raise UsageError(f"--consumer must look like 6.model, got {value!r}")
    return node_id, input_name


def _load_register(path: str) -> AdapterRegister:
    try:
        return AdapterRegister.from_dict(_read_json(path, "register profile"))
    except ValueError as exc:
        raise UsageError(f"register profile is not a valid register ({path}): {exc}") from exc


def _load_schema(path: str) -> NodeSchema:
    """Load a node schema as `{class_type: [input names]}`.

    Deliberately NOT a parser for ComfyUI's `/object_info` response. That format was not
    measured at this seat, and writing a parser for a shape nobody here has opened would be the
    same error as populating check 8's table from memory. Derive the mapping from your instance
    and pass it; the format this accepts is stated above and is the whole contract.
    """
    data = _read_json(path, "node schema")
    if not isinstance(data, dict):
        raise UsageError("node schema must be an object of {class_type: [input names]}")
    mapping: dict[str, frozenset[str]] = {}
    for class_type, names in data.items():
        if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
            raise UsageError(
                f"node schema entry {class_type!r} must be a list of input-name strings"
            )
        mapping[class_type] = frozenset(names)
    return NodeSchema(inputs_by_class=mapping)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description=(
            "Run the preflight checks on a ComfyUI API-format workflow graph. "
            "Does not submit anything and never contacts a provider."
        ),
        epilog=(
            "Exit codes: 0 = nothing halted (PASS, ADVISORY or NOT_APPLICABLE, each named in "
            "the output); 1 = HALT; 2 = usage or input error. ADVISORY and NOT_APPLICABLE exit "
            "0 on purpose: a nonzero exit would stop a shell chain, turning an advisory into a "
            "halt. THIS COMMAND IS NOT THE PRODUCTION GATE - call preflight() in-process on the "
            "submit path, where a shell chain cannot walk past it."
        ),
    )
    parser.add_argument("--version", action="version", version=f"{PROGRAM} {__version__}")
    sub = parser.add_subparsers(dest="verb", required=True)

    check = sub.add_parser(
        "check", help="run every registered check on a graph and report one verdict"
    )
    check.add_argument("graph", help="path to the API-format workflow JSON to check")
    check.add_argument(
        "--register",
        metavar="PATH",
        help=(
            "the subject's register profile as JSON. Without it check 2 declines, because the "
            "gate's reference must come from the subject rather than from the graph it gates"
        ),
    )
    check.add_argument(
        "--input-dims",
        metavar="WxH",
        help=(
            "the input image's dimensions, e.g. 1072x1024. Check 5's operand is the EFFECTIVE "
            "frame; on an img2img graph the frame lives in the uploaded image, not in the graph"
        ),
    )
    check.add_argument(
        "--saved",
        metavar="PATH",
        help="the sidecar JSON saved before submission, for check 4's saved-vs-submitted compare",
    )
    check.add_argument(
        "--consumer",
        metavar="NODE.INPUT",
        help="the input that must read from the base model when no adapter is declared, e.g. 6.model",
    )
    check.add_argument(
        "--schema",
        metavar="PATH",
        help="node schema as {class_type: [input names]}, enabling check 1's third clause",
    )
    check.add_argument(
        "--family",
        default="qwen",
        help="model family for check 5's frame rule (default: qwen; others are declared absent)",
    )
    check.add_argument("--json", action="store_true", help="emit the structured result as JSON")
    check.add_argument(
        "--debug",
        action="store_true",
        help=(
            "re-raise an internal error with its traceback. Without it an unexpected failure is "
            "reported as a structured error and exits 2 - a stack trace at a user is not an "
            "error message"
        ),
    )

    mcp = sub.add_parser(
        "mcp",
        help="serve the preflight tool over MCP on stdio (a transport, not the production gate)",
        description=(
            "Serve the same in-process preflight() over an MCP stdio transport. Requires the "
            "optional 'mcp' extra. THIS IS NOT THE PRODUCTION GATE: reading a HALT over a "
            "transport and submitting elsewhere is a shell chain with a protocol in the middle."
        ),
    )
    mcp.add_argument(
        "--debug",
        action="store_true",
        help="re-raise an internal error with its traceback instead of reporting it structurally",
    )
    return parser


def _render(result: PreflightResult, graph_path: str, out) -> None:
    print(f"{PROGRAM} {__version__}  {graph_path}", file=out)
    print(f"verdict: {result.verdict.value.upper()}", file=out)
    print("", file=out)

    for outcome in result.outcomes:
        print(f"  check {outcome.number}  {outcome.title}", file=out)
        print(f"    verdict: {outcome.verdict.value.upper()}", file=out)
        if outcome.clauses_evaluated:
            print(f"    evaluated: {', '.join(outcome.clauses_evaluated)}", file=out)
        for defect in outcome.defects:
            label = "HALT" if outcome.verdict is Verdict.HALT else "ADVISORY"
            print(f"    {label} {_locate(defect)}", file=out)
            print(f"      {defect.message}", file=out)
            print(f"      hint: {defect.hint}", file=out)
        for clause, why in outcome.clauses_declined:
            # Declined clauses print on a PASS too. A clause nobody asked is not a clause that
            # passed, and hiding it behind a green verdict is how coverage quietly shrinks.
            print(f"    declined {clause}:", file=out)
            print(f"      {why}", file=out)
        for note in outcome.notes:
            print(f"    note: {note}", file=out)
        print("", file=out)

    not_registered = ", ".join(
        f"{number} ({reason})" for number, reason in result.checks_not_registered
    )
    print(f"  not registered: {not_registered}", file=out)
    print("", file=out)
    if result.verdict is Verdict.HALT:
        print(
            f"  {len(result.defects)} defect(s). Nothing was submitted; nothing spent.", file=out
        )
    elif result.verdict is Verdict.ADVISORY:
        print(
            f"  {len(result.advisories)} advisory finding(s). This is not a halt - a documented "
            "band is documentation, and running outside it may be exactly what was intended.",
            file=out,
        )
    elif result.verdict is Verdict.NOT_APPLICABLE:
        print(
            "  Nothing halted, and at least one check could not be asked. See the declined "
            "clauses above for what would make each one askable.",
            file=out,
        )
    else:
        print(
            "  Nothing halted. PASS means nothing was found by what could be asked - any "
            "declined clauses above are still unasked questions.",
            file=out,
        )


def _locate(defect: Defect) -> str:
    where = ""
    if defect.node_id is not None:
        where = f" [node {defect.node_id}"
        if defect.input_name is not None:
            where += f".{defect.input_name}"
        where += "]"
    return f"{defect.code}{where}"


def main(argv: list[str] | None = None, out=None, err=None) -> int:
    """Run the CLI. Returns the exit code rather than calling sys.exit, so it is testable."""
    out = out if out is not None else sys.stdout
    err = err if err is not None else sys.stderr
    parser = build_parser()

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse's own usage errors and --help/--version
        return int(exc.code or 0)

    try:
        if args.verb == "mcp":
            return _serve_mcp(err)
        return _run_check(args, out, err)
    except UsageError as exc:
        print(f"{PROGRAM}: {exc}", file=err)
        return EXIT_USAGE
    except Exception as exc:  # noqa: BLE001 - the last line before a traceback reaches a user
        # A stack trace is not an error message. It is also not nothing: --debug re-raises so a
        # developer keeps the full frame, and the structured form always names how to get it.
        if getattr(args, "debug", False):
            raise
        print(f"{PROGRAM}: INTERNAL_ERROR: {type(exc).__name__}: {exc}", file=err)
        print(
            "  hint: this is a bug in comfy-preflight, not a defect in your graph. NOTHING was "
            "examined and no claim is made about the graph. Re-run with --debug for the "
            "traceback, and please report it at "
            "https://github.com/mcp-tool-shop-org/comfy-preflight/issues",
            file=err,
        )
        return EXIT_USAGE


def _serve_mcp(err) -> int:
    """Start the stdio MCP server. Imported lazily so `check` never pays for the optional extra."""
    from comfy_preflight import mcp_server

    return mcp_server.main()


def _run_check(args, out, err) -> int:
    graph = _load_graph(args.graph, "graph")
    register = _load_register(args.register) if args.register else None
    dims = _parse_dims(args.input_dims) if args.input_dims else None
    saved = _load_graph(args.saved, "saved graph") if args.saved else None
    consumer = _parse_consumer(args.consumer) if args.consumer else None
    schema = _load_schema(args.schema) if args.schema else None

    try:
        result = preflight(
            graph,
            register,
            dims,
            saved_graph=saved,
            schema=schema,
            consumer_input=consumer,
            family=args.family,
        )
    except PreflightHalt as halt:
        # The halt carries the whole report, which is why there is no second, non-raising entry
        # point for this command to call.
        result = halt.report

    if args.json:
        print(json.dumps(result.to_dict(), indent=2), file=out)
    else:
        _render(result, args.graph, out)

    return EXIT_HALT if result.verdict is Verdict.HALT else EXIT_OK


if __name__ == "__main__":  # pragma: no cover - exercised via the console script
    raise SystemExit(main())
