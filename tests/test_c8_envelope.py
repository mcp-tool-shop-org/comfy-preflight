"""Check 8 — the declared-envelope advisory.

Two properties carry this file. **It never halts** — proven over the whole recorded corpus and
over deliberately out-of-band mutations, not asserted in a docstring. And **every shipped entry
is cited** — proven by walking the shipped table, with a can-fail leg proving the constructor
actually refuses an uncited row.
"""

from __future__ import annotations

import copy
import dataclasses
import re

import pytest
from conftest import ADAPTER_15, ADAPTER_17, all_graph_names, load_graph, load_raw, mutate

from comfy_preflight.checks import check_declared_envelope
from comfy_preflight.envelope import (
    DECLARED_ABSENT_CHECKPOINTS,
    ENVELOPE,
    STUDIO_MEASURED,
    Band,
    DocumentedAbsence,
    EntryKind,
    EnvelopeEntry,
    MeasuredLadder,
    MeasuredRecord,
    Rung,
    basename,
    index,
)
from comfy_preflight.errors import PreflightHalt, Verdict
from comfy_preflight.graph import Graph

# The corpus splits by CONTROL CHECKPOINT, and that split is not the adapter split the rest
# of the suite names its fixtures by. The 15- and 14-node graphs load the Union checkpoint
# (46 of 70, denoise 0.92, ControlNetApplyAdvanced strength 0.9); the 17- and 16-node graphs
# load the Inpainting checkpoint (24 of 70, denoise 1.0). Aliased here so a reader is not
# left inferring that "the adapter fixture" and "the Union fixture" are the same axis.
UNION_GRAPH = ADAPTER_15
INPAINTING_GRAPH = ADAPTER_17

UNION = "Qwen-Image-InstantX-ControlNet-Union.safetensors"
INPAINTING = "Qwen-Image-InstantX-ControlNet-Inpainting.safetensors"
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _entries(parameter: str) -> tuple:
    """Every shipped entry speaking to one parameter of the Union checkpoint, in index order."""
    return ENVELOPE[(UNION.lower(), parameter)]


def _vendor_entry() -> EnvelopeEntry:
    return next(e for e in _entries("strength") if e.kind is EntryKind.VENDOR)


def _measured_entry() -> EnvelopeEntry:
    return next(e for e in _entries("denoise") if e.kind is EntryKind.STUDIO_MEASURED)


def _set_denoise(value):
    """Mutate every sampler's denoise, so the FIRE case differs from the recorded one by an edit."""

    def apply(raw: dict) -> None:
        for node in raw.values():
            if node["class_type"] in ("KSampler", "KSamplerAdvanced"):
                node["inputs"]["denoise"] = value

    return apply


def _measurement_finding(result):
    return next(f for f in result.findings if f.code == "PARAMETER_HAS_A_STUDIO_MEASUREMENT")


def _band_findings(result):
    return [f for f in result.findings if f.code == "PARAMETER_OUTSIDE_DECLARED_ENVELOPE"]


def _graphs_loading(checkpoint: str) -> list[str]:
    """Fixture names whose graph loads the named checkpoint."""
    out = []
    for name in all_graph_names():
        raw = load_raw(name)
        for node in raw.values():
            for value in node.get("inputs", {}).values():
                if isinstance(value, str) and basename(value) == checkpoint:
                    out.append(name)
                    break
            else:
                continue
            break
    return out


# ---------------------------------------------------------------------------------------------
# The load-bearing property: this check advises and never halts.
# ---------------------------------------------------------------------------------------------


def test_the_check_never_halts_on_any_recorded_graph():
    """The no-false-halt leg, over all 70. A halt here would be a spec violation, not a bug."""
    for name in all_graph_names():
        try:
            check_declared_envelope(load_graph(name))
        except PreflightHalt as exc:  # pragma: no cover - the failure path
            raise AssertionError(f"{name}: check 8 halted, and it must never halt: {exc}")


def test_the_check_never_halts_even_when_wildly_out_of_band():
    """The direction that matters: a finding is an ADVISORY, never a raise.

    A softer wording would let a later edit promote this to a halt and pass review. The value
    used is far outside the band, so nothing about the input excuses a non-halt.
    """
    graph = mutate(UNION_GRAPH, lambda raw: _set_controlnet_strength(raw, 0.05))
    result = check_declared_envelope(graph)  # must not raise
    assert result.verdict is Verdict.ADVISORY
    assert result.findings, "an out-of-band value produced no finding"


def test_the_check_exposes_no_raise_path_at_all():
    """Read the module rather than trusting the two tests above to have found every input.

    `PreflightHalt` must not be raised anywhere in check 8's source. This is the same shape as
    the repo's AST scan for bare asserts: a property proven by reading the code, because no
    finite set of inputs proves the absence of a branch.
    """
    import ast
    import pathlib

    import comfy_preflight.checks.c8_envelope as module

    tree = ast.parse(pathlib.Path(module.__file__).read_text(encoding="utf-8"))
    raises = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Raise)
        and isinstance(node.exc, ast.Call)
        and getattr(node.exc.func, "id", None) == "PreflightHalt"
    ]
    if raises:
        raise AssertionError(
            f"check 8 raises PreflightHalt at line(s) {raises}; Amendment 2 rules it ADVISORY "
            "only, never HALT"
        )


