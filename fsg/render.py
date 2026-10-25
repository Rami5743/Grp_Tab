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
    G.CHEVALLEY: "#2a78d6",
    G.STEINBERG: "#1baf7a",
    G.SUZUKI_REE: "#eda100",
    G.ALTERNATING: "#e87ba4",
    G.SPORADIC: "#6250d6",
}

INK = HexColor("#121212")
INK_SOFT = HexColor("#55534e")
INK_FAINT = HexColor("#8a8780")
PAPER = HexColor("#fcfcfb")


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

    #: largest rank with its own block of explicit columns.  The default, 8,
    #: is the last rank at which a new family appears (E_8); past it every
    #: block repeats the same six classical families.
    rank_max: int = 9
    #: largest field size q shown explicitly (rows are the prime powers <= this)
    q_max: int = 32
    #: include the q = 1 row, where A_n(1) = Alt(n+1)
    include_f1: bool = True
    #: further rows past ``q_max``, chosen so that the Suzuki and Ree columns
    #: -- which only exist for q = 2^(2m+1) and 3^(2m+1) -- carry at least
    #: two groups each
    extra_q: tuple = ()
    #: columns of the sporadic block (26 puts them all in one strip)
    sporadic_cols: int = 26

    cell_w: float = 100.0
    cell_h: float = 106.0
    dots_frac: float = 0.42          # width/height of an ellipsis row or column
    gap: float = 3.0                 # gap between neighbouring cells
    series_gap: float = 22.0         # extra gap between sporadic series

    margin: float = 46.0
    axis_w: float = 52.0
    header_h: float = 26.0           # per-column header band
    block_band_h: float = 30.0       # the band naming each rank block
    title_h: float = 224.0
    bottom_gap: float = 40.0

    show_alt_names: bool = True
    max_order_lines: int = 7
    symbol_size: float = 20.0
    alt_size: float = 7.4
    #: the order line is set as large as its box allows -- this is the cap,
    #: not the size it is usually printed at
    order_size: float = 14.0
    min_order_size: float = 5.0
    #: line spacing of the order line, as a multiple of its font size;  maths
    #: full of superscripts needs more than running text does
    order_leading: float = 1.34

    title: str = "A Periodic Table of the Finite Simple Groups"
    subtitle: str = ("Every finite simple group appears exactly once, in its simplest form.  "
                     "Columns are grouped by rank; the vertical axis is the field size q.")


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
    block_title: str = ""          # non-empty on the first column of a block
    block_span: int = 1


@dataclass
class Row:
    kind: str                      # "cells" | "dots"
    height: float
    q: int | None = None           # None => generic q


def build_columns(cfg: PosterConfig) -> list[Column]:
    """The cyclic column, then one block per rank, then the generic rank.

    Inside a block the families come in the order  A, B, C, D, 2A, 2D  and
    then the exceptional families of that rank, so the poster reads
    A_1 | A_2, B_2, 2A_2, G_2, 2B_2, 2G_2 | A_3, B_3, C_3, 2A_3 | ...
    """
    cols = [Column("cells", cfg.cell_w, None, None, header=f"C{G.sub('p')}",
                   block_title="cyclic", block_span=1)]

    def block(title: str, entries) -> None:
        start = len(cols)
        for fam, rank in entries:
            header = fam.symbol(str(rank)) if fam.ranked else fam.symbol("")
            cols.append(Column("cells", cfg.cell_w, fam,
                               rank if fam.ranked else 0, header=header))
        if len(cols) > start:
            cols[start].block_title = title
            cols[start].block_span = len(cols) - start

    for n in range(1, cfg.rank_max + 1):
        block(f"rank {n}", G.families_of_rank(n))
    cols.append(Column("dots", cfg.cell_w * cfg.dots_frac))
    start = len(cols)
    for key in G.RANKED_ORDER:
        fam = G.FAMILY_BY_KEY[key]
        cols.append(Column("cells", cfg.cell_w, fam, None, header=fam.symbol("n")))
    cols[start].block_title = "rank n"
    cols[start].block_span = len(cols) - start
    cols.append(Column("dots", cfg.cell_w * cfg.dots_frac))
    return cols


