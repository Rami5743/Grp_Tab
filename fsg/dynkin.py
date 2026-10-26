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
    #: the pairs of nodes the twist exchanges.  They are drawn as half
    #: ellipses about one common centre, so that they nest instead of crossing.
    swaps: list = field(default_factory=list)
    #: which side of the spine the arrow is drawn on, +1 above, -1 below
    arc_side: int = 1
    #: the three outer nodes triality turns through, and the node it turns
    #: about, for 3D4
    cycle: list | None = None
    centre: int = 0


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
        if key == "2A" and len(nodes) > 1:
            m = len(nodes)
            d.swaps = [(i, m - 1 - i) for i in range(m // 2)]
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
        return Diagram(nodes, bonds, cycle=[0, 2, 3], centre=1)

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
        # the arrow goes under the spine, clear of the branch node above it
        return Diagram(nodes, bonds,
                       swaps=[(0, 4), (1, 3)] if key == "2E6" else [], arc_side=-1)
    if key == "E7":
        return Diagram(*_branch(6, 2))
    if key == "E8":
        return Diagram(*_branch(7, 2))
    return None


# --------------------------------------------------------------------------
# drawing
# --------------------------------------------------------------------------

def _edge(x, y, tx, ty, d):
    """The point ``d`` away from ``(x, y)`` in the direction of ``(tx, ty)``."""
    dx, dy = tx - x, ty - y
    n = math.hypot(dx, dy) or 1.0
    return x + dx / n * d, y + dy / n * d


def _chevron(c, x, y, dx, dy, size):
    """An open "V" pointing along ``(dx, dy)``, drawn wider than it is long so
    that it reads across a double or triple bond."""
    n = math.hypot(dx, dy) or 1.0
    dx, dy = dx / n, dy / n
    px, py = -dy, dx
    wide = size * 0.95
    c.line(x - dx * size + px * wide, y - dy * size + py * wide, x, y)
    c.line(x - dx * size - px * wide, y - dy * size - py * wide, x, y)


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


def length(dia: Diagram, w: float, h: float) -> float:
    """How much of the spine direction ``dia`` takes up in a box ``w`` long."""
    xs = [p[0] for p in dia.nodes]
    span_x = max(max(xs) - min(xs), 1)
    r = 3.4
    unit = max(min((w - 12) / span_x, 24.0), 2.4 * r)
    tail = unit if any(abs(dia.nodes[i][0] - dia.nodes[j][0]) < 0.5
                       for i, j in dia.swaps) else 0.0
    head = unit * 1.05 if dia.cycle is not None else 0.0
    if dia.cycle is not None:
        tail = head
    return (max(xs) - min(xs)) * unit + 2 * r + head + tail


def draw(c, dia: Diagram, x: float, y: float, w: float, h: float,
         ink, twist_ink, x_align: float = 0.5) -> None:
    """Draw ``dia`` in the box ``(x, y, w, h)``.

    ``x_align`` places it along the spine direction: 0.5 centres it, 1.0 pushes
    it to the far end, so that diagrams of different lengths hang from a common
    line instead of floating.
    """
    xs = [p[0] for p in dia.nodes]
    ys = [p[1] for p in dia.nodes]
    span_x = max(max(xs) - min(xs), 1)
    r = 3.4                              # the node is the same size everywhere

    # how far above the spine the twist arcs reach, in diagram units
    spans = [abs(dia.nodes[i][0] - dia.nodes[j][0]) for i, j in dia.swaps]
    spans = [t for t in spans if t > 0.5]          # a fork's tips arc sideways
    rise_u = 0.55 + 0.20 * max(spans) if spans else 0.0

    if dia.cycle is not None:                     # the three arrows bow out
        hi_u, lo_u = max(ys) + 0.9, min(ys) - 0.9
    elif dia.arc_side > 0:
        hi_u, lo_u = max(ys) + rise_u, min(ys)
    else:
        hi_u, lo_u = max(ys), min(ys) - rise_u

    unit = min((w - 12) / span_x, 24.0)
    if hi_u > lo_u:
        unit = min(unit, (h - 2 * r - 4) / (hi_u - lo_u))
    unit = max(unit, 2.4 * r)

    # the arc over a fork's tips, and the arrows of a triality, reach past the
    # ends of the spine;  that reach is part of the room the diagram needs
    tail = unit if any(abs(dia.nodes[i][0] - dia.nodes[j][0]) < 0.5
                       for i, j in dia.swaps) else 0.0
    head = 0.0
    if dia.cycle is not None:
        head = tail = unit * 1.05
    used = (max(xs) - min(xs)) * unit
    cx = (x + r + head + x_align * (w - 2 * r - head - tail - used)
          - min(xs) * unit)
    cy = y + h / 2 - (hi_u + lo_u) / 2 * unit
    arc = rise_u * unit

    def pos(i):
        return cx + dia.nodes[i][0] * unit, cy + dia.nodes[i][1] * unit

    # ---- bonds
    c.saveState()
    c.setStrokeColor(ink)
    c.setFillColor(ink)
    c.setLineWidth(0.9)
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
            [-1.1, 1.1] if mult == 2 else [-1.9, 0.0, 1.9])
        for o in offs:
            c.line(x0 + px * o, y0 + py * o, x1 + px * o, y1 + py * o)
        if arrow:
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            s = 1 if arrow > 0 else -1
            c.saveState()
            c.setLineWidth(1.0)
            c.setLineJoin(1)
            c.setLineCap(1)
            _chevron(c, mx + ux * s * 3.4, my + uy * s * 3.4, ux * s, uy * s,
                     max(4.2, unit * 0.24))
            c.restoreState()

    # ---- nodes
    for i, (_, _, kind) in enumerate(dia.nodes):
        xi, yi = pos(i)
        if kind is ELLIPSIS:
            c.setFillColor(ink)
            for d in (-3.2, 0.0, 3.2):
                c.circle(xi + d, yi, 0.8, stroke=0, fill=1)
        else:
            c.setFillColorRGB(1, 1, 1)
            c.circle(xi, yi, r, stroke=1, fill=1)
    c.restoreState()

    # ---- the twist
    if not dia.swaps and dia.cycle is None:
        return
    c.saveState()
    c.setStrokeColor(twist_ink)
    c.setFillColor(twist_ink)
    c.setLineWidth(1.0)
    c.setLineCap(1)

    if dia.cycle is not None:
        # triality: three arcs of one circle about the branch node, each
        # carrying an outer node to the next
        ox, oy = pos(dia.centre)
        pts = [pos(i) for i in dia.cycle]
        angs = [math.degrees(math.atan2(py - oy, px - ox)) % 360 for px, py in pts]
        rad = sum(math.hypot(px - ox, py - oy) for px, py in pts) / 3 + r + 3.0
        order = sorted(range(3), key=lambda t: angs[t])
        ah = max(3.6, unit * 0.2)
        for t in range(3):
            a0 = angs[order[t]]
            a1 = angs[order[(t + 1) % 3]]
            extent = (a1 - a0) % 360
            pad = 16.0
            c.arc(ox - rad, oy - rad, ox + rad, oy + rad,
                  a0 + pad, extent - 2 * pad)
            a = math.radians(a1 - pad)
            _arrowhead(c, ox + rad * math.cos(a), oy + rad * math.sin(a),
                       -math.sin(a), math.cos(a), ah)
        c.restoreState()
        return

    side = dia.arc_side
    flat = [(i, j) for i, j in dia.swaps
            if abs(dia.nodes[i][0] - dia.nodes[j][0]) < 0.5]
    over = [(i, j) for i, j in dia.swaps
            if abs(dia.nodes[i][0] - dia.nodes[j][0]) >= 0.5]

    for i, j in flat:                            # the two tips of a fork
        (xi, yi), (xj, yj) = pos(i), pos(j)
        mid = (xi + xj) / 2 + unit * 0.9
        ah = max(3.4, unit * 0.19)
        p = c.beginPath()
        p.moveTo(xi + r + 2.0, yi)
        p.curveTo(mid, yi, mid, yj, xj + r + 2.0, yj)
        c.drawPath(p, stroke=1, fill=0)
        _arrowhead(c, xi + r + 2.0, yi, -1, 0, ah)
        _arrowhead(c, xj + r + 2.0, yj, -1, 0, ah)

    if over:
        # concentric half ellipses: every pair is exchanged by the same
        # reflection, so they all share a centre and nest without meeting
        ctr = (pos(over[0][0])[0] + pos(over[0][1])[0]) / 2
        base = pos(over[0][0])[1]
        a_max = max(abs(pos(i)[0] - pos(j)[0]) for i, j in over) / 2
        start, ang = (15.0, 150.0) if side > 0 else (195.0, 150.0)
        ca, sa = math.cos(math.radians(15.0)), math.sin(math.radians(15.0))
        for i, j in over:
            a = abs(pos(i)[0] - pos(j)[0]) / 2
            b = max(arc * a / a_max, r + 3.0)
            c.arc(ctr - a, base - b, ctr + a, base + b, start, ang)
            # the head sits on the end of the arc and points along its
            # tangent, so that no stroke shows past it
            for th, sign in ((math.radians(start), -1.0),
                             (math.radians(start + ang), +1.0)):
                ex, ey = ctr + a * math.cos(th), base + b * math.sin(th)
                _arrowhead(c, ex, ey, sign * -a * math.sin(th),
                           sign * b * math.cos(th), max(3.4, unit * 0.19))
    c.restoreState()