def test_the_raise_scan_fires_on_a_synthetic_module(tmp_path):
    """Can-fail leg for the scan above, against a synthetic file so no real module moves."""
    import ast

    bad = tmp_path / "zz_synthetic_check.py"
    bad.write_text(
        "def check(graph):\n    raise PreflightHalt('c', [])\n",
        encoding="utf-8",
    )
    tree = ast.parse(bad.read_text(encoding="utf-8"))
    found = [
        n.lineno
        for n in ast.walk(tree)
        if isinstance(n, ast.Raise)
        and isinstance(n.exc, ast.Call)
        and getattr(n.exc.func, "id", None) == "PreflightHalt"
    ]
    if found != [2]:
        raise RuntimeError(f"the scan missed a PreflightHalt raise on line 2; got {found}")


# ---------------------------------------------------------------------------------------------
# The citation discipline, made mechanical.
# ---------------------------------------------------------------------------------------------


def test_every_shipped_entry_is_cited_by_the_authority_it_claims():
    """Amendment 2: an uncited entry FAILS a test. This is that test, over both kinds.

    A vendor entry answers with a URL and a retrieval date; a measured entry answers with an
    experiment record and the recipe its rungs hold at. Neither may answer with nothing, and the
    walk covers whatever is shipped rather than a list written here — a row added tomorrow is
    checked by this test without anyone remembering to extend it.
    """
    if not ENVELOPE:
        raise AssertionError("the envelope table is empty; it ships at least one checkpoint")
    for key, entries in ENVELOPE.items():
        for entry in entries:
            if entry.kind is EntryKind.VENDOR:
                if not entry.source_url.startswith("https://"):
                    raise AssertionError(f"{key}: source_url {entry.source_url!r} is not a URL")
                if not ISO_DATE.match(entry.retrieved):
                    raise AssertionError(
                        f"{key}: retrieved {entry.retrieved!r} is not an ISO date"
                    )
            else:
                record = entry.record
                if record is None or not record.locator.strip():
                    raise AssertionError(f"{key}: a measured entry with no record locator")
                if not ISO_DATE.match(record.measured):
                    raise AssertionError(
                        f"{key}: measured {record.measured!r} is not an ISO date"
                    )
                if not record.finding.strip():
                    raise AssertionError(f"{key}: a measurement with no stated finding")
            for band in entry.bands:
                if not band.quote.strip():
                    raise AssertionError(f"{key}.{band.parameter}: no quote from the source")
                if not band.mapping.strip():
                    raise AssertionError(
                        f"{key}.{band.parameter}: no stated mapping from the card's parameter "
                        "name to the graph's input name"
                    )
            for ladder in entry.ladders:
                if not ladder.context.strip():
                    raise AssertionError(
                        f"{key}.{ladder.parameter}: rungs shipped without the recipe they hold "
                        "at, which is a recommendation wearing a number"
                    )
                for rung in ladder.rungs:
                    if not rung.outcome.strip():
                        raise AssertionError(
                            f"{key}.{ladder.parameter}: a rung at {rung.value} with no outcome"
                        )
            for absence in entry.documented_absent:
                if not absence.reason.strip():
                    raise AssertionError(
                        f"{key}.{absence.parameter}: absence claimed without reason"
                    )


def test_an_uncited_entry_cannot_be_constructed():
    """The can-fail leg. The refusal is in the constructor, so a hurried edit cannot slip past."""
    band = Band(
        parameter="strength",
        low=0.8,
        high=1.0,
        node_classes=frozenset({"ControlNetApplyAdvanced"}),
        quote="q",
        mapping="m",
    )
    with pytest.raises(ValueError, match="not a URL"):
        EnvelopeEntry(
            checkpoint="zz_synthetic.safetensors",
            source_url="remembered from a paper",
            retrieved="2026-08-14",
            bands=(band,),
        )
    with pytest.raises(ValueError, match="not an ISO date"):
        EnvelopeEntry(
            checkpoint="zz_synthetic.safetensors",
            source_url="https://example.invalid/card",
            retrieved="last week",
            bands=(band,),
        )
    with pytest.raises(ValueError, match="neither a band, a measured ladder"):
        EnvelopeEntry(
            checkpoint="zz_synthetic.safetensors",
            source_url="https://example.invalid/card",
            retrieved="2026-08-14",
        )


def test_a_band_without_the_cards_own_words_is_refused():
    """A number with a URL beside it is not a citation if nobody recorded what the source said."""
    with pytest.raises(ValueError, match="carries no quote"):
        Band(
            parameter="strength",
            low=0.8,
            high=1.0,
            node_classes=frozenset({"ControlNetApplyAdvanced"}),
            quote="   ",
            mapping="m",
        )
    with pytest.raises(ValueError, match="names no node classes"):
        Band(
            parameter="strength",
            low=0.8,
            high=1.0,
            node_classes=frozenset(),
            quote="q",
            mapping="m",
        )


