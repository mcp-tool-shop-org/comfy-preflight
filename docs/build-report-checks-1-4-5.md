# Build report — checks 1, 4 and 5 (the graph-structural group)

**Executor seat, 2026-08-09.** Repo `mcp-tool-shop-org/comfy-preflight` at `8f9f0ad`.
Suite **107 tests**, green under normal interpretation, `python -O`, and `PYTHONOPTIMIZE=1`.
CI **31338962553** (resolved by reading it, not written from expectation).

Nothing was submitted. No credit was spent. The API was not contacted at all — not even
`dry_run`. Nothing under `E:\AI\training` was read at test time or written at any time. No
package was installed into `E:\AI-Models\trellis2-env`.

Scope was checks **1, 4 and 5** — the spec's own decomposition, the group that knows nothing
about subjects. Checks 3, 6 and 7 were not started.

---

## 1. What each check covers

### Check 1 — link topology

| clause | state | operand |
|---|---|---|
| `self_link` — an input reading its own node | **built** | the graph alone |
| `dangling_link` — a link naming a node id absent from the graph | **built** | the graph alone |
| `undeclared_input` — an input the class does not declare | **built, declines without a schema** | an injected `NodeSchema` |

The founding case fires: `node 14.samples` repointed from `['13', 0]` to `['14', 0]` raises
`SELF_LINK` locating node and input. That is the graph that was in the recorded incident, edited
once.

**A self-link is reported once, not also as dangling.** Its target *is* in the graph, so clause
1b skips a link already reported by 1a. Two defects for one edit reads as two problems.

**`is_link` is structural, not a guess.** A two-element list is a link only when it is
`[str, int]`. A test plants `["not", "a link"]` as a literal and the check passes — without that
discrimination a legitimate list value would be misread as a wire and reported dangling.

### Check 4 — graph-saved-is-graph-submitted

Compares **as parsed graphs**: node id sets, class types, input name sets, link targets
(`source_id`, `source_slot`), and literal values. Eight distinct defect codes, each locating the
node and input.

Numbers compare numerically — Python's `1 == 1.0` — so a seed rendered `770700` or `770700.0`
has not moved. A comparison strict about int-versus-float would report a change where none
occurred, which is the false halt this check exists to avoid.

### Check 5 — generator-legal frame

Built against the **effective** frame, per the spec's Amendment 1.

| case | operand | verdict |
|---|---|---|
| the graph declares dimensions | the literals | PASS / HALT |
| img2img and the caller supplies the input's dimensions | the input image's dimensions | PASS / HALT |
| neither | — | NOT_APPLICABLE, naming what it could not see |

Declared literals win over supplied input dimensions where both exist, and a test pins that
ordering. `batch_size` is excluded from the dimension set — reading it as a frame width would
fire on every txt2img graph.

## 2. Every clause that returns NOT_APPLICABLE, and why

Four, and each names itself in the result rather than passing silently.

**a. `check_1_link_topology.undeclared_input`, with no schema supplied.**
ComfyUI serves a node schema at `/object_info`; this package makes no network calls by design, so
the schema is a parameter. The clause is **not** inferred from the corpus — deriving a gate's
reference from the thing it gates makes it a tautology that passes review because the numbers
look fine. The other two clauses still run; declining one does not weaken the rest, and a test
proves a partial schema still catches a typo on a class it does cover.

**b. A class absent from a supplied schema.** Reported in `classes_not_in_schema` with a note,
never assumed to pass. A schema that does not cover a node cannot answer for it in either
direction.

**c. `check_5_generator_legal_frame`, on an img2img graph with no input dimensions.**
This is the result on **70 of 70** recorded graphs. Zero `width`/`height` literals exist across
the corpus and there is no `EmptyLatentImage` node anywhere; every graph is
`LoadImage → VAEEncode → KSampler → VAEDecode`. The declined reason names the mechanism —
*the frame is inherited from the uploaded image* — and says how to make the clause askable.

**d. `check_5_generator_legal_frame`, for an unmeasured family.**
`sdxl`, `sd15`, `flux`, `wan`, `hunyuan`, `chroma` are declared absent. A test pins that
`family="flux"` with `input_dimensions=(1066, 1066)` returns NOT_APPLICABLE **and does not halt**,
even though Qwen would halt on exactly those numbers. It cannot know the frame is illegal, so it
does not claim to.

