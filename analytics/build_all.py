"""Build every deliverable from the marts and the study worksheets: the six reports, the three A3s, the dashboard, the README with its dashboard image, and the index.

Usage: python -m analytics.build_all
"""
import subprocess
import sys

MODULES = ["analytics.s1_msa.report", "analytics.s2_capability.report", "analytics.s3_root_cause.report", "analytics.s4_sampling.report", "analytics.s5_doe.report",
           "analytics.s6_cost_of_quality.report", "analytics.dashboard.build", "analytics.readme_image", "analytics.site"]


def main():
    for m in MODULES:
        print(m, flush=True)
        subprocess.run([sys.executable, "-m", m], check=True)


if __name__ == "__main__":
    main()