def test_a_documented_absence_must_say_how_it_was_checked():
    with pytest.raises(ValueError, match="carries no reason"):
        DocumentedAbsence(
            parameter="denoise", node_classes=frozenset({"KSampler"}), reason=""
        )


# ---------------------------------------------------------------------------------------------
# The day-one entry, against the corpus it was measured on.
# ---------------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------------
# The STUDIO_MEASURED entry kind (Amendment 3, reading B): the capability ships, the data does not.
# ---------------------------------------------------------------------------------------------


def _record(**over) -> MeasuredRecord:
    base = dict(
        experiment="E99",
        locator="docs/experiments/E99-synthetic.md",
        measured="2026-08-14",
        finding="a synthetic measurement, used only to exercise the schema",
    )
    base.update(over)
    return MeasuredRecord(**base)


# ⚑ The gate that used to stand here — `test_the_measured_kind_ships_empty_until_the_advisor_
# rules_an_entry_in`, asserting `STUDIO_MEASURED == {}` — was DELETED by Amendment 5, which is
# the deliberate act its own design demanded. It existed so that ruling a measurement in could
# never be a quiet append: whoever added the first entry had to first delete the test saying
# none had been ruled in, and in deleting it, say who ruled and when.
#
# Ruled: Gate R, the Director, 2026-08-14, holding the register at the recorded recipe. The
# entry it admitted is E35's denoise sweep, and the tests below are what replaced this one —
# a can-fail advisory leg per rung that matters, which the empty assertion could never carry.


def test_a_measured_entry_requires_a_record_locator():
    """The measured kind's citation. Without it the entry is populated from memory however true."""
    band = Band(
        parameter="denoise",
        low=0.1,
        high=0.5,
        node_classes=frozenset({"KSampler"}),
        quote="q",
        mapping="m",
    )
    with pytest.raises(ValueError, match="carries no record"):
        EnvelopeEntry(
            checkpoint="zz_synthetic.safetensors",
            kind=EntryKind.STUDIO_MEASURED,
            bands=(band,),
        )


def test_a_measured_record_validates_every_field_it_promises():
    with pytest.raises(ValueError, match="requires an `experiment`"):
        _record(experiment="  ")
    with pytest.raises(ValueError, match="requires a `locator`"):
        _record(locator="")
    with pytest.raises(ValueError, match="not an ISO date"):
        _record(measured="last week")
    with pytest.raises(ValueError, match="requires a one-line `finding`"):
        _record(finding="")


def test_the_two_authorities_are_mutually_exclusive():
    """An entry claiming both looks doubly-sourced while a reader cannot tell which number came
    from where."""
    band = Band(
        parameter="denoise",
        low=0.1,
        high=0.5,
        node_classes=frozenset({"KSampler"}),
        quote="q",
        mapping="m",
    )
    with pytest.raises(ValueError, match="carries a measured record"):
        EnvelopeEntry(
            checkpoint="zz_synthetic.safetensors",
            source_url="https://example.invalid/card",
            retrieved="2026-08-14",
            kind=EntryKind.VENDOR,
            record=_record(),
            bands=(band,),
        )
    with pytest.raises(ValueError, match="carries a vendor source_url"):
        EnvelopeEntry(
            checkpoint="zz_synthetic.safetensors",
            source_url="https://example.invalid/card",
            retrieved="2026-08-14",
            kind=EntryKind.STUDIO_MEASURED,
            record=_record(),
            bands=(band,),
        )


def test_a_measured_entry_renders_its_record_as_the_citation():
    """Both kinds answer `citation`, and neither is vague about which one it is."""
    band = Band(
        parameter="denoise",
        low=0.1,
        high=0.5,
        node_classes=frozenset({"KSampler"}),
        quote="q",
        mapping="m",
    )
    entry = EnvelopeEntry(
        checkpoint="zz_synthetic.safetensors",
        kind=EntryKind.STUDIO_MEASURED,
        record=_record(),
        bands=(band,),
    )
    citation = entry.citation
    assert "studio measurement E99" in citation
    assert "docs/experiments/E99-synthetic.md" in citation
    assert "measured 2026-08-14" in citation
    # ...and it does not claim a vendor said so.
    assert "retrieved" not in citation

    vendor = _vendor_entry()
    assert vendor.citation.startswith("https://")
    assert "retrieved 2026-08-14" in vendor.citation


