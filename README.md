# Quality engineering studies for a precision machining shop

Precision machining shop, about 150 employees, IATF 16949 and AS9100, one plant.  
Six quality engineering studies and a quality dashboard on the shop's records from January 2024 to December 2025.

## Studies

| Study | Question | Finding | PPAP or AS9102 element | Deliverable |
|---|---|---|---|---|
| S1. Measurement system analysis | How much of the tolerance on the critical bore do the gauges consume? | The bore gauge consumes 34.0% of tolerance (ndc 2) and the air gauge 7.2% (ndc 10); 30% of the apparent process variation on the bore in 2025 was measurement; the production history gives an operator sd of 0.0031 mm over 8 machinists against the study's 0.0024; bore-gauge bias against the CMM on 703 matched pieces is 0.0006 mm (0.0004 to 0.0009). | PPAP element 7, measurement system analysis studies; AS9102 supporting data | [report](docs/reports/s1_msa.html) |
| S2. Process capability | Are the characteristics the shop reports as capable capable? | Of 49 critical characteristics the shop reports as capable, 9 are not when the calculation uses the pooled within-subgroup standard deviation, the fitted distribution for bounded characteristics and all 2025 subgroups; 2 of 6 reported as marginal are capable; the reported values carry a sampling interval of ±0.20 to ±0.38 at 25 subgroups and 14 of the capable calls lie inside it; the medical bore gives Cpk 2.21 on the shop's 25 readings, 1.89 on the year's subgroups and 1.82 on every piece. | PPAP element 10, initial process studies; AS9102 Form 3 supporting data | [report](docs/reports/s2_capability.html) |
| S3. Root cause of scrap on family F-14 | What drives scrap on family F-14? | MT-04 accounted for 43% of scrap on the family; controlling for bar-lot hardness and insert grade the machine effect is not significant (p = 0.74); hardness above 32 HRC with the standard insert explains 69.4% of the between-lot scrap variance; the insert change cut the family's scrap rate from 3.55% to 0.87% on the next 25 lots (p < 0.001) and 0.92% on all 36 since, with the control family unchanged. | Corrective action record; DMAIC project with A3 | [report](docs/reports/s3_root_cause.html), [A3](docs/a3/s3_root_cause.html) |
| S4. Acceptance sampling and supplier quality | What does the receiving plan protect against, and which suppliers run above 1%? | The c=0 plan gives the same consumer protection at the LTPD as the current plan (6.6% against 6.5% on lots of 501 to 1,200) at 38% of the sample pieces and rejects 71 of 195 S-017 lots over 24 months against the current plan's 26; the Z1.4 switching rules, never applied in the record, would have moved 47 of 60 suppliers to reduced inspection and saved 2,322 receiving hours; evaluated on S-017's lot history the current plan accepts 47% of lots above 2.5% defective and the c=0 plan 29%; 4 of 60 suppliers have defect-rate intervals lying entirely above 1%; 2 of the five worst suppliers on the published scorecard have fewer than five lots. | PPAP element 15 supporting data for purchased product; supplier control | [report](docs/reports/s4_sampling.html) |
| S5. Designed experiment on surface finish | Which settings bring the surface finish inside its limit? | Feed and insert nose radius interact (effect -0.405 µm, p < 0.001); at 0.8 mm radius the feed effect reverses (+0.59 µm at 0.4 mm, -0.22 µm at 0.8 mm); the chosen settings reduce Ra from 1.40 to 0.76 µm, confirmed on four runs inside the prediction interval (0.61 to 0.91); the next 11 production lots hold 0.70 µm. | PPAP element 11 supporting data; DMAIC project with A3 | [report](docs/reports/s5_doe.html), [A3](docs/a3/s5_doe.html) |
| S6. Cost of quality | What does quality cost beyond the scrap report? | Cost of quality is 7.3% of 2025 revenue as booked and 7.8% with rework left on production jobs estimated; failure costs are 3.35 times the scrap report as booked; prevention is 6.1% of the booked total; the non-capable length, the F-14 scrap and the plating escapes account for 6.5% of failure cost. | Management summary; DMAIC project with A3 | [report](docs/reports/s6_cost_of_quality.html), [A3](docs/a3/s6_cost_of_quality.html) |

Dashboard: [docs/dashboard/index.html](docs/dashboard/index.html). Index of deliverables: [docs/index.html](docs/index.html).

Every figure in the studies is computed on all records in the period: 2,451 lots, 123,996 subgroups of five and 63,872 single-piece records (683,852 readings), 22,381 CMM reports, 4,704 receiving lots, January 2024 to December 2025; the gauge, attribute and designed-experiment studies are the shop's worksheets as recorded.

## Customer package mapping

