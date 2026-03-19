"""
第3轮代码验证：验证论坛中多个agent的量化声明
验证目标：
1. JEPI上行/下行捕获率 (风险量化声称: 上行53%, 下行78%)
2. JEPI分红逐年变化 (组合构建声称: 2022→2024下降32%)
3. AMLP历史最大回撤 (多agent声称: -77%)
4. RSP vs SPY YTD分化 (多个不一致数字: +3.16%, +5.5%, +7.03%)
5. JEPI YTD总回报 vs 价格回报
6. 压力场景下资产相关性收敛 (风险量化声称: JEPI-SPY从0.85升至0.93)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("代码验证 第3轮 — 量化声明验证")
print("=" * 70)

# ============================================================
# 验证1: JEPI上行/下行捕获率
# ============================================================
print("\n" + "=" * 70)
print("验证1: JEPI上行/下行捕获率")
print("风险量化声称: 上行53%, 下行78%, 比率0.68")
print("=" * 70)

jepi = yf.download("JEPI", start="2022-05-20", end="2026-03-15", auto_adjust=True)
spy = yf.download("SPY", start="2022-05-20", end="2026-03-15", auto_adjust=True)

jepi_ret = jepi['Close'].pct_change().dropna()
spy_ret = spy['Close'].pct_change().dropna()

# Align dates
common = jepi_ret.index.intersection(spy_ret.index)
jepi_ret = jepi_ret.loc[common]
spy_ret = spy_ret.loc[common]

# Flatten if needed
if hasattr(jepi_ret, 'values') and jepi_ret.values.ndim > 1:
    jepi_ret = jepi_ret.iloc[:, 0]
if hasattr(spy_ret, 'values') and spy_ret.values.ndim > 1:
    spy_ret = spy_ret.iloc[:, 0]

# Monthly returns for capture ratio (standard method)
jepi_monthly = jepi_ret.resample('ME').apply(lambda x: (1+x).prod()-1)
spy_monthly = spy_ret.resample('ME').apply(lambda x: (1+x).prod()-1)

common_m = jepi_monthly.index.intersection(spy_monthly.index)
jepi_monthly = jepi_monthly.loc[common_m]
spy_monthly = spy_monthly.loc[common_m]

# NOTE: This is PRICE-ONLY capture ratio. JEPI pays large dividends
# so total return capture would be different.
up_months = spy_monthly > 0
down_months = spy_monthly < 0

upside_capture = jepi_monthly[up_months].mean() / spy_monthly[up_months].mean() * 100
downside_capture = jepi_monthly[down_months].mean() / spy_monthly[down_months].mean() * 100

print(f"JEPI上行捕获率 (价格回报): {upside_capture:.1f}%")
print(f"JEPI下行捕获率 (价格回报): {downside_capture:.1f}%")
print(f"上/下行比: {upside_capture/downside_capture:.2f}")
print(f"风险量化声称: 上行53%, 下行78%, 比率0.68")
print(f"注意: 以上是价格回报，不含分红。含分红的总回报捕获率会不同。")

# ============================================================
# 验证2: JEPI分红逐年变化
# ============================================================
print("\n" + "=" * 70)
print("验证2: JEPI年度分红 (组合构建声称: 2022=$6.25, 2023=$4.76, 2024=$4.25, 下降32%)")
print("=" * 70)

jepi_ticker = yf.Ticker("JEPI")
divs = jepi_ticker.dividends
if len(divs) > 0:
    divs.index = divs.index.tz_localize(None) if divs.index.tz else divs.index
    for year in [2022, 2023, 2024, 2025]:
        year_divs = divs[(divs.index >= f"{year}-01-01") & (divs.index < f"{year+1}-01-01")]
        if len(year_divs) > 0:
            total = year_divs.sum()
            print(f"  {year}: ${total:.2f}/股 ({len(year_divs)}次分红)")

    d2022 = divs[(divs.index >= "2022-01-01") & (divs.index < "2023-01-01")].sum()
    d2024 = divs[(divs.index >= "2024-01-01") & (divs.index < "2025-01-01")].sum()
    if d2022 > 0:
        pct_change = (d2024 - d2022) / d2022 * 100
        print(f"  2022→2024变化: {pct_change:.1f}%")
        print(f"  组合构建声称: -32%")

# ============================================================
# 验证3: AMLP历史最大回撤
# ============================================================
print("\n" + "=" * 70)
print("验证3: AMLP历史最大回撤 (多agent声称: -77%)")
print("=" * 70)

amlp = yf.download("AMLP", start="2014-01-01", end="2026-03-15", auto_adjust=True)
amlp_close = amlp['Close']
if amlp_close.values.ndim > 1:
    amlp_close = amlp_close.iloc[:, 0]

running_max = amlp_close.cummax()
drawdown = (amlp_close - running_max) / running_max
max_dd = drawdown.min()
max_dd_date = drawdown.idxmin()

# Find the peak before the max drawdown
peak_date = amlp_close.loc[:max_dd_date].idxmax()
peak_val = amlp_close.loc[peak_date]
trough_val = amlp_close.loc[max_dd_date]

print(f"AMLP最大回撤: {max_dd*100:.2f}%")
print(f"峰值: ${peak_val:.2f} ({peak_date.strftime('%Y-%m-%d')})")
print(f"谷底: ${trough_val:.2f} ({max_dd_date.strftime('%Y-%m-%d')})")
print(f"多agent声称: -77%")

# Recovery time
if max_dd_date is not None:
    recovery = amlp_close.loc[max_dd_date:]
    recovered = recovery[recovery >= peak_val]
    if len(recovered) > 0:
        recovery_date = recovered.index[0]
        recovery_days = (recovery_date - max_dd_date).days
        print(f"恢复日期: {recovery_date.strftime('%Y-%m-%d')} ({recovery_days}天)")
    else:
        print(f"截至数据末尾尚未恢复至峰值${peak_val:.2f}")

# ============================================================
# 验证4: RSP vs SPY YTD分化
# ============================================================
print("\n" + "=" * 70)
print("验证4: RSP vs SPY 2026 YTD回报")
print("论坛各声明: RSP +3.16% / +5.5% / +7.03%, SPY -1.54%")
print("=" * 70)

rsp = yf.download("RSP", start="2025-12-31", end="2026-03-15", auto_adjust=True)
spy_ytd = yf.download("SPY", start="2025-12-31", end="2026-03-15", auto_adjust=True)

rsp_close = rsp['Close']
spy_close = spy_ytd['Close']
if rsp_close.values.ndim > 1:
    rsp_close = rsp_close.iloc[:, 0]
if spy_close.values.ndim > 1:
    spy_close = spy_close.iloc[:, 0]

rsp_ytd_ret = (rsp_close.iloc[-1] / rsp_close.iloc[0] - 1) * 100
spy_ytd_ret = (spy_close.iloc[-1] / spy_close.iloc[0] - 1) * 100
divergence = rsp_ytd_ret - spy_ytd_ret

print(f"RSP YTD价格回报: {rsp_ytd_ret:.2f}%")
print(f"SPY YTD价格回报: {spy_ytd_ret:.2f}%")
print(f"分化 (RSP - SPY): {divergence:.2f}个百分点")
print(f"论坛声明对比:")
print(f"  种子材料: RSP +3.16%, SPY -1.54%, 分化4.7pp")
print(f"  估值分析: RSP +5.5%, SPY -0.2%, 分化5.7pp")
print(f"  风险量化: RSP +7.03%")

# ============================================================
# 验证5: JEPI YTD总回报 vs 价格回报
# ============================================================
print("\n" + "=" * 70)
print("验证5: JEPI 2026 YTD回报 (种子材料声称: 价格-0.4%, 总回报+4.29%)")
print("=" * 70)

jepi_ytd = yf.download("JEPI", start="2025-12-31", end="2026-03-15", auto_adjust=True)
jepi_ytd_close = jepi_ytd['Close']
if jepi_ytd_close.values.ndim > 1:
    jepi_ytd_close = jepi_ytd_close.iloc[:, 0]

jepi_price_ret = (jepi_ytd_close.iloc[-1] / jepi_ytd_close.iloc[0] - 1) * 100
print(f"JEPI YTD价格回报: {jepi_price_ret:.2f}%")
print(f"种子材料声称价格回报: -0.4%")

# Calculate with dividends
jepi_divs_ytd = divs[(divs.index >= "2026-01-01") & (divs.index <= "2026-03-15")]
div_total = jepi_divs_ytd.sum()
start_price = jepi_ytd_close.iloc[0]
total_ret = (jepi_ytd_close.iloc[-1] + div_total - start_price) / start_price * 100
print(f"JEPI 2026年已派发分红: ${div_total:.2f}/股")
print(f"JEPI YTD近似总回报: {total_ret:.2f}% (价格+分红简单加总)")
print(f"种子材料声称总回报: +4.29%")

# ============================================================
# 验证6: 资产间相关性 (正常 vs 压力)
# ============================================================
print("\n" + "=" * 70)
print("验证6: 资产间相关性 — 正常期 vs 2020年3月压力期")
print("风险量化声称: JEPI-SPY正常0.85, 压力0.93; AMLP-SPY正常0.45, 压力0.80+")
print("=" * 70)

# Normal period: 2023-01 to 2024-12
tickers = ["JEPI", "SPY", "AMLP", "TLT", "GLD"]
data = yf.download(tickers, start="2022-06-01", end="2026-03-15", auto_adjust=True)['Close']

# Flatten multi-level columns if needed
if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(-1)

rets = data.pct_change().dropna()

# Normal period
normal = rets.loc["2023-06-01":"2024-12-31"]
print("\n正常期 (2023-06 到 2024-12) 相关性矩阵:")
normal_corr = normal.corr()
for pair in [("JEPI", "SPY"), ("AMLP", "SPY"), ("TLT", "SPY"), ("GLD", "SPY")]:
    if pair[0] in normal_corr.columns and pair[1] in normal_corr.columns:
        print(f"  {pair[0]}-{pair[1]}: {normal_corr.loc[pair[0], pair[1]]:.3f}")

# Stress period: 2022 Q3 (rate hike shock) — JEPI wasn't around for 2020
stress = rets.loc["2022-09-01":"2022-10-31"]
print("\n压力期 (2022年9-10月加息恐慌) 相关性:")
stress_corr = stress.corr()
for pair in [("JEPI", "SPY"), ("AMLP", "SPY"), ("TLT", "SPY"), ("GLD", "SPY")]:
    if pair[0] in stress_corr.columns and pair[1] in stress_corr.columns:
        print(f"  {pair[0]}-{pair[1]}: {stress_corr.loc[pair[0], pair[1]]:.3f}")

# For AMLP-SPY during 2020 March (JEPI didn't exist)
print("\nAMLP-SPY 2020年3月压力期相关性:")
data_2020 = yf.download(["AMLP", "SPY"], start="2020-02-15", end="2020-04-15", auto_adjust=True)['Close']
if isinstance(data_2020.columns, pd.MultiIndex):
    data_2020.columns = data_2020.columns.get_level_values(-1)
rets_2020 = data_2020.pct_change().dropna()
corr_2020 = rets_2020.corr()
if "AMLP" in corr_2020.columns and "SPY" in corr_2020.columns:
    print(f"  AMLP-SPY (2020年2-4月): {corr_2020.loc['AMLP', 'SPY']:.3f}")

# ============================================================
# 验证7: 当前JEPI/AMLP股息率
# ============================================================
print("\n" + "=" * 70)
print("验证7: 当前股息率 (种子材料声称: JEPI ~8.34%, AMLP ~8.1%)")
print("=" * 70)

for ticker_sym in ["JEPI", "AMLP", "JEPQ"]:
    t = yf.Ticker(ticker_sym)
    info = t.info
    div_yield = info.get('dividendYield') or info.get('yield') or info.get('trailingAnnualDividendYield')
    price = info.get('previousClose') or info.get('regularMarketPrice')
    trailing_div = info.get('trailingAnnualDividendRate')
    print(f"{ticker_sym}:")
    print(f"  当前价格: ${price}")
    print(f"  过去12个月分红: ${trailing_div}")
    if div_yield:
        print(f"  股息率 (yfinance): {div_yield*100:.2f}%")
    elif trailing_div and price:
        print(f"  股息率 (计算): {trailing_div/price*100:.2f}%")

# ============================================================
# 验证8: VDE YTD回报
# ============================================================
print("\n" + "=" * 70)
print("验证8: VDE YTD回报 (种子材料声称: +25%)")
print("=" * 70)

vde = yf.download("VDE", start="2025-12-31", end="2026-03-15", auto_adjust=True)['Close']
if vde.values.ndim > 1:
    vde = vde.iloc[:, 0]
vde_ret = (vde.iloc[-1] / vde.iloc[0] - 1) * 100
print(f"VDE YTD价格回报: {vde_ret:.2f}%")
print(f"种子材料声称: +25%")

print("\n" + "=" * 70)
print("验证完成")
print("=" * 70)
