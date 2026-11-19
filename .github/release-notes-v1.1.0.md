# comfy-preflight 1.1.0

The first two `STUDIO_MEASURED` envelope entries, measured in August 2026 and unreleased until now. The envelope table shipped empty of measured entries at 1.0.0.

### Added
- **The second `STUDIO_MEASURED` envelope entry — E35's quantisation trigger on
  `qwen-image-edit-2509`** (facet E35 Ruling 11, 2026-08-15; its own ruling, per *one ruling per
  entry, always*). The first entry on a **second checkpoint** — Amendment 2's "exactly one
  checkpoint" bound day one, and 1.0.0 has shipped. Three measured rungs on the input image's
  unique-colour count: `2,620 → edit encode CORRUPT` (the native Workbench render, four times),
  `5,046 → clean` (recorded clay resized locally — killed traversal), `5,336 → clean` (native
  render lanczos round-tripped — killed framing). **The fault is deterministic**: a verbatim
  re-submission came back pixel-identical, 0 differing pixels of 1,053,696, while the files'
  sha256 differ. One lanczos round-trip at native framing repairs it; framing, traversal, alpha,
  bit depth, colour type, seed and the turbo switch are each exonerated by measurement. **A
  trigger, not a mechanism**, and **no threshold is stated between 2,620 and 5,046** — where the
  boundary lies was never measured. Record locator: experiment E35,
  `docs/experiments/E35-D1-report.md` + `E35-E-report.md` sections D1/E1/E2, ruled in at
  `E35-ruling.md` Rulings 9 and 11, measured 2026-08-15.
- ⚠ **A boundary shipped as documentation rather than as a check.** That entry's operand is a
  property of the referenced **image file**, not a graph input, and comfy-preflight does not
  decode images (check 5's standing boundary: *dimensions in, verdict out*). So check 8
  **declines** on this ladder by construction, on every graph — *"the rungs were reported against
  nothing rather than against a guess"* — and the entry lands in the table and the handbook
  anyway, because the table is documentation before it is a lookup. **No check was invented to
  reach it.** The named future shape, uncommissioned, is check 5's: an injected
  `input_unique_colours` parameter on the submit path. Pinned by a can-fail test that fires if a
  later seat wires the property in or turns the decline into a guess.
- **The first `STUDIO_MEASURED` envelope entry — E35's denoise sweep on
  `Qwen-Image-InstantX-ControlNet-Union`** (spec Amendment 5, ruled by the Director at Gate R,
  2026-08-14). The capability shipped empty at 1.0.0 because no measured entry ships until the
  advisor rules a specific measurement in; this is that ruling, carrying four measured rungs —
  `0.92 → register C* 23.77 / 0.50% reverted (Director-ruled HOLD)`, `0.85 → 10.00 / 5.01%`,
  `0.80 → 3.91 / 36.66%`, `0.72 → 1.89 / 56.00%, census-0 by register destruction` — its
  validity envelope (the recipe the rungs hold at), and its record locator: experiment E35,
  `docs/experiments/E35-clean-twins-report.md` section "2b — the denoise sweep", measured
  2026-08-14. The finding it carries is the sweep's own: **the register dies before the specks
  do.**
- **`MeasuredLadder` and `Rung`** — the measured kind's answer to `Band`, and a separate shape
  for a reason. A band is a range a publisher endorses, so silence inside it is correct; a
  ladder endorses nothing, so **every value gets the nearest measured rungs**, including the
  value the Director held. Nothing is interpolated between rungs, and a value off the end of the
  sweep is reported as the nearest reading with the fact that it is outside stated in the
  finding.
- Finding code `PARAMETER_HAS_A_STUDIO_MEASUREMENT`, and the clause `envelope_measured.<param>`
  in check 8's evaluated/declined accounting.

### Changed
- **The envelope table is keyed by `(checkpoint, parameter)` rather than by checkpoint**, with a
  tuple of entries per key, built by `envelope.index(*entries)`. The old one-entry-per-checkpoint
  dict could not hold this ruling: the vendor's declared absence for denoise and the studio's
  measurement of denoise are both about the same checkpoint, and the second would have
  overwritten the first in silence. Two entries on one key is now the ruled shape — one vendor
  voice, one measured voice; two entries of the **same** kind on one key is refused at
  construction. `entries_for(table, checkpoint)` resolves all of a checkpoint's entries.
- **A graph on the Qwen Union checkpoint now aggregates to `ADVISORY` rather than `PASS`.** The
  studio measured the denoise this route runs, so check 8 has something to report on every run —
  including at the recorded, Director-held 0.92. This is the ruling's intended consequence, not
  a defect being reported: `defects` stays empty, **ADVISORY still exits `0`**, and no shell
  chain or submit path changes behaviour. What changes is that the caller is told, before the
  spend, what happens to the register at the value they are about to run.
- The vendor entry's **declared absence for denoise stays**, and still reports the value it
  cannot judge with its own citation. The measurement answers that absence; it does not erase
  it. Both authorities report on `denoise` in the same run, in their own voices.
- `EnvelopeEntry` now refuses cross-authority shapes: a VENDOR entry may not carry measured
  rungs, a STUDIO_MEASURED entry may not declare a documented absence (that is a claim about a
  publisher's card), and no entry may both band and declare-absent one parameter.

### Fixed
- Two CLI exit-code tests asserted `"verdict: PASS" in out`, which the rendering also prints on
  every per-check line — so they passed on check 1's line regardless of the aggregate verdict.
  They now assert the aggregate verdict line itself.

### Removed
- The test pinning `STUDIO_MEASURED` empty, **deleted deliberately as its own design required**:
  it existed so that ruling a measurement in could never be a quiet append, and whoever added
  the first entry had to delete it and say who ruled and when. Replaced by the entry's own
  can-fail advisory legs (0.92 cites E35 and the HOLD; 0.72 names the register destruction) and
  a count assertion — one ruling per entry, always.