def build_rows(cfg: PosterConfig) -> list[Row]:
    """One row per displayed q, with an ellipsis wherever prime powers are skipped."""
    from .arith import prime_powers_up_to
    qs = sorted(set(prime_powers_up_to(cfg.q_max)) | set(cfg.extra_q))
    every = prime_powers_up_to(max(qs)) if qs else []
    dots = Row("dots", cfg.cell_h * cfg.dots_frac)

    rows: list[Row] = []
    if cfg.include_f1:
        rows.append(Row("cells", cfg.cell_h, 1))
    prev = None
    for q in qs:
        if prev is not None and every.index(q) != every.index(prev) + 1:
            rows.append(Row("dots", dots.height))
        rows.append(Row("cells", cfg.cell_h, q))
        prev = q
    rows.append(Row("dots", dots.height))
    rows.append(Row("cells", cfg.cell_h, None))
    rows.append(Row("dots", dots.height))
    return rows


# --------------------------------------------------------------------------
# low-level drawing helpers
# --------------------------------------------------------------------------

def _style(font, size, color, align=TA_CENTER, leading=None):
    return ParagraphStyle("s", fontName=font, fontSize=size,
                          leading=leading or size * 1.14,
                          textColor=color, alignment=align)


def fitted(text: str, font: str, color, max_w: float, max_h: float,
           start: float, floor: float, align=TA_CENTER,
           leading: float = 1.14) -> tuple[Paragraph, float, float]:
    """Largest paragraph of ``text`` (down to ``floor`` pt) fitting the box."""
    size = start
    while True:
        p = Paragraph(text, _style(font, size, color, align, size * leading))
        w, h = p.wrap(max_w, 10_000)
        if h <= max_h or size <= floor:
            return p, w, h
        size -= 0.3


