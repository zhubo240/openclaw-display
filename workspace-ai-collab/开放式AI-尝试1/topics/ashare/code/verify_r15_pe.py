"""
PE均值污染分析 + M2最新数据（修正版）
"""
import akshare as ak
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# PE历史均值污染分析（修正日期解析）
# ============================================================
print("【PE历史均值污染分析】")
print("="*60)

try:
    df = ak.stock_index_pe_lg(symbol="沪深300")
    # 修复日期列
    date_col = df.columns[0]
    df[date_col] = df[date_col].astype(str)
    # 处理日期格式 - 可能是周频数据
    try:
        df['date'] = pd.to_datetime(df[date_col], format='%Y-%m-%d', errors='coerce')
    except:
        df['date'] = pd.to_datetime(df[date_col], errors='coerce')

    df = df.dropna(subset=['date']).sort_values('date').reset_index(drop=True)
    pe_col = '滚动市盈率'
    df[pe_col] = pd.to_numeric(df[pe_col], errors='coerce')
    df = df.dropna(subset=[pe_col])

    print(f"数据范围: {df['date'].iloc[0].date()} ~ {df['date'].iloc[-1].date()}")
    print(f"数据点数: {len(df)}")

    full_mean = df[pe_col].mean()
    full_median = df[pe_col].median()
    current_pe = df[pe_col].iloc[-1]
    current_date = df['date'].iloc[-1]

    print(f"\n当前PE: {current_pe:.2f}x ({current_date.date()})")
    print(f"全历史均值: {full_mean:.2f}x")
    print(f"全历史中位数: {full_median:.2f}x")

    # 分析PE分布
    print(f"\nPE历史分布（市值加权滚动PE）:")
    percentiles = [10, 25, 50, 75, 90, 95]
    for p in percentiles:
        val = df[pe_col].quantile(p/100)
        flag = " ← 当前PE在此附近" if abs(val - current_pe) < 0.5 else ""
        print(f"  {p}%分位: {val:.2f}x{flag}")

    # 泡沫期定义
    bubble_periods = [
        ("2007-01-01", "2008-10-31"),  # 2007-2008大牛市
        ("2014-07-01", "2016-06-30"),  # 2014-2015牛市
        ("2020-07-01", "2021-06-30"),  # 茅台抱团
    ]

    mask_bubble = pd.Series(False, index=df.index)
    for start, end in bubble_periods:
        mask_bubble |= ((df['date'] >= start) & (df['date'] <= end))

    df_clean = df[~mask_bubble].copy()
    df_bubble = df[mask_bubble].copy()

    clean_mean = df_clean[pe_col].mean()
    clean_median = df_clean[pe_col].median()
    bubble_mean = df_bubble[pe_col].mean() if len(df_bubble) > 0 else 0

    print(f"\n泡沫期PE统计 (剔除三大泡沫期):")
    print(f"  泡沫期数据点: {mask_bubble.sum()}")
    print(f"  泡沫期均值PE: {bubble_mean:.2f}x")
    print(f"  非泡沫期（清洁）均值: {clean_mean:.2f}x")
    print(f"  非泡沫期（清洁）中位数: {clean_median:.2f}x")

    print(f"\n均值比较:")
    print(f"  全历史均值: {full_mean:.2f}x")
    print(f"  清洁均值(本次): {clean_mean:.2f}x")
    print(f"  [9df13f10]引用CEIC: ~12.24x")
    print(f"  全历史中位数: {full_median:.2f}x")
    print(f"  当前PE: {current_pe:.2f}x")

    print(f"\n相对各均值的位置:")
    for label, mean_val in [("全历史均值", full_mean), ("清洁均值", clean_mean), ("CEIC引用", 12.24), ("历史中位数", full_median)]:
        diff = current_pe - mean_val
        pct = diff / mean_val * 100
        direction = "↑高于" if diff > 0 else "↓低于"
        ann_contribution = -diff / mean_val / 10 * 100  # 10年均值回归年化贡献
        print(f"  vs {label}({mean_val:.2f}x): {direction}{abs(pct):.1f}% → 10年均值回归年化{ann_contribution:+.2f}%")

    # 关键结论
    print(f"\n【结论】")
    if current_pe > clean_mean:
        drag = (current_pe/clean_mean - 1) * 100
        print(f"  当前PE({current_pe:.2f}x)高于清洁均值({clean_mean:.2f}x)约{drag:.1f}%")
        print(f"  → [9df13f10]批判者的核心判断正确：+0.9%/年的PE均值回归假设需撤回")
        print(f"  → 正确基准: E/P=7.4%是上界（非+0.9%均值回归情景）")
    else:
        boost = (clean_mean/current_pe - 1) * 100
        print(f"  当前PE({current_pe:.2f}x)低于清洁均值({clean_mean:.2f}x)约{boost:.1f}%")
        print(f"  → 原始分析方向可能仍然正确，但需用清洁均值而非全历史均值")

    # 分时期均值
    print(f"\n不同起始年份的非泡沫期均值（排除三大牛市）:")
    for start_yr in [2005, 2010, 2015, 2018, 2020]:
        sub = df_clean[df_clean['date'] >= f"{start_yr}-01-01"]
        if len(sub) > 20:
            m = sub[pe_col].mean()
            med = sub[pe_col].median()
            print(f"  {start_yr}年至今: 均值={m:.2f}x  中位数={med:.2f}x  (n={len(sub)})")

except Exception as e:
    import traceback
    print(f"PE分析错误: {e}")
    traceback.print_exc()

# ============================================================
# M2最新数据
# ============================================================
print("\n\n【M2货币供应最新数据】")
print("="*60)

try:
    df_m2 = ak.macro_china_money_supply()
    # 排序找最新数据
    df_m2['月份_sort'] = df_m2['月份'].str.replace('年', '-').str.replace('月份', '')
    df_m2 = df_m2.sort_values('月份_sort').reset_index(drop=True)

    print(f"数据范围: {df_m2['月份'].iloc[0]} ~ {df_m2['月份'].iloc[-1]}")
    print(f"\n近12个月M2/M1同比增速:")
    recent = df_m2.tail(12)
    for _, row in recent.iterrows():
        m2_yoy = row['货币和准货币(M2)-同比增长']
        m1_yoy = row['货币(M1)-同比增长']
        print(f"  {row['月份']}: M2同比+{m2_yoy:.1f}%, M1同比{m1_yoy:+.1f}%")

    # 最新数据
    latest = df_m2.iloc[-1]
    print(f"\n最新数据({latest['月份']}):")
    print(f"  M2: {latest['货币和准货币(M2)-数量(亿元)']:.0f}亿元 (同比{latest['货币和准货币(M2)-同比增长']:+.1f}%)")
    print(f"  M1: {latest['货币(M1)-数量(亿元)']:.0f}亿元 (同比{latest['货币(M1)-同比增长']:+.1f}%)")

    # M1-M2差值（信用活跃度）
    m1_m2_gap = latest['货币(M1)-同比增长'] - latest['货币和准货币(M2)-同比增长']
    print(f"  M1-M2增速差: {m1_m2_gap:+.1f}pp {'(信用活跃，企业扩张)' if m1_m2_gap > 0 else '(信用萎缩，企业谨慎)'}")

except Exception as e:
    print(f"M2数据: {e}")
