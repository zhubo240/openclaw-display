"""
验证：AI资本支出 vs 营收的4:1声明
声明：全球AI基础设施年投资~$300B vs AI实际营收~$75B
"""
import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("AI资本支出 vs 营收验证")
print("=" * 60)

# Check the big 4 hyperscalers' capex (as proxy for AI infra investment)
# Microsoft, Amazon, Alphabet, Meta
hyperscalers = {
    'MSFT': '微软',
    'AMZN': '亚马逊',
    'GOOGL': 'Alphabet',
    'META': 'Meta',
}

print("\n### 超大规模云厂商 Capex（最近TTM）")
total_capex = 0
for sym, name in hyperscalers.items():
    t = yf.Ticker(sym)
    try:
        cf = t.cashflow
        if cf is not None and not cf.empty:
            # Capital expenditure is typically negative (cash outflow)
            if 'Capital Expenditure' in cf.index:
                capex_row = cf.loc['Capital Expenditure']
            elif 'Capital Expenditures' in cf.index:
                capex_row = cf.loc['Capital Expenditures']
            else:
                # Try other names
                capex_candidates = [idx for idx in cf.index if 'Capital' in str(idx) or 'capex' in str(idx).lower()]
                if capex_candidates:
                    capex_row = cf.loc[capex_candidates[0]]
                else:
                    print(f"  {sym}: Capex行未找到，可用行: {list(cf.index[:5])}")
                    continue
            
            # Most recent year capex
            latest_capex = abs(capex_row.iloc[0]) / 1e9  # billions
            total_capex += latest_capex
            print(f"  {sym} ({name}): ${latest_capex:.1f}B capex (最近报告期)")
    except Exception as e:
        print(f"  {sym}: {e}")

print(f"\n  四大超大规模合计: ~${total_capex:.0f}B")
print(f"  声明全球AI基础设施投资: ~$300B")
print(f"  注：四大超大规模占全球AI capex约60-70%")
print(f"  推算全球: ~${total_capex/0.65:.0f}B (假设65%占比)")

# NVDA revenue as AI enabler revenue proxy
print("\n### NVIDIA营收验证（AI芯片侧最直接指标）")
nvda = yf.Ticker("NVDA")
try:
    income = nvda.income_stmt
    if income is not None and not income.empty:
        if 'Total Revenue' in income.index:
            rev = income.loc['Total Revenue']
            for col in rev.index[:3]:
                print(f"  NVDA {col.year}财年 总营收: ${rev[col]/1e9:.1f}B")
        
        # TTM revenue
        quarterly = nvda.quarterly_income_stmt
        if quarterly is not None and not quarterly.empty and 'Total Revenue' in quarterly.index:
            ttm_rev = quarterly.loc['Total Revenue'].iloc[:4].sum() / 1e9
            print(f"  NVDA TTM营收: ${ttm_rev:.1f}B")
except Exception as e:
    print(f"  NVDA营收获取失败: {e}")

# Assess the 4:1 claim
print("\n### 4:1比例验证")
print("声明：AI基础设施投资 $300B vs AI实际营收 $75B = 4:1")
print()
print("背景：")
print("- NVDA FY2026预期营收：~$195B（主要是AI GPU）")
print("- 但这是芯片营收，不是最终AI服务营收")
print("- 企业AI应用实际收入难以单独统计")
print()
print("OpenAI 2025年营收 ~$3.7B（声明数字），但：")
print("- 这只是一家公司")
print("- 全球AI应用层营收包括：云AI API服务、企业AI SaaS等")
print("- 估计全行业AI原生营收（应用层）约$50-100B")
print("- 基础设施投资$200-300B vs 应用营收$50-100B，约2-6:1")
print()
print("⚠️ 4:1比例方向正确，但缺乏精确来源支持")
print("   该数字来自声明中的Yale Insights/CNBC，应视为估算")

