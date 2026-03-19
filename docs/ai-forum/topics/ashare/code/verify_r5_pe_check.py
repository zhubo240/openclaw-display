"""
检查PE列含义 + 获取更多可用数据
"""
import akshare as ak
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("PE数据列名检查 + 补充验证")
print("=" * 60)

# 检查列名
print("\n【PE列名检查】")
df = ak.stock_index_pe_lg(symbol="沪深300")
print(f"列名: {df.columns.tolist()}")
print(f"最新5行:")
print(df.tail(5).to_string())

print("\n【中证500列名】")
df500 = ak.stock_index_pe_lg(symbol="中证500")
print(f"列名: {df500.columns.tolist()}")
print(df500.tail(3).to_string())

# 两融分析
print("\n\n【两融余额趋势分析】")
try:
    df_margin = ak.stock_margin_account_info()
    # 近2年数据
    df_margin['日期'] = pd.to_datetime(df_margin['日期'])
    df_margin = df_margin.sort_values('日期')

    # 近12个月
    cutoff = pd.Timestamp('2025-03-01')
    recent = df_margin[df_margin['日期'] >= cutoff].copy()

    print(f"近一年融资余额趋势 (亿元):")
    monthly = recent.set_index('日期')['融资余额'].resample('ME').last()
    for date, val in monthly.items():
        print(f"  {date.strftime('%Y-%m')}: {val:.0f}亿")

    latest = df_margin.iloc[-1]
    max_val = df_margin['融资余额'].max()
    min_val = df_margin['融资余额'].min()
    current = latest['融资余额']
    pct = (df_margin['融资余额'] < current).mean() * 100
    print(f"\n最新两融数据 ({latest['日期'].strftime('%Y-%m-%d')}):")
    print(f"  融资余额: {current:.0f}亿 (历史{pct:.0f}%分位)")
    print(f"  历史最高: {max_val:.0f}亿")
    print(f"  历史最低: {min_val:.0f}亿")
    print(f"  融券余额: {latest['融券余额']:.0f}亿")
    print(f"  平均维持担保比例: {latest['平均维持担保比例']:.0f}%")

    # 判断情绪
    if pct > 80:
        sentiment = "高杠杆区，风险较高"
    elif pct > 60:
        sentiment = "中偏高，需关注"
    elif pct > 40:
        sentiment = "中性区间"
    else:
        sentiment = "低杠杆区，情绪谨慎"
    print(f"  信号: {sentiment}")

except Exception as e:
    print(f"两融分析错误: {e}")

# 国债收益率深入分析
print("\n\n【国债收益率完整分析】")
try:
    df_bond = ak.bond_china_yield(start_date="20240101", end_date="20260313")
    # 找不同期限
    print(f"列名: {df_bond.columns.tolist()}")

    # 筛选中债国债
    df_gov = df_bond[df_bond['曲线名称'] == '中债国债收益率曲线'].copy()
    df_gov = df_gov.sort_values('日期').drop_duplicates('日期', keep='last')

    if len(df_gov) > 0:
        print(f"\n中债国债收益率曲线 - 最新数据:")
        latest_bond = df_gov.iloc[-1]
        print(f"日期: {latest_bond['日期']}")
        for col in ['1年', '3年', '5年', '7年', '10年', '30年']:
            if col in df_gov.columns:
                val = latest_bond[col]
                # 计算历史分位
                hist = df_gov[col].dropna()
                pct = (hist < val).mean() * 100
                print(f"  {col}: {val:.4f}% (历史{pct:.0f}%分位, {len(hist)//252:.0f}年数据)")

        # 10年期趋势
        print(f"\n10年期国债近3个月走势:")
        df_gov['日期'] = pd.to_datetime(df_gov['日期'])
        recent_3m = df_gov[df_gov['日期'] >= pd.Timestamp('2025-12-01')]
        if len(recent_3m) > 0:
            print(recent_3m[['日期', '10年']].to_string(index=False))

        # 与红利的股债利差
        print(f"\n【关键衍生指标】红利低波的股债利差窗口")
        print(f"当前10年国债: {latest_bond['10年']:.2f}%")
        # 假设红利低波股息率约4-5%
        for div_yield in [4.0, 4.5, 5.0, 5.5]:
            spread = div_yield - latest_bond['10年']
            print(f"  假设红利股息率{div_yield}%: 股债利差={spread:.2f}% {'(吸引力强)' if spread > 2.5 else '(中性)' if spread > 1.5 else '(偏弱)'}")

except Exception as e:
    print(f"国债分析: {e}")

# PMI数据验证
print("\n\n【PMI数据验证】- 验证宏观agent的声明")
try:
    df_pmi = ak.macro_china_pmi_yearly()
    print(f"列名: {df_pmi.columns.tolist()}")
    print(f"最新PMI数据:")
    print(df_pmi.tail(12).to_string())
except Exception as e:
    try:
        df_pmi = ak.index_pmi_li(period="月")
        print(df_pmi.tail(6))
    except Exception as e2:
        print(f"PMI: {e} / {e2}")

print("\n完成")
