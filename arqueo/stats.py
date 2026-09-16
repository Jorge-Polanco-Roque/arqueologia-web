"""Tests estadísticos en Python puro (solo math). Sin dependencias.

- Proporciones (presencia / densidad por token): test z de dos proporciones,
  IC 95% de la diferencia y tamaño de efecto Cohen's h.
- Continuas (por comentario): Mann-Whitney U (aprox. normal con corrección por
  empates) + tamaño de efecto Cliff's delta.
- Corrección por comparaciones múltiples: Benjamini-Hochberg (FDR).

Con n grande casi todo da p<0.05: por eso el veredicto se decide por el TAMAÑO
DE EFECTO, no por p sola.
"""
from __future__ import annotations
import math
from collections import Counter


def _phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def two_sided_p(z):
    return 2 * (1 - _phi(abs(z)))


def cohens_h(p1, p2):
    return 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))


def two_proportion(x1, n1, x2, n2):
    """Grupo 1 vs 2. Devuelve dict con p1,p2,diff,IC95,z,p,h."""
    p1, p2 = x1 / n1, x2 / n2
    pool = (x1 + x2) / (n1 + n2)
    se_pool = math.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2)) or 1e-12
    z = (p1 - p2) / se_pool
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    diff = p2 - p1
    return {"p1": p1, "p2": p2, "diff": diff, "ci": (diff - 1.96 * se, diff + 1.96 * se),
            "z": z, "p": two_sided_p(z), "h": cohens_h(p2, p1)}


def _avg_ranks(vals):
    idx = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and vals[idx[j + 1]] == vals[idx[i]]:
            j += 1
        avg = (i + j) / 2 + 1  # rango medio, base 1
        for k in range(i, j + 1):
            ranks[idx[k]] = avg
        i = j + 1
    return ranks


def mann_whitney(a, b):
    """U de Mann-Whitney (grupo a vs b) con aprox. normal y corrección por empates.
    Devuelve dict con U1, z, p, cliff (Cliff's delta, a>b positivo)."""
    n1, n2 = len(a), len(b)
    N = n1 + n2
    vals = a + b
    ranks = _avg_ranks(vals)
    R1 = sum(ranks[:n1])
    U1 = R1 - n1 * (n1 + 1) / 2
    mu = n1 * n2 / 2
    ties = Counter(vals)
    tsum = sum(t ** 3 - t for t in ties.values())
    var = n1 * n2 / 12 * ((N + 1) - tsum / (N * (N - 1)))
    sigma = math.sqrt(var) or 1e-12
    z = (U1 - mu) / sigma
    cliff = 2 * U1 / (n1 * n2) - 1
    return {"U1": U1, "z": z, "p": two_sided_p(z), "cliff": cliff}


def bh_fdr(pvals):
    """Benjamini-Hochberg. Devuelve q-values en el orden original."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    q = [0.0] * m
    prev = 1.0
    for rank in range(m - 1, -1, -1):
        i = order[rank]
        val = min(prev, pvals[i] * m / (rank + 1))
        q[i] = val
        prev = val
    return q


def mag_h(h):
    h = abs(h)
    return "insignificante" if h < 0.2 else "pequeño" if h < 0.5 else "medio" if h < 0.8 else "grande"


def mag_delta(d):
    d = abs(d)
    return "insignificante" if d < 0.147 else "pequeño" if d < 0.33 else "medio" if d < 0.474 else "grande"


def _selfcheck():
    r = two_proportion(50, 100, 70, 100)          # dos proporciones distintas
    assert abs(r["z"]) > 2.8 and r["p"] < 0.01, r
    r2 = two_proportion(500, 1000, 505, 1000)      # casi iguales, n grande
    assert r2["p"] > 0.7 and mag_h(r2["h"]) == "insignificante", r2
    mw = mann_whitney([1, 2, 3, 4, 100], [5, 6, 7, 8, 9])
    assert -1 <= mw["cliff"] <= 1
    mw2 = mann_whitney(list(range(100)), list(range(50, 150)))
    assert mw2["cliff"] < 0 and mw2["p"] < 0.05          # a<b, detecta diferencia
    q = bh_fdr([0.001, 0.04, 0.5, 0.9])
    assert q[0] < q[1] < q[2] <= q[3] and all(qi >= p for qi, p in zip(q, [0.001, 0.04, 0.5, 0.9]))
    assert mag_delta(0.5) == "grande" and mag_h(0.0) == "insignificante"
    print("stats OK")


if __name__ == "__main__":
    _selfcheck()
