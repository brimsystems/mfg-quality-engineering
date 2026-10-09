"""Measurement systems and process capability: the report, from its two halves.

Usage: python -m analytics.reports.measurement_and_capability
"""
from analytics.msa import sections as first
from analytics.capability import sections as second
from analytics.reports.combine import write


def build():
    return write("measurement", first, second, ("Measurement system analysis", "Process capability"), "[[S:second]] cover the stability and capability of the study characteristics, restated on every subgroup.")


if __name__ == "__main__":
    print(build())
