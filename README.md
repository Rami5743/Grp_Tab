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
* **The vertical axis is the field size `q`**: the `q = 1` row, then one row
  per prime power up to `--q-max`, then a vertical ellipsis, a generic `q`
  row, and a second ellipsis.
* **The first column** is the cyclic groups `Z/pZ` — a cell exists only on the
  rows whose `q` is prime.
* **After it the columns are grouped by rank.** Every family with a simple
  group of rank 1, then of rank 2, and so on:

  ```
  A_1 | A_2 B_2 ²A_2 G_2 ²B_2 ²G_2 | A_3 B_3 C_3 ²A_3 | A_4 B_4 C_4 D_4 ²A_4 ²D_4 F_4 ³D_4 ²F_4 | …
  ```

  Inside a block the order is `A, B, C, D, ²A, ²D`, then the exceptional
  families of that rank.  A family starts at the rank below which it would
  duplicate another one (`B_1 = A_1`, `C_2 = B_2`, `D_3 = A_3`,
  `²D_3 = ²A_3`), which is why rank 2 has no `C_2` and rank 3 no `D_3`.
* **The blocks run to rank 8 and then stop.**  `E_8` is the last family that
  ever appears, so from rank 9 onwards every block is the same six classical
  families — that is the point at which the table stops saying anything new,
  and it is replaced by an ellipsis, the generic-rank block
  `A_n B_n C_n D_n ²A_n ²D_n`, and a second ellipsis.
* **The `q = 1` row is the alternating groups.**  Over "the field with one
  element" a group of Lie type degenerates to its Weyl group, and
  `A_n(1) = Alt(n+1)`.  Of all the Weyl groups only those of type A give a
  simple group, so that row is exactly `Alt(5), Alt(6), Alt(7), …`, sitting in
  the `A` columns.  `A_2(1) = Alt(3)` is cyclic and `A_3(1) = Alt(4)` is
  solvable, so those two cells are not groups of their own.
* **The sporadic groups** get a strip of their own at the bottom.
* **Background colour encodes the type** of group (seven categories, see the
  legend on the poster).
* **No repetitions.** Every group is printed under its simplest name only.  A
  cell whose group is isomorphic to one printed elsewhere is drawn dashed and
  grey, pointing at the cell where it lives (`A_1(4) ≅ Alt(5)`,
  `C_n(q) ≅ B_n(q)` for even `q`, `²A_3(2) ≅ B_2(3)`, …).  An empty cell means
  the group is not defined there, or is not simple.

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
| `--rank-max` | 8 | largest rank with its own block of columns, before the ellipsis |
| `--q-max` | 13 | largest field size with an explicit row |
| `--no-f1-row` | off | drop the `q = 1` row, and with it the alternating groups |
| `--sporadic-cols` | 26 | columns of the sporadic block (26 = a single strip) |
| `--cell-w`, `--cell-h` | 100, 100 | cell size in points |
| `--dots-frac` | 0.42 | size of an ellipsis row/column, relative to a cell |
| `--symbol-size`, `--order-size` | 20, 6.6 | starting font sizes (text is shrunk to fit) |
| `--max-order-lines` | 6 | lines the order line may wrap onto |
| `--no-atlas-names` | off | drop the classical name above each symbol |
| `--title`, `--subtitle` | | the masthead text |

The page size is computed from the grid, so changing `--rank-max` or
`--q-max` simply makes a larger or smaller poster.  The defaults give
**202 × 61 cm**.

## How it is put together

| file | contents |
|---|---|
| `fsg/arith.py` | primality, Pollard-rho factorisation, and the cyclotomic splitting `q^k − 1 = ∏_{e\|k} Φ_e(q)` that makes the big orders factor instantly |
| `fsg/groups.py` | the families, their order formulas, the rank blocks, the exceptional isomorphisms, the 26 sporadic groups; produces one `Cell` per box |
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
The only collisions it tolerates are the two genuine ones — `A_7(1) = Alt(8)`
and `A_2(4) = L_3(4)` (both of order 20160, non-isomorphic), and `B_n(q)` /
`C_n(q)` for odd `q` and `n ≥ 3`.  Anything else would mean a missed
isomorphism.

### On the colours

The seven category hues are the first seven slots of a colour-vision-validated
categorical palette, ordered so that every pair of categories that ends up
side by side on the poster clears the CVD separation gate.  Cells use a 15 %
tint of the hue with a saturated accent bar, so that the text on them keeps
full contrast; identity is never carried by colour alone — every cell is
labelled and the legend is always present.