def test_the_shapes_are_exclusive_by_authority_too():
    """Amendment 5's boundary, in the constructor rather than in review.

    Rungs are the studio's; a declared absence is a claim about a publisher's card. An entry
    holding the other kind's shape is refused at construction, so the boundary cannot erode by
    someone appending a convenient field in a hurry.
    """
    ladder = MeasuredLadder(
        parameter="denoise",
        node_classes=frozenset({"KSampler"}),
        rungs=(Rung(value=0.9, outcome="held"),),
        context="a synthetic recipe",
    )
    with pytest.raises(ValueError, match="carries measured rungs"):
        EnvelopeEntry(
            checkpoint="zz_synthetic.safetensors",
            source_url="https://example.invalid/card",
            retrieved="2026-08-14",
            ladders=(ladder,),
        )
    with pytest.raises(ValueError, match="declares a documented absence"):
        EnvelopeEntry(
            checkpoint="zz_synthetic.safetensors",
            kind=EntryKind.STUDIO_MEASURED,
            record=_record(),
            ladders=(ladder,),
            documented_absent=(
                DocumentedAbsence(
                    parameter="cfg",
                    node_classes=frozenset({"KSampler"}),
                    reason="checked the card at this seat",
                ),
            ),
        )


def test_a_rung_without_an_outcome_and_a_ladder_without_its_recipe_are_refused():
    """A number with no result is a value someone tried; rungs with no recipe are advice."""
    with pytest.raises(ValueError, match="records no outcome"):
        Rung(value=0.9, outcome="  ")
    with pytest.raises(ValueError, match="carries no rungs"):
        MeasuredLadder(
            parameter="denoise",
            node_classes=frozenset({"KSampler"}),
            rungs=(),
            context="a synthetic recipe",
        )
    with pytest.raises(ValueError, match="states no context"):
        MeasuredLadder(
            parameter="denoise",
            node_classes=frozenset({"KSampler"}),
            rungs=(Rung(value=0.9, outcome="held"),),
            context="",
        )
    with pytest.raises(ValueError, match="two rungs at the same value"):
        MeasuredLadder(
            parameter="denoise",
            node_classes=frozenset({"KSampler"}),
            rungs=(Rung(value=0.9, outcome="held"), Rung(value=0.9, outcome="did not hold")),
            context="a synthetic recipe",
        )


def test_one_authority_may_claim_a_checkpoint_and_parameter_only_once():
    """The index's own refusal — the granularity change, made mechanical.

    Two entries of DIFFERENT kinds on one key is the ruled shape and builds fine. Two of the
    SAME kind is a duplicate whose disagreement nothing could resolve for a caller, and the
    index refuses rather than letting the later row win in silence, which is what the old
    checkpoint-keyed dict would have done.
    """
    band = Band(
        parameter="strength",
        low=0.8,
        high=1.0,
        node_classes=frozenset({"ControlNetApplyAdvanced"}),
        quote="q",
        mapping="m",
    )
    first = EnvelopeEntry(
        checkpoint="zz_synthetic.safetensors",
        source_url="https://example.invalid/card",
        retrieved="2026-08-14",
        bands=(band,),
    )
    second = dataclasses.replace(first, source_url="https://example.invalid/other-card")
    with pytest.raises(ValueError, match="two vendor entries both claim"):
        index(first, second)

    measured = EnvelopeEntry(
        checkpoint="zz_synthetic.safetensors",
        kind=EntryKind.STUDIO_MEASURED,
        record=_record(),
        ladders=(
            MeasuredLadder(
                parameter="strength",
                node_classes=frozenset({"ControlNetApplyAdvanced"}),
                rungs=(Rung(value=0.9, outcome="held"),),
                context="a synthetic recipe",
            ),
        ),
    )
    table = index(first, measured)
    assert [e.kind for e in table[("zz_synthetic.safetensors", "strength")]] == [
        EntryKind.VENDOR,
        EntryKind.STUDIO_MEASURED,
    ]


def test_a_measured_entry_works_end_to_end_through_the_check():
    """The schema is proven against the real check, not only against its constructor.

    Uses a synthetic checkpoint name so nothing in the shipped table moves.
    """
    raw = copy.deepcopy(load_raw(UNION_GRAPH))
    loader_id = next(
        nid for nid, n in raw.items() if n["class_type"] == "ControlNetLoader"
    )
    raw[loader_id]["inputs"]["control_net_name"] = "zz_synthetic.safetensors"
    entry = EnvelopeEntry(
        checkpoint="zz_synthetic.safetensors",
        kind=EntryKind.STUDIO_MEASURED,
        record=_record(finding="strength above 0.5 hardened interior speckle"),
        bands=(
            Band(
                parameter="strength",
                low=0.1,
                high=0.5,
                node_classes=frozenset({"ControlNetApplyAdvanced"}),
                quote="measured across the sweep's four arms",
                mapping="the graph's ControlNetApplyAdvanced.strength is the swept parameter",
            ),
        ),
    )
    result = check_declared_envelope(Graph.from_api_dict(raw), table=index(entry))
    # The recorded 0.9 is outside the synthetic 0.1-0.5 band, so this advises.
    assert result.verdict is Verdict.ADVISORY
    finding = _band_findings(result)[0]
    assert "studio measurement E99" in finding.message
    assert "hardened interior speckle" in finding.message


