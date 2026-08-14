"""The declared-envelope table — data beside the code, changing at documentation cadence.

This is check 8's reference, and like check 2's card vocabulary and check 5's family table it
is **declared, never recalled**. Every entry carries its parameter, its band, the source URL
and the retrieval date, and the constructor refuses to build an entry that does not.

## Why this table exists

Measured (E33→E35): a performer's twins were generated at img2img denoise **0.92** through a
control checkpoint, and nothing on the submit path said whether that was inside or outside the
checkpoint's documented operating range. The dark-speck class that followed cost an acceptance,
a consult, a five-agent research swarm and a repair arc. The fact was knowable at submit time.

## Why it advises and never halts

The studio ran 0.92 **deliberately** and the Director approved the register it produced. A
documented band is documentation, not a gate. A check that halted here would fire on correct
work, and a gate that halts correct work gets disabled by the third person who hits it — check
3's exclusion law, arriving at check 8. The advisory's job is to make an out-of-band fact
visible at the moment it is cheap, not to forbid it.

## ⚠ What the day-one entry does NOT contain, and why that is the headline

The dispatch expected this entry to carry an **img2img denoise band of ~0.10–0.50**, cited to
the InstantX Qwen-Image-ControlNet-Union model card, from the E35 research grounding (agent 1,
finding 8).

**Verified against the live card at build time, 2026-08-14, and that band is not on it.** Two
independent fetches — the rendered model page and `raw/main/README.md` — agree: the card
documents `controlnet_conditioning_scale` in `[0.8, 1.0]` for each of its four control types,
and shows `true_cfg_scale=4.0` / `num_inference_steps=30` as example values in its inference
snippet. It documents **no img2img denoise or strength range at all**. A public web search for
the 0.10–0.50 figure surfaces nothing on that card either.

So the denoise band does not ship, because the discipline that governs this table says an
entry populated from memory is worse than a missing one. What ships instead is what the card
actually documents, plus a **declared absence** — see `DocumentedAbsence` below — so that a run
on the 0.92 graph reports the 0.92, names the parameter, and says plainly that this check
cannot speak to it and why. Reporting the value it cannot judge is the honest half of the
finding; inventing a band to judge it against is the dishonest half.

The grounding's other Union card — InstantX/Shakker-Labs **FLUX.1-dev-Controlnet-Union**, whose
canny examples run at 0.5 — is a **different checkpoint** and its numbers do not enter a Qwen
entry.

## ⚑ And what answered that absence, one arc later (Amendment 5, 2026-08-14)

The vendor documents no denoise band and never will, so the only route to one was to measure it.
The studio did (experiment E35), the advisor ruled the measurement in, and it ships below as the
first `STUDIO_MEASURED` entry — **beside** the vendor entry, not inside it.

**The declared absence above STAYS.** The card still publishes nothing, and that stays true no
matter what the studio measures in its own kitchen. The measured entry *answers* the absence; it
does not erase it. A check-8 report on this checkpoint now carries both, each in its own voice:
the vendor cannot judge this parameter, and here is what the studio measured at it.

That is why the table is keyed by **(checkpoint, parameter)** rather than by checkpoint — see
`index()` below. One checkpoint, one parameter, two authorities.
"""

from __future__ import annotations

import dataclasses
import enum
import re
from collections.abc import Mapping

# Input names that carry the name of a loaded model checkpoint. `vae_name` and `clip_name` are
# deliberately excluded: they name components, not checkpoints with published operating bands,
# and including them would fill every NOT_APPLICABLE with names no envelope will ever cover.
CHECKPOINT_INPUT_NAMES = frozenset(
    {"control_net_name", "ckpt_name", "unet_name", "model_name"}
)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class EntryKind(enum.Enum):
    """Where an entry's authority comes from. Both kinds must justify themselves; neither may
    be populated from memory.

    The spec's discipline is *"each entry needs a measurement or a citation"* — two routes to the
    same standard, and this enum is the fork made explicit so a reader can tell at a glance which
    one an entry took.

    VENDOR — the checkpoint's publisher documents the band. Authority is the card, and the entry
    carries `source_url` + `retrieved` so the citation can be re-fetched and can go stale visibly.

    STUDIO_MEASURED — the publisher documents nothing, and the studio measured it. Authority is
    the studio's own record, and the entry carries a `record` locator the way a vendor entry
    carries a URL: a specific, retrievable experiment record, not "we found that...".

    **The measured kind exists because of a fact this table already reports.** The Qwen
    ControlNet-Union card documents no img2img denoise band at all, so no vendor citation for that
    parameter can ever exist — the only route to an entry is measuring it. Amendment 3 ruled the
    capability in and the data out: **the kind ships, and no measured entry ships with it** until
    the advisor rules a specific measurement in.
    """

    VENDOR = "vendor"
    STUDIO_MEASURED = "studio_measured"


