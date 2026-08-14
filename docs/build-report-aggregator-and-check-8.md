# Build report — the aggregator arc, and check 8

**Executor seat, 2026-08-14.** Repo `mcp-tool-shop-org/comfy-preflight`.
Suite **228 tests**, green under normal interpretation, `python -O`, and `PYTHONOPTIMIZE=1`.

Nothing was submitted. No credit was spent. The API was not contacted at all — not even
`dry_run`. Nothing under `E:\AI\training` was read or written. `E:\AI\facet` was read for the
spec and the grounding and was not modified. No npm publish, no tag, no repo-settings change.

Scope was Amendment 2's arc: the `preflight()` aggregator, the CLI verb, the MCP surface, and
check 8. Checks 3, 6 and 7 remain out for the standing reasons.

> ## ⚠ THE HEADLINE — a gate fired, and it is reported rather than tuned past
>
> **Amendment 2 rules that check 8's day-one entry carries the Qwen ControlNet-Union
> checkpoint's "img2img denoise band per its card, verified live."** The verification ran at
> this seat. **The band is not on the card.**
>
> That is the whole finding, and §2 is its evidence. The rest of the arc is built and green.

---

## 1. What was built

| piece | state |
|---|---|
| `Verdict.ADVISORY` + `merge_verdicts` | built — the ratified order, with the surprising rung pinned |
| `registry.py` — the check registry | built — the composition surface, with both extension directions tested |
| `aggregate.py` — `preflight()` | built — one entry point, one raise, full report on the halt |
| `envelope.py` — the cited envelope table | built — one checkpoint, citation enforced in the constructor |
| `checks/c8_envelope.py` — check 8 | built — ADVISORY only, proven three ways |
| `cli.py` + `[project.scripts]` | built — exit codes established, verified against the installed script |
| `mcp_server.py` — stdio | built — verified as a real subprocess against a stdio client |

`preflight(graph, register_profile, input_dims=None)` is Amendment 2's signature exactly.
`register_profile` is required and may be `None`, deliberately not defaulted: passing `None` is
a caller *stating* it has no subject profile, and a default would let the same situation arrive
by omission. Those are different facts and this repo's declined clauses exist to keep them apart.

## 2. THE FINDING — check 8's commissioned band is not on the card it cites

### What was expected

Amendment 2, verbatim: *"Day one ships exactly one checkpoint — `Qwen-Image-InstantX-ControlNet-Union`,
img2img denoise ~0.10–0.50 per its card, verified live at the seat."* The source is the E35
research grounding, agent 1, finding 8:

> InstantX Qwen-Image-ControlNet-Union model card —
> https://huggingface.co/InstantX/Qwen-Image-ControlNet-Union — vendor's own recommended img2img
> denoise range for canny conditioning is ~0.10–0.50; the pipeline's 0.92 sits 2–9x above the
> checkpoint's own tested range.

### What the live card says

Retrieved **2026-08-14**, from the cited URL, by **two independent fetches** — the rendered model
page and `raw/main/README.md`. Both agree:

| the card documents | value | kind |
|---|---|---|
| `controlnet_conditioning_scale` | **`[0.8, 1.0]`**, stated for each of canny, soft edge, depth and pose | an explicit recommended **range** |
| `controlnet_conditioning_scale` | `1.0` | the inference example |
| `true_cfg_scale` | `4.0` | the inference example |
| `num_inference_steps` | `30` | the inference example |
| **img2img denoise / strength** | — | **absent. The card publishes no denoise or strength range at all.** |

A public web search for the 0.10–0.50 figure surfaces nothing on that card either. The
**Inpainting** sibling card (`InstantX/Qwen-Image-ControlNet-Inpainting`, loaded by 24 of the 70
recorded graphs) was also opened at this seat: it documents no denoise range either.

The grounding's *other* Union card — InstantX/Shakker-Labs **FLUX.1-dev-Controlnet-Union**, whose
canny examples run at 0.5 — is a **different checkpoint**, and the dispatch flagged in advance
that its numbers do not enter a Qwen entry. They did not.

### What shipped instead, and why

The denoise band **does not ship**. The table's own discipline decides it, and Amendment 2 states
that discipline in the same paragraph that names the band: *"the envelope table ships with no
entry populated from memory."* A band this check cannot retrieve is one it must not judge
against.

What ships:

1. **The band the card does document** — `controlnet_conditioning_scale ∈ [0.8, 1.0]` — with its
   quote, URL and retrieval date.
2. **A declared absence for `denoise`**, which reports the graph's value and says plainly that
   the check cannot judge it. On the recorded graphs:

   ```
   declined envelope_bands.denoise:
     this graph runs denoise at node 13 = 0.92, and this check CANNOT say whether that is in or
     out of band for Qwen-Image-InstantX-ControlNet-Union.safetensors: the card documents NO
     img2img denoise or strength range. Verified against the live source 2026-08-14 by two
     independent fetches [...] Source consulted:
     https://huggingface.co/InstantX/Qwen-Image-ControlNet-Union (retrieved 2026-08-14)
   ```

   **Reporting the value it cannot judge is the honest half of the finding; inventing a band to
   judge it against would be the dishonest half.** The 0.92 still arrives in front of the caller
   at the moment it is cheap, which is what Amendment 2 says the check is for — it arrives as a
   named blind spot rather than as a verdict.

3. `true_cfg_scale=4.0` and `num_inference_steps=30` are recorded as **notes, not bands**. They
   are example values in a code snippet. An example is one point, and inferring a range around it
   would be inventing the measurement this table exists to avoid.

### The consequence, stated plainly, and it is the advisor's to rule on

**Check 8 as built does not flag the 0.92 that motivated it.** It reports it and declines to
judge it.

This is the same shape as Amendment 1's "fourth thing," arriving at check 8 — *the defect the
check exists for is not reachable by the operand the check was specified with*. There it was
that check 5's declared-frame operand could not have caught a frame derived upstream of the
graph. Here it is that the cited envelope does not contain the parameter the incident turned on.
Both were found by measuring rather than by reading, and both change the check rather than the
measurement.

Three readings, and this seat picks none of them:

- **A.** The absence *is* the finding, and the check is correct as built. A parameter with no
  published band is a parameter the vendor gives no guidance on, and saying so at submit time —
  with the source and the date — is real information a caller did not have before. Under this
  reading nothing further is needed.
- **B.** The envelope table is the wrong reference for denoise, and the right one is the
  **empirical** record: E33→E35 measured what 0.92 produced, and the studio's own repair arc is a
  stronger source than a vendor card. That would be a different kind of entry — *measured here*
  rather than *documented there* — and it needs the advisor's word on whether this table may
  carry studio measurements beside vendor citations.
- **C.** The grounding's finding 8 is itself the defect, and belongs back in facet as a
  correction. A cited practitioner claim that the cited source does not contain is exactly the
  class the studio's verifier standards exist to catch.

**A and B are not exclusive.** C is a report against facet's tree, which is read-only to this
seat, so it is filed here rather than fixed — see §6.

## 3. The aggregator, and the three decisions it forced

**One entry point.** A non-raising `preflight_report()` for the CLI and MCP to call would be a
skip flag with a different name: a caller on the submit path could reach for it and get a value
back where the gate should have stopped them. So `PreflightHalt` grew an optional `report` and
the renderers catch the halt. A test parses `aggregate.py` and fails if a second public function
appears — the property is enforced by reading the code, because no set of inputs proves the
absence of a function.

**One raise, carrying everything.** Each registry adapter catches its *own* check's halt so the
remaining checks still run, and the aggregator re-raises once with every defect. Without that, a
graph with a self-link reports the self-link and nothing else, and the caller fixes, reruns,
finds the next — a gate run five times before an act it exists to gate once. The adapters catch
`PreflightHalt` and **only** `PreflightHalt`: a bare `except Exception` would turn a bug in a
check into a quiet non-result, which is the gate-that-cannot-fail shape.

**PASS does not mean every clause was asked**, and this was forced into the open by a test
assertion of mine that was wrong. Two clauses decline on any clean run: check 1's
`undeclared_input` needs a schema from a live ComfyUI, and check 8's `denoise` is the absence
above. The alternative — any declined clause forcing the aggregate to NOT_APPLICABLE — was
considered and rejected: it would make PASS unreachable in every environment without a live
ComfyUI, and *a verdict that never occurs carries no information*. The unasked questions stay
listed in `declined` instead, and the CLI prints them **on a passing run**, because a clause
nobody asked is not a clause that passed.

### The registry earns its place, in both directions

