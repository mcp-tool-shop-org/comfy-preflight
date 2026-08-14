---
title: Getting started
description: Install comfy-preflight by any of three doors, and run it on a real graph.
sidebar:
  order: 1
---

## Three doors, and which one you want

| door | command | when |
|---|---|---|
| **npx** | `npx @mcptoolshop/comfy-preflight check graph.json` | you want to look at a graph and have no Python |
| **pip** | `pip install comfy-preflight` | you are going to call it from Python — which is the production path |
| **MCP** | `pip install "comfy-preflight[mcp]"` | an agent session is hand-driving a graph |

The npx door downloads a PyInstaller binary from the GitHub Release and **verifies its SHA256**
against the checksums published in that same release before running it. No Python is needed on
the machine.

Supported: **Python ≥ 3.11**; binaries for **linux-x64** and **win-x64**. macOS binaries are not
built — the org drops macOS runners at roughly ten times Linux cost — so macOS users install via
`pip`, which works everywhere.

## Your first run

```bash
npx @mcptoolshop/comfy-preflight check graph.json
```

On any of the 70 recorded graphs this repo tests against, that prints:

```
verdict: NOT_APPLICABLE
```

**That is the correct answer, and it is worth understanding before anything else.** Two checks
could not be asked: check 4 has no saved sidecar to compare against, and check 5 has no frame to
look at, because every recorded graph is img2img and the frame lives in the uploaded image rather
than in the graph. Reporting PASS there would claim work that was never done.

Give it the missing operands and the run becomes answerable:

```bash
npx @mcptoolshop/comfy-preflight check graph.json \
  --input-dims 1072x1024 \
  --saved saved-sidecar.json \
  --register subject.json \
  --consumer 6.model
```

## The flags, and what each one unlocks

Every optional flag is an **askability** parameter: supplying it makes a clause askable, and
omitting it makes a check decline and *name what it could not see*. None of them turns a check
off, and there is no flag that does.

| flag | unlocks |
|---|---|
| `--input-dims WxH` | check 5. The operand is the **input image's** dimensions — this package never decodes an image, so you supply them |
| `--saved PATH` | check 4's saved-vs-submitted comparison |
| `--register PATH` | check 2. The gate's reference must come from the subject, not from the graph it gates |
| `--consumer NODE.INPUT` | check 2's consumer-link clause, e.g. `6.model` |
| `--schema PATH` | check 1's third clause, as `{class_type: [input names]}` |
| `--json` | the structured result, which is what the MCP tool returns too |
| `--debug` | re-raise an internal error with its traceback instead of reporting it structurally |

## The register profile

```json
{
  "declared": false,
  "known_cards": [
    "house_style_v2.safetensors",
    "other-namespace__house_style_v2.safetensors"
  ]
}
```

`declared: false` is the no-adapter condition, and the claim it makes is *not* "the weight is
0.0" — it is that no loader node and no card reference exist anywhere in the graph.

For a subject that **does** use an adapter:

```json
{
  "declared": true,
  "card": "house_style_v2.safetensors",
  "weight": 0.75,
  "card_aliases": ["other-namespace__house_style_v2.safetensors"]
}
```

`card_aliases` exists because the recorded corpus carries **two names for one adapter** — the
same weights re-imported under a different cloud-side namespace, differing in the whole basename.
Equivalence is declared, never inferred: a prefix-stripping heuristic would also accept a
genuinely wrong card whose name happened to share a tail.

**Unknown keys are rejected rather than ignored.** A misspelled `known_card` silently dropped
would empty the vocabulary, and check 2 would then decline the very clause the misspelling was
meant to enable — a typo turning a gate off quietly.

## Verifying your install

```bash
python verify.py
```

Runs the suite in all three interpreter modes, builds sdist and wheel, then installs the wheel
into a clean venv and runs a real verb **from outside the checkout**. `--version` is kept in that
script as a labelled floor, not the gate: it touches no graph, so it stays green through exactly
the packaging defects that break a user.