@dataclasses.dataclass(frozen=True)
class MeasuredRecord:
    """The locator for a studio measurement — a measured entry's answer to `source_url`.

    A measurement with no retrievable record is the same defect as a band with no card: a number
    whose authority cannot be checked by the person it halts. So this is required, structured, and
    validated, rather than a free-text "measured internally".

    `experiment` is the record's own identifier (e.g. an E-number), `locator` the path or URL where
    that record lives, and `measured` the ISO date the measurement was taken — the exact analogue
    of a vendor entry's retrieval date, and it goes stale the same way.
    """

    experiment: str
    locator: str
    measured: str
    finding: str

    def __post_init__(self) -> None:
        if not self.experiment.strip():
            raise ValueError(
                "MeasuredRecord requires an `experiment` identifier; a measurement nobody can "
                "name is one nobody can re-open"
            )
        if not self.locator.strip():
            raise ValueError(
                f"MeasuredRecord({self.experiment!r}) requires a `locator` - the path or URL of "
                "the record. This is the measured kind's citation, and an entry without one is "
                "populated from memory no matter how true it is"
            )
        if not _ISO_DATE.match(self.measured):
            raise ValueError(
                f"MeasuredRecord({self.experiment!r}) has measured {self.measured!r}, which is "
                "not an ISO date. A measurement without a date cannot go stale visibly"
            )
        if not self.finding.strip():
            raise ValueError(
                f"MeasuredRecord({self.experiment!r}) requires a one-line `finding` - what the "
                "measurement actually showed, in the words of whoever took it"
            )


@dataclasses.dataclass(frozen=True)
class Rung:
    """One measured point on a swept parameter, with what the measurement recorded there.

    A rung is a **reading**, not a recommendation. It says what happened at this value under one
    recipe and says nothing at all about the values between rungs.

    `ruling` carries a seat's disposition where one was made. The Director holding the register
    at 0.92 is a fact about a decision, not about the pixels, and keeping it beside the number is
    what stops the number from being read as advice on its own.
    """

    value: float
    outcome: str
    ruling: str = ""

    def __post_init__(self) -> None:
        if not self.outcome.strip():
            raise ValueError(
                f"Rung({self.value}) records no outcome. A value with no measured result is a "
                "value someone tried, not a measurement"
            )

    def rendered(self, parameter: str) -> str:
        text = f"{parameter} {self.value:g} -> {self.outcome}"
        return f"{text} ({self.ruling})" if self.ruling else text


