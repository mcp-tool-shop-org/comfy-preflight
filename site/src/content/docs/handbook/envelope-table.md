---
title: The envelope table
description: Check 8's cited data — how an entry justifies itself, and the band that is not on the card.
sidebar:
  order: 4
---

Check 8 compares a graph's parameters against a **cited** envelope table, per checkpoint loaded.
Out of band is an **ADVISORY, never a HALT**. No entry for a checkpoint is **NOT_APPLICABLE,
naming the checkpoint it could not see.**

## Why it advises, and why that is a ruling rather than a softness

The studio ran an out-of-band denoise **deliberately**, and the Director approved the register it
produced. A documented band is documentation, not a gate. A check that halted on it would refuse
correct work, and a gate that halts correct work gets disabled by the third person who hits it.

The advisory's job is to make an out-of-band fact **visible at the moment it is cheap** — before
the credits are spent — not to forbid it.

This is enforced rather than asserted: check 8 never raises, proven over all 70 recorded graphs,
over a deliberately far-out-of-band mutation, **and by an AST scan proving the module contains no
`PreflightHalt` raise at all** — because no finite set of inputs proves the absence of a branch.

## How an entry justifies itself

The rule is *each entry needs a measurement or a citation*. Those are two routes to one standard,
and the table makes the fork explicit so a reader can tell at a glance which route an entry took.

| kind | authority | carries |
|---|---|---|
| `VENDOR` | the checkpoint's publisher documents the band | `source_url` + `retrieved` date + a **quote of the card's own words** |
| `STUDIO_MEASURED` | the publisher documents nothing and the studio measured it | a record locator: experiment id, path, measured date, and the finding |

**The two are mutually exclusive by construction.** An entry carrying both would look
doubly-sourced while leaving a reader unable to tell which number came from where.

The constructor **refuses to build an unjustified entry** — the discipline made mechanical rather
than documented, because a table whose citations are checked only by review acquires a recalled
number the first time someone is in a hurry.

**Parameter names are mapped, not matched.** A card documents a library API argument
(`controlnet_conditioning_scale`); a graph carries a node input (`strength`). The equivalence is
*declared* in the entry, because a parameter matched by name alone would let a band judge a knob
the card never governed.

**Bands follow the checkpoint's wires.** Only nodes that actually read from *that* checkpoint's
loader are examined, so a graph carrying two control checkpoints does not have one entry's band
applied to the other's apply node.

## What ships today

Exactly one checkpoint: **`Qwen-Image-InstantX-ControlNet-Union`**, kind `VENDOR`.

| parameter | band | source |
|---|---|---|
| `strength` (the card's `controlnet_conditioning_scale`) | `[0.8, 1.0]` | [the model card](https://huggingface.co/InstantX/Qwen-Image-ControlNet-Union), retrieved 2026-08-14 |

The `STUDIO_MEASURED` kind ships **empty**. The capability exists; no measured entry lands until
one is ruled in, and a test asserts the emptiness — so ruling one in must also delete the test
saying none was ruled in yet, which makes it a deliberate act rather than a quiet append.

## ⚠ The band that is not on the card

This check was commissioned to carry that checkpoint's **img2img denoise band of ~0.10–0.50**,
attributed to the model card by a research grounding.

**Verified against the live card at build time, 2026-08-14, by two independent fetches — the
rendered model page and `raw/main/README.md` — and that band is not on it.** The card documents
`controlnet_conditioning_scale` in `[0.8, 1.0]` for each of its four control types, and shows
`true_cfg_scale=4.0` / `num_inference_steps=30` as example values in an inference snippet. It
publishes **no img2img denoise or strength range at all**. (A third independent fetch at a later
seat agreed.)

So the denoise band **does not ship**. The table's own discipline decides it: an entry populated
from memory is worse than a missing one, and a band this check cannot retrieve is one it must not
judge against.

What ships instead is a **declared absence**, so a run on a real graph reports:

```
declined envelope_bands.denoise:
  this graph runs denoise at node 13 = 0.92, and this check CANNOT say whether that is in
  or out of band for Qwen-Image-InstantX-ControlNet-Union.safetensors: the card documents
  NO img2img denoise or strength range. [...] Source consulted:
  https://huggingface.co/InstantX/Qwen-Image-ControlNet-Union (retrieved 2026-08-14)
```

**Reporting the value it cannot judge is the honest half of the finding. Inventing a band to
judge it against would be the dishonest half.** The 0.92 still reaches the caller at the moment
it is cheap — as a named blind spot rather than as a verdict.

`true_cfg_scale=4.0` and `num_inference_steps=30` are recorded as **notes, not bands**. An
example is one point, and inferring a range around it would be inventing the measurement this
table exists to avoid.

## Adding an entry

Open the live card. Read it. Then add a row carrying its parameter, band, source URL, retrieval
date and a quote of what it actually said — or, if the vendor documents nothing, a
`STUDIO_MEASURED` entry pointing at the experiment record that measured it.

Do not add a row from memory, from a summary, or from a research report. **A citation that
becomes load-bearing is resolved against its live source at the moment it lands** — that is the
law this table earned, one seat late.
