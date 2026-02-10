#!/usr/bin/env bash
# OpenClaw Agent 诊断脚本 (v2)
# 按 agent 维度检查，输出 HTML 报告
# 用法: ./diagnose.sh <agent1> [agent2 ...] [--open] [--all]
#   agent:  指定检查的 agent 名称（必须至少一个，或用 --all）
#   --open: 生成后自动打开浏览器
#   --all:  检查所有活跃 agent
#
# 示例:
#   ./diagnose.sh butler us-mean-reversion
#   ./diagnose.sh --all --open
#   ./diagnose.sh realestate

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPORT_FILE="$SCRIPT_DIR/report.html"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
DIAG_TIME=$(date '+%Y-%m-%d %H:%M:%S')

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'; BOLD='\033[1m'

# Parse args
AUTO_OPEN=false
ALL_AGENTS=false
AGENTS=()
for arg in "$@"; do
  case "$arg" in
    --open) AUTO_OPEN=true ;;
    --all)  ALL_AGENTS=true ;;
    -*)     echo "Unknown option: $arg"; exit 1 ;;
    *)      AGENTS+=("$arg") ;;
  esac
done

# Collect global data first
echo -e "${BLUE}${BOLD}OpenClaw 诊断${NC} — $DIAG_TIME"
echo "────────────────────────────────────"

STATUS_RAW=$(openclaw status --deep 2>&1 || true)
LOGS_RAW=$(openclaw logs --max-bytes 200000 2>&1 || true)

# ── Global: Discord & Gateway ──
echo -e "\n${BLUE}[全局]${NC} 检查 Gateway 和 Discord 连接..."
DISCORD_OK=false; GATEWAY_OK=false
echo "$STATUS_RAW" | grep -q "Discord.*OK" && DISCORD_OK=true
echo "$STATUS_RAW" | grep -q "Gateway.*reachable" && GATEWAY_OK=true
GLOBAL_CONN_PASS=false
if [[ "$DISCORD_OK" == true && "$GATEWAY_OK" == true ]]; then
  GLOBAL_CONN_PASS=true
  echo -e "  ${GREEN}PASS${NC} — Discord: OK, Gateway: reachable"
else
  echo -e "  ${RED}FAIL${NC} — Discord: $DISCORD_OK, Gateway: $GATEWAY_OK"
fi

