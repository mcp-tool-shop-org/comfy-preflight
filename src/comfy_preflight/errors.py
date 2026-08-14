"""The halt surface.

Two laws are encoded here rather than documented elsewhere, because a law that lives only
in prose is one nobody's code obeys:

1. **A gate raises; it is never a bare `assert`.** `python -O` and `PYTHONOPTIMIZE=1` delete
   `assert` statements silently and execution continues past them. A check that decides
   whether an irreversible step proceeds must `raise`. `PreflightHalt` is that raise, and
   `tests/test_no_assert_in_library.py` fails if the halt ever degrades to an assert.

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

    ADVISORY is equally load-bearing and is equally not a synonym for PASS. It reports a fact
    the caller should see that is **not** grounds to stop: check 8's out-of-band parameter is
    the case it was added for. The studio ran an out-of-band value deliberately and the
    Director approved the result it produced — a documented band is documentation, not a gate.
    An advisory that halted would fire on correct work, and a gate that halts correct work gets
    disabled by the third person who hits it.
    """

    PASS = "pass"
    HALT = "halt"
    ADVISORY = "advisory"
    NOT_APPLICABLE = "not_applicable"


# The merge order, ratified by Amendment 2: HALT > ADVISORY > NOT_APPLICABLE > PASS.
#
# NOT_APPLICABLE outranking PASS is the surprising rung and it is deliberate. A run where one
# check declined and the rest passed has NOT checked everything, and reporting PASS for it
# would let the declined clause disappear behind the passing ones — the same collapse the
# Verdict docstring above refuses. Declining is louder than passing.
_RANK: dict[str, int] = {
    Verdict.PASS.value: 0,
    Verdict.NOT_APPLICABLE.value: 1,
    Verdict.ADVISORY.value: 2,
    Verdict.HALT.value: 3,
}


def merge_verdicts(verdicts: "list[Verdict] | tuple[Verdict, ...]") -> Verdict:
    """Reduce many check verdicts to one, by the ratified order.

    An empty sequence returns NOT_APPLICABLE rather than PASS. Nothing ran, so nothing passed —
    returning PASS there would be a gate that cannot fail, reached by running no checks at all.
    """
    if not verdicts:
        return Verdict.NOT_APPLICABLE
    return max(verdicts, key=lambda v: _RANK[v.value])


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

    ## Why the halt carries the whole report

    `report` is the aggregator's full structured result, attached when the aggregator raises.
    It exists so that **there is exactly one entry point** into a preflight run: a second,
    non-raising `preflight_report()` for the CLI and the MCP to call would be a skip flag with
    a different name — a caller on the submit path could reach for it and get a value back
    where the gate should have stopped them. Instead the halt itself carries everything a
    renderer needs, so the CLI and the MCP catch it and print, while the submit path simply
    lets it propagate.

    It is `None` when a single check raises on its own, because a single check has no
    aggregate report to carry.
    """

    def __init__(
        self,
        check: str,
        defects: list[Defect],
        *,
        report: object | None = None,
    ) -> None:
        if not defects:
            # An empty halt would be a gate that fired without evidence. Refuse to construct
            # one — this is a programming error in a check, not a graph defect.
            raise ValueError(
                "PreflightHalt requires at least one Defect; "
                "a gate that fires must name what it found"
            )
        self.check = check
        self.defects = list(defects)
        # Typed `object` rather than the aggregate result: errors.py is the bottom of the
        # import graph and importing the aggregator here would make it a cycle. The attribute
        # is documented, not typed, and the aggregator's tests pin what it actually holds.
        self.report = report
        body = "\n".join(f"  - {d}" for d in self.defects)
        super().__init__(f"{check} HALT ({len(self.defects)} defect(s)):\n{body}")
