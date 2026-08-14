---
title: comfy-preflight
description: A gate that runs on a ComfyUI workflow graph in the seconds before it is submitted.
sidebar:
  order: 0
---

**A gate that runs on a ComfyUI workflow graph in the seconds before it is submitted, and halts
a submission that would spend credits producing a known-wrong result.**

It does not submit. It does not fix your graph. It names the defect and the node, and the caller
decides.

## Why it exists

> A Comfy Cloud `dry_run` PASS does not prove link sanity. A hand-retyped payload with a
> self-referencing node link — `VAEDecode.samples = ["14", 0]`, the node pointing at itself —
> returned `status: validated`.

The provider's validator answers *is this graph well-formed enough to run.* It does not answer
*is this the graph you meant.* Every check here lives in that gap, and each one was paid for by a
run that got past `dry_run`.

## The framing that governs everything else

**Submission is the irreversible act with no real undo, and a preflight is a compensator you run
BEFORE instead of after.**

A completed cloud job is billed. The only compensator afterwards is *cancel it if it is still
queued, otherwise none* — which is not much of a compensator. So this package runs before the
irreversible step, and everything about it follows from that: it reaches nothing it does not
need, writes nothing anywhere, and cannot be turned off at a call site.

## What it does not do

- **It does not submit.** Nothing here spends a credit or contacts a provider.
- **It does not fix a graph.** No rewiring, no auto-inserted loader, no rounded frame. A graph a
  gate repaired is a graph nobody reviewed.
- **It does not judge the output.** It never sees one.
- **It does not model VRAM or predict fit.** Measured dead end: peak was 31.7–32.0 GB across
  three runs regardless of the reserve setting, because the runtime stages to fill whatever it
  sees free — freeing 6.5 GB made the working set grow 6.1 GB. A fit prediction here would sell
  a number the record already refuted.
- **It does not replace `dry_run`.** It runs *beside* it.

## Where to go next

| page | what's in it |
|---|---|
| [Getting started](../getting-started/) | install by three doors, and the first run |
| [The checks](../the-checks/) | what each check asserts, and what it declines to |
| [The adoption contract](../adoption-contract/) | why the gate must be called in-process, and the exit codes |
| [The envelope table](../envelope-table/) | check 8's cited data, and the band that is not on the card |
