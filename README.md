# Algo-Trade-Backtester (SNIPER v8.39)

## Project Overview

A backtesting engine for the SNIPER v8.39 trading strategy, developed and tuned on BIST:AKFYE. The strategy uses a hierarchical entry confirmation system combining EMA trend direction, volume flow, Bollinger Band positioning, and SuperTrend — and replaces a standard stop-loss with four distinct candle-based exhaustion exit signals. Tested on 2023–2026 AKFYE data, the strategy returned +116% against the underlying asset's +60% gain over the same period.

---

## Why I Built This

I wanted to test whether a rule-based entry/exit system could outperform simply holding the asset. The core question was: can disciplined exits during selling pressure preserve more capital than a fixed stop-loss? After 8 major iterations, v8.39 is the configuration that produced the most consistent results on AKFYE data.

---

## Core Tech Stack

- Python 3.10+
- `yfinance` — historical OHLCV data from Yahoo Finance
- `pandas-ta` — technical indicator calculations
- `pandas` — data manipulation
- `plotly` — interactive trade visualization

---

## Key Engineering Decisions

**Hierarchical entry confirmation ("King Criteria")**

Rather than entering on a single signal, three conditions must be satisfied simultaneously: price must be at least 0.33% above EMA-50 (breakout buffer, not just a touch), EMA slope must be positive (uptrend, not sideways), and volume must exceed the 20-day average (confirms institutional participation). SuperTrend is used as a fourth filter — but only when it is not flattening near the Bollinger upper band, where it tends to generate false positives.

**Candle-based exhaustion exits instead of fixed stop-loss**

A fixed stop-loss exits too early in volatile assets like AKFYE. I replaced it with four exit conditions ranked by severity. The precision exit triggers after four consecutive candles where the body exceeds 34.7% of the total candle range — this specific ratio emerged from manual analysis of AKFYE's historical sell-off patterns. The hard exit (five consecutive red candles) is unconditional. Both trigger a "penalty mode" that requires a strong confirmation candle before the next entry.

**Configurable parameters at the top of the file**

All thresholds (`BUY_TOLERANCE`, `STOP_TOLERANCE`, `BODY_RATIO_THRESHOLD`, etc.) are defined as constants at the top of `main.py`. Changing a parameter and re-running takes under a second — this made iterating through strategy versions significantly faster.

---

## Challenges & Lessons

**SuperTrend column naming is not stable**

`pandas-ta` generates SuperTrend column names dynamically based on the parameters passed (e.g. `SUPERT_10_3.0`). Hardcoding the column name broke every time parameters changed. I switched to dynamic detection using `startswith("SUPERTd")` and `startswith("SUPERT_")`, which made the code parameter-agnostic.

**The 34.7% body ratio is AKFYE-specific**

This threshold was not derived from a formula — it came from observing AKFYE's candle structure during confirmed sell-offs and iterating until false positives dropped to an acceptable level. It likely needs recalibration for other tickers. The strategy file documents this explicitly.

**Penalty mode prevents over-trading after bad exits**

Early versions re-entered immediately after an exhaustion exit, often catching the continuation of the same sell-off. Penalty mode was added to require a strong bullish candle before the next entry, which reduced the number of losing round-trips significantly.

---

## How to Run

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Run the backtest**
```bash
python main.py
```

The script prints each trade to the terminal and opens an interactive Plotly chart showing entry/exit points on the candlestick graph.

**To test a different ticker or date range**, edit the constants at the top of `main.py`:
```python
SYMBOL = "AKFYE"
START_DATE = "2023-01-01"
INITIAL_CAPITAL = 10_000
```

---

## Backtest Results (AKFYE, 2023–2026)

| Metric | Value |
|---|---|
| Starting capital | 10,000 TL |
| Final capital | 21,602 TL |
| Strategy return | +116% |
| Asset return (buy & hold) | +60% |
| Outperformance | ~2x |

---

## Disclaimer

All code, analysis, and backtest results in this repository are for educational purposes only. Past performance does not guarantee future results. This is not investment advice. All trading decisions and their consequences are the sole responsibility of the user.

---

## License

MIT — Emircan Bingöl, 2026