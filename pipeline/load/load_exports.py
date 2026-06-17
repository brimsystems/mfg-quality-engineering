"""Load the system exports under data/raw into DuckDB (schema raw), one table per export file.

Usage: python -m pipeline.load.load_exports
"""
from pathlib import Path

import dlt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "quality.duckdb"
SYSTEMS = ["erp", "qms", "cmm", "calibration", "accounting"]


def rows(path, chunk=50000):
    for df in pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""], chunksize=chunk):
        yield df.astype(object).where(df.notna(), None).to_dict("records")


def export_tables():
    """One resource per export file, named <system>__<table>. Columns load as text; staging casts them."""
    for system in SYSTEMS:
        for path in sorted((RAW / system).glob("*.csv")):
            name = f"{system}__{path.stem}"
            header = pd.read_csv(path, dtype=str, nrows=0).columns
            columns = {c: {"data_type": "text", "nullable": True} for c in header}
            yield dlt.resource(rows(path), name=name, write_disposition="replace", columns=columns)


def main():
    pipeline = dlt.pipeline(pipeline_name="quality_exports", destination=dlt.destinations.duckdb(str(DB)), dataset_name="raw")
    info = pipeline.run(list(export_tables()))
    print(info)


if __name__ == "__main__":
    main()
