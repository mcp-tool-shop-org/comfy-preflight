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


def test_every_site_that_declares_a_version_agrees():
    """Four files declare this version, and the npm launcher pins an EXACT tag and asset name.

    The release workflow gates on this too, but it gates at tag-push — after the release commit
    is written. Drift caught here is a local edit; drift caught there is a re-cut tag. The npm
    wrapper is the reason it matters: a version mismatch does not fail loudly, it ships a
    launcher that 404s at a user's `npx`.
    """
    import json
    import re

    root = PYPROJECT.parent
    pyproject = _project()["version"]
    dunder = re.search(
        r'__version__ = "([^"]+)"',
        (root / "src" / "comfy_preflight" / "__init__.py").read_text(encoding="utf-8"),
    ).group(1)
    pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))["version"]
    launcher = (root / "bin" / "comfy-preflight.js").read_text(encoding="utf-8")
    bin_version = re.search(r'version:\s*"([^"]+)"', launcher).group(1)
    bin_tag = re.search(r'tag:\s*"([^"]+)"', launcher).group(1)

    declared = {
        "pyproject.toml": pyproject,
        "__init__.py": dunder,
        "package.json": pkg,
        "bin/comfy-preflight.js": bin_version,
    }
    disagreeing = {k: v for k, v in declared.items() if v != pyproject}
    if disagreeing:
        raise AssertionError(
            f"version sites disagree with pyproject ({pyproject}): {disagreeing}"
        )
    if bin_tag != f"v{pyproject}":
        raise AssertionError(
            f"bin/comfy-preflight.js pins tag {bin_tag!r}, but version {pyproject} means the tag "
            f"must be 'v{pyproject}' - npm-launcher fetches the release named by this exact tag"
        )


def test_the_npm_launcher_names_the_assets_the_release_workflow_builds():
    """The launcher's tool name keys every asset filename. A rename here is a 404 at npx."""
    import json
    import re

    root = PYPROJECT.parent
    launcher = (root / "bin" / "comfy-preflight.js").read_text(encoding="utf-8")
    tool = re.search(r'toolName:\s*"([^"]+)"', launcher).group(1)
    workflow = (root / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    if f"{tool}-${{VERSION}}-" not in workflow.replace("${VERSION}", "${VERSION}"):
        # The workflow renames the PyInstaller output to <tool>-<version>-<label>[.exe].
        if f'out/{tool}-' not in workflow:
            raise AssertionError(
                f"release.yml does not produce assets named {tool}-<version>-<label>; "
                "npm-launcher derives that name by convention and would 404"
            )

    pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
    if list(pkg["bin"]) != [tool]:
        raise AssertionError(f"package.json bin is {list(pkg['bin'])}, expected [{tool!r}]")
    # npm 11's bin normalizer silently REMOVES a bin whose value leads with './', leaving the
    # installed package with no command at all.
    if pkg["bin"][tool].startswith("./"):
        raise AssertionError(
            f"package.json bin.{tool} leads with './' - npm's normalizer removes such a bin and "
            "the installed package would have no command"
        )
    if not pkg.get("repository", {}).get("url", "").startswith("git+https://github.com/"):
        raise AssertionError(
            "package.json needs repository.url matching the GitHub repo, or `npm publish "
            "--provenance` fails E422 after the provenance statement is already logged"
        )


def test_version_is_at_least_one_zero_zero():
    """The studio floor: v1.0.0 minimum, and never a pre-1.0 version to patch-bump later."""
    version = _project()["version"]
    major = int(version.split(".")[0])
    if major < 1:
        raise AssertionError(f"version {version} is pre-1.0; the floor for this repo is 1.0.0")
