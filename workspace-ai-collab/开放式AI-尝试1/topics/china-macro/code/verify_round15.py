"""
第15轮验证：工业利润弹性、FAI分项、融资余额、国债收益率、CSI300
"""
import akshare as ak
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 1. 工业利润 vs 工业产出：验证利润弹性0.12声明
# [35ba30c3] 声称：2025全年工业产出+5.2%，工业利润仅+0.6%，弹性=0.115≈0.12
# ============================================================
print("=" * 60)
print("1. 工业利润弹性验证")
print("=" * 60)

try:
    profit = ak.macro_china_industrial_profit_monthly()
    print(f"工业利润数据列: {profit.columns.tolist()}")
    print("最新12期:")
    print(profit.tail(12).to_string())
except Exception as e:
    print(f"工业利润接口失败: {e}")

# 也尝试工业产出
try:
    output = ak.macro_china_industrial_production_yoy()
    print(f"\n工业产出数据列: {output.columns.tolist()}")
    print(output.tail(12).to_string())
except Exception as e:
    print(f"工业产出接口失败: {e}")

# ============================================================
# 2. FAI分项验证：基建+11.4%, 制造业+3.1%, 房地产-11.1%
# [ca4e7d2f] 声称 Jan-Feb 2026 数据
# ============================================================
print("\n" + "=" * 60)
print("2. 固定资产投资(FAI)分项验证")
print("=" * 60)

try:
    fai = ak.macro_china_fai_yoy()
    print(f"FAI总量同比列: {fai.columns.tolist()}")
    print(fai.tail(6).to_string())
except Exception as e:
    print(f"FAI总量接口失败: {e}")

try:
    fai_infra = ak.macro_china_infrastructure_fai_yoy()
    print(f"\n基建FAI同比列: {fai_infra.columns.tolist()}")
    print(fai_infra.tail(6).to_string())
    print(f"论坛声称: 基建FAI 2026年1-2月 +11.4%")
except Exception as e:
    print(f"基建FAI接口失败: {e}")

try:
    fai_re = ak.macro_china_real_estate_fai_yoy()
    print(f"\n房地产FAI同比列: {fai_re.columns.tolist()}")
    print(fai_re.tail(6).to_string())
    print(f"论坛声称: 房地产FAI 2026年1-2月 -11.1%")
except Exception as e:
    print(f"房地产FAI接口失败: {e}")

# ============================================================
# 3. 融资余额验证：2.65万亿（声称2015年以来高位）
# [b5ce2bb8] 来源：Bloomberg 2026-01-13
# ============================================================
print("\n" + "=" * 60)
print("3. 融资余额验证")
print("=" * 60)

try:
    margin = ak.stock_margin_sse()  # 上交所融资余额
    print(f"上交所融资列: {margin.columns.tolist()}")
    print(margin.tail(5).to_string())
except Exception as e:
    print(f"上交所融资接口失败: {e}")

try:
    margin_sz = ak.stock_margin_szse()  # 深交所融资余额
    print(f"\n深交所融资列: {margin_sz.columns.tolist()}")
    print(margin_sz.tail(5).to_string())
except Exception as e:
    print(f"深交所融资接口失败: {e}")

# 尝试综合融资融券
try:
    margin_all = ak.stock_margin_detail_sse()
    print(f"\n融资融券综合列: {margin_all.columns.tolist()}")
    print(margin_all.tail(5).to_string())
except Exception as e:
    print(f"融资融券综合接口失败: {e}")

# ============================================================
# 4. CSI300当前估值与国债收益率
# ============================================================
print("\n" + "=" * 60)
print("4. CSI300当前价格 & 国债收益率")
print("=" * 60)

# CSI300
try:
    csi300 = yf.Ticker("000300.SS")
    hist = csi300.history(period="10d")
    if not hist.empty:
        latest = hist['Close'].iloc[-1]
        week_ago = hist['Close'].iloc[0] if len(hist) >= 5 else None
        print(f"CSI300最新价: {latest:.0f}")
        print(f"论坛声称: 4790 (3月中旬)")
        if week_ago:
            print(f"10日前: {week_ago:.0f}, 变化: {(latest-week_ago)/week_ago*100:+.1f}%")
except Exception as e:
    print(f"CSI300价格失败: {e}")

# 中国国债收益率
try:
    # 10Y中国国债
    cn10y = yf.Ticker("^TNX")  # 这是美国，试试中国的
    # 中国国债可通过CNYT10Y
    bond_10y = ak.bond_china_yield(start_date="20260101", end_date="20260320")
    print(f"\n中国国债收益率数据列: {bond_10y.columns.tolist()}")
    print(bond_10y.tail(10).to_string())
    print(f"论坛声称: 30Y国债收益率创18个月新高，10Y约1.82%")
except Exception as e:
    print(f"国债收益率接口1失败: {e}")

try:
    bond_china = ak.bond_zh_us_rate(start_date="20260101")
    print(f"\n中美利率数据列: {bond_china.columns.tolist()}")
    print(bond_china.tail(15).to_string())
except Exception as e:
    print(f"中美利率接口失败: {e}")

# ============================================================
# 5. 社零和工业产出同期比较（K型分化4.7倍验证）
# ============================================================
print("\n" + "=" * 60)
print("5. K型分化验证：工业+6.3% vs 社零+2.8%（Jan-Feb 2026）")
print("=" * 60)

try:
    retail = ak.macro_china_retail_total()
    print(f"社零数据列: {retail.columns.tolist()}")
    print(retail.tail(8).to_string())
except Exception as e:
    print(f"社零接口失败: {e}")

try:
    indus = ak.macro_china_industrial_production_yoy()
    print(f"\n工业产出列: {indus.columns.tolist()}")
    print(indus.tail(6).to_string())
except Exception as e:
    print(f"工业产出接口2失败: {e}")

# ============================================================
# 6. 黄金价格验证（上海金1156元/克声称）
# ============================================================
print("\n" + "=" * 60)
print("6. 黄金价格验证（上海金 声称1156元/克）")
print("=" * 60)

try:
    gold = yf.Ticker("GC=F")
    hist_gold = gold.history(period="5d")
    usd_price = hist_gold['Close'].iloc[-1]
    # 转换为人民币（约7.1 USDCNY）
    cny_price = usd_price * 7.1 / 31.1035  # troy oz to gram
    print(f"黄金USD/oz: {usd_price:.1f}")
    print(f"折合人民币/克 (7.1汇率): {cny_price:.0f}")
    print(f"论坛声称: 1156元/克 (3月中旬)")
    if abs(cny_price - 1156) / 1156 < 0.1:
        print("✅ 与声称值在10%以内")
    else:
        print(f"⚠️ 差异: {(cny_price-1156)/1156*100:+.1f}%")
except Exception as e:
    print(f"黄金价格失败: {e}")

# ============================================================
# 7. 汇率验证
# ============================================================
print("\n" + "=" * 60)
print("7. 人民币汇率（声称6.8961）")
print("=" * 60)

try:
    usdcny = yf.Ticker("USDCNY=X")
    hist_fx = usdcny.history(period="5d")
    latest_fx = hist_fx['Close'].iloc[-1]
    print(f"USDCNY最新: {latest_fx:.4f}")
    print(f"论坛声称: 6.8961 (3月17日中间价)")
except Exception as e:
    print(f"汇率接口失败: {e}")

print("\n" + "=" * 60)
print("验证完成")
print("=" * 60)