def test_the_table_covers_one_checkpoint_and_is_keyed_by_checkpoint_and_parameter():
    """Amendment 2 rules exactly one checkpoint; Amendment 5 puts two authorities on it.

    The key is the PAIR, and that is the shape change the ruling forced. Keyed by checkpoint
    alone, the studio's denoise measurement and the vendor's declared absence for denoise would
    have been one slot for two entries, and the second would have overwritten the first in
    silence.
    """
    assert list(ENVELOPE) == [(UNION.lower(), "strength"), (UNION.lower(), "denoise")]
    assert [e.kind for e in _entries("strength")] == [EntryKind.VENDOR]
    assert [e.kind for e in _entries("denoise")] == [
        EntryKind.VENDOR,
        EntryKind.STUDIO_MEASURED,
    ]
    vendor = _vendor_entry()
    assert vendor.source_url == "https://huggingface.co/InstantX/Qwen-Image-ControlNet-Union"
    assert vendor.retrieved == "2026-08-14"


def test_one_parameter_carries_two_authorities_and_neither_replaces_the_other():
    """Amendment 5's boundary rule, pinned at the data.

    The vendor's declared absence for denoise STAYS. The card still publishes nothing about it,
    and that stays true no matter what the studio measures in its own kitchen — so the measured
    entry answers the absence rather than erasing it, and a reader of the table sees both.
    """
    vendor, measured = _entries("denoise")
    assert "denoise" in {a.parameter for a in vendor.documented_absent}
    assert "denoise" in {ladder.parameter for ladder in measured.ladders}
    # ...and each entry carries exactly one authority, never both.
    assert vendor.record is None and not vendor.ladders
    assert measured.source_url == "" and not measured.documented_absent


def test_the_entry_carries_no_denoise_band_because_the_live_card_documents_none():
    """⚠ THE HEADLINE. The dispatch expected a 0.10-0.50 img2img denoise band here.

    Verified against the live card at build time, 2026-08-14, by two independent fetches (the
    rendered model page and raw/main/README.md): that band is not on the card. It documents
    controlnet_conditioning_scale in [0.8, 1.0] and nothing about denoise.

    This test pins the ABSENCE, so that if a later seat adds a denoise band it must first
    delete a test that says why there isn't one — which is the point at which someone re-reads
    the card instead of trusting the grounding.

    ⚑ Amendment 5 does not weaken this. The studio's measurement ships beside the absence, in a
    separate entry with a separate authority; the VENDOR entry still carries no denoise band,
    because the card still documents none.
    """
    entry = _vendor_entry()
    banded = {band.parameter for band in entry.bands}
    assert "denoise" not in banded, (
        "a denoise band appeared in the Qwen Union VENDOR entry. The live card documented none "
        "as of 2026-08-14 - re-verify against the card itself before adding one, and note that "
        "the E35 grounding's FLUX Union card is a DIFFERENT checkpoint. A studio measurement of "
        "denoise belongs in a STUDIO_MEASURED entry with its record, not here"
    )
    absent = {a.parameter for a in entry.documented_absent}
    assert "denoise" in absent, "the denoise absence must be declared, not merely omitted"


def test_the_only_shipped_band_is_the_conditioning_scale_the_card_actually_documents():
    entry = _vendor_entry()
    assert len(entry.bands) == 1
    band = entry.bands[0]
    assert (band.parameter, band.low, band.high) == ("strength", 0.8, 1.0)
    # The example values on the card are recorded as notes, never promoted to bands.
    assert any("example values" in note for note in entry.notes)
    banded = {b.parameter for b in entry.bands}
    assert "cfg" not in banded and "steps" not in banded


def test_the_recorded_union_graphs_raise_no_band_finding():
    """The no-false-advisory leg, for the BAND. 46 of 70 graphs load the Union at strength 0.9.

    0.9 sits inside the card's [0.8, 1.0], so a correct build must produce no band finding. A
    check that advised there would be advising against work the card endorses.

    ⚑ What changed at Amendment 5: these graphs no longer reach PASS. They reach ADVISORY,
    carrying the measurement of the denoise they run at — see the two tests below. The property
    this test guards is unchanged and is now stated precisely: the BAND finds nothing.
    """
    names = _graphs_loading(UNION)
    assert len(names) == 46, f"expected 46 Union graphs in the corpus, found {len(names)}"
    for name in names:
        result = check_declared_envelope(load_graph(name))
        assert _band_findings(result) == [], f"{name}: {result.findings}"
        assert UNION in result.checkpoints_covered
        assert ("strength", 0.9) in [(p, v) for _, p, v in result.parameters_checked]


# ---------------------------------------------------------------------------------------------
# The ruled-in measurement (Amendment 5), and the two rungs the ruling names by hand.
# ---------------------------------------------------------------------------------------------


