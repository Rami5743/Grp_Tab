#!/usr/bin/env python3
"""Build the poster.

    python3 make_poster.py --out out/finite_simple_groups.pdf

Every number that the layout depends on is a command-line option; run with
``--help`` to see them.
"""

from __future__ import annotations

import argparse
import os

from fsg.render import Poster, PosterConfig, register_fonts


def parse_args(argv=None) -> argparse.Namespace:
    cfg = PosterConfig()
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--out", default="out/finite_simple_groups.pdf",
                   help="path of the PDF to write")

    g = p.add_argument_group("content")
    g.add_argument("--ranks-shown", type=int, default=cfg.ranks_shown,
                   help="explicit ranks per family of Lie type, before the ellipsis")
    g.add_argument("--q-max", type=int, default=cfg.q_max,
                   help="largest field size q with an explicit row")
    g.add_argument("--alt-max", type=int, default=cfg.alt_max,
                   help="largest alternating group Alt(n) with an explicit cell")
    g.add_argument("--sporadic-cols", type=int, default=cfg.sporadic_cols,
                   help="columns of the sporadic block")
    g.add_argument("--no-atlas-names", action="store_true",
                   help="drop the classical name printed above each symbol")

    g = p.add_argument_group("geometry (points; 1 pt = 1/72 in)")
    g.add_argument("--cell-w", type=float, default=cfg.cell_w)
    g.add_argument("--cell-h", type=float, default=cfg.cell_h)
    g.add_argument("--dots-frac", type=float, default=cfg.dots_frac,
                   help="size of an ellipsis row/column, as a fraction of a cell")
    g.add_argument("--margin", type=float, default=cfg.margin)
    g.add_argument("--symbol-size", type=float, default=cfg.symbol_size)
    g.add_argument("--order-size", type=float, default=cfg.order_size)
    g.add_argument("--max-order-lines", type=int, default=cfg.max_order_lines)

    g = p.add_argument_group("text")
    g.add_argument("--title", default=cfg.title)
    g.add_argument("--subtitle", default=cfg.subtitle)
    return p.parse_args(argv)


def config_from_args(a: argparse.Namespace) -> PosterConfig:
    return PosterConfig(
        ranks_shown=a.ranks_shown, q_max=a.q_max, alt_max=a.alt_max,
        sporadic_cols=a.sporadic_cols, show_atlas_names=not a.no_atlas_names,
        cell_w=a.cell_w, cell_h=a.cell_h, dots_frac=a.dots_frac, margin=a.margin,
        symbol_size=a.symbol_size, order_size=a.order_size,
        max_order_lines=a.max_order_lines, title=a.title, subtitle=a.subtitle,
    )


def main(argv=None) -> None:
    a = parse_args(argv)
    register_fonts()
    poster = Poster(config_from_args(a))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    poster.draw(a.out)
    print(f"{a.out}: {poster.width / 72:.1f} x {poster.height / 72:.1f} in "
          f"({poster.width / 72 * 2.54:.0f} x {poster.height / 72 * 2.54:.0f} cm), "
          f"{len(poster.cols)} columns x {len(poster.rows)} rows")


if __name__ == "__main__":
    main()
