"""Fixture loading. Reads ONLY the copies under tests/fixtures/graphs.

The recorded source trees are not in git and have no revert. Nothing in the suite may reach
them — `test_fixtures_are_self_contained.py` fails if any test file names an absolute source
path.
"""

from __future__ import annotations

import copy
import json
import pathlib
from typing import Any

import pytest

from comfy_preflight.graph import Graph

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
GRAPHS = FIXTURES / "graphs"

# Named fixtures used by the register tests. The two branch pairs are the same subject line
# recorded with and without the style adapter, and they differ by exactly one node.
ADAPTER_17 = "facet_E08__ARMB__out__stroke_1_y+090_e+00_workflow.json"
NO_ADAPTER_16 = "facet_next__E13_stroke__run__graphs__workflow_stroke1_y292.json"
ADAPTER_15 = "facet_next__E04_g7__workflow_7_G7_headnoun.json"
NO_ADAPTER_14 = "facet_next__E12_twins__graphs__workflow_twin_0.json"

# The adapter cards in the recorded corpus. TWO names, one underlying LoRA: the same weights
# re-imported under a different cloud-side namespace. Measured, not assumed - a 69-graph walk
# reports only the first, because the second is carried by the 70th graph alone.
CORPUS_CARD = (
    "mcp-tool-shop__saltroad-style-lora__saltroad_style_v2_lowlr_000001500.safetensors"
)
CORPUS_CARD_ALIAS = (
    "mikeyfrilot__saltroad-lora__saltroad_style_v2_lowlr_000001500.safetensors"
)
CORPUS_CARDS = frozenset({CORPUS_CARD, CORPUS_CARD_ALIAS})

# The consumer whose model input the adapter routes through in this corpus.
CONSUMER = ("6", "model")


def load_raw(name: str) -> dict[str, Any]:
    return json.loads((GRAPHS / name).read_text(encoding="utf-8"))


def load_graph(name: str) -> Graph:
    return Graph.from_api_dict(load_raw(name))


def mutate(name: str, fn) -> Graph:
    """Load a fixture, apply `fn` to a deep copy of the raw dict, and parse the result.

    Can-fail fixtures are produced by mutating a good one so the PASS case and the FIRE case
    differ by exactly the edit under test. The copied fixture on disk is never modified.
    """
    raw = copy.deepcopy(load_raw(name))
    fn(raw)
    return Graph.from_api_dict(raw)


def all_graph_names() -> list[str]:
    return sorted(p.name for p in GRAPHS.glob("*.json"))


@pytest.fixture
def corpus_card() -> str:
    return CORPUS_CARD
