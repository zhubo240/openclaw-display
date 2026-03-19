#!/usr/bin/env python3
"""
Round 5 Final Verification:
1. IRA layout optimization: is 0.9pp "free alpha" real?
2. Roth IRA vs Traditional IRA vs Taxable for JEPI
3. Final data quality scorecard across all rounds
"""
import numpy as np

print("=" * 70)
print("FINAL VERIFICATION: IRA Layout Optimization + Data Quality Audit")
print("=" * 70)

# ============================================================
# 1. Account Layout Optimization: 0.9pp free alpha?
# ============================================================
print("\n" + "=" * 70)
print("1. ACCOUNT LAYOUT: NAIVE vs OPTIMIZED")
print("=" * 70)

# Assumptions
FED_TAX = 0.32
STATE_TAX = 0.05  # moderate state (not CA/NY)
JEPI_ORD_PCT = 0.75  # % taxed as ordinary
JEPI_QUAL_PCT = 0.25  # % taxed as qualified dividend

# Tax rates
ORD_RATE = FED_TAX + STATE_TAX  # 37% combined
QUAL_RATE = 0.15 + STATE_TAX    # 20% combined
ROC_RATE = 0.0                   # deferred

# Asset returns (tax-pre income yield)
assets = {
    'SGOV': {'yield': 3.54, 'tax_char': 'treasury'},  # fed only, no state
    'JEPI': {'yield': 8.34, 'tax_char': 'jepi_blend'},
    'AMLP': {'yield': 7.60, 'tax_char': 'mlp_roc'},   # ~70% ROC
    'STIP': {'yield': 3.80, 'tax_char': 'treasury'},   # TIPS = fed only
    'GLD':  {'yield': 0.00, 'tax_char': 'none'},
}

def after_tax(asset_name, in_ira=False):
    a = assets[asset_name]
    y = a['yield']
    if in_ira:
        return y  # grows tax-free in IRA (tax at withdrawal, but deferred)

    tc = a['tax_char']
    if tc == 'treasury':
        return y * (1 - FED_TAX)  # no state tax
    elif tc == 'jepi_blend':
        return y * (JEPI_ORD_PCT * (1 - ORD_RATE) + JEPI_QUAL_PCT * (1 - QUAL_RATE))
    elif tc == 'mlp_roc':
        roc_pct = 0.70
        ord_pct = 0.30
        return y * (roc_pct * 1.0 + ord_pct * (1 - ORD_RATE))
    elif tc == 'none':
        return 0.0

# Layout A: Naive (same allocation everywhere)
# Combined portfolio: 35%SGOV + 30%JEPI + 10%AMLP + 10%STIP + 10%GLD + 5%cash
naive_alloc = {'SGOV': 0.35, 'JEPI': 0.30, 'AMLP': 0.10, 'STIP': 0.10, 'GLD': 0.10}
# Assume 50% taxable, 50% IRA (total = naive in both)
# But ALL in taxable for worst case
naive_taxable = sum(w * after_tax(a) for a, w in naive_alloc.items()) + 0.05 * after_tax('SGOV')

print(f"\n  Layout A (All Taxable): {naive_taxable:.2f}%")

# Layout B: Optimized
# Taxable (say 70% of assets): 55%SGOV + 20%AMLP + 15%GLD + 10%STIP
# IRA (30% of assets): 100%JEPI
# Total portfolio = 0.70 * taxable_return + 0.30 * ira_return

taxable_pct = 0.70
ira_pct = 0.30

# Taxable sub-portfolio
taxable_alloc = {'SGOV': 0.55, 'AMLP': 0.20, 'GLD': 0.15, 'STIP': 0.10}
taxable_ret = sum(w * after_tax(a) for a, w in taxable_alloc.items())

# IRA sub-portfolio (JEPI, tax-free growth)
ira_ret = after_tax('JEPI', in_ira=True)

# Blended
optimized = taxable_pct * taxable_ret + ira_pct * ira_ret

