# Treatment report — the build-out arc

**Executor seat, 2026-08-14.** Repo `mcp-tool-shop-org/comfy-preflight`.
Suite **246 tests**, green under normal interpretation, `python -O`, and `PYTHONOPTIMIZE=1`.
`verify.py` green end to end. CI green. Landing page and handbook live.

Nothing was submitted. No credit was spent. The generation budget the arc sanctioned **went
unspent** — see §3. `E:\AI\facet` was read for the spec and was not modified. No tag, no
publish, no release: those are §7, and they wait on the handback.

> ## ⛔ THIS IS THE TASK-4 HALT
>
> README, handbook, landing page and every other public surface are **FINAL**. The one
> remaining ship-gate line is translations, which are the advisor's to run:
>
> ```
> node E:/AI/polyglot-mcp/scripts/translate-all.mjs E:/AI/comfy-preflight/README.md --cache-clear
> ```
>
> This seat resumes on the advisor's word and executes §7's release order.

---

## 1. Task 1 — the ruling follow-ups

### 1a. Check 5's ÷16 note is an ADVISORY

Amendment 1a's *"PASSES with a note"* predates the verdict vocabulary; with `ADVISORY` in the
merge order the note **is** one, so carrying it as one is a re-labeling. **Nothing about when
this check halts changed**, and one test pins all three rungs against each other so a later edit
cannot quietly promote the preference: ÷8 still halts, ÷16 still returns rather than raises, and
a ÷16-clean frame is still a plain PASS with no finding at all.

What did change is how the finding travels. It was prose in `notes`, which merges into a green
verdict and disappears. It is now a located `Defect` in **`findings`** — the same field name
check 8 uses, because the aggregator reads that one field across every check and an advisory
under a different name would be present in the check's own result and absent from the run's.

**A narrowing that came with it.** The "every finding names its node" exception was wider than it
needed to be. Check 5's defects now carry `node_id` and `input_name` whenever the graph
*declared* the dimension; only the input-image path lacks a node, because there the operand is
the uploaded image and there is genuinely nothing in the graph to point at. A fixture with an
illegal literal width pins that it names `node 9001.width`, so the two paths are told apart by a
test rather than by a sentence.

### 1b. The STUDIO_MEASURED entry kind, shipping empty

`EntryKind` makes the spec's own fork explicit — *"each entry needs a measurement or a
citation"* is two routes to one standard, and a reader should be able to tell at a glance which
route an entry took. `VENDOR` carries `source_url` + `retrieved`. `STUDIO_MEASURED` carries a
`MeasuredRecord`: experiment id, locator, measured date, and the one-line finding in the words of
whoever took it. **The locator is the measured kind's citation** — a measurement with no
retrievable record is the same defect as a band with no card: a number whose authority cannot be
checked by the person it halts.

**The two authorities are mutually exclusive by construction**, which is the non-obvious call. An
entry carrying both would look doubly-sourced while leaving a reader unable to tell which number
came from where.

Proven end to end through the real check, not only through its constructor: a synthetic measured
entry on a synthetic checkpoint advises on the recorded 0.9 and quotes the experiment in the
finding.

**`STUDIO_MEASURED` ships as an empty dict with a test asserting it stays empty.** Ruling an entry
in must therefore also delete the test saying none was ruled in yet — which makes it a deliberate
act rather than a quiet append. The first candidate is named in the code where the next seat will
look.

## 2. Task 2 — shipcheck, and the four lines that needed code

Not a checkbox pass. Hard gates **A–D all pass**; the audit reports 26 checked, 10 skipped with
reasons, 1 unchecked — that one being translations.

Four lines were false and became true:

