# Validation results

Measured at: 2026-10-22T16:28:04.317124+00:00

Command: `uv run python tools/verify_pipeline.py --report docs/verification.json`

The verification created fresh temporary data and warehouses for each seed.
No numbers or snapshot IDs were copied from the reference repositories.

| Seed | dbt tests | Contract checks | Reference outputs | Re-runs | Historical snapshots |
|---|---:|---:|---|---|---|
| 2026 | 26/26 | 22/22 before and after | All 3 match before and after | Unchanged before and after | All 3 readable |
| 11 | 26/26 | 22/22 before and after | All 3 match before and after | Unchanged before and after | All 3 readable |

## Seed 2026

| Table | Rows before | Rows after | Snapshots before | Snapshots after |
|---|---:|---:|---:|---:|
| `silver.product_cost_history` | 633 | 637 | 1 | 2 |
| `gold.weekly_margin` | 165 | 165 | 1 | 2 |
| `quality.price_quarantine` | 7 | 7 | 1 | 1 |

| Total | Before correction | After correction |
|---|---:|---:|
| `revenue_sar` | 3,504,002.19 | 3,504,002.19 |
| `cost_sar` | 1,654,199.98 | 1,651,701.06 |
| `margin_sar` | 801,016.88 | 803,515.80 |
| `lines` | 82,404.00 | 82,404.00 |
| `uncosted_lines` | 20,626.00 | 20,626.00 |

## Seed 11

| Table | Rows before | Rows after | Snapshots before | Snapshots after |
|---|---:|---:|---:|---:|
| `silver.product_cost_history` | 632 | 636 | 1 | 2 |
| `gold.weekly_margin` | 165 | 165 | 1 | 2 |
| `quality.price_quarantine` | 7 | 7 | 1 | 1 |

| Total | Before correction | After correction |
|---|---:|---:|
| `revenue_sar` | 3,332,299.11 | 3,332,299.11 |
| `cost_sar` | 1,673,016.80 | 1,672,533.06 |
| `margin_sar` | 748,231.25 | 748,714.99 |
| `lines` | 83,195.00 | 83,195.00 |
| `uncosted_lines` | 18,175.00 | 18,175.00 |

## Regression tests

`uv run python -m unittest discover -s tests -v`: 3/3 passed.

- Empty supplier inputs retain the expected raw schema.
- Byte-order marks and renamed or extra columns preserve rows and provenance.
- Cost parsing handles decimal commas and Arabic-Indic digits while preserving raw whitespace.

The snapshot IDs in `verification.json` identify the actual verification runs.
The temporary warehouses were removed after checking; run the command again to
produce new snapshots. The default warehouse is created by `run.py`.
