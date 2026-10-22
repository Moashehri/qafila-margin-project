"""Regression checks for supplier schema changes and preservation of raw values."""

import sys
import tempfile
import unittest
from pathlib import Path

import duckdb
from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run import _read_supplier_files  # noqa: E402


class SupplierIngestionTests(unittest.TestCase):
    def test_empty_supplier_input_has_a_usable_schema(self):
        table = _read_supplier_files([])
        self.assertEqual(table.num_rows, 0)
        self.assertTrue({"sku", "valid_from", "unit_cost", "cost_sar", "file_row"} <= set(table.column_names))

    def test_bom_and_changed_columns_preserve_all_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            first, second = Path(folder) / "first.csv", Path(folder) / "second.csv"
            first.write_text("\ufeffsku,valid_from,unit_cost\nQF-1,2026-08-31,9.49\n", encoding="utf-8")
            second.write_text("sku,valid_from,cost_sar,currency\nQF-1,2026-09-07,10.20,SAR\n", encoding="utf-8")
            rows = _read_supplier_files([first, second]).to_pylist()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["unit_cost"], "9.49")
        self.assertIsNone(rows[0]["cost_sar"])
        self.assertEqual(rows[1]["currency"], "SAR")
        self.assertEqual(rows[1]["source_file"], "second.csv")
        self.assertEqual(rows[1]["file_row"], 1)

    def test_parsing_keeps_the_original_cost_text(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "prices.csv"
            file.write_text('sku,valid_from,unit_cost\nQF-1,2026-08-31,  -1  \n'
                            'QF-2,2026-08-31,"9,49"\nQF-3,2026-08-31,٩٫٤٩\n', encoding="utf-8")
            table = _read_supplier_files([file])
        template = (ROOT / "dbt/models/staging/stg_supplier_prices.sql").read_text()
        sql = Environment().from_string(template).render(source=lambda schema, name: "incoming")
        with duckdb.connect() as connection:
            connection.register("incoming", table)
            rows = connection.sql(sql).to_arrow_table().to_pylist()
        self.assertEqual(rows[0]["raw_cost"], "  -1  ")
        self.assertEqual(rows[0]["unit_cost_sar"], -1)
        self.assertEqual(rows[1]["unit_cost_sar"], 9.49)
        self.assertEqual(rows[2]["unit_cost_sar"], 9.49)


if __name__ == "__main__":
    unittest.main()
