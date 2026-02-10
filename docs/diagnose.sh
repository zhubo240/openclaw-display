#!/usr/bin/env bash
# OpenClaw Agent 诊断脚本
# 自动跑完 6 步检查，输出 HTML 报告
# 用法: ./diagnose.sh [agent-id] [--open]
#   agent-id: 可选，指定检查哪个 agent（默认检查所有）
#   --open:   生成后自动打开浏览器

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPORT_FILE="$SCRIPT_DIR/report.html"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

AGENT_FILTER="${1:-}"
AUTO_OPEN=false
for arg in "$@"; do
  [[ "$arg" == "--open" ]] && AUTO_OPEN=true
done
[[ "$AGENT_FILTER" == "--open" ]] && AGENT_FILTER=""

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}OpenClaw 诊断${NC} — $(date '+%Y-%m-%d %H:%M:%S')"
echo "────────────────────────────────────"

# ── Step 1: Discord & Gateway status ──
echo -e "\n${BLUE}[Step 1]${NC} 检查 Gateway 和 Discord 连接..."
STEP1_RAW=$(openclaw status --deep 2>&1 || true)
STEP1_DISCORD="unknown"
STEP1_GATEWAY="unknown"
STEP1_SESSIONS=""
STEP1_PASS=false

if echo "$STEP1_RAW" | grep -q "Discord.*OK"; then
  STEP1_DISCORD="OK"
fi
if echo "$STEP1_RAW" | grep -q "Gateway.*reachable"; then
  STEP1_GATEWAY="reachable"
fi
STEP1_SESSIONS=$(echo "$STEP1_RAW" | grep "Sessions" | head -1 || true)

if [[ "$STEP1_DISCORD" == "OK" && "$STEP1_GATEWAY" == "reachable" ]]; then
  STEP1_PASS=true
  echo -e "  ${GREEN}PASS${NC} — Discord: $STEP1_DISCORD, Gateway: $STEP1_GATEWAY"
else
  echo -e "  ${RED}FAIL${NC} — Discord: $STEP1_DISCORD, Gateway: $STEP1_GATEWAY"
fi

# ── Step 2: Recent cli exec entries ──
echo -e "\n${BLUE}[Step 2]${NC} 检查最近 cli exec 记录..."
LOGS_RAW=$(openclaw logs --max-bytes 50000 2>&1 || true)
CLI_EXECS=$(echo "$LOGS_RAW" | grep "cli exec" | tail -10 || true)
if [[ -z "$CLI_EXECS" ]]; then
  STEP2_COUNT=0
else
  STEP2_COUNT=$(echo "$CLI_EXECS" | wc -l | tr -d ' ')
fi
STEP2_PASS=false

if [[ "$STEP2_COUNT" -gt 0 ]]; then
  STEP2_PASS=true
  echo -e "  ${GREEN}PASS${NC} — 找到 $STEP2_COUNT 条 cli exec 记录"
else
  echo -e "  ${RED}FAIL${NC} — 没有找到 cli exec 记录"
fi