# ── Global: serialize config ──
SERIALIZE_VAL=$(python3 -c "
import json
try:
  cfg=json.load(open('$HOME/.openclaw/openclaw.json'))
  backends=cfg.get('agents',{}).get('defaults',{}).get('cliBackends',{})
  for name,b in backends.items():
    ser=b.get('serialize', True)
    print(f'{name}: serialize={ser}')
except: print('error reading config')
" 2>/dev/null || echo "error")
SERIALIZE_PASS=true
if echo "$SERIALIZE_VAL" | grep -q "serialize=True"; then
  SERIALIZE_PASS=false
fi

# ── Resolve agent list ──
if [[ "$ALL_AGENTS" == true ]]; then
  # Extract agent names from session table
  while IFS= read -r line; do
    if [[ "$line" =~ agent:([a-zA-Z0-9_-]+): ]]; then
      AGENTS+=("${BASH_REMATCH[1]}")
    fi
  done <<< "$(echo "$STATUS_RAW" | grep "agent:")"
fi

if [[ ${#AGENTS[@]} -eq 0 ]]; then
  echo -e "\n${RED}错误: 请指定至少一个 agent 名称，或使用 --all${NC}"
  echo "用法: $0 <agent1> [agent2 ...] [--open] [--all]"
  echo ""
  echo "可用 agent:"
  echo "$STATUS_RAW" | grep "agent:" | sed 's/.*agent:\([^:]*\):.*/  \1/' | sort -u
  exit 1
fi

# Deduplicate
AGENTS=($(printf '%s\n' "${AGENTS[@]}" | sort -u))

echo -e "\n${CYAN}诊断 agent:${NC} ${AGENTS[*]}"
echo "────────────────────────────────────"

# ── Per-agent diagnostics ──
html_escape() {
  echo "$1" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g; s/"/\&quot;/g'
}

TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_WARN=0
AGENT_HTML=""

for AGENT in "${AGENTS[@]}"; do
  echo -e "\n${BOLD}${CYAN}━━ $AGENT ━━${NC}"
  A_PASS=0; A_FAIL=0; A_WARN=0

  # ── 1. Session status ──
  SESSION_LINE=$(echo "$STATUS_RAW" | grep "agent:${AGENT}:" || true)
  SESSION_AGE="未找到"; SESSION_TOKENS="未知"; TOKEN_PCT=0
  S1_PASS=true; S1_DETAIL=""

  if [[ -n "$SESSION_LINE" ]]; then
    SESSION_AGE=$(echo "$SESSION_LINE" | grep -oE '[0-9]+[mhd] ago' || echo "?")
    SESSION_TOKENS=$(echo "$SESSION_LINE" | grep -oE '[0-9]+k/[0-9]+k \([0-9]+%\)' || echo "?")
    TOKEN_PCT=$(echo "$SESSION_TOKENS" | grep -oE '[0-9]+%' | tr -d '%' || echo "0")
    TOKEN_PCT=${TOKEN_PCT:-0}

    if [[ "$TOKEN_PCT" -ge 90 ]]; then
      S1_PASS=false
      S1_DETAIL="Token $SESSION_TOKENS — 即将满！需要清 session"
      echo -e "  ${RED}[Session] FAIL${NC} — $S1_DETAIL"
      ((A_FAIL++))
    elif [[ "$TOKEN_PCT" -ge 75 ]]; then
      S1_DETAIL="Token $SESSION_TOKENS — 偏高"
      echo -e "  ${YELLOW}[Session] WARN${NC} — $S1_DETAIL"
      ((A_WARN++))
    else
      S1_DETAIL="Token $SESSION_TOKENS — 正常, 最近活跃 $SESSION_AGE"
      echo -e "  ${GREEN}[Session] PASS${NC} — $S1_DETAIL"
      ((A_PASS++))
    fi
  else
    S1_PASS=false
    S1_DETAIL="agent session 未找到（可能未启动或名称错误）"
    echo -e "  ${RED}[Session] FAIL${NC} — $S1_DETAIL"
    ((A_FAIL++))
  fi

  # ── 2. CLI exec activity ──
  # Look for cli exec entries that might be for this agent
  # Logs don't include agent name in cli exec, so we check OpenClaw session files
  CLI_EXEC_LINES=$(echo "$LOGS_RAW" | grep "cli exec" | tail -20 || true)
  if [[ -z "$CLI_EXEC_LINES" ]]; then
    CLI_EXEC_COUNT=0
  else
    CLI_EXEC_COUNT=$(echo "$CLI_EXEC_LINES" | wc -l | tr -d ' ')
  fi
  S2_PASS=true
  if [[ "$CLI_EXEC_COUNT" -gt 0 ]]; then
    echo -e "  ${GREEN}[CLI exec] PASS${NC} — 全局 $CLI_EXEC_COUNT 条 cli exec 记录"
    ((A_PASS++))
  else
    S2_PASS=false
    echo -e "  ${RED}[CLI exec] FAIL${NC} — 无 cli exec 记录"
    ((A_FAIL++))
  fi

  # ── 3. CLI errors (agent-level) ──
  # Check for errors. The "Embedded agent failed" line includes agent context nearby
  # Also look for stderr/stdout from the CLI process
  CLI_ERRORS=$(echo "$LOGS_RAW" | grep -iE "(Embedded agent failed|CLI failed|FailoverError|cli.*(error|timeout|EPIPE))" | tail -10 || true)
  S3_PASS=true; S3_DETAIL=""; CLI_ERROR_CONTEXT=""

  if [[ -z "$CLI_ERRORS" ]]; then
    CLI_ERROR_COUNT=0
    S3_DETAIL="无 CLI 错误"
    echo -e "  ${GREEN}[CLI 错误] PASS${NC} — $S3_DETAIL"
    ((A_PASS++))
  else
    CLI_ERROR_COUNT=$(echo "$CLI_ERRORS" | wc -l | tr -d ' ')
    S3_PASS=false
    S3_DETAIL="发现 $CLI_ERROR_COUNT 条 CLI 错误"
    echo -e "  ${RED}[CLI 错误] FAIL${NC} — $S3_DETAIL"
    ((A_FAIL++))

    # Extract more context: get ±5 lines around each error
    CLI_ERROR_CONTEXT=$(echo "$LOGS_RAW" | grep -B5 -A5 -iE "(Embedded agent failed|CLI failed|FailoverError)" | head -60 || true)

    # Check for specific patterns
    if echo "$CLI_ERROR_CONTEXT" | grep -q "code 1005"; then
      echo -e "    ${YELLOW}↳ 原因: Discord WebSocket 断连 (code 1005) 期间 CLI 请求失败${NC}"
    fi
    if echo "$CLI_ERROR_CONTEXT" | grep -q "EPIPE"; then
      echo -e "    ${YELLOW}↳ 原因: CLI 进程管道中断 (EPIPE)${NC}"
    fi
    if echo "$CLI_ERROR_CONTEXT" | grep -q "timeout"; then
      echo -e "    ${YELLOW}↳ 原因: CLI 响应超时${NC}"
    fi
    if echo "$CLI_ERROR_CONTEXT" | grep -q "rate.limit\|429"; then
      echo -e "    ${YELLOW}↳ 原因: API 速率限制${NC}"
    fi
    if echo "$CLI_ERROR_CONTEXT" | grep -q "socket hang up"; then
      echo -e "    ${YELLOW}↳ 原因: 网络连接中断 (socket hang up)${NC}"
    fi

    # Check for verbose stderr/stdout near the error
    CLI_STDERR=$(echo "$LOGS_RAW" | grep -A2 "cli stderr" | head -10 || true)
    if [[ -n "$CLI_STDERR" ]]; then
      echo -e "    ${YELLOW}↳ CLI stderr:${NC}"
      echo "$CLI_STDERR" | head -5 | sed 's/^/      /'
    fi
  fi

  # ── 4. NO_REPLY / HEARTBEAT_OK check (agent-specific) ──
  S4_PASS=true; S4_DETAIL=""; SILENT_INFO=""
  # Check Claude session files for this specific agent
  AGENT_JSONL=$(find "$HOME/.claude/projects" -path "*openclaw*" -name "*.jsonl" -mmin -120 2>/dev/null | xargs grep -l "\"$AGENT\"" 2>/dev/null || true)
  # Also check OpenClaw session store
  OC_SESSION_FILE="$HOME/.openclaw/agents/main/sessions/sessions.json"

  if [[ -n "$AGENT_JSONL" ]]; then
    for f in $AGENT_JSONL; do
      LAST_RESP=$(grep '"role":"assistant"' "$f" 2>/dev/null | tail -1 || true)
      if [[ -n "$LAST_RESP" ]]; then
        RESP_TEXT=$(echo "$LAST_RESP" | python3 -c "
import json,sys
try:
  data=json.loads(sys.stdin.read())
  msg=data.get('message',data)
  for c in msg.get('content',[]):
    if c.get('type')=='text':
      t=c.get('text','').strip()
      if t: print(t[:200]); break
except: pass
" 2>/dev/null || true)

        if [[ "$RESP_TEXT" == "HEARTBEAT_OK" || "$RESP_TEXT" == "NO_REPLY" ]]; then
          S4_PASS=false
          SILENT_INFO="最后响应: $RESP_TEXT"
        fi
      fi
    done
  fi

  if [[ "$S4_PASS" == true ]]; then
    S4_DETAIL="无静默过滤"
    echo -e "  ${GREEN}[静默检查] PASS${NC} — $S4_DETAIL"
    ((A_PASS++))
  else
    S4_DETAIL="检测到静默响应: $SILENT_INFO"
    echo -e "  ${RED}[静默检查] FAIL${NC} — $S4_DETAIL"
    ((A_FAIL++))
  fi

  # ── 5. Delivery check (Discord errors) ──
  DELIVER_ERRORS=$(echo "$LOGS_RAW" | grep -iE "deliver.*(error|fail)|discord.*(error|rate)" | tail -5 || true)
  S5_PASS=true; S5_DETAIL=""
  if [[ -z "$DELIVER_ERRORS" ]]; then
    S5_DETAIL="无投递错误"
    echo -e "  ${GREEN}[送达] PASS${NC} — $S5_DETAIL"
    ((A_PASS++))
  else
    DELIVER_COUNT=$(echo "$DELIVER_ERRORS" | wc -l | tr -d ' ')
    # Check if socket hang up (network issue, not agent issue)
    SOCKET_ERRORS=$(echo "$DELIVER_ERRORS" | grep -c "socket hang up" || true)
    if [[ "$SOCKET_ERRORS" -eq "$DELIVER_COUNT" ]]; then
      S5_DETAIL="$DELIVER_COUNT 条网络错误 (socket hang up) — 断网导致"
      echo -e "  ${YELLOW}[送达] WARN${NC} — $S5_DETAIL"
      ((A_WARN++))
    else
      S5_PASS=false
      S5_DETAIL="$DELIVER_COUNT 条投递错误"
      echo -e "  ${RED}[送达] FAIL${NC} — $S5_DETAIL"
      ((A_FAIL++))
    fi
  fi

  # ── Agent summary ──
  TOTAL_PASS=$((TOTAL_PASS + A_PASS))
  TOTAL_FAIL=$((TOTAL_FAIL + A_FAIL))
  TOTAL_WARN=$((TOTAL_WARN + A_WARN))

  # Determine overall agent status
  AGENT_STATUS_CLASS="pass"
  [[ "$A_WARN" -gt 0 ]] && AGENT_STATUS_CLASS="warn"
  [[ "$A_FAIL" -gt 0 ]] && AGENT_STATUS_CLASS="fail"

  # Determine token bar color
  TOKEN_BAR_CLASS="green"
  [[ "$TOKEN_PCT" -ge 75 ]] && TOKEN_BAR_CLASS="yellow"
  [[ "$TOKEN_PCT" -ge 90 ]] && TOKEN_BAR_CLASS="red"

  # Build HTML for this agent
  S1_CLASS="pass"; [[ "$S1_PASS" != true ]] && { [[ "$TOKEN_PCT" -ge 75 && "$TOKEN_PCT" -lt 90 ]] && S1_CLASS="warn" || S1_CLASS="fail"; }
  S2_CLASS="pass"; [[ "$S2_PASS" != true ]] && S2_CLASS="fail"
  S3_CLASS="pass"; [[ "$S3_PASS" != true ]] && S3_CLASS="fail"
  S4_CLASS="pass"; [[ "$S4_PASS" != true ]] && S4_CLASS="fail"
  S5_CLASS="pass"; [[ "$S5_PASS" != true ]] && S5_CLASS="fail"
  [[ -n "$DELIVER_ERRORS" && "$S5_PASS" == true ]] && S5_CLASS="warn"

  CLI_ERRORS_ESC=$(html_escape "${CLI_ERRORS:-}")
  CLI_ERROR_CTX_ESC=$(html_escape "${CLI_ERROR_CONTEXT:-}")
  DELIVER_ERRORS_ESC=$(html_escape "${DELIVER_ERRORS:-}")

  AGENT_HTML="$AGENT_HTML
<div class=\"agent-card ${AGENT_STATUS_CLASS}\" data-agent=\"${AGENT}\">
  <div class=\"agent-header\" onclick=\"toggleAgent(this)\">
    <span class=\"agent-name\">${AGENT}</span>
    <span class=\"agent-meta\">${SESSION_AGE} · ${SESSION_TOKENS}</span>
    <div class=\"token-bar\"><div class=\"token-fill ${TOKEN_BAR_CLASS}\" style=\"width:${TOKEN_PCT}%\"></div></div>
    <span class=\"agent-badge ${AGENT_STATUS_CLASS}\">${A_PASS}P ${A_FAIL}F ${A_WARN}W</span>
    <span class=\"arrow\">&#9654;</span>
  </div>
  <div class=\"agent-body\">
    <div class=\"check ${S1_CLASS}\"><span class=\"check-label\">Session 状态</span><span class=\"check-detail\">$(html_escape "$S1_DETAIL")</span></div>
    <div class=\"check ${S2_CLASS}\"><span class=\"check-label\">CLI 活跃</span><span class=\"check-detail\">全局 ${CLI_EXEC_COUNT} 条 exec 记录</span></div>
    <div class=\"check ${S3_CLASS}\"><span class=\"check-label\">CLI 错误</span><span class=\"check-detail\">$(html_escape "$S3_DETAIL")</span></div>"

  if [[ -n "$CLI_ERROR_CONTEXT" ]]; then
    AGENT_HTML="$AGENT_HTML
    <div class=\"error-detail\">
      <div class=\"error-title\">CLI 错误上下文 (±5行)</div>
      <div class=\"log-block\">${CLI_ERROR_CTX_ESC}</div>
    </div>"
  fi

  AGENT_HTML="$AGENT_HTML
    <div class=\"check ${S4_CLASS}\"><span class=\"check-label\">静默过滤</span><span class=\"check-detail\">$(html_escape "$S4_DETAIL")</span></div>
    <div class=\"check ${S5_CLASS}\"><span class=\"check-label\">Discord 送达</span><span class=\"check-detail\">$(html_escape "$S5_DETAIL")</span></div>"

  if [[ -n "$DELIVER_ERRORS" ]]; then
    AGENT_HTML="$AGENT_HTML
    <div class=\"error-detail\">
      <div class=\"error-title\">送达错误详情</div>
      <div class=\"log-block\">${DELIVER_ERRORS_ESC}</div>
    </div>"
  fi

  AGENT_HTML="$AGENT_HTML
  </div>
</div>"

done

# ── Summary ──
echo -e "\n────────────────────────────────────"
echo -e "总计: ${GREEN}$TOTAL_PASS PASS${NC}  ${RED}$TOTAL_FAIL FAIL${NC}  ${YELLOW}$TOTAL_WARN WARN${NC}"

# ── Generate HTML ──
SERIALIZE_ESC=$(html_escape "$SERIALIZE_VAL")
AGENT_NAMES_JSON=$(printf '%s\n' "${AGENTS[@]}" | python3 -c "import sys,json; print(json.dumps([l.strip() for l in sys.stdin]))")

cat > "$REPORT_FILE" << 'HTMLEOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OpenClaw 诊断报告</title>
<style>
  :root { --bg:#0d1117; --card:#161b22; --border:#30363d; --text:#e6edf3; --muted:#8b949e; --green:#3fb950; --red:#f85149; --yellow:#d29922; --blue:#58a6ff; --cyan:#56d4dd; --purple:#bc8cff; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif; background:var(--bg); color:var(--text); line-height:1.6; padding:1.5rem; max-width:1100px; margin:0 auto; }
  h1 { font-size:1.5rem; margin-bottom:0.2rem; }
  .meta { color:var(--muted); font-size:0.85rem; margin-bottom:1rem; }

  .global-bar { display:flex; gap:0.8rem; margin-bottom:1.5rem; flex-wrap:wrap; }
  .g-chip { background:var(--card); border:1px solid var(--border); border-radius:6px; padding:0.4rem 0.8rem; font-size:0.8rem; display:flex; align-items:center; gap:0.4rem; }
  .g-chip.pass { border-color:var(--green); }
  .g-chip.fail { border-color:var(--red); }
  .g-chip .dot { width:8px; height:8px; border-radius:50%; }
  .g-chip.pass .dot { background:var(--green); }
  .g-chip.fail .dot { background:var(--red); }

  .summary { display:flex; gap:1rem; margin-bottom:1.5rem; }
  .summary-card { flex:1; background:var(--card); border:1px solid var(--border); border-radius:8px; padding:0.8rem; text-align:center; }
  .summary-card.pass { border-color:var(--green); }
  .summary-card.fail { border-color:var(--red); }
  .summary-card.warn { border-color:var(--yellow); }
  .summary-num { font-size:1.8rem; font-weight:800; }
  .summary-card.pass .summary-num { color:var(--green); }
  .summary-card.fail .summary-num { color:var(--red); }
  .summary-card.warn .summary-num { color:var(--yellow); }
  .summary-label { font-size:0.75rem; color:var(--muted); }

  /* Agent selector tabs */
  .agent-tabs { display:flex; gap:0.5rem; margin-bottom:1rem; flex-wrap:wrap; }
  .agent-tab { background:var(--card); border:1px solid var(--border); border-radius:6px; padding:0.4rem 1rem; font-size:0.85rem; cursor:pointer; color:var(--muted); transition:all 0.2s; }
  .agent-tab:hover { border-color:var(--blue); color:var(--text); }
  .agent-tab.active { border-color:var(--blue); color:var(--blue); background:rgba(88,166,255,0.08); }
  .agent-tab.all { font-weight:600; }

  /* Agent card */
  .agent-card { background:var(--card); border:1px solid var(--border); border-radius:8px; margin-bottom:0.75rem; overflow:hidden; display:none; }
  .agent-card.visible { display:block; }
  .agent-card.pass { border-left:3px solid var(--green); }
  .agent-card.fail { border-left:3px solid var(--red); }
  .agent-card.warn { border-left:3px solid var(--yellow); }

  .agent-header { display:flex; align-items:center; gap:0.6rem; padding:0.75rem 1rem; cursor:pointer; }
  .agent-header:hover { background:rgba(255,255,255,0.02); }
  .agent-name { font-weight:700; font-size:1rem; color:var(--cyan); min-width:140px; }
  .agent-meta { color:var(--muted); font-size:0.8rem; min-width:160px; }
  .token-bar { flex:1; max-width:120px; height:6px; background:var(--border); border-radius:3px; overflow:hidden; }
  .token-fill { height:100%; border-radius:3px; transition:width 0.3s; }
  .token-fill.green { background:var(--green); }
  .token-fill.yellow { background:var(--yellow); }
  .token-fill.red { background:var(--red); }
  .agent-badge { font-size:0.7rem; font-weight:700; padding:0.15rem 0.5rem; border-radius:10px; }
  .agent-badge.pass { background:rgba(63,185,80,0.15); color:var(--green); }
  .agent-badge.fail { background:rgba(248,81,73,0.15); color:var(--red); }
  .agent-badge.warn { background:rgba(210,153,34,0.15); color:var(--yellow); }
  .arrow { color:var(--muted); transition:transform 0.2s; font-size:0.75rem; margin-left:auto; }
  .agent-card.open .arrow { transform:rotate(90deg); }

  .agent-body { display:none; padding:0 1rem 0.8rem; }
  .agent-card.open .agent-body { display:block; }

  .check { display:flex; align-items:center; gap:0.5rem; padding:0.35rem 0; border-bottom:1px solid rgba(48,54,61,0.5); font-size:0.85rem; }
  .check::before { content:''; width:8px; height:8px; border-radius:50%; flex-shrink:0; }
  .check.pass::before { background:var(--green); }
  .check.fail::before { background:var(--red); }
  .check.warn::before { background:var(--yellow); }
  .check-label { font-weight:600; min-width:100px; color:var(--text); }
  .check-detail { color:var(--muted); }

  .error-detail { margin:0.5rem 0; }
  .error-title { font-size:0.75rem; font-weight:600; color:var(--yellow); margin-bottom:0.3rem; }
  .log-block { background:var(--bg); border:1px solid var(--border); border-radius:6px; padding:0.6rem 0.8rem; font-family:'SF Mono',Monaco,Consolas,monospace; font-size:0.72rem; overflow-x:auto; white-space:pre-wrap; word-break:break-all; color:var(--muted); max-height:250px; overflow-y:auto; }

  footer { margin-top:2rem; padding-top:1rem; border-top:1px solid var(--border); color:var(--muted); font-size:0.75rem; text-align:center; }
  footer a { color:var(--blue); }
</style>
</head>
<body>
HTMLEOF

cat >> "$REPORT_FILE" << EOF
<h1>OpenClaw 诊断报告</h1>
<p class="meta">${DIAG_TIME} · $(hostname) · agents: ${AGENTS[*]}</p>

<div class="global-bar">
  <div class="g-chip $(if [[ "$GLOBAL_CONN_PASS" == true ]]; then echo pass; else echo fail; fi)"><span class="dot"></span>Discord $(if [[ "$DISCORD_OK" == true ]]; then echo OK; else echo FAIL; fi)</div>
  <div class="g-chip $(if [[ "$GLOBAL_CONN_PASS" == true ]]; then echo pass; else echo fail; fi)"><span class="dot"></span>Gateway $(if [[ "$GATEWAY_OK" == true ]]; then echo reachable; else echo FAIL; fi)</div>
  <div class="g-chip $(if [[ "$SERIALIZE_PASS" == true ]]; then echo pass; else echo fail; fi)"><span class="dot"></span>${SERIALIZE_ESC}</div>
</div>

<div class="summary">
  <div class="summary-card pass"><div class="summary-num">$TOTAL_PASS</div><div class="summary-label">PASS</div></div>
  <div class="summary-card fail"><div class="summary-num">$TOTAL_FAIL</div><div class="summary-label">FAIL</div></div>
  <div class="summary-card warn"><div class="summary-num">$TOTAL_WARN</div><div class="summary-label">WARN</div></div>
</div>

<div class="agent-tabs">
  <div class="agent-tab all active" onclick="filterAgent('all')">全部</div>
EOF

for AGENT in "${AGENTS[@]}"; do
  echo "  <div class=\"agent-tab\" onclick=\"filterAgent('${AGENT}')\">${AGENT}</div>" >> "$REPORT_FILE"
done

cat >> "$REPORT_FILE" << EOF
</div>

${AGENT_HTML}

<footer>
  <p>由 <code>diagnose.sh</code> 自动生成 · <a href="index.html">决策树参考</a></p>
</footer>

<script>
function filterAgent(name) {
  document.querySelectorAll('.agent-tab').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');
  document.querySelectorAll('.agent-card').forEach(c => {
    if (name === 'all' || c.dataset.agent === name) {
      c.classList.add('visible');
    } else {
      c.classList.remove('visible');
    }
  });
}
function toggleAgent(el) {
  el.closest('.agent-card').classList.toggle('open');
}
// Show all on load
document.querySelectorAll('.agent-card').forEach(c => c.classList.add('visible'));
// Auto-expand failed agents
document.querySelectorAll('.agent-card.fail').forEach(c => c.classList.add('open'));
</script>
</body>
</html>
EOF

echo -e "\n${GREEN}报告已生成:${NC} $REPORT_FILE"

if [[ "$AUTO_OPEN" == true ]]; then
  open "$REPORT_FILE" 2>/dev/null || xdg-open "$REPORT_FILE" 2>/dev/null || echo "请手动打开: $REPORT_FILE"
fi
