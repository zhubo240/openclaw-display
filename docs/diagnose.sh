#!/usr/bin/env bash
# OpenClaw Agent 诊断脚本 (v2)
# 按 agent 维度检查，输出 HTML 报告
# 用法: ./diagnose.sh <agent1> [agent2 ...] [--open] [--all] [--conv N]
#   agent:   指定检查的 agent 名称（必须至少一个，或用 --all）
#   --open:  生成后自动打开浏览器
#   --all:   检查所有活跃 agent
#   --conv N: 使用第 N 次对话 (1=最近, 最多5), 默认 1
#
# 示例:
#   ./diagnose.sh butler us-mean-reversion
#   ./diagnose.sh --all --open
#   ./diagnose.sh realestate --conv 3

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
CONV_NUM=1
AGENTS=()
NEXT_IS_CONV=false
for arg in "$@"; do
  if [[ "$NEXT_IS_CONV" == true ]]; then
    CONV_NUM="$arg"
    NEXT_IS_CONV=false
    continue
  fi
  case "$arg" in
    --open) AUTO_OPEN=true ;;
    --all)  ALL_AGENTS=true ;;
    --conv) NEXT_IS_CONV=true ;;
    --conv=*) CONV_NUM="${arg#--conv=}" ;;
    -*)     echo "Unknown option: $arg"; exit 1 ;;
    *)      AGENTS+=("$arg") ;;
  esac
