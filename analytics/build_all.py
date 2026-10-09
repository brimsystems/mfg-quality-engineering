"""Build every deliverable from the marts and the study worksheets: the three reports, the dashboard, the README with its dashboard image, and the index.

Usage: python -m analytics.build_all
"""
import subprocess
import sys

MODULES = ["analytics.reports.measurement_and_capability", "analytics.reports.root_cause_and_doe", "analytics.reports.supplier_and_cost_of_quality",
           "analytics.dashboard.build", "analytics.readme_image", "analytics.site"]


def main():
    for m in MODULES:
        print(m, flush=True)
        subprocess.run([sys.executable, "-m", m], check=True)


if __name__ == "__main__":
    main()
