"""
验证宏观分析师和链上研究员关于BTC-DXY负相关的声明
以及BTC在MPT组合中的夏普比率贡献
"""
import yfinance as yf
import pandas as pd
import numpy as np

print("=" * 60)
print("BTC-DXY相关性验证")
print("=" * 60)

# 下载数据
print("\n正在下载数据...")
btc = yf.download("BTC-USD", start="2020-01-01", end="2026-03-01", progress=False)
dxy = yf.download("DX-Y.NYB", start="2020-01-01", end="2026-03-01", progress=False)  # DXY
gold = yf.download("GC=F", start="2020-01-01", end="2026-03-01", progress=False)
sp500 = yf.download("^GSPC", start="2020-01-01", end="2026-03-01", progress=False)

if btc.empty or dxy.empty:
    print("数据下载失败，使用模拟数据进行演示")
    # 生成合理的模拟数据
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", "2026-03-01", freq='D')
    n = len(dates)
    btc_price = 10000 * np.exp(np.cumsum(np.random.normal(0.002, 0.04, n)))
    dxy_price = 100 * np.exp(np.cumsum(np.random.normal(0.0001, 0.003, n)))
    btc_returns = pd.Series(np.diff(np.log(btc_price)), index=dates[1:])
    dxy_returns = pd.Series(np.diff(np.log(dxy_price)), index=dates[1:])
else:
    # 使用Close价格，处理MultiIndex
    if isinstance(btc.columns, pd.MultiIndex):
        btc_close = btc['Close']['BTC-USD']
        dxy_close = dxy['Close']['DX-Y.NYB'] if 'DX-Y.NYB' in dxy['Close'].columns else dxy['Close'].iloc[:, 0]
        gold_close = gold['Close']['GC=F'] if 'GC=F' in gold['Close'].columns else gold['Close'].iloc[:, 0]
        sp500_close = sp500['Close']['^GSPC'] if '^GSPC' in sp500['Close'].columns else sp500['Close'].iloc[:, 0]
    else:
        btc_close = btc['Close']
        dxy_close = dxy['Close']
        gold_close = gold['Close']
        sp500_close = sp500['Close']

    # 日收益率
    btc_returns = btc_close.pct_change().dropna()
    dxy_returns = dxy_close.pct_change().dropna()
    gold_returns = gold_close.pct_change().dropna()
    sp500_returns = sp500_close.pct_change().dropna()

    # 对齐
    combined = pd.DataFrame({'BTC': btc_returns, 'DXY': dxy_returns,
                              'Gold': gold_returns, 'SP500': sp500_returns}).dropna()

    print(f"\n数据范围：{combined.index[0].strftime('%Y-%m-%d')} 至 {combined.index[-1].strftime('%Y-%m-%d')}")
    print(f"有效数据点：{len(combined)} 天")

    # 全期相关性
    corr_matrix = combined.corr()
    print("\n全期（2020-2026年初）相关性矩阵：")
    print(corr_matrix.round(3).to_string())

    btc_dxy_corr = corr_matrix.loc['BTC', 'DXY']
    btc_sp500_corr = corr_matrix.loc['BTC', 'SP500']
    btc_gold_corr = corr_matrix.loc['BTC', 'Gold']

    print(f"\nBTC-DXY相关性：{btc_dxy_corr:.3f}")
    print(f"宏观分析师声明：BTC-DXY历史负相关 {'✅ 验证' if btc_dxy_corr < 0 else '❌ 不成立'}")
    print(f"\nBTC-SP500相关性：{btc_sp500_corr:.3f}")
    print(f"宏观分析师声明：0.35-0.75（压力期）")

    print(f"\nBTC-黄金相关性：{btc_gold_corr:.3f}")
    print(f"宏观分析师声明：-0.17（当前） {'✅' if abs(btc_gold_corr - (-0.17)) < 0.15 else '⚠️ 偏差较大'}")

    # 滚动相关性分析（更准确）
    print("\n" + "=" * 60)
    print("不同时期BTC-DXY滚动相关性（90日窗口）")
    print("=" * 60)

    rolling_corr = combined['BTC'].rolling(90).corr(combined['DXY'])

    periods = {
        "2021 BTC牛市": ("2021-01-01", "2021-12-31"),
        "2022 熊市": ("2022-01-01", "2022-12-31"),
        "2023 复苏": ("2023-01-01", "2023-12-31"),
        "2024 ETF后": ("2024-01-01", "2024-12-31"),
        "2025-2026": ("2025-01-01", "2026-02-28"),
    }

    print(f"\n{'时期':>15} | {'平均相关性':>12} | {'含义':>20}")
    print("-" * 52)
    for period_name, (start, end) in periods.items():
        period_data = rolling_corr.loc[start:end]
        if len(period_data) > 0:
            avg_corr = period_data.mean()
            corr_str = f"{avg_corr:.3f}"
            if avg_corr < -0.3:
                meaning = "强负相关（BTC避险）"
            elif avg_corr < 0:
                meaning = "弱负相关"
            elif avg_corr < 0.3:
                meaning = "弱正相关"
            else:
                meaning = "强正相关（BTC风险资产）"
            print(f"{period_name:>15} | {corr_str:>12} | {meaning:>20}")

    # 压力期相关性（VIX高时）
    print("\n" + "=" * 60)
    print("BTC-SP500在压力期的相关性（月度数据）")
    print("=" * 60)

    # 月度数据计算
    monthly = combined.resample('ME').last().pct_change().dropna()
    btc_sp500_monthly = monthly['BTC'].corr(monthly['SP500'])
    print(f"\n月度BTC-SP500相关性（全期）：{btc_sp500_monthly:.3f}")

    # 识别下跌月份（SP500跌超3%）
    stress_months = monthly[monthly['SP500'] < -0.03]
    if len(stress_months) > 0:
        btc_sp500_stress = stress_months['BTC'].corr(stress_months['SP500'])
        print(f"压力月（SP500月跌>3%）的BTC-SP500相关性：{btc_sp500_stress:.3f}")
        print(f"宏观分析师声明「压力期相关性0.35-0.75」：{'✅ 基本验证' if 0.3 < btc_sp500_stress < 0.8 else '⚠️ 需验证'}")

    print("\n" + "=" * 60)
    print("BTC波动率验证")
    print("=" * 60)

    btc_annual_vol = btc_returns.std() * np.sqrt(252)
    print(f"\nBTC年化波动率（日收益率）：{btc_annual_vol*100:.1f}%")
    print(f"宏观分析师声明：~65% {'✅' if 55 < btc_annual_vol*100 < 75 else '⚠️'}")

    # 最近2年波动率
    btc_recent_vol = btc_returns.loc["2024-01-01":].std() * np.sqrt(252)
    print(f"2024年至今BTC年化波动率：{btc_recent_vol*100:.1f}%")

    print("\n" + "=" * 60)
    print("结论")
    print("=" * 60)
    print(f"""
BTC-DXY相关性：{btc_dxy_corr:.3f}
{'✅ 宏观分析师「BTC与DXY历史负相关」声明基本成立' if btc_dxy_corr < 0 else '❌ 相关性为正，与声明不符'}

BTC-SP500相关性：{btc_sp500_corr:.3f}（全期日度数据）
注意：相关性不稳定，在不同时期差异显著
⚠️ 仅用单一数字描述BTC-SP500相关性会产生误导

BTC-黄金相关性：{btc_gold_corr:.3f}
{'声明-0.17偏差较大' if abs(btc_gold_corr - (-0.17)) > 0.1 else '与声明基本一致'}

BTC年化波动率：{btc_annual_vol*100:.1f}%（声明65%）
""")
