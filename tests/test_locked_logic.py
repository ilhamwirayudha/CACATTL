"""
Regression Test — Locked Core Logic Verification
CACA — Dashboard Analisis Dual Cycle & Twinlift (Terminal Teluk Lamong)

Script ini memverifikasi bahwa seluruh logika inti yang dikunci di AGENTS.md
menghasilkan angka patokan (golden output) yang 100% identik tanpa pergeseran.

Cara menjalankan:
    python tests/test_locked_logic.py
"""

from __future__ import annotations

import pathlib
import sys
import unittest

import pandas as pd

# Pastikan root proyek ada di sys.path agar modul dapat diimpor dari mana saja
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.calculations import (  # noqa: E402
    AMBANG_COMBO_MENIT_DEFAULT,
    AMBANG_DUAL_MENIT_DEFAULT,
    AMBANG_TWINLIFT_MENIT_DEFAULT,
    CRANE_INTERNASIONAL_SUFFIX,
    SIZE_ELIGIBLE,
    bersihkan_ves_id,
    klasifikasi_activity,
    proses_analisis_lengkap,
    vba_val,
)
from modules.data_loader import baca_file  # noqa: E402
from modules.ui import (  # noqa: E402
    prepare_combo_table,
    prepare_dual_cycle_table,
    prepare_non_dual_table,
    prepare_potential_combo_table,
    prepare_potential_dual_table,
    prepare_single_table,
    prepare_twinlift_table,
)

SAMPLE_FILE = PROJECT_ROOT / "contoh file excel" / "Dual Cycle Truck 701.xlsx"
SAMPLE_COL_MAP = {
    "ves_id": "VES_ID",
    "size": "CTR_SIZE",
    "truck": "CAR_CHE_ID",
    "activity": "ACTIVITY",
    "ts_g": "DISC_LOAD_TS",
    "ts_h": "STACK_UNSTACK_TS",
    "crane": "CHE_ID",
    "ctr_no": "CTR_NO",
}

# Angka patokan (Golden Output) yang dikunci pada AGENTS.md
GOLDEN_SUMMARY_INT = {
    "container_total": 6700,
    "container_disc": 2915,
    "container_load": 3785,
    "total_20ft": 5428,
    "total_bukan_20ft": 1272,
    "total_event": 4119,
    "total_dual": 2062,
    "total_single": 2057,
    "dual_disc": 1721,
    "dual_load": 1664,
    "single_disc": 1194,
    "single_load": 2121,
    "total_combo": 2581,
    "combo_20ft": 5162,
    "single_20ft": 266,
    "combo_dual": 1323,
    "combo_single": 1258,
    "single_dual": 739,
    "single_single": 799,
    "total_twinlift": 691,
    "total_twinlift_kontainer": 1382,
    "total_bukan_twinlift_kontainer": 4046,
    "total_combo_bukan_twinlift": 1890,
    "combo_bukan_twinlift_kontainer": 3780,
    "total_non_twinlift": 3428,
}

GOLDEN_SUMMARY_FLOAT = {
    "pct_dual": 0.500606943432872,
    "pct_20ft_of_total": 0.8101492537313433,
    "pct_combo_20ft": 0.9509948415622698,
    "pct_single_20ft": 0.04900515843773029,
    "pct_twinlift_of_20ft": 0.2546057479734709,
    "pct_bukan_twinlift_of_20ft": 0.7453942520265291,
    "pct_twinlift_of_combo": 0.2677256877179388,
    "pct_twinlift_of_total": 0.16775916484583636,
}


