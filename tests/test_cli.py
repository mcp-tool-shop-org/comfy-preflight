"""The CLI verb — the development door.

The properties pinned here are its exit-code contract and its refusal to become the production
gate. Exit codes are established in this repo for the first time, so each one is tested against
the reason it was chosen rather than against a convention.
"""

from __future__ import annotations

import inspect
import io
import json

import pytest
from conftest import CORPUS_CARD, CORPUS_CARD_ALIAS, NO_ADAPTER_14, load_raw

from comfy_preflight import cli
from comfy_preflight.cli import EXIT_HALT, EXIT_OK, EXIT_USAGE


def _write(tmp_path, name: str, data) -> str:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def _run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(argv, out=out, err=err)
    return code, out.getvalue(), err.getvalue()


@pytest.fixture
def graph_path(tmp_path) -> str:
    return _write(tmp_path, "graph.json", load_raw(NO_ADAPTER_14))


@pytest.fixture
def register_path(tmp_path) -> str:
    return _write(
        tmp_path,
        "register.json",
        {"declared": False, "known_cards": [CORPUS_CARD, CORPUS_CARD_ALIAS]},
    )


def _self_linked(tmp_path) -> str:
    raw = load_raw(NO_ADAPTER_14)
    node_id = next(nid for nid, node in raw.items() if node["class_type"] == "VAEDecode")
    raw[node_id]["inputs"]["samples"] = [node_id, 0]
    return _write(tmp_path, "broken.json", raw)


def _out_of_band(tmp_path) -> str:
    raw = load_raw(NO_ADAPTER_14)
    for node in raw.values():
        if node["class_type"] == "ControlNetApplyAdvanced":
            node["inputs"]["strength"] = 0.4
    return _write(tmp_path, "advisory.json", raw)


# ---------------------------------------------------------------------------------------------
# The exit-code contract, each code against the reason it was chosen.
# ---------------------------------------------------------------------------------------------


def test_a_halt_exits_one(tmp_path, register_path):
    code, out, _ = _run(["check", _self_linked(tmp_path), "--register", register_path])
    assert code == EXIT_HALT
    assert "verdict: HALT" in out
    assert "SELF_LINK" in out


def test_an_advisory_exits_zero_so_a_shell_chain_does_not_turn_it_into_a_halt(
    tmp_path, register_path
):
    """The reason this code is 0, stated as the test's whole purpose.

    A nonzero exit stops a `&&` chain. Amendment 2 rules check 8 advisory precisely so it never
    stops correct work, and an exit status that stopped the next command would reinstate the
    halt the ruling removed.
    """
    code, out, _ = _run(["check", _out_of_band(tmp_path), "--register", register_path])
    assert code == EXIT_OK
    assert "verdict: ADVISORY" in out
    assert "this is not a halt" in out.lower()


def test_not_applicable_exits_zero_because_every_recorded_graph_reaches_it(
    graph_path, register_path
):
    """All 70 recorded graphs are img2img, so a run without --input-dims declines check 5.

    Exiting nonzero there would fire on correct work on the entire corpus, which is how a gate
    gets disabled by the third person who hits it.
    """
    code, out, _ = _run(["check", graph_path, "--register", register_path])
    assert code == EXIT_OK
    assert "verdict: NOT_APPLICABLE" in out


def test_a_pass_exits_zero(tmp_path, graph_path, register_path):
    code, out, _ = _run(
        [
            "check",
            graph_path,
            "--register",
            register_path,
            "--input-dims",
            "1072x1024",
            "--saved",
            graph_path,
            "--consumer",
            "6.model",
        ]
    )
    assert code == EXIT_OK
    assert "verdict: PASS" in out


def test_a_missing_file_is_a_usage_error_not_a_halt(tmp_path):
    """Exit 1 would tell a caller the gate examined a graph. It examined nothing."""
    code, _, err = _run(["check", str(tmp_path / "absent.json")])
    assert code == EXIT_USAGE
    assert "not found" in err


