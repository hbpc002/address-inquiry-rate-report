# 生产 → 测试 全量数据一键迁移（在测试服务器运行）

`sync_db.sh` 用于把**生产服务器**的全部数据（PostgreSQL 数据库 + 上传文件）一键拉取到**测试服务器**并覆盖导入。适用于「docker-compose.yml 三容器部署」环境。

> 注意：本脚本在**测试服务器**上运行，方向是"拉取"，即**生产数据覆盖本机测试库**。

## 前置条件

- 生产、测试均为三容器部署（`schedule-web` / `schedule-api` / `schedule-db`），compose 目录均在 `/home/hbpc/address-inquiry-rate-report/`
- 测试服务器已配置到**生产服务器的免密 SSH**（强烈建议，否则脚本每步都会让你输密码）。未配置时先执行：
  ```bash
  ssh-keygen -t rsa             # 已有密钥可跳过
  ssh-copy-id hbpc@<生产服务器IP>
  ```
  验证免密：`ssh hbpc@<生产服务器IP> 'echo ok'` 不提示输密码即成功。
- 测试与生产服务器均能执行 docker，二选一：
  ```bash
  sudo usermod -aG docker $USER   # 加入 docker 组，重新登录生效
  # 或配置免密 sudo：sudo visudo 添加  hbpc ALL=(ALL) NOPASSWD: ALL
  ```
  脚本会自动检测 `docker` 直接可用 → `sudo -n docker` 免密 sudo → 否则报错提示。

## 使用步骤

在**测试服务器**的 `hbpc` 账号下执行：

```bash
cd /home/hbpc/address-inquiry-rate-report/scripts   # 脚本所在目录
chmod +x ./sync_db.sh                                # 首次需要执行权限
./sync_db.sh <生产服务器IP>            # SSH 端口默认 22
./sync_db.sh <生产服务器IP> 22222       # 自定义 SSH 端口
```

> 确认生产 IP：脚本方向是"从该 IP 拉取并覆盖本机测试库"。跑之前务必先确认这个 IP 确实是**生产服务器**（例如 `ssh hbpc@<IP> hostname` 核对），拉错源会把测试库覆盖成那台机器的数据（不会影响对方机器，但会白白覆盖本机）。

示例（生产为 133.0.83.78）：

```bash
./sync_db.sh 133.0.83.78
```

交互流程：

1. 输入 `y` 确认（会清楚提示"覆盖本机测试库、源为生产 IP"）
2. 第 0 步会打印「生产机家目录」，确认是 `/home/hbpc` 后继续
3. 脚本自动完成 5 个步骤：
   - 生产服务器导出 PostgreSQL 库（经 SSH，输出 `[prod] 导出完成: /home/hbpc/schedule_prod.dump`）
   - 拉取 dump 到本机
   - 同步生产 `~/address-inquiry-rate-report/uploads/` → 本机（`--delete`）
   - 备份本机测试库后在导入前停止 web/api → 覆盖导入 → 重启
   - 打印生产/本机关键表行数，人工核对一致即成功

## 环境变量覆盖

默认值匹配 docker-compose.yml，如容器名/账号/目录不同可覆盖：

```bash
DB_CONTAINER=schedule-db PG_USER=postgres PG_DB=schedule \
WEB_CONTAINER=schedule-web API_CONTAINER=schedule-api \
SSH_USER=hbpc COMPOSE_DIR=$HOME/address-inquiry-rate-report \
./sync_db.sh <生产服务器IP>
```

| 变量 | 默认值 | 说明 |
|------|--------|------|
| DB_CONTAINER | schedule-db | 数据库容器名（测试、生产一致） |
| PG_USER | postgres | 数据库用户 |
| PG_DB | schedule | 数据库名 |
| WEB_CONTAINER | schedule-web | 前端容器名 |
| API_CONTAINER | schedule-api | 后端容器名 |
| SSH_USER | hbpc | 生产服务器登录账号 |
| COMPOSE_DIR | ~/address-inquiry-rate-report | compose 所在目录 |
| UPLOADS_DIR | $COMPOSE_DIR/uploads | 上传文件目录 |

## 迁移产物

| 文件 | 位置 | 说明 |
|------|------|------|
| `schedule_prod.dump` | 本机(测试) `~/` | 生产库 dump 暂存，可删除 |
| `schedule_prod.dump` | 生产 `~/` | 生产导出文件（脚本在生产机上保留），可手动删除：`ssh hbpc@<生产IP> rm -f ~/schedule_prod.dump` |
| `schedule_test_backup.<时间戳>.dump` | 本机(测试) `~/` | 导入前测试库自动备份，用于回滚 |

## 回滚方法

在测试服务器执行，恢复为本次导入前的旧数据：

```bash
docker cp ~/schedule_test_backup.<时间戳>.dump schedule-db:/tmp/backup.dump
docker exec schedule-db dropdb -U postgres --if-exists schedule
docker exec schedule-db createdb -U postgres schedule
docker exec schedule-db pg_restore -U postgres -d schedule /tmp/backup.dump
docker restart schedule-api schedule-web
```

## 常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| `./sync_db.sh: Permission denied` | 文件无执行权限 | `chmod +x ./sync_db.sh`，或改用 `bash ./sync_db.sh ...` |
| `permission denied ... docker.sock` | 当前用户不在 docker 组 | `sudo usermod -aG docker $USER` 后重新登录 |
| `File "$HOME/..." not found`（旧版本脚本） | scp 远程路径未展开 | 已修复为绝对路径，更新脚本到最新版即可 |
| 每步都提示输入密码 | 未配置 SSH 免密 | `ssh-copy-id hbpc@<生产IP>` |
| 迁移后两端行数不一致 | 导入未走完或源 IP 错误 | 用 `~/schedule_test_backup.<时间戳>.dump` 回滚后重跑，并先核对生产 IP |

## 注意事项

- 脚本方向为"拉取"，只影响**本机（测试）**，不会改动生产数据
- **不要直接复制 PostgreSQL 的 `postgres_data` 卷目录**，PG 运行中复制会损坏数据，必须用 dump/restore
- 登录账号/密码会随生产数据一起迁入测试库，测试环境建议迁移后重置 admin 密码，避免两侧串号
- 同步 `uploads/` 使用 `--delete`，本机多出的旧文件会被删除
- 导入过程请勿中断；若中断导致导入失败，用上文的备份回滚即可
- 脚本仅迁移数据，不迁移代码/镜像版本；测试与生产的应用版本需自行保持一致