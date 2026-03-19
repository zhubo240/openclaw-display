"""
第五轮验证脚本 v2 - 使用可用的akshare接口
"""
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("代码验证 第五轮 v2 - 使用可用接口")
print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# ============================================================
# 验证A: 主要指数PE估值分位 (stock_index_pe_lg 可用)
# ============================================================
print("\n【验证A】主要指数PE估值分位数 (实测数据)")
print("-" * 50)

results = {}
for idx_name in ["上证50", "沪深300", "中证500", "中证红利"]:
    try:
        df = ak.stock_index_pe_lg(symbol=idx_name)
        if len(df) > 0:
            # 找PE列
            pe_col = None
            for col in df.columns:
                if 'pe' in col.lower() or 'PE' in col or '市盈率' in col or '等权' in col:
                    pe_col = col
                    break
            if pe_col is None:
                pe_col = df.columns[-1]  # 取最后一列

            hist_pe = df[pe_col].dropna()
            current_pe = hist_pe.iloc[-1]
            pct = (hist_pe < current_pe).mean() * 100
            min_pe = hist_pe.min()
            max_pe = hist_pe.max()
            years = len(hist_pe) / 52  # 周频数据

            results[idx_name] = {
                'current_pe': current_pe,
                'percentile': pct,
                'min': min_pe,
                'max': max_pe,
                'years': years
            }
            print(f"{idx_name}: PE={current_pe:.1f}, 历史{pct:.0f}%分位 (min={min_pe:.1f}, max={max_pe:.1f}, 约{years:.0f}年数据)")

            # 简单显示最新几个数据点
            date_col = df.columns[0]
            print(f"  最新日期: {df[date_col].iloc[-1]}")
    except Exception as e:
        print(f"{idx_name}: 错误 - {e}")

# ============================================================
# 验证B: 创业板PE估值
# ============================================================
print("\n\n【验证B】创业板/成长类指数PE")
print("-" * 50)
for idx_name in ["创业板指", "科创50"]:
    try:
        df = ak.stock_index_pe_lg(symbol=idx_name)
        if len(df) > 0:
            pe_col = df.columns[-1]
            hist_pe = df[pe_col].dropna()
            current_pe = hist_pe.iloc[-1]
            pct = (hist_pe < current_pe).mean() * 100
            years = len(hist_pe) / 52
            print(f"{idx_name}: PE={current_pe:.1f}, 历史{pct:.0f}%分位 (约{years:.0f}年数据)")
    except Exception as e:
        print(f"{idx_name}: 错误 - {e}")

# ============================================================
# 验证C: 宏观债券收益率 (十年期国债)
# ============================================================
print("\n\n【验证C】十年期国债收益率 - 验证论坛「距黄灯仅18bp」的声明")
print("-" * 50)
try:
    df_bond = ak.bond_china_yield(start_date="20251201", end_date="20260313")
    if len(df_bond) > 0:
        print(f"数据列: {df_bond.columns.tolist()}")
        # 找10年期
        cols_10y = [c for c in df_bond.columns if '10' in str(c)]
        print(f"10年期相关列: {cols_10y}")
        if cols_10y:
            latest = df_bond.iloc[-1]
            print(f"\n最新数据 ({df_bond.iloc[-1, 0]}):")
            for col in cols_10y:
                print(f"  {col}: {latest[col]}")
            # 最近走势
            col_10y = cols_10y[0]
            print(f"\n近10个交易日走势:")
            print(df_bond[['日期', col_10y] if '日期' in df_bond.columns else [df_bond.columns[0], col_10y]].tail(10).to_string(index=False))
except Exception as e:
    print(f"国债收益率: {e}")

# ============================================================
# 验证D: 北向资金近期流向
# ============================================================
print("\n\n【验证D】北向资金近期流向")
print("-" * 50)
try:
    df_north = ak.stock_connect_hist_sina(symbol="北向资金")
    if len(df_north) > 0:
        print(f"数据列: {df_north.columns.tolist()}")
        recent = df_north.tail(20)
        print(f"\n近20日北向资金净买入(亿元):")
        print(recent.to_string(index=False))
except Exception as e:
    try:
        df_north = ak.stock_hsgt_north_acc_flow_in_em(symbol="北上资金")
        print(df_north.tail(10))
    except Exception as e2:
        print(f"北向资金: {e} / {e2}")

