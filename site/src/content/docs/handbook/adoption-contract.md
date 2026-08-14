---
title: The adoption contract
description: Call it in-process on the submit path. There is no skip flag, and the CLI is not the gate.
sidebar:
  order: 3
---

## The rule

**Call `preflight()` in-process on the submit path. There is no skip flag.**

```python
from comfy_preflight import preflight

# Inside the function that submits. Not in a shell step before it.
preflight(graph, register, input_dims=(width, height))   # raises PreflightHalt
submit(graph)                                            # only reached if nothing raised
```

## Why a shell step is not a gate

*The check lives inside the tool that performs the irreversible step.* A preflight in a shell
chain before a submit is a **transport, not a guard** — and that is not a hypothetical. In the
incident that produced this rule, **47,020 texels were committed after a gate had already
fired**, because a PowerShell chain walked past a failing exit code. Nobody decided to proceed.
The construction was incapable of stopping.

**The CLI and the MCP server are both transports.** Reading a HALT from either and then
submitting from somewhere else is that same shell chain with a nicer interface. They exist for
developing a graph by hand; the production gate is the call above.

## There is exactly one entry point

A second, non-raising `preflight_report()` for the CLI and MCP to call would be **a skip flag
under another name** — a caller on the submit path could reach for it and get a value back where
the gate should have stopped them.

So `preflight()` raises, and **the halt carries the whole report** as `PreflightHalt.report`. The
renderers catch it and print; the submit path lets it propagate. A test parses the aggregator's
own module and fails if a second public function ever appears, because no set of inputs proves
the absence of a function.

```python
try:
    result = preflight(graph, register, input_dims=dims)
except PreflightHalt as halt:
    result = halt.report      # the full structured result, for rendering
```

## One raise, carrying everything

A halting check does not stop the others from running. Each registry adapter catches **its own**
check's halt, and the aggregator re-raises once with every defect from every check.

Without that, a graph with a self-link reports the self-link and nothing else — and the caller
fixes it, reruns, finds the next. That is a gate run five times before an act it exists to gate
once.

The adapters catch `PreflightHalt` and **only** `PreflightHalt`. A bare `except Exception` would
turn a bug in a check into a quiet non-result, which is the gate-that-cannot-fail shape.

## No skip, anywhere

No function in this package takes a `skip`, `force`, `warn_only`, `ignore` or `enabled`
parameter, and **tests read the actual signatures** rather than trusting the docstrings. The CLI
exposes no such flag either, and a test reads the parser's real option strings.

## Every gate raises; none is a bare assert

`python -O` and `PYTHONOPTIMIZE=1` delete `assert` statements silently and execution continues
past them. In the repo that produced this rule, **87 gates were removable by an environment
variable** — including every one in the write path.

So every gate here `raise`s, an AST scan keeps `src/` free of bare `assert` with one declared
exception, and CI runs the whole suite three times: normally, under `-O`, and under
`PYTHONOPTIMIZE=1`.

## The exit codes

| code | meaning |
|---|---|
| `0` | nothing halted — PASS, ADVISORY or NOT_APPLICABLE, **each named in the output** |
| `1` | HALT |
| `2` | **nothing was examined** — bad arguments, unreadable file, unparseable graph, or an internal error |

**ADVISORY exits 0 on purpose.** A nonzero status stops a `&&` chain, which would make the
advisory a halt in every shell that runs one — reinstating exactly what the advisory ruling
removed.

**NOT_APPLICABLE exits 0 for the inverse reason.** All 70 recorded graphs are img2img, so a run
without `--input-dims` declines check 5; a gate that exits nonzero across a whole corpus of
correct work is a gate that gets disabled by the third person who hits it.

Both stay named in the output and in `--json`, so a caller that wants to gate on an advisory
reads the verdict rather than the exit status. **The exit code is a transport signal; the verdict
is the finding.**

**Exit 2 is one code for two causes on purpose.** A bad path and a bug in this package differ in
whose fault they are — and the message says which — but not in what the caller may conclude,
which is *nothing about the graph*. The distinction an exit code should carry is examined /
not examined.

## The MCP surface is a transport, not a second implementation

The tool returns `preflight()`'s structured result **verbatim**; a test asserts byte-identity with
what the library returns. A HALT is a *successful* call returning `{"verdict": "halt", ...}` —
reporting it as a protocol error would throw away the structure the caller needs and leave a
client retrying a call that keeps succeeding at finding the same defect.

The graph arrives inline rather than as a path, so the server adds no filesystem-read surface to
a package whose threat model says its inputs reach neither the filesystem nor the network.

## Compensators

| action | irreversible? | compensator |
|---|---|---|
| running any check, the CLI, or the MCP tool | no | read-only on the graph, register and table |
| writing the saved sidecar (check 4) | no | delete it; it is derived from the graph in hand |
| **submitting a graph** | **yes — credits spend** | **cancel the job if it is still queued; otherwise none.** A completed cloud job is billed |

**That last row is the whole product.** Submission is the irreversible act with no real undo, and
a preflight is a compensator you run BEFORE instead of after — which is why it must be in-process,
and why there is no way to turn it off.
