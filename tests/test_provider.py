"""Exercise Norgate's contract using synthetic fixtures, never licensed rows."""
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd

from provider import DataError, load_prices, validate_request


class ProviderTests(unittest.TestCase):
    def sdk(self, frame):
        sdk = Mock()
        sdk.databases.return_value = ["US Equities"]
        sdk.database_symbols.return_value = ["AAPL", "SPY"]
        sdk.StockPriceAdjustmentType = SimpleNamespace(TOTALRETURN="total-return")
        sdk.PaddingType = SimpleNamespace(NONE="no-padding")
        sdk.price_timeseries.return_value = frame
        return sdk

    def test_validates_and_deduplicates_symbols(self):
        result = validate_request(" aapl, AAPL, msft ", "spy", "2025-01-01", "2025-02-01")
        self.assertEqual(result[0], ["AAPL", "MSFT", "SPY"])

    def test_invalid_requests_rejected(self):
        for symbols, benchmark, start, end in [
            ("", "SPY", "2025-01-01", "2025-02-01"),
            ("AAPL", "../secret", "2025-01-01", "2025-02-01"),
            ("A,B,C,D,E,F,G", "SPY", "2025-01-01", "2025-02-01"),
            ("AAPL", "SPY", "2025-02-01", "2025-01-01"),
            ("AAPL", "SPY", "2025-01-01", "2999-01-01"),
        ]:
            with self.subTest(symbols=symbols, end=end), self.assertRaises(DataError):
                validate_request(symbols, benchmark, start, end)

    def test_adjustment_padding_and_dates_are_explicit(self):
        frame = pd.DataFrame({"Close": [100., 105., 102.]}, index=pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"]))
        sdk = self.sdk(frame)
        result, warnings = load_prices(["AAPL"], date(2025, 1, 1), date(2025, 1, 7), sdk)
        self.assertEqual(result["AAPL"][0], {"date": "2025-01-02", "close": 100.})
        self.assertEqual(warnings, [])
        sdk.price_timeseries.assert_called_once_with("AAPL", start_date="2025-01-01", end_date="2025-01-07", interval="D", stock_price_adjustment_setting="total-return", padding_setting="no-padding", timeseriesformat="pandas-dataframe")

    def test_empty_unknown_or_outside_range_never_falls_back(self):
        for frame, symbol in [(pd.DataFrame(), "AAPL"), (None, "AAPL"), (None, "BAD")]:
            with self.subTest(symbol=symbol), self.assertRaises(DataError):
                load_prices([symbol], date(2025, 1, 1), date(2025, 2, 1), self.sdk(frame))
        frame = pd.DataFrame({"Close": [100.]}, index=pd.to_datetime(["2024-12-01"]))
        with self.assertRaises(DataError):
            load_prices(["AAPL"], date(2025, 1, 1), date(2025, 2, 1), self.sdk(frame))

    def test_date_column_and_stale_data_are_visible(self):
        frame = pd.DataFrame({"Date": pd.to_datetime(["2025-01-02", "2025-01-03"]), "Close": [100., 101.]})
        _, warnings = load_prices(["AAPL"], date(2025, 1, 1), date(2025, 2, 1), self.sdk(frame))
        self.assertIn("2025-01-03", warnings[0])


if __name__ == "__main__":
    unittest.main()