A hardcoded list makes "which checks ran" unanswerable from the result, so a check silently
dropping out looks exactly like a check that passed. Two tests pin the property: a check added to
the registry runs with **no edit to `preflight()`**, and a check removed from it is **visible in
the result**. Check 8 is the live proof — it was specified after the aggregator and landed as one
registry line plus one adapter.

Each check gets an adapter rather than a shared signature. The checks decompose by what they
know and their signatures say so; forcing one signature on all of them would push every check's
requirements into every other check's argument list, which is the coupling decompose-by-secrets
exists to prevent. The seam sits in one file instead of smeared across five.

## 4. The exit-code contract, established rather than inherited

This repo had no CLI, so there was no convention to enumerate. These follow from its laws:

| code | meaning | the law it follows from |
|---|---|---|
| 0 | nothing halted — PASS, ADVISORY or NOT_APPLICABLE, each **named** in the output | see below |
| 1 | HALT | the gate fired |
| 2 | usage or input error | nothing was examined, so nothing can be claimed about a graph |

**ADVISORY exits 0, and this is the load-bearing one.** A nonzero status stops a `&&` chain,
which would make the advisory a halt in every shell that runs one — reinstating exactly what
Amendment 2 ruled out. **NOT_APPLICABLE exits 0 for the inverse reason**: all 70 recorded graphs
are img2img, so a run without `--input-dims` declines check 5, and a gate that exits nonzero
across a whole corpus of correct work is a gate that gets disabled by the third person who hits
it. Both stay named in the output and in `--json`; a caller wanting to gate on an advisory reads
the verdict, not the exit status.

**Exit 2 is not exit 1.** A missing file, unparseable JSON, or a UI-export graph is a usage
error. Exit 1 tells a caller the gate examined a graph; when nothing parsed, nothing was
examined, and saying otherwise is the false confidence this repo keeps paying for.

## 5. Four defects found by running things rather than by reading them

**a. `mcp>=1.0` would have installed a version that ImportErrors.** The surface is built on
`mcp.server.MCPServer`; the installed SDK is 2.0.0, and 2.0 removed the 1.x
`mcp.server.fastmcp.FastMCP`. This was found by installing the SDK and introspecting it before
writing a line against it — the same discipline check 8's table is held to, applied to an API.
Corrected to `>=2.0` and pinned by a test.

**b. The absolute-path guard matched every URL scheme.** `https://` ends in `s:/` and `s` is a
letter, so `ABSOLUTE_PATH` fired on the first test file to carry a citation — a guard meant to
catch leaked local paths failing on a source URL, which is the opposite of its job. A drive
letter is exactly one letter; the pattern now requires that no letter precede it. A guard that
rejects citations teaches the next seat to drop the citation.

**c. Printed em dashes rendered as `?` on a Windows console.** Found by running the installed
console script rather than only `main()` — cp1252 cannot encode them. Runtime strings are now
ASCII, checked by encoding the whole CLI rendering across four runs. Docstrings stay free.

**d. `errors.py` named a guard file that does not exist** (`tests/test_gates_survive_O.py`; the
guard is `tests/test_no_assert_in_library.py`). Small, but it is a claim about this repo that a
reader would act on.

## 6. Findings reported, not fixed