def test_the_ruled_in_measurement_is_e35s_denoise_sweep_with_its_four_rungs():
    """The data, pinned against the record it came from.

    Numbers here were read out of `E35-clean-twins-report.md` section "2b — the denoise sweep",
    not recalled: 0.92 / 0.85 / 0.80 / 0.72 with the register C* and reverted-to-init column
    beside each. If a later seat edits a rung, this test is what makes them go back to the report.
    """
    entry = _measured_entry()
    # One ruling per entry, always. A second measurement enters through its own ruling, not by
    # being appended beside this one — which is what the deleted empty-dict gate was protecting,
    # stated now as a count rather than as a zero.
    assert len(STUDIO_MEASURED) == 1
    assert STUDIO_MEASURED[0] is entry
    assert entry.kind is EntryKind.STUDIO_MEASURED
    assert entry.record.experiment == "E35"
    assert "E35-clean-twins-report.md" in entry.record.locator
    assert "2b" in entry.record.locator
    assert entry.record.measured == "2026-08-14"
    assert "register dies before the specks do" in entry.record.finding

    ladder = entry.ladders[0]
    assert ladder.parameter == "denoise"
    assert [rung.value for rung in ladder.ordered] == [0.72, 0.80, 0.85, 0.92]
    by_value = {rung.value: rung for rung in ladder.rungs}
    assert "23.77" in by_value[0.92].outcome and "0.50%" in by_value[0.92].outcome
    assert "10.00" in by_value[0.85].outcome and "5.01%" in by_value[0.85].outcome
    assert "3.91" in by_value[0.80].outcome and "36.66%" in by_value[0.80].outcome
    assert "1.89" in by_value[0.72].outcome and "56.00%" in by_value[0.72].outcome
    # The validity envelope, without which the rungs would read as universal.
    for fragment in ("cn_strength 0.9", "steps 20", "cfg 2.5", "352x1024", "no LoRA"):
        assert fragment in ladder.context


def test_a_graph_at_the_recorded_denoise_advises_with_e35_and_the_hold():
    """0.92 — the value 46 recorded graphs run, and the value the Director held at Gate R.

    This is the can-fail leg the empty-dict gate could never have: the entry has to actually
    reach a real graph, name the experiment, and carry the ruling. A measurement that shipped
    into the table without being wired to the check would pass an empty-dict assertion and fail
    this one.

    That it fires on the HELD value is the ruling, not an oversight. A ladder endorses nothing,
    so there is no band-shaped 'inside' for it to be silent about — the caller is told what was
    measured at the value they are running, and ADVISORY exits 0, so nothing stops.
    """
    result = check_declared_envelope(load_graph(UNION_GRAPH))
    assert result.verdict is Verdict.ADVISORY
    finding = _measurement_finding(result)
    assert finding.node_id is not None, "a finding must name its node"
    assert finding.input_name == "denoise"
    assert "denoise is 0.92" in finding.message
    assert "E35" in finding.message
    assert "HOLD" in finding.message
    assert "23.77" in finding.message and "0.50%" in finding.message
    assert "E35-clean-twins-report.md" in finding.message
    assert "not a halt" in finding.hint


def test_a_graph_at_the_census_zero_denoise_advises_by_naming_the_register_destruction():
    """0.72 — where the speck census reaches zero, and why that is not a win.

    The finding has to carry the mechanism, not the headline: census-0 was bought by reverting
    56% of the figure toward the clay init. A report that said only 'census 0' would be read as
    a recommendation to run there, which is the exact misreading this entry exists to prevent.
    """
    result = check_declared_envelope(mutate(UNION_GRAPH, _set_denoise(0.72)))
    assert result.verdict is Verdict.ADVISORY
    finding = _measurement_finding(result)
    assert "denoise is 0.72" in finding.message
    assert "1.89" in finding.message
    assert "56.00%" in finding.message
    assert "register destruction" in finding.message
    assert "E35" in finding.message


def test_a_denoise_between_rungs_gets_both_and_nothing_is_interpolated():
    """0.88 was never measured. Two readings are reported, not a number nobody took."""
    result = check_declared_envelope(mutate(UNION_GRAPH, _set_denoise(0.88)))
    message = _measurement_finding(result).message
    assert "denoise 0.85" in message and "denoise 0.92" in message
    assert "0.88 ->" not in message, "a value nobody measured was rendered as a rung"


def test_a_denoise_off_the_end_of_the_sweep_says_so_rather_than_extrapolating():
    """A reading taken at 0.72 is not evidence about 0.40, and the finding says which it is."""
    result = check_declared_envelope(mutate(UNION_GRAPH, _set_denoise(0.40)))
    message = _measurement_finding(result).message
    assert "below every rung this sweep measured" in message
    assert "0.72 to 0.92" in message
    assert "nothing is extrapolated" in message


def test_both_authorities_report_on_denoise_in_the_same_run():
    """Amendment 5's boundary, at the OUTPUT rather than at the data.

    The vendor's declared absence is still a declined clause naming the value it cannot judge,
    and the studio's measurement is a finding. Two sentences about one parameter, neither
    speaking for the other.
    """
    result = check_declared_envelope(load_graph(UNION_GRAPH))
    declined = dict(result.clauses_declined)
    assert "CANNOT" in declined["envelope_bands.denoise"]
    assert "huggingface.co" in declined["envelope_bands.denoise"]
    assert "envelope_measured.denoise" in result.clauses_evaluated
    assert "studio measurement E35" in _measurement_finding(result).message


