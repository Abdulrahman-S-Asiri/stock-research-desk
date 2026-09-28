import math
import unittest

from analytics import analyze


def records(dates, closes):
    return [{"date": day, "close": close} for day, close in zip(dates, closes)]


class AnalyzeTests(unittest.TestCase):
    def test_hand_calculated_metrics_and_contract(self):
        dates = ["2026-01-01", "2026-01-02", "2026-01-05"]
        result = analyze({
            "ABC": records(dates, [100, 110, 99]),
            "SPY": records(dates, [100, 100, 100]),
        }, "SPY")

        self.assertEqual(set(result), {"dates", "benchmark", "rows", "warnings", "dropped_observations"})
        self.assertEqual(result["dates"], dates)
        self.assertEqual(result["benchmark"], "SPY")
        self.assertEqual(result["dropped_observations"], {"ABC": 0, "SPY": 0})
        self.assertEqual([row["symbol"] for row in result["rows"]], ["ABC", "SPY"])
        self.assertEqual(len(result["warnings"]), 1)
        self.assertIn("60 daily returns", result["warnings"][0])

        row = result["rows"][0]
        self.assertEqual(set(row), {
            "symbol", "total_return", "annualized_volatility", "max_drawdown",
            "excess_return", "observations", "first_date", "last_date",
            "normalized", "drawdown", "adjusted_close",
        })
        self.assertAlmostEqual(row["total_return"], -0.01)
        self.assertAlmostEqual(row["annualized_volatility"], math.sqrt(5.04))
        self.assertAlmostEqual(row["max_drawdown"], -0.1)
        self.assertAlmostEqual(row["excess_return"], -0.01)
        self.assertEqual(row["observations"], 3)
        self.assertEqual((row["first_date"], row["last_date"]), (dates[0], dates[-1]))
        self.assertEqual(row["normalized"], [100, 110.00000000000001, 99.0])
        self.assertEqual(row["drawdown"], [0, 0, -0.09999999999999998])
        self.assertEqual(row["adjusted_close"], 99)
        self.assertEqual(result["rows"][1]["annualized_volatility"], 0)
        self.assertEqual(result["rows"][1]["excess_return"], 0)

    def test_alignment_crops_later_listing_without_forward_fill(self):
        dates = ["2026-01-01", "2026-01-02", "2026-01-05", "2026-01-06", "2026-01-07"]
        result = analyze({
            "SPY": records(dates, [10, 11, 12, 13, 14]),
            "NEW": records(dates[1:4], [20, 22, 24]),
        }, "SPY")
        self.assertEqual(result["dates"], dates[1:4])
        self.assertEqual(result["dropped_observations"], {"SPY": 2, "NEW": 0})
        self.assertEqual(result["rows"][0]["adjusted_close"], 13)
        self.assertEqual(result["rows"][1]["normalized"], [100, 110.00000000000001, 120.0])
        self.assertTrue(any("SPY: 2 observation" in warning for warning in result["warnings"]))

    def test_unsorted_records_are_sorted(self):
        dates = ["2026-01-01", "2026-01-02", "2026-01-05"]
        rows = records(dates, [1, 2, 3])
        result = analyze({"SPY": list(reversed(rows))}, "SPY")
        self.assertEqual(result["dates"], dates)
        self.assertEqual(result["rows"][0]["total_return"], 2)

    def test_duplicate_invalid_or_nonfinite_close_rejected(self):
        dates = ["2026-01-01", "2026-01-02", "2026-01-05"]
        good = records(dates, [1, 2, 3])
        bad_cases = [
            good + [good[0]],
            records(dates, [1, 0, 3]),
            records(dates, [1, -2, 3]),
            records(dates, [1, math.nan, 3]),
            records(dates, [1, math.inf, 3]),
            records(["2026-01-01", "2026-02-30", "2026-03-01"], [1, 2, 3]),
            records(["2026-1-1", "2026-01-02", "2026-01-05"], [1, 2, 3]),
        ]
        for bad in bad_cases:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                analyze({"SPY": bad}, "SPY")

    def test_internal_missing_benchmark_session_rejected(self):
        dates = ["2026-01-01", "2026-01-02", "2026-01-05", "2026-01-06"]
        with self.assertRaisesRegex(ValueError, "missing benchmark session 2026-01-02"):
            analyze({
                "SPY": records(dates, [1, 2, 3, 4]),
                "ABC": records([dates[0], dates[2], dates[3]], [1, 2, 3]),
            }, "SPY")

    def test_at_least_three_common_dates_required(self):
        dates = ["2026-01-01", "2026-01-02", "2026-01-05"]
        with self.assertRaisesRegex(ValueError, "three common dates"):
            analyze({
                "SPY": records(dates, [1, 2, 3]),
                "NEW": records(dates[1:], [1, 2]),
            }, "SPY")


if __name__ == "__main__":
    unittest.main()