@dataclasses.dataclass(frozen=True)
class MeasuredLadder:
    """A studio sweep of one parameter: the rungs it measured, and the recipe they hold at.

    This is the measured kind's answer to `Band`, and the difference between the two shapes is
    the whole reason it is a separate one. **A band is a range a publisher endorses**, so a value
    inside it is unremarkable and only a value outside is worth saying. **A ladder endorses
    nothing** — it reports what was measured at specific points under one recipe. So every value
    gets the nearest rungs, *including* a value sitting exactly on the rung the Director held: the
    caller is told what the studio measured there, not whether the studio approves of it.

    `context` is the measurement's **validity envelope** and is required. A sweep detached from
    its recipe is a recommendation wearing a number — the same denoise at a different
    conditioning strength, step count or frame is a different measurement — and this string is
    what stops the rungs being read as universal.

    Resolution is **by class across the whole graph**, like `DocumentedAbsence` and for the same
    reason: the swept parameter typically sits downstream of the checkpoint rather than on a
    direct consumer of it. `denoise` lives on the sampler, not on the control-apply node.
    """

    parameter: str
    node_classes: frozenset[str]
    rungs: tuple[Rung, ...]
    context: str

    def __post_init__(self) -> None:
        if not self.rungs:
            raise ValueError(
                f"MeasuredLadder({self.parameter!r}) carries no rungs, so it is a citation with "
                "nothing measured under it"
            )
        if not self.context.strip():
            raise ValueError(
                f"MeasuredLadder({self.parameter!r}) states no context. A sweep without the "
                "recipe it ran at is a recommendation wearing a number: the reader cannot tell "
                "which of their own settings the rungs apply to"
            )
        if not self.node_classes:
            raise ValueError(
                f"MeasuredLadder({self.parameter!r}) names no node classes, so it could never "
                "find the value it reports on"
            )
        values = [rung.value for rung in self.rungs]
        if len(set(values)) != len(values):
            raise ValueError(
                f"MeasuredLadder({self.parameter!r}) has two rungs at the same value. Two "
                "readings at one point is a disagreement this table cannot resolve for a caller"
            )

    @property
    def ordered(self) -> tuple[Rung, ...]:
        return tuple(sorted(self.rungs, key=lambda rung: rung.value))

    @property
    def span(self) -> tuple[float, float]:
        """The lowest and highest value this sweep actually measured."""
        ordered = self.ordered
        return ordered[0].value, ordered[-1].value

    def spans(self, value: float) -> bool:
        low, high = self.span
        return low <= value <= high

    def nearest(self, value: float) -> tuple[Rung, ...]:
        """The rungs this sweep can speak from for `value`.

        The exact rung if that value was measured; otherwise the pair bracketing it; otherwise —
        for a value beyond either end — the single nearest one. **Nothing is interpolated.** Two
        bracketing rungs are two readings, not a range, and the caller is handed both rather than
        a number nobody measured.
        """
        ordered = self.ordered
        exact = tuple(rung for rung in ordered if rung.value == value)
        if exact:
            return exact
        below = [rung for rung in ordered if rung.value < value]
        above = [rung for rung in ordered if rung.value > value]
        if below and above:
            return (below[-1], above[0])
        return (below[-1],) if below else (above[0],)


@dataclasses.dataclass(frozen=True)
class Band:
    """One documented operating range for one graph input.

    `parameter` is the **graph's** input name, not the card's. Cards document a library API;
    graphs carry ComfyUI node inputs, and the two use different names for the same knob.
    `mapping` states that equivalence in words — declared, the way the register's `card_aliases`
    are declared, because an inferred equivalence is a heuristic that also silently accepts a
    parameter the card never governed.

    `linked` ties the parameter to the checkpoint by **following the graph's wires**: only nodes
    that actually read from this checkpoint's loader are examined. Without it a graph carrying
    two control checkpoints would have one entry's band applied to the other's apply node.
    """

    parameter: str
    low: float
    high: float
    node_classes: frozenset[str]
    quote: str
    mapping: str
    linked: bool = True

    def __post_init__(self) -> None:
        if not self.quote.strip():
            raise ValueError(
                f"Band({self.parameter!r}) carries no quote from its source. A band without "
                "the card's own words is a recalled number wearing a citation"
            )
        if self.low > self.high:
            raise ValueError(f"Band({self.parameter!r}) has low {self.low} above high {self.high}")
        if not self.node_classes:
            raise ValueError(
                f"Band({self.parameter!r}) names no node classes, so it can never find its "
                "operand and would be a clause that cannot fire"
            )

    def contains(self, value: float) -> bool:
        return self.low <= value <= self.high


