#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<EOF
生产 -> 测试 全量数据一键迁移脚本
用法:
    ./sync_db.sh <生产服务器IP> [SSH端口]

说明:
    在【测试服务器】的 hbpc 账号下运行，自动完成:
      1. 生产服务器导出 PostgreSQL 数据库
      2. 从生产拉取 dump 到本机
      3. 同步上传文件目录 (uploads)
      4. 备份本机测试当前数据库后覆盖导入
      (生产侧操作通过 SSH 执行，需配置免密登录)

docker 权限:
    本机与生产机均需能执行 docker。脚本自动检测: 直接可用 -> sudo -n docker 免密 sudo。
    若都不行，请先在本机执行:  sudo usermod -aG docker \$USER  (然后重新登录)
    生产机同理；或用 sudo visudo 配置免密。

可覆盖的环境变量:
    DB_CONTAINER=schedule-db   PG_USER=postgres   PG_DB=schedule
    WEB_CONTAINER=schedule-web API_CONTAINER=schedule-api
    SSH_USER=hbpc  COMPOSE_DIR=~/address-inquiry-rate-report
EOF
}

PROD_IP="${1:-}"
SSH_PORT="${2:-22}"
if [[ -z "$PROD_IP" ]]; then
    usage
    exit 1
fi

DB_CONTAINER="${DB_CONTAINER:-schedule-db}"
PG_USER="${PG_USER:-postgres}"
PG_DB="${PG_DB:-schedule}"
WEB_CONTAINER="${WEB_CONTAINER:-schedule-web}"
API_CONTAINER="${API_CONTAINER:-schedule-api}"
SSH_USER="${SSH_USER:-hbpc}"
COMPOSE_DIR="${COMPOSE_DIR:-$HOME/address-inquiry-rate-report}"
UPLOADS_DIR="${UPLOADS_DIR:-$COMPOSE_DIR/uploads}"

DUMP_FILE="$HOME/schedule_prod.dump"
TS="$(date +%Y%m%d_%H%M%S)"

log() { echo "[$(date '+%F %T')] $*"; }

pick_docker() {
    if docker ps >/dev/null 2>&1; then
        DOCKER="docker"
    elif sudo -n docker ps >/dev/null 2>&1; then
        DOCKER="sudo -n docker"
    else
        echo "无法执行 docker 命令。请二选一重试后重新运行本脚本:"
        echo "  1) 加入 docker 组并重新登录:  sudo usermod -aG docker \$USER"
        echo "  2) 配置免密 sudo:             sudo visudo 添加  hbpc ALL=(ALL) NOPASSWD: ALL"
        exit 1
    fi
}
dk() { $DOCKER "$@"; }

log "本机 = 测试环境（将被覆盖的目标）"
log "生产服务器 = ${SSH_USER}@${PROD_IP}:${SSH_PORT} (数据源)"
log "测试数据库 = ${PG_USER}@${DB_CONTAINER}/${PG_DB}"

read -r -p "确认覆盖【本机测试库】全部数据（导入前自动备份），从生产 ${PROD_IP} 拉取，继续? [y/N] " confirm
[[ "$confirm" == "y" || "$confirm" == "Y" ]] || { echo "已取消"; exit 0; }

log "0/5 检查 docker 与 SSH 连通性..."
pick_docker
dk ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER" || { echo "本机(测试)容器 $DB_CONTAINER 不存在，请检查"; exit 1; }
PROD_HOME="$(ssh -p "$SSH_PORT" "${SSH_USER}@${PROD_IP}" 'echo $HOME' 2>/dev/null)" || { echo "无法 SSH 到生产 ${PROD_IP}，请检查 SSH 配置"; exit 1; }
PROD_DUMP_PATH="${PROD_HOME}/schedule_prod.dump"
PROD_UPLOADS_PATH="${PROD_HOME}${UPLOADS_DIR#$HOME}"
log "生产机家目录: $PROD_HOME"

