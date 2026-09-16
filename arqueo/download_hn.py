"""Descarga Hacker News desde BigQuery (`hacker_news.full`) a NDJSON crudo.

Streamea el resultado de la query directo a disco (sin bucket GCS intermedio).
Requiere credenciales ADC de gcloud montadas y GOOGLE_CLOUD_PROJECT (ver
docker-compose.yml). Coste: 1 escaneo del dataset, dentro del TB/mes gratis.
La salida la ingiere `ingest.from_hn`.
"""
from __future__ import annotations
import json
import os

QUERY = """
SELECT id, `by`, `time`, text, title, parent, type
FROM `bigquery-public-data.hacker_news.full`
WHERE type IN ('comment', 'story')
  AND EXTRACT(YEAR FROM timestamp) IN UNNEST(@years)
"""


def download(years=(2012, 2022), out="data/raw/hn/hn.ndjson", project=None):
    from google.cloud import bigquery   # import perezoso: solo si se descarga HN
    os.makedirs(os.path.dirname(out), exist_ok=True)
    client = bigquery.Client(project=project or os.environ.get("GOOGLE_CLOUD_PROJECT"))
    job = client.query(QUERY, job_config=bigquery.QueryJobConfig(
        query_parameters=[bigquery.ArrayQueryParameter("years", "INT64", list(years))]))
    n = 0
    with open(out, "w", encoding="utf-8") as f:
        for row in job.result():                       # itera paginando, memoria acotada
            f.write(json.dumps(dict(row), default=str, ensure_ascii=False) + "\n")
            n += 1
    return n, out


if __name__ == "__main__":
    import sys
    yrs = tuple(int(y) for y in (sys.argv[1].split(",") if len(sys.argv) > 1 else ["2012", "2022"]))
    print(download(years=yrs))
