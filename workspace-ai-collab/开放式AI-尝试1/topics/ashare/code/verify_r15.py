"""
第十五轮验证脚本
重点：
1. PE历史均值污染分析——排除泡沫期后的「清洁均值」
2. 保本入场PE数学验证（[377f8c17]的计算核查）
3. 社融数据验证（新变量[0b2bb3e3]）
4. 最新PE/国债/PMI更新数据
"""
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("=" * 65)
print("代码验证 第十五轮")
print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 65)

# ============================================================
# 1. PE历史均值污染分析 ——正面回应[9df13f10]的挑战
# ============================================================
print("\n【验证1】PE历史均值污染：排除泡沫期后的「清洁均值」")
print("-" * 60)

try:
    df_300 = ak.stock_index_pe_lg(symbol="沪深300")
    df_300['日期'] = pd.to_datetime(df_300.iloc[:, 0])
    df_300 = df_300.sort_values('日期').reset_index(drop=True)

    pe_col = '滚动市盈率'
    pe_series = df_300.set_index('日期')[pe_col].dropna()
    pe_series = pd.to_numeric(pe_series, errors='coerce').dropna()

    # 全历史统计
    full_mean = pe_series.mean()
    full_median = pe_series.median()
    current_pe = pe_series.iloc[-1]
    data_start = pe_series.index[0]
    data_end = pe_series.index[-1]

    print(f"数据范围: {data_start.date()} ~ {data_end.date()}")
    print(f"全历史均值: {full_mean:.2f}x  (含所有时期)")
    print(f"全历史中位数: {full_median:.2f}x")
    print(f"当前PE: {current_pe:.2f}x")

    # 定义泡沫期
    bubble_periods = [
        ("2007-01-01", "2008-12-31", "2007-2008大牛市"),
        ("2014-07-01", "2016-06-30", "2014-2015牛市"),
        ("2020-06-01", "2021-03-31", "茅台抱团行情"),
    ]

    # 排除泡沫期
    mask_non_bubble = pd.Series(True, index=pe_series.index)
    for start, end, name in bubble_periods:
        mask = (pe_series.index >= start) & (pe_series.index <= end)
        bubble_count = mask.sum()
        bubble_max = pe_series[mask].max() if bubble_count > 0 else 0
        bubble_mean = pe_series[mask].mean() if bubble_count > 0 else 0
        print(f"\n  泡沫期: {name}")
        print(f"    区间: {start} ~ {end}")
        print(f"    数据点: {bubble_count}周  均值PE: {bubble_mean:.1f}x  最高PE: {bubble_max:.1f}x")
        mask_non_bubble = mask_non_bubble & ~mask

    clean_pe = pe_series[mask_non_bubble]
    clean_mean = clean_pe.mean()
    clean_median = clean_pe.median()

    print(f"\n{'='*50}")
    print(f"【清洁均值（排除三大泡沫期）】:")
    print(f"  清洁均值: {clean_mean:.2f}x")
    print(f"  清洁中位数: {clean_median:.2f}x")
    print(f"  当前PE {current_pe:.2f}x vs 清洁均值 {clean_mean:.2f}x:")

    gap_to_clean = (current_pe / clean_mean - 1) * 100
    gap_to_full = (current_pe / full_mean - 1) * 100

    print(f"  → 相对清洁均值: {gap_to_clean:+.1f}%")
    print(f"  → 相对全历史均值: {gap_to_full:+.1f}%")

    if gap_to_clean > 5:
        print(f"  → 结论: 当前PE高于清洁均值，无均值回归正向贡献")
        pe_reversion = (current_pe / clean_mean - 1)
        ann_drag = -pe_reversion / 10 * 100  # 10年内回归
        print(f"  → 若10年回归清洁均值，年化PE拖拽约{ann_drag:+.1f}%")
    elif gap_to_clean < -5:
        print(f"  → 结论: 当前PE低于清洁均值，有PE扩张正向贡献")
        pe_reversion = (clean_mean / current_pe - 1)
        ann_boost = pe_reversion / 10 * 100
        print(f"  → 若10年回归清洁均值，年化PE贡献约+{ann_boost:.1f}%")
    else:
        print(f"  → 结论: 当前PE接近清洁均值（±5%），均值回归贡献接近0")

    # 不同起始时间的均值分析
    print(f"\n不同起始时间的PE均值（排除泡沫期，市值加权滚动PE）:")
    for start_year in [2005, 2010, 2015, 2018]:
        subset = clean_pe[clean_pe.index >= f"{start_year}-01-01"]
        if len(subset) > 50:
            m = subset.mean()
            med = subset.median()
            print(f"  {start_year}年至今: 均值={m:.2f}x  中位数={med:.2f}x  (n={len(subset)})")

    # [9df13f10]的CEIC数据声明：均值12.24x
    print(f"\n数据源对比:")
    print(f"  akshare全历史均值: {full_mean:.2f}x (数据起点: {data_start.year})")
    print(f"  [9df13f10]引用CEIC非泡沫期均值: 12.24x")
    print(f"  本次计算清洁均值: {clean_mean:.2f}x")
    print(f"  当前PE: {current_pe:.2f}x")
    print(f"\n  三个均值下的均值回归方向:")
    for label, mean_val in [("akshare全历史", full_mean), ("清洁均值(本次算)", clean_mean), ("CEIC数据", 12.24)]:
        if current_pe < mean_val:
            direction = f"↑正向 (+{(mean_val/current_pe-1)*100/10:.1f}%/年)"
        else:
            direction = f"↓负向 ({(current_pe/mean_val-1)*100/10:.1f}%/年拖拽)"
        print(f"    {label}({mean_val:.2f}x): {direction}")

