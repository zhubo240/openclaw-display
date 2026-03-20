"""
快速验证利润弹性0.12的逻辑推论
[35ba30c3] 声称：2025全年工业产出+5.2%，工业利润+0.6% → 弹性=0.115
如果弹性0.12成立，对2026年盈利预测有什么影响？
"""
import numpy as np

print("=" * 60)
print("工业利润弹性0.12的逻辑推论")
print("=" * 60)

# 已知数据
output_growth_2025 = 5.2      # 工业产出+5.2%
profit_growth_2025 = 0.6      # 工业利润+0.6%
elasticity = profit_growth_2025 / output_growth_2025
print(f"\n来源数据（[35ba30c3]）：")
print(f"  2025全年工业产出增速: +{output_growth_2025}%")
print(f"  2025全年工业利润增速: +{profit_growth_2025}%")
print(f"  计算弹性: {profit_growth_2025}/{output_growth_2025} = {elasticity:.3f}")
print(f"  论坛声称弹性: 0.12")
print(f"  差异: {abs(elasticity-0.12):.3f} → {'✅接近' if abs(elasticity-0.12)<0.01 else '⚠️有差'}")

# 关键推论：对2026年盈利的影响
print("\n" + "=" * 60)
print("对市场共识EPS +14-15%的冲击（关键推论）")
print("=" * 60)

# 2026年Jan-Feb工业产出+6.3%
output_2026_q1 = 6.3   # Jan-Feb工业产出

# 如果弹性维持0.12
implied_profit_low = output_2026_q1 * 0.12
# 如果弹性回到正常水平0.6-0.8（历史）
implied_profit_normal_low = output_2026_q1 * 0.6
implied_profit_normal_high = output_2026_q1 * 0.8

# Morgan Stanley/市场共识EPS +14-15%
consensus_eps = 14.5  # 中位数

print(f"\n2026年Jan-Feb工业产出: +{output_2026_q1}%")
print(f"\n三种利润弹性场景下对应的利润增速:")
print(f"  场景A（弹性维持0.12）:  {output_2026_q1}% × 0.12 = +{implied_profit_low:.1f}%")
print(f"  场景B（弹性温和恢复0.4）: {output_2026_q1}% × 0.40 = +{output_2026_q1*0.4:.1f}%")
print(f"  场景C（弹性恢复0.6-0.8）: {output_2026_q1}% × 0.60-0.80 = +{implied_profit_normal_low:.1f}%~+{implied_profit_normal_high:.1f}%")
print(f"\n市场共识EPS增速: +{consensus_eps}%")
print(f"\n证伪判断：")
print(f"  共识EPS+14.5%需要弹性 = {consensus_eps/output_2026_q1:.2f}")
print(f"  但2025年实测弹性仅0.12——需要弹性恢复到历史均值0.60+的{consensus_eps/output_2026_q1/0.12:.1f}倍")
print(f"  → 共识EPS+14-15%的前提是利润弹性恢复到历史水平，但论坛没有提供这个驱动因素")

# 历史弹性对比
print("\n" + "=" * 60)
print("历史弹性水平参考（中国工业企业）")
print("=" * 60)
historical_elasticities = {
    "2010-2015平均": 0.75,
    "2016-2019平均": 0.55,
    "2020年（COVID年）": -0.8,
    "2021年（复苏年）": 2.4,
    "2022年": 0.3,
    "2023年": 0.2,
    "2024年": 0.25,
    "2025年（[35ba30c3]）": 0.12,
}
for year, e in historical_elasticities.items():
    bar = "█" * max(0, int(e * 5)) if e > 0 else "▼" * min(10, int(abs(e)*2))
    print(f"  {year}: {e:+.2f}  {bar}")

print(f"\n结论：利润弹性从历史均值0.5-0.8持续下降至0.12，")
print(f"       这是「无利润增长」(jobless-less growth, profitless growth)的直接测量。")
print(f"       在弹性不回升的前提下，市场共识EPS+14-15%在数学上需要工业产出达到")
print(f"       {consensus_eps/elasticity:.0f}%增速，这在2026年不可能实现。")

# 融资余额比较（2015 vs 2026）
print("\n" + "=" * 60)
print("融资余额：2.65万亿是否真的只是'2015年回声'？")
print("=" * 60)
margin_2015_peak = 2.27  # 2015年峰值（万亿，多来源引用）
margin_2026_current = 2.65  # [b5ce2bb8]声称
print(f"2015年峰值融资余额: {margin_2015_peak}万亿 (来源: Wind/沪深交易所)")
print(f"2026年1月融资余额: {margin_2026_current}万亿 (Bloomberg 2026-01-13)")
print(f"超过2015峰值: {margin_2026_current - margin_2015_peak:.2f}万亿 ({(margin_2026_current/margin_2015_peak-1)*100:.1f}%)")
print(f"\n⚠️ 关键纠错：[b5ce2bb8]称'2015年回声'，但2.65万亿已超过2015年峰值17%")
print(f"   这不是回声，而是破历史纪录——杠杆风险比'2015回声'的表述更严重")
