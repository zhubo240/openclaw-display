#!/usr/bin/env python3
"""
Round 3 Code Verification: Comprehensive check of quantitative claims
from all agents in the SP500 vs BigTech discussion.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIG
# ============================================================
TODAY = datetime(2026, 3, 15)
YTD_START = datetime(2026, 1, 1)
# yfinance won't have data past its cutoff, so we use latest available
# and note the actual date range in output

results = {}

print("=" * 70)
print("VERIFICATION SCRIPT — Round 3 Code Verification")
print("=" * 70)

# ============================================================
# 1. JEPI: Dividend yield, total return, capture ratios
# ============================================================
print("\n" + "=" * 70)
print("1. JEPI VERIFICATION")
print("=" * 70)

jepi = yf.Ticker("JEPI")
spy = yf.Ticker("SPY")

# Get dividend history
jepi_divs = jepi.dividends
print(f"\nJEPI dividend history (last 36 months):")

# Annual dividend totals
for year in [2022, 2023, 2024, 2025]:
    year_divs = jepi_divs[jepi_divs.index.year == year]
    if len(year_divs) > 0:
        total = year_divs.sum()
        print(f"  {year}: ${total:.4f}/share ({len(year_divs)} payments)")

# Claim: 组合构建 says JEPI dividends declined 32% from 2022 to 2024
# ($6.25 -> $4.76 -> $4.25)
divs_2022 = jepi_divs[jepi_divs.index.year == 2022].sum()
divs_2023 = jepi_divs[jepi_divs.index.year == 2023].sum()
divs_2024 = jepi_divs[jepi_divs.index.year == 2024].sum()
if divs_2022 > 0 and divs_2024 > 0:
    decline = (divs_2024 - divs_2022) / divs_2022 * 100
    print(f"\n  CLAIM: 组合构建 says dividends declined 32% from 2022→2024")
    print(f"  ACTUAL: 2022=${divs_2022:.2f}, 2023=${divs_2023:.2f}, 2024=${divs_2024:.2f}")
    print(f"  ACTUAL decline: {decline:.1f}%")
    results['jepi_div_decline'] = decline

# Current yield
jepi_hist = jepi.history(period="1y")
if len(jepi_hist) > 0:
    latest_price = jepi_hist['Close'].iloc[-1]
    ttm_divs = jepi_divs.last('12M').sum()
    current_yield = ttm_divs / latest_price * 100
    print(f"\n  JEPI latest price: ${latest_price:.2f}")
    print(f"  TTM dividends: ${ttm_divs:.2f}")
    print(f"  CLAIM: Seed material says yield ~8.34%")
    print(f"  ACTUAL TTM yield: {current_yield:.2f}%")
    results['jepi_yield'] = current_yield

# JEPI vs SPY: capture ratios
print("\n  --- Capture Ratio Analysis ---")
jepi_prices = yf.download("JEPI", start="2021-06-01", progress=False)
spy_prices = yf.download("SPY", start="2021-06-01", progress=False)

if len(jepi_prices) > 0 and len(spy_prices) > 0:
    # Use Adjusted Close for total return
    adj_col_jepi = 'Adj Close' if 'Adj Close' in jepi_prices.columns else 'Close'
    adj_col_spy = 'Adj Close' if 'Adj Close' in spy_prices.columns else 'Close'

    jepi_ret = jepi_prices[adj_col_jepi].pct_change().dropna()
    spy_ret = spy_prices[adj_col_spy].pct_change().dropna()

    # Flatten if MultiIndex
    if hasattr(jepi_ret, 'columns'):
        jepi_ret = jepi_ret.iloc[:, 0]
    if hasattr(spy_ret, 'columns'):
        spy_ret = spy_ret.iloc[:, 0]

    # Align dates
    common = jepi_ret.index.intersection(spy_ret.index)
    jepi_ret = jepi_ret.loc[common]
    spy_ret = spy_ret.loc[common]

    # Monthly returns for capture ratio
    jepi_monthly = (1 + jepi_ret).resample('M').prod() - 1
    spy_monthly = (1 + spy_ret).resample('M').prod() - 1

    common_m = jepi_monthly.index.intersection(spy_monthly.index)
    jepi_monthly = jepi_monthly.loc[common_m]
    spy_monthly = spy_monthly.loc[common_m]

    up_months = spy_monthly > 0
    down_months = spy_monthly < 0

    if up_months.sum() > 0:
        upside_capture = (jepi_monthly[up_months].mean() / spy_monthly[up_months].mean()) * 100
        print(f"  Upside capture: {upside_capture:.1f}%")
        print(f"  CLAIM (风险量化): 53%")

    if down_months.sum() > 0:
        downside_capture = (jepi_monthly[down_months].mean() / spy_monthly[down_months].mean()) * 100
        print(f"  Downside capture: {downside_capture:.1f}%")
        print(f"  CLAIM (风险量化): 78%")

    updown_ratio = upside_capture / downside_capture if downside_capture > 0 else 0
    print(f"  Up/Down ratio: {updown_ratio:.2f}")
    print(f"  CLAIM (风险量化): 0.68 (53/78)")

    results['jepi_upside_capture'] = upside_capture
    results['jepi_downside_capture'] = downside_capture

# ============================================================
# 2. AMLP: Max drawdown, 52-week range, dividend yield
# ============================================================
print("\n" + "=" * 70)
print("2. AMLP VERIFICATION")
print("=" * 70)

amlp_hist = yf.download("AMLP", start="2014-01-01", progress=False)
if len(amlp_hist) > 0:
    close_col = 'Adj Close' if 'Adj Close' in amlp_hist.columns else 'Close'
    prices = amlp_hist[close_col]
    if hasattr(prices, 'columns'):
        prices = prices.iloc[:, 0]

    # Max drawdown calculation
    cummax = prices.cummax()
    drawdown = (prices - cummax) / cummax
    max_dd = drawdown.min()
    max_dd_date = drawdown.idxmin()

    print(f"\n  AMLP Max Drawdown: {max_dd*100:.2f}%")
    print(f"  Max DD date: {max_dd_date}")
    print(f"  CLAIM (multiple agents): -77%")
    results['amlp_max_dd'] = max_dd * 100

    # 52-week range
    one_year_ago = prices.index[-1] - timedelta(days=365)
    recent = prices[prices.index >= one_year_ago]
    if len(recent) > 0:
        print(f"\n  52-week low: ${recent.min():.2f}")
        print(f"  52-week high: ${recent.max():.2f}")
        print(f"  Latest: ${prices.iloc[-1]:.2f}")
        print(f"  CLAIM (Yahoo Finance): $43.75 - $53.24")

    # Recovery time from max drawdown
    if max_dd_date is not None:
        pre_dd_peak = cummax.loc[max_dd_date]
        recovery = prices[prices.index > max_dd_date]
        recovered = recovery[recovery >= pre_dd_peak * 0.99]  # within 1%
        if len(recovered) > 0:
            recovery_date = recovered.index[0]
            recovery_days = (recovery_date - max_dd_date).days
            print(f"\n  Recovery from max DD: {recovery_days} trading days")
            print(f"  CLAIM (风险量化): 934 trading days")
        else:
            print(f"\n  Has NOT recovered to pre-DD peak (${pre_dd_peak:.2f})")

# AMLP dividend yield
amlp = yf.Ticker("AMLP")
amlp_divs = amlp.dividends
if len(amlp_divs) > 0:
    ttm_amlp_divs = amlp_divs.last('12M').sum()
    amlp_latest = prices.iloc[-1]
    amlp_yield = ttm_amlp_divs / amlp_latest * 100
    print(f"\n  AMLP TTM dividends: ${ttm_amlp_divs:.2f}")
    print(f"  AMLP yield: {amlp_yield:.2f}%")
    print(f"  CLAIM (种子材料): ~8.1%")
    results['amlp_yield'] = amlp_yield

# ============================================================
# 3. RSP vs SPY YTD divergence
# ============================================================
print("\n" + "=" * 70)
print("3. RSP vs SPY YTD DIVERGENCE")
print("=" * 70)

for ticker in ["RSP", "SPY"]:
    data = yf.download(ticker, start="2025-01-01", progress=False)
    close_col = 'Adj Close' if 'Adj Close' in data.columns else 'Close'
    prices = data[close_col]
    if hasattr(prices, 'columns'):
        prices = prices.iloc[:, 0]
    if len(prices) > 0:
        ytd_return = (prices.iloc[-1] / prices.iloc[0] - 1) * 100
        print(f"  {ticker} YTD return: {ytd_return:.2f}%  (from {prices.index[0].date()} to {prices.index[-1].date()})")
        results[f'{ticker.lower()}_ytd'] = ytd_return

if 'rsp_ytd' in results and 'spy_ytd' in results:
    divergence = results['rsp_ytd'] - results['spy_ytd']
    print(f"\n  RSP - SPY divergence: {divergence:.2f}pp")
    print(f"  CLAIMS:")
    print(f"    种子材料: equal-weight +3.16% vs cap-weight -1.54% (divergence 4.7pp)")
    print(f"    估值分析 [541715e2]: equal-weight +5.5% vs cap-weight -0.2% (divergence 5.7pp)")
    print(f"    风险量化 [83d2b104]: RSP YTD +7.03%")

# ============================================================
# 4. VDE YTD return
# ============================================================
print("\n" + "=" * 70)
print("4. VDE YTD RETURN")
print("=" * 70)

vde_data = yf.download("VDE", start="2025-01-01", progress=False)
close_col = 'Adj Close' if 'Adj Close' in vde_data.columns else 'Close'
vde_prices = vde_data[close_col]
if hasattr(vde_prices, 'columns'):
    vde_prices = vde_prices.iloc[:, 0]
if len(vde_prices) > 0:
    vde_ytd = (vde_prices.iloc[-1] / vde_prices.iloc[0] - 1) * 100
    print(f"  VDE YTD: {vde_ytd:.2f}%  ({vde_prices.index[0].date()} to {vde_prices.index[-1].date()})")
    print(f"  CLAIM (种子材料): +25%")
    results['vde_ytd'] = vde_ytd

# ============================================================
# 5. JEPI vs JEPQ dividend yields
# ============================================================
print("\n" + "=" * 70)
print("5. JEPQ DIVIDEND YIELD")
print("=" * 70)

jepq = yf.Ticker("JEPQ")
jepq_divs = jepq.dividends
jepq_hist = jepq.history(period="1y")
if len(jepq_divs) > 0 and len(jepq_hist) > 0:
    ttm_jepq_divs = jepq_divs.last('12M').sum()
    jepq_latest = jepq_hist['Close'].iloc[-1]
    jepq_yield = ttm_jepq_divs / jepq_latest * 100
    print(f"  JEPQ latest: ${jepq_latest:.2f}")
    print(f"  JEPQ TTM divs: ${ttm_jepq_divs:.2f}")
    print(f"  JEPQ yield: {jepq_yield:.2f}%")
    print(f"  CLAIM (种子材料): ~10.9%")
    results['jepq_yield'] = jepq_yield

# ============================================================
# 6. Expense ratios verification
# ============================================================
print("\n" + "=" * 70)
print("6. EXPENSE RATIO VERIFICATION")
print("=" * 70)

expense_claims = {
    'SGOV': 0.09,
    'JEPI': 0.35,
    'AMLP': 0.85,
    'XLE': 0.08,
}

for ticker, claimed in expense_claims.items():
    t = yf.Ticker(ticker)
    info = t.info
    actual = info.get('annualReportExpenseRatio') or info.get('totalExpenseRatio')
    if actual is not None:
        actual_pct = actual * 100
        print(f"  {ticker}: claimed={claimed}%, actual={actual_pct:.2f}%")
    else:
        # Try fundProfile
        print(f"  {ticker}: claimed={claimed}%, actual=N/A (not in yfinance info)")

# ============================================================
# 7. Portfolio stress test: 40/30/20/10 SGOV/JEPI/AMLP/TLT
# ============================================================
print("\n" + "=" * 70)
print("7. PORTFOLIO BACKTEST: 40% SGOV / 30% JEPI / 20% AMLP / 10% TLT")
print("=" * 70)

# JEPI launched mid-2020, so we start from 2021
tickers_port = ['SGOV', 'JEPI', 'AMLP', 'TLT']
weights = [0.40, 0.30, 0.20, 0.10]

port_data = yf.download(tickers_port, start="2022-06-01", progress=False)
close_col = 'Adj Close' if 'Adj Close' in port_data.columns else 'Close'
port_prices = port_data[close_col]

if len(port_prices) > 0:
    port_returns = port_prices.pct_change().dropna()

    # Weighted portfolio return
    port_ret = sum(w * port_returns[t] for w, t in zip(weights, tickers_port))

    # Key metrics
    total_ret = (1 + port_ret).prod() - 1
    ann_ret = (1 + total_ret) ** (252 / len(port_ret)) - 1
    ann_vol = port_ret.std() * np.sqrt(252)

    # Max drawdown
    cumulative = (1 + port_ret).cumprod()
    max_dd = (cumulative / cumulative.cummax() - 1).min()

    # Sharpe (assuming rf=3.5%)
    sharpe = (ann_ret - 0.035) / ann_vol if ann_vol > 0 else 0

    print(f"  Period: {port_returns.index[0].date()} to {port_returns.index[-1].date()}")
    print(f"  Total return: {total_ret*100:.2f}%")
    print(f"  Annualized return: {ann_ret*100:.2f}%")
    print(f"  Annualized volatility: {ann_vol*100:.2f}%")
    print(f"  Max drawdown: {max_dd*100:.2f}%")
    print(f"  Sharpe (rf=3.5%): {sharpe:.2f}")
    print(f"\n  CLAIM (种子材料): weighted expected return 5.5-6.5%")
    print(f"  CLAIM (风险量化 83d2b104): crisis scenario loss -23.5%")
    results['portfolio_ann_ret'] = ann_ret * 100
    results['portfolio_max_dd'] = max_dd * 100

# ============================================================
# 8. Correlation analysis: crisis vs normal
# ============================================================
print("\n" + "=" * 70)
print("8. CORRELATION ANALYSIS: NORMAL vs STRESS")
print("=" * 70)

corr_tickers = ['JEPI', 'AMLP', 'TLT', 'SPY', 'GLD']
corr_data = yf.download(corr_tickers, start="2022-01-01", progress=False)
close_col = 'Adj Close' if 'Adj Close' in corr_data.columns else 'Close'
corr_prices = corr_data[close_col]
corr_returns = corr_prices.pct_change().dropna()

if len(corr_returns) > 0:
    # Overall correlation
    print("\n  Full-period correlation matrix:")
    corr_full = corr_returns.corr()
    print(corr_full.round(3).to_string())

    # Stress period: 2022 (rate hike bear market)
    stress = corr_returns['2022']
    if len(stress) > 20:
        print("\n  2022 stress period correlation:")
        corr_stress = stress.corr()
        print(corr_stress.round(3).to_string())

    print(f"\n  CLAIMS (风险量化):")
    print(f"    JEPI-SPY normal: 0.85, crisis: 0.93")
    print(f"    AMLP-SPY normal: 0.45, crisis: 0.80+")
    print(f"    TLT-SPY: -0.30")

    results['jepi_spy_corr'] = corr_full.loc['JEPI', 'SPY'] if 'JEPI' in corr_full.index else None
    results['amlp_spy_corr'] = corr_full.loc['AMLP', 'SPY'] if 'AMLP' in corr_full.index else None

# ============================================================
# 9. TLT max drawdown & recent performance
# ============================================================
print("\n" + "=" * 70)
print("9. TLT VERIFICATION")
print("=" * 70)

tlt_data = yf.download("TLT", start="2002-01-01", progress=False)
close_col = 'Adj Close' if 'Adj Close' in tlt_data.columns else 'Close'
tlt_prices = tlt_data[close_col]
if hasattr(tlt_prices, 'columns'):
    tlt_prices = tlt_prices.iloc[:, 0]

if len(tlt_prices) > 0:
    cummax = tlt_prices.cummax()
    dd = (tlt_prices - cummax) / cummax
    max_dd = dd.min()
    max_dd_date = dd.idxmin()
    print(f"  TLT max drawdown: {max_dd*100:.2f}% on {max_dd_date.date()}")
    print(f"  CLAIM (风险量化 4fc4fe31): -47.75%")
    results['tlt_max_dd'] = max_dd * 100

    # 1-year total return
    one_yr_ago = tlt_prices.index[-1] - timedelta(days=365)
    tlt_1yr = tlt_prices[tlt_prices.index >= one_yr_ago]
    if len(tlt_1yr) > 1:
        tlt_1yr_ret = (tlt_1yr.iloc[-1] / tlt_1yr.iloc[0] - 1) * 100
        print(f"  TLT 1-year return: {tlt_1yr_ret:.2f}%")
        print(f"  CLAIM (风险量化): 0.53% total return past 12 months")

# ============================================================
# 10. Mag 7 concentration in SPY
# ============================================================
print("\n" + "=" * 70)
print("10. MAG 7 WEIGHT IN S&P 500")
print("=" * 70)

mag7 = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA']
print("  Individual Mag7 market caps:")
total_mag7_cap = 0
for t in mag7:
    info = yf.Ticker(t).info
    mcap = info.get('marketCap', 0)
    total_mag7_cap += mcap
    print(f"    {t}: ${mcap/1e12:.2f}T")

spy_info = yf.Ticker("SPY").info
# SPY total assets as proxy
print(f"\n  Total Mag7 market cap: ${total_mag7_cap/1e12:.2f}T")
print(f"  CLAIMS:")
print(f"    种子材料: top 10 = 38%, NVDA+MSFT+AAPL = ~20%")
print(f"    风险量化 [93be89f6]: Mag7 = 32.7%")

# ============================================================
# 11. RSP max drawdown (2008)
# ============================================================
print("\n" + "=" * 70)
print("11. RSP MAX DRAWDOWN")
print("=" * 70)

rsp_data = yf.download("RSP", start="2003-01-01", progress=False)
close_col = 'Adj Close' if 'Adj Close' in rsp_data.columns else 'Close'
rsp_prices = rsp_data[close_col]
if hasattr(rsp_prices, 'columns'):
    rsp_prices = rsp_prices.iloc[:, 0]

if len(rsp_prices) > 0:
    cummax = rsp_prices.cummax()
    dd = (rsp_prices - cummax) / cummax
    max_dd = dd.min()
    max_dd_date = dd.idxmin()
    print(f"  RSP max drawdown: {max_dd*100:.2f}% on {max_dd_date.date()}")
    print(f"  CLAIM (风险量化 83d2b104): -59.92%")
    results['rsp_max_dd'] = max_dd * 100

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 70)
print("SUMMARY OF ALL VERIFICATIONS")
print("=" * 70)

for k, v in results.items():
    if isinstance(v, float):
        print(f"  {k}: {v:.2f}")
    else:
        print(f"  {k}: {v}")
