"""Núcleo: esquema unificado (Record) + eras + almacén DuckDB.

Todo el toolkit depende del esquema de aquí. Una "unidad de análisis" es un
mensaje/post individual normalizado, venga de Usenet, Reddit o donde sea.
Formato en disco: JSONL (stdlib, sin deps para escribir). DuckDB lo lee por glob.
"""
from __future__ import annotations
import json, re, os
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone

# Cortes "testigo de sondeo": capas de sedimento donde el dato existe.
# 2007 = pasado profundo (Usenet/Giganews; 1992 y 2002 caen en costuras de archivo
# sin bulk comparable). 2012/2022 = Reddit/HN (within-platform limpio).
SNAPSHOTS = (2007, 2012, 2022)
ERAS = {str(y): (y, y) for y in SNAPSHOTS}


def era_of(ts) -> str | None:
    """Etiqueta del corte ('1992'..'2022') o None si el año no es un corte."""
    y = ts.year if isinstance(ts, datetime) else datetime.fromtimestamp(int(ts), tz=timezone.utc).year
    for name, (lo, hi) in ERAS.items():
        if lo <= y <= hi:
            return name
    return None


_WS = re.compile(r"\s+")
_QUOTE = re.compile(r"^\s*>.*$", re.M)    # líneas citadas (Usenet/email/reddit)
_SIG = re.compile(r"\n-- \n.*$", re.S)    # firma estándar de Usenet


def clean_text(text: str, strip_quotes: bool = True) -> str:
    if not text:
        return ""
    text = _SIG.sub("", text)
    if strip_quotes:
        text = _QUOTE.sub("", text)
    return _WS.sub(" ", text).strip()


@dataclass
class Record:
    id: str
    platform: str            # 'usenet' | 'reddit' | 'hn' | 'web' | ...
    community: str           # newsgroup / subreddit / dominio
    author: str              # seudónimo; hashéalo antes de publicar datos
    ts: int                  # epoch UTC
    text: str
    lang: str = "en"
    parent_id: str | None = None
    url: str | None = None
    era: str | None = field(default=None)

    def __post_init__(self):
        self.text = clean_text(self.text)
        if self.era is None:
            self.era = era_of(self.ts)


def write_jsonl(records, path) -> int:
    """Escribe Records a JSONL. Descarta los que caen fuera de las eras."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            d = asdict(r) if isinstance(r, Record) else r
            if d.get("era") is None or not d.get("text"):
                continue
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
            n += 1
    return n


NORMALIZED_GLOB = "data/normalized/**/*.jsonl"


def db(glob_pattern: str = NORMALIZED_GLOB):
    """Conexión DuckDB con vista 'corpus' sobre todo el JSONL normalizado."""
    import duckdb
    con = duckdb.connect()
    con.execute(
        f"CREATE VIEW corpus AS "
        f"SELECT * FROM read_json_auto('{glob_pattern}', union_by_name=true)"
    )
    return con


def to_parquet(glob_pattern: str = NORMALIZED_GLOB, out: str = "data/corpus.parquet"):
    # ponytail: JSONL basta a escala de portátil; pasa a Parquet si el escaneo duele.
    import duckdb
    duckdb.connect().execute(
        f"COPY (SELECT * FROM read_json_auto('{glob_pattern}', union_by_name=true)) "
        f"TO '{out}' (FORMAT parquet)"
    )


def _selfcheck():
    assert era_of(datetime(2007, 6, 1, tzinfo=timezone.utc)) == "2007"
    assert era_of(datetime(2022, 6, 1, tzinfo=timezone.utc)) == "2022"
    assert era_of(datetime(2003, 6, 1, tzinfo=timezone.utc)) is None
    ts = int(datetime(2007, 6, 1, tzinfo=timezone.utc).timestamp())
    r = Record(id="1", platform="usenet", community="comp.lang.c", author="bob",
               ts=ts, text="hi\n> quoted line\nthere\n-- \nsig")
    assert r.era == "2007", r.era
    assert r.text == "hi there", repr(r.text)
    print("core OK")


if __name__ == "__main__":
    _selfcheck()
