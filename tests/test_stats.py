"""Independent arithmetic and edge-case checks for the assumption model."""
from pathlib import Path
import tempfile
import unittest
import warnings

from finance import stats
from data.validation.validate_mock_data import validate


class EconomicsTests(unittest.TestCase):
    def test_base_arithmetic(self) -> None:
        m = stats.calculate_metrics(stats.SCENARIOS["base"])
        for key, expected in {"arpu": 2.32, "variable_full": 1.05, "variable_modular": 0.51, "margin_modular": 1.81, "fixed": 70, "break_even_modular": 39, "break_even_full": 56, "token_saving": 0.6, "monthly_cost_saving": 162, "margin_difference": 0.54}.items():
            self.assertAlmostEqual(m[key], expected)

    def test_nonpositive_margin(self) -> None:
        for margin in (0, -1):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                self.assertIsNone(stats.calculate_break_even_users(100, margin))
                self.assertEqual(len(caught), 1)
                self.assertIn("无法达到盈亏平衡", str(caught[0].message))

    def test_zero_and_rounding(self) -> None:
        self.assertEqual(stats.calculate_token_cost(0, 15), 0)
        self.assertEqual(stats.calculate_token_cost(1_000_000, 15), 15)
        self.assertEqual(stats.calculate_token_saving_rate(0, 0), 0)
        self.assertEqual(stats.calculate_break_even_users(10, 3), 4)
        self.assertEqual(stats.calculate_break_even_users(0, 3), 0)

    def test_architecture_extremes(self) -> None:
        from dataclasses import replace
        s = stats.SCENARIOS["base"]
        self.assertEqual(stats.calculate_variable_cost_per_user(replace(s, module_replacement_ratio=0)), stats.calculate_variable_cost_per_user(s, "full"))
        self.assertAlmostEqual(stats.calculate_variable_cost_per_user(replace(s, module_replacement_ratio=1)), 0.15)
        with self.assertRaises(ValueError):
            replace(s, paid_conversion_rate=1.1)

    def test_report_and_scenarios(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            for s in stats.SCENARIOS.values():
                m = stats.calculate_metrics(s)
                self.assertAlmostEqual(m["monthly_cost_full"] - m["monthly_cost_modular"], m["monthly_cost_saving"])
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "report.md"
                report = stats.generate_report(path)
                self.assertEqual(report, path.read_text(encoding="utf-8"))
                self.assertIn("假设值，待验证", report)

    def test_mock_fixture(self) -> None:
        self.assertEqual(validate(Path(__file__).resolve().parents[1] / "data" / "mock" / "mock_db.json"), [])


if __name__ == "__main__":
    unittest.main()
