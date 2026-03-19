"""
最终验证 - 深入分析已获取的数据
"""
import akshare as ak
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("代码验证 第五轮 - 深入分析")
print("=" * 60)

# ============================================================
# 1. PE指标澄清 - 三种PE的历史分位数
# ============================================================
print("\n【核心发现1】PE指标澄清：论坛引用的是哪种PE？")
print("-" * 50)

for idx_name in ["沪深300", "中证500", "上证50"]:
    try:
        df = ak.stock_index_pe_lg(symbol=idx_name)
        latest = df.iloc[-1]

        def pct(series, val):
            return (series.dropna() < val).mean() * 100

        print(f"\n{idx_name} ({latest['日期']}):")
        print(f"  市值加权滚动PE:  {latest['滚动市盈率']:>6.2f}x  (历史{pct(df['滚动市盈率'], latest['滚动市盈率']):.0f}%分位)")
        print(f"  等权滚动PE:      {latest['等权滚动市盈率']:>6.2f}x  (历史{pct(df['等权滚动市盈率'], latest['等权滚动市盈率']):.0f}%分位)")
        print(f"  滚动PE中位数:    {latest['滚动市盈率中位数']:>6.2f}x  (历史{pct(df['滚动市盈率中位数'], latest['滚动市盈率中位数']):.0f}%分位)")
    except Exception as e:
        print(f"{idx_name}: {e}")

# ============================================================
# 2. 两融余额历史分位 - 深入分析
# ============================================================
print("\n\n【核心发现2】两融余额：99%分位警告！")
print("-" * 50)

try:
    df_margin = ak.stock_margin_account_info()
    df_margin['日期'] = pd.to_datetime(df_margin['日期'])
    df_margin = df_margin.sort_values('日期').reset_index(drop=True)

    current_val = df_margin['融资余额'].iloc[-1]
    hist_pct = (df_margin['融资余额'] < current_val).mean() * 100
    max_val = df_margin['融资余额'].max()
    max_date = df_margin.loc[df_margin['融资余额'].idxmax(), '日期']

    print(f"当前融资余额: {current_val:.0f}亿元")
    print(f"历史分位: {hist_pct:.1f}%分位")
    print(f"历史峰值: {max_val:.0f}亿元 ({max_date.strftime('%Y-%m-%d')})")
    print(f"距峰值: {max_val - current_val:.0f}亿元")

    # 关键历史节点对比
    print(f"\n历史关键节点融资余额:")
    key_dates = [
        ('2015-06-12', '牛市顶部'),
        ('2021-09-01', '2021年高点'),
        ('2024-09-01', '9月行情前'),
        ('2024-10-01', '9月行情后'),
        ('2025-01-01', '2025年初'),
        ('2026-01-01', '2026年初'),
    ]
    for date_str, label in key_dates:
        dt = pd.Timestamp(date_str)
        near = df_margin[df_margin['日期'] >= dt]
        if len(near) > 0:
            val = near.iloc[0]['融资余额']
            print(f"  {label}({date_str}): {val:.0f}亿")

    print(f"\n论坛声明 vs 实测:")
    print(f"  [933adeca]市场数据agent预测: '两融余额若突破28000亿是情绪升温信号'")
    print(f"  实测当前: {current_val:.0f}亿 (历史{hist_pct:.0f}%分位)")
    print(f"  ⚠️ 重要: 28000亿是'信号'，当前已在99%分位，远超市场情绪中性区")
    print(f"  → 融资余额高位是强制平仓风险的直接来源")

except Exception as e:
    print(f"两融分析: {e}")

# ============================================================
# 3. 国债收益率 - 红利股债利差计算
# ============================================================
print("\n\n【核心发现3】股债利差计算")
print("-" * 50)

try:
    df_bond = ak.bond_china_yield(start_date="20200101", end_date="20260313")
    df_gov = df_bond[df_bond['曲线名称'] == '中债国债收益率曲线'].copy()
    df_gov = df_gov.sort_values('日期').drop_duplicates('日期', keep='last')
    df_gov['日期'] = pd.to_datetime(df_gov['日期'])

    current_10y = df_gov['10年'].iloc[-1]
    latest_date = df_gov['日期'].iloc[-1]

    print(f"最新10年国债: {current_10y:.4f}% (日期: {latest_date.strftime('%Y-%m-%d')})")

    # 历史分位
    hist_10y = df_gov['10年'].dropna()
    pct_10y = (hist_10y < current_10y).mean() * 100
    print(f"历史分位: {pct_10y:.0f}%分位 (历史最低:{hist_10y.min():.2f}%, 最高:{hist_10y.max():.2f}%)")

    # 验证「距2.0%黄灯仅18bp」
    gap_to_2pct = 2.0 - current_10y
    print(f"\n验证论坛声明: '距2.0%红灯仅18bp'")
    print(f"  2.0% - {current_10y:.4f}% = {gap_to_2pct*100:.1f}bp")
    print(f"  → {'✓ 准确' if abs(gap_to_2pct*100 - 18) < 5 else '△ 有偏差'}")

    # 股债利差测算 (基于公开报告中512890约4.5%股息率)
    print(f"\n股债利差测算 (基于512890约4-5%股息率假设):")
    for div_yield in [4.0, 4.5, 5.0]:
        spread = div_yield - current_10y * 100
        # 历史百分位 - 用固定的利差计算
        print(f"  股息率{div_yield:.1f}%: 股债利差={spread:.2f}pp {'(极高，有吸引力)' if spread > 2.5 else '(中等)' if spread > 1.5 else '(低)'}")

    # 近3个月走势
    print(f"\n近3个月10年国债走势:")
    recent = df_gov[df_gov['日期'] >= pd.Timestamp('2025-12-01')]
    if len(recent) > 0:
        for _, row in recent.tail(15).iterrows():
            print(f"  {row['日期'].strftime('%Y-%m-%d')}: {row['10年']:.4f}%")

except Exception as e:
    print(f"国债分析: {e}")

# ============================================================
# 4. PMI深入分析
# ============================================================
print("\n\n【PMI验证】制造业景气度")
print("-" * 50)

try:
    df_pmi = ak.macro_china_pmi_yearly()
    mfg_pmi = df_pmi[df_pmi['商品'] == '中国官方制造业PMI'].copy()
    mfg_pmi = mfg_pmi.sort_values('日期')
    mfg_pmi['今值'] = pd.to_numeric(mfg_pmi['今值'], errors='coerce')

    print("近12个月制造业PMI:")
    recent_pmi = mfg_pmi.tail(12)
    for _, row in recent_pmi.iterrows():
        flag = "▲荣枯线上" if row['今值'] >= 50 else "▼荣枯线下"
        print(f"  {row['日期']}: {row['今值']:.1f} {flag}")

    above_50 = (recent_pmi['今值'] >= 50).sum()
    print(f"\n近12个月中: {above_50}个月在荣枯线以上，{12-above_50}个月在荣枯线以下")

    # 验证宏观agent声明
    latest_pmi = mfg_pmi.iloc[-1]
    print(f"\n验证 [8ad39193] 宏观声明: 'PMI整体在荣枯线附近，结构分化'")
    print(f"实测最新PMI: {latest_pmi['今值']:.1f} ({latest_pmi['日期']})")
    # Note: 数据只到2025-08，最新月度数据需要更新来源

except Exception as e:
    print(f"PMI: {e}")

print("\n" + "=" * 60)
print("分析完成")
print("=" * 60)
