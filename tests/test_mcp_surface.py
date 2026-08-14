"""The MCP surface — a transport over the same in-process function.

The property this file exists to pin: **the MCP is not a second implementation.** Its output is
byte-identical to the library's, it holds no opinion about what matters in a result, and it
does not become a production gate by existing.
"""

from __future__ import annotations

import asyncio
import inspect
import json

import pytest
from conftest import CORPUS_CARD, CORPUS_CARD_ALIAS, NO_ADAPTER_14, load_raw

from comfy_preflight import mcp_server, preflight
from comfy_preflight.errors import PreflightHalt
from comfy_preflight.graph import Graph
from comfy_preflight.register import AdapterRegister

mcp = pytest.importorskip("mcp", reason="the MCP surface is an optional extra")

REGISTER = {"declared": False, "known_cards": [CORPUS_CARD, CORPUS_CARD_ALIAS]}
NO_ADAPTER = AdapterRegister(declared=False, known_cards=frozenset({CORPUS_CARD, CORPUS_CARD_ALIAS}))


def _self_linked() -> dict:
    raw = load_raw(NO_ADAPTER_14)
    node_id = next(nid for nid, node in raw.items() if node["class_type"] == "VAEDecode")
    raw[node_id]["inputs"]["samples"] = [node_id, 0]
    return raw


def _out_of_band() -> dict:
    raw = load_raw(NO_ADAPTER_14)
    for node in raw.values():
        if node["class_type"] == "ControlNetApplyAdvanced":
            node["inputs"]["strength"] = 0.4
    return raw


# ---------------------------------------------------------------------------------------------
# The load-bearing property: a transport, not a second implementation.
# ---------------------------------------------------------------------------------------------


def test_the_tool_returns_exactly_what_the_library_returns():
    """Byte-identical, not merely equivalent. A transport that reshaped the result would be a
    second opinion about what matters in a preflight run."""
    raw = load_raw(NO_ADAPTER_14)
    through_mcp = mcp_server.run_preflight(raw, register=REGISTER, input_dims=[1072, 1024])
    in_process = preflight(
        Graph.from_api_dict(raw), NO_ADAPTER, (1072, 1024)
    ).to_dict()
    assert json.dumps(through_mcp, sort_keys=True) == json.dumps(in_process, sort_keys=True)


def test_a_halt_returns_the_same_report_the_library_raises():
    raw = _self_linked()
    through_mcp = mcp_server.run_preflight(raw, register=REGISTER)
    with pytest.raises(PreflightHalt) as exc:
        preflight(Graph.from_api_dict(raw), NO_ADAPTER)
    assert through_mcp == exc.value.report.to_dict()


def test_a_halt_is_a_successful_call_not_a_tool_error():
    """Reporting a halt as a protocol failure would throw away the structure the caller needs,
    and leave a client retrying a call that keeps succeeding at finding the same defect."""
    payload = mcp_server.run_preflight(_self_linked(), register=REGISTER)
    assert payload["verdict"] == "halt"
    codes = [f["code"] for check in payload["checks"] for f in check["findings"]]
    assert "SELF_LINK" in codes


def test_an_advisory_comes_back_as_an_advisory_verdict():
    payload = mcp_server.run_preflight(_out_of_band(), register=REGISTER)
    assert payload["verdict"] == "advisory"


def test_the_tool_body_imports_no_mcp_so_it_is_testable_without_the_sdk():
    """The core package keeps zero runtime dependencies, and that is load-bearing: the npm door
    is only open to packages whose dependencies are stdlib, sqlite3 and mcp."""
    source = inspect.getsource(mcp_server.run_preflight)
    assert "import mcp" not in source
    assert "MCPServer" not in source


