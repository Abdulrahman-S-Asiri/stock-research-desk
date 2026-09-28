# Stock Research Desk

A small personal US stock research dashboard using **your local Norgate Data subscription**. Compare up to six symbols with a benchmark ETF over a chosen period. Inspect dividend-adjusted growth, total return, excess return, annualized volatility, and maximum drawdown.

## Open it

While the app is running, open **http://127.0.0.1:8765**. Enter symbols separated by commas, choose dates, and select **Compare stocks**. The 1Y, 3Y, and 5Y buttons set dates; select Compare stocks to apply them. Switch the chart between Growth and Drawdown.

On this computer the environment is already installed. From the project folder:

```powershell
.\start.ps1
```

Leave that terminal running; Ctrl+C stops the app. If PowerShell blocks the script, run `.\.venv\Scripts\python.exe app.py` directly. If port 8765 is occupied, use `.\.venv\Scripts\python.exe app.py --port 8766` and open that port instead.

On another Windows computer, install 64-bit Python 3.13 or later, install and sign into Norgate Data Updater with an active US equities subscription, finish its data update, then run:

```powershell
.\setup.ps1
.\start.ps1
```

Dependency versions are pinned in `requirements.lock.txt`. No API key or paid AI service is needed. The app reads the local database; it does not trigger a Norgate data download. Use Norgate Data Updater to keep data current.

## What the numbers mean

- **Total return:** last adjusted close / first adjusted close − 1.
- **Growth of 100:** adjusted close / first adjusted close × 100.
- **Excess return:** stock total return minus benchmark total return, shown in percentage points.
- **Volatility:** sample standard deviation of daily percentage returns × √252. This is historical variability, not a prediction.
- **Drawdown:** adjusted close / running maximum adjusted close − 1. Maximum drawdown is the worst observation within the displayed window; it is not an all-time maximum drawdown.

All symbols use the intersection of observed dates. There is no forward fill. An internal missing benchmark session in a stock's data causes an error rather than silently treating a multi-session change as a daily return. The benchmark is also checked against other symbols' observed dates within the common window. Later listings and earlier endings shorten the common period and generate alignment notes. There is no independent exchange calendar; sessions absent from every selected series cannot be detected this way.

Data is explicitly requested with Norgate `TOTALRETURN` adjustment and `PaddingType.NONE`, using daily observations. Actual first and last dates are displayed. A last date more than seven calendar days before the requested end generates a warning; this is a simple gap heuristic, not a full exchange-calendar freshness check. Fewer than 60 daily returns also generates a warning.

## Evidence level and limits

**Historical comparison**, not a strategy backtest, paper result, live result, trade recommendation, or portfolio simulation. The app excludes costs, slippage, taxes, and execution assumptions because it places no simulated or live orders. It has no broker connection. Today's chosen watchlist can introduce selection and survivorship bias. Delisted Norgate symbols can be entered if your subscription includes them, but there is no historical index-membership universe. No claim of profitability or unbiased strategy validation is made.

Raw adjusted price levels are not current tradable quotes. This is end-of-day research. Symbols with insufficient shared history cannot be compared. Unknown symbols, missing subscriptions, and unavailable data produce explicit errors; no synthetic or alternate-provider prices are substituted.

## Local data and licensing

The server binds only to `127.0.0.1`, allows only its local hosts/origins, and exposes a fixed list of public assets. No external chart services, fonts, analytics, or cloud processing are used. API responses are marked `no-store`; the app does not save price rows to files or browser storage. Norgate's own local files remain governed by its license.

Do not expose this server to the internet or upload licensed market data. Norgate permits personal research and restricts content redistribution; consult your current agreement, including data retention requirements on subscription expiry. The app is local because Norgate's Python integration reads the Windows updater database.

Primary references checked during development:

- [Norgate's Python package and API](https://pypi.org/project/norgatedata/)
- [Norgate FAQ](https://norgatedata.com/faq.php)
- [Norgate EULA](https://norgatedata.com/subscribe/eula.php)
- [Adjustment methods](https://norgatedata.com/data-package-faq.php)

## Verify or develop

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --check static/app.js
```

Tests use small synthetic fixtures, not licensed data. CI can run the Python suite without Norgate installed or signed in. Node is needed only for the optional JavaScript syntax check, not to run the dashboard.

The project has four simple parts: `provider.py` reads Norgate, `analytics.py` computes metrics, `app.py` serves the local interface, and `static/` contains the browser UI. Separate agents researched the API, implemented/tested analytics, and independently reviewed the project. Relevant coding and browser skills were used; unrelated plugins were deliberately excluded.

This is private personal source with no open-source license granted. Runtime files, dependencies, logs, credentials, and market-data exports are excluded from Git. Development verification logs are kept outside the repository.