print(f"  Layout B (Optimized):")
print(f"    Taxable ({taxable_pct*100:.0f}%): {taxable_ret:.2f}%")
for a, w in taxable_alloc.items():
    print(f"      {a}: {w*100:.0f}% × {after_tax(a):.2f}% = {w*after_tax(a):.3f}%")
print(f"    IRA ({ira_pct*100:.0f}%): {ira_ret:.2f}% (JEPI, tax-deferred growth)")
print(f"    Blended: {optimized:.2f}%")
print(f"\n  Layout improvement: {optimized - naive_taxable:.2f}pp")
print(f"  CLAIM (风险量化 R6): +0.9pp")

# ============================================================
# 2. 10-Year Simulation: Roth IRA vs Traditional IRA vs Taxable
# ============================================================
print("\n" + "=" * 70)
print("2. 10-YEAR JEPI SIMULATION: ROTH vs TRAD IRA vs TAXABLE")
print("=" * 70)

initial = 100000
jepi_yield = 0.0834
jepi_price_return = 0.0  # assume flat price
years = 10

# Effective tax on JEPI distributions in taxable account
jepi_eff_tax = JEPI_ORD_PCT * ORD_RATE + JEPI_QUAL_PCT * QUAL_RATE
# = 0.75 * 0.37 + 0.25 * 0.20 = 0.2775 + 0.05 = 0.3275

print(f"  JEPI effective tax rate in taxable: {jepi_eff_tax*100:.2f}%")

# Taxable: pay tax each year on distributions, reinvest remainder
taxable = initial
for y in range(years):
    dist = taxable * jepi_yield
    net_dist = dist * (1 - jepi_eff_tax)
    taxable = taxable * (1 + jepi_price_return) + net_dist

# Traditional IRA: no tax on distributions, reinvest all
# At withdrawal: ALL taxed at ordinary income rate (fed+state)
trad_ira = initial
for y in range(years):
    dist = trad_ira * jepi_yield
    trad_ira = trad_ira * (1 + jepi_price_return) + dist

# Withdrawal tax (all at ordinary rate since trad IRA distributions = ordinary)
trad_ira_after = trad_ira * (1 - ORD_RATE)

# Roth IRA: no tax on distributions, no tax at withdrawal
roth_ira = initial
for y in range(years):
    dist = roth_ira * jepi_yield
    roth_ira = roth_ira * (1 + jepi_price_return) + dist

roth_ira_after = roth_ira  # no withdrawal tax

print(f"\n  After 10 years (${initial:,} initial, {jepi_yield*100}% yield, 0% price return):")
print(f"  Taxable account:      ${taxable:>12,.0f}")
print(f"  Traditional IRA:      ${trad_ira:>12,.0f} pre-tax → ${trad_ira_after:>12,.0f} after withdrawal")
print(f"  Roth IRA:             ${roth_ira:>12,.0f} (tax-free)")

print(f"\n  Roth vs Taxable advantage: ${roth_ira_after - taxable:,.0f} ({(roth_ira_after/taxable - 1)*100:.1f}%)")
print(f"  Trad IRA vs Taxable:       ${trad_ira_after - taxable:,.0f} ({(trad_ira_after/taxable - 1)*100:.1f}%)")

print(f"\n  CONCLUSION:")
print(f"    Roth IRA: BEST — {(roth_ira_after/taxable - 1)*100:.1f}% better than taxable over 10yr")
print(f"    Traditional IRA (same tax bracket): {(trad_ira_after/taxable - 1)*100:.1f}% vs taxable")

# What if retirement tax rate drops to 22%?
trad_lower = trad_ira * (1 - (0.22 + STATE_TAX))
print(f"\n  If retirement tax rate drops to 22%+5%:")
print(f"    Trad IRA after withdrawal: ${trad_lower:,.0f}")
print(f"    Trad IRA vs Taxable: ${trad_lower - taxable:,.0f} ({(trad_lower/taxable - 1)*100:.1f}%)")

# ============================================================
# 3. DATA QUALITY SCORECARD: ALL ROUNDS
# ============================================================
print("\n" + "=" * 70)
print("3. FIVE-ROUND DATA QUALITY SCORECARD")
print("=" * 70)

