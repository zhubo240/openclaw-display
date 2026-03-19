"""
代码验证 - 第5轮验证脚本
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("代码验证第5轮 - 黄金论坛量化声明核查")
print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 60)

# ============================================
# 1. 金铜比 [2f5646b0] 声称 = 830，45年最高
# 定义: 黄金($/oz) ÷ 铜($/lb)
# ============================================
print("\n## 验证1：金铜比声称=830 [2f5646b0]")
print("-" * 40)

gold = yf.download("GC=F", period="3mo", interval="1d", progress=False)
copper = yf.download("HG=F", period="3mo", interval="1d", progress=False)

gold_price = float(gold['Close'].dropna().iloc[-1])
copper_price = float(copper['Close'].dropna().iloc[-1])  # $/lb

# 金铜比 = 黄金($/oz) / 铜($/lb)
gold_copper_ratio = gold_price / copper_price

print(f"当前金价: ${gold_price:.2f}/oz")
print(f"当前铜价: ${copper_price:.4f}/lb")
print(f"金铜比 = {gold_price:.2f} / {copper_price:.4f} = {gold_copper_ratio:.1f}")
print(f"声明值: 830")
if abs(gold_copper_ratio - 830) < 50:
    print(f"结论: ✅ 符合（实际={gold_copper_ratio:.0f}，声明=830）")
else:
    print(f"结论: ⚠️ 偏差: 实际={gold_copper_ratio:.0f} vs 声明=830")

# 历史金铜比
gold_hist = yf.download("GC=F", start="2020-01-01", end="2026-03-20", progress=False)['Close'].dropna()
copper_hist = yf.download("HG=F", start="2020-01-01", end="2026-03-20", progress=False)['Close'].dropna()
common_dates = gold_hist.index.intersection(copper_hist.index)
ratio_hist = gold_hist.loc[common_dates] / copper_hist.loc[common_dates]
max_ratio = ratio_hist.max()
max_date = ratio_hist.idxmax()
print(f"\n2020至今历史最高金铜比: {max_ratio:.1f} (日期: {pd.Timestamp(max_date).date()})")
print(f"2020至今历史最低金铜比: {ratio_hist.min():.1f}")
pct = (ratio_hist <= gold_copper_ratio).mean() * 100
print(f"当前({gold_copper_ratio:.0f})处于过去5年第{pct:.0f}百分位")

# ============================================
# 2. 金价回调幅度 [c755472d] vs [dbd9196e]
# ============================================
print("\n## 验证2：金价回调幅度")
print("-" * 40)

gold_1y = yf.download("GC=F", start="2025-09-01", end="2026-03-20", progress=False)['Close'].dropna()
current_price = float(gold_1y.iloc[-1])
peak_price = float(gold_1y.max())
peak_date = pd.Timestamp(gold_1y.idxmax()).date()
drawdown = (current_price - peak_price) / peak_price * 100

print(f"当前金价: ${current_price:,.0f}/oz")
print(f"近期高点: ${peak_price:,.0f}/oz ({peak_date})")
print(f"实际回调幅度: {drawdown:.1f}%")
print(f"")
print(f"[c755472d] 声称: 当前$4,573，从高点回调18.3%")
print(f"[dbd9196e] 声称: 当前$4,861，从$5,589回调约13%")

# 判断哪个更接近
err1 = abs(drawdown - (-18.3))
err2 = abs(drawdown - (-13))
print(f"")
if err1 < err2:
    print(f"→ [c755472d] 更接近实际（误差{err1:.1f}pp vs {err2:.1f}pp）")
    if err1 < 3: print(f"   结论: ✅")
    else: print(f"   结论: ⚠️ 偏差{err1:.1f}pp")
else:
    print(f"→ [dbd9196e] 更接近实际（误差{err2:.1f}pp vs {err1:.1f}pp）")
    if err2 < 3: print(f"   结论: ✅")
    else: print(f"   结论: ⚠️ 偏差{err2:.1f}pp")

# ============================================
# 3. GDX杠杆倍数 [c4dad77d]
# ============================================
print("\n## 验证3：GDX杠杆倍数声称2-3倍 [c4dad77d]")
print("-" * 40)

def get_leverage(start_date, label):
    gdx = yf.download("GDX", start=start_date, end="2026-03-20", progress=False)['Close'].dropna()
    gld = yf.download("GLD", start=start_date, end="2026-03-20", progress=False)['Close'].dropna()
    if len(gdx) < 5 or len(gld) < 5:
        print(f"{label}: 数据不足")
        return
    common = gdx.index.intersection(gld.index)
    gdx_ret = float(gdx.loc[common[-1]] / gdx.loc[common[0]] - 1) * 100
    gld_ret = float(gld.loc[common[-1]] / gld.loc[common[0]] - 1) * 100
    lev = gdx_ret / gld_ret if gld_ret != 0 else float('nan')
    print(f"{label}: GDX={gdx_ret:.1f}%, GLD={gld_ret:.1f}%, 杠杆={lev:.2f}x")
    return lev

l1 = get_leverage("2025-01-01", "2025年至今")
l2 = get_leverage("2026-01-01", "2026年以来")
l3 = get_leverage("2025-10-01", "近6个月")

if l1 and l2:
    if 1.5 <= l1 <= 3.5 or 1.5 <= l2 <= 3.5:
        print("结论: ✅ 某些时期符合2-3倍杠杆")
    else:
        print("结论: ❌ 实际杠杆与2-3倍声明偏差较大")

# ============================================
# 4. α框架验证 [ffaaca81] α = 10.4%
# P = (α × W_global) / S_gold
# ============================================
print("\n## 验证4：α框架 α=10.4% [ffaaca81]")
print("-" * 40)

P_gold = gold_price
# 215,000吨，每吨=32150.75 troy oz
S_gold_oz = 215000 * 32150.75
W_global = 500e12  # 500万亿美元（种子文件）

# 总市值
S_value = P_gold * S_gold_oz
alpha_calc = S_value / W_global * 100

print(f"金价: ${P_gold:,.0f}/oz")
print(f"存量: 215,000吨 = {S_gold_oz/1e9:.3f}十亿盎司")
print(f"黄金总市值: ${S_value/1e12:.2f}万亿")
print(f"全球金融资产: $500万亿（种子文件）")
print(f"计算得α = {alpha_calc:.1f}%")
print(f"声称α = 10.4%")

if abs(alpha_calc - 10.4) < 2:
    print(f"结论: ✅ 与声明值基本一致")
else:
    print(f"结论: ⚠️ 偏差{alpha_calc - 10.4:.1f}pp")

# 反推目标价
for alpha_target, label in [(10.4, "当前α=10.4%"), (15.0, "α=15%"), (20.0, "α=20%")]:
    P_target = alpha_target / 100 * W_global / S_gold_oz
    print(f"  {label} → 金价 = ${P_target:,.0f}/oz")

# ============================================
# 5. COMEX注册金仓储 [fa6a6708] 声称从1350万降至~1000万盎司(-25%)
# ============================================
print("\n## 验证5：COMEX注册金仓储 [fa6a6708]")
print("-" * 40)
print("声称: 从1350万盎司→约1000万盎司（-25%）")
print("数据来源: CME官网/Kitco，yfinance无法直接获取")
print("→ 无法通过公开API验证，需手动查CME COMEX报告")
print("→ 标记为 ⚠️ 无法自动验证（需人工核查）")

# ============================================
# 6. 2025年央行购金863吨 [3d2780f1]
# ============================================
print("\n## 验证6：2025年央行购金863吨 [3d2780f1]")
print("-" * 40)
print("数据来源: 世界黄金协会(WGC)")
print("声称: 2025年全球央行净购金约863吨，四年来首次跌破1000吨")
print("历史数据: 2022=1136吨, 2023=1037吨, 2024≈~1000吨, 2025=863吨")
print("WGC官方数据无法通过yfinance获取，需从WGC网站或Bloomberg获取")
print("→ ⚠️ 无法自动验证，依赖WGC数据")

print("\n" + "=" * 60)
print("验证汇总")
print("=" * 60)
print(f"实际金价: ${gold_price:,.0f}/oz | 铜价: ${copper_price:.4f}/lb")
print(f"金铜比(实测): {gold_copper_ratio:.0f} | 声明: 830")
print(f"金价回调(实测): {drawdown:.1f}% | 声明A:-18.3% 声明B:-13%")
print(f"α系数(实测): {alpha_calc:.1f}% | 声明: 10.4%")