done
# Clamp conv number to 1-5
[[ "$CONV_NUM" -lt 1 ]] 2>/dev/null && CONV_NUM=1
[[ "$CONV_NUM" -gt 5 ]] 2>/dev/null && CONV_NUM=5

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

  # ── Extract recent conversations from JSONL sessions (top 5) ──
  LAST_MSG_TIME=""
  LAST_MSG_TEXT=""
  LAST_ASST_TEXT=""
  _JSONL_RAW=$(python3 << PYEOF
import json, os, glob, re

agent = "${AGENT}"
conv_num = max(1, min(5, int("${CONV_NUM}")))

# Step 1: Resolve agent workspace -> Claude projects dir
base_ws = os.path.expanduser("~/.openclaw/workspace")
agent_ws = base_ws + "-" + agent
if not os.path.isdir(agent_ws):
    agent_ws = base_ws

proj_name = agent_ws.replace("/", "-").replace(".", "-")
proj_dir = os.path.expanduser("~/.claude/projects/" + proj_name)

# Step 2: Find top 5 most recently modified JSONLs
jsonls = []
if os.path.isdir(proj_dir):
    candidates = glob.glob(os.path.join(proj_dir, "*.jsonl"))
    candidates = [c for c in candidates if "/subagents/" not in c]
    candidates.sort(key=os.path.getmtime, reverse=True)
    jsonls = candidates[:5]

if not jsonls:
    print("EMPTY|")
    exit()

actual_sel = min(conv_num, len(jsonls))
sel_ts = sel_txt = sel_asst = ""

def extract_user_text(content):
    """Extract user message text from content field."""
    if isinstance(content, str):
        t = content.strip()
        match = re.search(r'\]\s*\w[^:\n]*:\s*(.+?)(?:\n|$)', t)
        if match:
            return match.group(1).strip()[:60]
        while t.startswith("[") and "]" in t:
            t = t[t.index("]")+1:].strip()
        return t[:60]
    elif isinstance(content, list):
        for c in content:
            if c.get("type") == "text":
                t = c["text"].strip()
                while t.startswith("[") and "]" in t:
                    t = t[t.index("]")+1:].strip()
                return t[:60]
    return ""

def extract_asst_text(content):
    """Extract assistant message text from content field."""
    if isinstance(content, list):
        for c in content:
            if c.get("type") == "text":
                t = c.get("text", "").strip()
                if t:
                    return t[:60]
    elif isinstance(content, str) and content.strip():
        return content.strip()[:60]
    return ""

for idx, jf in enumerate(jsonls, 1):
    ts = txt = asst = ""
    with open(jf) as f:
        for line in f:
            try:
                e = json.loads(line.strip())
                if e.get("type") == "user":
                    m = e.get("message", {})
                    if m.get("role") == "user":
                        ts = e.get("timestamp", "")
                        txt = extract_user_text(m.get("content", ""))
                elif e.get("type") == "assistant":
                    asst = extract_asst_text(e.get("message", {}).get("content", []))
            except: pass
    sel = "*" if idx == actual_sel else " "
    print(f"CONV|{sel}|{idx}|{ts}|{txt}|{asst}")
    if idx == actual_sel:
        sel_ts = ts
        sel_txt = txt
        sel_asst = asst

print(f"USER|{sel_ts}|{sel_txt}")
print(f"ASST|{sel_asst}")
PYEOF
)

  # Parse conversation list and selected data
  CONV_LIST=$(echo "$_JSONL_RAW" | grep "^CONV|" || true)
  LAST_MSG_TIME=$(echo "$_JSONL_RAW" | grep "^USER|" | head -1 | cut -d'|' -f2)
  LAST_MSG_TEXT=$(echo "$_JSONL_RAW" | grep "^USER|" | head -1 | cut -d'|' -f3-)
  LAST_ASST_TEXT=$(echo "$_JSONL_RAW" | grep "^ASST|" | head -1 | cut -d'|' -f2-)

  if [[ -n "$LAST_MSG_TIME" ]]; then
    LAST_MSG_DISPLAY="${LAST_MSG_TIME:0:10} ${LAST_MSG_TIME:11:8}"
  else
    LAST_MSG_DISPLAY="无数据"
  fi

  # Display conversation list
  if [[ -n "$CONV_LIST" ]]; then
    CONV_TOTAL=$(echo "$CONV_LIST" | wc -l | tr -d ' ')
    echo -e "  ${BLUE}对话记录 (${CONV_TOTAL} 条, 选中 #${CONV_NUM}):${NC}"
    while IFS='|' read -r _ sel idx ts txt asst; do
      TS_SHORT="${ts:0:10} ${ts:11:8}"
      if [[ "$sel" == "*" ]]; then
        echo -e "    ${GREEN}→ [$idx]${NC} $TS_SHORT — $txt"
      else
        echo -e "      ${CYAN}[$idx]${NC} $TS_SHORT — $txt"
      fi
    done <<< "$CONV_LIST"
  fi

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

  # ── 2. CLI exec activity — 提取最近一条的时间戳 ──
  CLI_EXEC_LAST=$(echo "$LOGS_RAW" | grep "cli exec:" | tail -1 || true)
  CLI_EXEC_COUNT=$(echo "$LOGS_RAW" | grep -c "cli exec" || true)
  S2_PASS=true; S2_DETAIL=""

  if [[ -n "$CLI_EXEC_LAST" ]]; then
    # Extract ISO timestamp from log line (e.g. 2025-01-15T15:16:09.123Z)
    CLI_EXEC_TIME=$(echo "$CLI_EXEC_LAST" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}' | tail -1 || true)
    if [[ -n "$CLI_EXEC_TIME" ]]; then
      CLI_TIME_SHORT="${CLI_EXEC_TIME:11:8}"
      # Calculate minutes ago (macOS date -j)
      CLI_EPOCH=$(date -j -f "%Y-%m-%dT%H:%M:%S" "$CLI_EXEC_TIME" +%s 2>/dev/null || echo "0")
      NOW_EPOCH=$(date +%s)
      if [[ "$CLI_EPOCH" -gt 0 ]]; then
        CLI_AGO_MIN=$(( (NOW_EPOCH - CLI_EPOCH) / 60 ))
        S2_DETAIL="最近调用: ${CLI_TIME_SHORT} (${CLI_AGO_MIN}分钟前, 全局 ${CLI_EXEC_COUNT} 条)"
      else
        S2_DETAIL="最近调用: ${CLI_TIME_SHORT} (全局 ${CLI_EXEC_COUNT} 条)"
      fi
    else
      S2_DETAIL="有 cli exec 记录 (全局 ${CLI_EXEC_COUNT} 条)"
    fi
    echo -e "  ${GREEN}[CLI exec] PASS${NC} — $S2_DETAIL"
    ((A_PASS++))
  else
    S2_PASS=false
    S2_DETAIL="无 cli exec 记录"
    echo -e "  ${RED}[CLI exec] FAIL${NC} — $S2_DETAIL"
    ((A_FAIL++))
  fi

  # ── 3. CLI 完成 & 错误 ──
  # Positive signal: embedded run done with aborted=false
  RUN_DONE=$(echo "$LOGS_RAW" | grep "embedded run done.*aborted=false" | tail -1 || true)
  RUN_ABORTED=$(echo "$LOGS_RAW" | grep "embedded run done.*aborted=true" | tail -1 || true)
  RUN_DURATION=""
  if [[ -n "$RUN_DONE" ]]; then
    RUN_DURATION=$(echo "$RUN_DONE" | grep -oE 'durationMs=[0-9]+' | head -1 | cut -d= -f2 || true)
  fi

  # Error detection (existing logic preserved)
  CLI_ERRORS=$(echo "$LOGS_RAW" | grep -iE "(Embedded agent failed|CLI failed|FailoverError|cli.*(error|timeout|EPIPE))" | tail -10 || true)
  S3_PASS=true; S3_DETAIL=""; S3_STATUS="pass"; CLI_ERROR_CONTEXT=""

  if [[ -n "$RUN_ABORTED" ]]; then
    # Aborted run = FAIL
    S3_PASS=false; S3_STATUS="fail"
    S3_DETAIL="运行被中断 (aborted=true)"
    echo -e "  ${RED}[CLI 完成] FAIL${NC} — $S3_DETAIL"
    ((A_FAIL++))
  elif [[ -n "$CLI_ERRORS" ]]; then
    CLI_ERROR_COUNT=$(echo "$CLI_ERRORS" | wc -l | tr -d ' ')
    S3_PASS=false; S3_STATUS="fail"
    S3_DETAIL="发现 $CLI_ERROR_COUNT 条 CLI 错误"
    echo -e "  ${RED}[CLI 完成] FAIL${NC} — $S3_DETAIL"
    ((A_FAIL++))

    # Extract more context: get ±5 lines around each error
    CLI_ERROR_CONTEXT=$(echo "$LOGS_RAW" | grep -B5 -A5 -iE "(Embedded agent failed|CLI failed|FailoverError)" | head -60 || true)

    # Build error analysis — pattern matching with explanations
    CLI_ERROR_ANALYSIS=""
    if echo "$CLI_ERROR_CONTEXT" | grep -q "code 1005"; then
      CLI_ERROR_ANALYSIS="${CLI_ERROR_ANALYSIS}WebSocket 断连 (1005): Discord 连接中断期间 CLI 请求失败，通常是短暂网络波动，会自动恢复\n"
      echo -e "    ${YELLOW}↳ 原因: Discord WebSocket 断连 (code 1005)${NC}"
    fi
    if echo "$CLI_ERROR_CONTEXT" | grep -q "EPIPE"; then
      CLI_ERROR_ANALYSIS="${CLI_ERROR_ANALYSIS}管道中断 (EPIPE): CLI 子进程提前退出，父进程写入失败，可能是 OOM 或 crash\n"
      echo -e "    ${YELLOW}↳ 原因: CLI 进程管道中断 (EPIPE)${NC}"
    fi
    if echo "$CLI_ERROR_CONTEXT" | grep -q "timeout"; then
      CLI_ERROR_ANALYSIS="${CLI_ERROR_ANALYSIS}响应超时: CLI 未在规定时间内完成，可能是 API 慢或 prompt 太大\n"
      echo -e "    ${YELLOW}↳ 原因: CLI 响应超时${NC}"
    fi
    if echo "$CLI_ERROR_CONTEXT" | grep -q "rate.limit\|429"; then
      CLI_ERROR_ANALYSIS="${CLI_ERROR_ANALYSIS}速率限制 (429): Anthropic API 限流，需要等待或升级 plan\n"
      echo -e "    ${YELLOW}↳ 原因: API 速率限制${NC}"
    fi
    if echo "$CLI_ERROR_CONTEXT" | grep -q "socket hang up"; then
      CLI_ERROR_ANALYSIS="${CLI_ERROR_ANALYSIS}网络中断 (socket hang up): 底层 TCP 连接被重置，通常是 ISP 或 DNS 问题\n"
      echo -e "    ${YELLOW}↳ 原因: 网络连接中断 (socket hang up)${NC}"
    fi

    # Check for verbose stderr/stdout near the error
    CLI_STDERR=$(echo "$LOGS_RAW" | grep -A2 "cli stderr" | head -10 || true)
    if [[ -n "$CLI_STDERR" ]]; then
      echo -e "    ${YELLOW}↳ CLI stderr:${NC}"
      echo "$CLI_STDERR" | head -5 | sed 's/^/      /'
    fi
  elif [[ -n "$RUN_DONE" ]]; then
    # Positive: completed successfully
    if [[ -n "$RUN_DURATION" ]]; then
      DUR_SEC=$(echo "scale=1; $RUN_DURATION / 1000" | bc 2>/dev/null || echo "${RUN_DURATION}ms")
      S3_DETAIL="最近完成: ${DUR_SEC}s, 未中断"
    else
      S3_DETAIL="最近完成, aborted=false"
    fi
    echo -e "  ${GREEN}[CLI 完成] PASS${NC} — $S3_DETAIL"
    ((A_PASS++))
  else
    # No completion record and no errors — WARN
    S3_STATUS="warn"
    S3_DETAIL="无完成记录（日志窗口可能太短）"
    echo -e "  ${YELLOW}[CLI 完成] WARN${NC} — $S3_DETAIL"
    ((A_WARN++))
  fi

  # ── 4. 静默过滤 — 查 agent JSONL 最后 assistant 消息 ──
  S4_PASS=true; S4_DETAIL=""; S4_STATUS="pass"

  if [[ -z "$LAST_ASST_TEXT" ]]; then
    # No assistant message found in JSONL
    S4_STATUS="warn"
    S4_DETAIL="无 assistant 消息记录"
    echo -e "  ${YELLOW}[静默检查] WARN${NC} — $S4_DETAIL"
    ((A_WARN++))
  elif [[ "$LAST_ASST_TEXT" == "HEARTBEAT_OK" || "$LAST_ASST_TEXT" == "NO_REPLY" ]]; then
    S4_PASS=false; S4_STATUS="fail"
    S4_DETAIL="最后响应: $LAST_ASST_TEXT"
    echo -e "  ${RED}[静默检查] FAIL${NC} — $S4_DETAIL"
    ((A_FAIL++))
  else
    ASST_DISPLAY="${LAST_ASST_TEXT:0:40}"
    S4_DETAIL="最后回复: '${ASST_DISPLAY}'"
    echo -e "  ${GREEN}[静默检查] PASS${NC} — $S4_DETAIL"
    ((A_PASS++))
  fi

  # ── 5. 送达 — 查 session 状态 + systemSent ──
  # Positive signal 1: session state transition to idle with run_completed
  DELIVERY_OK=$(echo "$LOGS_RAW" | grep 'session state:.*new=idle.*reason="run_completed"' | tail -1 || true)
  # Positive signal 2: systemSent in sessions.json
  SYSTEM_SENT=$(python3 -c "
import json, os
try:
    f = os.path.expanduser(os.path.join('~', '.openclaw', 'agents', 'main', 'sessions', 'sessions.json'))
    data = json.load(open(f))
    for sid, sess in data.items():
        if '${AGENT}' in str(sid) or sess.get('agent','') == '${AGENT}':
            print('true' if sess.get('systemSent') else 'false')
            break
    else:
        print('unknown')
except: print('error')
" 2>/dev/null || echo "error")

  # Error detection (existing)
  DELIVER_ERRORS=$(echo "$LOGS_RAW" | grep -iE "deliver.*(error|fail)|discord.*(error|rate)" | tail -5 || true)

  S5_PASS=true; S5_DETAIL=""; S5_STATUS="pass"
  HAS_POSITIVE=false
  POSITIVE_PARTS=""

  if [[ -n "$DELIVERY_OK" ]]; then
    HAS_POSITIVE=true
    POSITIVE_PARTS="run_completed"
  fi
  if [[ "$SYSTEM_SENT" == "true" ]]; then
    HAS_POSITIVE=true
    if [[ -n "$POSITIVE_PARTS" ]]; then
      POSITIVE_PARTS="${POSITIVE_PARTS} + systemSent=true"
    else
      POSITIVE_PARTS="systemSent=true"
    fi
  fi

  if [[ -n "$DELIVER_ERRORS" ]]; then
    DELIVER_COUNT=$(echo "$DELIVER_ERRORS" | wc -l | tr -d ' ')
    SOCKET_ERRORS=$(echo "$DELIVER_ERRORS" | grep -c "socket hang up" || true)

    if [[ "$HAS_POSITIVE" == true ]]; then
      # Errors exist but positive signal too — WARN
      S5_STATUS="warn"
      S5_DETAIL="${POSITIVE_PARTS} (但有 ${DELIVER_COUNT} 条历史错误)"
      echo -e "  ${YELLOW}[送达] WARN${NC} — $S5_DETAIL"
      ((A_WARN++))
    elif [[ "$SOCKET_ERRORS" -eq "$DELIVER_COUNT" ]]; then
      S5_STATUS="warn"
      S5_DETAIL="$DELIVER_COUNT 条网络错误 (socket hang up) — 断网导致"
      echo -e "  ${YELLOW}[送达] WARN${NC} — $S5_DETAIL"
      ((A_WARN++))
    else
      S5_PASS=false; S5_STATUS="fail"
      S5_DETAIL="$DELIVER_COUNT 条投递错误, 无正向信号"
      echo -e "  ${RED}[送达] FAIL${NC} — $S5_DETAIL"
      ((A_FAIL++))
    fi
  elif [[ "$HAS_POSITIVE" == true ]]; then
    S5_DETAIL="${POSITIVE_PARTS}"
    echo -e "  ${GREEN}[送达] PASS${NC} — $S5_DETAIL"
    ((A_PASS++))
  else
    # No positive signal and no errors
    S5_STATUS="warn"
    S5_DETAIL="无正向信号也无错误（数据不足）"
    echo -e "  ${YELLOW}[送达] WARN${NC} — $S5_DETAIL"
    ((A_WARN++))
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
  S3_CLASS="${S3_STATUS:-pass}"
  S4_CLASS="${S4_STATUS:-pass}"
  S5_CLASS="${S5_STATUS:-pass}"

  # Decision tree: Gateway and Serialize classes (global, but shown per agent)
  GW_CLASS="pass"; [[ "$GLOBAL_CONN_PASS" != true ]] && GW_CLASS="fail"
  S_SER_CLASS="pass"; [[ "$SERIALIZE_PASS" != true ]] && S_SER_CLASS="warn"

  CLI_ERRORS_ESC=$(html_escape "${CLI_ERRORS:-}")
  CLI_ERROR_CTX_ESC=$(html_escape "${CLI_ERROR_CONTEXT:-}")
  CLI_ERROR_ANALYSIS_ESC=$(html_escape "$(echo -e "${CLI_ERROR_ANALYSIS:-}")")
  DELIVER_ERRORS_ESC=$(html_escape "${DELIVER_ERRORS:-}")
  LAST_MSG_TEXT_ESC=$(html_escape "${LAST_MSG_TEXT:-}")

  # Build conversation list HTML
  CONV_LIST_HTML=""
  if [[ -n "$CONV_LIST" ]]; then
    CONV_LIST_HTML="<div class=\"conv-list\"><span class=\"conv-title\">对话记录:</span>"
    while IFS='|' read -r _ sel idx ts txt asst; do
      TS_SHORT="${ts:0:10} ${ts:11:8}"
      if [[ "$sel" == "*" ]]; then
        CONV_LIST_HTML="${CONV_LIST_HTML}<span class=\"conv-item sel\">[$idx] ${TS_SHORT} — $(html_escape "$txt")</span>"
      else
        CONV_LIST_HTML="${CONV_LIST_HTML}<span class=\"conv-item\">[$idx] ${TS_SHORT} — $(html_escape "$txt")</span>"
      fi
    done <<< "$CONV_LIST"
    CONV_LIST_HTML="${CONV_LIST_HTML}</div>"
  fi

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
    ${CONV_LIST_HTML}
    <div class=\"last-msg\">选中对话 #${CONV_NUM}: <em>${LAST_MSG_DISPLAY}</em> (UTC) — <em>${LAST_MSG_TEXT_ESC:-(空)}</em></div>
    <div class=\"dtree-flow\">
      <div class=\"dtree-step\"><div class=\"dtree-node ${GW_CLASS}\"><div class=\"dtree-dot\"></div><div class=\"dtree-label\">Gateway</div></div><div class=\"dtree-line\"></div></div>
      <div class=\"dtree-step\"><div class=\"dtree-node ${S2_CLASS}\"><div class=\"dtree-dot\"></div><div class=\"dtree-label\">CLI 调用</div></div><div class=\"dtree-line\"></div></div>
      <div class=\"dtree-step\"><div class=\"dtree-node ${S_SER_CLASS}\"><div class=\"dtree-dot\"></div><div class=\"dtree-label\">串行队列</div></div><div class=\"dtree-line\"></div></div>
      <div class=\"dtree-step\"><div class=\"dtree-node ${S3_CLASS}\"><div class=\"dtree-dot\"></div><div class=\"dtree-label\">CLI 完成</div></div><div class=\"dtree-line\"></div></div>
      <div class=\"dtree-step\"><div class=\"dtree-node ${S4_CLASS}\"><div class=\"dtree-dot\"></div><div class=\"dtree-label\">静默过滤</div></div><div class=\"dtree-line\"></div></div>
      <div class=\"dtree-step\"><div class=\"dtree-node ${S5_CLASS}\"><div class=\"dtree-dot\"></div><div class=\"dtree-label\">送达</div></div></div>
    </div>
    <div class=\"check ${S1_CLASS}\"><span class=\"check-label\">Session 状态</span><span class=\"check-detail\">$(html_escape "$S1_DETAIL")</span></div>
    <div class=\"check ${S2_CLASS}\"><span class=\"check-label\">CLI 活跃</span><span class=\"check-detail\">$(html_escape "$S2_DETAIL")</span></div>
    <div class=\"check ${S3_CLASS}\"><span class=\"check-label\">CLI 完成</span><span class=\"check-detail\">$(html_escape "$S3_DETAIL")</span></div>"

  if [[ -n "$CLI_ERROR_CONTEXT" ]]; then
    AGENT_HTML="$AGENT_HTML
    <div class=\"error-detail\">"
    # Show analysis if available
    if [[ -n "$CLI_ERROR_ANALYSIS" ]]; then
      AGENT_HTML="$AGENT_HTML
      <div class=\"error-analysis\">${CLI_ERROR_ANALYSIS_ESC}</div>"
    fi
    AGENT_HTML="$AGENT_HTML
      <details class=\"error-expand\">
        <summary>展开日志上下文 (±5行)</summary>
        <div class=\"log-block\">${CLI_ERROR_CTX_ESC}</div>
      </details>
    </div>"
  fi

  AGENT_HTML="$AGENT_HTML
    <div class=\"check ${S4_CLASS}\"><span class=\"check-label\">静默过滤</span><span class=\"check-detail\">$(html_escape "$S4_DETAIL")</span></div>
    <div class=\"check ${S5_CLASS}\"><span class=\"check-label\">Discord 送达</span><span class=\"check-detail\">$(html_escape "$S5_DETAIL")</span></div>"

  if [[ -n "$DELIVER_ERRORS" ]]; then
    AGENT_HTML="$AGENT_HTML
    <div class=\"error-detail\">
      <details class=\"error-expand\">
        <summary>展开送达错误详情</summary>
        <div class=\"log-block\">${DELIVER_ERRORS_ESC}</div>
      </details>
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
  .error-analysis { font-size:0.78rem; color:var(--yellow); background:rgba(210,153,34,0.08); border:1px solid rgba(210,153,34,0.2); border-radius:6px; padding:0.5rem 0.8rem; margin-bottom:0.4rem; white-space:pre-line; line-height:1.5; }
  .error-expand { margin-top:0.3rem; }
  .error-expand summary { font-size:0.75rem; font-weight:600; color:var(--muted); cursor:pointer; padding:0.2rem 0; }
  .error-expand summary:hover { color:var(--blue); }
  .error-expand[open] summary { color:var(--blue); }
  .log-block { background:var(--bg); border:1px solid var(--border); border-radius:6px; padding:0.6rem 0.8rem; font-family:'SF Mono',Monaco,Consolas,monospace; font-size:0.72rem; overflow-x:auto; white-space:pre-wrap; word-break:break-all; color:var(--muted); max-height:250px; overflow-y:auto; }

  .conv-list { font-size:0.75rem; color:var(--muted); padding:0.4rem 0; border-bottom:1px solid rgba(48,54,61,0.5); margin-bottom:0.2rem; display:flex; flex-direction:column; gap:0.15rem; }
  .conv-title { font-weight:600; color:var(--text); margin-bottom:0.2rem; }
  .conv-item { padding:0.1rem 0.4rem; border-radius:3px; }
  .conv-item.sel { background:rgba(88,166,255,0.1); color:var(--blue); font-weight:600; }

  .last-msg { font-size:0.8rem; color:var(--muted); padding:0.5rem 0 0.4rem; border-bottom:1px solid rgba(48,54,61,0.5); margin-bottom:0.2rem; }
  .last-msg em { color:var(--text); font-style:normal; }
  .dtree-flow { display:flex; align-items:flex-start; padding:0.6rem 0; margin-bottom:0.4rem; border-bottom:1px solid rgba(48,54,61,0.5); }
  .dtree-step { display:flex; align-items:flex-start; flex:1; min-width:0; }
  .dtree-step:last-child { flex:0 0 auto; }
  .dtree-node { display:flex; flex-direction:column; align-items:center; }
  .dtree-dot { width:14px; height:14px; border-radius:50%; flex-shrink:0; }
  .dtree-node.pass .dtree-dot { background:var(--green); box-shadow:0 0 4px rgba(63,185,80,0.4); }
  .dtree-node.fail .dtree-dot { background:var(--red); box-shadow:0 0 4px rgba(248,81,73,0.4); }
  .dtree-node.warn .dtree-dot { background:var(--yellow); box-shadow:0 0 4px rgba(210,153,34,0.4); }
  .dtree-label { font-size:0.65rem; color:var(--muted); margin-top:0.2rem; white-space:nowrap; }
  .dtree-line { flex:1; height:2px; background:var(--border); margin:6px 4px 0; min-width:8px; }

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