log "1/5 生产服务器导出数据库 ..."
ssh -p "$SSH_PORT" "${SSH_USER}@${PROD_IP}" "bash -s $DB_CONTAINER $PG_USER $PG_DB" <<'PROD_EOF'
set -euo pipefail
DBC="$1"; PGU="$2"; PGD="$3"
if docker ps >/dev/null 2>&1; then D="docker"
elif sudo -n docker ps >/dev/null 2>&1; then D="sudo -n docker"
else echo "生产服务器无法执行 docker，请在生产机配置权限"; exit 1; fi
$D exec "$DBC" pg_dump -U "$PGU" -d "$PGD" -F c -f /tmp/schedule_prod.dump
$D cp "$DBC":/tmp/schedule_prod.dump "$HOME/schedule_prod.dump"
$D exec "$DBC" rm -f /tmp/schedule_prod.dump
echo "[prod] 导出完成: $HOME/schedule_prod.dump"
PROD_EOF

log "2/5 拉取 dump 到本机 ..."
scp -P "$SSH_PORT" "${SSH_USER}@${PROD_IP}:$PROD_DUMP_PATH" "$DUMP_FILE"
log "已拉取: $DUMP_FILE ($(du -h "$DUMP_FILE" | cut -f1))"

log "3/5 同步上传文件目录（生产 -> 本机）..."
mkdir -p "$UPLOADS_DIR"
if ssh -p "$SSH_PORT" "${SSH_USER}@${PROD_IP}" "test -d ${PROD_UPLOADS_PATH}"; then
    rsync -av --delete -e "ssh -p $SSH_PORT" "${SSH_USER}@${PROD_IP}:$PROD_UPLOADS_PATH/" "$UPLOADS_DIR/"
else
    log "警告: 生产机 ${PROD_UPLOADS_PATH} 不存在，跳过上传目录同步"
fi

log "4/5 备份本机测试库并覆盖导入 ..."
dk exec "$DB_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" -F c -f /tmp/schedule_test_backup.dump
dk cp "$DB_CONTAINER":/tmp/schedule_test_backup.dump "$HOME/schedule_test_backup.$TS.dump"
log "测试库已备份到 ~/schedule_test_backup.$TS.dump"

log "停止 $WEB_CONTAINER / $API_CONTAINER ..."
dk stop "$WEB_CONTAINER" "$API_CONTAINER" || true

dk cp "$DUMP_FILE" "$DB_CONTAINER":/tmp/schedule_prod.dump
dk exec "$DB_CONTAINER" dropdb -U "$PG_USER" --if-exists "$PG_DB"
dk exec "$DB_CONTAINER" createdb -U "$PG_USER" "$PG_DB"
dk exec "$DB_CONTAINER" pg_restore -U "$PG_USER" -d "$PG_DB" /tmp/schedule_prod.dump
dk exec "$DB_CONTAINER" rm -f /tmp/schedule_prod.dump /tmp/schedule_test_backup.dump

dk start "$API_CONTAINER" "$WEB_CONTAINER"
log "服务已重启"

log "5/5 行数对比 ..."
echo "--- 生产库 ---"
ssh -p "$SSH_PORT" "${SSH_USER}@${PROD_IP}" "bash -s $DB_CONTAINER $PG_USER $PG_DB" <<'PROD_COUNT_EOF'
set -euo pipefail
DBC="$1"; PGU="$2"; PGD="$3"
if docker ps >/dev/null 2>&1; then D="docker"
elif sudo -n docker ps >/dev/null 2>&1; then D="sudo -n docker"
else echo "(生产机无法执行 docker)"; exit 0; fi
$D exec "$DBC" psql -U "$PGU" -d "$PGD" -t -A -c \
  "select 'employees='||count(*) from employees union all select 'shift_types='||count(*) from shift_types union all select 'schedules='||count(*) from schedules union all select 'checkins='||count(*) from checkins;"
PROD_COUNT_EOF
echo "--- 本机测试库 ---"
dk exec "$DB_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -t -A -c \
  "select 'employees='||count(*) from employees union all select 'shift_types='||count(*) from shift_types union all select 'schedules='||count(*) from schedules union all select 'checkins='||count(*) from checkins;"

cat <<EOF

=== 迁移完成 ===
请核对上面"生产库"与"本机测试库"行数是否一致。
本机测试库登录账号/密码已随生产数据迁入，建议重置测试环境 admin 密码。
回滚: 本机恢复 ~/schedule_test_backup.$TS.dump
EOF