"""
第五轮验证脚本 - 代码验证agent
验证论坛关键数据声明：
1. 红利低波 vs 沪深300 近三年收益
2. 主要宽基指数PE/PB估值分位
3. 沪深300 vs 红利低波近期走势对比
4. 不可能三角：55%权益+45%短债组合的历史回测
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("代码验证 第五轮 - 关键数据验证")
print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# ============================================================
# 验证1: 红利低波 vs 沪深300 近三年净值数据
# ============================================================
print("\n【验证1】红利低波(512890) vs 沪深300 ETF(510300) 近三年收益对比")
print("-" * 50)

try:
    # 获取512890 (华泰柏瑞红利低波) 近三年净值
    end_date = "20260313"
    start_date = "20230313"

    df_hl = ak.fund_etf_hist_em(symbol="512890", period="daily",
                                  start_date=start_date, end_date=end_date, adjust="qfq")
    df_csi300 = ak.fund_etf_hist_em(symbol="510300", period="daily",
                                      start_date=start_date, end_date=end_date, adjust="qfq")

    if len(df_hl) > 0 and len(df_csi300) > 0:
        # 计算收益率
        hl_return = (df_hl['收盘'].iloc[-1] / df_hl['收盘'].iloc[0] - 1) * 100
        csi300_return = (df_csi300['收盘'].iloc[-1] / df_csi300['收盘'].iloc[0] - 1) * 100

        print(f"512890 红利低波ETF:")
        print(f"  起始价: {df_hl['收盘'].iloc[0]:.3f} (日期: {df_hl['日期'].iloc[0]})")
        print(f"  最新价: {df_hl['收盘'].iloc[-1]:.3f} (日期: {df_hl['日期'].iloc[-1]})")
        print(f"  近三年收益: {hl_return:+.1f}%")

        print(f"\n510300 沪深300ETF:")
        print(f"  起始价: {df_csi300['收盘'].iloc[0]:.3f} (日期: {df_csi300['日期'].iloc[0]})")
        print(f"  最新价: {df_csi300['收盘'].iloc[-1]:.3f} (日期: {df_csi300['日期'].iloc[-1]})")
        print(f"  近三年收益: {csi300_return:+.1f}%")

        print(f"\n超额收益: {hl_return - csi300_return:+.1f}%")
        print(f"论坛声明: 红利低波近三年+36.3% vs 沪深300全收益-0.23%")
        print(f"⚠️ 注意: ETF含分红再投，与全收益指数有差异")

        # 最大回撤计算
        def max_drawdown(prices):
            peak = prices.cummax()
            dd = (prices - peak) / peak
            return dd.min() * 100

        hl_mdd = max_drawdown(df_hl['收盘'])
        csi300_mdd = max_drawdown(df_csi300['收盘'])

        print(f"\n最大回撤(近三年):")
        print(f"  512890: {hl_mdd:.1f}%")
        print(f"  510300: {csi300_mdd:.1f}%")

        # 年化波动率
        df_hl['daily_ret'] = df_hl['收盘'].pct_change()
        df_csi300['daily_ret'] = df_csi300['收盘'].pct_change()

        hl_vol = df_hl['daily_ret'].std() * np.sqrt(252) * 100
        csi300_vol = df_csi300['daily_ret'].std() * np.sqrt(252) * 100

        print(f"\n年化波动率:")
        print(f"  512890: {hl_vol:.1f}%")
        print(f"  510300: {csi300_vol:.1f}%")
    else:
        print("数据获取失败")

except Exception as e:
    print(f"错误: {e}")

# ============================================================
# 验证2: 主要指数近期PE/PB估值
# ============================================================
print("\n\n【验证2】主要指数最新估值数据")
print("-" * 50)

try:
    # 获取沪深300、中证500、创业板指数PE/PB
    indices = {
        "沪深300": "000300",
        "中证500": "000905",
        "中证1000": "000852",
        "创业板指": "399006",
        "上证50": "000016",
    }

    for name, code in indices.items():
        try:
            df_val = ak.stock_market_fund_flow()  # 备用方案
            break
        except:
            pass

    # 用东方财富接口获取估值
    try:
        df_pe = ak.index_value_hist_funddb(symbol="沪深300", indicator="市盈率")
        if len(df_pe) > 0:
            latest_pe = df_pe.iloc[-1]
            # 计算历史分位
            pe_col = df_pe.columns[-1]  # PE列
            hist_pe = df_pe[pe_col].dropna()
            current_pe = hist_pe.iloc[-1]
            percentile = (hist_pe < current_pe).mean() * 100
            print(f"沪深300 PE: {current_pe:.1f} (历史{percentile:.0f}%分位, 近{len(hist_pe)//252}年数据)")
    except Exception as e:
        print(f"估值接口1失败: {e}")

    # 尝试另一种方式
    try:
        for idx_name, idx_code in [("沪深300", "000300"), ("中证500", "000905"), ("创业板指", "399006")]:
            df_val = ak.stock_index_pe_lg(symbol=idx_name)
            if len(df_val) > 0:
                pe_col = [c for c in df_val.columns if 'pe' in c.lower() or 'PE' in c or '市盈率' in c][0]
                hist_pe = df_val[pe_col].dropna()
                current_pe = hist_pe.iloc[-1]
                percentile = (hist_pe < current_pe).mean() * 100
                print(f"{idx_name}({idx_code}) PE: {current_pe:.1f} (历史{percentile:.0f}%分位)")
    except Exception as e:
        print(f"估值接口2失败: {e}")

    # 尝试指数估值
    try:
        val_data = ak.index_value_name_funddb()
        print("\n可用指数估值:")
        print(val_data.head(10))
    except Exception as e:
        print(f"估值接口3: {e}")

except Exception as e:
    print(f"估值验证错误: {e}")

# ============================================================
# 验证3: 不可能三角验证 —— 55%权益+45%短债历史回测
# ============================================================
print("\n\n【验证3】不可能三角验证 - 55%权益+45%短债组合历史回测")
print("-" * 50)

try:
    # 获取近5年数据
    start_5y = "20210101"
    end_now = "20260313"

    # 权益: 中证A500 or 沪深300 (用510300代替)
    # 固收: 511010 (华夏国债ETF) or 货基

    df_equity = ak.fund_etf_hist_em(symbol="510300", period="daily",
                                     start_date=start_5y, end_date=end_now, adjust="qfq")
    df_bond = ak.fund_etf_hist_em(symbol="511010", period="daily",
                                   start_date=start_5y, end_date=end_now, adjust="qfq")

    if len(df_equity) > 100 and len(df_bond) > 100:
        # 对齐日期
        df_equity = df_equity.set_index('日期')['收盘']
        df_bond = df_bond.set_index('日期')['收盘']

        common_dates = df_equity.index.intersection(df_bond.index)
        eq = df_equity.loc[common_dates]
        bd = df_bond.loc[common_dates]

        # 计算日收益率
        eq_ret = eq.pct_change().dropna()
        bd_ret = bd.pct_change().dropna()

        # 55%权益 + 45%债券组合
        portfolio_55_45 = 0.55 * eq_ret + 0.45 * bd_ret
        # 100%沪深300
        portfolio_100_eq = eq_ret

        # 累计收益
        cum_55_45 = (1 + portfolio_55_45).cumprod()
        cum_100_eq = (1 + portfolio_100_eq).cumprod()

        total_55_45 = (cum_55_45.iloc[-1] - 1) * 100
        total_100_eq = (cum_100_eq.iloc[-1] - 1) * 100

        years = len(common_dates) / 252
        ann_55_45 = ((cum_55_45.iloc[-1]) ** (1/years) - 1) * 100
        ann_100_eq = ((cum_100_eq.iloc[-1]) ** (1/years) - 1) * 100

        def max_drawdown_series(cum):
            peak = cum.cummax()
            dd = (cum - peak) / peak
            return dd.min() * 100

        mdd_55_45 = max_drawdown_series(cum_55_45)
        mdd_100_eq = max_drawdown_series(cum_100_eq)

        vol_55_45 = portfolio_55_45.std() * np.sqrt(252) * 100
        vol_100_eq = portfolio_100_eq.std() * np.sqrt(252) * 100

        print(f"数据区间: {common_dates[0]} ~ {common_dates[-1]} ({years:.1f}年)")
        print(f"\n{'指标':<20} {'55%股+45%债':>15} {'100%沪深300':>15}")
        print("-" * 52)
        print(f"{'累计收益':<20} {total_55_45:>+14.1f}% {total_100_eq:>+14.1f}%")
        print(f"{'年化收益':<20} {ann_55_45:>+14.1f}% {ann_100_eq:>+14.1f}%")
        print(f"{'最大回撤':<20} {mdd_55_45:>14.1f}% {mdd_100_eq:>14.1f}%")
        print(f"{'年化波动率':<20} {vol_55_45:>14.1f}% {vol_100_eq:>14.1f}%")

        # Sharpe ratio (假设无风险利率2%)
        rf = 0.02 / 252
        sharpe_55_45 = (portfolio_55_45.mean() - rf) / portfolio_55_45.std() * np.sqrt(252)
        sharpe_100_eq = (portfolio_100_eq.mean() - rf) / portfolio_100_eq.std() * np.sqrt(252)
        print(f"{'夏普比率(rf=2%)':<20} {sharpe_55_45:>+14.2f} {sharpe_100_eq:>+14.2f}")

        # 是否能达到8%年化?
        print(f"\n【不可能三角验证】")
        print(f"  目标: 年化8-12%, 回撤<20%, 1-3年期")
        print(f"  55%权益+45%债: 年化{ann_55_45:.1f}%, 最大回撤{mdd_55_45:.1f}%")
        if ann_55_45 >= 8.0:
            print(f"  ✓ 年化8%目标: 历史上可达(但起点依赖)")
        else:
            print(f"  ✗ 年化8%目标: 历史回测不支持({ann_55_45:.1f}% < 8%)")
        if abs(mdd_55_45) <= 20:
            print(f"  ✓ 回撤<20%目标: 满足({mdd_55_45:.1f}%)")
        else:
            print(f"  △ 回撤<20%目标: 临界({mdd_55_45:.1f}%)")

    else:
        print("数据量不足")

except Exception as e:
    print(f"回测错误: {e}")

# ============================================================
# 验证4: 512890近一年与两年走势 vs 论坛声明
# ============================================================
print("\n\n【验证4】512890实际近期表现验证")
print("-" * 50)

try:
    df_hl_1y = ak.fund_etf_hist_em(symbol="512890", period="daily",
                                    start_date="20250101", end_date="20260313", adjust="qfq")
    df_500 = ak.fund_etf_hist_em(symbol="510500", period="daily",  # 中证500 ETF
                                  start_date="20250101", end_date="20260313", adjust="qfq")

    if len(df_hl_1y) > 0:
        ret_hl_1y = (df_hl_1y['收盘'].iloc[-1] / df_hl_1y['收盘'].iloc[0] - 1) * 100
        print(f"512890 2025年至今收益: {ret_hl_1y:+.1f}%")

    if len(df_500) > 0:
        ret_500_1y = (df_500['收盘'].iloc[-1] / df_500['收盘'].iloc[0] - 1) * 100
        print(f"510500(中证500) 2025年至今收益: {ret_500_1y:+.1f}%")

    # 近3个月
    df_hl_3m = ak.fund_etf_hist_em(symbol="512890", period="daily",
                                    start_date="20251213", end_date="20260313", adjust="qfq")
    if len(df_hl_3m) > 0:
        ret_hl_3m = (df_hl_3m['收盘'].iloc[-1] / df_hl_3m['收盘'].iloc[0] - 1) * 100
        print(f"512890 近3个月收益: {ret_hl_3m:+.1f}%")

    # 股息率估算 (通过近一年分红/当前价格)
    try:
        fund_div = ak.fund_etf_fund_info_em(fund="512890", start_date="20250101", end_date="20260313")
        print(f"\n512890分红记录(2025-2026):")
        if len(fund_div) > 0:
            print(fund_div[['净值日期', '单位净值', '日增长率']].tail(10).to_string())
    except:
        pass

except Exception as e:
    print(f"512890验证错误: {e}")

# ============================================================
# 验证5: A500 ETF规模变化（批判者声明的帮忙资金问题）
# ============================================================
print("\n\n【验证5】A500 ETF规模变化验证")
print("-" * 50)

try:
    # 512050 华泰柏瑞中证A500 ETF
    df_a500 = ak.fund_etf_hist_em(symbol="512050", period="daily",
                                   start_date="20260101", end_date="20260313", adjust="qfq")
    if len(df_a500) > 0:
        print(f"512050(A500 ETF) 2026年开年至今:")
        print(f"  开年价: {df_a500['收盘'].iloc[0]:.3f} ({df_a500['日期'].iloc[0]})")
        print(f"  最新价: {df_a500['收盘'].iloc[-1]:.3f} ({df_a500['日期'].iloc[-1]})")
        ret_a500 = (df_a500['收盘'].iloc[-1] / df_a500['收盘'].iloc[0] - 1) * 100
        print(f"  2026年至今收益: {ret_a500:+.1f}%")

        # 成交量分析
        avg_vol = df_a500['成交额'].mean() / 1e8  # 转亿元
        print(f"  日均成交额: {avg_vol:.1f}亿元")
except Exception as e:
    print(f"A500验证错误: {e}")

print("\n" + "=" * 60)
print("验证完成")
print("=" * 60)