class TestLockedCoreLogic(unittest.TestCase):
    """Pengujian regresi untuk seluruh logika inti yang dikunci di AGENTS.md."""

    @classmethod
    def setUpClass(cls) -> None:
        if not SAMPLE_FILE.exists():
            raise FileNotFoundError(
                f"File sampel patokan tidak ditemukan: {SAMPLE_FILE}"
            )
        sheets = baca_file(SAMPLE_FILE.read_bytes(), SAMPLE_FILE.name)
        first_sheet = next(iter(sheets.keys()))
        cls.raw = sheets[first_sheet]
        cls.out_df, cls.events, cls.summary = proses_analisis_lengkap(
            cls.raw,
            SAMPLE_COL_MAP,
            SIZE_ELIGIBLE,
            AMBANG_COMBO_MENIT_DEFAULT,
            AMBANG_DUAL_MENIT_DEFAULT,
            AMBANG_TWINLIFT_MENIT_DEFAULT,
        )

    def test_01_baca_file_hanya_menerima_xlsx(self) -> None:
        """Poin 18: baca_file wajib menolak format non-.xlsx."""
        with self.assertRaises(ValueError):
            baca_file(b"col1,col2\n1,2\n", "data.csv")
        with self.assertRaises(ValueError):
            baca_file(b"dummy", "legacy.xls")

    def test_02_preprocessing_helpers(self) -> None:
        """Poin 18: vba_val, klasifikasi_activity, bersihkan_ves_id."""
        self.assertEqual(vba_val("20FT"), 20.0)
        self.assertEqual(vba_val("40HC"), 40.0)
        self.assertEqual(vba_val(20), 20.0)
        self.assertEqual(vba_val(None), 0.0)

        self.assertEqual(klasifikasi_activity("LOADING"), "LOAD")
        self.assertEqual(klasifikasi_activity("load"), "LOAD")
        self.assertEqual(klasifikasi_activity("DISCHARGE"), "DISC")

        ves = bersihkan_ves_id(pd.Series(["  VES01 ", "", None]))
        self.assertEqual(ves.iloc[0], "VES01")
        self.assertTrue(pd.isna(ves.iloc[1]))
        self.assertTrue(pd.isna(ves.iloc[2]))

    def test_03_golden_summary_integers(self) -> None:
        """Poin 1-4 & 11: Seluruh angka KPI absolut harus cocok 100%."""
        for key, expected in GOLDEN_SUMMARY_INT.items():
            actual = self.summary[key]
            self.assertEqual(
                actual,
                expected,
                f"KPI '{key}' bergeser! Diharapkan {expected}, didapat {actual}.",
            )

    def test_04_golden_summary_percentages(self) -> None:
        """Poin 1-4 & 11: Seluruh rasio/persentase KPI harus cocok presisi."""
        for key, expected in GOLDEN_SUMMARY_FLOAT.items():
            actual = self.summary[key]
            self.assertAlmostEqual(
                actual,
                expected,
                places=9,
                msg=f"Persentase '{key}' bergeser! Diharapkan {expected}, didapat {actual}.",
            )

    def test_05_twinlift_only_international_cranes(self) -> None:
        """Poin 2: Crane domestik (tidak berakhiran 'I') tidak boleh pernah Twinlift."""
        tl_rows = self.out_df[self.out_df["TWINLIFT_STATUS"] == "Twinlift"]
        self.assertGreater(len(tl_rows), 0)
        cranes = tl_rows["CRANE_ID"].astype(str).str.upper()
        non_intl = cranes[~cranes.str.endswith(CRANE_INTERNASIONAL_SUFFIX)]
        self.assertEqual(
            len(non_intl),
            0,
            f"Ditemukan {len(non_intl)} baris Twinlift pada crane non-internasional!",
        )

    def test_06_modal_tables_golden_counts_and_columns(self) -> None:
        """Poin 5-9: Verifikasi jumlah baris, anomali, dan pembersihan kolom modal."""
        dual_tbl = prepare_dual_cycle_table(self.events, self.out_df)
        self.assertEqual(len(dual_tbl), 1031)
        self.assertEqual(int((dual_tbl["Anomali"] == "Anomali").sum()), 42)
        self.assertNotIn("Tipe DISC", dual_tbl.columns)
        self.assertNotIn("Tipe LOAD", dual_tbl.columns)

        non_dual_tbl = prepare_non_dual_table(self.events, self.out_df)
        self.assertEqual(len(non_dual_tbl), 2057)
        self.assertNotIn("Tipe Kontainer", non_dual_tbl.columns)

        combo_tbl = prepare_combo_table(
            self.out_df, self.events, AMBANG_COMBO_MENIT_DEFAULT
        )
        self.assertEqual(len(combo_tbl), 2581)

        single_tbl = prepare_single_table(self.out_df, self.events)
        self.assertEqual(len(single_tbl), 266)

        tl_tbl, non_tl_tbl = prepare_twinlift_table(self.out_df)
        self.assertEqual(len(tl_tbl), 691)
        self.assertEqual(len(non_tl_tbl), 2156)
        self.assertNotIn("Waktu Lapangan", tl_tbl.columns)

        pot_dual_tbl = prepare_potential_dual_table(
            self.events, self.out_df, ambang_dual=AMBANG_DUAL_MENIT_DEFAULT
        )
        self.assertEqual(len(pot_dual_tbl), 115)

        pot_combo_tbl = prepare_potential_combo_table(
            self.out_df, self.events, ambang_combo=AMBANG_COMBO_MENIT_DEFAULT
        )
        self.assertEqual(len(pot_combo_tbl), 105)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestLockedCoreLogic)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