def test_a_measurement_with_no_operand_declines_rather_than_reporting_on_a_guess():
    """The ladder's own not-applied shape, matching the band's."""

    def drop_denoise(raw):
        for node in raw.values():
            if node["class_type"] in ("KSampler", "KSamplerAdvanced"):
                del node["inputs"]["denoise"]

    result = check_declared_envelope(mutate(UNION_GRAPH, drop_denoise))
    reason = dict(result.clauses_declined)["envelope_measured.denoise"]
    assert "reported against nothing rather than against a guess" in reason
    assert result.findings == ()


def test_the_measurement_never_halts_at_any_rung():
    """Check 8 stays ADVISORY-only with the measured kind populated, at every measured value."""
    for value in (0.72, 0.80, 0.85, 0.92, 1.0, 0.05):
        result = check_declared_envelope(mutate(UNION_GRAPH, _set_denoise(value)))
        assert result.verdict is Verdict.ADVISORY, value


def test_the_recorded_graphs_report_the_0_92_denoise_they_cannot_judge():
    """The finding this check exists for, reported honestly rather than judged against a guess.

    The graph runs denoise=0.92. The card documents no denoise band. So the check names the
    parameter, quotes the value, and says it cannot speak to it - which puts the fact in front
    of the caller at the moment it is cheap, without inventing the band that would judge it.
    """
    result = check_declared_envelope(load_graph(UNION_GRAPH))
    declined = dict(result.clauses_declined)
    key = "envelope_bands.denoise"
    assert key in declined, f"denoise absence not reported; declined: {list(declined)}"
    reason = declined[key]
    assert "0.92" in reason
    assert "CANNOT" in reason
    assert "huggingface.co/InstantX/Qwen-Image-ControlNet-Union" in reason
    assert "2026-08-14" in reason


def test_an_out_of_band_conditioning_scale_advises_and_names_its_evidence():
    graph = mutate(UNION_GRAPH, lambda raw: _set_controlnet_strength(raw, 0.4))
    result = check_declared_envelope(graph)
    assert result.verdict is Verdict.ADVISORY
    assert len(_band_findings(result)) == 1
    finding = _band_findings(result)[0]
    assert finding.code == "PARAMETER_OUTSIDE_DECLARED_ENVELOPE"
    assert finding.input_name == "strength"
    assert finding.node_id is not None, "a finding must name its node"
    assert "0.4" in finding.message
    assert "[0.8, 1]" in finding.message
    assert "controlnet_conditioning_scale in [0.8, 1.0]" in finding.message
    assert "retrieved 2026-08-14" in finding.message
    assert "ADVISORY, not a halt" in finding.hint


def test_the_band_edges_are_inclusive():
    """0.8 and 1.0 are documented values, not values just outside the documentation."""
    for value in (0.8, 1.0):
        result = check_declared_envelope(
            mutate(UNION_GRAPH, lambda raw, v=value: _set_controlnet_strength(raw, v))
        )
        assert _band_findings(result) == [], f"{value} should be inside [0.8, 1.0]"


# ---------------------------------------------------------------------------------------------
# The NOT_APPLICABLE shape: name what you could not see.
# ---------------------------------------------------------------------------------------------


def test_an_absent_checkpoint_returns_not_applicable_naming_it():
    """Amendment 2: an absent checkpoint returns NOT_APPLICABLE naming the checkpoint.

    Uses the recorded inpainting graphs, which load a real checkpoint the table does not cover -
    a natural fixture rather than a synthetic one.
    """
    assert len(_graphs_loading(INPAINTING)) == 24, "the inpainting half of the corpus moved"
    result = check_declared_envelope(load_graph(INPAINTING_GRAPH))
    assert result.verdict is Verdict.NOT_APPLICABLE
    assert result.findings == ()
    assert INPAINTING in result.checkpoints_not_in_table
    reason = dict(result.clauses_declined)["envelope_bands"]
    assert INPAINTING in reason
    assert "was not read" in reason


def test_the_uncovered_checkpoint_is_declared_absent_rather_than_silently_missing():
    """The boundary is named in the module, so a reader sees it without inferring it."""
    assert INPAINTING in DECLARED_ABSENT_CHECKPOINTS
    assert basename(INPAINTING).lower() not in ENVELOPE


def test_a_graph_with_no_checkpoint_at_all_declines_and_says_why():
    graph = Graph.from_api_dict(
        {"1": {"class_type": "PreviewImage", "inputs": {"images": ["2", 0]}}}
    )
    result = check_declared_envelope(graph)
    assert result.verdict is Verdict.NOT_APPLICABLE
    assert result.checkpoints_found == ()
    assert "no named checkpoint" in dict(result.clauses_declined)["envelope_bands"]


def test_not_applicable_is_not_reported_as_pass():
    """The repo's central refusal, at check 8: declining is not passing."""
    result = check_declared_envelope(load_graph(INPAINTING_GRAPH))
    assert result.verdict is not Verdict.PASS


# ---------------------------------------------------------------------------------------------
# Resolution: the band follows the checkpoint's wires.
# ---------------------------------------------------------------------------------------------


