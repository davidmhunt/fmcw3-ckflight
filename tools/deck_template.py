"""Shared 16:9 deck template for every analysis deck.

Five layouts: title, bullet, figure, table, decisions. All slides are drawn on the blank
layout of python-pptx's default template with explicit text boxes, so the geometry below is
the single source of truth for both rendering and the overflow estimate.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

SLIDE_W_IN = 13.333
SLIDE_H_IN = 7.5

LAYOUTS = ("title", "bullet", "figure", "table", "decisions")

# Average glyph width as a fraction of the font size (sans serif, mixed text), line height as
# a multiple of the font size, and extra space after each paragraph in points.
CHAR_WIDTH_EM = 0.52
LINE_HEIGHT_EM = 1.2
PARA_SPACE_PT = 6.0
BOX_PAD_IN = 0.1  # left/right/top/bottom inset of a text box

NAVY = RGBColor(0x1F, 0x2A, 0x44)
GREY = RGBColor(0x55, 0x55, 0x55)
ACCENT = RGBColor(0xC0, 0x39, 0x2B)


@dataclass(frozen=True)
class Box:
    left: float
    top: float
    width: float
    height: float


@dataclass(frozen=True)
class LayoutSpec:
    title_box: Box
    title_pt: int
    body_box: Box | None  # bullets, figure, or table area
    body_pt: int


_TITLE = Box(0.6, 0.35, 12.1, 1.0)
_BODY = Box(0.6, 1.6, 12.1, 5.2)

SPECS: dict[str, LayoutSpec] = {
    "title": LayoutSpec(Box(0.9, 2.4, 11.5, 1.6), 44, Box(0.9, 4.2, 11.5, 1.4), 20),
    "bullet": LayoutSpec(_TITLE, 32, _BODY, 22),
    "figure": LayoutSpec(_TITLE, 32, Box(0.6, 1.5, 12.1, 5.4), 18),
    "table": LayoutSpec(_TITLE, 32, _BODY, 14),
    "decisions": LayoutSpec(_TITLE, 32, _BODY, 20),
}


def estimate_lines(text: str, width_in: float, font_pt: float) -> int:
    """Wrapped line count of one paragraph in a box of the given usable width."""
    usable_pt = max(width_in - 2 * BOX_PAD_IN, 0.1) * 72
    chars_per_line = max(int(usable_pt / (font_pt * CHAR_WIDTH_EM)), 1)
    return max(1, math.ceil(len(text) / chars_per_line))


def estimate_height_in(paragraphs: list[str], width_in: float, font_pt: float) -> float:
    """Height in inches the paragraphs need, including box insets."""
    lines = sum(estimate_lines(p, width_in, font_pt) for p in paragraphs)
    pts = lines * font_pt * LINE_HEIGHT_EM + len(paragraphs) * PARA_SPACE_PT
    return pts / 72 + 2 * BOX_PAD_IN


def _bullet_text(b: str) -> str:
    return "• " + b  # bullet glyph plus space counts toward width


def overflow_problems(slide: dict) -> list[str]:
    """Return a message per text box of `slide` that the estimate says overflows."""
    layout = slide.get("layout")
    if layout not in SPECS:
        return []
    spec = SPECS[layout]
    out: list[str] = []
    title = str(slide.get("title", ""))
    need = estimate_height_in([title], spec.title_box.width, spec.title_pt)
    if need > spec.title_box.height:
        out.append(f"title overflows ({need:.2f} in needed, {spec.title_box.height:.2f} in box)")
    if layout in ("bullet", "decisions"):
        paras = [_bullet_text(str(b)) for b in slide.get("bullets", [])]
        need = estimate_height_in(paras, spec.body_box.width, spec.body_pt)
        if need > spec.body_box.height:
            out.append(f"bullets overflow ({need:.2f} in needed, {spec.body_box.height:.2f} in box)")
    elif layout == "title":
        sub = [str(b) for b in slide.get("bullets", [])]
        if sub:
            need = estimate_height_in(sub, spec.body_box.width, spec.body_pt)
            if need > spec.body_box.height:
                out.append(f"subtitle overflows ({need:.2f} in needed, {spec.body_box.height:.2f} in box)")
    return out


def table_problems(rows: list[list[str]]) -> list[str]:
    """Estimate whether a CSV table fits the table layout (row height from the wrapped cells)."""
    spec = SPECS["table"]
    if not rows:
        return ["table is empty"]
    ncols = max(len(r) for r in rows)
    col_w = spec.body_box.width / ncols
    total = 0.0
    for r in rows:
        total += max(estimate_height_in([c], col_w, spec.body_pt) for c in r) + 0.05
    if total > spec.body_box.height:
        return [f"table overflows ({total:.2f} in needed, {spec.body_box.height:.2f} in box)"]
    return []


def read_csv(path: Path) -> list[list[str]]:
    with open(path, newline="") as f:
        return [row for row in csv.reader(f)]


def _text(slide, box: Box, paras: list[str], pt: int, *, color=NAVY, bold=False):
    tb = slide.shapes.add_textbox(Inches(box.left), Inches(box.top), Inches(box.width), Inches(box.height))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, p in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.space_after = Pt(PARA_SPACE_PT)
        run = para.add_run()
        run.text = p
        run.font.size = Pt(pt)
        run.font.bold = bold
        run.font.color.rgb = color
    return tb


def new_presentation() -> Presentation:
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W_IN)
    prs.slide_height = Inches(SLIDE_H_IN)
    return prs


def add_slide(prs, slide: dict, build_dir: Path) -> None:
    """Append one slide described by a deck.yaml entry."""
    layout = slide["layout"]
    spec = SPECS[layout]
    s = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    title = str(slide.get("title", ""))
    _text(s, spec.title_box, [title], spec.title_pt, bold=True)
    bullets = [str(b) for b in slide.get("bullets", [])]
    if layout in ("bullet", "decisions"):
        color = ACCENT if layout == "decisions" else NAVY
        if layout == "decisions":
            # accent bar marks the "decisions needed" layout
            bar = s.shapes.add_shape(1, Inches(0), Inches(0), Inches(0.25), Inches(SLIDE_H_IN))
            bar.fill.solid()
            bar.fill.fore_color.rgb = ACCENT
            bar.line.fill.background()
        _text(s, spec.body_box, [_bullet_text(b) for b in bullets], spec.body_pt, color=NAVY if layout == "bullet" else color)
    elif layout == "title":
        if bullets:
            _text(s, spec.body_box, bullets, spec.body_pt, color=GREY)
    elif layout == "figure":
        pic_path = build_dir / slide["figure"]
        b = spec.body_box
        pic = s.shapes.add_picture(str(pic_path), Inches(b.left), Inches(b.top))
        # fit inside the body box, keep aspect, centre
        scale = min(Inches(b.width) / pic.width, Inches(b.height) / pic.height)
        pic.width, pic.height = int(pic.width * scale), int(pic.height * scale)
        pic.left = int(Inches(b.left) + (Inches(b.width) - pic.width) / 2)
        pic.top = int(Inches(b.top) + (Inches(b.height) - pic.height) / 2)
    elif layout == "table":
        rows = read_csv(build_dir / slide["table"])
        b = spec.body_box
        ncols = max(len(r) for r in rows)
        gt = s.shapes.add_table(len(rows), ncols, Inches(b.left), Inches(b.top), Inches(b.width), Inches(0.4 * len(rows)))
        for ri, r in enumerate(rows):
            for ci in range(ncols):
                cell = gt.table.cell(ri, ci)
                cell.text = r[ci] if ci < len(r) else ""
                for p in cell.text_frame.paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(spec.body_pt)
    note = slide.get("note")
    if note:
        s.notes_slide.notes_text_frame.text = str(note)