def test_nothing_imports_mcp_at_module_load():
    """`import comfy_preflight.mcp_server` must work with the extra absent."""
    import ast
    import pathlib

    tree = ast.parse(pathlib.Path(mcp_server.__file__).read_text(encoding="utf-8"))
    top_level = [
        node
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    names = [
        alias.name if isinstance(node, ast.Import) else (node.module or "")
        for node in top_level
        for alias in node.names
    ]
    assert not any(n.split(".")[0] == "mcp" for n in names), (
        f"mcp is imported at module load: {names}. It is an optional extra and the import "
        "belongs inside the function that needs it"
    )


# ---------------------------------------------------------------------------------------------
# The registered tool, against the real SDK.
# ---------------------------------------------------------------------------------------------


def test_the_server_registers_one_tool_with_a_derived_schema():
    server = mcp_server.build_server()
    tools = asyncio.run(server.list_tools())
    assert [tool.name for tool in tools] == [mcp_server.TOOL_NAME]
    schema = tools[0].input_schema
    assert schema["required"] == ["graph"]
    for optional in ("register", "input_dims", "saved_graph", "consumer_input", "schema", "family"):
        assert optional in schema["properties"], f"{optional} missing from the tool schema"


def test_the_tool_schema_exposes_no_skip_shaped_argument():
    server = mcp_server.build_server()
    tools = asyncio.run(server.list_tools())
    properties = set(tools[0].input_schema["properties"])
    forbidden = {"skip", "force", "ignore", "warn_only", "soft", "disable", "enabled"}
    assert not (properties & forbidden)


def test_calling_the_tool_through_the_sdk_returns_the_structured_result():
    """End to end through the SDK's own dispatch, not just the Python function."""
    server = mcp_server.build_server()
    raw = load_raw(NO_ADAPTER_14)
    result = asyncio.run(
        server.call_tool(
            mcp_server.TOOL_NAME,
            {
                "graph": raw,
                "register": REGISTER,
                "input_dims": [1072, 1024],
                # Every operand supplied, so this reaches PASS rather than the NOT_APPLICABLE
                # every img2img graph lands on when check 4 and check 5 cannot be asked.
                "saved_graph": raw,
                "consumer_input": "6.model",
            },
        )
    )
    assert result.is_error is False
    assert result.structured_content["verdict"] == "pass"
    assert [c["check"] for c in result.structured_content["checks"]] == [1, 2, 4, 5, 8]


def test_the_tool_description_says_it_is_not_the_production_gate():
    """The one sentence that stops an agent reading a HALT here and submitting elsewhere."""
    assert "NOT THE PRODUCTION GATE" in mcp_server.TOOL_DESCRIPTION
    assert "in-process" in mcp_server.TOOL_DESCRIPTION
    server = mcp_server.build_server()
    assert "TRANSPORT" in server.instructions
    assert "not the production gate" in server.instructions


def test_the_declared_mcp_bound_matches_the_api_this_was_built_against():
    """`MCPServer` is a 2.x class; a >=1.0 bound would resolve to a version that ImportErrors."""
    import tomllib
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["optional-dependencies"]["mcp"] == [mcp_server.MCP_REQUIREMENT]
    assert mcp_server.MCP_REQUIREMENT == "mcp>=2.0"


# ---------------------------------------------------------------------------------------------
# Bad arguments are bad arguments, not preflight findings.
# ---------------------------------------------------------------------------------------------


def test_an_unparseable_graph_is_a_value_error_not_a_halt_verdict():
    """Nothing was checked, so a HALT verdict would claim the gate examined a graph it never had."""
    with pytest.raises(ValueError, match="did not parse"):
        mcp_server.run_preflight({"nodes": [], "links": []})


def test_bad_input_dims_is_a_value_error():
    with pytest.raises(ValueError, match=r"\[width, height\]"):
        mcp_server.run_preflight(load_raw(NO_ADAPTER_14), input_dims=[1072])


def test_bad_consumer_input_is_a_value_error():
    with pytest.raises(ValueError, match="6.model"):
        mcp_server.run_preflight(load_raw(NO_ADAPTER_14), consumer_input="6")


def test_a_register_with_an_unknown_key_is_rejected():
    with pytest.raises(ValueError, match="unknown register key"):
        mcp_server.run_preflight(
            load_raw(NO_ADAPTER_14), register={"declared": False, "known_card": []}
        )


# ---------------------------------------------------------------------------------------------
# The askability parameters reach their checks through the transport too.
# ---------------------------------------------------------------------------------------------


def test_input_dims_reaches_check_5_through_the_transport():
    payload = mcp_server.run_preflight(
        load_raw(NO_ADAPTER_14), register=REGISTER, input_dims=[1066, 1024]
    )
    assert payload["verdict"] == "halt"
    codes = [f["code"] for check in payload["checks"] for f in check["findings"]]
    assert "FRAME_NOT_GENERATOR_LEGAL" in codes


def test_the_saved_graph_reaches_check_4_through_the_transport():
    raw = load_raw(NO_ADAPTER_14)
    submitted = json.loads(json.dumps(raw))
    node_id = next(nid for nid, node in submitted.items() if "seed" in node["inputs"])
    submitted[node_id]["inputs"]["seed"] += 1
    payload = mcp_server.run_preflight(submitted, register=REGISTER, saved_graph=raw)
    codes = [f["code"] for check in payload["checks"] for f in check["findings"]]
    assert "VALUE_CHANGED" in codes


def test_the_schema_reaches_check_1_through_the_transport():
    payload = mcp_server.run_preflight(
        load_raw(NO_ADAPTER_14),
        register=REGISTER,
        schema={"VAEDecode": ["samples", "vae"]},
    )
    check_1 = next(c for c in payload["checks"] if c["check"] == 1)
    assert "undeclared_input" in check_1["clauses_evaluated"]


def test_the_0_92_denoise_is_reported_through_the_transport():
    """Check 8's finding survives the transport intact, citation and date included."""
    payload = mcp_server.run_preflight(load_raw(NO_ADAPTER_14), register=REGISTER)
    check_8 = next(c for c in payload["checks"] if c["check"] == 8)
    denoise = next(
        d for d in check_8["clauses_declined"] if d["clause"] == "envelope_bands.denoise"
    )
    assert "0.92" in denoise["why"]
    assert "2026-08-14" in denoise["why"]


def test_main_returns_an_exit_code_rather_than_calling_sys_exit():
    assert inspect.signature(mcp_server.main).return_annotation == "int"