def test_a_band_is_not_applied_to_another_checkpoints_apply_node():
    """Linked resolution, and it is why `linked` exists.

    A graph carrying BOTH a covered and an uncovered control checkpoint must apply the covered
    entry's band only to the apply node wired to the covered loader. Built by splicing two real
    fixtures so the shape is the corpus's own, not an invention.
    """
    raw = copy.deepcopy(load_raw(UNION_GRAPH))
    loader_id = next(
        nid
        for nid, node in raw.items()
        if node["class_type"] == "ControlNetLoader"
        and basename(node["inputs"]["control_net_name"]) == UNION
    )
    apply_id = next(
        nid
        for nid, node in raw.items()
        if node["class_type"] == "ControlNetApplyAdvanced"
        and node["inputs"].get("control_net") == [loader_id, 0]
    )
    # A second, UNCOVERED control checkpoint with its own apply node, out of the covered band.
    raw["9001"] = {
        "class_type": "ControlNetLoader",
        "inputs": {"control_net_name": INPAINTING},
    }
    raw["9002"] = {
        "class_type": "ControlNetApplyAdvanced",
        "inputs": {
            "control_net": ["9001", 0],
            "strength": 0.2,
            "start_percent": 0.0,
            "end_percent": 1.0,
        },
    }
    result = check_declared_envelope(Graph.from_api_dict(raw))

    # 0.2 belongs to the uncovered checkpoint and must NOT be judged by the Union's band.
    assert _band_findings(result) == [], f"unexpected band findings: {result.findings}"
    checked = {(nid, param): val for nid, param, val in result.parameters_checked}
    assert checked[(apply_id, "strength")] == 0.9
    assert not any(param == "strength" and nid == "9002" for (nid, param) in checked)
    assert INPAINTING in result.checkpoints_not_in_table
    assert UNION in result.checkpoints_covered


def test_a_covered_checkpoint_with_no_apply_node_declines_that_band():
    """The band is not applied to a guess when its operand is absent."""
    def drop_apply(raw):
        for nid in [
            nid for nid, n in raw.items() if n["class_type"] == "ControlNetApplyAdvanced"
        ]:
            del raw[nid]["inputs"]["strength"]

    result = check_declared_envelope(mutate(UNION_GRAPH, drop_apply))
    reason = dict(result.clauses_declined)["envelope_bands.strength"]
    assert "not applied to anything rather than applied to a guess" in reason


def test_a_boolean_is_not_read_as_a_strength():
    """`bool` is an `int` subclass; a strength of `True` is a malformed graph, not a 1.0."""
    result = check_declared_envelope(
        mutate(UNION_GRAPH, lambda raw: _set_controlnet_strength(raw, True))
    )
    assert not [p for _, p, _ in result.parameters_checked if p == "strength"]


# ---------------------------------------------------------------------------------------------
# Conventions shared with every other check in this repo.
# ---------------------------------------------------------------------------------------------


def test_check_has_no_skip_parameter():
    """Reads the actual signature rather than trusting the docstring."""
    import inspect

    params = set(inspect.signature(check_declared_envelope).parameters)
    forbidden = {"skip", "force", "ignore", "warn_only", "soft", "disable", "enabled"}
    assert not (params & forbidden), f"check exposes a skip-shaped parameter: {params & forbidden}"


def test_the_result_carries_the_shared_accounting_fields():
    """An aggregator reads any check's result through these three; check 8 is no exception."""
    result = check_declared_envelope(load_graph(UNION_GRAPH))
    for field in ("verdict", "clauses_evaluated", "clauses_declined"):
        assert hasattr(result, field)
    assert dataclasses.is_dataclass(result)


def test_every_finding_names_its_node_and_the_authority_behind_it():
    """Amendment 2: every finding names its node and its evidence.

    Both kinds of finding are in this run, and the evidence differs by kind on purpose — a URL
    for what a vendor published, an experiment record for what the studio measured. A finding
    that blurred the two into "the source says" would be the defect the two-kind split exists
    to prevent.
    """
    result = check_declared_envelope(
        mutate(UNION_GRAPH, lambda raw: _set_controlnet_strength(raw, 0.1))
    )
    codes = {finding.code for finding in result.findings}
    assert codes == {"PARAMETER_OUTSIDE_DECLARED_ENVELOPE", "PARAMETER_HAS_A_STUDIO_MEASUREMENT"}
    for finding in result.findings:
        assert finding.node_id is not None
        assert finding.hint
        if finding.code == "PARAMETER_OUTSIDE_DECLARED_ENVELOPE":
            assert "huggingface.co" in finding.message
            assert "studio measurement" not in finding.message
        else:
            assert "studio measurement E35" in finding.message
            assert "huggingface.co" not in finding.message


def _set_controlnet_strength(raw: dict, value) -> None:
    """Mutate every ControlNetApplyAdvanced strength, so the FIRE case differs by one edit."""
    for node in raw.values():
        if node["class_type"] == "ControlNetApplyAdvanced":
            node["inputs"]["strength"] = value
