"""Root cause and designed experiment: the report, from its two halves.

Usage: python -m analytics.reports.root_cause_and_doe
"""
from analytics.root_cause import sections as first
from analytics.doe import sections as second
from analytics.reports.combine import write


def build():
    return write("root_cause", first, second, ("Root cause of scrap on family F-14", "Designed experiment on surface finish"), "[[S:second]] cover the designed experiment on surface finish and production since the change of settings.")


if __name__ == "__main__":
    print(build())
