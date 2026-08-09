"""The halt surface.

Two laws are encoded here rather than documented elsewhere, because a law that lives only
in prose is one nobody's code obeys:

1. **A gate raises; it is never a bare `assert`.** `python -O` and `PYTHONOPTIMIZE=1` delete
   `assert` statements silently and execution continues past them. A check that decides
   whether an irreversible step proceeds must `raise`. `PreflightHalt` is that raise, and
   `tests/test_gates_survive_O.py` fails if the halt ever degrades to an assert.

2. **There is no skip flag.** No parameter, environment variable, or keyword on this
   exception or on any check suppresses it. A gate a caller can turn off at the call site is
   a transport, not a guard.
"""

from __future__ import annotations

import dataclasses
import enum


class Verdict(enum.Enum):
    """The result of one check.

    NOT_APPLICABLE is load-bearing and is not a synonym for PASS. A check that found nothing
    to examine has not passed — it has declined to answer, and saying so is the difference
    between a gate and a check that cannot fail. Check 5 exists in this state on every
    img2img graph, where the frame is inherited from the input image rather than declared in
    the graph; reporting that as PASS would claim a frame was examined when none was seen.
    """

    PASS = "pass"
    HALT = "halt"
    NOT_APPLICABLE = "not_applicable"


@dataclasses.dataclass(frozen=True)
class Defect:
    """One named defect, located.

    The structured error shape the studio's standards require: a stable machine-readable
    `code`, a human `message`, and a `hint` that says what to do. `node_id` and `input_name`
    locate it in the graph, because "the graph is wrong" is not an actionable halt.
    """

    code: str
    message: str
    hint: str
    node_id: str | None = None
    input_name: str | None = None

    def __str__(self) -> str:
        where = ""
        if self.node_id is not None:
            where = f" [node {self.node_id}"
            if self.input_name is not None:
                where += f".{self.input_name}"
            where += "]"
        return f"{self.code}{where}: {self.message}\n  hint: {self.hint}"


class PreflightHalt(Exception):
    """Raised when a check finds a defect. Carries every defect, not just the first.

    Deliberately a subclass of `Exception` and not of `AssertionError`: `-O` does not remove
    `raise`, and nothing in this class's construction depends on `__debug__`.
    """

    def __init__(self, check: str, defects: list[Defect]) -> None:
        if not defects:
            # An empty halt would be a gate that fired without evidence. Refuse to construct
            # one — this is a programming error in a check, not a graph defect.
            raise ValueError(
                "PreflightHalt requires at least one Defect; "
                "a gate that fires must name what it found"
            )
        self.check = check
        self.defects = list(defects)
        body = "\n".join(f"  - {d}" for d in self.defects)
        super().__init__(f"{check} HALT ({len(self.defects)} defect(s)):\n{body}")