def test_an_unparseable_graph_is_a_usage_error(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    code, _, err = _run(["check", str(path)])
    assert code == EXIT_USAGE
    assert "not valid JSON" in err


def test_a_ui_export_graph_is_a_usage_error_with_the_conversion_hint(tmp_path):
    """The API format is not the UI export format, and the message says so."""
    path = _write(tmp_path, "ui.json", {"nodes": [], "links": []})
    code, _, err = _run(["check", path])
    assert code == EXIT_USAGE
    assert "did not parse" in err
    assert "class_type" in err


def test_bad_input_dims_is_a_usage_error(graph_path):
    code, _, err = _run(["check", graph_path, "--input-dims", "big"])
    assert code == EXIT_USAGE
    assert "1072x1024" in err


def test_bad_consumer_is_a_usage_error(graph_path):
    code, _, err = _run(["check", graph_path, "--consumer", "6"])
    assert code == EXIT_USAGE
    assert "6.model" in err


def test_a_malformed_register_is_a_usage_error(tmp_path, graph_path):
    path = _write(tmp_path, "reg.json", {"declared": False, "card": "x.safetensors"})
    code, _, err = _run(["check", graph_path, "--register", path])
    assert code == EXIT_USAGE
    assert "not a valid register" in err


def test_a_register_with_an_unknown_key_is_rejected_rather_than_ignored(tmp_path, graph_path):
    """A misspelled `known_card` silently dropped would empty the vocabulary, and check 2 would
    then decline the very clause the misspelling was meant to enable."""
    path = _write(tmp_path, "reg.json", {"declared": False, "known_card": ["x.safetensors"]})
    code, _, err = _run(["check", graph_path, "--register", path])
    assert code == EXIT_USAGE
    assert "unknown register key" in err


def test_a_register_must_state_declared(tmp_path, graph_path):
    path = _write(tmp_path, "reg.json", {"known_cards": []})
    code, _, err = _run(["check", graph_path, "--register", path])
    assert code == EXIT_USAGE
    assert "must state `declared`" in err


# ---------------------------------------------------------------------------------------------
# The output.
# ---------------------------------------------------------------------------------------------


def test_the_json_output_is_the_aggregators_own_rendering(graph_path, register_path):
    code, out, _ = _run(["check", graph_path, "--register", register_path, "--json"])
    assert code == EXIT_OK
    payload = json.loads(out)
    assert payload["verdict"] == "not_applicable"
    assert [entry["check"] for entry in payload["checks"]] == [1, 2, 4, 5, 8]


def test_declined_clauses_print_even_on_a_passing_run(tmp_path, graph_path, register_path):
    """A clause nobody asked is not a clause that passed.

    Hiding declines behind a green verdict is how coverage quietly shrinks, so they print.
    """
    code, out, _ = _run(
        [
            "check",
            graph_path,
            "--register",
            register_path,
            "--input-dims",
            "1072x1024",
            "--saved",
            graph_path,
            "--consumer",
            "6.model",
        ]
    )
    assert code == EXIT_OK
    assert "verdict: PASS" in out
    assert "declined undeclared_input" in out
    assert "declined envelope_bands.denoise" in out


def test_the_0_92_denoise_is_reported_at_the_development_door(graph_path, register_path):
    """The finding check 8 exists for, visible to a human developing a graph by hand."""
    _, out, _ = _run(["check", graph_path, "--register", register_path])
    assert "0.92" in out
    assert "CANNOT say whether that is in or out of band" in out
    assert "huggingface.co/InstantX/Qwen-Image-ControlNet-Union" in out


def test_the_whole_rendering_is_ascii_encodable(tmp_path, graph_path, register_path):
    """Measured on this rig: a Windows console encodes with cp1252 and renders an em dash as a
    replacement character. The first version of the unregistered-checks line printed as
    `3 (recipe-vs-profile agreement ? no subject-profile fixture...)`.

    Docstrings and comments stay free to use whatever punctuation reads best. Anything a user
    sees printed does not, and this scans the real rendering rather than any one string.
    """
    for argv in (
        ["check", graph_path, "--register", register_path],
        ["check", graph_path, "--register", register_path, "--input-dims", "1066x1024"],
        ["check", _out_of_band(tmp_path), "--register", register_path],
        ["check", _self_linked(tmp_path), "--register", register_path],
    ):
        _, out, err = _run(argv)
        for stream, text in (("stdout", out), ("stderr", err)):
            try:
                text.encode("cp1252")
            except UnicodeEncodeError as exc:
                raise AssertionError(
                    f"{argv[1]}: {stream} carries a character a Windows console cannot render: "
                    f"{text[exc.start:exc.end]!r} at offset {exc.start}"
                ) from exc


def test_the_unregistered_checks_are_named_in_the_output(graph_path):
    _, out, _ = _run(["check", graph_path])
    assert "not registered:" in out
    for number in (3, 6, 7):
        assert f"{number} (" in out


def test_the_recorded_frame_defect_reaches_the_command_line(graph_path, register_path):
    code, out, _ = _run(
        ["check", graph_path, "--register", register_path, "--input-dims", "1066x1024"]
    )
    assert code == EXIT_HALT
    assert "FRAME_NOT_GENERATOR_LEGAL" in out
    assert "1064" in out


def test_nothing_was_submitted_is_stated_on_a_halt(tmp_path, register_path):
    _, out, _ = _run(["check", _self_linked(tmp_path), "--register", register_path])
    assert "Nothing was submitted" in out


# ---------------------------------------------------------------------------------------------
# The CLI is not the production gate, and carries no skip.
# ---------------------------------------------------------------------------------------------


def test_an_internal_error_is_reported_structurally_not_as_a_traceback(monkeypatch, graph_path):
    """A stack trace is not an error message.

    The failure is injected at the aggregator so the path under test is the real one - the CLI's
    outermost guard - rather than a mocked-out renderer.
    """
    def boom(*a, **k):
        raise RuntimeError("a synthetic bug in the gate itself")

    monkeypatch.setattr(cli, "preflight", boom)
    code, out, err = _run(["check", graph_path])
    assert code == EXIT_USAGE
    assert "INTERNAL_ERROR" in err
    assert "RuntimeError" in err
    assert "Traceback" not in err and "Traceback" not in out
    # It must say whose fault it is and what the caller may conclude.
    assert "bug in comfy-preflight, not a defect in your graph" in err
    assert "NOTHING was examined" in err
    assert "--debug" in err


def test_debug_re_raises_so_a_developer_keeps_the_frame(monkeypatch, graph_path):
    """The other half: suppressing a traceback at a user must not destroy it for a developer."""
    def boom(*a, **k):
        raise RuntimeError("a synthetic bug in the gate itself")

    monkeypatch.setattr(cli, "preflight", boom)
    with pytest.raises(RuntimeError, match="synthetic bug"):
        cli.main(["check", graph_path, "--debug"], out=io.StringIO(), err=io.StringIO())


def test_an_internal_error_exits_two_because_nothing_was_examined(monkeypatch, graph_path):
    """Not exit 1. Exit 1 says a defect was found in the graph; a bug in the gate found nothing."""
    monkeypatch.setattr(cli, "preflight", lambda *a, **k: (_ for _ in ()).throw(ValueError("x")))
    code, _, _ = _run(["check", graph_path])
    assert code == EXIT_USAGE
    assert code != EXIT_HALT


def test_the_mcp_verb_exists_and_says_it_is_not_the_production_gate():
    """`comfy-preflight mcp` is how the npx binary reaches the stdio server with no Python."""
    parser = cli.build_parser()
    mcp = parser._subparsers._group_actions[0].choices["mcp"]  # noqa: SLF001
    assert "NOT THE PRODUCTION GATE" in mcp.description


def test_the_mcp_verb_dispatches_to_the_server_module(monkeypatch):
    """A transport launcher, not a second implementation: it calls mcp_server.main and nothing else."""
    from comfy_preflight import mcp_server

    called = []
    monkeypatch.setattr(mcp_server, "main", lambda: called.append(True) or 0)
    code = cli.main(["mcp"], out=io.StringIO(), err=io.StringIO())
    assert code == EXIT_OK
    assert called == [True]


def test_the_command_exposes_no_skip_flag():
    """Read the parser's actual options rather than trusting the help text."""
    parser = cli.build_parser()
    check = parser._subparsers._group_actions[0].choices["check"]  # noqa: SLF001
    options = {opt for action in check._actions for opt in action.option_strings}  # noqa: SLF001
    forbidden = {
        "--skip", "--force", "--ignore", "--warn-only", "--soft", "--disable", "--no-halt",
        "--allow-halt", "--exit-zero",
    }
    assert not (options & forbidden), f"the CLI exposes a skip-shaped flag: {options & forbidden}"


def test_main_returns_its_exit_code_rather_than_calling_sys_exit():
    """So the contract is testable, and so a caller embedding it is not killed by it."""
    assert inspect.signature(cli.main).return_annotation == "int"


def test_the_help_says_this_is_not_the_production_gate():
    """The one sentence that keeps a shell chain from being mistaken for a guard."""
    parser = cli.build_parser()
    assert "NOT THE PRODUCTION GATE" in parser.epilog
    assert "in-process" in parser.epilog


def test_the_help_documents_every_exit_code():
    parser = cli.build_parser()
    for fragment in ("0 =", "1 = HALT", "2 = usage"):
        assert fragment in parser.epilog


def test_help_and_version_exit_zero():
    for flag in ("--help", "--version"):
        out, err = io.StringIO(), io.StringIO()
        # argparse writes to the real streams for these; only the code is under test.
        try:
            code = cli.main([flag], out=out, err=err)
        except SystemExit as exc:  # pragma: no cover - argparse may raise before we catch
            code = int(exc.code or 0)
        assert code == EXIT_OK


def test_a_missing_verb_is_a_usage_error():
    try:
        code = cli.main([], out=io.StringIO(), err=io.StringIO())
    except SystemExit as exc:  # pragma: no cover
        code = int(exc.code or 0)
    assert code == EXIT_USAGE
