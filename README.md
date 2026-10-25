# A Periodic Table of the Finite Simple Groups

A parametrised generator for a one-page poster that lays out **every finite
simple group exactly once**, in the style of a periodic table.

![poster](out/preview.png)

The PDF is vector-only and is produced directly by Python (reportlab) — no
LaTeX or other external toolchain is needed.

## Layout

* **Each cell** carries three lines: the classical / ATLAS name on top, the
  group's own symbol in the middle, and the **prime factorisation of its
  order** at the bottom.  A cell that carries a parameter (a generic rank, a
  generic field size, or both) shows the **generic order formula** instead of
  a factorisation.
* **The vertical axis is the field size `q`**: one row per prime power up to
  `--q-max`, then a vertical ellipsis, then a generic `q` row, then a second
  ellipsis.
* **The first column** is the cyclic groups `Z/pZ` — a cell exists only on the
  rows whose `q` is prime.
* **Then one block per family of Lie type**: `A_1(q), A_2(q), …` up to
  `--ranks-shown` explicit ranks, a horizontal ellipsis, a generic-rank column
  `A_n(q)`, and a second ellipsis; then the same for `²A_n(q)`, `B_n(q)`,
  `C_n(q)`, `D_n(q)`, `²D_n(q)`, and one column each for the exceptional
  families `G_2, F_4, E_6, E_7, E_8, ³D_4, ²E_6, ²B_2, ²G_2, ²F_4`.
* **Alternating and sporadic groups** get their own strips at the bottom.
* **Background colour encodes the type** of group (seven categories, see the
  legend on the poster).
* **No repetitions.** Every group is printed under its simplest name only.  A
  cell whose group is isomorphic to one printed elsewhere is drawn dashed and
  grey, pointing at the cell where it lives (`A_1(4) ≅ Alt(5)`,
  `C_n(q) ≅ B_n(q)` for even `q`, …).  An empty cell means the group is not
  defined there, or is not simple.

## Use

```bash
python3 make_poster.py --out out/finite_simple_groups.pdf
python3 make_poster.py --help          # every parameter
python3 selftest.py                    # check the mathematical content
```

The parameters the task left open are command-line options; the defaults are
the ones used for `out/finite_simple_groups.pdf`:

| option | default | meaning |
|---|---|---|
| `--ranks-shown` | 3 | explicit ranks per family of Lie type, before the ellipsis |
| `--q-max` | 13 | largest field size with an explicit row |
| `--alt-max` | 9 | largest alternating group with an explicit cell |
| `--sporadic-cols` | 26 | columns of the sporadic block (26 = a single strip) |
| `--cell-w`, `--cell-h` | 104, 96 | cell size in points |
| `--dots-frac` | 0.42 | size of an ellipsis row/column, relative to a cell |
| `--symbol-size`, `--order-size` | 20, 6.6 | starting font sizes (text is shrunk to fit) |
| `--max-order-lines` | 5 | lines the order line may wrap onto |
| `--no-atlas-names` | off | drop the classical name above each symbol |
| `--title`, `--subtitle` | | the masthead text |

The page size is computed from the grid, so changing `--ranks-shown` or
`--q-max` simply makes a larger or smaller poster.  The defaults give
**152 × 55 cm**.

## How it is put together

| file | contents |
|---|---|
| `fsg/arith.py` | primality, Pollard-rho factorisation, and the cyclotomic splitting `q^k − 1 = ∏_{e\|k} Φ_e(q)` that makes the big orders factor instantly |
| `fsg/groups.py` | the families, their order formulas, the exceptional isomorphisms, the 26 sporadic groups; produces one `Cell` per box |
| `fsg/render.py` | the grid model and all drawing |
| `make_poster.py` | command-line front end |
| `selftest.py` | orders checked against published values, and a check that no group is printed twice |

### On the orders

Orders of groups of Lie type are products of `q^N` with factors `q^k ± 1`.
Factoring those directly is hopeless for, say, `E_8(13)`, but each
`q^k − 1` splits into cyclotomic values `Φ_e(q)`, each of size about `q^φ(e)`,
and those factor in microseconds.  `q^k + 1` is handled as
`(q^{2k} − 1)/(q^k − 1)`.

### On the "no repetitions" rule

`selftest.py` collects every group the poster prints and groups them by order.
The only collisions it tolerates are the two genuine ones — `Alt(8)` and
`A_2(4)` (both of order 20160, non-isomorphic), and `B_n(q)` / `C_n(q)` for
odd `q` and `n ≥ 3`.  Anything else would mean a missed isomorphism.

### On the colours

The seven category hues are the first seven slots of a colour-vision-validated
categorical palette, ordered so that every pair of categories that ends up
side by side on the poster clears the CVD separation gate.  Cells use a 15 %
tint of the hue with a saturated accent bar, so that the text on them keeps
full contrast; identity is never carried by colour alone — every cell is
labelled and the legend is always present.
