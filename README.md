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
| # | check | halts on | state |
|---|---|---|---|
| 1 | Link topology | a node input referencing its own node; a link to a node id not in the graph; an input the class does not declare | ✅ **built** — 2 clauses of 3; `undeclared_input` needs an injected schema and declines without one |
| 2 | Inverted register scan | a declared register that does not match the graph's actual construction — **in both directions** | ✅ **built** — both directions |
| 3 | Recipe-vs-profile agreement, by value | a parameter reaching the graph that disagrees with the subject profile | **not built** |
| 4 | Graph-saved-is-graph-submitted | saved sidecar and submitted payload differing **as parsed graphs** | ✅ **built** |
| 5 | Generator-legal frame | a dimension the effective frame's VAE cannot decode at | ✅ **built** — Qwen only; every other family declared-absent |
| 6 | Estimate before submit | a missing or unread credit estimate | **not built** — transport-side |
| 7 | Anchor reproduction | a recorded graph that no longer rebuilds from its recorded inputs | **not built** |

Every built check passes on **all 70 recorded graphs** (the no-false-halt leg) and fires on a
one-edit mutation of a real one, so the passing case and the failing case differ by exactly the
edit under test. **103 tests, green under normal interpretation, `python -O`, and
`PYTHONOPTIMIZE=1`.**

### What the built checks do NOT cover

- **Check 1's third clause** (*an input the class does not declare*) requires a node schema.
  ComfyUI serves one at `/object_info`; this package makes no network calls, so the schema is a
  parameter. Without it the clause returns NOT_APPLICABLE **naming itself** — and it is
  deliberately not inferred from the corpus, because deriving a gate's reference from the thing
  it gates makes it a tautology. A class absent from a supplied schema is reported as unknown
  rather than assumed to pass.
- **Check 1 does not detect orphans** (a node whose output nothing reads). A graph may
  legitimately carry one; it is a candidate clause, not an omission.
- **Check 5 knows one family.** Qwen's ÷8 is measured. `sdxl`, `sd15`, `flux`, `wan`, `hunyuan`
  and `chroma` are **declared absent** and return NOT_APPLICABLE rather than borrowing another
  family's divisor — an unmeasured entry either halts correct work or passes the defect it was
  added for.
- **Check 5 returns NOT_APPLICABLE on all 70 recorded graphs** unless the caller supplies the
  input image's dimensions. That is the honest result on an img2img corpus, not a gap: see below.
- **Check 4 answers the value question, not the byte question.** Both live in this repo and they
  are different: the fixture manifest asserts byte-identity with the recorded artifact, and check
  4 asserts that no *value* moved between save and submit.

## Check 1 — link topology, and the case that started all this

```python
from comfy_preflight.graph import Graph
from comfy_preflight.checks import check_link_topology

check_link_topology(Graph.from_api_dict(graph_json))
```

```
check_1_link_topology HALT (1 defect(s)):
  - SELF_LINK [node 14.samples]: input reads slot 0 of its own node (14); a node cannot
    be its own producer
    hint: repoint this input at the node that actually produces the value. A provider
    dry_run has returned `validated` on exactly this defect, so a passing pre-flight
    elsewhere is not evidence against it
```

That is the recorded incident, reproduced by repointing `node 14.samples` from `['13', 0]` to
`['14', 0]` in the graph that was actually in it. **The corpus carries 0 self-links and 0
dangling links across all 70 graphs** — so there is no naturally-occurring failing fixture, and
the break is constructed by one documented edit.

## Check 5 — the effective frame, not the declared one

`1066 / 8 = 133.25` encodes to 133 latent columns and decodes to **1064**, putting every output
2 px off its control image and breaking every downstream pairing.

**The defect happened upstream of the graph.** The record is explicit that the 1066 was derived
correctly from a mesh bounding box; the image was rendered at that width and uploaded, and the
graph never declared it. So a check that read graph literals could not have caught the incident
that motivates it. The operand is the frame the run will actually produce:

| case | operand | verdict |
|---|---|---|
| the graph declares dimensions | the literals | PASS / HALT |
| img2img and the caller has the input | **the input image's dimensions** | PASS / HALT |
| neither | — | NOT_APPLICABLE, naming what it could not see |

```python
check_generator_legal_frame(graph, family="qwen", input_dimensions=(1072, 1024))   # PASS
check_generator_legal_frame(graph, family="qwen", input_dimensions=(1066, 1024))   # HALT
check_generator_legal_frame(graph, family="qwen")                                  # NOT_APPLICABLE
```

`input_dimensions` is a parameter, not an architecture: **the production gate runs in-process on
the submit path, where the image is in hand by construction**, and the CLI degrades to
NOT_APPLICABLE. This package does not decode images — dimensions in, verdict out.

**÷8 halts; ÷16 advises.** The constraint is *"÷8 is the floor, prefer ÷16"* — a floor and a
preference, not two floors. 1064 is ÷8-legal and ÷16-short: it passes with an advisory note.
Promoting the preference to a halt would fire on every legal ÷8 frame.

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

```python
from comfy_preflight.graph import Graph
from comfy_preflight.register import AdapterRegister
from comfy_preflight.checks import check_register_scan

# The photo-real pass: this subject is deliberately built WITHOUT the style adapter.
register = AdapterRegister(declared=False, known_cards=frozenset({"house_style_v2.safetensors"}))

check_register_scan(
    Graph.from_api_dict(graph_json),
    register,
    consumer_input=("6", "model"),   # the node that must read straight from the base model
)
# -> CheckResult(verdict=PASS, ...) or raises PreflightHalt naming the node
```

A halt names what it found and where:

```
check_2_inverted_register_scan HALT (2 defect(s)):
  - ADAPTER_LOADER_PRESENT_BUT_NOT_DECLARED [node 5]: the register declares no style
    adapter, but node 5 is an adapter loader (LoraLoaderModelOnly). The claim being
    asserted is that no loader node exists - not that its weight is 0.0
    hint: remove the loader node and route the consumer directly from the base model, ...
  - CONSUMER_READS_THROUGH_LOADER [node 6.model]: no adapter is declared, but 6.model
    reads from adapter loader node 5
```

**The result reports which clauses it evaluated and which it declined.** Three clauses run:
`loader_nodes` (structural, always), `consumer_link` (needs a named consumer), and
`card_vocabulary` (needs the register's declared card names). A check that quietly skips a
clause it could not evaluate would report PASS for work it never did, so a declined clause is
named in the result with the reason.

**Card names are declared, never sniffed.** Two measurements shaped this. Scanning for any
`.safetensors` string matches the base model, CLIP, VAE and ControlNet on **all 70** recorded
graphs — including all 43 with no adapter — so the naive form halts every correct build. And
the corpus carries **two names for one adapter** (the same weights re-imported under a
different cloud-side namespace, differing in the whole basename), so a single declared card
string halts a correct build too. Hence `card_aliases`: equivalence is declared, because a
prefix-stripping heuristic would also accept a genuinely wrong card whose name shared a tail.

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
from comfy_preflight.checks import check_register_scan

# Inside the function that submits. Not in a shell step before it.
check_register_scan(graph, register, consumer_input=consumer)   # raises PreflightHalt
submit(graph)                                                   # only reached if nothing raised
```

No check takes a `skip`, `force`, `warn_only` or `enabled` parameter, and a test reads each
signature to keep it that way rather than trusting the docstring.

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
