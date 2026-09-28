"""Small, descriptive analytics for adjusted daily closing prices."""

from datetime import date
from math import isfinite, sqrt
from statistics import stdev


def analyze(series: dict[str, list[dict]], benchmark: str) -> dict:
    """Align adjusted closes by date and report descriptive, in-sample metrics.

    Assets must contain benchmark sessions; the benchmark must also contain
    every session observed by an asset within the common window. This prevents
    an observable missing session from distorting daily return volatility.
    """
    if not isinstance(series, dict) or not series:
        raise ValueError("series must be a nonempty mapping")
    if benchmark not in series:
        raise ValueError("benchmark must be present in series")

    prices = {}
    for symbol, records in series.items():
        if not isinstance(symbol, str) or not symbol:
            raise ValueError("symbols must be nonempty strings")
        if not isinstance(records, list) or not records:
            raise ValueError(f"{symbol}: records must be a nonempty list")
        by_date = {}
        for record in records:
            if not isinstance(record, dict):
                raise ValueError(f"{symbol}: record must be a mapping")
            day = record.get("date")
            close = record.get("close")
            if not isinstance(day, str):
                raise ValueError(f"{symbol}: invalid date")
            try:
                parsed = date.fromisoformat(day)
            except ValueError as exc:
                raise ValueError(f"{symbol}: invalid date {day!r}") from exc
            if parsed.isoformat() != day:
                raise ValueError(f"{symbol}: date must use YYYY-MM-DD")
            if day in by_date:
                raise ValueError(f"{symbol}: duplicate date {day}")
            if isinstance(close, bool) or not isinstance(close, (int, float)):
                raise ValueError(f"{symbol}: close must be a positive finite number")
            close = float(close)
            if not isfinite(close) or close <= 0:
                raise ValueError(f"{symbol}: close must be a positive finite number")
            by_date[day] = close
        prices[symbol] = dict(sorted(by_date.items()))

    benchmark_dates = set(prices[benchmark])
    for symbol, by_date in prices.items():
        first, last = next(iter(by_date)), next(reversed(by_date))
        missing = sorted(day for day in benchmark_dates if first <= day <= last and day not in by_date)
        if missing:
            raise ValueError(f"{symbol}: missing benchmark session {missing[0]}")

    common_dates = sorted(set.intersection(*(set(by_date) for by_date in prices.values())))
    if len(common_dates) < 3:
        raise ValueError("at least three common dates are required")

    observed_dates = set.union(*(set(by_date) for by_date in prices.values()))
    missing_benchmark = sorted(day for day in observed_dates
                               if common_dates[0] <= day <= common_dates[-1]
                               and day not in benchmark_dates)
    if missing_benchmark:
        raise ValueError(f"{benchmark}: benchmark is missing observed session {missing_benchmark[0]}")

    dropped = {symbol: len(by_date) - len(common_dates) for symbol, by_date in prices.items()}
    warnings = []
    if len(common_dates) - 1 < 60:
        warnings.append("Fewer than 60 daily returns; volatility is based on a short sample.")
    for symbol, count in dropped.items():
        if count:
            warnings.append(f"{symbol}: {count} observation(s) dropped during date alignment.")

    benchmark_closes = [prices[benchmark][day] for day in common_dates]
    benchmark_return = benchmark_closes[-1] / benchmark_closes[0] - 1
    rows = []
    for symbol, by_date in prices.items():
        closes = [by_date[day] for day in common_dates]
        daily_returns = [current / previous - 1 for previous, current in zip(closes, closes[1:])]
        peak = closes[0]
        drawdown = []
        for close in closes:
            peak = max(peak, close)
            drawdown.append(close / peak - 1)
        total_return = closes[-1] / closes[0] - 1
        rows.append({
            "symbol": symbol,
            "total_return": total_return,
            "annualized_volatility": stdev(daily_returns) * sqrt(252),
            "max_drawdown": min(drawdown),
            "excess_return": total_return - benchmark_return,
            "observations": len(common_dates),
            "first_date": common_dates[0],
            "last_date": common_dates[-1],
            "normalized": [close / closes[0] * 100 for close in closes],
            "drawdown": drawdown,
            "adjusted_close": closes[-1],
        })
    return {
        "dates": common_dates,
        "benchmark": benchmark,
        "rows": rows,
        "warnings": warnings,
        "dropped_observations": dropped,
    }
