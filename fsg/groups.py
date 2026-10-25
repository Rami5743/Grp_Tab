"""The mathematical content: families, orders, exceptional isomorphisms.

Every cell of the poster is produced here as a :class:`Cell` -- a small record
holding the markup for the three lines of the cell (ATLAS name, group symbol,
order) plus the colour category.  The renderer knows nothing about groups.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import gcd
from typing import Callable

from . import arith

# --------------------------------------------------------------------------
# tiny markup helpers (the subset of reportlab's mini-HTML that we use)
# --------------------------------------------------------------------------

MINUS = "−"      # proper minus sign
CDOT = "·"       # multiplication dot
CONG = "≅"       # isomorphism sign
PROD = "∏"       # n-ary product
VDOTS = "⋮"
CDOTS = "⋯"


def sup(s) -> str:
    return f"<super>{s}</super>"


def sub(s) -> str:
    return f"<sub>{s}</sub>"


def power(base, exp) -> str:
    """``base**exp`` as markup; the exponent ``1`` is dropped."""
    exp = str(exp)
    return str(base) if exp == "1" else f"{base}{sup(exp)}"


def factorisation_markup(fac: dict[int, int]) -> str:
    """``p1^e1 . p2^e2 . ...``, with a space after each dot.

    The space is the only place a line may be broken, so a prime power is
    never split across two lines; the dot stays at the end of the line.
    """
    return (CDOT + " ").join(power(p, e) for p, e in sorted(fac.items()))


# --------------------------------------------------------------------------
# colour categories
# --------------------------------------------------------------------------

CYCLIC = "cyclic"
ALTERNATING = "alternating"
CLASSICAL = "classical"            # untwisted classical Lie type
CLASSICAL_TWISTED = "classical2"   # twisted classical Lie type
EXCEPTIONAL = "exceptional"        # untwisted exceptional Lie type
EXCEPTIONAL_TWISTED = "exceptional2"
SPORADIC = "sporadic"

CATEGORY_TITLES = {
    CYCLIC: "Cyclic groups",
    ALTERNATING: "Alternating groups",
    CLASSICAL: "Classical Lie type (untwisted)",
    CLASSICAL_TWISTED: "Classical Lie type (twisted)",
    EXCEPTIONAL: "Exceptional Lie type (untwisted)",
    EXCEPTIONAL_TWISTED: "Exceptional Lie type (twisted)",
    SPORADIC: "Sporadic groups",
}


# --------------------------------------------------------------------------
# cells
# --------------------------------------------------------------------------

@dataclass
class Cell:
    """One box of the poster."""
    symbol: str                  # centre line, markup
    order: str = ""              # bottom line, markup
    order_alt: str = ""          # same order as a formula, if the factorisation
                                 # is too long to print
    alt: str = ""                # top line: other descriptions of this group
    category: str = CLASSICAL
    generic: bool = False        # a parametrised cell (order is a formula)
    note: str = ""               # small marker, e.g. the prime of a derived subgroup


# --------------------------------------------------------------------------
# families of Lie type
# --------------------------------------------------------------------------

@dataclass
class Family:
    key: str
    category: str
    ranked: bool                       # does it carry a rank parameter n?
    min_rank: int                      # smallest rank that is displayed
    symbol: Callable[[str], str]       # rank (as a string) -> symbol markup, "(q)" appended later
    atlas: Callable[[str], str]        # rank -> ATLAS/classical name, "(q)" appended later
    q_exponent: Callable[[str], str]   # rank -> exponent N of q, as markup
    terms: Callable[[int], list]       # concrete rank -> [(k, sign, mult), ...]
    generic_terms: Callable[[], str]   # product notation for a generic rank
    divisor: Callable[[int, int], int] = lambda n, q: 1
    divisor_markup: Callable[[str, str], str] = lambda n, q: ""
    q_allowed: Callable[[int], bool] = lambda q: True
    title: str = ""
    # q-values that exist but whose group is not simple
    not_simple: Callable[[int, int], bool] = lambda n, q: False
    # numeric value of the exponent N in q**N
    q_exp_value: Callable[[int], int] = lambda n: 0
    # rank of the Dynkin diagram;  the fixed-rank families use it to find the
    # rank block they belong to
    lie_rank: int = 0


def _gcd_markup(a: str, b: str) -> str:
    """``gcd(a, b)``, evaluated as far as the two arguments allow.

    The divisor d of an order formula collapses for many concrete q -- e.g.
    gcd(n+1, q-1) is 1 for every n once q = 2 -- and printing "/gcd(n+1,1)"
    there would be noise.  An empty result means "the divisor is 1".
    """
    if a.isdigit() and b.isdigit():
        g = gcd(int(a), int(b))
        return "" if g == 1 else str(g)
    if a == "1" or b == "1":
        return ""
    return f"gcd({a},{b})"


def _shift(x: str, delta: int) -> str:
    """``x + delta`` -- evaluated when ``x`` is a literal number, symbolic otherwise."""
    if x.isdigit():
        return str(int(x) + delta)
    return f"{x}{'+' if delta > 0 else MINUS}{abs(delta)}"


def _terms_markup(terms: list, q: str) -> str:
    """Render ``[(k, sign, mult), ...]`` as ``(q^k-1)(q^k+1)/(q^k-1)``."""
    num, den = [], []
    for k, sign, mult in sorted(terms, key=lambda t: -t[0]):
        piece = f"({power(q, k)}{'+' if sign > 0 else MINUS}1)"
        (num if mult > 0 else den).append(piece)
    out = " ".join(num)                     # a factor is never split in two
    if den:
        out += " / " + " ".join(den)
    return out


# ---- the rank-parametrised families --------------------------------------

def _A(n):      return [(i, -1, +1) for i in range(2, n + 2)]
def _2A(n):     return [(i, -1 if i % 2 == 0 else +1, +1) for i in range(2, n + 2)]
def _BC(n):     return [(2 * i, -1, +1) for i in range(1, n + 1)]
def _D(n):      return [(n, -1, +1)] + [(2 * i, -1, +1) for i in range(1, n)]
def _2D(n):     return [(n, +1, +1)] + [(2 * i, -1, +1) for i in range(1, n)]


RANKED_FAMILIES = [
    Family(
        key="A", category=CLASSICAL, ranked=True, min_rank=1,
        symbol=lambda n: f"A{sub(n)}",
        atlas=lambda n: f"L{sub(n + '+1' if not n.isdigit() else int(n) + 1)}",
        q_exponent=lambda n: "n(n+1)/2" if not n.isdigit() else str(int(n) * (int(n) + 1) // 2),
        terms=_A,
        generic_terms=lambda: f"{PROD}{sub('i=2')}{sup('n+1')}({power('q', 'i')}{MINUS}1)",
        divisor=lambda n, q: gcd(n + 1, q - 1),
        divisor_markup=lambda n, q: _gcd_markup(_shift(n, 1), _shift(q, -1)),
        title="Linear",
        q_exp_value=lambda n: n * (n + 1) // 2,
        not_simple=lambda n, q: n == 1 and q < 4,
    ),
    Family(
        key="2A", category=CLASSICAL_TWISTED, ranked=True, min_rank=2,
        symbol=lambda n: f"{sup(2)}A{sub(n)}",
        atlas=lambda n: f"U{sub(n + '+1' if not n.isdigit() else int(n) + 1)}",
        q_exponent=lambda n: "n(n+1)/2" if not n.isdigit() else str(int(n) * (int(n) + 1) // 2),
        terms=_2A,
        generic_terms=lambda: f"{PROD}{sub('i=2')}{sup('n+1')}({power('q', 'i')}{MINUS}({MINUS}1){sup('i')})",
        divisor=lambda n, q: gcd(n + 1, q + 1),
        divisor_markup=lambda n, q: _gcd_markup(_shift(n, 1), _shift(q, 1)),
        title="Unitary",
        q_exp_value=lambda n: n * (n + 1) // 2,
        not_simple=lambda n, q: n == 2 and q == 2,
    ),
    Family(
        key="B", category=CLASSICAL, ranked=True, min_rank=2,
        symbol=lambda n: f"B{sub(n)}",
        atlas=lambda n: f"O{sub('2n+1' if not n.isdigit() else 2 * int(n) + 1)}",
        q_exponent=lambda n: "n\u00b2" if not n.isdigit() else str(int(n) ** 2),
        terms=_BC,
        generic_terms=lambda: f"{PROD}{sub('i=1')}{sup('n')}({power('q', '2i')}{MINUS}1)",
        divisor=lambda n, q: gcd(2, q - 1),
        divisor_markup=lambda n, q: _gcd_markup("2", _shift(q, -1)),
        title="Orthogonal (odd)",
        q_exp_value=lambda n: n * n,
        not_simple=lambda n, q: n == 2 and q == 2,
    ),
    Family(
        key="C", category=CLASSICAL, ranked=True, min_rank=3,
        symbol=lambda n: f"C{sub(n)}",
        atlas=lambda n: f"S{sub('2n' if not n.isdigit() else 2 * int(n))}",
        q_exponent=lambda n: "n\u00b2" if not n.isdigit() else str(int(n) ** 2),
        terms=_BC,
        generic_terms=lambda: f"{PROD}{sub('i=1')}{sup('n')}({power('q', '2i')}{MINUS}1)",
        divisor=lambda n, q: gcd(2, q - 1),
        divisor_markup=lambda n, q: _gcd_markup("2", _shift(q, -1)),
        title="Symplectic",
        q_exp_value=lambda n: n * n,
    ),
    Family(
        key="D", category=CLASSICAL, ranked=True, min_rank=4,
        symbol=lambda n: f"D{sub(n)}",
        atlas=lambda n: f"O{sup('+')}{sub('2n' if not n.isdigit() else 2 * int(n))}",
        q_exponent=lambda n: "n(n" + MINUS + "1)" if not n.isdigit() else str(int(n) * (int(n) - 1)),
        terms=_D,
        generic_terms=lambda: f"({power('q', 'n')}{MINUS}1){PROD}{sub('i=1')}{sup('n' + MINUS + '1')}"
                              f"({power('q', '2i')}{MINUS}1)",
        divisor=lambda n, q: gcd(4, q ** n - 1),
        divisor_markup=lambda n, q: _gcd_markup("4", f"{power(q, n)}{MINUS}1"),
        title="Orthogonal (plus)",
        q_exp_value=lambda n: n * (n - 1),
    ),
    Family(
        key="2D", category=CLASSICAL_TWISTED, ranked=True, min_rank=4,
        symbol=lambda n: f"{sup(2)}D{sub(n)}",
        atlas=lambda n: f"O{sup(MINUS)}{sub('2n' if not n.isdigit() else 2 * int(n))}",
        q_exponent=lambda n: "n(n" + MINUS + "1)" if not n.isdigit() else str(int(n) * (int(n) - 1)),
        terms=_2D,
        generic_terms=lambda: f"({power('q', 'n')}+1){PROD}{sub('i=1')}{sup('n' + MINUS + '1')}"
                              f"({power('q', '2i')}{MINUS}1)",
        divisor=lambda n, q: gcd(4, q ** n + 1),
        divisor_markup=lambda n, q: _gcd_markup("4", f"{power(q, n)}+1"),
        title="Orthogonal (minus)",
        q_exp_value=lambda n: n * (n - 1),
    ),
]


# ---- the fixed-rank (exceptional) families -------------------------------

def _fixed(key, category, symbol, atlas, N, terms, divisor=lambda q: 1,
           divisor_markup=lambda q: "", q_allowed=lambda q: True, title="",
           not_simple=lambda q: False):
    return Family(
        key=key, category=category, ranked=False, min_rank=0,
        symbol=lambda n, _s=symbol: _s,
        atlas=lambda n, _a=atlas: _a,
        q_exponent=lambda n, _N=N: str(_N),
        terms=lambda n, _t=terms: _t,
        generic_terms=lambda: "",
        divisor=lambda n, q, _d=divisor: _d(q),
        divisor_markup=lambda n, q, _d=divisor_markup: _d(q),
        q_allowed=q_allowed,
        title=title,
        not_simple=lambda n, q, _ns=not_simple: _ns(q),
        q_exp_value=lambda n, _N=N: _N,
    )


def _odd_power_of(p, min_exponent=1):
    """q = p**(2m+1).  ``min_exponent`` cuts off the degenerate m = 0 case."""
    def ok(q):
        pp = arith.prime_power(q)
        return (pp is not None and pp[0] == p and pp[1] % 2 == 1
                and pp[1] >= min_exponent)
    return ok


EXCEPTIONAL_FAMILIES = [
    _fixed("G2", EXCEPTIONAL, f"G{sub(2)}", f"G{sub(2)}", 6,
           [(6, -1, 1), (2, -1, 1)], title="Exceptional G₂",
           not_simple=lambda q: q == 2),
    _fixed("F4", EXCEPTIONAL, f"F{sub(4)}", f"F{sub(4)}", 24,
           [(12, -1, 1), (8, -1, 1), (6, -1, 1), (2, -1, 1)], title="Exceptional F₄"),
    _fixed("E6", EXCEPTIONAL, f"E{sub(6)}", f"E{sub(6)}", 36,
           [(12, -1, 1), (9, -1, 1), (8, -1, 1), (6, -1, 1), (5, -1, 1), (2, -1, 1)],
           divisor=lambda q: gcd(3, q - 1),
           divisor_markup=lambda q: _gcd_markup("3", f"{q}{MINUS}1"), title="Exceptional E₆"),
    _fixed("E7", EXCEPTIONAL, f"E{sub(7)}", f"E{sub(7)}", 63,
           [(18, -1, 1), (14, -1, 1), (12, -1, 1), (10, -1, 1), (8, -1, 1), (6, -1, 1), (2, -1, 1)],
           divisor=lambda q: gcd(2, q - 1),
           divisor_markup=lambda q: _gcd_markup("2", f"{q}{MINUS}1"), title="Exceptional E₇"),
    _fixed("E8", EXCEPTIONAL, f"E{sub(8)}", f"E{sub(8)}", 120,
           [(30, -1, 1), (24, -1, 1), (20, -1, 1), (18, -1, 1), (14, -1, 1), (12, -1, 1),
            (8, -1, 1), (2, -1, 1)], title="Exceptional E₈"),
    _fixed("3D4", EXCEPTIONAL_TWISTED, f"{sup(3)}D{sub(4)}", f"{sup(3)}D{sub(4)}", 12,
           [(12, -1, 1), (4, -1, -1), (6, -1, 1), (2, -1, 1)], title="Triality"),
    _fixed("2E6", EXCEPTIONAL_TWISTED, f"{sup(2)}E{sub(6)}", f"{sup(2)}E{sub(6)}", 36,
           [(12, -1, 1), (9, +1, 1), (8, -1, 1), (6, -1, 1), (5, +1, 1), (2, -1, 1)],
           divisor=lambda q: gcd(3, q + 1),
           divisor_markup=lambda q: _gcd_markup("3", f"{q}+1"), title="Twisted E₆"),
    _fixed("2B2", EXCEPTIONAL_TWISTED, f"{sup(2)}B{sub(2)}", "Sz", 2,
           [(2, +1, 1), (1, -1, 1)], q_allowed=_odd_power_of(2, 3), title="Suzuki"),
    _fixed("2G2", EXCEPTIONAL_TWISTED, f"{sup(2)}G{sub(2)}", "R", 3,
           [(3, +1, 1), (1, -1, 1)], q_allowed=_odd_power_of(3), title="Ree (small)",
           not_simple=lambda q: q == 3),
    _fixed("2F4", EXCEPTIONAL_TWISTED, f"{sup(2)}F{sub(4)}", f"{sup(2)}F{sub(4)}", 12,
           [(6, +1, 1), (4, -1, 1), (3, +1, 1), (1, -1, 1)], q_allowed=_odd_power_of(2),
           title="Ree (large)", not_simple=lambda q: q == 2),
]

#: rank of the Dynkin diagram of each exceptional family
EXCEPTIONAL_RANKS = {"G2": 2, "F4": 4, "E6": 6, "E7": 7, "E8": 8,
                     "3D4": 4, "2E6": 6, "2B2": 2, "2G2": 2, "2F4": 4}
for _fam in EXCEPTIONAL_FAMILIES:
    _fam.lie_rank = EXCEPTIONAL_RANKS[_fam.key]

LIE_FAMILIES = RANKED_FAMILIES + EXCEPTIONAL_FAMILIES
FAMILY_BY_KEY = {f.key: f for f in LIE_FAMILIES}

#: order of the families inside one rank block: untwisted classical, twisted
#: classical, untwisted exceptional, twisted exceptional
FAMILY_ORDER = ["A", "B", "C", "D", "2A", "2D",
                "G2", "F4", "E6", "E7", "E8", "3D4", "2E6", "2B2", "2G2", "2F4"]

RANKED_ORDER = [k for k in FAMILY_ORDER if FAMILY_BY_KEY[k].ranked]

#: the largest rank at which a family appears for the first time.  Past it
#: every rank block is the same six classical families -- the point at which
#: the table stops saying anything new.
LAST_INTERESTING_RANK = max(EXCEPTIONAL_RANKS.values())


def families_of_rank(n: int) -> list[tuple["Family", int]]:
    """The families with a simple group of rank ``n``, in display order.

    Each family starts at the rank below which it would duplicate another
    one:  B_1 = A_1,  C_2 = B_2,  D_3 = A_3  and  2D_3 = 2A_3  are not
    repeated, so B starts at 2, C at 3, D and 2D at 4.
    """
    out: list[tuple[Family, int]] = []
    for key in FAMILY_ORDER:
        fam = FAMILY_BY_KEY[key]
        if fam.ranked:
            if n >= fam.min_rank:
                out.append((fam, n))
        elif fam.lie_rank == n:
            out.append((fam, 0))
    return out


# --------------------------------------------------------------------------
# orders
# --------------------------------------------------------------------------

def lie_order_factorisation(fam: Family, n: int, q: int) -> dict[int, int]:
    p, a = arith.prime_power(q)
    out = {p: a * fam.q_exp_value(n)}
    for k, sign, mult in fam.terms(n):
        arith.merge(out, arith.factor_binom(q, k, sign), sign=mult)
    d = fam.divisor(n, q)
    if d > 1:
        arith.merge(out, arith.factor(d), sign=-1)
    return out


def lie_order_value(fam: Family, n: int, q: int) -> int:
    return arith.value(lie_order_factorisation(fam, n, q))


def lie_order_formula(fam: Family, n, q) -> str:
    """Order of ``fam`` as a formula, with any concrete value substituted in.

    ``n`` or ``q`` may be ``None``, meaning "generic".
    """
    q_str = "q" if q is None else str(q)
    n_str = "n" if n is None else str(n)
    body = power(q_str, fam.q_exponent(n_str))
    if n is None and fam.ranked:
        body += fam.generic_terms().replace("q", q_str) if q is not None else fam.generic_terms()
    else:
        body += _terms_markup(fam.terms(n if n is not None else fam.min_rank), q_str)
    dm = fam.divisor_markup(n_str, q_str)
    if dm:
        body += " / " + dm
    return body


def lie_order_markup(fam: Family, n, q) -> str:
    """Prime factorisation of the order when both parameters are concrete,
    the order formula otherwise."""
    if n is not None and q is not None:
        return factorisation_markup(lie_order_factorisation(fam, n, q))
    return lie_order_formula(fam, n, q)


# --------------------------------------------------------------------------
# exceptional isomorphisms -- "every group in its simplest form"
# --------------------------------------------------------------------------

def _alt(n: int) -> str:
    """The alternating group on n letters.  Like the cyclic C_p, it carries no
    field, which is what tells it apart from the linear family A_n(q)."""
    return f"A{sub(n)}"


#: ``(family key, rank, q) -> the cell where that group actually lives``
DUPLICATES: dict[tuple, str] = {
    ("A", 1, 4): _alt(5),
    ("A", 1, 5): _alt(5),
    ("A", 1, 9): _alt(6),
    ("A", 3, 2): _alt(8),
    ("A", 2, 2): f"A{sub(1)}(7)",
    ("2A", 3, 2): f"B{sub(2)}(3)",
}

#: groups that are not simple, but whose derived subgroup is simple and lives
#: somewhere else on the poster
DERIVED: dict[tuple, str] = {
    ("B", 2, 2): _alt(6),
    ("G2", 0, 2): f"{sup(2)}A{sub(2)}(3)",
    ("2G2", 0, 3): f"A{sub(1)}(8)",
}

#: groups that are not simple and contribute nothing
NOT_SIMPLE_EMPTY: set = {("A", 1, 2), ("A", 1, 3), ("2A", 2, 2)}

#: the Tits group, displayed in the  2F4  column
TITS = ("2F4", 0, 2)


#: Every hole the "simplest form" rule leaves in the table, as
#: (what is not printed there, where that group is printed instead).
#: A prime marks a derived subgroup: the group in that cell is not simple,
#: but its derived subgroup is, and it lives elsewhere.
HOLE_KEY: list[tuple[str, str]] = [
    (f"A{sub(2)}(1)", f"C{sub(3)}"),
    (f"A{sub(1)}(4), A{sub(1)}(5)", f"A{sub(5)}   [ A{sub(4)}(1) ]"),
    (f"A{sub(1)}(9)", f"A{sub(6)}   [ A{sub(5)}(1) ]"),
    (f"A{sub(2)}(2)", f"A{sub(1)}(7)"),
    (f"A{sub(3)}(2)", f"A{sub(8)}   [ A{sub(7)}(1) ]"),
    (f"{sup(2)}A{sub(3)}(2)", f"B{sub(2)}(3)"),
    (f"C{sub('n')}(q),  q even", f"B{sub('n')}(q)"),
    (f"B{sub(2)}(2)\u2032", f"A{sub(6)}   [ A{sub(5)}(1) ]"),
    (f"G{sub(2)}(2)\u2032", f"{sup(2)}A{sub(2)}(3)"),
    (f"{sup(2)}G{sub(2)}(3)\u2032", f"A{sub(1)}(8)"),
]


#: Other descriptions of a group, printed on the top line of its cell.  Only
#: genuine coincidences go here -- a second notation for the same construction
#: (A_n(q) = L_{n+1}(q)) is in the key of families instead.
ALT_DESCRIPTIONS: dict[tuple, list[str]] = {
    ("A", 1, 7): [f"A{sub(2)}(2)"],
    ("A", 1, 8): [f"{sup(2)}G{sub(2)}(3)\u2032"],
    ("B", 2, 3): [f"{sup(2)}A{sub(3)}(2)"],
    ("2A", 2, 3): [f"G{sub(2)}(2)\u2032"],
}

#: the same, for the alternating groups in the q = 1 row, keyed by n in A_n(1)
F1_ALT_DESCRIPTIONS: dict[int, list[str]] = {
    4: [f"A{sub(1)}(4)", f"A{sub(1)}(5)"],
    5: [f"A{sub(1)}(9)", f"B{sub(2)}(2)\u2032"],
    7: [f"A{sub(3)}(2)"],
}


def _alt_line(parts: list[str], lead: str = "") -> str:
    """``lead`` followed by each alternative description, each after a congruence."""
    return lead + "".join(f"{' ' if lead or i else ''}{CONG} {t}"
                          for i, t in enumerate(parts))


def alt_descriptions(fam_key: str, n: int, q: int) -> list[str]:
    out = list(ALT_DESCRIPTIONS.get((fam_key, n, q), ()))
    if fam_key == "B" and q % 2 == 0:            # B_n(q) = C_n(q) in characteristic 2
        out.append(f"C{sub(n)}({q})")
    return out


def duplicate_of(fam_key: str, n: int, q: int) -> str | None:
    """Where this group lives instead, or ``None`` if this is its home."""
    if (fam_key, n, q) in DUPLICATES:
        return DUPLICATES[(fam_key, n, q)]
    if fam_key == "C" and q % 2 == 0:
        return f"B{sub(n)}({q})"
    return None


# --------------------------------------------------------------------------
# cell construction
# --------------------------------------------------------------------------

def f1_cell(n, show_alt: bool = True) -> Cell | None:
    """The cell of ``A_n(1)``.

    Over "the field with one element" a group of Lie type degenerates to its
    Weyl group, and the cell A_n(1) holds the alternating group A_(n+1).  Of
    all the Weyl groups only those of type A give a simple group, so this is
    the whole q = 1 row -- and it is where the alternating groups live.  The
    group is named A_(n+1);  "A_n(1)" is only its address on the poster.
    """
    if n is None:
        return Cell(symbol=f"A{sub('n+1')}", order="(n+1)! / 2",
                    category=ALTERNATING, generic=True)
    m = n + 1
    if m < 5:                 # A_2 trivial, A_3 = C_3 cyclic, A_4 solvable
        return None
    fac = arith.factor_factorial(m)
    arith.merge(fac, {2: 1}, sign=-1)
    alt = _alt_line(F1_ALT_DESCRIPTIONS.get(n, [])) if show_alt else ""
    return Cell(symbol=_alt(m), alt=alt,
                order=factorisation_markup(fac), category=ALTERNATING)


def lie_cell(fam: Family, n, q, show_alt: bool = True) -> Cell | None:
    """Build the cell for ``fam`` at rank ``n`` / field ``q`` (``None`` = generic)."""
    if q == 1:
        return f1_cell(n, show_alt) if fam.key == "A" else None
    concrete = n is not None and q is not None
    n_str = "n" if n is None else str(n)
    q_str = "q" if q is None else str(q)

    if q is not None and not fam.q_allowed(q):
        return None
    if n is not None and n < fam.min_rank:
        return None

    symbol = f"{fam.symbol(n_str)}({q_str})"
    alt = ""
    if show_alt and n is not None and q is not None:
        alt = _alt_line(alt_descriptions(fam.key, n if fam.ranked else 0, q))

    if concrete:
        rank_key = n if fam.ranked else 0
        if (fam.key, rank_key, q) in NOT_SIMPLE_EMPTY:
            return None
        if (fam.key, rank_key, q) == TITS:
            return Cell(symbol=f"{sup(2)}F{sub(4)}(2)′", alt="Tits group",
                        order=factorisation_markup(arith.factor(17971200)),
                        category=EXCEPTIONAL_TWISTED, note="derived subgroup")
        # a group that is not simple here, or that is isomorphic to one
        # printed elsewhere, leaves the cell empty: see HOLE_KEY
        if (fam.key, rank_key, q) in DERIVED or fam.not_simple(rank_key, q):
            return None
        if duplicate_of(fam.key, rank_key, q) is not None:
            return None

    return Cell(symbol=symbol, alt=alt,
                order=lie_order_markup(fam, n, q),
                order_alt=lie_order_formula(fam, n, q) if concrete else "",
                category=fam.category, generic=not concrete)


def cyclic_cell(q, show_alt: bool = True) -> Cell | None:
    """The cyclic column: C_p, the cyclic group of prime order p.

    C with a subscript and no argument is the cyclic group;  C_n(q), with a
    field, is the symplectic family.  The two are told apart by the argument,
    and they never share a column.
    """
    if q is None:
        return Cell(symbol=f"C{sub('p')}", alt="p prime" if show_alt else "",
                    order="p", category=CYCLIC, generic=True)
    if not arith.is_prime(q):
        return None
    alt = _alt_line([f"A{sub(2)}(1)"]) if (show_alt and q == 3) else ""
    return Cell(symbol=f"C{sub(q)}", alt=alt, order=str(q), category=CYCLIC)


def alternating_cell(n, show_alt: bool = True) -> Cell:
    if n is None:
        return Cell(symbol=f"A{sub('n')}", order="n! / 2",
                    category=ALTERNATING, generic=True)
    fac = arith.factor_factorial(n)
    arith.merge(fac, {2: 1}, sign=-1)
    return Cell(symbol=_alt(n), order=factorisation_markup(fac),
                category=ALTERNATING)


# --------------------------------------------------------------------------
# sporadic groups
# --------------------------------------------------------------------------

SPORADIC_GROUPS: list[tuple[str, str, int]] = [
    ("M<sub>11</sub>", "Mathieu", 7920),
    ("M<sub>12</sub>", "Mathieu", 95040),
    ("M<sub>22</sub>", "Mathieu", 443520),
    ("M<sub>23</sub>", "Mathieu", 10200960),
    ("M<sub>24</sub>", "Mathieu", 244823040),
    ("J<sub>1</sub>", "Janko", 175560),
    ("J<sub>2</sub>", "Hall–Janko", 604800),
    ("J<sub>3</sub>", "Janko", 50232960),
    ("J<sub>4</sub>", "Janko", 86775571046077562880),
    ("HS", "Higman–Sims", 44352000),
    ("McL", "McLaughlin", 898128000),
    ("He", "Held", 4030387200),
    ("Ru", "Rudvalis", 145926144000),
    ("Suz", "Suzuki", 448345497600),
    ("O′N", "O’Nan", 460815505920),
    ("Co<sub>1</sub>", "Conway", 4157776806543360000),
    ("Co<sub>2</sub>", "Conway", 42305421312000),
    ("Co<sub>3</sub>", "Conway", 495766656000),
    ("Fi<sub>22</sub>", "Fischer", 64561751654400),
    ("Fi<sub>23</sub>", "Fischer", 4089470473293004800),
    ("Fi<sub>24</sub>′", "Fischer", 1255205709190661721292800),
    ("HN", "Harada–Norton", 273030912000000),
    ("Ly", "Lyons", 51765179004000000),
    ("Th", "Thompson", 90745943887872000),
    ("B", "Baby Monster", 4154781481226426191177580544000000),
    ("M", "Monster", 808017424794512875886459904961710757005754368000000000),
]


def sporadic_cells(show_alt: bool = True) -> list[Cell]:
    return [
        Cell(symbol=sym, alt=(name if show_alt else ""),
             order=factorisation_markup(arith.factor(order)), category=SPORADIC)
        for sym, name, order in SPORADIC_GROUPS
    ]
