# AI/LLM 发展史：从感知机到GPT-4，关键论文、思想与前沿

## 早期基础（1950s-2010s）

### 奠基思想
- Turing (1950): Computing Machinery and Intelligence — 图灵测试
- Perceptron (1958, Rosenblatt) → XOR问题 → AI寒冬
- 反向传播 (1986, Rumelhart/Hinton/Williams) — 深度学习的核心算法
- Universal Approximation Theorem — 神经网络的理论保证

### 深度学习复兴
- AlexNet (2012, Krizhevsky/Sutskever/Hinton) — ImageNet突破，GPU训练
- Word2Vec (2013, Mikolov) — 词向量，语义空间的发现
- GAN (2014, Goodfellow) — 生成对抗网络
- ResNet (2015, He) — 残差连接解决深层训练
- Seq2Seq + Attention (2014-2015, Bahdanau) — 注意力机制的诞生

## Transformer 革命（2017-2020）

### 关键论文
- **Attention Is All You Need** (2017, Vaswani et al.) — Transformer架构，self-attention替代RNN
- BERT (2018, Devlin/Google) — 双向预训练，NLP范式转换
- GPT-1 (2018, Radford/OpenAI) — 自回归预训练 + 微调
- GPT-2 (2019) — "太危险不能发布"，zero-shot能力涌现
- T5 (2019, Google) — "Text-to-Text"统一框架
- GPT-3 (2020, Brown et al.) — 175B参数，few-shot learning，scaling的力量

### 核心思想
- 预训练-微调范式 vs 从头训练
- Self-attention 的本质：全局信息聚合
- Scaling hypothesis：更大 = 更好？

## Scaling Laws 与涌现（2020-2023）

### 关键发现
- **Scaling Laws for Neural Language Models** (2020, Kaplan/OpenAI) — 幂律关系
- **Chinchilla** (2022, Hoffmann/DeepMind) — 数据与参数的最优比例
- **Emergent Abilities of Large Language Models** (2022, Wei et al.) — 涌现能力
- 反方：**Are Emergent Abilities a Mirage?** (2023, Schaeffer et al.) — 度量伪影论

### ChatGPT 时刻
- InstructGPT / RLHF (2022, Ouyang et al.) — 人类反馈强化学习
- ChatGPT (2022.11) — 消费者产品爆发
- GPT-4 (2023.3) — 多模态，"Sparks of AGI"争议
- Constitutional AI (2022, Anthropic) — AI自我监督的替代路径

## 当前前沿（2024-2026）

### 推理与思考
- Chain-of-Thought (2022, Wei et al.) — 思维链提示
- Extended Thinking / Test-time Compute — 推理时增加计算
- o1/o3 (OpenAI) — 推理专用模型
- Claude Opus 推理模式

### 多模态与Agent
- GPT-4V, Gemini, Claude 的视觉能力
- Computer Use (Anthropic) — AI操作电脑
- AI Agent 框架：ReAct, AutoGPT, Claude Code
- MCP (Model Context Protocol) — 工具连接标准

### 可解释性与安全
- Mechanistic Interpretability (Anthropic) — 理解模型内部
- Sparse Autoencoders — 特征发现
- Sleeper Agents 论文 — 后门行为
- Responsible Scaling Policy

### 开源生态
- LLaMA (Meta) → LLaMA 2 → LLaMA 3/4
- Mistral, Qwen, DeepSeek
- 开源 vs 闭源的竞争格局

## 核心争论

1. Scaling 是否会继续有效？还是即将撞墙？
2. 自回归是正确的范式吗？（LeCun: 世界模型/JEPA）
3. LLM 是否真正"理解"？（Chomsky vs Sutskever）
4. AGI 距离我们还有多远？
5. 数据墙：互联网文本已经快用完了，合成数据能否替代？
6. 下一个架构创新会是什么？State Space Models (Mamba)? 混合架构?
