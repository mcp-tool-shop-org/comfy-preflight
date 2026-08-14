"""comfy-preflight — a gate on a ComfyUI workflow graph, run before submission.

Submitting a graph is the one irreversible act in a generation pipeline: a completed cloud
job is billed, and the only compensator is "cancel it if it is still queued, otherwise
none." This package is a compensator you run *before* instead of after.

It does not submit, does not repair a graph, and never sees an output.

`preflight()` is the function the adoption contract names: call it **in-process on the submit
path**, and let it raise. See the README's build-state table for which checks it composes; that
table is the honest state of this repo.
"""

__version__ = "1.0.0"

from comfy_preflight.aggregate import PreflightResult, preflight
from comfy_preflight.errors import Defect, PreflightHalt, Verdict, merge_verdicts

__all__ = [
    "__version__",
    "preflight",
    "PreflightResult",
    "Defect",
    "PreflightHalt",
    "Verdict",
    "merge_verdicts",
]
