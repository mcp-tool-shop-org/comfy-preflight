<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/comfy-preflight/readme.png" alt="comfy-preflight" width="600">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/comfy-preflight/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/comfy-preflight/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.npmjs.com/package/@mcptoolshop/comfy-preflight"><img src="https://img.shields.io/npm/v/@mcptoolshop/comfy-preflight?color=cb3837&label=npm" alt="npm"></a>
  <a href="https://pypi.org/project/comfy-preflight/"><img src="https://img.shields.io/pypi/v/comfy-preflight?color=3775a9&label=pypi" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/comfy-preflight/"><img src="https://img.shields.io/badge/landing%20page-live-2ea043" alt="Landing page"></a>
</p>

<p align="center">
  <strong>A gate that runs on a ComfyUI workflow graph in the seconds before it is submitted,</strong><br>
  and halts a submission that would spend credits producing a known-wrong result.<br>
  It does not submit. It does not fix your graph.
</p>

---

## The gap it lives in

> **A Comfy Cloud `dry_run` PASS does not prove link sanity.**
> A hand-retyped payload with a self-referencing node link — `VAEDecode.samples = ["14", 0]`,
> the node pointing at itself — returned `status: validated`.

The provider's validator answers *is this graph well-formed enough to run.* It does not answer
*is this the graph you meant.* Every check here lives in that gap, and each one was paid for by
a run that got past `dry_run`.

**Submission is the irreversible act with no real undo, and a preflight is a compensator you run
BEFORE instead of after.** A completed cloud job is billed; the only compensator afterwards is
*cancel it if it is still queued, otherwise none.* That is the whole argument for this package.

## Install

```bash
npx @mcptoolshop/comfy-preflight check graph.json   # no Python needed
pip install comfy-preflight                          # for the in-process gate
pip install "comfy-preflight[mcp]"                   # + the MCP stdio server
```

The npx launcher downloads a binary from this repo's GitHub Release and **verifies its SHA256**
against the checksums in that same release before running it. Python ≥ 3.11; binaries for
linux-x64 and win-x64 (macOS installs via `pip`).

## Use it

**The production gate — in-process, on the submit path:**

```python
from comfy_preflight import preflight

# Inside the function that submits. Not in a shell step before it.
preflight(graph, register, input_dims=(width, height))   # raises PreflightHalt
submit(graph)                                            # only reached if nothing raised
```

**The development door:**

```bash
comfy-preflight check graph.json \
  --input-dims 1072x1024 --register subject.json --saved sidecar.json --json
```

| exit | meaning |
|---|---|
| `0` | nothing halted — PASS, ADVISORY or NOT_APPLICABLE, **each named in the output** |
| `1` | HALT |
| `2` | **nothing was examined** — bad arguments, unreadable file, or an internal error |

ADVISORY exits `0` on purpose: a nonzero status stops a `&&` chain, which would turn an advisory
into a halt in every shell that runs one.

## What it checks

| # | check | halts on |
|---|---|---|
| 1 | **Link topology** | a node input reading its own node; a link to a node id not in the graph |
| 2 | **The inverted register scan** | a declared register that does not match the graph's construction — **in both directions** |
| 4 | **Saved-is-submitted** | the saved sidecar and the submitted payload differing **as parsed graphs** |
| 5 | **Generator-legal frame** | a dimension the effective frame's VAE cannot decode at |
| 8 | **Declared envelope** | **nothing — it never halts.** Out-of-band is an ADVISORY |

Three checks from the original design are **not built**, and are named rather than quietly
missing: recipe-vs-profile agreement (no subject-profile fixture exists), estimate-before-submit
(transport-side — no graph-structural operand), and anchor reproduction (needs the graph
*builder*; the corpus holds outputs, not the scripts that made them).

### Check 2 — the one that names the method

When a subject's register declares **no style adapter**, the claim being asserted is *not* "the
weight is 0.0". It is that **no loader node and no adapter card reference exist anywhere in the
graph**.

> *A weight of 0.0 is not a weight of zero on a loaded card; it is no card.*

**And it asserts the mirror image.** A decided positive weight with **no loader node** is
*silently inert*: the run completes, costs money, and produces base-model output while every log
line says the adapter was requested. That direction produces no signal a human could notice —
which is exactly where a gate earns its place over a person looking.

### Check 5 — the effective frame, not the declared one

`1066 / 8 = 133.25` encodes to 133 latent columns and decodes to **1064**, putting every output
2 px off its control image and breaking every downstream pairing.

**The defect happened upstream of the graph.** The 1066 was derived correctly from a mesh, the
image was rendered at that width and uploaded, and the graph never declared it — so a check
reading graph literals could not have caught the incident that motivates it. The operand is the
frame the run will actually produce, which on an img2img graph is the input image's dimensions.

÷8 halts. ÷16 advises. A floor and a preference, not two floors.

### Check 8 — advisory, and honest about what it cannot say

For each checkpoint the graph loads, parameters are compared against a **cited** envelope table.
Every entry carries its band, source URL, retrieval date and a quote of the card's own words —
and the constructor refuses to build an entry that does not.

The day-one entry is `Qwen-Image-InstantX-ControlNet-Union`. It carries the
`controlnet_conditioning_scale` band its card documents, and a **declared absence** for denoise,
because that card publishes no denoise range at all — verified against the live card rather than
recalled. So a run on a graph at `denoise=0.92` reports the 0.92, names the parameter, and says
plainly that it cannot judge it and why.

Reporting the value it cannot judge is the honest half of the finding. Inventing a band to judge
it against would be the dishonest half.

## The adoption contract

**Call it in-process on the submit path. There is no skip flag.**

*The check lives inside the tool that performs the irreversible step.* A preflight in a shell
chain before a submit is a **transport, not a guard** — in the incident that produced this rule,
47,020 texels were committed after a gate had already fired, because a PowerShell chain walked
past a failing exit code. Nobody decided to proceed; the construction was incapable of stopping.

**The CLI and the MCP server are both transports, not gates.** Reading a HALT from either and
then submitting from somewhere else is that same chain with a nicer interface.

No function here takes a `skip`, `force`, `warn_only` or `enabled` parameter, and tests read each
signature rather than trusting the docs. **Every gate `raise`s; none is a bare `assert`** —
`python -O` deletes `assert` silently, and CI runs the whole suite under `-O` and
`PYTHONOPTIMIZE=1` to prove the gates survive it.

## Over MCP

```bash
python -m comfy_preflight.mcp_server     # stdio
npx @mcptoolshop/comfy-preflight mcp     # same server, no Python required
```

One tool, `preflight`, returning the same structured result the library returns — a test asserts
byte-identity. A HALT is a *successful* call returning `{"verdict": "halt", ...}`, because
reporting it as a protocol error would throw away the structure the caller needs.

## Security

No network calls, no credentials, no telemetry, and it writes nothing anywhere. It reads a graph
and a profile, and returns a verdict. Full threat model — data touched, data *not* touched, and
the permissions required — in [SECURITY.md](SECURITY.md).

## Documentation

📖 **[The handbook](https://mcp-tool-shop-org.github.io/comfy-preflight/handbook/)** — getting
started, every check in detail, the adoption contract, and the envelope table.

## License

MIT — see [LICENSE](LICENSE).

<p align="center">
  Built by <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
</p>
