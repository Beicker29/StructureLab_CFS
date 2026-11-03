"""CLI: prints JSON, writes nothing unless asked, exit 2 on invalid input; examples run."""
import json

import pytest

from cfs_design.run import main

from .conftest import ROOT

EXAMPLES = sorted((ROOT / "examples").glob("*.json"))


def test_there_are_examples():
    assert EXAMPLES


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_examples_run(path, capsys):
    assert main([str(path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] in {"PASS", "FAIL", "INCOMPLETE"}


def test_cli_writes_nothing_by_default(tmp_path, member_payload, monkeypatch, capsys):
    source = tmp_path / "m.json"
    source.write_text(json.dumps(member_payload), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert main([str(source)]) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == ["m.json"]
    assert json.loads(capsys.readouterr().out)["status"] == "INCOMPLETE"


def test_cli_output_file(tmp_path, member_payload):
    source, target = tmp_path / "m.json", tmp_path / "r.json"
    source.write_text(json.dumps(member_payload), encoding="utf-8")
    assert main([str(source), "--output", str(target)]) == 0
    assert json.loads(target.read_text(encoding="utf-8"))["status"] == "INCOMPLETE"


@pytest.mark.parametrize("content", ["{", "[]", json.dumps({"material": "X"})])
def test_cli_invalid_input(tmp_path, content, capsys):
    source = tmp_path / "bad.json"
    source.write_text(content, encoding="utf-8")
    assert main([str(source)]) == 2
    assert "error" in json.loads(capsys.readouterr().err)


def test_cli_unknown_material(tmp_path, member_payload, capsys):
    source = tmp_path / "m.json"
    source.write_text(json.dumps({**member_payload, "material": "ASTM A36"}), encoding="utf-8")
    assert main([str(source)]) == 2
    assert json.loads(capsys.readouterr().err)["error"]["code"] == "MATERIAL_NOT_FOUND"
