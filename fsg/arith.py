"""Integer arithmetic helpers: primality, factorisation, cyclotomic splitting.

Orders of groups of Lie type are products of a prime power ``q**N`` with
factors ``q**k - 1`` and ``q**k + 1``.  Factoring such a number directly is
hopeless once ``k`` is large, but

    q**k - 1 = prod_{e | k} Phi_e(q)

and each cyclotomic value ``Phi_e(q)`` has only ``phi(e)`` digits-worth of
size, so it factors instantly.  Everything in this module is built around
that observation.
"""

from __future__ import annotations

import random
from functools import lru_cache
from math import gcd

# --------------------------------------------------------------------------
# primality / factorisation
# --------------------------------------------------------------------------

_SMALL_PRIMES = [
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67,
    71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149,
    151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229,
    233, 239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293,
]


def is_prime(n: int) -> bool:
    """Deterministic Miller-Rabin (the witness set is proven for n < 3.3e24)."""
    if n < 2:
        return False
    for p in _SMALL_PRIMES:
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def _pollard_rho(n: int) -> int:
    """Return a non-trivial divisor of composite ``n``."""
    if n % 2 == 0:
        return 2
    while True:
        c = random.randrange(1, n)
        f = lambda x: (x * x + c) % n
        x = y = random.randrange(0, n)
        d = 1
        while d == 1:
            x = f(x)
            y = f(f(y))
            d = gcd(abs(x - y), n)
        if d != n:
            return d


def factor(n: int) -> dict[int, int]:
    """Prime factorisation of ``n >= 1`` as ``{prime: exponent}``."""
    if n < 1:
        raise ValueError(f"factor() needs a positive integer, got {n}")
    out: dict[int, int] = {}
    for p in _SMALL_PRIMES:
        while n % p == 0:
            out[p] = out.get(p, 0) + 1
            n //= p
    stack = [n] if n > 1 else []
    while stack:
        m = stack.pop()
        if m == 1:
            continue
        if is_prime(m):
            out[m] = out.get(m, 0) + 1
            continue
        d = _pollard_rho(m)
        stack.append(d)
        stack.append(m // d)
    return dict(sorted(out.items()))


def merge(dst: dict[int, int], src: dict[int, int], sign: int = 1) -> dict[int, int]:
    """Multiply (``sign=1``) or divide (``sign=-1``) factorisation ``dst`` by ``src``."""
    for p, e in src.items():
        new = dst.get(p, 0) + sign * e
        if new:
            dst[p] = new
        else:
            dst.pop(p, None)
    return dst


def value(fac: dict[int, int]) -> int:
    """Rebuild the integer from a factorisation (used by the self-check)."""
    out = 1
    for p, e in fac.items():
        out *= p ** e
    return out


# --------------------------------------------------------------------------
# cyclotomic splitting
# --------------------------------------------------------------------------

def divisors(n: int) -> list[int]:
    return [d for d in range(1, n + 1) if n % d == 0]


@lru_cache(maxsize=None)
def cyclotomic_value(e: int, q: int) -> int:
    """``Phi_e(q)``, computed from ``q**e - 1 = prod_{d | e} Phi_d(q)``."""
    num = q ** e - 1
    for d in divisors(e)[:-1]:
        num //= cyclotomic_value(d, q)
    return num


@lru_cache(maxsize=None)
def factor_q_pow_minus_1(q: int, k: int) -> tuple[tuple[int, int], ...]:
    """Factorisation of ``q**k - 1`` via its cyclotomic factors."""
    out: dict[int, int] = {}
    for e in divisors(k):
        merge(out, factor(cyclotomic_value(e, q)))
    return tuple(sorted(out.items()))


def factor_binom(q: int, k: int, sign: int) -> dict[int, int]:
    """Factorisation of ``q**k - 1`` (``sign=-1``) or ``q**k + 1`` (``sign=+1``)."""
    if sign < 0:
        return dict(factor_q_pow_minus_1(q, k))
    # q**k + 1 = (q**(2k) - 1) / (q**k - 1)
    out = dict(factor_q_pow_minus_1(q, 2 * k))
    merge(out, dict(factor_q_pow_minus_1(q, k)), sign=-1)
    return out


def factor_factorial(n: int) -> dict[int, int]:
    """Factorisation of ``n!`` by Legendre's formula."""
    out: dict[int, int] = {}
    for p in range(2, n + 1):
        if not is_prime(p):
            continue
        e, pk = 0, p
        while pk <= n:
            e += n // pk
            pk *= p
        out[p] = e
    return out


# --------------------------------------------------------------------------
# prime powers
# --------------------------------------------------------------------------

def prime_power(q: int) -> tuple[int, int] | None:
    """Return ``(p, a)`` with ``q = p**a``, ``a >= 1``, or ``None``."""
    fac = factor(q) if q > 1 else {}
    if len(fac) != 1:
        return None
    (p, a), = fac.items()
    return p, a


def prime_powers_up_to(limit: int) -> list[int]:
    return [q for q in range(2, limit + 1) if prime_power(q) is not None]


def primes_up_to(limit: int) -> list[int]:
    return [p for p in range(2, limit + 1) if is_prime(p)]
