"""Tests of tools/build_all.py on a tiny analysis root."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_all as ba  # noqa: E402
from test_build_report import DECK, FIGURES, REPORT  # noqa: E402,F401


def make(root, name, deck=DECK):
    d = root / name
    d.mkdir()
    (d / "figures.py").write_text(FIGURES)
    (d / "deck.yaml").write_text(deck)
    (d / "writeup.md").write_text(REPORT)


def test_find_skips_without_deck(tmp_path):
    make(tmp_path, "02_b")
    make(tmp_path, "01_a")
    (tmp_path / "03_nodeck").mkdir()
    (tmp_path / "targets").mkdir()
    assert [d.name for d in ba.find_analyses(tmp_path)] == ["01_a", "02_b"]


def test_check_all_ok_and_failure(tmp_path, capsys):
    make(tmp_path, "01_a")
    assert ba.main(["--check", "--analysis-root", str(tmp_path)]) == 0
    make(tmp_path, "02_b", DECK.replace("fig.png", "nope.png"))
    assert ba.main(["--check", "--analysis-root", str(tmp_path)]) == 1
    assert "failed: 02_b" in capsys.readouterr().err
