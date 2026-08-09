"""The checks. Each one halts by raising; none takes a skip parameter.

Build state is in the README's table and is the honest state of the repo.
"""

from comfy_preflight.checks.c2_register import CheckResult, check_register_scan

__all__ = ["CheckResult", "check_register_scan"]
