"""comfy-preflight — a gate on a ComfyUI workflow graph, run before submission.

Submitting a graph is the one irreversible act in a generation pipeline: a completed cloud
job is billed, and the only compensator is "cancel it if it is still queued, otherwise
none." This package is a compensator you run *before* instead of after.

It does not submit, does not repair a graph, and never sees an output.

Nothing is exported here yet beyond the version and the error surface — see the README's
build-state table for which checks exist. That table is the honest state of this repo.
"""

__version__ = "1.0.0"

from comfy_preflight.errors import PreflightHalt, Verdict, merge_verdicts

__all__ = ["__version__", "PreflightHalt", "Verdict", "merge_verdicts"]
