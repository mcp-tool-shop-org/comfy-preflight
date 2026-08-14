#!/usr/bin/env node
"use strict";

// Pure JSON config — npm-launcher derives the asset names from convention:
//   binary:    comfy-preflight-1.0.0-linux-x64  /  comfy-preflight-1.0.0-win-x64.exe
//   checksums: checksums-1.0.0.txt
// It downloads from the GitHub Release for `tag`, verifies SHA256, caches, and
// execs with argv passthrough.
//
// This is the org's standard wrapper and it is standard ON PURPOSE. The
// alternative — bootstrapping pip — trades away the thing npm-launcher exists
// to provide: `npx` that works with NO Python on the machine, plus SHA256
// verification of what actually gets executed.
//
// The door is only open because this package's dependencies are stdlib plus the
// optional mcp SDK. pyproject.toml pins that with a test; adding a third-party
// runtime dependency closes it, and the comment there says so at the site.
//
// `version` and `tag` are checked against pyproject.toml and the git tag by the
// release workflow's version gate. Drift here ships a wrapper that 404s at a
// user's npx rather than failing in CI.
process.env.MCPTOOLSHOP_LAUNCH_CONFIG = JSON.stringify({
  toolName: "comfy-preflight",
  owner: "mcp-tool-shop-org",
  repo: "comfy-preflight",
  version: "1.0.0",
  tag: "v1.0.0",
});

require("@mcptoolshop/npm-launcher/bin/mcptoolshop-launch.js");