**Against facet — the E35 grounding's finding 8.** `docs/research/E35-speck-research-grounding.md`
attributes a "~0.10–0.50 recommended img2img denoise" to the InstantX Qwen ControlNet-Union model
card. The live card does not contain it (§2). The synthesis section carries the same claim
(*"The InstantX control checkpoint's own documented img2img band is 0.10–0.50; our 0.92 is 2–9×
above it"*), so the correction is not confined to one line. **facet's tree is read-only to this
seat; this is a report, not an edit.** Its resolution is the advisor's — including whether the
0.92-was-out-of-band conclusion in the E35 arc survives it, which is a question about that arc
and not about this repo.

**Check 8's operand coverage is narrower than the incident.** §2's three readings. Not this
seat's call.

**The recorded corpus reaches PASS on check 8's shipped band.** 46 of 70 graphs run
`ControlNetApplyAdvanced.strength = 0.9`, inside the documented `[0.8, 1.0]`. So the
no-false-advisory leg is real recorded work rather than a synthetic pass — but it also means the
shipped band has never fired on anything in this corpus except a constructed mutation.

**Check 5's ÷16 note and check 8's advisory are the same shape with different verdicts.** Check 5
returns `PASS` with an advisory note for a ÷16-short frame (Amendment 1a's ratified wording:
*"it PASSES with a note"*), while check 8 returns `ADVISORY`. This seat did **not** promote check
5, because re-specifying a ratified check is not the executor's act. The note is still carried
into the aggregate result and printed. Whether the two should align is a question for the
advisor; nothing is lost either way today.

## 7. Compensators for this arc

| action | irreversible? | compensator | post-rollback state | owner |
|---|---|---|---|---|
| running any check, the aggregator, the CLI or the MCP tool | no | read-only on the graph, register and table | unchanged | — |
| the commits on `main` this arc | no | `git revert`; nothing published, no tag, no npm | prior state | this seat |
| `git push` to `mcp-tool-shop-org/comfy-preflight` | **partly** — history is public once pushed | `git revert` and push the revert; the arc is additive, so nothing prior is destroyed | prior behaviour restored, history retains both | this seat |
| installing `mcp` into the repo's local `.venv` | no | `pip uninstall mcp`; `.venv/` is gitignored and rig-local | unchanged | this seat |
| reading facet's spec and grounding | no | read-only; nothing under `E:\AI\facet` was written | unchanged | — |
| **submitting a graph** | **yes** | **not performed by this arc.** Nothing here contacts the API | — | — |
| npm publish | **yes** | **not performed.** Gated on the Director's word | — | the Director |
| tag / GitHub release | **yes** | **not performed.** Gated on the Director's word | — | the Director |
| repo-settings change | **yes** | **not performed.** Gated on the Director's word | — | the Director |

## 8. Standards compliance

| standard | score | evidence |
|---|---|---|
| PIN_PER_STEP | 3 | every number here names its instrument and scope. The envelope entry pins parameter, band, quote, source URL and retrieval date, and the constructor refuses a row missing any of them. The `mcp` bound is pinned to the API actually introspected, by a test |
| ANDON_AUTHORITY | 3 | the aggregator raises once with everything and has exactly one entry point, enforced by parsing its own module. No function takes a skip-shaped parameter, checked by reading signatures. §2's gate fired and its band is reported rather than written in. The CLI's exit codes are chosen so an advisory cannot become a halt through a shell |
| NAMED_COMPENSATORS | 3 | complete in §7, including the partly-irreversible push and the local SDK install, and honest that the three Director-gated actions were simply not performed |
| DECOMPOSE_BY_SECRETS | 3 | the registry is the seam: one adapter per check, each knowing exactly one signature, so no check's requirements leak into another's. The envelope table is data beside the code at documentation cadence, like check 5's family table. The MCP and CLI are transports holding no opinion, pinned by a byte-identity test |
| UNCERTAINTY_GATED_HUMANS | 3 | §2 gives three readings and picks none; §6 routes four findings out with the reason each is not this seat's. Check 8 advises and never halts, so a human decides. Declined clauses print on a passing run so a reader sees what was not asked. The contrastive frame is stated: *you probably expected a 0.10–0.50 denoise band; I shipped a declared absence, because the card does not carry it* |
| EXTERNAL_VERIFIER | 3 | the arc's central act was verifying a dispatch's own cited claim against the live source and reporting that it does not hold. The card was fetched twice by independent routes and cross-checked by search; the sibling checkpoint's card was opened too. Four further defects (§5) were found by running the installed console script and the real stdio server rather than by reading the code that produced them |

## 9. State

- **Built:** checks 1 (2 clauses of 3), 2, 4, 5, 8; the `preflight()` aggregator over a check
  registry; the CLI verb; the MCP stdio surface.
- **Not built:** checks 3, 6, 7 — named in `registry.NOT_REGISTERED` with their reasons, so the
  boundary lives in the code and not only in the README.
- **228 tests** across three interpreter modes. The AST scans keep `src/` free of bare `assert`
  (one declared exception), keep `PreflightHalt` out of check 8 entirely, keep `mcp` out of
  module-load imports, and keep a second entry point out of the aggregator.
- **Verified by running, not only by testing:** the installed console script's four exit codes,
  and a stdio client handshake against the server as a real subprocess.
- **Open for the advisor:** §2's three readings; the facet correction in §6; whether check 5's
  ÷16 note should become an ADVISORY alongside check 8's.
