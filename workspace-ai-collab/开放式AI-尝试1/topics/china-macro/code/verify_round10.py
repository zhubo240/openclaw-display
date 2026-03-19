"""
第10轮验证：沪深300估值、M1加速、房价城市裂变、CPI/PMI
验证论坛第6-10轮的关键量化声明
"""
import akshare as ak
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

results = {}

# ============================================================
# 1. 沪深300：现价4790点，PE=15.36倍
# ============================================================
print("=" * 60)
print("1. 沪深300估值验证")
print("=" * 60)

try:
    # yfinance: 000300.SS is CSI 300
    csi300 = yf.Ticker("000300.SS")
    hist = csi300.history(period="5d")
    if not hist.empty:
        latest_close = hist['Close'].iloc[-1]
        print(f"沪深300最新收盘价: {latest_close:.1f}")
        print(f"论坛声称: 4790")
        diff_pct = (latest_close - 4790) / 4790 * 100
        print(f"差异: {diff_pct:+.1f}%")
        results['csi300_price'] = latest_close
    else:
        print("yfinance无数据，尝试akshare...")
        raise ValueError("empty")
except Exception as e:
    try:
        df = ak.stock_zh_index_daily(symbol="sh000300")
        if not df.empty:
            latest = df.iloc[-1]
            print(f"沪深300最新: {latest.get('close', latest.get('收盘', 'N/A'))}")
            results['csi300_akshare'] = latest.to_dict()
    except Exception as e2:
        print(f"akshare也失败: {e2}")

# PE数据
try:
    pe_df = ak.stock_market_pe_lg()  # A股整体PE
    if not pe_df.empty:
        latest_pe = pe_df.iloc[-1]
        print(f"\nA股市场PE（最新）: {latest_pe.to_dict()}")
except Exception as e:
    print(f"PE数据获取失败: {e}")

# ============================================================
# 2. M1数据验证：3.8%→4.9%→5.9%
# ============================================================
print("\n" + "=" * 60)
print("2. M1货币数据验证")
print("=" * 60)

try:
    m_data = ak.macro_china_m2()
    if not m_data.empty:
        print(f"M2数据列: {m_data.columns.tolist()}")
        print(m_data.tail(6).to_string())
        results['m2_data'] = m_data.tail(6).to_dict()
except Exception as e:
    print(f"M2接口失败: {e}")

try:
    m1_data = ak.macro_china_m1()
    if not m1_data.empty:
        print(f"\nM1数据列: {m1_data.columns.tolist()}")
        print(m1_data.tail(6).to_string())
        results['m1_data'] = m1_data.tail(6).to_dict()

        # 验证声称的3.8%→4.9%→5.9%趋势
        if '同比增长' in m1_data.columns:
            recent = m1_data.tail(4)
            print("\nM1近期同比增速:")
            for _, row in recent.iterrows():
                print(f"  {row.get('月份', row.get('时间', '?'))}: {row.get('同比增长', '?')}%")
except Exception as e:
    print(f"M1接口失败: {e}")

# 尝试货币供应量综合接口
try:
    money_supply = ak.macro_china_money_supply()
    if not money_supply.empty:
        print(f"\n货币供应量数据（最新6期）:")
        print(money_supply.tail(6).to_string())
except Exception as e:
    print(f"货币供应量综合接口失败: {e}")

# ============================================================
# 3. CPI验证：2月同比+1.3%（37个月新高）
# ============================================================
print("\n" + "=" * 60)
print("3. CPI数据验证")
print("=" * 60)

