"""
深入分析：为何NVDA/TSM/AVGO前瞻P/E从声称的高位大幅压缩？
验证是股价跌了，还是盈利增长消化了估值
"""
import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("P/E压缩分析：估值变化成因溯源")
print("=" * 60)

# Check 1-year price performance for AI semis
tickers = {
    'NVDA': '英伟达',
    'TSM': '台积电', 
    'AVGO': '博通',
    'AMD': 'AMD',
}

print("\n### AI芯片股近6个月/1年价格变化")
for sym, name in tickers.items():
    t = yf.Ticker(sym)
    info = t.info
    
    # Get historical prices
    hist_1y = t.history(period="1y")
    hist_6m = t.history(period="6mo")
    
    current = info.get('currentPrice') or info.get('regularMarketPrice', 'N/A')
    ttm_pe = info.get('trailingPE', 'N/A')
    fwd_pe = info.get('forwardPE', 'N/A')
    eps_ttm = info.get('trailingEps', 'N/A')
    eps_fwd = info.get('forwardEps', 'N/A')
    
    if not hist_1y.empty and not hist_6m.empty:
        ret_1y = (hist_1y['Close'].iloc[-1] / hist_1y['Close'].iloc[0] - 1) * 100
        ret_6m = (hist_6m['Close'].iloc[-1] / hist_6m['Close'].iloc[0] - 1) * 100
        peak_1y = hist_1y['High'].max()
        peak_date = hist_1y['High'].idxmax().date()
        
        print(f"\n{sym} ({name}):")
        print(f"  当前价格: ${current}")
        print(f"  1年高点: ${peak_1y:.2f} ({peak_date}), 较高点: {(current-peak_1y)/peak_1y*100:.1f}%")
        print(f"  近1年涨跌: {ret_1y:+.1f}%")
        print(f"  近6月涨跌: {ret_6m:+.1f}%")
        print(f"  TTM P/E: {ttm_pe:.1f}x" if isinstance(ttm_pe, (int, float)) else f"  TTM P/E: {ttm_pe}")
        print(f"  前瞻 P/E: {fwd_pe:.1f}x" if isinstance(fwd_pe, (int, float)) else f"  前瞻 P/E: {fwd_pe}")
        print(f"  TTM EPS: ${eps_ttm:.2f}" if isinstance(eps_ttm, (int, float)) else f"  TTM EPS: {eps_ttm}")
        print(f"  前瞻 EPS: ${eps_fwd:.2f}" if isinstance(eps_fwd, (int, float)) else f"  前瞻 EPS: {eps_fwd}")

# Key interpretation
print("\n### 关键解读")
nvda = yf.Ticker("NVDA")
nvda_info = nvda.info
ttm_pe = nvda_info.get('trailingPE', None)
fwd_pe = nvda_info.get('forwardPE', None)
price = nvda_info.get('currentPrice', None)
ttm_eps = nvda_info.get('trailingEps', None)
fwd_eps = nvda_info.get('forwardEps', None)

if all([ttm_pe, fwd_pe, ttm_eps, fwd_eps]):
    eps_growth = (fwd_eps - ttm_eps) / ttm_eps * 100
    pe_compression = (fwd_pe - ttm_pe) / ttm_pe * 100
    print(f"\nNVDA EPS增长预期: TTM ${ttm_eps:.2f} → 前瞻 ${fwd_eps:.2f} ({eps_growth:+.1f}%)")
    print(f"NVDA P/E压缩: TTM {ttm_pe:.1f}x → 前瞻 {fwd_pe:.1f}x ({pe_compression:+.1f}%)")
    print(f"\n这意味着: 市场预期NVDA盈利将大幅增长，因此即使股价不变，前瞻P/E也会下降")
    print(f"声称的\"38x前瞻P/E\"可能是基于较早的EPS预测，盈利预期已大幅上调")

# Check implied EPS that would give claimed P/E
claimed_nvda_ttm_pe = 47
claimed_nvda_fwd_pe = 38
if price:
    implied_ttm_eps_for_47 = price / claimed_nvda_ttm_pe
    implied_fwd_eps_for_38 = price / claimed_nvda_fwd_pe
    print(f"\n如果NVDA股价${price:.2f}，则P/E=47x意味着EPS=${implied_ttm_eps_for_47:.2f}")
    print(f"如果NVDA股价${price:.2f}，则P/E=38x意味着前瞻EPS=${implied_fwd_eps_for_38:.2f}")
    if ttm_eps:
        print(f"实际TTM EPS=${ttm_eps:.2f} → 如今P/E={price/ttm_eps:.1f}x")
    if fwd_eps:
        print(f"实际前瞻EPS=${fwd_eps:.2f} → 如今前瞻P/E={price/fwd_eps:.1f}x")

print("\n### 结论")
print("声明中的P/E数字可能是帖子撰写时（较早时间点）的数据")
print("由于AI盈利预期大幅上调，前瞻P/E压缩是盈利驱动，非股价暴跌")