| Study | PPAP or AS9102 element | Deliverable |
|---|---|---|
| S1. Measurement system analysis | PPAP element 7, measurement system analysis studies; AS9102 supporting data | [report](docs/reports/s1_msa.html) |
| S2. Process capability | PPAP element 10, initial process studies; AS9102 Form 3 supporting data | [report](docs/reports/s2_capability.html) |
| S3. Root cause of scrap on family F-14 | Corrective action record; DMAIC project with A3 | [report](docs/reports/s3_root_cause.html), [A3](docs/a3/s3_root_cause.html) |
| S4. Acceptance sampling and supplier quality | PPAP element 15 supporting data for purchased product; supplier control | [report](docs/reports/s4_sampling.html) |
| S5. Designed experiment on surface finish | PPAP element 11 supporting data; DMAIC project with A3 | [report](docs/reports/s5_doe.html), [A3](docs/a3/s5_doe.html) |
| S6. Cost of quality | Management summary; DMAIC project with A3 | [report](docs/reports/s6_cost_of_quality.html), [A3](docs/a3/s6_cost_of_quality.html) |

## Data sources

Export batch 20260106T061500Z-QE24M.

| System | Export | Grain | Records |
|---|---|---|---|
| ERP | data/raw/erp/customers.csv | customer | 45 |
| ERP | data/raw/erp/employees.csv | employee | 70 |
| ERP | data/raw/erp/jobs.csv | lot | 2,451 |
| ERP | data/raw/erp/machines.csv | machine | 24 |
| ERP | data/raw/erp/material_certs.csv | bar lot | 1,119 |
| ERP | data/raw/erp/parts.csv | part | 600 |
| ERP | data/raw/erp/routings.csv | part and operation | 2,841 |
| ERP | data/raw/erp/scrap_transactions.csv | scrap transaction | 4,303 |
| QMS with SPC module | data/raw/qms/audit_findings.csv | audit finding | 90 |
| QMS with SPC module | data/raw/qms/capa.csv | corrective action | 60 |
| QMS with SPC module | data/raw/qms/capability_reports.csv | capability report | 877 |
| QMS with SPC module | data/raw/qms/characteristics.csv | part and characteristic | 2,400 |
| QMS with SPC module | data/raw/qms/complaints.csv | complaint | 80 |
| QMS with SPC module | data/raw/qms/final_inspection.csv | lot | 2,424 |
| QMS with SPC module | data/raw/qms/ncrs.csv | nonconformance | 709 |
| QMS with SPC module | data/raw/qms/receiving_inspection.csv | receiving lot | 4,704 |
| QMS with SPC module | data/raw/qms/spc_subgroups.csv | subgroup | 187,868 |
| QMS with SPC module | data/raw/qms/suppliers.csv | supplier | 60 |
| CMM and vision software | data/raw/cmm/cmm_features.csv | report and feature | 276,862 |
| CMM and vision software | data/raw/cmm/cmm_reports.csv | CMM report | 22,381 |
| Calibration system | data/raw/calibration/calibrations.csv | calibration event | 1,361 |
| Calibration system | data/raw/calibration/gauges.csv | gauge | 300 |
| Accounting | data/raw/accounting/cost_of_quality_lines.csv | cost line | 2,037 |
| Accounting | data/raw/accounting/labor_rates.csv | role and year | 8 |
| Study worksheets | data/raw/studies/attribute_agreement_cosmetic.csv | inspector, part and trial | 300 |
| Study worksheets | data/raw/studies/doe_surface_finish.csv | run | 20 |
| Study worksheets | data/raw/studies/gauge_rr_air_gauge.csv | operator, part and trial | 90 |
| Study worksheets | data/raw/studies/gauge_rr_bore_gauge.csv | operator, part and trial | 90 |

## Pipeline

`pipeline/load` loads the CSV exports under `data/raw` into DuckDB with dlt, one table per file. The dbt project under `pipeline/dbt` builds the staging models (one per export, typed), the intermediate models (the process history of each characteristic with lot, machine, operator, gauge, bar lot and calibration status; the CMM feature mapping and the serial match; lot outcomes; receiving outcomes with the Z1.4 table values; cost lines with their source records) and the marts, with schema tests on keys, ranges and relationships in every layer. The scripts under `analytics/` read the marts and the study worksheets under `data/raw/studies` and write each study's report, A3 and figures under `docs/`, the dashboard and this file.

## How to run

Python 3.12 or later, from a clean clone:

```
python -m venv .venv
.venv\Scripts\activate            # Windows; on Linux or macOS: source .venv/bin/activate
pip install -e .
python -m pipeline.load.load_exports
cd pipeline/dbt
dbt build --profiles-dir .
cd ../..
python -m analytics.build_all
```