scorecard = [
    # (Agent, Claim, Verdict, Impact)
    ("种子材料", "JEPI yield 8.34%", "✅", "Low"),
    ("种子材料", "JEPQ yield 10.9%", "✅", "Low"),
    ("种子材料", "VDE YTD +25%", "⚠️ actual +29-37%", "Low"),
    ("种子材料", "CAPE ~40", "✅ 38.93", "Low"),
    ("种子材料", "SPY down ~5% from high", "✅", "Low"),
    ("风险量化", "JEPI capture 53%/78%=0.68", "❌ actual 63.5/60.3=1.05", "CRITICAL"),
    ("风险量化", "TLT-SPY corr = -0.30", "❌ actual +0.093", "HIGH"),
    ("风险量化", "AMLP-SPY crisis corr 0.80+", "❌ actual 0.543", "MEDIUM"),
    ("风险量化", "AMLP max DD -77%", "✅ -77.70%", "LOW"),
    ("风险量化", "RSP max DD -59.92%", "✅ exact", "LOW"),
    ("风险量化", "TLT max DD -47.75%", "✅ -48.35%", "LOW"),
    ("风险量化", "HY OAS ~309 bps", "✅ FRED=317", "LOW"),
    ("风险量化", "CCC yield 13.04%", "⚠️ FRED=13.44%", "MEDIUM"),
    ("风险量化", "CCC-B spread 1600bps/2.7x", "❌ FRED=~600/1.16x", "HIGH"),
    ("风险量化", "AMLP recovery 934 days", "❌ actual 1409 days", "MEDIUM"),
    ("估值分析", "GOOGL PE 18.6", "❌ trailing 27.9", "HIGH"),
    ("估值分析", "TSLA PE 334", "⚠️ actual 355.6", "LOW"),
    ("组合构建", "JEPI div decline -32%", "✅ actual -33.7%", "LOW"),
    ("组合构建", "Portfolio tax-after ~3.7%", "✅ calc=3.72%", "LOW"),
    ("组合构建", "SGOV tax-after 2.80%", "❌ should be 2.41%", "MEDIUM"),
    ("组合构建", "GLD LTCG rate 20%", "❌ 28% collectibles", "MEDIUM"),
    ("组合构建", "AMLP 'almost tax-free'", "⚠️ misleading (C-corp)", "MEDIUM"),
]

# Count by verdict
correct = sum(1 for _,_,v,_ in scorecard if v.startswith("✅"))
partial = sum(1 for _,_,v,_ in scorecard if v.startswith("⚠️"))
wrong = sum(1 for _,_,v,_ in scorecard if v.startswith("❌"))
total = len(scorecard)

print(f"\n  Total claims verified: {total}")
print(f"  ✅ Correct: {correct} ({correct/total*100:.0f}%)")
print(f"  ⚠️ Partially correct: {partial} ({partial/total*100:.0f}%)")
print(f"  ❌ Wrong: {wrong} ({wrong/total*100:.0f}%)")

# By agent
from collections import defaultdict
by_agent = defaultdict(lambda: {"✅": 0, "⚠️": 0, "❌": 0})
for agent, _, verdict, _ in scorecard:
    if verdict.startswith("✅"): by_agent[agent]["✅"] += 1
    elif verdict.startswith("⚠️"): by_agent[agent]["⚠️"] += 1
    elif verdict.startswith("❌"): by_agent[agent]["❌"] += 1

print(f"\n  By Agent:")
for agent in sorted(by_agent.keys()):
    v = by_agent[agent]
    t = sum(v.values())
    err = v["❌"] / t * 100
    print(f"    {agent:10s}: ✅{v['✅']} ⚠️{v['⚠️']} ❌{v['❌']}  (error rate: {err:.0f}%)")

# Critical errors
print(f"\n  CRITICAL/HIGH impact errors:")
for agent, claim, verdict, impact in scorecard:
    if impact in ("CRITICAL", "HIGH") and not verdict.startswith("✅"):
        print(f"    [{impact:8s}] {agent}: {claim} → {verdict}")
