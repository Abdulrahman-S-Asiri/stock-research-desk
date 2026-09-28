import unittest
from analytics import analyze


class BenchmarkGapTests(unittest.TestCase):
    def test_benchmark_gap_visible_in_stock_is_rejected(self):
        benchmark = [{"date": f"2026-01-{day:02}", "close": close} for day, close in [(5, 100), (7, 110), (8, 105)]]
        stock = [{"date": f"2026-01-{day:02}", "close": close} for day, close in [(5, 100), (6, 105), (7, 110), (8, 105)]]
        with self.assertRaisesRegex(ValueError, "benchmark is missing observed session 2026-01-06"):
            analyze({"STOCK": stock, "BENCH": benchmark}, "BENCH")


if __name__ == "__main__":
    unittest.main()
