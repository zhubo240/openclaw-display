#!/usr/bin/env python3
"""
Round 5 Final Deep Verification:
1. AMLP C-corp tracking error vs direct MLPs (EPD, ET)
2. JEPI performance by VIX regime
3. Tax-optimized final portfolio backtest (STIP replacing TLT)
4. JEPI "dividend recovery speed" — how many months of dividends to recover a 10% drawdown
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("ROUND 5 FINAL DEEP VERIFICATION")
print("=" * 70)

# ============================================================
# 1. AMLP C-corp Tracking Error vs Direct MLPs
# ============================================================
print("\n" + "=" * 70)
print("1. AMLP C-CORP TRACKING ERROR vs DIRECT MLPs")
print("=" * 70)

# Compare AMLP total return vs EPD and ET (major direct MLPs)
tickers = ['AMLP', 'EPD', 'ET']
data = yf.download(tickers, start="2021-01-01", progress=False)
close_col = 'Adj Close' if 'Adj Close' in data.columns else 'Close'
prices = data[close_col]

if len(prices) > 0:
    # Annualized returns
    for t in tickers:
        col = prices[t].dropna()
        if len(col) > 252:
            total_ret = col.iloc[-1] / col.iloc[0] - 1
            years = len(col) / 252
            ann_ret = (1 + total_ret) ** (1/years) - 1
            print(f"  {t}: total return {total_ret*100:.1f}%, annualized {ann_ret*100:.2f}% ({years:.1f} years)")

    # Tracking error: AMLP vs average of EPD+ET
    rets = prices.pct_change().dropna()
    mlp_avg = (rets['EPD'] + rets['ET']) / 2
    tracking_diff = rets['AMLP'] - mlp_avg
    te_annual = tracking_diff.std() * np.sqrt(252)
    mean_diff = tracking_diff.mean() * 252
    print(f"\n  AMLP vs (EPD+ET)/2:")
    print(f"    Annual tracking error: {te_annual*100:.2f}%")
    print(f"    Annual return drag (AMLP underperformance): {mean_diff*100:.2f}%")
    print(f"    This drag = C-corp tax + 0.85% fee + structural differences")

    # Also check dividends
    for t in tickers:
        tk = yf.Ticker(t)
        divs = tk.dividends
        ttm = divs.last('12M').sum()
        latest = prices[t].dropna().iloc[-1]
        yld = ttm / latest * 100
        print(f"  {t}: TTM dividend ${ttm:.2f}, yield {yld:.2f}%")

# ============================================================
# 2. JEPI Performance by VIX Regime
# ============================================================
print("\n" + "=" * 70)
print("2. JEPI PERFORMANCE BY VIX REGIME")
print("=" * 70)

# Get VIX data
vix = yf.download("^VIX", start="2021-06-01", progress=False)
vix_close = vix['Close']
if hasattr(vix_close, 'columns'):
    vix_close = vix_close.iloc[:, 0]

jepi_data = yf.download("JEPI", start="2021-06-01", progress=False)
spy_data = yf.download("SPY", start="2021-06-01", progress=False)

adj_jepi = jepi_data['Adj Close'] if 'Adj Close' in jepi_data.columns else jepi_data['Close']
adj_spy = spy_data['Adj Close'] if 'Adj Close' in spy_data.columns else spy_data['Close']
if hasattr(adj_jepi, 'columns'):
    adj_jepi = adj_jepi.iloc[:, 0]
if hasattr(adj_spy, 'columns'):
    adj_spy = adj_spy.iloc[:, 0]

jepi_ret = adj_jepi.pct_change().dropna()
spy_ret = adj_spy.pct_change().dropna()

# Align all series
common_idx = jepi_ret.index.intersection(spy_ret.index).intersection(vix_close.index)
jepi_ret = jepi_ret.loc[common_idx]
spy_ret = spy_ret.loc[common_idx]
vix_aligned = vix_close.loc[common_idx]

# Monthly aggregation for cleaner analysis
jepi_monthly = (1 + jepi_ret).resample('M').prod() - 1
spy_monthly = (1 + spy_ret).resample('M').prod() - 1
vix_monthly = vix_aligned.resample('M').mean()

# Common monthly index
common_m = jepi_monthly.index.intersection(spy_monthly.index).intersection(vix_monthly.index)
jepi_m = jepi_monthly.loc[common_m]
spy_m = spy_monthly.loc[common_m]
vix_m = vix_monthly.loc[common_m]

print(f"  Analysis period: {common_m[0].date()} to {common_m[-1].date()} ({len(common_m)} months)")

# Segment by VIX regime
regimes = [
    ("Low VIX (<18)", vix_m < 18),
    ("Mid VIX (18-25)", (vix_m >= 18) & (vix_m < 25)),
    ("High VIX (25+)", vix_m >= 25),
]

print(f"\n  {'Regime':<20s} {'Months':>6s} {'JEPI avg':>10s} {'SPY avg':>10s} {'JEPI-SPY':>10s}")
print(f"  {'-'*56}")

for name, mask in regimes:
    n = mask.sum()
    if n > 0:
        jepi_avg = jepi_m[mask].mean() * 100
        spy_avg = spy_m[mask].mean() * 100
        diff = (jepi_avg - spy_avg)
        print(f"  {name:<20s} {n:>6d} {jepi_avg:>+10.2f}% {spy_avg:>+10.2f}% {diff:>+10.2f}%")

print("""
  CLAIMS TO TEST:
  - 种子材料: 'VIX高位是卖波动率策略的甜蜜点'
  - 组合构建: 'JEPI分红从2022(VIX~26)到2024(VIX~15.5)下降了32%'
  - 风险量化R3: 'VIX 25+环境下凸性税性价比可接受'