# ── Step 3: Serialization delay check ──
echo -e "\n${BLUE}[Step 3]${NC} 检查串行队列延迟..."
STEP3_PASS=true
STEP3_DELAYS=""
SERIALIZE_VAL=$(python3 -c "
import json,sys
try:
  cfg=json.load(open('$HOME/.openclaw/openclaw.json'))
  backends=cfg.get('agents',{}).get('defaults',{}).get('cliBackends',{})
  for name,b in backends.items():
    ser=b.get('serialize', True)
    print(f'{name}: serialize={ser}')
except: print('error reading config')
" 2>/dev/null || echo "error")

if echo "$SERIALIZE_VAL" | grep -q "serialize=True"; then
  STEP3_PASS=false
  STEP3_DELAYS="serialize=true (所有 agent 串行执行)"
  echo -e "  ${RED}WARN${NC} — $STEP3_DELAYS"
else
  STEP3_DELAYS="serialize=false (并发执行)"
  echo -e "  ${GREEN}PASS${NC} — $STEP3_DELAYS"
fi

# Check for slow listener warnings
SLOW_LISTENER_LINES=$(echo "$LOGS_RAW" | grep "Slow listener" || true)
if [[ -z "$SLOW_LISTENER_LINES" ]]; then
  SLOW_LISTENERS=0
else
  SLOW_LISTENERS=$(echo "$SLOW_LISTENER_LINES" | wc -l | tr -d ' ')
fi
if [[ "$SLOW_LISTENERS" -gt 0 ]]; then
  echo -e "  ${YELLOW}WARN${NC} — $SLOW_LISTENERS 次 Slow listener 警告"
fi

# ── Step 4: CLI response check ──
echo -e "\n${BLUE}[Step 4]${NC} 检查 Claude CLI 响应..."
STEP4_PASS=true
STEP4_DETAILS=""

# Check for errors in logs
CLI_ERRORS=$(echo "$LOGS_RAW" | grep -iE "cli.*(error|fail|timeout|EPIPE)" | tail -5 || true)
if [[ -z "$CLI_ERRORS" ]]; then
  CLI_ERROR_COUNT=0
else
  CLI_ERROR_COUNT=$(echo "$CLI_ERRORS" | wc -l | tr -d ' ')
fi

if [[ "$CLI_ERROR_COUNT" -gt 0 ]]; then
  STEP4_PASS=false
  STEP4_DETAILS="发现 $CLI_ERROR_COUNT 条 CLI 错误"
  echo -e "  ${RED}FAIL${NC} — $STEP4_DETAILS"
else
  STEP4_DETAILS="无 CLI 错误"
  echo -e "  ${GREEN}PASS${NC} — $STEP4_DETAILS"
fi

# ── Step 5: NO_REPLY / HEARTBEAT_OK check ──
echo -e "\n${BLUE}[Step 5]${NC} 检查静默过滤 (NO_REPLY / HEARTBEAT_OK)..."
STEP5_PASS=true
STEP5_DETAILS=""
SILENT_SESSIONS=""

# Find recent session files and check for silent responses
JSONL_FILES=$(find "$HOME/.claude/projects" -path "*openclaw-workspace*" -name "*.jsonl" -newer /tmp/.openclaw-diag-marker 2>/dev/null || \
  find "$HOME/.claude/projects" -path "*openclaw-workspace*" -name "*.jsonl" -mmin -60 2>/dev/null || true)

touch /tmp/.openclaw-diag-marker 2>/dev/null || true

for f in $JSONL_FILES; do
  WORKSPACE=$(echo "$f" | sed 's/.*openclaw-workspace-\{0,1\}//' | cut -d/ -f1)
  [[ -z "$WORKSPACE" ]] && WORKSPACE="default"

  # Get the last assistant response
  LAST_RESPONSE=$(grep '"role":"assistant"' "$f" 2>/dev/null | tail -1 || true)
  if [[ -n "$LAST_RESPONSE" ]]; then
    RESPONSE_TEXT=$(echo "$LAST_RESPONSE" | python3 -c "
import json,sys
try:
  data=json.loads(sys.stdin.read())
  msg=data.get('message',data)
  for c in msg.get('content',[]):
    if c.get('type')=='text':
      print(c.get('text',''))
      break
except: pass
" 2>/dev/null || true)

    if [[ "$RESPONSE_TEXT" == "HEARTBEAT_OK" || "$RESPONSE_TEXT" == "NO_REPLY" ]]; then
      STEP5_PASS=false
      SILENT_SESSIONS="$SILENT_SESSIONS\n  - $WORKSPACE: $RESPONSE_TEXT"
    fi
  fi
done

if [[ "$STEP5_PASS" == true ]]; then
  STEP5_DETAILS="最近 session 无静默过滤"
  echo -e "  ${GREEN}PASS${NC} — $STEP5_DETAILS"
else
  STEP5_DETAILS="发现静默响应:"
  echo -e "  ${RED}FAIL${NC} — $STEP5_DETAILS"
  echo -e "$SILENT_SESSIONS"
fi

# ── Step 6: Delivery check ──
echo -e "\n${BLUE}[Step 6]${NC} 检查消息送达..."
STEP6_PASS=true
DELIVER_LINES=$(echo "$LOGS_RAW" | grep -iE "deliver|discord.*send|discord.*message" | tail -5 || true)
DELIVER_ERRORS=$(echo "$LOGS_RAW" | grep -iE "deliver.*(error|fail)|discord.*(error|rate)" | tail -5 || true)
if [[ -z "$DELIVER_ERRORS" ]]; then
  DELIVER_ERROR_COUNT=0
else
  DELIVER_ERROR_COUNT=$(echo "$DELIVER_ERRORS" | wc -l | tr -d ' ')
fi

if [[ "$DELIVER_ERROR_COUNT" -gt 0 ]]; then
  STEP6_PASS=false
  echo -e "  ${RED}FAIL${NC} — 发现 $DELIVER_ERROR_COUNT 条投递错误"
else
  echo -e "  ${GREEN}PASS${NC} — 无投递错误"
fi

# ── Per-agent status ──
echo -e "\n${BLUE}[Agent 状态]${NC}"
AGENT_STATUS=$(echo "$STEP1_RAW" | sed -n '/^Sessions$/,/^$/p' || true)
if [[ -z "$AGENT_STATUS" ]]; then
  AGENT_STATUS=$(echo "$STEP1_RAW" | grep -A20 "Sessions" | head -20 || true)
fi

AGENT_ROWS=""
# Parse session info from status
while IFS= read -r line; do
  if echo "$line" | grep -q "agent:"; then
    AGENT_NAME=$(echo "$line" | sed 's/.*agent:\([^:]*\).*/\1/' | head -c 20)
    AGENT_AGE=$(echo "$line" | grep -oE '[0-9]+[mhd] ago' || echo "?")
    AGENT_TOKENS=$(echo "$line" | grep -oE '[0-9]+k/[0-9]+k \([0-9]+%\)' || echo "?")
    AGENT_ROWS="$AGENT_ROWS<tr><td>$AGENT_NAME</td><td>$AGENT_AGE</td><td>$AGENT_TOKENS</td></tr>"
    echo -e "  $AGENT_NAME — $AGENT_AGE — $AGENT_TOKENS"
  fi
done <<< "$(echo "$STEP1_RAW")"

# ── Summary ──
echo -e "\n────────────────────────────────────"
TOTAL_PASS=0
TOTAL_FAIL=0
for s in "$STEP1_PASS" "$STEP2_PASS" "$STEP3_PASS" "$STEP4_PASS" "$STEP5_PASS" "$STEP6_PASS"; do
  [[ "$s" == true ]] && ((TOTAL_PASS++)) || ((TOTAL_FAIL++))
done
echo -e "结果: ${GREEN}$TOTAL_PASS PASS${NC}  ${RED}$TOTAL_FAIL FAIL${NC}"

# ── Escape HTML helper ──
html_escape() {
  echo "$1" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g; s/"/\&quot;/g'
}

# ── Generate HTML Report ──
step_class() { [[ "$1" == true ]] && echo "pass" || echo "fail"; }
step_icon() { [[ "$1" == true ]] && echo "&#10003;" || echo "&#10007;"; }
step_label() { [[ "$1" == true ]] && echo "PASS" || echo "FAIL"; }

CLI_EXECS_ESCAPED=$(html_escape "$CLI_EXECS")
CLI_ERRORS_ESCAPED=$(html_escape "$CLI_ERRORS")

cat > "$REPORT_FILE" << 'HTMLHEAD'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OpenClaw 诊断报告</title>
<style>
  :root { --bg:#0d1117; --card:#161b22; --border:#30363d; --text:#e6edf3; --muted:#8b949e; --green:#3fb950; --red:#f85149; --yellow:#d29922; --blue:#58a6ff; --purple:#bc8cff; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif; background:var(--bg); color:var(--text); line-height:1.6; padding:1.5rem; max-width:960px; margin:0 auto; }
  h1 { font-size:1.5rem; margin-bottom:0.2rem; }
  .meta { color:var(--muted); font-size:0.85rem; margin-bottom:1.5rem; }
  .summary { display:flex; gap:1rem; margin-bottom:1.5rem; }
  .summary-card { flex:1; background:var(--card); border:1px solid var(--border); border-radius:8px; padding:1rem; text-align:center; }
  .summary-card.pass { border-color:var(--green); }
  .summary-card.fail { border-color:var(--red); }
  .summary-num { font-size:2rem; font-weight:800; }
  .summary-card.pass .summary-num { color:var(--green); }
  .summary-card.fail .summary-num { color:var(--red); }
  .summary-label { font-size:0.8rem; color:var(--muted); }

  .step { background:var(--card); border:1px solid var(--border); border-radius:8px; margin-bottom:0.75rem; overflow:hidden; }
  .step.pass { border-left:3px solid var(--green); }
  .step.fail { border-left:3px solid var(--red); }
  .step.warn { border-left:3px solid var(--yellow); }
  .step-header { display:flex; align-items:center; gap:0.6rem; padding:0.75rem 1rem; cursor:pointer; }
  .step-header:hover { background:rgba(255,255,255,0.02); }
  .step-icon { font-size:1.1rem; flex-shrink:0; }
  .step.pass .step-icon { color:var(--green); }
  .step.fail .step-icon { color:var(--red); }
  .step.warn .step-icon { color:var(--yellow); }
  .step-num { background:var(--blue); color:#fff; font-size:0.65rem; font-weight:700; padding:0.1rem 0.4rem; border-radius:10px; flex-shrink:0; }
  .step-title { font-weight:600; font-size:0.9rem; flex:1; }
  .step-badge { font-size:0.7rem; font-weight:700; padding:0.1rem 0.5rem; border-radius:10px; }
  .step.pass .step-badge { background:rgba(63,185,80,0.15); color:var(--green); }
  .step.fail .step-badge { background:rgba(248,81,73,0.15); color:var(--red); }
  .step.warn .step-badge { background:rgba(210,153,34,0.15); color:var(--yellow); }
  .arrow { color:var(--muted); transition:transform 0.2s; font-size:0.75rem; }
  .step.open .arrow { transform:rotate(90deg); }
  .step-body { display:none; padding:0 1rem 0.8rem; font-size:0.85rem; }
  .step.open .step-body { display:block; }
  .log-block { background:var(--bg); border:1px solid var(--border); border-radius:6px; padding:0.6rem 0.8rem; margin:0.5rem 0; font-family:'SF Mono',Monaco,Consolas,monospace; font-size:0.75rem; overflow-x:auto; white-space:pre-wrap; word-break:break-all; color:var(--muted); max-height:200px; overflow-y:auto; }
  .detail { margin:0.4rem 0; }
  .detail strong { color:var(--blue); }

  .seq { display:flex; flex-direction:column; align-items:center; margin:1.5rem 0; }
  .seq-flow { display:flex; gap:0; align-items:stretch; width:100%; }
  .seq-node { flex:1; text-align:center; padding:0.6rem 0.3rem; border:1px solid var(--border); font-size:0.7rem; font-weight:600; position:relative; }
  .seq-node::after { content:'→'; position:absolute; right:-8px; top:50%; transform:translateY(-50%); color:var(--muted); font-size:0.9rem; z-index:1; }
  .seq-node:last-child::after { display:none; }
  .seq-node.pass { background:rgba(63,185,80,0.08); border-color:var(--green); color:var(--green); }
  .seq-node.fail { background:rgba(248,81,73,0.08); border-color:var(--red); color:var(--red); }
  .seq-node.warn { background:rgba(210,153,34,0.08); border-color:var(--yellow); color:var(--yellow); }
  .seq-node.skip { opacity:0.3; }
  .seq-node:first-child { border-radius:6px 0 0 6px; }
  .seq-node:last-child { border-radius:0 6px 6px 0; }

  table { width:100%; border-collapse:collapse; margin:0.5rem 0; }
  th,td { padding:0.4rem 0.6rem; text-align:left; border-bottom:1px solid var(--border); font-size:0.8rem; }
  th { color:var(--muted); font-weight:600; }

  footer { margin-top:2rem; padding-top:1rem; border-top:1px solid var(--border); color:var(--muted); font-size:0.75rem; text-align:center; }
</style>
</head>
<body>
HTMLHEAD

cat >> "$REPORT_FILE" << EOF
<h1>OpenClaw 诊断报告</h1>
<p class="meta">$(date '+%Y-%m-%d %H:%M:%S') · $(hostname)</p>

<div class="summary">
  <div class="summary-card pass">
    <div class="summary-num">$TOTAL_PASS</div>
    <div class="summary-label">PASS</div>
  </div>
  <div class="summary-card fail">
    <div class="summary-num">$TOTAL_FAIL</div>
    <div class="summary-label">FAIL</div>
  </div>
</div>

<!-- Sequence flow -->
<div class="seq">
  <div class="seq-flow">
    <div class="seq-node $(step_class $STEP1_PASS)">1. Discord<br>→ Gateway</div>
    <div class="seq-node $(step_class $STEP2_PASS)">2. Gateway<br>→ Agent</div>
    <div class="seq-node $(step_class $STEP3_PASS)">3. Queue<br>serialize</div>
    <div class="seq-node $(step_class $STEP4_PASS)">4. Claude<br>CLI</div>
    <div class="seq-node $(step_class $STEP5_PASS)">5. NO_REPLY<br>过滤</div>
    <div class="seq-node $(step_class $STEP6_PASS)">6. → Discord<br>送达</div>
  </div>
</div>

<!-- Step 1 -->
<div class="step $(step_class $STEP1_PASS) open" onclick="this.classList.toggle('open')">
  <div class="step-header">
    <span class="step-icon">$(step_icon $STEP1_PASS)</span>
    <span class="step-num">Step 1</span>
    <span class="step-title">Gateway & Discord 连接</span>
    <span class="step-badge">$(step_label $STEP1_PASS)</span>
    <span class="arrow">&#9654;</span>
  </div>
  <div class="step-body">
    <div class="detail"><strong>Discord:</strong> $STEP1_DISCORD</div>
    <div class="detail"><strong>Gateway:</strong> $STEP1_GATEWAY</div>
    <div class="detail"><strong>Sessions:</strong> $(html_escape "$STEP1_SESSIONS")</div>
  </div>
</div>

<!-- Step 2 -->
<div class="step $(step_class $STEP2_PASS)" onclick="this.classList.toggle('open')">
  <div class="step-header">
    <span class="step-icon">$(step_icon $STEP2_PASS)</span>
    <span class="step-num">Step 2</span>
    <span class="step-title">Agent 路由 (cli exec)</span>
    <span class="step-badge">$(step_label $STEP2_PASS)</span>
    <span class="arrow">&#9654;</span>
  </div>
  <div class="step-body">
    <div class="detail"><strong>最近 cli exec:</strong> $STEP2_COUNT 条</div>
    <div class="log-block">$CLI_EXECS_ESCAPED</div>
  </div>
</div>

<!-- Step 3 -->
<div class="step $(step_class $STEP3_PASS)" onclick="this.classList.toggle('open')">
  <div class="step-header">
    <span class="step-icon">$(step_icon $STEP3_PASS)</span>
    <span class="step-num">Step 3</span>
    <span class="step-title">串行队列 (serialize)</span>
    <span class="step-badge">$(step_label $STEP3_PASS)</span>
    <span class="arrow">&#9654;</span>
  </div>
  <div class="step-body">
    <div class="detail"><strong>配置:</strong> $(html_escape "$SERIALIZE_VAL")</div>
    <div class="detail"><strong>Slow listener 警告:</strong> $SLOW_LISTENERS 次</div>
  </div>
</div>

<!-- Step 4 -->
<div class="step $(step_class $STEP4_PASS)" onclick="this.classList.toggle('open')">
  <div class="step-header">
    <span class="step-icon">$(step_icon $STEP4_PASS)</span>
    <span class="step-num">Step 4</span>
    <span class="step-title">Claude CLI 响应</span>
    <span class="step-badge">$(step_label $STEP4_PASS)</span>
    <span class="arrow">&#9654;</span>
  </div>
  <div class="step-body">
    <div class="detail"><strong>状态:</strong> $STEP4_DETAILS</div>
$(if [[ -n "$CLI_ERRORS" ]]; then echo "    <div class=\"log-block\">$CLI_ERRORS_ESCAPED</div>"; fi)
  </div>
</div>

<!-- Step 5 -->
<div class="step $(step_class $STEP5_PASS)" onclick="this.classList.toggle('open')">
  <div class="step-header">
    <span class="step-icon">$(step_icon $STEP5_PASS)</span>
    <span class="step-num">Step 5</span>
    <span class="step-title">静默过滤 (NO_REPLY / HEARTBEAT_OK)</span>
    <span class="step-badge">$(step_label $STEP5_PASS)</span>
    <span class="arrow">&#9654;</span>
  </div>
  <div class="step-body">
    <div class="detail"><strong>状态:</strong> $STEP5_DETAILS</div>
$(if [[ -n "$SILENT_SESSIONS" ]]; then echo "    <div class=\"log-block\">$(echo -e "$SILENT_SESSIONS")</div>"; fi)
  </div>
</div>

<!-- Step 6 -->
<div class="step $(step_class $STEP6_PASS)" onclick="this.classList.toggle('open')">
  <div class="step-header">
    <span class="step-icon">$(step_icon $STEP6_PASS)</span>
    <span class="step-num">Step 6</span>
    <span class="step-title">Discord 送达</span>
    <span class="step-badge">$(step_label $STEP6_PASS)</span>
    <span class="arrow">&#9654;</span>
  </div>
  <div class="step-body">
    <div class="detail"><strong>投递错误:</strong> $DELIVER_ERROR_COUNT 条</div>
  </div>
</div>

<!-- Agent table -->
<h2 style="font-size:1.1rem;margin:1.5rem 0 0.5rem;">Agent 状态</h2>
<table>
  <tr><th>Agent</th><th>最近活跃</th><th>Token 用量</th></tr>
  $AGENT_ROWS
</table>

<footer>
  <p>由 <code>openclaw-diagnose.sh</code> 自动生成 · <a href="index.html" style="color:var(--blue);">决策树参考</a></p>
</footer>

</body>
</html>
EOF

echo -e "\n${GREEN}报告已生成:${NC} $REPORT_FILE"

if [[ "$AUTO_OPEN" == true ]]; then
  open "$REPORT_FILE" 2>/dev/null || xdg-open "$REPORT_FILE" 2>/dev/null || echo "请手动打开: $REPORT_FILE"
fi
