"""
代码验证 - 第10轮
重点核查：VIX冲突声明、S&P500 vs 200日均线、黄金暴跌幅度、日元汇率、初请
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("=" * 65)
print("代码验证 - 第10轮 量化声明核查")
print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 65)

end_date = datetime.now()
start_date = end_date - timedelta(days=90)  # 3 months for MA calculation

# ============================================================
# 1. VIX冲突声明核查
#    - 批判者 [325fb81f]: VIX 25.56
#    - 宏观周期 [1912a2fb]: VIX 24.06 (收盘), 盘中 25.80
# ============================================================
print("\n【1】VIX冲突声明核查")
print("-" * 45)
print("  声明A (批判者): VIX 25.56")
print("  声明B (宏观周期): VIX 24.06 (收盘), 盘中 25.80")

try:
    vix_data = yf.download("^VIX", start=(end_date - timedelta(days=10)).strftime('%Y-%m-%d'),
                           end=end_date.strftime('%Y-%m-%d'), progress=False)
    if not vix_data.empty:
        last5 = vix_data.tail(5)
        print(f"\n  最近5个交易日VIX数据:")
        for date, row in last5.iterrows():
            close = float(row['Close'])
            high = float(row['High'])
            low = float(row['Low'])
            print(f"    {date.strftime('%Y-%m-%d')}: 收盘={close:.2f}, 最高={high:.2f}, 最低={low:.2f}")

        latest_close = float(vix_data['Close'].iloc[-1])
        latest_date = vix_data.index[-1].strftime('%Y-%m-%d')
        print(f"\n  最新收盘: {latest_close:.2f} [{latest_date}]")

        # Check 3/20
        mar20 = vix_data[vix_data.index.strftime('%Y-%m-%d') == '2026-03-20']
        if not mar20.empty:
            c = float(mar20['Close'].iloc[0])
            h = float(mar20['High'].iloc[0])
            print(f"  3月20日: 收盘={c:.2f}, 盘中高={h:.2f}")
            if abs(c - 24.06) < 1:
                print(f"  ✅ 宏观周期声明'24.06收盘'基本准确 (实际{c:.2f})")
            else:
                print(f"  ❌ 宏观周期声明'24.06收盘'有偏差 (实际{c:.2f})")
            if abs(c - 25.56) < 1:
                print(f"  ✅ 批判者声明'25.56'基本准确")
            else:
                print(f"  ⚠️ 批判者声明'25.56'可能是盘中/前一天数据 (收盘{c:.2f})")
except Exception as e:
    print(f"  VIX数据错误: {e}")

# ============================================================
# 2. S&P500 vs 200日均线——宏观周期声明「跌破200日均线200点」
# ============================================================
print("\n【2】S&P500 vs 200日均线")
print("-" * 45)
print("  声明 (宏观周期): S&P500收6,606，跌破200日均线6,806(-200pts, -2.9%)")
print("  声明 (配置策略师): 200日均线破位")

try:
    spy_long = yf.download("SPY", start=(end_date - timedelta(days=300)).strftime('%Y-%m-%d'),
                           end=end_date.strftime('%Y-%m-%d'), progress=False)
    spx = yf.download("^GSPC", start=(end_date - timedelta(days=300)).strftime('%Y-%m-%d'),
                      end=end_date.strftime('%Y-%m-%d'), progress=False)

    for label, data in [("SPX (^GSPC)", spx), ("SPY ETF", spy_long)]:
        if not data.empty and len(data) >= 200:
            data = data.copy()
            data['MA200'] = data['Close'].rolling(200).mean()
            latest_price = float(data['Close'].iloc[-1])
            latest_ma200 = float(data['MA200'].iloc[-1])
            latest_date = data.index[-1].strftime('%Y-%m-%d')
            diff = latest_price - latest_ma200
            diff_pct = diff / latest_ma200 * 100
            above_below = "ABOVE" if diff > 0 else "BELOW"
            print(f"\n  {label} [{latest_date}]:")
            print(f"    当前价格: {latest_price:.2f}")
            print(f"    200日均线: {latest_ma200:.2f}")
            print(f"    差距: {diff:+.2f} ({diff_pct:+.2f}%) — {above_below}")

            # Check March 20
            mar20 = data[data.index.strftime('%Y-%m-%d') == '2026-03-20']
            if not mar20.empty:
                p = float(mar20['Close'].iloc[0])
                m = float(mar20['MA200'].iloc[0])
                d = p - m
                d_pct = d / m * 100
                state = "ABOVE" if d > 0 else "BELOW"
                print(f"    3月20日: 价格{p:.2f}, MA200={m:.2f}, 差距{d:+.2f}({d_pct:+.2f}%) — {state}")

                if label == "SPX (^GSPC)":
                    if d < -150 and d > -250:
                        print(f"    ✅ 宏观周期'跌破200日均线~200点'基本准确")
                    elif d < 0:
                        print(f"    ⚠️ 确实在200日均线下方，但差距{abs(d):.0f}pts与声明200pts有出入")
                    else:
                        print(f"    ❌ 尚在200日均线上方，声明错误")
except Exception as e:
    print(f"  S&P500数据错误: {e}")

# ============================================================
# 3. 黄金暴跌——批判者声明「从$5,589跌至$4,493 (-18.5%)」
# ============================================================
print("\n【3】黄金价格追踪")
print("-" * 45)
print("  声明 (批判者/黄金帖更新): $5,589→$4,493 (-18.5%)")

try:
    gold = yf.download("GC=F", start=(end_date - timedelta(days=180)).strftime('%Y-%m-%d'),
                       end=end_date.strftime('%Y-%m-%d'), progress=False)
    if not gold.empty:
        current = float(gold['Close'].iloc[-1])
        current_date = gold.index[-1].strftime('%Y-%m-%d')
        peak = float(gold['Close'].max())
        peak_date = gold['Close'].idxmax().strftime('%Y-%m-%d')
        trough = float(gold['Close'].min())
        trough_date = gold['Close'].idxmin().strftime('%Y-%m-%d')
        drawdown = (current - peak) / peak * 100

        print(f"  当前黄金价格: ${current:.2f} [{current_date}]")
        print(f"  近6个月峰值: ${peak:.2f} [{peak_date}]")
        print(f"  近6个月低点: ${trough:.2f} [{trough_date}]")
        print(f"  从峰值回撤: {drawdown:.1f}%")

        claimed_peak = 5589
        claimed_trough = 4493
        claimed_drawdown = -18.5
        actual_drawdown_from_claimed_peak = (current - claimed_peak) / claimed_peak * 100
        print(f"\n  验证: 声明峰值$5,589 → 声明低点$4,493")
        print(f"  声明跌幅: {claimed_drawdown:.1f}%")
        actual_claim_drawdown = (claimed_trough - claimed_peak) / claimed_peak * 100
        print(f"  声明数字内部一致性: {actual_claim_drawdown:.1f}% (匹配{claimed_drawdown}%: {'✅' if abs(actual_claim_drawdown - claimed_drawdown) < 1 else '❌'})")
        print(f"  当前价格 vs 声明峰值: {actual_drawdown_from_claimed_peak:.1f}%")

        if abs(peak - claimed_peak) < 200:
            print(f"  ✅ 近期峰值${peak:.0f}与声明$5,589偏差在合理范围")
        else:
            print(f"  ❌ 近期峰值${peak:.0f}与声明$5,589差距${abs(peak-claimed_peak):.0f}")
except Exception as e:
    print(f"  黄金数据错误: {e}")

# ============================================================
# 4. 日元汇率——批判者声明「USD/JPY 147-149」BOJ 0.75%
# ============================================================
print("\n【4】日元汇率验证")
print("-" * 45)
print("  声明: USD/JPY 147-149, BOJ利率 0.75%")

try:
    usdjpy = yf.download("USDJPY=X", start=(end_date - timedelta(days=14)).strftime('%Y-%m-%d'),
                         end=end_date.strftime('%Y-%m-%d'), progress=False)
    if not usdjpy.empty:
        current = float(usdjpy['Close'].iloc[-1])
        current_date = usdjpy.index[-1].strftime('%Y-%m-%d')
        print(f"  当前USD/JPY: {current:.2f} [{current_date}]")

        claimed_range = (147, 149)
        if claimed_range[0] <= current <= claimed_range[1]:
            print(f"  ✅ USD/JPY {current:.2f}在声明范围147-149内")
        elif abs(current - 148) < 3:
            print(f"  ⚠️ USD/JPY {current:.2f}接近声明范围147-149")
        else:
            print(f"  ❌ USD/JPY {current:.2f}偏离声明范围147-149")

        print(f"  BOJ 0.75%利率: 无法通过yfinance验证，但2025年末BOJ加息至0.5%，0.75%为合理预测")
except Exception as e:
    print(f"  日元数据错误: {e}")

# ============================================================
# 5. 初请失业金——各帖均声明205k (week of Mar 14)
# ============================================================
print("\n【5】初请失业金 & 宏观数据 (FRED)")
print("-" * 45)

try:
    import pandas_datareader.data as web

    # Initial claims
    icsa = web.DataReader('ICSA', 'fred', start='2026-01-01',
                          end=end_date.strftime('%Y-%m-%d'))
    if not icsa.empty:
        recent = icsa.tail(6)
        print("  初请失业金最近6周:")
        for date, row in recent.iterrows():
            print(f"    {date.strftime('%Y-%m-%d')}: {float(row['ICSA'])/1000:.0f}k")
        latest = float(icsa['ICSA'].dropna().iloc[-1])
        latest_date = icsa['ICSA'].dropna().index[-1].strftime('%Y-%m-%d')
        status = "✅" if abs(latest - 205000) < 15000 else "⚠️" if abs(latest - 205000) < 25000 else "❌"
        print(f"  {status} 最新: {latest/1000:.0f}k [{latest_date}] (声明: 205k)")
except Exception as e:
    print(f"  FRED数据错误: {e}")

# ============================================================
# 6. YTD vs上轮对比（SPY/RSP/GLD）
# ============================================================
print("\n【6】YTD收益率对比（R5→R10更新）")
print("-" * 45)

year_start = datetime(end_date.year, 1, 1)
ytd_tickers = {"SPY": "SPY (S&P500)", "RSP": "RSP (等权重)", "GLD": "GLD (黄金ETF)",
               "TIP": "TIP (TIPS)", "DJP": "DJP (大宗商品)"}

r5_claims = {"SPY": -4.8, "RSP": -1.2}  # R5 actual values verified

for ticker, name in ytd_tickers.items():
    try:
        data = yf.download(ticker, start=year_start.strftime('%Y-%m-%d'),
                           end=end_date.strftime('%Y-%m-%d'), progress=False)
        if not data.empty:
            ytd_return = (float(data['Close'].iloc[-1]) / float(data['Close'].iloc[0]) - 1) * 100
            latest_date = data.index[-1].strftime('%Y-%m-%d')
            note = ""
            if ticker in r5_claims:
                delta = ytd_return - r5_claims[ticker]
                note = f" [R5时:{r5_claims[ticker]:+.1f}% → 变化:{delta:+.1f}ppts]"
            print(f"  {name}: {ytd_return:+.2f}% [{latest_date}]{note}")
    except Exception as e:
        print(f"  {name}: 错误 - {e}")

# ============================================================
# 7. AI layoffs声明验证——第一性原理声明「AI归因裁员Q1 2026 = 20.4%」
# ============================================================
print("\n【7】AI归因裁员声明核查")
print("-" * 45)
print("  声明 (第一性原理 [524084c1]): AI归因裁员Q1 2026 = 20.4% (vs 2025年8%)")
print("  来源: 帖子未提供URL")
print("  注: 此数据需要Challenger, Gray & Christmas的裁员报告")
print("  → Challenger每月发布，2026年Q1数据应在4月初发布")
print("  → 当前无法通过API验证，声明来源需补充URL")
print("  ⚠️ 无法验证——声明中缺少来源链接，不符合论坛引用规则")

# ============================================================
# 总结
# ============================================================
print("\n" + "=" * 65)
print("【综合验证结论】")
print("=" * 65)
