"""A synthetic lesson using the real analytics engine; no Norgate required.

From the repository root: python -m examples.learn_metrics
Change the fictional prices below to explore the exercises in README.md.
"""
from analytics import analyze


def main():
    # These are invented observations, not market data or a trading result.
    dates = ["2026-01-05", "2026-01-06", "2026-01-07"]
    prices = {
        "LESSON_STOCK": [100, 110, 99],
        "LESSON_BENCH": [100, 101, 102],
    }
    # Convert a readable lesson fixture into the engine's input contract.
    series = {
        symbol: [{"date": day, "close": close} for day, close in zip(dates, closes, strict=True)]
        for symbol, closes in prices.items()
    }
    result = analyze(series, benchmark="LESSON_BENCH")
    print("SYNTHETIC LEARNING EXAMPLE - no market data or Norgate connection\n")
    for row in result["rows"]:
        # The engine returns fractions: 0.02 is displayed as 2.00%.
        print(f"Symbol: {row['symbol']}")
        print(f"Total return: {row['total_return']:.2%}")
        print(f"Annualized volatility: {row['annualized_volatility']:.2%}")
        print(f"Maximum drawdown: {row['max_drawdown']:.2%}")
        print(f"Excess return: {row['excess_return'] * 100:.2f} pp")
        print(f"Growth of 100: {[round(value, 2) for value in row['normalized']]}")
        print()
    for warning in result["warnings"]:
        print(f"Data note: {warning}")


if __name__ == "__main__":
    main()
