"""Access to the marts and the study worksheets."""
import io
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "quality.duckdb"
STUDIES = ROOT / "data" / "raw" / "studies"


def query(sql):
    """Run a query against the marts; every query states its own order."""
    con = duckdb.connect(str(DB), read_only=True)
    try:
        return con.sql(sql).df()
    finally:
        con.close()


def worksheet(name):
    """A study worksheet as recorded: the header rows as a dictionary and the table below them."""
    text = (STUDIES / name).read_text(encoding="utf8")
    head, body = text.split("\n\n", 1)
    return dict(line.split(",", 1) for line in head.splitlines()), pd.read_csv(io.StringIO(body))
