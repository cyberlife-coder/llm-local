from __future__ import annotations

import pytest

from llm_local.cli import build_parser, main


def test_parser_has_expected_commands():
    parser = build_parser()
    help_text = parser.format_help()

    assert "doctor" in help_text
    assert "profiles" in help_text
    assert "qwen36-a3b-64k" in help_text


def test_no_args_prints_practical_help(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("LLM_LOCAL_HOME", str(tmp_path))

    main([])

    out = capsys.readouterr().out
    assert "Daily flow:" in out
    assert "llm-local doctor" in out


def test_unknown_model_exits_cleanly(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_LOCAL_HOME", str(tmp_path))

    with pytest.raises(SystemExit):
        main(["serve", "missing-model"])

