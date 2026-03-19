"""
代码验证：黄金波动率 + 黄金-实际利率相关性 + 朴素基线评分
验证论坛中的以下声明：
1. [f96b5ed4] 年化波动率约13.6%，日波动率0.86%
2. [23946b08] 黄金与实际利率相关性：2005-2021 = 84%，2022-2024 = 3-7%
3. [ba1ca5b6] 朴素基线在FutureX评分公式下黄金约得51/100
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy import stats
from scipy.integrate import quad
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("代码验证：黄金波动率与实际利率相关性")
print("=" * 70)

# ============================================================
# 1. 黄金波动率验证
# ============================================================
print("\n### 1. 黄金波动率验证 ([f96b5ed4] 声明: 年化13.6%，日0.86%) ###\n")

gld = yf.download('GLD', start='2015-01-01', end='2026-01-01', progress=False, auto_adjust=True)
# Handle MultiIndex columns
if isinstance(gld.columns, pd.MultiIndex):
    gld_close = gld['Close']['GLD']
else:
    gld_close = gld['Close']

gold_ret = gld_close.pct_change().dropna()

# 分期间波动率
periods = {
    '2015-2019': ('2015-01-01', '2019-12-31'),
    '2020-2021': ('2020-01-01', '2021-12-31'),
    '2022-2023': ('2022-01-01', '2023-12-31'),
    '2024-2025': ('2024-01-01', '2025-12-31'),
    '10年全期': ('2015-01-01', '2025-12-31'),
}

print(f"{'期间':<20} {'年化波动率':>12} {'日波动率':>10}")
print("-" * 46)
for label, (start, end) in periods.items():
    mask = (gold_ret.index >= start) & (gold_ret.index <= end)
    sub = gold_ret[mask]
    ann_vol = float(np.std(sub, ddof=1)) * np.sqrt(252)
    daily_vol = float(np.std(sub, ddof=1))
    print(f"{label:<20} {ann_vol*100:>11.2f}%  {daily_vol*100:>9.3f}%")

# 10年全期
mask_all = (gold_ret.index >= '2015-01-01') & (gold_ret.index <= '2025-12-31')
sub_all = gold_ret[mask_all]
ann_vol_10yr = float(np.std(sub_all, ddof=1)) * np.sqrt(252)
daily_vol_10yr = float(np.std(sub_all, ddof=1))

# 滚动30日波动率均值
rolling_vol = gold_ret.rolling(30).std() * np.sqrt(252)
mean_rolling_vol = float(rolling_vol.mean())
print(f"\n10年滚动30日波动率均值: {mean_rolling_vol*100:.2f}%")
print(f"\n结论：")
print(f"  实测年化波动率 = {ann_vol_10yr*100:.2f}%  （声明：13.6%）")
print(f"  实测日波动率   = {daily_vol_10yr*100:.3f}% （声明：0.86%）")
if abs(ann_vol_10yr - 0.136) < 0.04:
    print("  ✅ 年化波动率声明基本准确（误差<4ppt）")
else:
    print(f"  ⚠️ 年化波动率偏差：实测{ann_vol_10yr*100:.1f}% vs 声明13.6%")

# ============================================================
# 2. 黄金-实际利率相关性验证
# ============================================================
print("\n\n### 2. 黄金-实际利率相关性验证 ([23946b08] 声明：84%→3-7%) ###\n")

# 使用FRED数据
try:
    import pandas_datareader.data as web
    tips_data = web.DataReader('DFII10', 'fred', '2004-01-01', '2025-12-31')
    tips_monthly = tips_data.resample('ME').last()
    tips_monthly.columns = ['real_rate']
    tips_source = "FRED DFII10（10年TIPS实际收益率，月末值）"
    use_level = True
except Exception as e:
    print(f"FRED获取失败 ({e})，改用TIP ETF")
    tip_data = yf.download('TIP', start='2004-01-01', end='2026-01-01', progress=False, auto_adjust=True)
    if isinstance(tip_data.columns, pd.MultiIndex):
        tip_close = tip_data['Close']['TIP']
    else:
        tip_close = tip_data['Close']
    tips_monthly = tip_close.resample('ME').last().to_frame()
    tips_monthly.columns = ['real_rate']
    tips_source = "TIP ETF月末收盘价（TIPS债券价格代理）"
    use_level = False

# 黄金月末价格
gold_monthly = gld_close.resample('ME').last()

# 合并数据
df = pd.DataFrame({'gold': gold_monthly, 'tips': tips_monthly['real_rate']}).dropna()

print(f"数据来源: {tips_source}")
print(f"数据区间: {df.index[0].date()} ~ {df.index[-1].date()}\n")

# 分期间相关性（水平值）
periods_corr = {
    '2005-2021 (声称 84%)': ('2005-01-01', '2021-12-31'),
    '2022-2024 (声称 3-7%)': ('2022-01-01', '2024-12-31'),
    '2005-2025 全期': ('2005-01-01', '2025-12-31'),
}

print("水平值相关性（黄金价格 vs TIPS利率/价格）：")
print(f"{'期间':<28} {'Pearson r':>10} {'p值':>10} {'n':>6}")
print("-" * 58)
for label, (start, end) in periods_corr.items():
    mask = (df.index >= start) & (df.index <= end)
    sub = df[mask].dropna()
    if len(sub) < 10:
        continue
    r, p = stats.pearsonr(sub['gold'], sub['tips'])
    print(f"{label:<28} {r:>10.3f}   {p:>9.4f}   {len(sub):>5}")

# 月度变化相关性
print("\n月度变化相关性（更稳健的方法）：")
df_chg = df.copy()
df_chg['gold_chg'] = df['gold'].pct_change()
if use_level:
    df_chg['tips_chg'] = df['tips'].diff()  # 利率水平差分（百分点变化）
else:
    df_chg['tips_chg'] = df['tips'].pct_change()  # ETF价格变化
df_chg = df_chg.dropna()

print(f"{'期间':<28} {'Pearson r':>10} {'p值':>10} {'n':>6}")
print("-" * 58)
for label, (start, end) in periods_corr.items():
    mask = (df_chg.index >= start) & (df_chg.index <= end)
    sub = df_chg[mask].dropna()
    if len(sub) < 10:
        continue
    r, p = stats.pearsonr(sub['gold_chg'], sub['tips_chg'])
    print(f"{label:<28} {r:>10.3f}   {p:>9.4f}   {len(sub):>5}")

# 声明验证
mask_0521 = (df_chg.index >= '2005-01-01') & (df_chg.index <= '2021-12-31')
mask_2224 = (df_chg.index >= '2022-01-01') & (df_chg.index <= '2024-12-31')
r_0521, p_0521 = stats.pearsonr(df_chg[mask_0521]['gold_chg'], df_chg[mask_0521]['tips_chg'])
r_2224, p_2224 = stats.pearsonr(df_chg[mask_2224]['gold_chg'], df_chg[mask_2224]['tips_chg'])

print(f"\n结论：")
print(f"  2005-2021 相关系数 = {r_0521:.3f}  （声明：+84% 或 -84%）")
print(f"  2022-2024 相关系数 = {r_2224:.3f}  （声明：3-7%）")
corr_drop = abs(r_0521) - abs(r_2224)
print(f"  相关性绝对值下降: {corr_drop:.3f}")
if abs(r_2224) < 0.2:
    print(f"  ✅ 相关性崩溃得到验证：2022后相关性确实接近零")
else:
    print(f"  ⚠️ 相关性下降，但不如声称的那么极端（r={r_2224:.3f}）")

# ============================================================
# 3. 朴素基线评分验证
# ============================================================
print("\n\n### 3. 朴素基线评分验证 ([ba1ca5b6] 声明：黄金~51/100) ###\n")
print("FutureX-Pro Finance评分公式：S = max(0, 1 - 20×|ΔP/P|)")
print("朴素基线：预测值=今日价格，误差=n天后的实际涨跌幅\n")

def expected_naive_score(daily_vol_val, n_days):
    """E[max(0, 1-20|x|)] where x ~ N(0, daily_vol^2 * n)"""
    sigma = daily_vol_val * np.sqrt(n_days)
    threshold = 1 / 20  # 5%容差
    def integrand(x):
        return (1 - 20 * abs(x)) * stats.norm.pdf(x, 0, sigma)
    result, _ = quad(integrand, -threshold, threshold)
    return result * 100

# 理论得分表格
print(f"{'资产':<22} {'日波动率':>8}  {'7天':>8}  {'15天':>8}  {'30天':>8}")
print("-" * 60)
assets_vol = [
    ('黄金(声明 0.86%/日)', 0.0086),
    (f'黄金(实测 {daily_vol_10yr*100:.3f}%/日)', daily_vol_10yr),
    ('S&P500大盘股 ~1.5%', 0.015),
    ('高波动科技股 ~2.5%', 0.025),
]
for name, vol in assets_vol:
    s7 = expected_naive_score(vol, 7)
    s15 = expected_naive_score(vol, 15)
    s30 = expected_naive_score(vol, 30)
    print(f"{name:<22} {vol*100:>7.3f}%  {s7:>8.1f}  {s15:>8.1f}  {s30:>8.1f}")

# 实际GLD数据验证
print(f"\n实际GLD历史数据验证（不同窗口期）：")
n_list = [5, 7, 10, 15, 20]
for n in n_list:
    rets = []
    prices = gld_close.values
    for i in range(len(prices) - n):
        r = (prices[i+n] - prices[i]) / prices[i]
        rets.append(float(r))
    scores = [max(0, 1 - 20 * abs(r)) * 100 for r in rets]
    mean_s = np.mean(scores)
    print(f"  n={n:2d}天: 平均得分 {mean_s:.1f}/100  (理论: {expected_naive_score(daily_vol_10yr, n):.1f})")

# 分期间15天朴素基线
print(f"\n分期间15天朴素基线实际得分：")
gld_prices = gld_close.values
gld_idx = gld_close.index
for label, (start, end) in [
    ('2015-2019 (平静期)', ('2015-01-01', '2019-12-31')),
    ('2020-2021 (疫情高波)', ('2020-01-01', '2021-12-31')),
    ('2022-2024 (高波期)', ('2022-01-01', '2024-12-31')),
]:
    mask = (gld_idx >= start) & (gld_idx <= end)
    idx_arr = np.where(mask)[0]
    scores = []
    for pos in idx_arr:
        if pos + 15 < len(gld_prices):
            r = float((gld_prices[pos+15] - gld_prices[pos]) / gld_prices[pos])
            scores.append(max(0, 1 - 20 * abs(r)) * 100)
    if scores:
        print(f"  {label:<25} {np.mean(scores):.1f}/100  (n={len(scores)})")

# 最终汇总
n15_scores = []
for i in range(len(gld_prices) - 15):
    r = float((gld_prices[i+15] - gld_prices[i]) / gld_prices[i])
    n15_scores.append(max(0, 1 - 20 * abs(r)) * 100)
actual_15d = np.mean(n15_scores)

print(f"\n### 结论汇总 ###\n")
print(f"黄金波动率：实测年化 {ann_vol_10yr*100:.1f}%，日 {daily_vol_10yr*100:.3f}%  （声明：13.6%，0.86%）")
print(f"实际利率相关性崩溃：{r_0521:.2f}→{r_2224:.2f}  （声明：84%→3-7%）")
print(f"朴素基线15天：实测 {actual_15d:.1f}/100  （声明：~51/100）")
print(f"GPT-5-high FutureX得分：46.37/100  vs  朴素基线：{actual_15d:.1f}/100")
print(f"Grok-4 FutureX得分：41.25/100  vs  朴素基线：{actual_15d:.1f}/100")

print("\n" + "=" * 70)
print("验证完成")
print("=" * 70)
