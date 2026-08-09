"""The checks. Each one halts by raising; none takes a skip parameter.

Build state is in the README's table and is the honest state of the repo.

Each check exports its own `CheckResult` because the checks decompose by what they know:
1, 4 and 5 are graph-structural and know nothing about subjects; 2 and 3 resolve against a
profile; 6 is transport-side. Their results carry the same three accounting fields —
`verdict`, `clauses_evaluated`, `clauses_declined` — so an aggregator can read any of them,
plus whatever else that check measured.
"""

from comfy_preflight.checks import c1_link_topology, c2_register, c4_saved_is_submitted, c5_frame
from comfy_preflight.checks.c1_link_topology import NodeSchema, check_link_topology
from comfy_preflight.checks.c2_register import check_register_scan
from comfy_preflight.checks.c4_saved_is_submitted import check_saved_is_submitted
from comfy_preflight.checks.c5_frame import (
    DECLARED_ABSENT_FAMILIES,
    FAMILIES,
    FrameConstraint,
    check_generator_legal_frame,
)

__all__ = [
    "NodeSchema",
    "FrameConstraint",
    "FAMILIES",
    "DECLARED_ABSENT_FAMILIES",
    "check_link_topology",
    "check_register_scan",
    "check_saved_is_submitted",
    "check_generator_legal_frame",
    "c1_link_topology",
    "c2_register",
    "c4_saved_is_submitted",
    "c5_frame",
]
