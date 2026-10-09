"""Supplier quality and cost of quality: the report, from its two halves.

Usage: python -m analytics.reports.supplier_and_cost_of_quality
"""
from analytics.sampling import sections as first
from analytics.cost_of_quality import sections as second
from analytics.reports.combine import write


def build():
    return write("supplier", first, second, ("Acceptance sampling and supplier quality", "Cost of quality"), "[[S:second]] cover the cost of quality by category, its reconciliation to the source tables, and the cost attributable to the findings.")


if __name__ == "__main__":
    print(build())
