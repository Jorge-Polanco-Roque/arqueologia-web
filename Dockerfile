# Entorno aislado para el pipeline de Arqueología Web.
# Instala solo la capa NÚCLEO (ingesta + log-odds + DuckDB) -> imagen liviana.
# La capa ML (torch/bertopic) se añade cuando se construya la fase 4.
FROM python:3.12-slim

WORKDIR /app
COPY requirements-core.txt requirements-download.txt ./
RUN pip install --no-cache-dir -r requirements-core.txt -r requirements-download.txt

COPY arqueo/ arqueo/

# Por defecto: self-checks + smoke test end-to-end (este sí usa DuckDB).
CMD ["sh", "-c", "python -m arqueo.core && python -m arqueo.ingest && python -m arqueo.analyze && python -m arqueo.download_reddit && python -m arqueo.smoke"]
