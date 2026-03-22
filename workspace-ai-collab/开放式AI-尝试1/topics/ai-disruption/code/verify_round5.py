"""
Round 5 verification: Check key quantitative claims from forum posts
Focus on:
1. Chegg stock: claimed -99.6% from 2021 high
2. NVDA P/E: claimed ~47x TTM / ~38x FY2026
3. TSMC P/E: claimed ~27-28x forward
4. AVGO P/E: claimed ~57x forward
5. AI capex vs revenue: claimed 4:1 ratio (~$300B vs ~$75B)
6. Robo-advisor AUM: claimed $2.97 trillion
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

results = {}
print("=" * 60)
print("代码验证：量化声明核查 Round 5")
print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# 1. Chegg stock verification
print("\n### 1. Chegg (CHGG) 股价验证")
print("声明：2021年2月高点→2026年3月跌幅 -99.6%")
try:
    chgg = yf.Ticker("CHGG")
    hist = chgg.history(start="2021-01-01", end="2021-04-01")
    if not hist.empty:
        peak_2021 = hist['High'].max()
        peak_date = hist['High'].idxmax()
        print(f"  2021年Q1最高价: ${peak_2021:.2f} ({peak_date.date()})")
    
    # Current price
    current = chgg.history(period="5d")
    if not current.empty:
        current_price = current['Close'].iloc[-1]
        current_date = current.index[-1]
        print(f"  当前价格: ${current_price:.2f} ({current_date.date()})")
        
        if not hist.empty:
            drop_pct = (current_price - peak_2021) / peak_2021 * 100
            print(f"  实际跌幅: {drop_pct:.1f}%")
            claimed_drop = -99.6
            print(f"  声明跌幅: {claimed_drop}%")
            diff = abs(drop_pct - claimed_drop)
            status = "✅ 验证通过" if diff < 5 else "⚠️ 存在偏差"
            print(f"  {status} (差异: {diff:.1f}pp)")
            results['chegg_drop'] = {'claimed': claimed_drop, 'actual': drop_pct, 'status': status}
except Exception as e:
    print(f"  ❌ 获取数据失败: {e}")

# 2. NVIDIA P/E
print("\n### 2. NVIDIA (NVDA) 估值验证")
print("声明：TTM P/E ~47x, FY2026前瞻 ~38x")
try:
    nvda = yf.Ticker("NVDA")
    info = nvda.info
    ttm_pe = info.get('trailingPE', None)
    fwd_pe = info.get('forwardPE', None)
    price = info.get('currentPrice', None) or info.get('regularMarketPrice', None)
    
    print(f"  当前股价: ${price}")
    print(f"  TTM P/E: {ttm_pe:.1f}x" if ttm_pe else "  TTM P/E: N/A")
    print(f"  前瞻 P/E: {fwd_pe:.1f}x" if fwd_pe else "  前瞻 P/E: N/A")
    
    if ttm_pe:
        diff = abs(ttm_pe - 47)
        status = "✅" if diff < 10 else "⚠️"
        print(f"  TTM P/E声明47x: {status} (实际{ttm_pe:.1f}x, 差{diff:.1f})")
        results['nvda_ttm_pe'] = {'claimed': 47, 'actual': ttm_pe}
    if fwd_pe:
        diff = abs(fwd_pe - 38)
        status = "✅" if diff < 8 else "⚠️"
        print(f"  前瞻P/E声明38x: {status} (实际{fwd_pe:.1f}x, 差{diff:.1f})")
        results['nvda_fwd_pe'] = {'claimed': 38, 'actual': fwd_pe}
except Exception as e:
    print(f"  ❌ 获取数据失败: {e}")

# 3. TSMC P/E
print("\n### 3. 台积电 (TSM) 估值验证")
print("声明：前瞻 P/E ~27-28x")
try:
    tsm = yf.Ticker("TSM")
    info = tsm.info
    ttm_pe = info.get('trailingPE', None)
    fwd_pe = info.get('forwardPE', None)
    price = info.get('currentPrice', None) or info.get('regularMarketPrice', None)
    
    print(f"  当前股价: ${price}")
    print(f"  TTM P/E: {ttm_pe:.1f}x" if ttm_pe else "  TTM P/E: N/A")
    print(f"  前瞻 P/E: {fwd_pe:.1f}x" if fwd_pe else "  前瞻 P/E: N/A")
    
    if fwd_pe:
        diff = abs(fwd_pe - 27.5)
        status = "✅" if diff < 5 else "⚠️"
        print(f"  前瞻P/E声明27-28x: {status} (实际{fwd_pe:.1f}x, 差{diff:.1f})")
        results['tsm_fwd_pe'] = {'claimed': '27-28', 'actual': fwd_pe}
except Exception as e:
    print(f"  ❌ 获取数据失败: {e}")

# 4. Broadcom P/E
print("\n### 4. 博通 (AVGO) 估值验证")
print("声明：前瞻 P/E ~57x")
try:
    avgo = yf.Ticker("AVGO")
    info = avgo.info
    ttm_pe = info.get('trailingPE', None)
    fwd_pe = info.get('forwardPE', None)
    price = info.get('currentPrice', None) or info.get('regularMarketPrice', None)
    
    print(f"  当前股价: ${price}")
    print(f"  TTM P/E: {ttm_pe:.1f}x" if ttm_pe else "  TTM P/E: N/A")
    print(f"  前瞻 P/E: {fwd_pe:.1f}x" if fwd_pe else "  前瞻 P/E: N/A")
    
    if fwd_pe:
        diff = abs(fwd_pe - 57)
        status = "✅" if diff < 10 else "⚠️"
        print(f"  前瞻P/E声明57x: {status} (实际{fwd_pe:.1f}x, 差{diff:.1f})")
        results['avgo_fwd_pe'] = {'claimed': 57, 'actual': fwd_pe}
except Exception as e:
    print(f"  ❌ 获取数据失败: {e}")

# 5. NVDA vs TSM vs AVGO relative valuation comparison
print("\n### 5. 估值剪刀差计算")
print("声明：TSMC最便宜(~27-28x) vs AVGO最贵(~57x)，差距约2倍")
try:
    tickers = {"NVDA": 47, "TSM": 27.5, "AVGO": 57}
    actual_fwd = {}
    for sym, claimed in tickers.items():
        t = yf.Ticker(sym)
        pe = t.info.get('forwardPE', None)
        actual_fwd[sym] = pe
        if pe:
            print(f"  {sym}: 声明{claimed}x → 实际前瞻{pe:.1f}x")
    
    if actual_fwd.get('AVGO') and actual_fwd.get('TSM'):
        ratio = actual_fwd['AVGO'] / actual_fwd['TSM']
        print(f"\n  实际AVGO/TSM倍数: {ratio:.1f}x (声明约2x)")
        status = "✅" if 1.5 < ratio < 3 else "⚠️"
        print(f"  {status} 剪刀差方向正确" if ratio > 1 else "  ❌ 估值关系已逆转")
except Exception as e:
    print(f"  ❌ 计算失败: {e}")

# 6. Compare sector ETF returns: semiconductors vs broad market
print("\n### 6. AI铲子（半导体）vs 大盘 近1年相对表现")
try:
    etfs = {
        'SMH': '半导体ETF (VanEck)',
        'SOXX': '费城半导体ETF',
        'SPY': '标普500',
        'QQQ': '纳斯达克100',
    }
    
    perf = {}
    for sym, name in etfs.items():
        t = yf.Ticker(sym)
        hist = t.history(period="1y")
        if not hist.empty:
            ret = (hist['Close'].iloc[-1] / hist['Close'].iloc[0] - 1) * 100
            perf[sym] = ret
            print(f"  {sym} ({name}): {ret:+.1f}%")
    
    if 'SMH' in perf and 'SPY' in perf:
        spread = perf['SMH'] - perf['SPY']
        print(f"\n  半导体vs大盘超额收益: {spread:+.1f}pp")
        if spread > 0:
            print("  ✅ 半导体跑赢大盘（铲子逻辑有效）")
        else:
            print("  ⚠️ 半导体跑输大盘（铲子逻辑受挑战）")
except Exception as e:
    print(f"  ❌ 获取ETF数据失败: {e}")

print("\n" + "=" * 60)
print("验证完成")
print("=" * 60)
