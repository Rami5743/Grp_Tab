#!/usr/bin/env python3
"""Checks on the data and on the poster the generator produces.

Run with ``python3 selftest.py``.  Nothing here draws anything; it is the
mathematical content that is being checked.
"""

from __future__ import annotations

import sys

from fsg import arith
from fsg import groups as G
from fsg.render import MATH, Poster, PosterConfig, missing_glyphs, register_fonts

FAILURES: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        FAILURES.append(f"{name}: got {got}, want {want}")


# --------------------------------------------------------------------------
# orders of groups of Lie type, against values that can be looked up
# --------------------------------------------------------------------------

KNOWN_ORDERS = {
    ("A", 1, 4): 60, ("A", 1, 5): 60, ("A", 1, 7): 168, ("A", 1, 8): 504,
    ("A", 1, 9): 360, ("A", 1, 11): 660, ("A", 2, 2): 168, ("A", 2, 3): 5616,
    ("A", 2, 4): 20160, ("A", 3, 2): 20160, ("A", 4, 2): 9999360,
    ("2A", 2, 3): 6048, ("2A", 2, 4): 62400, ("2A", 3, 2): 25920,
    ("2A", 3, 3): 3265920, ("2A", 4, 2): 13685760,
    ("B", 2, 3): 25920, ("B", 2, 5): 4680000, ("B", 3, 3): 4585351680,
    ("C", 3, 3): 4585351680, ("C", 3, 5): 228501000000000,
    ("D", 4, 2): 174182400, ("D", 4, 3): 4952179814400,
    ("2D", 4, 2): 197406720, ("2D", 4, 3): 10151968619520,
    ("G2", 0, 3): 4245696, ("G2", 0, 4): 251596800,
    ("3D4", 0, 2): 211341312, ("3D4", 0, 3): 20560831566912,
    ("F4", 0, 2): 3311126603366400,
    ("E6", 0, 2): 214841575522005575270400,
    ("2E6", 0, 2): 76532479683774853939200,
    ("2B2", 0, 8): 29120, ("2B2", 0, 32): 32537600,
    ("2G2", 0, 27): 10073444472,
}


def test_lie_orders() -> None:
    for (key, n, q), want in KNOWN_ORDERS.items():
        fam = G.FAMILY_BY_KEY[key]
        check(f"|{key}_{n}({q})|", G.lie_order_value(fam, n, q), want)


def test_sporadic_factorisations() -> None:
    """A handful of orders, re-derived from their published factorisations."""
    expected = {
        "M": {2: 46, 3: 20, 5: 9, 7: 6, 11: 2, 13: 3, 17: 1, 19: 1, 23: 1, 29: 1,
              31: 1, 41: 1, 47: 1, 59: 1, 71: 1},
        "B": {2: 41, 3: 13, 5: 6, 7: 2, 11: 1, 13: 1, 17: 1, 19: 1, 23: 1, 31: 1, 47: 1},
        "J<sub>4</sub>": {2: 21, 3: 3, 5: 1, 7: 1, 11: 3, 23: 1, 29: 1, 31: 1, 37: 1, 43: 1},
        "M<sub>24</sub>": {2: 10, 3: 3, 5: 1, 7: 1, 11: 1, 23: 1},
        "Co<sub>1</sub>": {2: 21, 3: 9, 5: 4, 7: 2, 11: 1, 13: 1, 23: 1},
    }
    by_name = {sym: order for sym, _, order in G.SPORADIC_GROUPS}
    check("sporadic count", len(G.SPORADIC_GROUPS), 26)
    for name, fac in expected.items():
        check(f"|{name}|", arith.factor(by_name[name]), fac)


