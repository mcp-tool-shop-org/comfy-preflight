# comfy-preflight

**A gate that runs on a ComfyUI workflow graph in the seconds before it is submitted, and
halts a submission that would spend credits producing a known-wrong result.**

It does not submit. It does not fix your graph. It names the defect and the node, and the
caller decides.

---

## Why this exists

> **A Comfy Cloud `dry_run` PASS does not prove link sanity.**
> A hand-retyped payload with a self-referencing node link — `VAEDecode.samples = ["14", 0]`,
> the node pointing at itself — returned `status: validated`.

The provider's validator answers *is this graph well-formed enough to run.* It does not
answer *is this the graph you meant.* Every check here lives in that gap, and each one was
paid for by a run that got past `dry_run`.

The framing that matters: **submitting a graph is the one irreversible act in a generation
pipeline.** A completed cloud job is billed. The compensator is *cancel it if it is still
queued, otherwise none* — which is not much of a compensator. So this is a compensator you
run **before** instead of after.

## Build state — read this before trusting a row

This repo is **under construction**. The table is the honest state, not a roadmap.

| # | check | halts on | state |
|---|---|---|---|
| 1 | Link topology | a node input referencing its own node; a link to a node id not in the graph; an input the class does not declare | **not built** |
| 2 | Inverted register scan | a declared register that does not match the graph's actual construction — **in both directions** | **not built** |
| 3 | Recipe-vs-profile agreement, by value | a parameter reaching the graph that disagrees with the subject profile | **not built** |
| 4 | Graph-saved-is-graph-submitted | saved sidecar and submitted payload differing **as parsed graphs** | **not built** |
| 5 | Generator-legal frame | a dimension the model family's VAE cannot decode at | **specification open** — see below |
| 6 | Estimate before submit | a missing or unread credit estimate | **not built** |
| 7 | Anchor reproduction | a recorded graph that no longer rebuilds from its recorded inputs | **not built** |

**Check 5's operand is missing from every fixture we have.** Across 70 recorded workflow
graphs there are zero `width`/`height`/`resolution` inputs and no `EmptyLatentImage` node —
every one is an img2img topology (`LoadImage → VAEEncode → KSampler → VAEDecode`) whose frame
is inherited from the uploaded image rather than declared in the graph. The defect this check
exists for (a width of 1066 decoding as 1064 on a ÷8 VAE) happened in frame-derivation code
*upstream of the graph*. A check that finds nothing to check and returns PASS is not a check,
so check 5 ships only once its verdict set can express *frame-not-in-graph* honestly.

## Check 2 — the inverted register scan

The check that names the method, and the reason the tool is not just a linter.

When a subject's register declares **no style adapter**, the claim being asserted is *not*
"the weight is 0.0". It is that **no loader node and no adapter card reference exist anywhere
in the graph** — asserted by walking every node and every input, plus the link assertion that
the downstream consumer reads directly from the base model.

> *A weight of 0.0 is not a weight of zero on a loaded card; it is no card.*

**And it asserts the mirror image.** A decided positive weight with **no loader node** is
*silently inert*: the run completes, costs money, and produces base-model output while every
log line says the adapter was requested. That direction produces no signal a human could
notice, which is exactly where a gate earns its place over a person looking.

## What it does NOT do

- **It does not submit.** Nothing here spends a credit.
- **It does not fix a graph.** No rewiring, no auto-inserted loader, no rounded frame. A
  graph that a gate repaired is a graph nobody reviewed.
- **It does not judge the output.** It never sees one.
- **It does not evaluate prompts.** Whether the terms are right is a different tool's job.
- **It does not model VRAM or predict fit.** Measured dead end: peak was 31.7–32.0 GB across
  three runs regardless of the reserve setting or the desktop baseline, because the runtime
  stages to fill whatever it sees free; freeing 6.5 GB made the working set grow 6.1 GB.
  `--reserve-vram` and `--disable-smart-memory` are falsified as levers. A fit prediction
  here would sell a number the record already refuted.
- **It does not replace `dry_run`.** It runs *beside* it.

## The adoption contract

**Call it in-process on the submit path. There is no skip flag.**

The check lives inside the tool that performs the irreversible step. A preflight in a shell
chain before a submit is a *transport, not a guard* — in the incident that produced this rule,
47,020 texels were committed after a gate had already fired, because a PowerShell chain walked
past a failing exit code. Nobody decided to proceed; the construction was incapable of
stopping.

```python
from comfy_preflight import preflight   # once check surfaces land

preflight(graph, profile=profile)       # raises PreflightHalt; no skip parameter exists
submit(graph)                           # only reached if nothing raised
```

**Every gate `raise`s. None is a bare `assert`.** `python -O` and `PYTHONOPTIMIZE=1` delete
`assert` silently and execution continues past it — in the repo that produced this rule, 87
gates were removable by an environment variable, including every one in the write path. CI
runs the suite under `-O` to prove the gates survive it.

The standalone CLI exists for development. It is not the production gate.

## Security

No network calls, no credentials, no telemetry. It reads a graph and a profile from disk or
memory and returns a verdict. See [SECURITY.md](SECURITY.md).

## License

MIT — see [LICENSE](LICENSE).
