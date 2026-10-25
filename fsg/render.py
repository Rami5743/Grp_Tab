"""Turn the group data into a one-page PDF poster (reportlab, no LaTeX needed)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import Paragraph

from . import groups as G

# --------------------------------------------------------------------------
# fonts
# --------------------------------------------------------------------------

_FONT_DIRS = [
    "/usr/share/fonts/truetype/freefont",
    "/usr/share/fonts/truetype/dejavu",
]

MATH = "Math"
UI = "UI"


def _find(name: str) -> str | None:
    for d in _FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


def register_fonts() -> None:
    """Register a Unicode serif (maths) and a Unicode sans (labels).

    GNU FreeFont covers the mathematical operators we need (product sign,
    congruence, ellipses, true minus); the built-in Type-1 fonts do not.
    """
    faces = {
        MATH: ("FreeSerif.ttf", "FreeSerifBold.ttf", "FreeSerifItalic.ttf",
               "FreeSerifBoldItalic.ttf"),
        UI: ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf",
             "DejaVuSans-Bold.ttf"),
    }
    for base, (reg, bold, ital, bi) in faces.items():
        for suffix, fname in (("", reg), ("-Bold", bold), ("-Italic", ital),
                              ("-BoldItalic", bi)):
            path = _find(fname)
            if path is None:
                raise RuntimeError(f"font not found: {fname}")
            pdfmetrics.registerFont(TTFont(base + suffix, path))
        pdfmetrics.registerFontFamily(
            base, normal=base, bold=base + "-Bold",
            italic=base + "-Italic", boldItalic=base + "-BoldItalic")


def missing_glyphs(text: str, font: str = MATH) -> list[str]:
    """Characters of ``text`` that ``font`` cannot draw (used by the self-test)."""
    face = pdfmetrics.getFont(font).face
    return [ch for ch in sorted(set(text)) if ord(ch) > 127 and ord(ch) not in face.charToGlyph]


# --------------------------------------------------------------------------
# palette
# --------------------------------------------------------------------------
# The seven category hues are the first seven slots of the data-viz reference
# categorical palette, ordered so that every pair of categories that ends up
# side by side on the poster clears the colour-vision separation gate
# (validated with scripts/validate_palette.js, light mode: all checks PASS).

HUES = {
    G.CYCLIC: "#eb6834",
    G.CLASSICAL: "#2a78d6",
    G.CLASSICAL_TWISTED: "#1baf7a",
    G.EXCEPTIONAL: "#6250d6",
    G.EXCEPTIONAL_TWISTED: "#e87ba4",
    G.ALTERNATING: "#008300",
    G.SPORADIC: "#eda100",
}

INK = HexColor("#121212")
INK_SOFT = HexColor("#55534e")
INK_FAINT = HexColor("#8a8780")
PAPER = HexColor("#fcfcfb")
GHOST_FILL = HexColor("#f0efec")
GHOST_INK = HexColor("#857f74")


def tint(hex_color: str, t: float) -> Color:
    """Mix ``hex_color`` with the paper colour; ``t = 0`` is pure paper."""
    c = HexColor(hex_color)
    return Color(PAPER.red + (c.red - PAPER.red) * t,
                 PAPER.green + (c.green - PAPER.green) * t,
                 PAPER.blue + (c.blue - PAPER.blue) * t)


# --------------------------------------------------------------------------
# poster configuration
# --------------------------------------------------------------------------

@dataclass
class PosterConfig:
    """Everything the poster is parametrised by."""

    #: how many explicit ranks of each rank-parametrised family to show
    ranks_shown: int = 3
    #: largest field size q shown explicitly (rows are the prime powers <= this)
    q_max: int = 13
    #: alternating groups Alt(5) .. Alt(alt_max) are shown explicitly
    alt_max: int = 9
    #: columns of the sporadic block (26 puts them all in one strip)
    sporadic_cols: int = 26

    cell_w: float = 104.0
    cell_h: float = 96.0
    dots_frac: float = 0.42          # width/height of an ellipsis row or column
    gap: float = 3.0                 # gap between neighbouring cells

    margin: float = 46.0
    axis_w: float = 52.0
    header_h: float = 26.0           # per-column header band
    family_band_h: float = 30.0      # family-title band
    title_h: float = 212.0
    bottom_gap: float = 40.0

    show_atlas_names: bool = True
    max_order_lines: int = 5
    symbol_size: float = 20.0
    atlas_size: float = 7.2
    order_size: float = 6.6
    min_order_size: float = 4.2

    title: str = "A Periodic Table of the Finite Simple Groups"
    subtitle: str = ("Every finite simple group appears exactly once, in its simplest form.  "
                     "Columns are families; the vertical axis is the field size q.")


# --------------------------------------------------------------------------
# grid model
# --------------------------------------------------------------------------

@dataclass
class Column:
    kind: str                      # "cells" | "dots"
    width: float
    family: G.Family | None = None
    rank: int | None = None        # None => generic rank
    header: str = ""
    family_title: str = ""         # non-empty on the first column of a family
    family_span: int = 1


@dataclass
class Row:
    kind: str                      # "cells" | "dots"
    height: float
    q: int | None = None           # None => generic q


def build_columns(cfg: PosterConfig) -> list[Column]:
    cols: list[Column] = [Column("cells", cfg.cell_w, None, None, header="ℤ/pℤ",
                                 family_title="Cyclic", family_span=1)]
    for fam in G.LIE_FAMILIES:
        start = len(cols)
        if fam.ranked:
            for n in range(fam.min_rank, fam.min_rank + cfg.ranks_shown):
                cols.append(Column("cells", cfg.cell_w, fam, n,
                                   header=fam.symbol(str(n))))
            cols.append(Column("dots", cfg.cell_w * cfg.dots_frac))
            cols.append(Column("cells", cfg.cell_w, fam, None, header=fam.symbol("n")))
            cols.append(Column("dots", cfg.cell_w * cfg.dots_frac))
        else:
            cols.append(Column("cells", cfg.cell_w, fam, 0, header=fam.symbol("")))
        cols[start].family_title = _family_title(fam)
        cols[start].family_span = len(cols) - start
    return cols


def _family_title(fam: G.Family) -> str:
    sym = fam.symbol("n" if fam.ranked else "")
    return f"{sym}(q)  —  {fam.title}" if fam.title else f"{sym}(q)"


def build_rows(cfg: PosterConfig) -> list[Row]:
    from .arith import prime_powers_up_to
    rows = [Row("cells", cfg.cell_h, q) for q in prime_powers_up_to(cfg.q_max)]
    rows.append(Row("dots", cfg.cell_h * cfg.dots_frac))
    rows.append(Row("cells", cfg.cell_h, None))
    rows.append(Row("dots", cfg.cell_h * cfg.dots_frac))
    return rows


# --------------------------------------------------------------------------
# low-level drawing helpers
# --------------------------------------------------------------------------

def _style(font, size, color, align=TA_CENTER, leading=None):
    return ParagraphStyle("s", fontName=font, fontSize=size,
                          leading=leading or size * 1.14,
                          textColor=color, alignment=align)


def fitted(text: str, font: str, color, max_w: float, max_h: float,
           start: float, floor: float, align=TA_CENTER) -> tuple[Paragraph, float, float]:
    """Largest paragraph of ``text`` (down to ``floor`` pt) fitting the box."""
    size = start
    while True:
        p = Paragraph(text, _style(font, size, color, align))
        w, h = p.wrap(max_w, 10_000)
        if h <= max_h or size <= floor:
            return p, w, h
        size -= 0.3


def draw_para(c, p: Paragraph, x: float, y_top: float, w: float, h: float) -> None:
    p.drawOn(c, x, y_top - h)


def rounded(c, x, y, w, h, r, fill, stroke=None, lw=0.6, dash=None):
    c.saveState()
    c.setFillColor(fill)
    if stroke is not None:
        c.setStrokeColor(stroke)
        c.setLineWidth(lw)
        if dash:
            c.setDash(dash)
    c.roundRect(x, y, w, h, r, stroke=1 if stroke is not None else 0, fill=1)
    c.restoreState()


# --------------------------------------------------------------------------
# the cell
# --------------------------------------------------------------------------

def draw_cell(c, cell: G.Cell, x: float, y: float, w: float, h: float,
              cfg: PosterConfig) -> None:
    hue = HUES[cell.category]
    pad = 4.5
    r = 4.0

    if cell.ghost:
        rounded(c, x, y, w, h, r, GHOST_FILL, HexColor("#dddbd4"), 0.6, dash=(1.6, 1.8))
        p, _, ph = fitted(cell.ghost, MATH, GHOST_INK, w - 2 * pad, h - 2 * pad, 10.5, 5.5)
        draw_para(c, p, x + pad, y + (h + ph) / 2, w - 2 * pad, ph)
        return

    rounded(c, x, y, w, h, r, tint(hue, 0.15), tint(hue, 0.62), 0.7)

    # accent bar across the top: the category signal, repeated by the legend
    c.saveState()
    c.setFillColor(HexColor(hue))
    c.roundRect(x, y + h - 6.0, w, 6.0, r, stroke=0, fill=1)
    c.rect(x, y + h - 6.0, w, 3.0, stroke=0, fill=1)
    c.restoreState()

    top = y + h - 6.0 - 2.0

    if cell.atlas:
        p, _, ph = fitted(cell.atlas, MATH, INK_SOFT, w - 2 * pad, 13, cfg.atlas_size, 5.0)
        draw_para(c, p, x + pad, top, w - 2 * pad, ph)
        top -= ph + 1.0

    order_h = 0.0
    if cell.order:
        max_h = cfg.order_size * 1.16 * cfg.max_order_lines
        p_ord, _, order_h = fitted(cell.order, MATH, INK_SOFT, w - 2 * pad, max_h,
                                   cfg.order_size, cfg.min_order_size)
        draw_para(c, p_ord, x + pad, y + pad + order_h, w - 2 * pad, order_h)
        # hairline separating the symbol from its order
        c.setStrokeColor(tint(hue, 0.45))
        c.setLineWidth(0.4)
        c.line(x + pad * 2, y + pad + order_h + 3.0, x + w - pad * 2, y + pad + order_h + 3.0)

    mid_top, mid_bot = top, y + pad + order_h + 5.0
    p_sym, _, sh = fitted(cell.symbol, MATH, INK, w - 2 * pad, mid_top - mid_bot,
                          cfg.symbol_size, 7.0)
    draw_para(c, p_sym, x + pad, (mid_top + mid_bot) / 2 + sh / 2, w - 2 * pad, sh)

    if cell.note:
        c.setFont(UI, 4.8)
        c.setFillColor(INK_FAINT)
        c.drawRightString(x + w - pad, y + h - 14.0, cell.note)


def draw_dots(c, x, y, w, h, vertical: bool) -> None:
    c.setFillColor(INK_FAINT)
    c.setFont(MATH, 15)
    c.drawCentredString(x + w / 2, y + h / 2 - 5, "⋮" if vertical else "⋯")


# --------------------------------------------------------------------------
# the poster
# --------------------------------------------------------------------------

class Poster:
    def __init__(self, cfg: PosterConfig):
        self.cfg = cfg
        self.cols = build_columns(cfg)
        self.rows = build_rows(cfg)
        self.grid_w = sum(col.width for col in self.cols)
        self.grid_h = sum(row.height for row in self.rows)
        self.bottom_h = self._bottom_height()
        self.width = cfg.margin * 2 + cfg.axis_w + self.grid_w
        self.height = (cfg.margin * 2 + cfg.title_h + cfg.family_band_h + cfg.header_h
                       + self.grid_h + cfg.bottom_gap + self.bottom_h)

    # -- geometry ---------------------------------------------------------
    def col_x(self, i: int) -> float:
        return self.cfg.margin + self.cfg.axis_w + sum(c.width for c in self.cols[:i])

    def row_y(self, j: int) -> float:
        """Bottom edge of row ``j``."""
        top = self.height - self.cfg.margin - self.cfg.title_h - self.cfg.family_band_h \
            - self.cfg.header_h
        return top - sum(r.height for r in self.rows[:j + 1])

    def _bottom_height(self) -> float:
        cfg = self.cfg
        n_sporadic_rows = -(-len(G.SPORADIC_GROUPS) // cfg.sporadic_cols)
        return 24.0 + max(cfg.cell_h, n_sporadic_rows * cfg.cell_h) + 10.0

    # -- drawing ----------------------------------------------------------
    def draw(self, path: str) -> None:
        cfg = self.cfg
        c = pdfcanvas.Canvas(path, pagesize=(self.width, self.height))
        c.setTitle(cfg.title)
        c.setAuthor("fsg poster generator")
        c.setFillColor(PAPER)
        c.rect(0, 0, self.width, self.height, stroke=0, fill=1)

        self._draw_title(c)
        self._draw_headers(c)
        self._draw_axis(c)
        self._draw_grid(c)
        self._draw_bottom(c)
        c.showPage()
        c.save()

    # ...................................................................
    def _draw_title(self, c) -> None:
        cfg = self.cfg
        x0 = cfg.margin
        top = self.height - cfg.margin

        c.setFillColor(INK)
        c.setFont(UI + "-Bold", 40)
        c.drawString(x0, top - 38, cfg.title)
        c.setFillColor(INK_SOFT)
        c.setFont(UI, 13.5)
        c.drawString(x0, top - 60, cfg.subtitle)

        # ---- legend: one swatch per category, in the fixed palette order
        lx, ly = x0, top - 93
        c.setFont(UI + "-Bold", 10.5)
        c.setFillColor(INK)
        c.drawString(lx, ly + 17, "TYPE")
        for key in (G.CYCLIC, G.ALTERNATING, G.CLASSICAL, G.CLASSICAL_TWISTED,
                    G.EXCEPTIONAL, G.EXCEPTIONAL_TWISTED, G.SPORADIC):
            hue = HUES[key]
            rounded(c, lx, ly - 4, 28, 16, 3, tint(hue, 0.15), tint(hue, 0.62), 0.7)
            c.setFillColor(HexColor(hue))
            c.rect(lx, ly + 8.5, 28, 3.5, stroke=0, fill=1)
            c.setFillColor(INK)
            c.setFont(UI, 10.5)
            c.drawString(lx + 34, ly + 0.5, G.CATEGORY_TITLES[key])
            lx += 34 + c.stringWidth(G.CATEGORY_TITLES[key], UI, 10.5) + 30

        # ---- lower row of the masthead
        hy = top - 118                       # baseline of the small headings
        dw, dh = cfg.cell_w + 6, 66.0
        x = x0

        def heading(xx, text):
            c.setFillColor(INK)
            c.setFont(UI + "-Bold", 10.5)
            c.drawString(xx, hy, text)

        def lines(xx, yy, texts, size=9.0, leading=11.0, color=INK_SOFT):
            c.setFillColor(color)
            c.setFont(UI, size)
            for i, t in enumerate(texts):
                c.drawString(xx, yy - i * leading, t)

        # how to read a cell
        heading(x, "HOW TO READ A CELL")
        cell_top = hy - 12
        demo = G.lie_cell(G.FAMILY_BY_KEY["A"], 1, 7, cfg.show_atlas_names)
        draw_cell(c, demo, x, cell_top - dh, dw, dh, cfg)
        callouts = [(cell_top - 8, "classical name"),
                    (cell_top - dh * 0.46, "name as a group of Lie type"),
                    (cell_top - dh + 11, "prime factorisation of the order")]
        c.setFont(UI, 9)
        for yy, text in callouts:
            c.setStrokeColor(INK_FAINT)
            c.setLineWidth(0.5)
            c.line(x + dw + 3, yy, x + dw + 14, yy)
            c.setFillColor(INK_SOFT)
            c.drawString(x + dw + 18, yy - 3, text)
        x += dw + 215

        # the no-repetition rule
        heading(x, "NO REPETITIONS")
        draw_cell(c, G.Cell(symbol="", category=G.CLASSICAL, ghost=f"{G.CONG} Alt(5)"),
                  x, cell_top - dh, dw, dh, cfg)
        lines(x + dw + 14, cell_top - 10,
              ["a dashed cell marks a group isomorphic to one",
               "shown elsewhere; it is printed only under its",
               "simplest name.  An empty cell means the group",
               "is not defined there, or is not simple."])
        x += dw + 260

        # notes, in two columns
        heading(x, "NOTES")
        col_w = 470.0
        for k in range(0, len(self.NOTES), 3):
            yy = cell_top - 4
            for note in self.NOTES[k:k + 3]:
                p, _, ph = fitted(note, MATH, INK_SOFT, col_w, 60, 9.0, 7.5, align=TA_LEFT)
                draw_para(c, p, x, yy, col_w, ph)
                yy -= ph + 4
            x += col_w + 28

    # ...................................................................
    def _draw_headers(self, c) -> None:
        cfg = self.cfg
        band_top = self.height - cfg.margin - cfg.title_h
        fam_y = band_top - cfg.family_band_h
        hdr_y = fam_y - cfg.header_h

        for i, col in enumerate(self.cols):
            if col.family_title:
                x = self.col_x(i)
                w = sum(cc.width for cc in self.cols[i:i + col.family_span])
                cat = col.family.category if col.family else G.CYCLIC
                hue = HUES[cat]
                rounded(c, x + 1, fam_y + 3, w - 2, cfg.family_band_h - 6, 3,
                        tint(hue, 0.30), None)
                p, _, ph = fitted(col.family_title, MATH, INK, w - 8,
                                  cfg.family_band_h - 8, 12.5, 6.0)
                draw_para(c, p, x + 4, fam_y + 3 + (cfg.family_band_h - 6 + ph) / 2,
                          w - 8, ph)
            if col.kind == "cells":
                x = self.col_x(i)
                p, _, ph = fitted(col.header, MATH, INK_SOFT, col.width - 6,
                                  cfg.header_h - 6, 12.0, 6.0)
                draw_para(c, p, x + 3, hdr_y + (cfg.header_h + ph) / 2, col.width - 6, ph)

    # ...................................................................
    def _draw_axis(self, c) -> None:
        cfg = self.cfg
        x = cfg.margin
        for j, row in enumerate(self.rows):
            y = self.row_y(j)
            if row.kind == "dots":
                draw_dots(c, x, y, cfg.axis_w, row.height, vertical=True)
                continue
            label = "q" if row.q is None else str(row.q)
            p, _, ph = fitted(label, MATH + "-Bold", INK, cfg.axis_w - 8, row.height,
                              17.0, 9.0)
            draw_para(c, p, x + 4, y + (row.height + ph) / 2, cfg.axis_w - 8, ph)
            if row.q is not None:
                from .arith import prime_power
                pp = prime_power(row.q)
                sub = f"{pp[0]}{G.sup(pp[1])}" if pp[1] > 1 else "prime"
                p2, _, ph2 = fitted(sub, MATH, INK_FAINT, cfg.axis_w - 8, 12, 7.0, 5.0)
                draw_para(c, p2, x + 4, y + (row.height - ph) / 2 - 1, cfg.axis_w - 8, ph2)

        # axis title
        c.saveState()
        c.translate(cfg.margin + 12, self.row_y(len(self.rows) - 1) - 4)
        c.setFillColor(INK_SOFT)
        c.setFont(UI + "-Bold", 11)
        c.drawString(0, -12, "q  =  size of the field")
        c.restoreState()

    # ...................................................................
    def _draw_grid(self, c) -> None:
        cfg = self.cfg
        for i, col in enumerate(self.cols):
            x = self.col_x(i)
            for j, row in enumerate(self.rows):
                y = self.row_y(j)
                if col.kind == "dots" or row.kind == "dots":
                    if col.kind == "dots" and row.kind == "cells":
                        draw_dots(c, x, y, col.width, row.height, vertical=False)
                    elif row.kind == "dots" and col.kind == "cells":
                        draw_dots(c, x, y, col.width, row.height, vertical=True)
                    continue
                cell = (G.cyclic_cell(row.q, cfg.show_atlas_names) if col.family is None
                        else G.lie_cell(col.family, col.rank, row.q, cfg.show_atlas_names))
                if cell is None:
                    continue
                draw_cell(c, cell, x + cfg.gap / 2, y + cfg.gap / 2,
                          col.width - cfg.gap, row.height - cfg.gap, cfg)

    # ...................................................................
    NOTES = [
        "\u2022  Each column of a family of Lie type is one rank n;  the column after the "
        "ellipsis is the generic rank, and the row after the ellipsis is the generic q.",
        "\u2022  A cell carrying a parameter shows the generic order formula in place of a "
        "prime factorisation.",
        "\u2022  C<sub>n</sub>(q) \u2245 B<sub>n</sub>(q) for q even, so only the odd-q cells "
        "of the C columns are printed.",
        "\u2022  <super>2</super>B<sub>2</sub>(q) and <super>2</super>F<sub>4</sub>(q) exist for "
        "q = 2<super>2m+1</super> and <super>2</super>G<sub>2</sub>(q) for q = "
        "3<super>2m+1</super> (m \u2265 1);  their other rows are empty.",
        "\u2022  <super>2</super>F<sub>4</sub>(2) is not simple, but its derived subgroup \u2014 "
        "the Tits group \u2014 is, and is printed in that cell.",
        "\u2022  Alternating and sporadic groups belong to no family of Lie type;  they are "
        "shown in their own strips below.",
    ]

    def _draw_bottom(self, c) -> None:
        cfg = self.cfg
        top = self.row_y(len(self.rows) - 1) - cfg.bottom_gap
        x = cfg.margin + cfg.axis_w
        y = top - 24 - cfg.cell_h

        def heading(xx, text):
            c.setFillColor(INK)
            c.setFont(UI + "-Bold", 13)
            c.drawString(xx, top - 14, text)

        # ---- alternating strip
        heading(x, "Alternating groups")
        for n in range(5, cfg.alt_max + 1):
            draw_cell(c, G.alternating_cell(n, cfg.show_atlas_names), x, y,
                      cfg.cell_w - cfg.gap, cfg.cell_h - cfg.gap, cfg)
            x += cfg.cell_w
        dw = cfg.cell_w * cfg.dots_frac
        draw_dots(c, x, y, dw, cfg.cell_h, vertical=False)
        x += dw
        draw_cell(c, G.alternating_cell(None, cfg.show_atlas_names), x, y,
                  cfg.cell_w - cfg.gap, cfg.cell_h - cfg.gap, cfg)
        x += cfg.cell_w
        draw_dots(c, x, y, dw, cfg.cell_h, vertical=False)
        x += dw + 30

        # ---- sporadic strip
        heading(x, "Sporadic groups")
        for k, cell in enumerate(G.sporadic_cells(cfg.show_atlas_names)):
            r, cc = divmod(k, cfg.sporadic_cols)
            draw_cell(c, cell, x + cc * cfg.cell_w, top - 24 - (r + 1) * cfg.cell_h,
                      cfg.cell_w - cfg.gap, cfg.cell_h - cfg.gap, cfg)
        x += min(cfg.sporadic_cols, len(G.SPORADIC_GROUPS)) * cfg.cell_w + 30

        # ---- the theorem that makes the poster finite
        right = cfg.margin + cfg.axis_w + self.grid_w
        box_w = max(240.0, right - x)
        rounded(c, x, y, box_w, cfg.cell_h, 5, HexColor("#f4f3ef"), HexColor("#d9d7cf"), 0.8)
        c.setFillColor(INK)
        c.setFont(UI + "-Bold", 11)
        c.drawString(x + 12, y + cfg.cell_h - 20, "CLASSIFICATION THEOREM")
        body = ("Every finite simple group is cyclic of prime order, alternating of degree "
                "n \u2265 5, a group of Lie type, or one of the 26 sporadic groups.  "
                "This poster shows every one of them, each exactly once.")
        p, _, ph = fitted(body, MATH, INK_SOFT, box_w - 24, cfg.cell_h - 34, 10.5, 7.0,
                          align=TA_LEFT)
        draw_para(c, p, x + 12, y + cfg.cell_h - 28, box_w - 24, ph)
