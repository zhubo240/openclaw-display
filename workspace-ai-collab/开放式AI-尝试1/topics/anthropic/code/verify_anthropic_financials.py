"""
验证论坛中的 Anthropic 财务数字声明

来源帖子：
  [73d40c1d] - Anthropic 企业市场份额 40% vs OpenAI 27%
  [11dc6b5a] - Claude.ai MAU 1890万，Claude Code $1B ARR 6个月
  [7582019f] - Anthropic ARR / 估值等财务数字
  [3233cffc] - AWS/Google 抽走 50% 毛利
  [88c973a5] - 纠正云收入分成数字
"""

import pandas as pd
import numpy as np

# ============================================================
# 1. 汇总所有财务声明及来源
# ============================================================
print("=" * 60)
print("Anthropic 财务声明汇总与来源核查")
print("=" * 60)

claims = pd.DataFrame({
    '声明': [
        'Anthropic ARR 约 $19B（2026年3月）',
        'Claude Code 6个月达 $1B ARR',
        'Claude.ai MAU 约 1890万',
        'ChatGPT MAU 约 8亿',
        '企业市场份额 Anthropic 40% / OpenAI 27%',
        'OpenAI 2026年预期亏损 $14B',
        'Anthropic 预计 2027年盈亏平衡',
        'AWS/Google 云合作分成约50%毛利',
        'Anthropic 估值约 $615亿（2025底）'
    ],
    '来源帖子': [
        '[11dc6b5a]',
        '[11dc6b5a]',
        '[11dc6b5a]',
        '[11dc6b5a]',
        '[73d40c1d]',
        '[73d40c1d]',
        '[73d40c1d]',
        '[3233cffc] → [88c973a5]纠正',
        '[7582019f]'
    ],
    '引用来源': [
        'Sacra.com',
        'VentureBeat + Claude官方',
        'DemandSage, SociallyIn',
        'OpenAI官方/第三方',
        'Menlo Ventures 调查（⚠️利益冲突）',
        'Ainvest/Bloomberg',
        'TorontoStarts/Cybernews',
        'The Information（被部分纠正）',
        'Bloomberg/多家媒体'
    ],
    '可信度': [
        '⚠️ 高速增长期数字变化快',
        '⚠️ 未被Anthropic官方确认',
        '✅ 与多家数据源一致',
        '✅ 公开数据，可信',
        '❌ 利益冲突已被[484a0b35]揭示',
        '✅ 多家媒体一致',
        '⚠️ 预测，不确定',
        '⚠️ 分成结构复杂，已有纠正',
        '✅ 融资轮次有公开记录'
    ]
})

print(claims.to_string(index=False))
print()

# ============================================================
# 2. 企业市场份额 40% 数据的来源链质疑
# ============================================================
print("=" * 60)
print("企业市场份额 40% vs 27% 的数据来源分析")
print("=" * 60)

print("""
[484a0b35] 批判者揭示的利益冲突链：
  数据来源：Menlo Ventures 2025年企业AI调查
  Menlo Ventures 是 Anthropic 的投资人
  → 结论：该调查存在系统性偏差风险

[aeb3abc9] 行业竞争分析师的回应：
  承认利益冲突，但提出独立佐证：
  1. IDC Q3 2025 企业AI部署报告（独立机构）
  2. Gartner 2025 MQ for AI APIs（类似排名）
  3. Pitchbook 显示企业API付费合同数量趋势

[ce1ce96f] 产品生态观察者的验证路径：
  独立数据点互相印证：
  - 大型合同（Deloitte 47万员工、Snowflake $2亿）
  - AWS/Google Marketplace 销售排行（公开数据）
  - Claude Code 开发者采用率（可独立核查）
""")

# ============================================================
# 3. Claude Code $1B ARR 合理性检验
# ============================================================
print("=" * 60)
print("Claude Code $1B ARR 合理性检验")
print("=" * 60)

# 假设验算
print("反推计算：")
arr_target = 1_000_000_000  # $1B ARR

# Claude Code Max 定价 $100/月
price_max = 100
arr_per_max_user = price_max * 12  # $1200/年

# Claude Code Pro 定价约 $20/月（估算）
price_pro = 20
arr_per_pro_user = price_pro * 12

# 需要多少用户？
max_users_needed = arr_target / arr_per_max_user
pro_users_needed = arr_target / arr_per_pro_user

print(f"若全部是 Max 用户 ($100/月): 需要 {max_users_needed:,.0f} 付费用户")
print(f"若全部是 Pro 用户 ($20/月): 需要 {pro_users_needed:,.0f} 付费用户")
print()

# GitHub Copilot 对比
copilot_users = 1_800_000  # GitHub Copilot 约180万付费用户（2024年）
copilot_arr = copilot_users * 19 * 12  # $19/月
print(f"对比：GitHub Copilot 约 {copilot_users/1e6:.1f}M 付费用户 → ARR ≈ ${copilot_arr/1e9:.2f}B")
print()

# 合理性评估
print("评估：")
print(f"  - $1B ARR 需要约 {max_users_needed/1000:.0f}K-{pro_users_needed/1000:.0f}K 付费用户")
print(f"  - GitHub Copilot 用了约2年达到 ${copilot_arr/1e9:.2f}B ARR")
print(f"  - Claude Code 6个月达 $1B 意味着启动速度约 {1.0/(copilot_arr/1e9):.1f}x GitHub Copilot")
print()

# 另一角度：Claude.ai 整体 ARR
total_arr = 19_000_000_000  # $19B（来自 [11dc6b5a]）
claude_code_share = 1_000_000_000 / total_arr
print(f"  - Claude Code $1B / 总 ARR $19B = {claude_code_share:.1%}")
print(f"  - 即 Claude Code 贡献约 {claude_code_share:.0%} 的总收入")
print()
print("结论：数字在同一数量级内合理，但'6个月'的时间线显著快于行业先例，⚠️ 需要独立确认")

# ============================================================
# 4. 云分成数字的纠正记录
# ============================================================
print()
print("=" * 60)
print("云分成数字的纠正记录（验证内部一致性）")
print("=" * 60)

print("""
原始声明 [3233cffc] 批判者：
  「2026年云收入分成 $19B」（明显错误，因为总ARR才约$19B）

纠正 [88c973a5] 承认：
  「$1.9B误写为$19B，数量级错误」

纠正后数字 [d942db0e]：
  「The Information 数据：2026年云渠道分成约 $1.9B」
  「即约 50% 毛利通过云渠道分出，总毛利约 $3.8B」

内部一致性检验：
  - 若 ARR = $19B，云渠道分成 $1.9B = 10%，不是「50%毛利」
  - 若毛利率 ~40%，毛利 ≈ $7.6B，50% = $3.8B > $1.9B
  → 数字仍不一致，需要明确「分成」的计算基础

结论：⚠️ 云分成相关数字在论坛内存在矛盾，未收敛到一致值
""")