def fits_at(text: str, font: str, max_w: float, max_h: float, size: float,
            leading: float = 1.14) -> bool:
    p = Paragraph(text, _style(font, size, INK_SOFT, leading=size * leading))
    return p.wrap(max_w, 10_000)[1] <= max_h


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
    """One box: alternative descriptions flush left at the top, the group's
    symbol just below them, and the order filling everything underneath."""
    hue = HUES[cell.category]
    pad = 4.5
    inner = w - 2 * pad
    rounded(c, x, y, w, h, 4.0, tint(hue, 0.15), tint(hue, 0.62), 0.7)

    # accent bar across the top: the category signal, repeated by the legend
    c.saveState()
    c.setFillColor(HexColor(hue))
    c.roundRect(x, y + h - 6.0, w, 6.0, 4.0, stroke=0, fill=1)
    c.rect(x, y + h - 6.0, w, 3.0, stroke=0, fill=1)
    c.restoreState()

    # The three bands have fixed heights, so symbols, rules and order lines
    # all sit at the same height right across a row.
    band_alt = cfg.alt_size * 1.25
    # a symbol carries subscripts that reach below the line box reportlab
    # reports, and the order line above carries superscripts that reach above
    # it, so both bands are given room beyond their measured height
    band_sym = cfg.symbol_size * 1.45
    top = y + h - 6.0 - 1.5
    if cell.alt:
        p, _, ph = fitted(cell.alt, MATH, INK_SOFT, inner, band_alt, cfg.alt_size, 4.2,
                          align=TA_LEFT)
        draw_para(c, p, x + pad, top, inner, ph)
    top -= band_alt + 2.0

    # the symbol sits at the top of its band, so all the slack falls below it,
    # which is where the subscripts go
    p_sym, _, sh = fitted(cell.symbol, MATH, INK, inner, band_sym, cfg.symbol_size, 7.0)
    draw_para(c, p_sym, x + pad, top, inner, sh)
    top -= band_sym + 4.0

    if cell.order:
        box_h = top - 4.5 - (y + pad)
        text = cell.order
        # a factorisation that will not fit even at the smallest size gives
        # way to the order formula with q substituted in
        if cell.order_alt and not fits_at(text, MATH, inner, box_h,
                                          cfg.min_order_size, cfg.order_leading):
            text = cell.order_alt
        # the floor here is a hard one: the text must never cross into the
        # symbol above it, so it keeps shrinking past the preferred minimum
        p_ord, _, oh = fitted(text, MATH, INK_SOFT, inner, box_h,
                              cfg.order_size, 3.4, leading=cfg.order_leading)
        draw_para(c, p_ord, x + pad, y + pad + (box_h + oh) / 2, inner, oh)
        c.setStrokeColor(tint(hue, 0.45))
        c.setLineWidth(0.4)
        c.line(x + pad * 2, top - 0.5, x + w - pad * 2, top - 0.5)


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
        self.height = (cfg.margin * 2 + cfg.title_h + cfg.block_band_h + cfg.header_h
                       + self.grid_h + cfg.bottom_gap + self.bottom_h)

    # -- geometry ---------------------------------------------------------
    def col_x(self, i: int) -> float:
        return self.cfg.margin + self.cfg.axis_w + sum(c.width for c in self.cols[:i])

    def row_y(self, j: int) -> float:
        """Bottom edge of row ``j``."""
        top = self.height - self.cfg.margin - self.cfg.title_h - self.cfg.block_band_h \
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
        for key in (G.CYCLIC, G.ALTERNATING, G.CHEVALLEY, G.STEINBERG,
                    G.SUZUKI_REE, G.SPORADIC):
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
        cell_top = hy - 12
        x = x0

        def heading(xx, text):
            c.setFillColor(INK)
            c.setFont(UI + "-Bold", 10.5)
            c.drawString(xx, hy, text)

        def lines(xx, yy, texts, size=9.0, leading=11.0):
            c.setFillColor(INK_SOFT)
            c.setFont(UI, size)
            for i, t in enumerate(texts):
                c.drawString(xx, yy - i * leading, t)

        # how to read a cell
        heading(x, "HOW TO READ A CELL")
        demo = G.lie_cell(G.FAMILY_BY_KEY["A"], 1, 7, cfg.show_alt_names)
        draw_cell(c, demo, x, cell_top - dh, dw, dh, cfg)
        for yy, text in [(cell_top - 8, "other descriptions of the same group"),
                         (cell_top - dh * 0.5, "the group"),
                         (cell_top - dh + 11, "prime factorisation of its order")]:
            c.setStrokeColor(INK_FAINT)
            c.setLineWidth(0.5)
            c.line(x + dw + 3, yy, x + dw + 14, yy)
            c.setFillColor(INK_SOFT)
            c.setFont(UI, 9)
            c.drawString(x + dw + 18, yy - 3, text)
        x += dw + 215

        # why a cell is empty, and where the missing groups are
        heading(x, "AN EMPTY CELL")
        lines(x, cell_top - 8,
              ["the group is not defined there, or is not simple,",
               "or it is isomorphic to one printed elsewhere \u2014",
               "every group appears only under its simplest name:"])
        key_x = x + 8
        col_w, per_col = 190.0, 3
        for k in range(0, len(G.HOLE_KEY), per_col):
            yy = cell_top - 44
            for missing, home in G.HOLE_KEY[k:k + per_col]:
                p, _, ph = fitted(f"{missing}  \u2192  {home}", MATH, INK_SOFT,
                                  col_w, 20, 8.5, 6.0, align=TA_LEFT)
                draw_para(c, p, key_x, yy, col_w, ph)
                yy -= ph + 1.5
            key_x += col_w + 10
        x += 4 * (col_w + 10) + 40

        # ---- the families, four to a column
        heading(x, "FAMILIES")
        entries = []
        for key in G.FAMILY_ORDER:
            fam = G.FAMILY_BY_KEY[key]
            sym = fam.symbol("n") if fam.ranked else fam.symbol("")
            name = fam.atlas("n") if fam.ranked else ""
            label = f"{sym}(q)"
            if name and name != sym:
                label += f" = {name}(q)"
            entries.append(f"{label}  \u2014  {fam.title}")
        col_w, per_col = 268.0, 4
        for k in range(0, len(entries), per_col):
            yy = cell_top - 4
            for e in entries[k:k + per_col]:
                p, _, ph = fitted(e, MATH, INK_SOFT, col_w, 26, 9.0, 6.0, align=TA_LEFT)
                draw_para(c, p, x, yy, col_w, ph)
                yy -= ph + 3
            x += col_w + 16

    # ...................................................................
    def _draw_headers(self, c) -> None:
        cfg = self.cfg
        band_top = self.height - cfg.margin - cfg.title_h
        band_y = band_top - cfg.block_band_h
        hdr_y = band_y - cfg.header_h

        for i, col in enumerate(self.cols):
            if col.block_title:
                x = self.col_x(i)
                w = sum(cc.width for cc in self.cols[i:i + col.block_span])
                rounded(c, x + 1, band_y + 3, w - 2, cfg.block_band_h - 6, 3,
                        HexColor("#eceae4"), None)
                p, _, ph = fitted(col.block_title, UI + "-Bold", INK, w - 8,
                                  cfg.block_band_h - 8, 12.5, 6.0)
                draw_para(c, p, x + 4, band_y + 3 + (cfg.block_band_h - 6 + ph) / 2,
                          w - 8, ph)
            if col.kind == "cells":
                x = self.col_x(i)
                p, _, ph = fitted(col.header, MATH, INK_SOFT, col.width - 6,
                                  cfg.header_h - 6, 12.0, 6.0)
                draw_para(c, p, x + 3, hdr_y + (cfg.header_h + ph) / 2, col.width - 6, ph)

    # ...................................................................
    def _draw_axis(self, c) -> None:
        from .arith import prime_power
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
            if row.q is None:
                continue
            if row.q == 1:
                note = "\u201cF\u2081\u201d"
            else:
                pr, e = prime_power(row.q)
                note = f"{pr}{G.sup(e)}" if e > 1 else "prime"
            p2, _, ph2 = fitted(note, MATH, INK_FAINT, cfg.axis_w - 6, 12, 7.0, 5.0)
            draw_para(c, p2, x + 3, y + (row.height - ph) / 2 - 1, cfg.axis_w - 6, ph2)

        c.setFillColor(INK_SOFT)
        c.setFont(UI + "-Bold", 11)
        c.drawString(cfg.margin + 12, self.row_y(len(self.rows) - 1) - 16,
                     "q  =  size of the field")

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
                cell = (G.cyclic_cell(row.q, cfg.show_alt_names) if col.family is None
                        else G.lie_cell(col.family, col.rank, row.q, cfg.show_alt_names))
                if cell is None:
                    continue
                draw_cell(c, cell, x + cfg.gap / 2, y + cfg.gap / 2,
                          col.width - cfg.gap, row.height - cfg.gap, cfg)

    # ...................................................................
    NOTES = [
        "\u2022  After the cyclic column the columns are grouped by rank:  every family "
        "with a simple group of rank 1, then of rank 2, and so on.",
        "\u2022  E<sub>8</sub> is the last family to appear, so from rank 9 onwards every "
        "block is the same six classical families \u2014 hence the ellipsis.",
        "\u2022  Row q = 1:  over \u201cthe field with one element\u201d a group of Lie type "
        "degenerates to its Weyl group, and the cell A<sub>n</sub>(1) holds the alternating "
        "group A<sub>n+1</sub>.  Only type A is simple there, so that row is exactly the "
        "alternating groups.",
        "\u2022  A cell carrying a parameter shows the generic order formula in place of a "
        "prime factorisation, and so does a cell whose factorisation is too long to print.",
        "\u2022  C<sub>n</sub>(q) \u2245 B<sub>n</sub>(q) for q even, so only the odd-q cells "
        "of the C columns are printed.",
        "\u2022  <super>2</super>B<sub>2</sub>(q) and <super>2</super>F<sub>4</sub>(q) exist for "
        "q = 2<super>2m+1</super> and <super>2</super>G<sub>2</sub>(q) for q = "
        "3<super>2m+1</super> (m \u2265 1);  their other rows are empty.",
        "\u2022  <super>2</super>F<sub>4</sub>(2) is not simple, but its derived subgroup \u2014 "
        "the Tits group \u2014 is, and is printed in that cell.",
        "\u2022  The 26 sporadic groups belong to no family of Lie type;  they are shown in "
        "their own strip.",
        "\u2022  A symbol with a subscript and no field is a group over \u201cF<sub>1</sub>\u201d:  "
        "C<sub>p</sub> is cyclic of order p and A<sub>m</sub> is alternating of degree m.  With a "
        "field, A<sub>n</sub>(q) is linear and C<sub>n</sub>(q) symplectic \u2014 the argument "
        "tells them apart.",
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

        # ---- sporadic strip
        heading(x, "Sporadic groups")
        breaks = G.sporadic_series_breaks()
        xx, row, right_edge = x, 0, x
        for k, cell in enumerate(G.sporadic_cells(cfg.show_alt_names)):
            if k and k % cfg.sporadic_cols == 0:       # next row of the block
                row, xx = row + 1, x
            elif breaks[k]:                            # a new series starts here
                xx += cfg.series_gap
            draw_cell(c, cell, xx, top - 24 - (row + 1) * cfg.cell_h,
                      cfg.cell_w - cfg.gap, cfg.cell_h - cfg.gap, cfg)
            xx += cfg.cell_w
            right_edge = max(right_edge, xx)
        x = right_edge + 32

        # ---- the theorem that makes the poster finite
        box_w = 980.0
        rounded(c, x, y, box_w, cfg.cell_h, 5, HexColor("#f4f3ef"), HexColor("#d9d7cf"), 0.8)
        c.setFillColor(INK)
        c.setFont(UI + "-Bold", 11)
        c.drawString(x + 14, y + cfg.cell_h - 21, "CLASSIFICATION THEOREM")
        body = ("Every finite simple group is cyclic of prime order, alternating of degree "
                "n \u2265 5, a group of Lie type, or one of the 26 sporadic groups.  "
                "This poster shows every one of them, each exactly once.")
        p, _, ph = fitted(body, MATH, INK_SOFT, box_w - 28, cfg.cell_h - 36, 11.0, 7.0,
                          align=TA_LEFT)
        draw_para(c, p, x + 14, y + cfg.cell_h - 30, box_w - 28, ph)
        x += box_w + 32

        # ---- notes, in two columns
        c.setFillColor(INK)
        c.setFont(UI + "-Bold", 11)
        c.drawString(x, top - 14, "NOTES")
        right = cfg.margin + cfg.axis_w + self.grid_w
        n_cols = 3
        per_col = -(-len(self.NOTES) // n_cols)
        col_w = max(380.0, (right - x - 26.0 * (n_cols - 1)) / n_cols)
        for k in range(0, len(self.NOTES), per_col):
            yy = top - 22
            for note in self.NOTES[k:k + per_col]:
                p, _, ph = fitted(note, MATH, INK_SOFT, col_w, 60, 8.6, 6.5, align=TA_LEFT)
                draw_para(c, p, x, yy, col_w, ph)
                yy -= ph + 4
            x += col_w + 26