try:
    cpi = ak.macro_china_cpi_monthly()
    if not cpi.empty:
        print(f"CPI数据列: {cpi.columns.tolist()}")
        print(cpi.tail(12).to_string())

        # 寻找37个月内最高值
        if '同比增长' in cpi.columns or 'value' in cpi.columns:
            col = '同比增长' if '同比增长' in cpi.columns else 'value'
            recent_37 = cpi.tail(37)
            max_val = recent_37[col].astype(float).max()
            max_idx = recent_37[col].astype(float).idxmax()
            print(f"\n过去37个月CPI同比最高值: {max_val}% (时间: {cpi.loc[max_idx, cpi.columns[0]] if max_idx in cpi.index else '?'})")
            latest_cpi = cpi.iloc[-1][col]
            print(f"最新CPI同比: {latest_cpi}%")
            print(f"论坛声称: +1.3% (37个月新高)")
except Exception as e:
    print(f"CPI接口失败: {e}")

# ============================================================
# 4. PMI验证：NBS=49.0 vs Caixin=52.1
# ============================================================
print("\n" + "=" * 60)
print("4. PMI数据验证")
print("=" * 60)

try:
    pmi_mfg = ak.macro_china_pmi_monthly()
    if not pmi_mfg.empty:
        print(f"官方PMI数据列: {pmi_mfg.columns.tolist()}")
        print(pmi_mfg.tail(6).to_string())
        print(f"\n论坛声称2026年2月NBS制造业PMI=49.0")
except Exception as e:
    print(f"官方PMI接口失败: {e}")

try:
    caixin_pmi = ak.macro_china_pmi_cx_monthly()
    if not caixin_pmi.empty:
        print(f"\n财新PMI数据列: {caixin_pmi.columns.tolist()}")
        print(caixin_pmi.tail(6).to_string())
        print(f"\n论坛声称2026年2月财新PMI=52.1")
except Exception as e:
    print(f"财新PMI接口失败: {e}")

# ============================================================
# 5. 房价城市数据验证：上海+4.2% vs 深圳-5.5%
# ============================================================
print("\n" + "=" * 60)
print("5. 70城房价数据验证")
print("=" * 60)

try:
    # 尝试获取70城房价
    house_price = ak.macro_china_new_house_price()
    if not house_supply.empty:
        print(f"房价数据列: {house_price.columns.tolist()}")
        print(house_price.tail(10).to_string())
except Exception as e:
    print(f"70城房价接口失败: {e}")

# 尝试上海房价
try:
    sh_house = ak.house_price_shanghaicenter()
    if not sh_house.empty:
        print(f"\n上海房价数据: {sh_house.tail(6).to_string()}")
except Exception as e:
    print(f"上海房价接口失败: {e}")

# ============================================================
# 6. 社零数据验证
# ============================================================
print("\n" + "=" * 60)
print("6. 社会消费品零售数据")
print("=" * 60)

try:
    retail = ak.macro_china_retail_total()
    if not retail.empty:
        print(f"社零数据列: {retail.columns.tolist()}")
        print(retail.tail(8).to_string())
except Exception as e:
    print(f"社零接口失败: {e}")

# ============================================================
# 7. 沪深300 PE历史数据
# ============================================================
print("\n" + "=" * 60)
print("7. 沪深300 PE历史分位")
print("=" * 60)

try:
    # 尝试获取沪深300 PE
    csi_pe = ak.stock_a_pe(symbol="000300")
    if not csi_pe.empty:
        print(f"PE数据列: {csi_pe.columns.tolist()}")
        print(csi_pe.tail(10).to_string())
        # 历史PE分位
        if 'pe' in csi_pe.columns or 'PE' in csi_pe.columns:
            pe_col = 'pe' if 'pe' in csi_pe.columns else 'PE'
            latest_pe = csi_pe[pe_col].iloc[-1]
            historical_pct = (csi_pe[pe_col] < latest_pe).mean() * 100
            print(f"\n最新PE: {latest_pe}")
            print(f"历史分位: {historical_pct:.1f}%")
            print(f"论坛声称: PE=15.36（高于历史均值12.24）")
except Exception as e:
    print(f"PE历史数据接口失败: {e}")

print("\n" + "=" * 60)
print("验证完成")
print("=" * 60)
print("\n结果摘要（results字典）:")
for k, v in results.items():
    print(f"  {k}: {str(v)[:100]}")