## 3. Two judgment calls, stated rather than buried

**÷8 halts; ÷16 advises.** The standing constraint reads *"÷8 is the floor, prefer ÷16"* — a
floor and a preference, not two floors. 1066 fails the floor and halts. 1064 is ÷8-legal and
÷16-short: PASS with an advisory note that says *this is not a halt*. Promoting the preference
would fire on 1064 and on every other legal ÷8 frame, and a gate that halts correct work gets
disabled by the third person who hits it.

**Six families declared absent rather than populated.** Qwen's ÷8 carries its measurement in the
constraint object's `source` field. An unmeasured divisor either halts correct work or passes the
defect it was added for, so a missing row is preferable to a recalled one. Open question 2 in the
spec is unchanged by this arc.

## 4. What the enumeration changed before any code was written

**The three saved/submitted pairs are byte-identical, not merely value-identical.** W2, W2b and
W2c each appear twice in the corpus with the same sha256. They are sound PASS fixtures for check
4 and they **cannot demonstrate its distinguishing property**, because a byte comparison would
pass them too — the very comparison the ruling rejects.

So the false-halt leg is constructed: the submitted side is re-serialised with sorted keys,
changed indent and changed separators, then re-parsed. The leg **asserts the bytes really did
change** before asserting the graphs compare equal — otherwise it could not fail. A second test
pins the byte-identity itself, so if the corpus ever changes that arrives as a notification
rather than as a silently weakened fixture.

**The byte question and the value question both live in this repo and are kept apart in the
code.** The fixture manifest asserts byte-identity with the recorded artifact; check 4 asserts
that no value moved between save and submit. Each module says which question it is answering.
Conflating them is what produced a red CI leg on git's line-ending conversion earlier in this
build.

## 5. An error the suite caught

A check-4 FIRE leg deleted `node 13`'s `steps` input, borrowing the 15-node graph's numbering for
a 17-node pair. `KeyError`. The sampler is now located by *having* a `steps` input rather than by
an assumed id — an assumed node id is a fixture that breaks silently the moment the pair changes,
and this one broke loudly only because the node existed at a different number.

## 6. Findings about out-of-scope checks — reported, not built

**Check 3 (recipe-vs-profile agreement) has no profile fixture in this repo.** The register is
the only profile-shaped object here, and it carries adapter facts alone — no sampler values, no
seed, no model names. Check 3 needs a subject-profile fixture with declared parameter values
before it can be built against anything, and constructing one from the graphs it would check
reproduces the tautology problem named in §2a.

**Check 7 (anchor reproduction) may be narrower than it appears.** It asks whether a recorded
graph still rebuilds from its recorded inputs — which needs the *builder*, not just the graph. The
corpus holds outputs, not the scripts that produced them. Whether the builders are reachable from
this repo is unresolved and was not investigated.

**Check 6 (estimate before submit) is transport-side** by the spec's own decomposition and has no
graph-structural operand at all.

## 7. Compensators for this arc

| action | irreversible? | compensator | owner |
|---|---|---|---|
| running any check | no | read-only on the graph and the register | — |
| the commits `8f9f0ad` and earlier | no | `git revert`; nothing published, no tag, no npm | this seat |
| reading the recorded trees | no | not done at test time; the one-time importer already ran | — |
| submitting a graph | **yes** | **not performed by this arc.** Nothing here contacts the API | — |

## 8. State

- **Built:** checks 1 (2 clauses of 3), 2, 4, 5.
- **Not built:** checks 3, 6, 7.
- **107 tests** across three interpreter modes; the AST scan keeps `src/` free of bare
  `assert` with one declared exception; no check exposes a skip-shaped parameter, and a test
  reads each signature rather than trusting a docstring.
- **Not yet present:** the `preflight()` aggregator that runs the built checks together, the MCP
  tool surface, and the CLI verb named in `pyproject.toml`'s `[project.scripts]` — that entry
  points at `comfy_preflight.cli:main`, which does not exist yet. Naming it here because a
  console script pointing at an absent module is a defect the moment someone installs the
  package.
