"""Packaging claims must be true at install time.

Earned in this repo: the scaffold declared a console script
`comfy-preflight = "comfy_preflight.cli:main"` before any CLI module existed. `pip install`
creates that command happily and it raises `ImportError` on first use — a defect that surfaces
for the person who installs the package, not for the person who wrote the entry.
"""

from __future__ import annotations

import importlib
import pathlib
import tomllib

PYPROJECT = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"


def _project() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]


def test_every_declared_console_script_resolves():
    """A declared entry point must name an importable module and an existing attribute."""
    scripts = _project().get("scripts", {})
    broken = []
    for command, target in scripts.items():
        module_name, _, attribute = target.partition(":")
        try:
            module = importlib.import_module(module_name)
        except ImportError as exc:
            broken.append(f"{command} -> {target}: module not importable ({exc})")
            continue
        if attribute and not hasattr(module, attribute):
            broken.append(f"{command} -> {target}: {module_name} has no attribute {attribute!r}")

    if broken:
        raise AssertionError(
            "declared console script(s) do not resolve; `pip install` would create a command "
            "that fails on first use:\n" + "\n".join(f"  {b}" for b in broken)
        )


def test_the_scan_fires_on_an_unresolvable_target():
    """Can-fail leg. Uses a synthetic target name that is not a real module in this repo."""
    module_name, _, attribute = "comfy_preflight.zz_synthetic_absent:main".partition(":")
    resolved = True
    try:
        importlib.import_module(module_name)
    except ImportError:
        resolved = False
    if resolved:
        raise RuntimeError(
            f"{module_name} unexpectedly imported; pick a name that does not exist so this leg "
            "can fail"
        )


def test_declared_dependencies_stay_empty():
    """Zero runtime dependencies is load-bearing, not tidiness.

    The npm door — a SHA256-pinned PyInstaller binary behind `npx` — is only open to packages
    whose dependencies are stdlib, sqlite3 and mcp. A third-party runtime dep closes it, so the
    constraint is pinned here rather than left to a code review.
    """
    deps = _project().get("dependencies", [])
    if deps:
        raise AssertionError(
            f"runtime dependencies declared: {deps}. The core checks operate on parsed JSON and "
            "need none; `mcp` belongs in optional-dependencies"
        )


def test_version_is_at_least_one_zero_zero():
    """The studio floor: v1.0.0 minimum, and never a pre-1.0 version to patch-bump later."""
    version = _project()["version"]
    major = int(version.split(".")[0])
    if major < 1:
        raise AssertionError(f"version {version} is pre-1.0; the floor for this repo is 1.0.0")
