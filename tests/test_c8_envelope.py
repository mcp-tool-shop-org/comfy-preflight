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
    MeasuredRecord,
    basename,
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


def test_every_shipped_entry_is_cited_with_a_retrieval_date():
    """Amendment 2: an uncited entry FAILS a test. This is that test."""
    if not ENVELOPE:
        raise AssertionError("the envelope table is empty; day one ships one checkpoint")
    for key, entry in ENVELOPE.items():
        if not entry.source_url.startswith("https://"):
            raise AssertionError(f"{key}: source_url {entry.source_url!r} is not a URL")
        if not ISO_DATE.match(entry.retrieved):
            raise AssertionError(f"{key}: retrieved {entry.retrieved!r} is not an ISO date")
        for band in entry.bands:
            if not band.quote.strip():
                raise AssertionError(f"{key}.{band.parameter}: no quote from the source")
            if not band.mapping.strip():
                raise AssertionError(
                    f"{key}.{band.parameter}: no stated mapping from the card's parameter name "
                    "to the graph's input name"
                )
        for absence in entry.documented_absent:
            if not absence.reason.strip():
                raise AssertionError(f"{key}.{absence.parameter}: absence claimed without reason")


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
    with pytest.raises(ValueError, match="neither a band nor a documented absence"):
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


def test_the_measured_kind_ships_empty_until_the_advisor_rules_an_entry_in():
    """Amendment 3 adopted reading B as a CAPABILITY, gated as DATA.

    This test is the gate. Ruling a measured entry in must also delete this assertion, which
    makes the ruling a deliberate act rather than a quiet append.
    """
    assert STUDIO_MEASURED == {}
    assert all(e.kind is EntryKind.VENDOR for e in ENVELOPE.values())


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

    vendor = ENVELOPE[UNION.lower()]
    assert vendor.citation.startswith("https://")
    assert "retrieved 2026-08-14" in vendor.citation


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
    result = check_declared_envelope(
        Graph.from_api_dict(raw), table={"zz_synthetic.safetensors": entry}
    )
    # The recorded 0.9 is outside the synthetic 0.1-0.5 band, so this advises.
    assert result.verdict is Verdict.ADVISORY
    finding = result.findings[0]
    assert "studio measurement E99" in finding.message
    assert "hardened interior speckle" in finding.message


def test_the_day_one_entry_is_the_qwen_union_checkpoint_and_only_it():
    """Amendment 2 rules exactly one checkpoint for day one."""
    assert list(ENVELOPE) == [UNION.lower()]
    entry = ENVELOPE[UNION.lower()]
    assert entry.source_url == "https://huggingface.co/InstantX/Qwen-Image-ControlNet-Union"
    assert entry.retrieved == "2026-08-14"


def test_the_entry_carries_no_denoise_band_because_the_live_card_documents_none():
    """⚠ THE HEADLINE. The dispatch expected a 0.10-0.50 img2img denoise band here.

    Verified against the live card at build time, 2026-08-14, by two independent fetches (the
    rendered model page and raw/main/README.md): that band is not on the card. It documents
    controlnet_conditioning_scale in [0.8, 1.0] and nothing about denoise.

    This test pins the ABSENCE, so that if a later seat adds a denoise band it must first
    delete a test that says why there isn't one — which is the point at which someone re-reads
    the card instead of trusting the grounding.
    """
    entry = ENVELOPE[UNION.lower()]
    banded = {band.parameter for band in entry.bands}
    assert "denoise" not in banded, (
        "a denoise band appeared in the Qwen Union entry. The live card documented none as of "
        "2026-08-14 - re-verify against the card itself before adding one, and note that the "
        "E35 grounding's FLUX Union card is a DIFFERENT checkpoint"
    )
    absent = {a.parameter for a in entry.documented_absent}
    assert "denoise" in absent, "the denoise absence must be declared, not merely omitted"


def test_the_only_shipped_band_is_the_conditioning_scale_the_card_actually_documents():
    entry = ENVELOPE[UNION.lower()]
    assert len(entry.bands) == 1
    band = entry.bands[0]
    assert (band.parameter, band.low, band.high) == ("strength", 0.8, 1.0)
    # The example values on the card are recorded as notes, never promoted to bands.
    assert any("example values" in note for note in entry.notes)
    banded = {b.parameter for b in entry.bands}
    assert "cfg" not in banded and "steps" not in banded


def test_the_recorded_union_graphs_pass_their_documented_band():
    """The no-false-advisory leg. 46 of 70 graphs load the Union checkpoint at strength 0.9.

    0.9 sits inside the card's [0.8, 1.0], so a correct build must produce no finding. A check
    that advised here would be advising on work the card endorses.
    """
    names = _graphs_loading(UNION)
    assert len(names) == 46, f"expected 46 Union graphs in the corpus, found {len(names)}"
    for name in names:
        result = check_declared_envelope(load_graph(name))
        assert result.verdict is Verdict.PASS, f"{name}: {result.findings}"
        assert result.findings == ()
        assert UNION in result.checkpoints_covered
        assert ("strength", 0.9) in [(p, v) for _, p, v in result.parameters_checked]


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
    assert len(result.findings) == 1
    finding = result.findings[0]
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
        assert result.verdict is Verdict.PASS, f"{value} should be inside [0.8, 1.0]"


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
    assert result.verdict is Verdict.PASS, f"unexpected findings: {result.findings}"
    checked = {(nid, param): val for nid, param, val in result.parameters_checked}
    assert checked == {(apply_id, "strength"): 0.9}
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
    assert result.parameters_checked == ()


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


def test_every_finding_names_its_node():
    """Amendment 2: every finding names its node and its evidence."""
    result = check_declared_envelope(
        mutate(UNION_GRAPH, lambda raw: _set_controlnet_strength(raw, 0.1))
    )
    for finding in result.findings:
        assert finding.node_id is not None
        assert finding.hint
        assert "huggingface.co" in finding.message


def _set_controlnet_strength(raw: dict, value) -> None:
    """Mutate every ControlNetApplyAdvanced strength, so the FIRE case differs by one edit."""
    for node in raw.values():
        if node["class_type"] == "ControlNetApplyAdvanced":
            node["inputs"]["strength"] = value