def test_alternating_orders() -> None:
    import math
    for n in range(5, 13):
        cell = G.alternating_cell(n)
        value = 1
        for tok in cell.order.split(G.CDOT):
            base, _, exp = tok.partition("<super>")
            value *= int(base) ** (int(exp.rstrip("</super>")) if exp else 1)
        check(f"|Alt({n})|", value, math.factorial(n) // 2)


# --------------------------------------------------------------------------
# the poster itself
# --------------------------------------------------------------------------

def drawn_cells(cfg: PosterConfig):
    """Every concrete (non-ghost) group the poster prints, with its order."""
    import math
    poster = Poster(cfg)
    out = []
    for col in poster.cols:
        if col.kind != "cells":
            continue
        for row in poster.rows:
            if row.kind != "cells" or row.q is None:
                continue
            if col.family is None:
                cell = G.cyclic_cell(row.q)
                if cell is not None:
                    out.append((f"C_{row.q}", row.q, cell))
                continue
            if col.rank is None:
                continue
            cell = G.lie_cell(col.family, col.rank, row.q)
            if cell is None:
                continue
            if row.q == 1:                      # A_n(1) = Alt(n+1)
                out.append((f"A_{col.rank}(1)",
                            math.factorial(col.rank + 1) // 2, cell))
                continue
            if (col.family.key, col.rank, row.q) == G.TITS:
                out.append(("2F4(2)'", 17971200, cell))
                continue
            out.append((f"{col.family.key}_{col.rank}({row.q})",
                        G.lie_order_value(col.family, col.rank, row.q), cell))
    for sym, _, order in G.SPORADIC_GROUPS:
        out.append((sym, order, None))
    return out


def test_no_repetitions() -> None:
    """No group is printed twice.

    Groups of the same order that really are different are listed here; every
    other collision would be a bug in the isomorphism bookkeeping.
    """
    cells = drawn_cells(PosterConfig())
    by_order: dict[int, list[str]] = {}
    for name, order, _ in cells:
        by_order.setdefault(order, []).append(name)

    def allowed(names: list[str]) -> bool:
        s = set(names)
        if s == {"A_7(1)", "A_2(4)"}:          # Alt(8) and L_3(4), both of order 20160
            return True
        # B_n(q) and C_n(q), q odd, n >= 3: equal orders, non-isomorphic
        if len(s) == 2 and all(n.startswith(("B_", "C_")) for n in s):
            ranks = {n.split("_")[1] for n in s}
            return len(ranks) == 1
        return False

    for order, names in sorted(by_order.items()):
        if len(names) > 1 and not allowed(names):
            FAILURES.append(f"repeated group of order {order}: {names}")


def test_simple_orders() -> None:
    """Every printed group has order > 1, and only the cyclic ones have prime order."""
    for name, order, _ in drawn_cells(PosterConfig()):
        if order <= 1:
            FAILURES.append(f"{name} has order {order}")
        if arith.is_prime(order) and not (name.startswith("C_") and "(" not in name):
            FAILURES.append(f"{name} has prime order but is not in the cyclic column")


def test_glyphs() -> None:
    """Every character the poster prints must exist in the maths font."""
    register_fonts()
    cfg = PosterConfig()
    text = cfg.title + cfg.subtitle + "".join(Poster.NOTES)
    text += "".join(G.CATEGORY_TITLES.values())
    text += "".join(a + b for a, b in G.HOLE_KEY)
    for name, _order, cell in drawn_cells(cfg):
        if cell is not None:
            text += cell.symbol + cell.order + cell.alt
    for fam in G.LIE_FAMILIES:
        for n in (None, fam.min_rank):
            for q in (None, 4):
                try:
                    c = G.lie_cell(fam, n, q)
                except Exception:
                    continue
                if c is not None:
                    text += c.symbol + c.order + c.alt
    text = text.replace("<super>", "").replace("</super>", "")
    text = text.replace("<sub>", "").replace("</sub>", "")
    missing = missing_glyphs(text, MATH)
    if missing:
        FAILURES.append(f"glyphs missing from the maths font: {missing}")


def main() -> int:
    for fn in (test_lie_orders, test_sporadic_factorisations, test_alternating_orders,
               test_no_repetitions, test_simple_orders, test_glyphs):
        fn()
        print(f"  ran {fn.__name__}")
    if FAILURES:
        print("\nFAILED:")
        for f in FAILURES:
            print("  -", f)
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
