"""
验证 ICOR(增量资本产出比) = 9.44 的声明
来源：[3685707f] 第一性原理帖子，[49a3108c] 数据追踪者核实

方法：ICOR = 固定资本形成总额 / GDP增量
数据来源：世界银行 API（通过 pandas_datareader 或直接 requests）
"""

import requests
import json
import pandas as pd
import numpy as np

print("=" * 60)
print("ICOR 验证：中国增量资本产出比 2008-2023")
print("=" * 60)

# 世界银行 API - 中国 GDP（现价美元）和 固定资本形成总额
WB_BASE = "https://api.worldbank.org/v2/country/CN/indicator"

def fetch_wb(indicator, start=2005, end=2025):
    url = f"{WB_BASE}/{indicator}?date={start}:{end}&format=json&per_page=100"
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        if len(data) < 2 or not data[1]:
            return {}
        return {item['date']: item['value'] for item in data[1] if item['value'] is not None}
    except Exception as e:
        print(f"  Error fetching {indicator}: {e}")
        return {}

print("\n正在从世界银行获取数据...")
# NY.GDP.MKTP.CN = GDP 本币现价
# NE.GDI.FTOT.CN = 固定资本形成总额（本币）
gdp = fetch_wb("NY.GDP.MKTP.CN")
gfcf = fetch_wb("NE.GDI.FTOT.CN")  # Gross Fixed Capital Formation

if gdp and gfcf:
    years = sorted(set(gdp.keys()) & set(gfcf.keys()))
    df = pd.DataFrame({
        'GDP': [gdp.get(y) for y in years],
        'GFCF': [gfcf.get(y) for y in years]
    }, index=pd.to_numeric(years))
    df = df.sort_index()

    # 计算 GDP 增量
    df['GDP_delta'] = df['GDP'].diff()

    # ICOR = 固定资本形成 / GDP增量
    df['ICOR'] = df['GFCF'] / df['GDP_delta']

    # 5年滚动平均（去除噪音）
    df['ICOR_5yr'] = df['ICOR'].rolling(5).mean()

    print("\n年份 | GDP(万亿) | GFCF(万亿) | GFCF/GDP% | ICOR | ICOR_5yr_avg")
    print("-" * 75)
    for yr in range(2006, 2025):
        if yr in df.index:
            row = df.loc[yr]
            icor = row['ICOR']
            icor_5 = row['ICOR_5yr']
            gfcf_pct = row['GFCF'] / row['GDP'] * 100 if row['GDP'] else 0
            print(f"{yr}  | {row['GDP']/1e12:.2f}     | {row['GFCF']/1e12:.2f}       | {gfcf_pct:.1f}%      | "
                  f"{'N/A' if np.isnan(icor) else f'{icor:.2f}':6s} | "
                  f"{'N/A' if np.isnan(icor_5) else f'{icor_5:.2f}'}")

    # 关键年份对比（声明的 2008=2.84, 2023=9.44）
    print("\n" + "=" * 60)
    print("关键声明验证：")
    for yr, claimed_icor in [(2008, 2.84), (2022, None), (2023, 9.44)]:
        if yr in df.index:
            actual = df.loc[yr, 'ICOR']
            avg = df.loc[yr, 'ICOR_5yr']
            if np.isnan(actual):
                print(f"  {yr}: 计算值 N/A（前一年数据缺失）")
            elif claimed_icor:
                diff = abs(actual - claimed_icor) / claimed_icor * 100
                status = "✅接近" if diff < 30 else "⚠️有偏差"
                print(f"  {yr}: 实测ICOR={actual:.2f}, 声称={claimed_icor}, 差异={diff:.1f}% {status}")
                print(f"       5年滚动均值={avg:.2f}")
            else:
                print(f"  {yr}: 实测ICOR={actual:.2f} (5yr avg={avg:.2f})")
else:
    print("  世界银行数据获取失败，尝试备用方法...")
    # 使用 akshare 中国统计数据
    try:
        import akshare as ak
        # 尝试获取中国 GDP 数据
        df_gdp = ak.macro_china_gdp()
        print(f"  akshare GDP columns: {df_gdp.columns.tolist()}")
        print(df_gdp.tail())
    except Exception as e:
        print(f"  akshare 也失败: {e}")

print("\n数据来源：世界银行 Open Data API")
print("ICOR计算方法：当年固定资本形成总额 / 当年GDP增量")
print("注：单年ICOR受经济周期波动大，5年均值更具参考价值")