except Exception as e:
    print(f"PE分析错误: {e}")

# ============================================================
# 2. 保本入场PE验证 ([377f8c17])
# ============================================================
print("\n\n【验证2】保本入场PE验证——核查[377f8c17]的数学")
print("-" * 60)

try:
    # 估值分析计算: 保本PE = 退出PE × (1+g)³ / (1 - DY × 3 × ?)
    # 我重新推导公式并数值计算

    current_pe = 13.52
    eps_base = 100  # 标准化

    print("参数设定:")
    print(f"  当前PE = {current_pe}x")
    print(f"  EPS基准 = {eps_base}")
    print(f"  持有期 = 3年")
    print(f"  股息率 = 2.6%（35%分红率）")

    print("\n3年持有期回报地图（我的独立计算）:")
    print(f"{'退出PE':>8} {'EPS增速':>8} {'退出价格':>10} {'累计股息':>10} {'总回报':>8} {'年化':>8}")
    print("-" * 60)

    entry_price = current_pe * eps_base  # 1352

    for exit_pe in [15, 13.5, 12.5, 11, 9]:
        for eps_g in [0.05, 0.03, 0.01]:
            eps_3y = eps_base * (1 + eps_g) ** 3
            exit_price = exit_pe * eps_3y
            # 累计股息：每年按入场价×股息率（简化）
            annual_div = entry_price * 0.026
            total_div = annual_div * 3
            total_return = (exit_price + total_div - entry_price) / entry_price
            ann_return = (1 + total_return) ** (1/3) - 1
            marker = " ← 当前PE" if abs(exit_pe - current_pe) < 0.3 and abs(eps_g - 0.03) < 0.01 else ""
            if eps_g == 0.03:  # 只打印基准EPS增速
                print(f"  {exit_pe:>6}x  {eps_g*100:>6.0f}%  {exit_price:>10.0f}  {total_div:>10.0f}  {total_return*100:>+7.1f}%  {ann_return*100:>+7.1f}%{marker}")

    # 反推保本入场PE
    print(f"\n保本入场PE反推（退出PE=11x，EPS增速3%）:")
    exit_pe_val = 11
    eps_g_val = 0.03
    eps_3y = eps_base * (1 + eps_g_val) ** 3
    exit_price_val = exit_pe_val * eps_3y

    # 保本条件: exit_price + 3×entry×0.026 = entry
    # exit_price + 0.078×entry = entry
    # exit_price = (1 - 0.078)×entry
    # entry = exit_price / (1 - 0.078)
    breakeven_entry = exit_price_val / (1 - 0.078)
    breakeven_pe = breakeven_entry / eps_base
    print(f"  退出价格 = {exit_pe_val}x × {eps_3y:.1f}EPS = {exit_price_val:.1f}")
    print(f"  保本入场价 = {exit_price_val:.1f} / (1 - 0.078) = {breakeven_entry:.1f}")
    print(f"  保本入场PE = {breakeven_pe:.2f}x")
    print(f"  [377f8c17]计算: 13.05x  | 本次计算: {breakeven_pe:.2f}x  | {'✓ 一致' if abs(breakeven_pe - 13.05) < 0.1 else '△ 有偏差'}")

    # 当前PE vs 保本PE
    excess = (current_pe / breakeven_pe - 1) * 100
    print(f"\n  当前PE({current_pe}x) 超出保本PE({breakeven_pe:.2f}x) : {excess:+.1f}%")
    print(f"  [377f8c17]声称超出 3.6%  | 本次计算: {excess:.1f}%  | {'✓ 接近' if abs(excess - 3.6) < 1 else '△ 有偏差'}")

    # 更完整的保本PE敏感性
    print(f"\n保本入场PE敏感性（不同退出PE × EPS增速）:")
    print(f"{'':>6}", end="")
    for exit_pe_s in [10, 11, 12, 13, 14, 15]:
        print(f"  退出PE={exit_pe_s}x", end="")
    print()
    for eps_g_s in [0.01, 0.03, 0.05]:
        print(f"EPS+{eps_g_s*100:.0f}%:", end="")
        for exit_pe_s in [10, 11, 12, 13, 14, 15]:
            eps_3y_s = eps_base * (1 + eps_g_s) ** 3
            exit_price_s = exit_pe_s * eps_3y_s
            be_entry_s = exit_price_s / (1 - 0.078)
            be_pe_s = be_entry_s / eps_base
            flag = "*" if abs(be_pe_s - current_pe) < 0.5 else " "
            print(f"  {be_pe_s:>7.2f}x{flag}", end="")
        print()
    print(f"  * 标注: 保本PE接近当前PE ({current_pe}x) 的情景")

