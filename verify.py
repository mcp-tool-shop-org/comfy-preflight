#!/usr/bin/env python3
"""The verify gate — test + build + smoke, in one command, on any platform.

    python verify.py

One script rather than a `verify.ps1` plus a `verify.sh`, because the two would drift and the
CI leg would then be verifying something the rig does not. This runs on the rig and in the
release workflow unchanged.

## What it runs, and why each leg is here

1. **The suite, three times** — normal, `-O`, and `PYTHONOPTIMIZE=1`. Not redundancy: `-O` and
   `PYTHONOPTIMIZE` delete `assert` statements, and this package's gates `raise` precisely so
   they survive that. A suite green only under normal interpretation would not prove it.
2. **The distribution builds** — sdist and wheel. A package that tests green and cannot build is
   not shippable, and the failure otherwise surfaces at release time.
3. **The wheel runs a VERB from a clean venv, outside a checkout.** This is the leg that earns
   its place. `--help` and `--version` are a floor, not a gate: they touch no fixture, no graph
   and no envelope table, so they stay green through exactly the packaging defects that break a
   user. So the smoke test installs the built wheel into a throwaway venv, changes to a
   directory that is not this repo, and runs `check` on a graph — the thing a user runs.

Exit code is 0 when every leg passes and 1 when any fails, with the failing leg named.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
FIXTURE = (
    ROOT / "tests" / "fixtures" / "graphs" / "facet_next__E12_twins__graphs__workflow_twin_0.json"
)


def run(label: str, argv: list[str], *, cwd: pathlib.Path | None = None, env: dict | None = None):
    """Run one leg. Returns (ok, output)."""
    merged = {**os.environ, **(env or {})}
    print(f"\n=== {label} ===", flush=True)
    proc = subprocess.run(
        argv, cwd=str(cwd or ROOT), env=merged, capture_output=True, text=True
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    print(output.rstrip()[-4000:], flush=True)
    return proc.returncode == 0, output


def main() -> int:
    failures: list[str] = []
    py = sys.executable

    # ---- 1. the suite, in all three interpreter modes ------------------------------------
    legs = [
        ("pytest (normal)", [py, "-m", "pytest", "-q"], None),
        ("pytest (-O, assert-stripped)", [py, "-O", "-m", "pytest", "-q"], None),
        ("pytest (PYTHONOPTIMIZE=1)", [py, "-m", "pytest", "-q"], {"PYTHONOPTIMIZE": "1"}),
    ]
    for label, argv, env in legs:
        ok, _ = run(label, argv, env=env)
        if not ok:
            failures.append(label)

    # ---- 2. the distribution builds ------------------------------------------------------
    dist = ROOT / "dist"
    if dist.exists():
        shutil.rmtree(dist)
    ok, _ = run("build sdist + wheel", [py, "-m", "build"])
    if not ok:
        failures.append("build sdist + wheel")
        print("\nverify: the build failed, so the wheel smoke test cannot run", flush=True)
        return _report(failures)

    wheels = sorted(dist.glob("*.whl"))
    sdists = sorted(dist.glob("*.tar.gz"))
    if not wheels or not sdists:
        failures.append(f"build produced wheel={len(wheels)} sdist={len(sdists)}, expected 1 each")
        return _report(failures)

    # ---- 3. the wheel runs a VERB from a clean venv, outside a checkout -------------------
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = pathlib.Path(tmp)
        venv = tmpdir / "venv"
        ok, _ = run("create a clean venv", [py, "-m", "venv", str(venv)])
        if not ok:
            failures.append("create a clean venv")
            return _report(failures)

        vpy = venv / ("Scripts" if os.name == "nt" else "bin") / (
            "python.exe" if os.name == "nt" else "python"
        )
        ok, _ = run("install the built wheel", [str(vpy), "-m", "pip", "install", "-q", str(wheels[0])])
        if not ok:
            failures.append("install the built wheel")
            return _report(failures)

        # The floor. Green through the packaging defects that break a user, kept as a floor and
        # labelled as one rather than removed, so nobody re-promotes it to the gate.
        ok, _ = run("floor: --version", [str(vpy), "-m", "comfy_preflight.cli", "--version"], cwd=tmpdir)
        if not ok:
            failures.append("floor: --version")

        # THE GATE: a real verb, on a real graph, from a directory that is not this repo.
        graph = tmpdir / "graph.json"
        graph.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        ok, output = run(
            "gate: `check` on a graph, outside the checkout",
            [str(vpy), "-m", "comfy_preflight.cli", "check", str(graph), "--json"],
            cwd=tmpdir,
        )
        if not ok:
            failures.append("gate: `check` on a graph, outside the checkout")
        else:
            try:
                payload = json.loads(output[output.index("{") :])
                ran = payload.get("checks_run")
                if ran != [1, 2, 4, 5, 8]:
                    failures.append(f"gate: checks_run was {ran}, expected [1, 2, 4, 5, 8]")
            except (ValueError, json.JSONDecodeError) as exc:
                failures.append(f"gate: --json did not parse ({exc})")

        # THE HALT, from outside the checkout: exit 1 on the recorded 1066 frame. A verb that
        # only ever returns 0 would not prove the gate survived packaging.
        proc = subprocess.run(
            [
                str(vpy), "-m", "comfy_preflight.cli", "check", str(graph),
                "--input-dims", "1066x1024",
            ],
            cwd=str(tmpdir), capture_output=True, text=True,
        )
        print("\n=== gate: the recorded 1066 frame must exit 1 ===", flush=True)
        print(f"exit={proc.returncode}", flush=True)
        if proc.returncode != 1:
            failures.append(f"gate: the 1066 halt exited {proc.returncode}, expected 1")

    return _report(failures)


def _report(failures: list[str]) -> int:
    print("\n" + "=" * 70, flush=True)
    if failures:
        print(f"verify: FAILED ({len(failures)} leg(s))", flush=True)
        for name in failures:
            print(f"  - {name}", flush=True)
        return 1
    print("verify: all legs passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
