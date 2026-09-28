"""Read personal, local Norgate data. Never persist or substitute price data."""
import os
import re
from datetime import date
from pathlib import Path


class DataError(ValueError):
    """A data problem that can be explained to the user."""


def validate_request(symbols, benchmark, start, end):
    symbols = list(dict.fromkeys(s.strip().upper() for s in symbols.split(",") if s.strip()))
    benchmark = benchmark.strip().upper()
    if not 1 <= len(symbols) <= 6:
        raise DataError("Enter between 1 and 6 stock symbols, separated by commas.")
    if any(not re.fullmatch(r"[A-Z0-9.$^_\-]{1,32}", s) for s in symbols + [benchmark]):
        raise DataError("Use valid US symbols such as AAPL, MSFT, BRK.B, or SPY.")
    try:
        start, end = date.fromisoformat(start), date.fromisoformat(end)
    except (ValueError, TypeError):
        raise DataError("Enter valid start and end dates.") from None
    if start >= end:
        raise DataError("The start date must be before the end date.")
    if end > date.today():
        raise DataError("The end date cannot be in the future.")
    if (end - start).days > 365 * 20 + 5:
        raise DataError("Choose a date range of 20 years or less.")
    return list(dict.fromkeys(symbols + [benchmark])), benchmark, start, end


def connect():
    runtime = Path(__file__).resolve().parent / ".runtime"
    runtime.mkdir(exist_ok=True)
    os.environ.setdefault("NORGATEDATA_ROOT", str(runtime))
    try:
        import norgatedata
    except ImportError:
        raise DataError("Norgate's Python package is missing. Run setup.ps1, then restart the app.") from None
    if not norgatedata.status():
        raise DataError("Open Norgate Data Updater, sign in, and finish its data update. Then try again.")
    return norgatedata


def load_prices(symbols, start, end, sdk=None):
    sdk = sdk or connect()
    databases = sdk.databases()
    # Include delisted equities for explicitly chosen historical comparisons.
    available = set()
    for database in ("US Equities", "US Equities Delisted"):
        if database in databases:
            available.update(sdk.database_symbols(database))
    if not available:
        raise DataError("The US equities database is unavailable. Check your Norgate subscription and update status.")
    missing = [s for s in symbols if s not in available]
    if missing:
        raise DataError("Not found in your local US equities data: " + ", ".join(missing) + ". Check the symbol in Norgate Data Updater.")
    series, warnings = {}, []
    for symbol in symbols:
        try:
            frame = sdk.price_timeseries(
                symbol, start_date=start.isoformat(), end_date=end.isoformat(), interval="D",
                stock_price_adjustment_setting=sdk.StockPriceAdjustmentType.TOTALRETURN,
                padding_setting=sdk.PaddingType.NONE, timeseriesformat="pandas-dataframe",
            )
        except ValueError:
            raise DataError(f"Norgate could not return data for {symbol} in this date range.") from None
        if frame is None or frame.empty or "Close" not in frame.columns:
            raise DataError(f"No daily prices for {symbol} in this date range. Check the dates and your subscription history.")
        dates = frame["Date"] if "Date" in frame.columns else frame.index
        records = [{"date": d.strftime("%Y-%m-%d"), "close": float(c)} for d, c in zip(dates, frame["Close"])]
        if any(not start.isoformat() <= row["date"] <= end.isoformat() for row in records):
            raise DataError(f"Norgate returned {symbol} prices outside the requested dates.")
        series[symbol] = records
        latest = date.fromisoformat(records[-1]["date"])
        if (end - latest).days > 7:
            warnings.append(f"{symbol} ends on {latest.isoformat()}, more than 7 calendar days before the requested end. It may be stale, suspended, or delisted.")
        earliest = date.fromisoformat(records[0]["date"])
        if (earliest - start).days > 7:
            warnings.append(f"{symbol} starts on {earliest.isoformat()}; earlier requested history is unavailable.")
    return series, warnings