**B3 — a traceback reached the user.** The CLI now has an outermost guard converting any
unhandled failure into a structured `INTERNAL_ERROR` naming whose fault it is (*"a bug in
comfy-preflight, not a defect in your graph"*), what the caller may conclude (*"NOTHING was
examined"*), and how to get the frame. `--debug` re-raises: suppressing a traceback at a user
must not destroy it for a developer. It exits **2, not 1** — exit 1 says a defect was found in
the graph, and a bug in the gate found nothing.

**D1 — there was no verify script.** `verify.py` is one file rather than a `.ps1` plus a `.sh`,
because two would drift and the CI leg would then verify something the rig does not. Suite in
three interpreter modes → sdist + wheel → **the wheel installed into a clean venv running a real
verb from outside the checkout**, including the recorded 1066 frame having to exit 1. `--version`
is kept as a *labelled floor, not the gate*: it touches no graph, so it stays green through
exactly the packaging defects that break a user. CI and the release workflow run this same
command.

**D3 — no dependency scanning.** Now a `pip-audit --strict` job. See §5 for the two red runs it
took.

**D5/D6/D7 — the npm door this package was designed for did not exist.** It does now.

Two lines are **SKIPPED with reasons** rather than quietly checked: A5 has no dangerous action to
gate (an `--allow-*` flag on a read-only tool advertises a capability it does not have), and D4
requires dependabot, which the org's own Actions rule forbids without an explicit request — a
real standards contradiction already recorded in shipcheck's own audit.

**B2 is checked with a documented deviation, at the line.** The template's 0/1/2/3 does not fit a
gate whose advisory must not stop a shell chain; the deviation is Amendment 3's ratified contract
and says so where a reader will find it.

## 3. Task 3a — the mark, and the spend that did not happen

The kickoff sanctioned one generation spend. **It went unspent, and the enumeration it ordered
first is why.**

`logos/armature/readme.png`'s own commit records that generation was **tried and lost**: the
Director's render was *"better than anything the generated rounds produced."* A node graph is a
worse diffusion candidate than a figure was — exact topology is precisely what a diffusion model
approximates into mush — so the mark is drawn, deterministically, from a committed script. A
brand asset nobody can regenerate is one nobody can correct.

**The form was matched by measurement, not by eye.** Every constant was read off the armature
asset with PIL: canvas 1600×540, background gradient (44,45,51) → (29,30,35), name (231,225,219),
tagline (141,141,149), a 2px rule at (86,88,96), text column starting at x=648 — and the fact
that **armature's rule spans its TAGLINE, not its name**, which is not visible without measuring.
Type is flat Segoe UI Semilight tracked out, per the armature commit's own account of why the
heavy treatment was abandoned.

Type size is the one thing that had to move: *comfy-preflight* is 15 characters against
*armature*'s 8, so the same point size ran off the canvas. The proportions are what is matched.

**The subject carries the founding case.** A node graph in copper wire, with **one link leaving a
node and returning to that same node** — the self-link, drawn brightest. The defect the product
exists for is in the mark.

### The favicon failed, and looking at it is what caught it

The first icon was the wordmark's node-and-loop scaled down. At 16–64px it read unmistakably as a
**hamburger**: a bun over a patty. That is the armature record's "gingerbread man" lesson arriving
in another costume — and it would have shipped if the icon had been assumed rather than rendered
and viewed at true size.

The icon is now a genuine second drawing of a *different* idea from the same product: a node on a
wire arriving at a gate and **stopping short of it**, where the gap is the meaning. Three
strokes, no enclosed shapes to fill in at small size, and it cannot collapse into food.

It also ships `favicon.svg`, fixing the **org-wide 404** the armature seat found: site-theme's
`BaseLayout` hardcodes `<link rel="icon" href="{base}favicon.svg">` with no prop and no head
slot, so every repo on the theme points at a file none of them ship. Verified in the built HTML
and live at the deployed URL.

## 4. Task 3b/3c — the front door

The README opened with a build-state table headed *"read this before trusting a row."* That is a
build report's opening, not a front door's. It now opens where the product does — a provider's
`dry_run` returning `status: validated` — with the internal-process framing gone and the scope
honesty kept: the three unbuilt checks are still named, because that is the product's boundary
rather than internal process.

**The landing page headline was rewritten on the Director's feedback.** It had been *"It will run.
But is it the graph you meant?"* — three problems at once: it duplicated the wordmark verbatim
(the banner directly above says exactly that), *"it"* had no antecedent as the first line on the
page, and it put a riddle where the value proposition goes. Now: **"The wrong graph bills the
same. / Catch it before you submit."** — the stake in five words, the remedy in the accent half.
The Director picked this over provocation-first, benefit-first and descriptive.

Handbook: five pages, amber accent (the mark is copper; the playbook says a warm logo takes
amber). *The adoption contract* and *the envelope table* earn their own pages because they are
where a reader goes wrong — the first carries why a shell step is not a gate, the second carries
how an entry justifies itself **and** the band that is not on the card.

repo-knowledge entry: thesis, architecture, convention, command, next_step, a **warning** carrying
the denoise-band finding so the next seat cannot re-add it from memory, and a relationship to
facet naming it as the governing spec and the fixture source.

## 5. Defects found by running things

**a. `pip-audit` went red twice, and the second fix could never have worked.** `--strict` on the
installed environment failed with *"comfy-preflight: Dependency not found on PyPI and could not
be audited"* — the project itself is not on PyPI. Adding `--skip-editable` then failed with
*"distribution marked as editable"*, because `--strict` treats **any** skipped distribution as an
error: the two flags are mutually exclusive by design. The fix audits the **declared** dependency
surface derived from `pyproject.toml`, which removes the project from the question entirely,
keeps `--strict` at full force for every real dependency, and audits what a user is promised
rather than what one runner happened to resolve.

**b. The favicon read as food** (§3), found by rendering it at 16/32/64px on both a light and a
dark plate and looking.

**c. Pagefind builds to `dist/pagefind/`, not `dist/_pagefind/`.** The handbook playbook's halt
criterion names the underscore path, which is stale for the current Starlight. The search index
is real — 6 HTML files indexed — and live at `/comfy-preflight/pagefind/pagefind.js`. **Reported
against the playbook, not worked around here.**

**d. Two defects on the README header, found by the Director reading the rendered page** — not
by any check in this arc, and both were mine.

*The logo carried a tagline this arc had already rejected.* It read *"It will run. But is it the
graph you meant?"* — the exact sentence cut from the landing-page hero for being a riddle whose
*"it"* has no antecedent. The hero was fixed and the permanent brand asset was left carrying the
discarded draft, so the two front doors disagreed with each other. **A wording decision has to
propagate to every surface that carries it, and nothing in this arc checked that.**

*The mark floated in its canvas, and measuring said so precisely:* 59.3% of canvas height against
the reference's 79.1%, margins of 88/131 against 55/57, sitting 22px above centre. **The cause
was orientation, not scale** — armature's figure is portrait (344×427), which is how it fills the
height; a left-to-right node graph is landscape and could never fill more than ~59% before
colliding with the text column at x=648. Scaling it only moved the imbalance (a second pass hit
75.7% height but pushed the centre to 228 and the margins to 24/106). The graph is now a vertical
spine, and the drawing is **cropped to its own ink bbox and pasted centred** rather than centring
the drawing box — because the box is not the picture, and the self-loop and port pips push the
ink off-centre inside it. Final: margins 44/45, centre 269.0 against 270.0, 83.3% of height, left
margin 228 against the reference's 228.

The self-link took three tries. A wide arc read as a speech balloon; a short bezier collapsed
into a cramped stub; the third drew a 34° scribble because interpolating start→end took the
**short way** round the circle — silent, and it looks like a rendering bug rather than a maths
bug. It is now a near-closed circle swept the long way, with the arrowhead derived from the
path's own final tangent so it survives retuning.

*And the badges were broken in public:* `npm invalid` and `pypi package or version not found`
rendered red, because neither package is published — which the treatment playbook forbids in as
many words. Removed until the release commit, when they will resolve.

**The lesson, stated against myself:** every other defect in this section was caught by an
instrument I ran. These two shipped to a public surface and were caught by a person looking at
it. The measurement that diagnosed the composition existed the whole time — I had used it to
*match* the reference and never re-ran it to *check my own output*.

**e. shipcheck under-detects this repo as `[all] [pypi]`.** It reads `pyproject.toml` and cannot
see that the repo also ships an npm launcher, a console script and an MCP server. Nine applicable
lines would have been skipped. The tags are corrected by hand in `SHIP_GATE.md` with that reason
stated at the top. **Reported against shipcheck's detector, not worked around silently.**

## 6. The release path, and the one thing this seat cannot do

The org's proven shape for a Python tool going to npm is facet's: **one workflow, both
registries**, plus the binaries the launcher fetches. That is what `release.yml` does — PyPI via
`pypa/gh-action-pypi-publish` and npm via `npm publish --provenance`, both OIDC trusted
publishing, **and the repo holds no token** (`gh secret list` is empty, and it must stay that
way).

The binary is the **CLI carrying the new `mcp` verb**, so one artifact serves both doors and
`npx @mcptoolshop/comfy-preflight mcp` reaches the stdio server on a machine with no Python. Its
smoke test runs a verb and requires the 1066 halt to still exit 1 — a binary that only ever
returned 0 would not prove the gate survived freezing.

**The version gate has four sites** (`pyproject.toml`, `__init__.py`, `package.json`,
`bin/comfy-preflight.js`) plus the pinned tag, and a **local test catches drift before the tag
does** — because the launcher pins an exact tag, and drift there does not fail loudly, it ships a
wrapper that 404s at a user's `npx`.

**Trusted publishing could not be configured from this seat** — it is an account action on each
registry. The Director configured **PyPI's pending publisher** during this arc and showed the
binding: repository `mcp-tool-shop-org/comfy-preflight`, workflow **`release.yml`**, environment
*Any*. Both halves match what is committed: the workflow is named `release.yml` (**it must never
be renamed — npm masks that failure as a 404 rather than an auth error**) and declares no
`environment:`. The npm-side trusted publisher is not readable from this seat; the release will
prove it.

## 7. What happens on the advisor's word

The release order, which is law:

1. **Translations already staged** — the advisor's run, then heading parity / no two-candidate
   headings / nav bars intact / line endings measured in Python.
2. **ONE release commit** carrying `README.md` + `README.*.md` together.
3. **npm + PyPI via OIDC**, no tokens — triggered by the tag, not by a manual publish.
4. **Tag by SHA**, pointing at that release commit.
5. **The GitHub Release**, cut by the workflow with the binaries and dists attached — the launcher
   fetches checksums and binary from that tag at run time, so the release must exist with its
   assets before anyone can `npx`.
6. **Verify by installing the published package and running a VERB from outside a checkout** —
   never `--help` — and read the **simple index**, not the cached aggregate.

## 8. Compensators

| action | irreversible? | compensator | owner |
|---|---|---|---|
| the commits on `main` this arc | no | `git revert` | this seat |
| `git push` to comfy-preflight | partly — history is public | `git revert` + push; the arc is additive | this seat |
| **push to `mcp-tool-shop-org/brand`** | partly — public, and the README's image URL depends on it | `gh api -X DELETE` the logo path (or PR revert), **paired with** reverting the README commit that references it, or the image 404s | this seat / advisor |
| `gh repo edit` description/homepage/topics | no | `--remove-topic` per tag; prior description restorable from this report | advisor |
| GitHub Pages deploy | no | revert and push; Pages redeploys, CDN cache 1–10 min | advisor |
| repo-knowledge insert | no | `rk note --delete` per note; re-scan is idempotent | advisor |
| **npm publish** | **yes** | `npm deprecate` + a fixed patch. Cannot unpublish after 72h, cannot reuse a version ever | **the Director** |
| **PyPI publish** | **yes** | yank the release; the version number is burned permanently | **the Director** |
| **tag + GitHub Release** | **yes** | `gh release delete` + `git push --delete origin <tag>`; anyone who fetched keeps their copy | **the Director** |
| **submitting a graph** | **yes** | **not performed by this arc.** Nothing here contacts the API | — |

## 9. Standards compliance

| standard | score | evidence |
|---|---|---|
| PIN_PER_STEP | 3 | four version sites gated locally and again at tag-push; the launcher pins an exact tag and asset name; envelope entries pin parameter, band, quote, URL and retrieval date, with the constructor refusing a row missing any; the brand asset is regenerable from a committed script; `verify.py` is the single pinned gate CI, release and rig all run |
| ANDON_AUTHORITY | 3 | hard gates A–D bind and translations remain honestly unchecked rather than pre-ticked; CI went red twice and was fixed rather than routed around; the arc halts here for the handback instead of proceeding to an irreversible publish; no function or flag is skip-shaped, checked by reading signatures and the parser |
| NAMED_COMPENSATORS | 3 | §8, including the brand-repo push whose compensator must be *paired* with a README revert or the image 404s, and honest that four rows are the Director's and were not performed |
| DECOMPOSE_BY_SECRETS | 3 | the registry keeps one adapter per check so no check's requirements leak into another's; the envelope table is data beside the code at documentation cadence; the two entry KINDS separate vendor authority from studio authority and are mutually exclusive; brand generation lives outside `src/` and never reaches a wheel |
| UNCERTAINTY_GATED_HUMANS | 3 | the headline was routed to the Director as a taste call with four real directions rather than decided unilaterally after his feedback; §5c and §5d are reported against their owners rather than worked around; the measured entry kind ships empty pending a ruling; the contrastive frame is stated throughout — *you probably expected a generation spend; I drew it, because this form's own record says generation lost* |
| EXTERNAL_VERIFIER | 2 | the brand form was verified by measuring the reference asset rather than eyeballing it; the favicon was verified by rendering at true size and looking, which is the only thing that caught the hamburger; the live site was verified by fetching the deployed HTML, not by trusting the build; CI was verified by reading the failing logs; `verify.py` verifies the wheel from outside the checkout, where the packaging defects actually live. **Marked down from 3 because of §5d**: the brand asset was measured against the reference to BUILD it and never re-measured to CHECK it, so two defects reached a public surface and a person caught them. The instrument existed and was not pointed at my own output. Remediation: the logo script now reports its own bbox/margins/centre against the reference constants, and any future asset change re-runs that comparison before it is pushed |

## 10. State

- **Built and green:** checks 1, 2, 4, 5, 8; the aggregator over a registry; CLI; MCP stdio;
  246 tests in three interpreter modes; `verify.py` end to end; CI green.
- **Shipped surfaces:** logo + favicons in the brand repo, landing page, five-page handbook,
  GitHub metadata, repo-knowledge entry.
- **Ready and not fired:** `release.yml`, the npm launcher, the version gate. PyPI trusted
  publisher confirmed; npm's unverified from this seat.
- **Blocked on the advisor:** translations (§7 step 1), then the release order.
- **Open for the advisor:** §5c (playbook's stale pagefind path), §5e (shipcheck's detector),
  and whether a `STUDIO_MEASURED` entry gets ruled in from E35's sweep.
