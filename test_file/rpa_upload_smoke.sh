#!/usr/bin/env bash
#
# RPA 自动上传冒烟验证脚本
# 用法:
#   export API_BASE=http://<服务器>:8000
#   export RPA_USER=rpa_bot RPA_PASS='******'
#   ./rpa_upload_smoke.sh <排班出勤情况.xlsx> [签入签出.csv] [工作量详单.xlsx]
#
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"
RPA_USER="${RPA_USER:?请设置环境变量 RPA_USER}"
RPA_PASS="${RPA_PASS:?请设置环境变量 RPA_PASS}"

SCHEDULE_FILE="${1:-}"
CHECKIN_FILE="${2:-}"
WORKLOAD_FILE="${3:-}"

CURL_SSL="${CURL_SSL:--k}"  # 自签名https证书跳过校验; 正式CA证书可 CURL_SSL="" 运行

if [[ -z "$SCHEDULE_FILE" && -z "$CHECKIN_FILE" && -z "$WORKLOAD_FILE" ]]; then
    echo "用法: $0 <排班出勤情况.xlsx> [签入签出.csv] [工作量详单.xlsx]" >&2
    exit 2
fi

TOTAL=1
for f in "$SCHEDULE_FILE" "$CHECKIN_FILE" "$WORKLOAD_FILE"; do
    [[ -z "$f" ]] && continue
    TOTAL=$((TOTAL + 1))
    if [[ ! -f "$f" ]]; then
        echo "FAIL: 文件不存在: $f" >&2
        exit 2
    fi
done

extract_json_field() {
    local json="$1" field="$2"
    if command -v jq >/dev/null 2>&1; then
        printf '%s' "$json" | jq -r --arg f "$field" '$f | split(".") | reduce .[] as $k (.; .[$k]) // empty'
    elif command -v python3 >/dev/null 2>&1; then
        printf '%s' "$json" | python3 -c '
import sys, json
data = json.load(sys.stdin)
for key in sys.argv[1].split("."):
    if isinstance(data, dict):
        data = data.get(key)
    else:
        data = None
        break
print(data if data is not None else "")' "$field"
    else
        echo "需要 jq 或 python3 之一来解析响应" >&2
        exit 2
    fi
}

fail() {
    echo "FAIL: $1" >&2
    echo "响应内容: $2" >&2
    exit 1
}

echo "==> [1/$TOTAL] 登录 $API_BASE/api/auth/login (用户: $RPA_USER)"
LOGIN_RESP=$(curl -sS $CURL_SSL -X POST "$API_BASE/api/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "username=$RPA_USER" \
    --data-urlencode "password=$RPA_PASS") || fail "登录请求发送失败(检查 API_BASE 与网络)" ""
TOKEN=$(extract_json_field "$LOGIN_RESP" "access_token")
[[ -n "$TOKEN" ]] || fail "登录失败,未获取到 access_token" "$LOGIN_RESP"
echo "PASS: 登录成功"

STEP=2
if [[ -n "$SCHEDULE_FILE" ]]; then
    echo "==> [$STEP/$TOTAL] 上传排班出勤情况: $SCHEDULE_FILE"
    SCHED_RESP=$(curl -sS $CURL_SSL -X POST "$API_BASE/api/schedules/import-attendance-report" \
        -H "Authorization: Bearer $TOKEN" \
        -F "file=@${SCHEDULE_FILE};type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet") \
        || fail "排班上传请求失败" ""
    echo "$SCHED_RESP" | grep -q '"message"' || fail "排班导入被拒绝" "$SCHED_RESP"
    echo "PASS: $(printf '%s' "$SCHED_RESP" | tr -d '\n' | cut -c1-200)"
    STEP=$((STEP + 1))
fi

if [[ -n "$CHECKIN_FILE" ]]; then
    echo "==> [$STEP/$TOTAL] 上传签入签出记录: $CHECKIN_FILE"
    CHECKIN_RESP=$(curl -sS $CURL_SSL -X POST "$API_BASE/api/checkins/import" \
        -H "Authorization: Bearer $TOKEN" \
        -F "file=@${CHECKIN_FILE};type=text/csv") \
        || fail "签到上传请求失败" ""
    COUNT=$(extract_json_field "$CHECKIN_RESP" "count")
    [[ -n "$COUNT" ]] || fail "签到导入被拒绝" "$CHECKIN_RESP"
    echo "PASS: 导入 $COUNT 条签到记录"
    STEP=$((STEP + 1))
fi

if [[ -n "$WORKLOAD_FILE" ]]; then
    echo "==> [$STEP/$TOTAL] 上传工作量详单: $WORKLOAD_FILE"
    WORKLOAD_RESP=$(curl -sS $CURL_SSL -X POST "$API_BASE/api/workloads/import" \
        -H "Authorization: Bearer $TOKEN" \
        -F "file=@${WORKLOAD_FILE};type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet") \
        || fail "工作量上传请求失败" ""
    COUNT=$(extract_json_field "$WORKLOAD_RESP" "count")
    [[ -n "$COUNT" ]] || fail "工作量导入被拒绝" "$WORKLOAD_RESP"
    echo "PASS: 导入 $COUNT 条工作量记录"
fi

echo ""
echo "全部通过。请到系统页面核对:"
echo "  1. 排班管理 -> 对应日期的排班数据"
echo "  2. 签到记录 -> 当日签到明细"
echo "  3. 考勤日报 -> 状态/工时是否已重算"
[[ -n "$WORKLOAD_FILE" ]] && echo "  4. 工作量详单 -> 对应日期的指标数据"
echo "  5. 系统管理 -> 操作日志 -> $RPA_USER 的 import 记录"