# ============================================================
# 验证E: 两融余额数据 (验证市场情绪)
# ============================================================
print("\n\n【验证E】两融余额 - 验证[933adeca]市场数据agent声明")
print("-" * 50)
try:
    df_margin = ak.stock_margin_account_info()
    if len(df_margin) > 0:
        print(f"最新两融余额数据:")
        print(df_margin.tail(5).to_string())
except Exception as e:
    try:
        df_margin = ak.stock_margin_sz_summary_em()
        print(df_margin.tail(5))
    except Exception as e2:
        print(f"两融余额: {e} / {e2}")

# ============================================================
# 验证F: PE相关性分析 - 红利低波与宽基的相对估值
# ============================================================
print("\n\n【验证F】中证红利 vs 沪深300 PE对比分析")
print("-" * 50)
try:
    # 中证红利
    df_dividend = ak.stock_index_pe_lg(symbol="中证红利")
    df_csi300 = ak.stock_index_pe_lg(symbol="沪深300")

    if len(df_dividend) > 0 and len(df_csi300) > 0:
        # 找PE列
        def get_pe_series(df):
            for col in df.columns:
                if 'PE' in col or '市盈率' in col or 'pe' in col.lower():
                    return df.set_index(df.columns[0])[col].dropna()
            return df.set_index(df.columns[0])[df.columns[-1]].dropna()

        div_pe = get_pe_series(df_dividend)
        csi_pe = get_pe_series(df_csi300)

        # 对齐
        common = div_pe.index.intersection(csi_pe.index)
        if len(common) > 50:
            ratio = csi_pe.loc[common] / div_pe.loc[common]

            current_ratio = ratio.iloc[-1]
            hist_pct = (ratio < current_ratio).mean() * 100

            print(f"沪深300/中证红利 PE比率:")
            print(f"  当前: {current_ratio:.2f}x")
            print(f"  历史分位: {hist_pct:.0f}%")
            print(f"  历史均值: {ratio.mean():.2f}x")
            print(f"  历史最高: {ratio.max():.2f}x")
            print(f"  历史最低: {ratio.min():.2f}x")

            print(f"\n解读: 沪深300相对红利股的溢价 = {hist_pct:.0f}%分位")
            if hist_pct > 70:
                print("  → 红利股相对低估，价值洼地特征明显")
            elif hist_pct > 50:
                print("  → 相对估值适中，无明显方向信号")
            else:
                print("  → 红利股相对昂贵，需注意拥挤度风险")
except Exception as e:
    print(f"PE对比: {e}")

# ============================================================
# 验证G: 尝试获取基金ETF数据 (sina接口)
# ============================================================
print("\n\n【验证G】ETF实时信息 (备用接口)")
print("-" * 50)
try:
    # 尝试获取ETF实时行情
    for etf_code, etf_name in [("512890", "红利低波"), ("510300", "沪深300ETF"), ("512050", "A500ETF")]:
        try:
            df_etf = ak.fund_etf_spot_em()
            if len(df_etf) > 0:
                row = df_etf[df_etf['代码'] == etf_code]
                if len(row) > 0:
                    r = row.iloc[0]
                    print(f"{etf_name}({etf_code}): 价格={r.get('最新价','N/A')}, "
                          f"规模={r.get('资产净值','N/A')}, 涨跌幅={r.get('涨跌幅','N/A')}")
            break  # 只需获取一次列表
        except Exception as e:
            pass

    # 从大列表里筛选
    try:
        df_all = ak.fund_etf_spot_em()
        etf_codes = ["512890", "510300", "512050", "511010", "159545"]
        filtered = df_all[df_all['代码'].isin(etf_codes)]
        if len(filtered) > 0:
            print("\n关键ETF实时数据:")
            cols = ['代码', '名称', '最新价', '涨跌幅', '成交额', '资产净值']
            available_cols = [c for c in cols if c in filtered.columns]
            print(filtered[available_cols].to_string(index=False))
    except Exception as e:
        print(f"ETF实时数据: {e}")

except Exception as e:
    print(f"ETF接口错误: {e}")

print("\n" + "=" * 60)
print("验证完成")
print("=" * 60)
