# Anthropic 深度研究：产品、技术、论文与实现

## 公司背景
- Dario Amodei & Daniela Amodei 创立，核心团队从 OpenAI 出走
- 融资历程：Google、Amazon 领投，估值演变
- 公司使命："AI safety" 公司，但同时是前沿模型竞争者

## 产品线
- Claude 模型家族：Haiku / Sonnet / Opus，各代演进（Claude 1→2→3→3.5→4→4.5/4.6）
- Claude.ai（消费端产品）
- Claude API / Anthropic SDK
- Claude Code（CLI 开发工具）
- Claude for Enterprise
- 定价策略与商业模式

## 核心技术与论文

### Constitutional AI (CAI)
- 核心思想：用 AI 自我监督替代人工标注
- 论文：Constitutional AI: Harmlessness from AI Feedback
- 与 RLHF 的区别和优势

### 上下文窗口
- 从 100K 到 200K 到 1M context，技术实现
- 长上下文的实际表现（Needle in a Haystack 测试）

### 模型能力
- Artifacts / 工具使用 / Computer Use
- Extended thinking（深度推理模式）
- MCP (Model Context Protocol) — 开放标准
- Claude Code 的 agentic 能力

### 安全研究
- Responsible Scaling Policy (RSP)
- Interpretability 研究：Sparse Autoencoders、特征可视化
- 对齐税（alignment tax）的思考
- Sleeper agents 论文：后门行为研究

### 训练方法
- RLHF vs RLAIF（AI feedback）
- 预训练数据策略（与 OpenAI/Google 的差异）
- 模型规模与 scaling laws

## 讨论方向
1. Anthropic 的技术护城河是什么？vs OpenAI、Google、Meta
2. "安全优先"的商业策略是真诚的还是营销手段？
3. Claude 模型的实际优劣势：coding、推理、创意、多语言
4. MCP 能否成为 AI 工具生态的标准？
5. Anthropic 的商业可持续性：烧钱速度 vs 收入增长
6. 下一代模型（Claude 5?）可能的突破方向
7. Interpretability 研究的实际价值：学术意义 vs 实用价值
