"""Dynkin diagrams for the column headings.

Each column of the poster is one family of Lie type, and a family is its
Dynkin diagram.  For the Steinberg, Suzuki and Ree groups the diagram carries
a second mark: the automorphism of the diagram that the Frobenius twist uses,
drawn as an arrow (or, for triality, a turn) in its own colour.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

NODE, ELLIPSIS = "o", "."


@dataclass
class Diagram:
    #: (x, y, kind) in diagram units;  y = 0 is the spine
    nodes: list
    #: (i, j, multiplicity, arrow):  arrow is +1 toward j, -1 toward i, 0 none
    bonds: list = field(default_factory=list)
    #: pairs of nodes the twist exchanges
    swaps: list = field(default_factory=list)
    #: node the triality turns about, for 3D4
    triality: int | None = None


# --------------------------------------------------------------------------
# the diagrams
# --------------------------------------------------------------------------

def _spine(k: int) -> list:
    """``k`` nodes along the spine, or ``o o ... o`` when ``k`` is None."""
    if k is None:
        return [(0, 0.0, NODE), (1, 0.0, NODE), (2, 0.0, ELLIPSIS), (3, 0.0, NODE)]
    return [(i, 0.0, NODE) for i in range(k)]


def _spine_bonds(m: int, mult_last: int = 1, arrow_last: int = 0) -> list:
    """Single bonds along ``m`` nodes, the last one possibly multiple."""
    out = [(i, i + 1, 1, 0) for i in range(max(m - 2, 0))]
    if m >= 2:
        out.append((m - 2, m - 1, mult_last, arrow_last))
    return out


def _fork(k: int) -> tuple[list, list]:
    """Type D:  a spine with two nodes forked off its end."""
    spine = _spine(None if k is None else k - 2)
    tip = len(spine) - 1
    x = spine[-1][0] + 1
    nodes = spine + [(x, 0.62, NODE), (x, -0.62, NODE)]
    bonds = _spine_bonds(len(spine)) + [(tip, tip + 1, 1, 0), (tip, tip + 2, 1, 0)]
    return nodes, bonds


def _branch(chain: int, at: int) -> tuple[list, list]:
    """Type E:  a spine of ``chain`` nodes with one hung above node ``at``."""
    nodes = _spine(chain) + [(at, 1.0, NODE)]
    bonds = _spine_bonds(chain) + [(at, chain, 1, 0)]
    return nodes, bonds


def diagram(key: str, n) -> Diagram | None:
    """The diagram of family ``key`` at rank ``n`` (``None`` = generic rank)."""
    k = n                                        # None means "generic"
    width = 4 if k is None else k                # nodes actually drawn

    if key in ("A", "2A"):
        nodes = _spine(k)
        d = Diagram(nodes, _spine_bonds(len(nodes)))
        if key == "2A":
            m = len(nodes)
            d.swaps = ([(0, m - 1)] if k is None else
                       [(i, m - 1 - i) for i in range(m // 2)])
        return d

    if key in ("B", "C"):
        nodes = _spine(k)
        return Diagram(nodes, _spine_bonds(len(nodes), 2, +1 if key == "B" else -1))

    if key in ("D", "2D"):
        nodes, bonds = _fork(k)
        d = Diagram(nodes, bonds)
        if key == "2D":
            d.swaps = [(len(nodes) - 2, len(nodes) - 1)]
        return d

    if key == "3D4":
        nodes, bonds = _fork(4)
        return Diagram(nodes, bonds, triality=len(nodes) - 3)

    if key == "G2":
        return Diagram(_spine(2), [(0, 1, 3, +1)])
    if key == "2G2":
        return Diagram(_spine(2), [(0, 1, 3, +1)], swaps=[(0, 1)])
    if key == "2B2":
        return Diagram(_spine(2), [(0, 1, 2, +1)], swaps=[(0, 1)])

    if key in ("F4", "2F4"):
        nodes = _spine(4)
        bonds = [(0, 1, 1, 0), (1, 2, 2, +1), (2, 3, 1, 0)]
        return Diagram(nodes, bonds, swaps=[(0, 3), (1, 2)] if key == "2F4" else [])

    if key in ("E6", "2E6"):
        nodes, bonds = _branch(5, 2)
        return Diagram(nodes, bonds, swaps=[(0, 4), (1, 3)] if key == "2E6" else [])
    if key == "E7":
        return Diagram(*_branch(6, 2))
    if key == "E8":
        return Diagram(*_branch(7, 2))
    return None


# --------------------------------------------------------------------------
# drawing
# --------------------------------------------------------------------------

def _arrowhead(c, x, y, dx, dy, size):
    n = math.hypot(dx, dy) or 1.0
    dx, dy = dx / n, dy / n
    px, py = -dy, dx
    p = c.beginPath()
    p.moveTo(x, y)
    p.lineTo(x - dx * size + px * size * 0.55, y - dy * size + py * size * 0.55)
    p.lineTo(x - dx * size - px * size * 0.55, y - dy * size - py * size * 0.55)
    p.close()
    c.drawPath(p, stroke=0, fill=1)


def draw(c, dia: Diagram, x: float, y: float, w: float, h: float,
         ink, twist_ink) -> None:
    """Draw ``dia`` centred in the box ``(x, y, w, h)``."""
    xs = [p[0] for p in dia.nodes]
    ys = [p[1] for p in dia.nodes]
    span_x = max(max(xs) - min(xs), 1)
    r = 2.7                              # the node is the same size everywhere

    # how far above the spine the twist arcs reach, in diagram units
    spans = [abs(dia.nodes[i][0] - dia.nodes[j][0]) for i, j in dia.swaps]
    spans = [t for t in spans if t > 0.5]          # a fork's tips arc sideways
    rise_u = 0.55 + 0.20 * max(spans) if spans else 0.0

    if dia.triality is not None:                   # the turn encircles it all
        hi_u, lo_u = 1.3, -1.3
    else:
        hi_u, lo_u = max(ys) + rise_u, min(ys)

    unit = min((w - 12) / span_x, 16.0)
    if hi_u > lo_u:
        unit = min(unit, (h - 2 * r - 4) / (hi_u - lo_u))
    unit = max(unit, 2.4 * r)

    cx = x + w / 2 - (min(xs) + max(xs)) / 2 * unit
    cy = y + h / 2 - (hi_u + lo_u) / 2 * unit
    arc = rise_u * unit

    def pos(i):
        return cx + dia.nodes[i][0] * unit, cy + dia.nodes[i][1] * unit

    # ---- bonds
    c.saveState()
    c.setStrokeColor(ink)
    c.setFillColor(ink)
    c.setLineWidth(0.7)
    for i, j, mult, arrow in dia.bonds:
        (xi, yi), (xj, yj) = pos(i), pos(j)
        dx, dy = xj - xi, yj - yi
        n = math.hypot(dx, dy) or 1.0
        ux, uy = dx / n, dy / n
        px, py = -uy, ux
        # a bond stops short of an ellipsis, so the dots stand clear of it
        ri = r if dia.nodes[i][2] is NODE else 5.0
        rj = r if dia.nodes[j][2] is NODE else 5.0
        x0, y0 = xi + ux * ri, yi + uy * ri
        x1, y1 = xj - ux * rj, yj - uy * rj
        offs = [0.0] if mult == 1 else (
            [-0.85, 0.85] if mult == 2 else [-1.5, 0.0, 1.5])
        for o in offs:
            c.line(x0 + px * o, y0 + py * o, x1 + px * o, y1 + py * o)
        if arrow:
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            s = 1 if arrow > 0 else -1
            _arrowhead(c, mx + ux * s * 2.2, my + uy * s * 2.2, ux * s, uy * s, 3.2)

    # ---- nodes
    for i, (_, _, kind) in enumerate(dia.nodes):
        xi, yi = pos(i)
        if kind is ELLIPSIS:
            c.setFillColor(ink)
            for d in (-2.6, 0.0, 2.6):
                c.circle(xi + d, yi, 0.62, stroke=0, fill=1)
        else:
            c.setFillColorRGB(1, 1, 1)
            c.circle(xi, yi, r, stroke=1, fill=1)
    c.restoreState()

    # ---- the twist
    if not dia.swaps and dia.triality is None:
        return
    c.saveState()
    c.setStrokeColor(twist_ink)
    c.setFillColor(twist_ink)
    c.setLineWidth(0.8)

    if dia.triality is not None:
        # a turn about the branch node: the three outer nodes rotate into
        # one another, and the gap in the arc is where no node sits
        ox, oy = pos(dia.triality)
        rad = unit * 1.3
        c.arc(ox - rad, oy - rad, ox + rad, oy + rad, 100, 320)
        a = math.radians(60)
        _arrowhead(c, ox + rad * math.cos(a), oy + rad * math.sin(a),
                   -math.sin(a), math.cos(a), 3.6)
        c.restoreState()
        return

    for i, j in dia.swaps:
        (xi, yi), (xj, yj) = pos(i), pos(j)
        if abs(xi - xj) < 0.5:                   # the two tips of a fork
            mid = (xi + xj) / 2 + unit * 0.75
            p = c.beginPath()
            p.moveTo(xi + r + 1.2, yi)
            p.curveTo(mid, yi, mid, yj, xj + r + 1.2, yj)
            c.drawPath(p, stroke=1, fill=0)
            _arrowhead(c, xi + r + 1.2, yi, -1, -0.45, 3.0)
            _arrowhead(c, xj + r + 1.2, yj, -1, 0.45, 3.0)
            continue
        reach = cy + arc
        p = c.beginPath()
        p.moveTo(xi, yi + r + 1.2)
        p.curveTo(xi, reach, xj, reach, xj, yj + r + 1.2)
        c.drawPath(p, stroke=1, fill=0)
        _arrowhead(c, xi, yi + r + 1.2, 0, -1, 3.0)
        _arrowhead(c, xj, yj + r + 1.2, 0, -1, 3.0)
    c.restoreState()
