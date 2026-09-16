"""Descarga Reddit desde la API de Arctic Shift (HTTP sin auth) -> NDJSON crudo.

Pagina por subreddit y año avanzando `after` sobre created_utc (la API no da
cursor). Cortés con el rate limit dinámico (429 -> espera X-RateLimit-Reset).
Usa solo stdlib (urllib) -> sin dependencia extra. La salida tiene la misma
forma que los dumps -> la ingiere `ingest.from_reddit_dump`.

`max_items` acota la descarga: doble uso como TOPE y como muestra por celda
(útil para equilibrar 2012 vs 2022; ver PLAN.md fase 2). Para años enormes sin
tope, prefiere el dump completo del download-tool.
"""
from __future__ import annotations
import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone

API = "https://arctic-shift.photon-reddit.com/api"

# La API devuelve ~90 campos por registro; pedimos solo lo que usa el ingester
# -> disco ~4x menor y descarga más rápida.
FIELDS = {
    "comments": "id,author,subreddit,created_utc,body,parent_id,link_id",
    "posts": "id,author,subreddit,created_utc,title,selftext,permalink,url",
}


def _year_bounds(year: int):
    lo = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp())
    hi = int(datetime(year + 1, 1, 1, tzinfo=timezone.utc).timestamp())
    return lo, hi


def _month_bounds(year: int, month: int):
    lo = int(datetime(year, month, 1, tzinfo=timezone.utc).timestamp())
    ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
    hi = int(datetime(ny, nm, 1, tzinfo=timezone.utc).timestamp())
    return lo, hi


def _next_after(batch):
    # avanza un segundo más allá del último created_utc (orden asc).
    # ponytail: puede perder ítems que compartan ese segundo exacto; irrelevante
    # salvo picos >1000 msg/seg en un sub, que no es el caso de subs medios.
    return int(batch[-1]["created_utc"]) + 1


def _fetch(kind, subreddit, after, before, limit="auto"):
    params = urllib.parse.urlencode({
        "subreddit": subreddit, "after": after, "before": before,
        "limit": limit, "sort": "asc", "fields": FIELDS[kind],
    })
    url = f"{API}/{kind}/search?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "arqueo-web/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    return payload["data"] if isinstance(payload, dict) and "data" in payload else payload


def _window(kind, subreddit, after, before, max_items=None, sleep=1.0):
    """Pagina una ventana [after, before) avanzando el cursor. Genera dicts crudos."""
    seen = 0
    while True:
        try:
            batch = _fetch(kind, subreddit, after, before)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get("X-RateLimit-Reset", "30") or 30)
                time.sleep(min(wait, 120))
                continue
            raise
        if not batch:
            break
        for obj in batch:
            yield obj
            seen += 1
        if max_items and seen >= max_items:
            break
        nxt = _next_after(batch)
        if nxt <= after or nxt >= before:     # sin avance o fuera de ventana -> fin
            break
        after = nxt
        time.sleep(sleep)


def download(kind, subreddit, year, max_items=None, sleep=1.0):
    """Ventana del año completo (sesga al inicio del año si se capa con max_items)."""
    lo, hi = _year_bounds(year)
    yield from _window(kind, subreddit, lo, hi, max_items, sleep)


def download_stratified(kind, subreddit, year, per_month, sleep=1.0):
    """Muestra REPRESENTATIVA: per_month por cada mes -> cubre los 12, sin sesgo temporal."""
    for m in range(1, 13):
        lo, hi = _month_bounds(year, m)
        yield from _window(kind, subreddit, lo, hi, per_month, sleep)


def to_file(subreddit, year, kind="comments", out=None, max_items=None, per_month=None):
    out = out or f"data/raw/reddit/{subreddit}_{year}_{kind}.ndjson"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    gen = (download_stratified(kind, subreddit, year, per_month) if per_month
           else download(kind, subreddit, year, max_items=max_items))
    n = 0
    with open(out, "w", encoding="utf-8") as f:
        for obj in gen:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            n += 1
    return n, out


def _selfcheck():
    lo, hi = _year_bounds(2012)
    assert lo == 1325376000 and hi == 1356998400, (lo, hi)   # 2012-01-01 .. 2013-01-01 UTC
    m1, m2 = _month_bounds(2012, 1), _month_bounds(2012, 12)
    assert m1[0] == 1325376000 and m2[1] == 1356998400, (m1, m2)  # ene arranca año, dic cierra año
    assert _next_after([{"created_utc": 100}, {"created_utc": 205}]) == 206
    assert _next_after([{"created_utc": "300"}]) == 301       # la API puede dar string
    print("download_reddit OK")


if __name__ == "__main__":
    _selfcheck()
