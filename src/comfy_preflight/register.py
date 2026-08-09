"""The register — what a subject DECLARES, against which a graph's construction is checked.

The register is the reference, and it comes from the subject's profile. This matters beyond
bookkeeping: **a gate's reference must be derived from something other than what it gates.**
Taking the adapter vocabulary from the graphs being checked would make check 2 a tautology
that passes review because the numbers look fine.

## Why `known_cards` exists, and what happens without it

Check 2's strongest clause is *no adapter card reference exists anywhere in the graph*. Stating
that requires knowing what an adapter card looks like — and the naive answer, "any
`.safetensors` string", is measurably wrong. Across 70 recorded graphs it matches the base
model, the CLIP, the VAE and the ControlNet on **every** graph, including all 43 that carry no
adapter at all. A check built that way halts every correct build on day one, which is how a
gate gets disabled by the third person who hits it.

So: `known_cards` is the declared vocabulary of adapter cards for this subject or project. When
it is empty, the vocabulary clause **is not askable**, and check 2 reports it as
NOT_APPLICABLE rather than passing it. The structural clauses (loader nodes, the consumer link)
need no vocabulary and are always evaluated.
"""

from __future__ import annotations

import dataclasses

# ComfyUI's built-in adapter loader classes. A custom loader outside this set is caught by
# `SUSPECTED_LOADER_SUBSTRING` below rather than evading the scan.
ADAPTER_LOADER_CLASSES = frozenset(
    {
        "LoraLoader",
        "LoraLoaderModelOnly",
        "LoraLoaderModelOnlyAdvanced",
        "HypernetworkLoader",
    }
)

# A class name we do not recognise but which names itself an adapter loader still trips the
# no-adapter direction. The bias is deliberate: an unknown loader class errs toward HALT in
# both directions - it does not satisfy a positive declaration, and it does not pass a
# negative one. A gate that fails open on an unrecognised node is not a gate.
SUSPECTED_LOADER_SUBSTRING = ("lora", "hypernetwork", "adapter")

# Input names that carry a card filename on a loader node.
CARD_INPUT_NAMES = frozenset({"lora_name", "hypernetwork_name", "adapter_name"})

# Input names carrying an adapter strength.
WEIGHT_INPUT_NAMES = ("strength_model", "strength", "strength_clip", "weight")


@dataclasses.dataclass(frozen=True)
class AdapterRegister:
    """What the subject declares about its style adapter.

    `declared=False` is the no-adapter condition, and the claim it makes is NOT "the weight is
    0.0" - it is that no loader node and no card reference exist anywhere in the graph.

    `declared=True` requires `card` and a positive `weight`; the mirror direction (a decided
    weight with no loader node) is the silently-inert failure this check exists to catch.
    """

    declared: bool
    card: str | None = None
    weight: float | None = None
    known_cards: frozenset[str] = frozenset()
    card_aliases: frozenset[str] = frozenset()
    loader_classes: frozenset[str] = ADAPTER_LOADER_CLASSES

    def __post_init__(self) -> None:
        # A malformed register would make the check answer a question nobody asked. These
        # raise rather than assert - a register error must not vanish under -O.
        if self.declared:
            if not self.card:
                raise ValueError(
                    "AdapterRegister(declared=True) requires `card`: declaring an adapter "
                    "without naming it cannot be checked against a graph"
                )
            if self.weight is None or self.weight <= 0:
                raise ValueError(
                    "AdapterRegister(declared=True) requires a positive `weight`; "
                    "a weight of 0.0 is not a declaration of an adapter, it is no adapter - "
                    "use declared=False"
                )
        else:
            if self.card is not None or self.weight is not None:
                raise ValueError(
                    "AdapterRegister(declared=False) must not carry a card or weight; "
                    "the no-adapter claim is about absence, and carrying either invites the "
                    "'weight 0.0' reading this check exists to reject"
                )

    @property
    def acceptable_cards(self) -> frozenset[str]:
        """The declared card plus any alias that names the same adapter.

        **Aliases exist because the recorded corpus contains two names for one adapter.** The
        same LoRA appears as

            mcp-tool-shop__saltroad-style-lora__saltroad_style_v2_lowlr_000001500.safetensors
            mikeyfrilot__saltroad-lora__saltroad_style_v2_lowlr_000001500.safetensors

        — identical weights, different cloud-side namespace prefix from a re-import under a
        different account. Exact-string comparison halts a correct build in that case, and the
        whole basename differs so basename comparison does not help either.

        **Aliases are declared, never inferred.** Stripping a prefix or matching on a common
        substring would be a heuristic that also silently accepts a genuinely wrong card whose
        name happened to share a tail. The register says which names are the same adapter; the
        check does not guess.
        """
        cards = set(self.card_aliases)
        if self.card:
            cards.add(self.card)
        return frozenset(cards)

    @property
    def vocabulary(self) -> frozenset[str]:
        """Every card name this register can RECOGNISE in a graph.

        Wider than `acceptable_cards`: it includes cards known to the project but not declared
        for this subject, so the no-adapter direction can catch a reference to any of them.
        """
        return frozenset(set(self.known_cards) | set(self.acceptable_cards))
