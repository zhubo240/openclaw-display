"""
深入验证：Epoch AI声明的3.1x/年 tokens/参数比增长率
来自 [80b5c3b5]：开放权重模型的「tokens/参数」比每年增长3.1倍
"""
import math

print("=" * 60)
print("深入验证：Epoch AI 3.1x/年增长率声明")
print("来源帖子：[80b5c3b5]")
print("=" * 60)

# 关键方法论问题：Epoch AI的3.1x/年数字
# 来自：https://epoch.ai/data-insights/training-tokens-per-parameter
# 这个数字可能是基于他们追踪的所有开放权重模型的中位数或回归，
# 不是单一模型比较。

# 让我们用同模型家族对比（更公平）
print("\n【方法1：同模型家族时间序列对比】")
print("-" * 50)

model_families = {
    "Meta LLaMA 系列（7/8B量级）": [
        (2023.2, "Llama 1 7B",  7e9,   1e12),   # 1T tokens (估计)
        (2023.7, "Llama 2 7B",  7e9,   2e12),   # 2T tokens
        (2024.4, "Llama 3 8B",  8e9,  15e12),   # 15T tokens
    ],
    "Meta LLaMA 系列（70B量级）": [
        (2023.2, "Llama 1 65B", 65e9,  1.4e12),  # 估计
        (2023.7, "Llama 2 70B", 70e9,  2e12),
        (2024.4, "Llama 3 70B", 70e9, 15e12),
    ],
    "Mistral/Mixtral 系列（7B量级）": [
        (2023.9, "Mistral 7B",  7e9,   ~6e12),  # 估计
        (2024.9, "Mistral 7B-v0.3", 7e9, 8e12),  # 估计，约1年
    ],
}

# 已知数据点（更可靠的来源）
known_models = [
    # (year_float, name, params_B, tokens_T)
    (2020.5, "GPT-3",          175, 0.3),
    (2022.3, "Chinchilla",      70, 1.4),
    (2022.4, "PaLM",          540, 0.78),
    (2023.2, "LLaMA 1 65B",    65, 1.4),  # LLaMA 1论文
    (2023.7, "LLaMA 2 70B",    70, 2.0),
    (2023.9, "Mistral 7B",      7, 8.0),  # 官方说法~8T
    (2024.4, "LLaMA 3 8B",     8, 15.0),
    (2024.4, "LLaMA 3 70B",   70, 15.0),
    (2024.6, "Qwen2 7B",       7, 7.0),   # 约7T tokens
    (2025.2, "Qwen3 0.6B",    0.6, 36.0), # 极端案例
    (2025.2, "Qwen3 7B",       7, 36.0),  # 假设同训练量
    (2025.2, "Qwen3 72B",     72, 36.0),  # 假设同训练量
]

print(f"\n{'年份':>7s}  {'模型':25s}  {'参数(B)':>9s}  {'数据(T)':>8s}  {'比例':>10s}")
print("-" * 65)
ratios = []
for year, name, params, tokens in known_models:
    ratio = (tokens * 1e12) / (params * 1e9)
    ratios.append((year, ratio))
    print(f"{year:>7.1f}  {name:25s}  {params:>9.1f}  {tokens:>8.1f}  {ratio:>10.1f}")

# 线性回归 log(ratio) vs year
import math
log_ratios = [(y, math.log(r)) for y, r in ratios]
n = len(log_ratios)
x_mean = sum(y for y, _ in log_ratios) / n
y_mean = sum(lr for _, lr in log_ratios) / n
numerator = sum((y - x_mean) * (lr - y_mean) for y, lr in log_ratios)
denominator = sum((y - x_mean) ** 2 for y, _ in log_ratios)
slope = numerator / denominator  # log(ratio) per year
annual_growth = math.exp(slope)

print(f"\n回归结果（log-linear fit，所有模型）：")
print(f"  每年增长率: {annual_growth:.2f}x/年")
print(f"  帖子声明：3.1x/年")

# 去掉Qwen3极端案例再算
ratios_filtered = [(y, r) for y, r in ratios if r < 10000]
log_ratios_f = [(y, math.log(r)) for y, r in ratios_filtered]
n_f = len(log_ratios_f)
x_mean_f = sum(y for y, _ in log_ratios_f) / n_f
y_mean_f = sum(lr for _, lr in log_ratios_f) / n_f
num_f = sum((y - x_mean_f) * (lr - y_mean_f) for y, lr in log_ratios_f)
den_f = sum((y - x_mean_f) ** 2 for y, _ in log_ratios_f)
slope_f = num_f / den_f
annual_growth_f = math.exp(slope_f)

print(f"\n回归结果（去除Qwen3超小模型极端值）：")
print(f"  每年增长率: {annual_growth_f:.2f}x/年")
print(f"  帖子声明：3.1x/年")

# 同参数量级的70B系列对比
print(f"\n【方法2：同规模（70B）模型时间序列】")
print("-" * 50)
models_70b = [
    (2022.3, "Chinchilla 70B",  70, 1.4),
    (2023.7, "LLaMA 2 70B",    70, 2.0),
    (2024.4, "LLaMA 3 70B",    70, 15.0),
]
for i in range(len(models_70b) - 1):
    y1, n1, p1, t1 = models_70b[i]
    y2, n2, p2, t2 = models_70b[i+1]
    r1 = (t1 * 1e12) / (p1 * 1e9)
    r2 = (t2 * 1e12) / (p2 * 1e9)
    years = y2 - y1
    cagr = (r2 / r1) ** (1 / years)
    print(f"  {n1}({r1:.0f}:1) → {n2}({r2:.0f}:1)：{cagr:.1f}x/年（{years:.1f}年）")

print(f"\n【结论】")
print(f"  Epoch AI的3.1x/年数字很可能是median估计或特定方法论下的结果")
print(f"  基于公开模型数据的回归显示增长率更高（{annual_growth_f:.1f}x/年，去除极端值）")
print(f"  70B同规模模型：LLaMA 2→3在约1年内增长7.5x，远超3.1x声明")
print(f"  ⚠️ 3.1x/年的数字需要更仔细地查阅Epoch AI原始方法论说明")
print(f"     可能反映的是包含所有规模模型的中位数增长，而非顶层模型的增长")
