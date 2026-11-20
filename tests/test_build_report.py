"""Tests of tools/build_report.py and tools/deck_template.py on a tiny fixture analysis."""
import shutil
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import build_report as br  # noqa: E402
import deck_template as dt  # noqa: E402

FIGURES = textwrap.dedent("""
    from pathlib import Path
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    b = Path("build"); b.mkdir(exist_ok=True)
    plt.bar(["a", "b"], [1, 2]); plt.savefig(b / "fig.png"); plt.close()
    (b / "t.csv").write_text("name,count\\nx,1\\ny,2\\n")
""")
DECK = textwrap.dedent("""
    slides:
      - {layout: title, title: Fixture, bullets: [sub]}
      - {layout: bullet, title: Points, bullets: [one, two], note: hello}
      - {layout: figure, title: Fig, figure: fig.png}
      - {layout: table, title: Tab, table: t.csv}
      - {layout: decisions, title: Decide, bullets: [pick one]}
""")
REPORT = "# Fixture\n\n![fig](build/fig.png)\n"


@pytest.fixture
def fixture(tmp_path):
    d = tmp_path / "99_fix"
    d.mkdir()
    (d / "figures.py").write_text(FIGURES)
    (d / "deck.yaml").write_text(DECK)
    (d / "writeup.md").write_text(REPORT)
    return d


def test_overflow_flags_long_bullets():
    ok = {"layout": "bullet", "title": "T", "bullets": ["short"] * 4}
    bad = {"layout": "bullet", "title": "T", "bullets": ["word " * 60] * 8}
    assert dt.overflow_problems(ok) == []
    assert any("bullets overflow" in m for m in dt.overflow_problems(bad))


def test_overflow_flags_long_title():
    s = {"layout": "bullet", "title": "x" * 400, "bullets": []}
    assert any("title overflows" in m for m in dt.overflow_problems(s))


def test_bigger_font_overflows_sooner():
    paras = ["word " * 20] * 6
    small = dt.estimate_height_in(paras, 12.1, 14)
    big = dt.estimate_height_in(paras, 12.1, 28)
    assert big > small


def test_check_ok(fixture, capsys):
    assert br.main([str(fixture), "--check"]) == 0
    assert "check ok" in capsys.readouterr().out


def test_check_missing_figure(fixture, capsys):
    (fixture / "deck.yaml").write_text(DECK.replace("fig.png", "nope.png"))
    assert br.main([str(fixture), "--check"]) == 1
    assert "missing figure build/nope.png" in capsys.readouterr().err


def test_check_unresolved_reference(fixture, capsys):
    (fixture / "writeup.md").write_text(REPORT + "\n![x](build/gone.png)\n")
    assert br.main([str(fixture), "--check"]) == 1
    assert "unresolved reference build/gone.png" in capsys.readouterr().err


def test_check_overflow(fixture, capsys):
    (fixture / "deck.yaml").write_text(
        "slides:\n  - layout: bullet\n    title: T\n    bullets: [%s]\n" % ("word " * 400))
    assert br.main([str(fixture), "--check"]) == 1
    assert "overflow" in capsys.readouterr().err


def test_build_pptx(fixture, tmp_path):
    from pptx import Presentation
    out = tmp_path / "out"
    br.run_figures(fixture, "default")
    out.mkdir()
    br.build_pptx(br.load_deck(fixture), fixture / "build", out / "x.pptx")
    prs = Presentation(str(out / "x.pptx"))
    assert len(prs.slides) == 5
    assert prs.slide_width / prs.slide_height == pytest.approx(16 / 9, rel=1e-3)
    assert prs.slides[1].notes_slide.notes_text_frame.text == "hello"


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc not installed (use ./run)")
def test_full_build(fixture, tmp_path):
    out = tmp_path / "out"
    assert br.main([str(fixture), "--out", str(out)]) == 0
    assert (out / "99_fix.pdf").stat().st_size > 0
    assert (out / "99_fix.pptx").stat().st_size > 0