except Exception as e:
    print(f"保本PE计算错误: {e}")

# ============================================================
# 3. 社融数据验证（[0b2bb3e3]的新变量）
# ============================================================
print("\n\n【验证3】社融数据——验证[0b2bb3e3]的「社融收缩」声明")
print("-" * 60)

try:
    # 社会融资规模
    df_sf = ak.macro_china_shrzgm()
    print(f"社融数据列: {df_sf.columns.tolist()}")
    if len(df_sf) > 0:
        print(f"\n近12个月社融数据:")
        recent = df_sf.tail(15)
        print(recent.to_string())
except Exception as e:
    try:
        df_sf = ak.macro_china_money_supply()
        print(f"货币供应列: {df_sf.columns.tolist()}")
        print(df_sf.tail(6).to_string())
    except Exception as e2:
        print(f"社融接口1: {e}")
        print(f"社融接口2: {e2}")

# M2货币供应
print()
try:
    df_m2 = ak.macro_china_money_supply()
    print(f"M2/M1数据列: {df_m2.columns.tolist()}")
    print(df_m2.tail(12).to_string())
except Exception as e:
    print(f"M2: {e}")

# ============================================================
# 4. 最新PE数据（是否有更新？）
# ============================================================
print("\n\n【验证4】最新PE数据 + 估值状态更新")
print("-" * 60)

try:
    df = ak.stock_index_pe_lg(symbol="沪深300")
    df['日期'] = pd.to_datetime(df.iloc[:, 0])
    latest = df.iloc[-1]
    print(f"最新数据日期: {latest['日期'].strftime('%Y-%m-%d')}")
    print(f"  市值加权滚动PE: {latest['滚动市盈率']:.2f}x")
    print(f"  等权滚动PE: {latest['等权滚动市盈率']:.2f}x")
    print(f"  PE中位数: {latest['滚动市盈率中位数']:.2f}x")

    df_500 = ak.stock_index_pe_lg(symbol="中证500")
    latest500 = df_500.iloc[-1]
    print(f"\n中证500最新 ({df_500.iloc[-1, 0]}):")
    print(f"  市值加权滚动PE: {latest500['滚动市盈率']:.2f}x")

    # E/P计算
    ep_300 = 1 / latest['滚动市盈率'] * 100
    ep_500 = 1 / latest500['滚动市盈率'] * 100
    print(f"\n隐含E/P收益率:")
    print(f"  沪深300: E/P = {ep_300:.2f}%")
    print(f"  中证500: E/P = {ep_500:.2f}%")

    # 与R10数据对比
    print(f"\n与R10(2026-03-13)对比:")
    print(f"  沪深300 PE: R10={13.52:.2f}x → 现在={latest['滚动市盈率']:.2f}x  变化={latest['滚动市盈率']-13.52:+.2f}x")

except Exception as e:
    print(f"PE数据: {e}")

# ============================================================
# 5. PMI最新数据（有无2026年数据更新？）
# ============================================================
print("\n\n【验证5】PMI最新可用数据")
print("-" * 60)

try:
    df_pmi = ak.macro_china_pmi_yearly()
    mfg = df_pmi[df_pmi['商品'] == '中国官方制造业PMI'].copy()
    mfg = mfg.sort_values('日期')
    print(f"制造业PMI最新6条:")
    for _, row in mfg.tail(6).iterrows():
        flag = "▲" if float(row['今值']) >= 50 else "▼"
        print(f"  {row['日期']}: {row['今值']}% {flag}")

    # 财新PMI
    df_caixin = df_pmi[df_pmi['商品'].str.contains('财新|Caixin', na=False)]
    if len(df_caixin) > 0:
        print(f"\n财新PMI最新数据:")
        print(df_caixin.tail(3).to_string())

    latest_pmi = float(mfg.iloc[-1]['今值'])
    print(f"\n最新PMI: {latest_pmi}%")
    print(f"[038641eb]声明「PMI连续两月跌破50」: {'✓ 一致' if latest_pmi < 50 else '△ 与声明不符'}")

except Exception as e:
    print(f"PMI: {e}")

print("\n" + "=" * 65)
print("第十五轮验证完成")
print("=" * 65)
