---
title: The checks
description: What each check asserts, what it declines to answer, and the incident that bought it.
sidebar:
  order: 2
---

Five checks are built and composed. Three from the original table are not, and they are named
here rather than quietly missing — a report that cannot enumerate its own coverage makes a check
silently dropping out look exactly like a check that passed.

| # | check | halts on |
|---|---|---|
| 1 | Link topology | a node input reading its own node; a link to a node id not in the graph |
| 2 | Inverted register scan | a declared register that does not match the graph's construction — **both directions** |
| 4 | Saved-is-submitted | the saved sidecar and the submitted payload differing as parsed graphs |
| 5 | Generator-legal frame | a dimension the effective frame's VAE cannot decode at |
| 8 | Declared envelope | **nothing. It never halts** — out-of-band is an ADVISORY |

Not built: **3** (recipe-vs-profile agreement — no subject-profile fixture exists), **6**
(estimate before submit — transport-side, no graph-structural operand), **7** (anchor
reproduction — needs the graph *builder*, and the corpus holds outputs rather than the scripts
that made them).

## Check 1 — link topology

The founding case. A hand-retyped payload carried `VAEDecode.samples = ["14", 0]` — node 14's
input reading node 14 — and the provider's `dry_run` returned `status: validated`.

```
check_1_link_topology HALT (1 defect(s)):
  - SELF_LINK [node 14.samples]: input reads slot 0 of its own node (14); a node cannot
    be its own producer
    hint: repoint this input at the node that actually produces the value. A provider
    dry_run has returned `validated` on exactly this defect, so a passing pre-flight
    elsewhere is not evidence against it
```

**A self-link is reported once, not also as dangling.** Its target *is* in the graph, so the
dangling clause skips a link already reported. Two defects for one edit reads as two problems.

**Links are distinguished structurally, not guessed.** `["14", 0]` is a link; `["a", "b"]` and
`[1, 2]` and `["14", 0, 0]` are not. Without that discrimination a legitimate two-element list
value would be misread as a wire and reported dangling.

The third clause — *an input the class does not declare* — needs a node schema. ComfyUI serves
one at `/object_info`; this package makes no network calls, so the schema is a parameter. Without
it the clause **declines and names itself**. It is deliberately not inferred from the corpus:
deriving a gate's reference from the thing it gates makes it a tautology that passes review
because the numbers look fine.

**Orphan detection is out of scope, named rather than missing.** A graph may legitimately carry a
node whose output nothing reads.

## Check 2 — the inverted register scan

The check that names the method, and the reason this is not just a linter.

When a subject's register declares **no style adapter**, the claim being asserted is *not* "the
weight is 0.0". It is that **no loader node and no adapter card reference exist anywhere in the
graph** — asserted by walking every node and every input, plus the link assertion that the
downstream consumer reads directly from the base model.

> A weight of 0.0 is not a weight of zero on a loaded card; it is no card.

**And it asserts the mirror image.** A decided positive weight with **no loader node** is
*silently inert*: the run completes, costs money, and produces base-model output while every log
line says the adapter was requested. That direction produces no signal a human could notice,
which is exactly where a gate earns its place over a person looking.

The check reports which of its three clauses it evaluated and which it declined — `loader_nodes`
(structural, always), `consumer_link` (needs a named consumer), `card_vocabulary` (needs the
register's declared cards). A check that quietly skipped a clause would report PASS for work it
never did.

**Card names are declared, never sniffed.** Scanning for any `.safetensors` string matches the
base model, CLIP, VAE and ControlNet on **all 70** recorded graphs — including all 43 with no
adapter — so the naive form halts every correct build on day one.

## Check 4 — saved is submitted

Compared **as parsed graphs**: node id sets, class types, input name sets, link targets and
literal values. Never as text — *a JSON re-dump can differ in whitespace without a value moving*,
so comparing text produces false halts while comparing parsed graphs produces true ones.

Numbers compare numerically, so a seed rendered `770700` or `770700.0` has not moved. A
comparison strict about int-versus-float would report a change where none occurred.

**Two different questions live in this repo and are kept apart in the code.** The fixture manifest
asks the BYTE question — *is this file the artifact it was copied from*. Check 4 asks the VALUE
question — *did a parameter move between save and submit*. Conflating them produced a red CI leg
on git's line-ending conversion.

## Check 5 — the effective frame, not the declared one

`1066 / 8 = 133.25` encodes to 133 latent columns and decodes to **1064**, putting every output
2 px off its control image and breaking every downstream pairing.

**The defect happened upstream of the graph.** The 1066 was derived correctly from a mesh bounding
box, the image was rendered at that width and uploaded, and the graph never declared it. So a
check that read graph literals could not have caught the incident that motivates it.

| case | operand | verdict |
|---|---|---|
| the graph declares dimensions | the literals | PASS / HALT |
| img2img and the caller has the input | **the input image's dimensions** | PASS / HALT |
| neither | — | NOT_APPLICABLE, naming what it could not see |

**÷8 halts; ÷16 advises.** The constraint is *"÷8 is the floor, prefer ÷16"* — a floor and a
preference, not two floors. 1064 is ÷8-legal and ÷16-short: it returns **ADVISORY**, never a halt.
Promoting the preference would fire on every legal ÷8 frame.

**Check 5 knows one family.** Qwen's ÷8 is measured. `sdxl`, `sd15`, `flux`, `wan`, `hunyuan` and
`chroma` are **declared absent** and return NOT_APPLICABLE rather than borrowing another family's
divisor — an unmeasured entry either halts correct work or passes the defect it was added for.

## Check 8 — the declared envelope

Advisory, never a halt. It gets [its own page](../envelope-table/), because what it does *not*
contain is as important as what it does.

## How the verdicts merge

`HALT > ADVISORY > NOT_APPLICABLE > PASS`.

The rung that surprises people is **NOT_APPLICABLE outranking PASS**, and it is deliberate: a run
where one check declined has not checked everything, and reporting PASS would let the declined
clause vanish behind the passing ones. Declining is louder than passing.

**PASS does not mean every clause was asked.** Two decline on any clean run — check 1's
`undeclared_input` needs a live ComfyUI's schema, and check 8's `denoise` is a parameter its card
documents no band for. The unasked questions stay listed rather than folded into a green verdict,
and the CLI prints them **on a passing run**.
