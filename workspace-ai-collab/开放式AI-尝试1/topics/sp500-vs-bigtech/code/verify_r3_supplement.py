"""
补充验证:
1. 手动计算股息率
2. JEPI总回报捕获率 (含分红)
"""
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 补充1: 手动计算过去12个月股息率
# ============================================================
print("=" * 70)
print("补充验证1: 手动计算过去12个月股息率")
print("=" * 70)

for sym in ["JEPI", "AMLP", "JEPQ"]:
    t = yf.Ticker(sym)
    divs = t.dividends
    if len(divs) > 0:
        divs.index = divs.index.tz_localize(None) if divs.index.tz else divs.index
        # Last 12 months of dividends
        cutoff = pd.Timestamp("2025-03-15")
        recent_divs = divs[(divs.index >= cutoff) & (divs.index <= pd.Timestamp("2026-03-15"))]
        total_div = recent_divs.sum()

        # Get current price
        hist = yf.download(sym, start="2026-03-12", end="2026-03-15", auto_adjust=True)
        close = hist['Close']
        if close.values.ndim > 1:
            close = close.iloc[:, 0]
        price = close.iloc[-1]

        div_yield = total_div / price * 100
        print(f"{sym}: 过去12个月分红 ${total_div:.2f}, 当前价 ${price:.2f}, 股息率 {div_yield:.2f}%")

# ============================================================
# 补充2: JEPI总回报捕获率 (含分红再投资)
# ============================================================
print("\n" + "=" * 70)
print("补充验证2: JEPI总回报捕获率 (含分红)")
print("=" * 70)

# Use monthly total returns (price + dividends)
jepi_t = yf.Ticker("JEPI")
spy_t = yf.Ticker("SPY")

# Get history with dividends
jepi_hist = yf.download("JEPI", start="2022-05-20", end="2026-03-15", auto_adjust=False)
spy_hist = yf.download("SPY", start="2022-05-20", end="2026-03-15", auto_adjust=False)

# Calculate adjusted close (accounts for dividends)
jepi_adj = jepi_hist['Adj Close']
spy_adj = spy_hist['Adj Close']

if jepi_adj.values.ndim > 1:
    jepi_adj = jepi_adj.iloc[:, 0]
if spy_adj.values.ndim > 1:
    spy_adj = spy_adj.iloc[:, 0]

# Monthly total returns from adjusted close
jepi_monthly_tr = jepi_adj.resample('ME').last().pct_change().dropna()
spy_monthly_tr = spy_adj.resample('ME').last().pct_change().dropna()

common = jepi_monthly_tr.index.intersection(spy_monthly_tr.index)
jepi_monthly_tr = jepi_monthly_tr.loc[common]
spy_monthly_tr = spy_monthly_tr.loc[common]

up = spy_monthly_tr > 0
down = spy_monthly_tr < 0

up_capture_tr = jepi_monthly_tr[up].mean() / spy_monthly_tr[up].mean() * 100
down_capture_tr = jepi_monthly_tr[down].mean() / spy_monthly_tr[down].mean() * 100

print(f"JEPI总回报上行捕获率: {up_capture_tr:.1f}%")
print(f"JEPI总回报下行捕获率: {down_capture_tr:.1f}%")
print(f"上/下行比: {up_capture_tr/down_capture_tr:.2f}")
print(f"风险量化声称 (来源Morningstar): 上行53%, 下行78%, 比率0.68")
print()
print(f"价格回报捕获 vs 总回报捕获差异说明:")
print(f"  JEPI每月派息约$0.35-0.50, 这在上行月份降低价格回报的捕获,")
print(f"  在下行月份部分抵消亏损。总回报捕获才是准确衡量。")

# ============================================================
# 补充3: JEPI beta
# ============================================================
print("\n" + "=" * 70)
print("补充验证3: JEPI beta (风险量化声称: 0.59)")
print("=" * 70)

jepi_daily = jepi_adj.pct_change().dropna()
spy_daily = spy_adj.pct_change().dropna()
common_d = jepi_daily.index.intersection(spy_daily.index)
jepi_daily = jepi_daily.loc[common_d]
spy_daily = spy_daily.loc[common_d]

cov = np.cov(jepi_daily.values, spy_daily.values)
beta = cov[0, 1] / cov[1, 1]
print(f"JEPI beta (总回报): {beta:.3f}")
print(f"风险量化声称: 0.59")

# ============================================================
# 补充4: Shiller CAPE check via S&P 500 PE
# ============================================================
print("\n" + "=" * 70)
print("补充验证4: 估值数据交叉检查")
print("=" * 70)

spy_info = yf.Ticker("SPY").info
pe_spy = spy_info.get('trailingPE')
print(f"SPY trailing PE (yfinance): {pe_spy}")
print(f"多agent声称CAPE ~38.93, 标普PE ~27.5")
print(f"注意: CAPE是10年周期调整PE, 与trailing PE不同, yfinance无法直接获取CAPE")
