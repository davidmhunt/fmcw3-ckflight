"""The KiCad editing rules in .claude/friday.json and CLAUDE.md are the IPC-when-open rules.

A test rather than a grep in Verify: the bash_file_io hook denies a Verify line that reads files.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLD = "while the user has the project open"
STATUS = "tools/kicad_ipc.py status"


def rules_text():
    data = json.loads((ROOT / ".claude" / "friday.json").read_text())
    assert isinstance(data["rules"], list)
    return "\n".join(data["rules"])


def test_friday_json_rules():
    text = rules_text()
    assert OLD not in text
    assert STATUS in text


def test_claude_md():
    text = (ROOT / "CLAUDE.md").read_text()
    assert OLD not in text
    assert STATUS in text