@dataclasses.dataclass(frozen=True)
class DocumentedAbsence:
    """A parameter this checkpoint's card is **known not to document**, verified at the source.

    This is the shape Amendment 1 ruled for check 5, applied to a parameter rather than a whole
    check: a refusal that states its own blind spot. The check reports the graph's value for
    this parameter and says it cannot judge it — which surfaces the fact at the moment it is
    cheap without inventing a band to judge it against.

    Resolution is **by class across the whole graph**, not by following the checkpoint's wires,
    because the parameter typically lives on a node that is downstream of the checkpoint rather
    than a direct consumer of it. `denoise` sits on the sampler, not on the control-apply node.
    """

    parameter: str
    node_classes: frozenset[str]
    reason: str

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError(
                f"DocumentedAbsence({self.parameter!r}) carries no reason. 'The card does not "
                "document this' is a claim about a source and must say how it was checked"
            )
        if not self.node_classes:
            raise ValueError(
                f"DocumentedAbsence({self.parameter!r}) names no node classes, so it could "
                "never report the value it declines to judge"
            )


@dataclasses.dataclass(frozen=True)
class EnvelopeEntry:
    """One checkpoint's declared envelope, with the authority for every number in it.

    The constructor refuses to build an unjustified entry, in either kind. That refusal is the
    data discipline made mechanical rather than documented: a table whose citations are checked
    only by review is a table that acquires a recalled number the first time someone is in a
    hurry.

    `kind` selects which justification is required, and the two are mutually exclusive by
    construction. A VENDOR entry carries a URL and a retrieval date and must NOT carry a record;
    a STUDIO_MEASURED entry carries a record and must NOT carry a URL. Allowing both would let an
    entry look doubly-sourced while being neither — the reader could not tell which number came
    from where.

    **The shapes are exclusive the same way** (Amendment 5's boundary, made mechanical):

    - `ladders` are the studio's rungs, so only a STUDIO_MEASURED entry may carry them. A card
      publishes ranges, not sweeps; a vendor entry holding rungs would be a measurement wearing a
      citation.
    - `documented_absent` is a claim about a **publisher's card** — "this source documents no
      band here" — so only a VENDOR entry may make it. The measured entry *answers* an absence;
      it does not carry one, and it never replaces the vendor's. Both stay, on one parameter, in
      two voices.
    """

    checkpoint: str
    source_url: str = ""
    retrieved: str = ""
    kind: EntryKind = EntryKind.VENDOR
    record: MeasuredRecord | None = None
    bands: tuple[Band, ...] = ()
    ladders: tuple[MeasuredLadder, ...] = ()
    documented_absent: tuple[DocumentedAbsence, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.checkpoint.strip():
            raise ValueError("EnvelopeEntry requires a checkpoint name")

        if self.kind is EntryKind.VENDOR:
            if not self.source_url.startswith(("http://", "https://")):
                raise ValueError(
                    f"EnvelopeEntry({self.checkpoint!r}) has source_url {self.source_url!r}, "
                    "which is not a URL. A vendor entry cites a retrievable source; an uncited "
                    "entry is a number recalled from memory and is worse than a missing row"
                )
            if not _ISO_DATE.match(self.retrieved):
                raise ValueError(
                    f"EnvelopeEntry({self.checkpoint!r}) has retrieved {self.retrieved!r}, which "
                    "is not an ISO date. A citation without a retrieval date cannot go stale "
                    "visibly"
                )
            if self.record is not None:
                raise ValueError(
                    f"EnvelopeEntry({self.checkpoint!r}) is kind VENDOR but carries a measured "
                    "record. The two authorities are exclusive: an entry claiming both looks "
                    "doubly-sourced while a reader cannot tell which number came from where. "
                    "Split it into two entries, or pick the authority the numbers actually have"
                )
            if self.ladders:
                raise ValueError(
                    f"EnvelopeEntry({self.checkpoint!r}) is kind VENDOR but carries measured "
                    "rungs. A card publishes ranges, not sweeps - rungs are the studio's "
                    "authority, and an entry holding them is kind STUDIO_MEASURED with a record"
                )
        else:
            if self.record is None:
                raise ValueError(
                    f"EnvelopeEntry({self.checkpoint!r}) is kind STUDIO_MEASURED but carries no "
                    "record. The record locator IS the measured kind's citation - without one "
                    "the entry is populated from memory no matter how true it is"
                )
            if self.source_url or self.retrieved:
                raise ValueError(
                    f"EnvelopeEntry({self.checkpoint!r}) is kind STUDIO_MEASURED but carries a "
                    "vendor source_url/retrieved. If the vendor documents the band, the entry is "
                    "kind VENDOR; if it does not, the URL belongs in `notes` as context rather "
                    "than beside numbers it did not supply"
                )
            if self.documented_absent:
                raise ValueError(
                    f"EnvelopeEntry({self.checkpoint!r}) is kind STUDIO_MEASURED but declares a "
                    "documented absence. An absence is a claim about a PUBLISHER's card, which "
                    "is the vendor entry's to make. A measured entry answers an absence - it "
                    "never carries one, and it never replaces the vendor's, which stays"
                )

        if not self.bands and not self.ladders and not self.documented_absent:
            raise ValueError(
                f"EnvelopeEntry({self.checkpoint!r}) declares neither a band, a measured ladder "
                "nor a documented absence, so it says nothing about the checkpoint it names"
            )

        banded = {band.parameter for band in self.bands}
        absent = {absence.parameter for absence in self.documented_absent}
        if banded & absent:
            raise ValueError(
                f"EnvelopeEntry({self.checkpoint!r}) both bands and declares absent "
                f"{sorted(banded & absent)}. One source cannot document a range for a parameter "
                "and also document nothing for it; one of the two readings of the card is wrong"
            )

    @property
    def citation(self) -> str:
        """The authority, rendered for a finding. Both kinds answer; neither is allowed to be
        vague about which one it is."""
        if self.kind is EntryKind.VENDOR:
            return f"{self.source_url} (retrieved {self.retrieved})"
        record = self.record
        return (
            f"studio measurement {record.experiment} at {record.locator} "
            f"(measured {record.measured}): {record.finding}"
        )


def basename(value: str) -> str:
    """The filename component, so a path-prefixed checkpoint reference still resolves."""
    return value.replace("\\", "/").rsplit("/", 1)[-1]


# ---------------------------------------------------------------------------------------------
# THE INDEX. Keyed by (checkpoint, parameter), because one parameter can have two authorities.
# ---------------------------------------------------------------------------------------------
#
# The table shipped at 1.0.0 was `dict[checkpoint, EnvelopeEntry]` — one entry per checkpoint,
# which was enough while every entry was a vendor citation. Amendment 5's ruling breaks that
# shape: the studio's denoise measurement and the vendor's declared absence for denoise are
# **both** about this checkpoint, and both must ship. Keyed by checkpoint, the second would have
# overwritten the first silently.
#
# So the key is the pair, and the value is a tuple. A key holding two entries is the ruled shape
# and not a collision — one vendor voice, one measured voice, on the same parameter. A key
# holding two entries of the SAME kind is a duplicate whose disagreement nothing could resolve
# for a caller, and `index()` refuses to build it.

EnvelopeKey = tuple[str, str]  # (checkpoint basename lowercased, graph input name)
EnvelopeTable = Mapping[EnvelopeKey, tuple[EnvelopeEntry, ...]]


def parameters_of(entry: EnvelopeEntry) -> tuple[str, ...]:
    """Every graph parameter this entry speaks to — banded, laddered or declared absent."""
    seen: dict[str, None] = {}
    for parameter in (
        [band.parameter for band in entry.bands]
        + [ladder.parameter for ladder in entry.ladders]
        + [absence.parameter for absence in entry.documented_absent]
    ):
        seen.setdefault(parameter, None)
    return tuple(seen)


def keys_of(entry: EnvelopeEntry) -> tuple[EnvelopeKey, ...]:
    """The index keys one entry occupies."""
    name = basename(entry.checkpoint).lower()
    return tuple((name, parameter) for parameter in parameters_of(entry))


def index(*entries: EnvelopeEntry) -> dict[EnvelopeKey, tuple[EnvelopeEntry, ...]]:
    """Build the (checkpoint, parameter) index from declared entries, in declaration order."""
    table: dict[EnvelopeKey, tuple[EnvelopeEntry, ...]] = {}
    for entry in entries:
        for key in keys_of(entry):
            existing = table.get(key, ())
            if any(prior.kind is entry.kind for prior in existing):
                raise ValueError(
                    f"two {entry.kind.value} entries both claim {key}. One authority speaks once "
                    "per (checkpoint, parameter): a second row from the same authority is a "
                    "disagreement this table cannot resolve for a caller. Two entries of "
                    "DIFFERENT kinds on one key is the ruled shape - the vendor's declared "
                    "absence and the studio's measurement of the same parameter, each in its "
                    "own voice"
                )
            table[key] = existing + (entry,)
    return table


def entries_for(table: EnvelopeTable, checkpoint: str) -> tuple[EnvelopeEntry, ...]:
    """Every entry speaking about this checkpoint, deduplicated, in index order.

    An entry occupies one key per parameter it speaks to, so a checkpoint lookup gathers across
    keys. Order is the index's insertion order, which is declaration order: vendor first, then
    the rulings — so a report reads the card before it reads the kitchen.
    """
    name = basename(checkpoint).lower()
    found: dict[EnvelopeEntry, None] = {}
    for (candidate, _parameter), entries in table.items():
        if candidate != name:
            continue
        for entry in entries:
            found.setdefault(entry, None)
    return tuple(found)


# ---------------------------------------------------------------------------------------------
# THE TABLE. One checkpoint, two authorities. Adding a vendor row requires opening the live card;
# adding a measured row requires the advisor ruling a specific measurement in.
# ---------------------------------------------------------------------------------------------

QWEN_CONTROLNET_UNION = EnvelopeEntry(
    # The name as it appears in a graph — the Comfy-Org repackage of InstantX's checkpoint. The
    # corpus loads it under this filename on 46 of 70 recorded graphs.
    checkpoint="Qwen-Image-InstantX-ControlNet-Union.safetensors",
    source_url="https://huggingface.co/InstantX/Qwen-Image-ControlNet-Union",
    retrieved="2026-08-14",
    bands=(
        Band(
            parameter="strength",
            low=0.8,
            high=1.0,
            node_classes=frozenset({"ControlNetApplyAdvanced", "ControlNetApply"}),
            quote=(
                "the card states 'set controlnet_conditioning_scale in [0.8, 1.0]' for each of "
                "its four control types (canny, soft edge, depth, pose), and its inference "
                "example runs controlnet_conditioning_scale = 1.0"
            ),
            mapping=(
                "the card documents the diffusers pipeline argument "
                "`controlnet_conditioning_scale`; the same knob reaches a ComfyUI graph as the "
                "`strength` input of the control-apply node. The equivalence is DECLARED here "
                "rather than inferred, because a parameter matched by name alone would let this "
                "band judge a knob the card never governed"
            ),
        ),
    ),
    documented_absent=(
        DocumentedAbsence(
            parameter="denoise",
            node_classes=frozenset({"KSampler", "KSamplerAdvanced"}),
            reason=(
                "the card documents NO img2img denoise or strength range. Verified against the "
                "live source 2026-08-14 by two independent fetches - the rendered model page "
                "and raw/main/README.md - which agree: the only ranges it publishes are "
                "controlnet_conditioning_scale in [0.8, 1.0], plus true_cfg_scale=4.0 and "
                "num_inference_steps=30 as example values in an inference snippet. The E35 "
                "research grounding (agent 1, finding 8) attributes a '~0.10-0.50 recommended "
                "img2img denoise' to this card; that band is not on it, and a band this check "
                "cannot retrieve is one it must not judge against"
            ),
        ),
    ),
    notes=(
        "true_cfg_scale=4.0 and num_inference_steps=30 appear on the card as example values in "
        "a code snippet, not as recommended ranges. They are recorded here and deliberately NOT "
        "shipped as bands: an example is one point, and inferring a range around it would be "
        "inventing the measurement this table exists to avoid.",
    ),
)


# ---------------------------------------------------------------------------------------------
# THE FIRST STUDIO-MEASURED ENTRY, RULED IN BY AMENDMENT 5 (advisor, 2026-08-14).
#
# Amendment 3 adopted the measured kind "as a capability, gated as data": the schema shipped at
# 1.0.0 and the table shipped empty of it, because **no measured entry ships until the advisor
# rules one in.** The named candidate was E35's denoise sweep "once ruled". It is ruled — Gate R
# (the Director, 2026-08-14) held the register at the recorded recipe — so the data lands here,
# and the test that pinned the dict empty was deleted as the deliberate act that ruling requires.
#
# This is the parameter the vendor entry above reports as a declared absence, which is exactly
# why it was the first candidate: no vendor citation for it can ever exist, so measuring it was
# the only route to documentation. What ships is facet's own record, converted into the
# documentation the publisher never wrote.
# ---------------------------------------------------------------------------------------------

QWEN_CONTROLNET_UNION_DENOISE = EnvelopeEntry(
    checkpoint="Qwen-Image-InstantX-ControlNet-Union.safetensors",
    kind=EntryKind.STUDIO_MEASURED,
    record=MeasuredRecord(
        experiment="E35",
        # The report titles that section with em dashes; the ASCII hyphen here keeps every
        # string this table can print through a CLI inside the range every console encodes.
        locator="docs/experiments/E35-clean-twins-report.md, section '2b - the denoise sweep'",
        measured="2026-08-14",
        finding=(
            "The register dies before the specks do: census-0 at 0.72 is reached only by "
            "reverting 56% of the figure toward the clay init (C* 23.77 -> 1.89). At this "
            "route's recorded recipe, 0.92 is the measured register-safe point (Gate R, "
            "Director-ruled)."
        ),
    ),
    ladders=(
        MeasuredLadder(
            parameter="denoise",
            node_classes=frozenset({"KSampler", "KSamplerAdvanced"}),
            context=(
                "img2img on the canny route: cn_strength 0.9, steps 20, cfg 2.5, euler/simple, "
                "shift 3.1, 352x1024, no LoRA. These rungs hold at this recipe and nowhere "
                "else - a different conditioning strength, step count or frame is a different "
                "measurement"
            ),
            rungs=(
                Rung(
                    value=0.92,
                    outcome="register C* 23.77, reverted-to-init 0.50%, speck census 16",
                    ruling="the recorded value, Director-ruled HOLD at Gate R",
                ),
                Rung(
                    value=0.85,
                    outcome="register C* 10.00, reverted-to-init 5.01%, speck census 10",
                ),
                Rung(
                    value=0.80,
                    outcome="register C* 3.91, reverted-to-init 36.66%, speck census 12",
                ),
                Rung(
                    value=0.72,
                    outcome="register C* 1.89, reverted-to-init 56.00%, speck census 0",
                    ruling=(
                        "census-0 by register destruction - the specks vanish because the paint "
                        "vanishes, back to the white-grey clay init"
                    ),
                ),
            ),
        ),
    ),
    notes=(
        "The sweep's reg-IoU column is confounded in this regime (E01's law: a grey figure on a "
        "grey ground cannot be found by a border-ring threshold) and is deliberately not carried "
        "here. The two uncontaminated columns - reverted-to-init and register C* - are the ones "
        "the rungs report.",
    ),
)


# The vendor-cited entries and the ruled-in measurements, declared separately so a reader can see
# at a glance what each authority contributed, and indexed together into the one table check 8
# reads. One ruling per entry, always: a second measurement enters here only through its own.
VENDOR_ENTRIES: tuple[EnvelopeEntry, ...] = (QWEN_CONTROLNET_UNION,)
STUDIO_MEASURED: tuple[EnvelopeEntry, ...] = (QWEN_CONTROLNET_UNION_DENOISE,)

ENVELOPE: dict[EnvelopeKey, tuple[EnvelopeEntry, ...]] = index(
    *VENDOR_ENTRIES, *STUDIO_MEASURED
)

# Checkpoints the recorded corpus loads that this table does NOT cover, named so the boundary is
# visible rather than inferred from a quiet NOT_APPLICABLE. Each needs its own live card read.
#
# `Qwen-Image-InstantX-ControlNet-Inpainting.safetensors` is loaded by 24 of the 70 recorded
# graphs. Its card was opened at this seat (2026-08-14) and documents no denoise or strength
# range either — but Amendment 2 rules exactly one checkpoint for day one, so it ships absent
# rather than as a second entry, and this line records what was seen rather than discarding it.
DECLARED_ABSENT_CHECKPOINTS = (
    "Qwen-Image-InstantX-ControlNet-Inpainting.safetensors",
)