""")

# JEPI dividend per share by VIX regime (quarterly)
jepi_tk = yf.Ticker("JEPI")
jepi_divs = jepi_tk.dividends

print("  JEPI monthly dividends vs VIX (last 24 months):")
for i in range(min(24, len(jepi_divs))):
    idx = len(jepi_divs) - 24 + i
    if idx >= 0:
        d = jepi_divs.iloc[idx]
        dt = jepi_divs.index[idx]
        # Find closest VIX
        try:
            vix_val = vix_close.asof(dt)
            print(f"    {dt.date()}: ${d:.4f}  VIX≈{vix_val:.1f}")
        except:
            print(f"    {dt.date()}: ${d:.4f}")

# Correlation between VIX level and JEPI dividend
div_vix_pairs = []
for dt, d in jepi_divs.items():
    try:
        v = vix_close.asof(dt)
        if not np.isnan(v):
            div_vix_pairs.append((v, d))
    except:
        pass

if len(div_vix_pairs) > 10:
    vix_arr = np.array([p[0] for p in div_vix_pairs])
    div_arr = np.array([p[1] for p in div_vix_pairs])
    from scipy.stats import pearsonr
    corr, pval = pearsonr(vix_arr, div_arr)
    print(f"\n  VIX-JEPI dividend correlation: r={corr:.3f}, p={pval:.4f}")
    print(f"  CLAIM: JEPI dividends are positively correlated with VIX")
    if corr > 0 and pval < 0.05:
        print(f"  VERDICT: ✅ Confirmed (r={corr:.3f})")
    elif corr > 0:
        print(f"  VERDICT: ⚠️ Positive but not statistically significant")
    else:
        print(f"  VERDICT: ❌ Not confirmed")

# ============================================================
# 3. Tax-Optimized Final Portfolio Backtest (STIP replacing TLT)
# ============================================================
print("\n" + "=" * 70)
print("3. FINAL PORTFOLIO BACKTEST: SGOV/JEPI/AMLP/STIP/GLD")
print("=" * 70)

# Original: 40% SGOV / 30% JEPI / 20% AMLP / 10% TLT
# Final proposed: 35% SGOV / 30% JEPI / 10% AMLP / 10% STIP / 10% GLD / 5% cash(=SGOV)
# Which = 40% SGOV / 30% JEPI / 10% AMLP / 10% STIP / 10% GLD

portfolios = {
    "Original (SGOV/JEPI/AMLP/TLT)": {
        'SGOV': 0.40, 'JEPI': 0.30, 'AMLP': 0.20, 'TLT': 0.10
    },
    "Final (SGOV/JEPI/AMLP/STIP/GLD)": {
        'SGOV': 0.40, 'JEPI': 0.30, 'AMLP': 0.10, 'STIP': 0.10, 'GLD': 0.10
    },
    "Simple (70% SGOV / 30% JEPI)": {
        'SGOV': 0.70, 'JEPI': 0.30
    },
    "Pure SGOV": {
        'SGOV': 1.00
    }
}

all_tickers = list(set(t for p in portfolios.values() for t in p.keys()))
port_data = yf.download(all_tickers, start="2022-06-01", progress=False)
close_col = 'Adj Close' if 'Adj Close' in port_data.columns else 'Close'
port_prices = port_data[close_col]
port_returns = port_prices.pct_change().dropna()

print(f"\n  Period: {port_returns.index[0].date()} to {port_returns.index[-1].date()}")
print(f"\n  {'Portfolio':<42s} {'Ann Ret':>8s} {'Max DD':>8s} {'Vol':>8s} {'Sharpe':>8s}")
print(f"  {'-'*74}")

for name, weights in portfolios.items():
    try:
        port_ret = sum(w * port_returns[t] for t, w in weights.items())
        total_ret = (1 + port_ret).prod() - 1
        ann_ret = (1 + total_ret) ** (252 / len(port_ret)) - 1
        ann_vol = port_ret.std() * np.sqrt(252)
        cumulative = (1 + port_ret).cumprod()
        max_dd = (cumulative / cumulative.cummax() - 1).min()
        sharpe = (ann_ret - 0.035) / ann_vol if ann_vol > 0.001 else float('inf')
        print(f"  {name:<42s} {ann_ret*100:>+7.2f}% {max_dd*100:>+7.2f}% {ann_vol*100:>7.2f}% {sharpe:>7.2f}")
    except Exception as e:
        print(f"  {name:<42s} ERROR: {e}")

# ============================================================
# 4. JEPI Dividend Recovery Speed
# ============================================================
print("\n" + "=" * 70)
print("4. JEPI DRAWDOWN RECOVERY VIA DIVIDENDS")
print("=" * 70)

# How many months of dividends to recover a 10%, 15%, 20% drawdown?
jepi_annual_div = jepi_divs.last('12M').sum()
jepi_monthly_div = jepi_annual_div / 12
jepi_latest_price = adj_jepi.iloc[-1]

print(f"  JEPI latest price: ${jepi_latest_price:.2f}")
print(f"  JEPI TTM annual dividend: ${jepi_annual_div:.2f}")
print(f"  JEPI avg monthly dividend: ${jepi_monthly_div:.4f}")

for dd_pct in [5, 10, 15, 20]:
    loss_per_share = jepi_latest_price * dd_pct / 100
    months_to_recover = loss_per_share / jepi_monthly_div
    print(f"\n  {dd_pct}% drawdown = ${loss_per_share:.2f}/share loss")
    print(f"    Recovery via dividends: {months_to_recover:.1f} months ({months_to_recover/12:.1f} years)")
    print(f"    种子材料 claim for 10%: '14-15 months' → Actual: {loss_per_share / jepi_monthly_div:.1f} months")

# ============================================================
# 5. AMLP Dividend Stability Over Time
# ============================================================
print("\n" + "=" * 70)
print("5. AMLP DIVIDEND HISTORY & STABILITY")
print("=" * 70)

amlp_tk = yf.Ticker("AMLP")
amlp_divs = amlp_tk.dividends
print("  AMLP annual dividends:")
for year in range(2015, 2027):
    year_divs = amlp_divs[amlp_divs.index.year == year]
    if len(year_divs) > 0:
        total = year_divs.sum()
        print(f"    {year}: ${total:.4f} ({len(year_divs)} payments)")

# Dividend stability: coefficient of variation of annual dividends
annual_divs = []
for year in range(2018, 2026):
    yd = amlp_divs[amlp_divs.index.year == year].sum()
    if yd > 0:
        annual_divs.append(yd)

if len(annual_divs) > 2:
    cv = np.std(annual_divs) / np.mean(annual_divs)
    print(f"\n  AMLP dividend CV (2018-2025): {cv:.3f}")
    print(f"  Mean annual dividend: ${np.mean(annual_divs):.2f}")
    print(f"  Std: ${np.std(annual_divs):.2f}")
    print(f"  Min: ${min(annual_divs):.2f}, Max: ${max(annual_divs):.2f}")

    # Compare with JEPI
    jepi_annual = []
    for year in range(2022, 2026):
        jd = jepi_divs[jepi_divs.index.year == year].sum()
        if jd > 0:
            jepi_annual.append(jd)
    if len(jepi_annual) > 1:
        jepi_cv = np.std(jepi_annual) / np.mean(jepi_annual)
        print(f"\n  JEPI dividend CV (2022-2025): {jepi_cv:.3f}")
        print(f"  AMLP CV: {cv:.3f} vs JEPI CV: {jepi_cv:.3f}")
        if cv < jepi_cv:
            print(f"  → AMLP dividends are MORE stable than JEPI")
        else:
            print(f"  → JEPI dividends are MORE stable than AMLP")

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
