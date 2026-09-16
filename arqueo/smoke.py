"""Smoke test end-to-end: sintético -> ingesta -> DuckDB -> compare.

Ejercita el camino que los self-checks por módulo NO cubren: la vista DuckDB
sobre el JSONL normalizado y `analyze.compare_eras` de punta a punta. Necesita
duckdb -> corre dentro del contenedor (`docker compose up`), no en el host pelado.

    python -m arqueo.smoke
"""
from __future__ import annotations
import json
import os
import tempfile

from . import core, ingest, analyze

# Vocabulario que separa los cortes de forma inequívoca (misma plataforma+comunidad).
_2012 = "the occupy protest and my blackberry flash player obama debate"
_2022 = "the tiktok trend and my crypto nft ukraine dodge inflation"


def _raw(subreddit, ts, body, i):
    return {"id": f"{ts}-{i}", "subreddit": subreddit, "author": "u",
            "created_utc": ts, "body": body}


def run():
    ts2012 = 1325376000   # 2012-01-01 UTC
    ts2022 = 1640995200   # 2022-01-01 UTC
    with tempfile.TemporaryDirectory() as d:
        raw_dir = os.path.join(d, "raw")
        norm_dir = os.path.join(d, "normalized", "reddit")
        os.makedirs(raw_dir)

        # 1. datos crudos con forma de dump, dos cortes
        for year, ts, text in ((2012, ts2012, _2012), (2022, ts2022, _2022)):
            p = os.path.join(raw_dir, f"politics_{year}.ndjson")
            with open(p, "w") as f:
                for i in range(40):
                    f.write(json.dumps(_raw("politics", ts + i, text, i)) + "\n")
            # 2. ingesta REAL -> JSONL normalizado
            n = core.write_jsonl(ingest.from_reddit_dump(p),
                                 os.path.join(norm_dir, f"politics_{year}.jsonl"))
            assert n == 40, n

        # 3. DuckDB sobre el JSONL + 4. comparación diacrónica
        con = core.db(os.path.join(d, "normalized", "**", "*.jsonl"))
        counts = dict(con.execute(
            "SELECT era, count(*) FROM corpus GROUP BY era").fetchall())
        assert counts == {"2012": 40, "2022": 40}, counts

        res = analyze.compare_eras(con, era_a="2012", era_b="2022",
                                   platform="reddit", community="politics", top=5)
        a = {w for w, _ in res["a_distinctive"]}   # propio de 2012
        b = {w for w, _ in res["b_distinctive"]}   # propio de 2022
        assert a & {"occupy", "blackberry", "obama", "flash", "protest"}, a
        assert b & {"tiktok", "crypto", "nft", "ukraine", "inflation"}, b
        assert not (a & b), a & b                   # sin fugas entre cortes

    print("smoke OK (ingesta -> DuckDB -> compare end-to-end)")


if __name__ == "__main__":
    run()
