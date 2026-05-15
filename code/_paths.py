"""Common path resolution for NameRank analysis scripts.

All scripts in this directory read inputs from ../data/ and write outputs back
to ../data/analysis/ (overwriting the released CSVs) so that the public repo
is self-contained.

If you re-run the full English probe (code/run_probe.py), the record-level
output lands in ../data/raw/pilot_summary_en.csv and the gzipped form is
recreated by gzip after the fact. The analysis scripts read whichever variant
exists, transparently.
"""
from __future__ import annotations

import gzip
import io
import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
INPUTS = DATA / "inputs"
ANALYSIS = DATA / "analysis"
RAW = DATA / "raw"


def open_text(path: Path):
    """Open a text file, transparently un-gzipping if the path ends with .gz."""
    p = Path(path)
    if p.suffix == ".gz":
        if p.exists():
            return io.TextIOWrapper(gzip.open(p, "rb"), encoding="utf-8")
    if p.exists():
        return open(p, "r", encoding="utf-8")
    gz = p.with_suffix(p.suffix + ".gz")
    if gz.exists():
        return io.TextIOWrapper(gzip.open(gz, "rb"), encoding="utf-8")
    raise FileNotFoundError(f"neither {p} nor {gz} exists")


def raw_records_path(lang: str = "en") -> Path:
    """Path to the record-level pilot_summary CSV for the chosen language."""
    plain = RAW / f"pilot_summary_{lang}.csv"
    if plain.exists():
        return plain
    return RAW / f"pilot_summary_{lang}.csv.gz"
