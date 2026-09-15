# RPA 自动下载文件上传入库 - 对接说明

> 适用对象：弘玑 Cyclone RPA 流程配置人员
> 目标：RPA 下载「排班出勤情况」xlsx 和「签入签出查询」CSV 后，自动调用系统 HTTP 接口入库，替代人工页面上传。
> 后端无需任何改造，全部使用现有接口。

## 一、前置准备（一次性）

| 事项 | 说明 |
|------|------|
| 专用账号 | 管理员在「用户管理」创建 `rpa_bot`，角色分配 **manager**（默认含 `schedules.upload`、`checkins.upload` 权限）。禁止共用个人账号 |
| API 地址 | 如 `http://<服务器IP>:8000`，或经 nginx 的 `https://<域名>`。RPA 机器需能直连 |
| 密码保管 | RPA 中通过密码库/凭据组件存储，不要明文写在流程里 |

## 二、调用顺序（必须严格遵守）

```
下载文件 ──► ① 登录拿token ──► ② 上传排班xlsx ──► ③ 上传签到CSV ──► ④ 上传工作量详单xlsx ──► ⑤ 校验结果
```

**排班必须先于签到上传**：签到导入完成后系统会按当天排班自动重算考勤日报（迟到/早退/工时），先有排班才能保证口径正确。工作量详单与考勤计算无依赖，放最后即可。

## 三、接口规格

### ① 登录获取 Token

- `POST {API_BASE}/api/auth/login`
- Content-Type: `application/x-www-form-urlencoded`（注意：**不是 JSON**）

```
username=rpa_bot&password=******
```

成功响应 200：

```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": { "id": 5, "username": "rpa_bot", ... }
}
```

失败：401 `{"detail": "用户名或密码错误"}`；403 `{"detail": "用户已被禁用"}`

后续所有请求带 Header：`Authorization: Bearer <access_token>`

### ② 上传排班出勤情况（.xlsx）

- `POST {API_BASE}/api/schedules/import-attendance-report`
- Content-Type: `multipart/form-data`，字段名固定为 **`file`**

成功响应 200：

```json
{ "message": "导入成功", "employees": 3, "schedules": 86, "shift_types": 4 }
```

### ③ 上传签入签出记录（.csv）

- `POST {API_BASE}/api/checkins/import`
- Content-Type: `multipart/form-data`，字段名固定为 **`file`**
- 编码支持 UTF-8 / GBK 自动识别
- 注意：系统只导入目标部门（`广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表`）的行，返回的 `count` 小于文件行数属正常现象

成功响应 200：

```json
{ "count": 87, "batch": "a1b2c3d4" }
```

### ④ 上传工作量详单（.xlsx）

- `POST {API_BASE}/api/workloads/import`
- Content-Type: `multipart/form-data`，字段名固定为 **`file`**
- 即「客服代表工作量和操作情况统计表」（Sheet_0，第3行为表头），.XLSX/.xlsx 均可
- 注意：系统只导入归属部门含 `客户服务营销中心` 的行，返回的 `count` 小于文件行数属正常现象
- 权限：需要 `workload.upload`（工作量详单-导入）。若 rpa_bot 用的自定义角色，请在角色管理里勾选该权限

成功响应 200：

```json
{ "count": 62, "batch": "e5f6g7h8" }
```

## 四、幂等性与重跑

| 接口 | 覆盖策略 | 重复上传同一文件 |
|------|---------|----------------|
| 排班导入 | 按 xlsx 内覆盖到的日期，先删旧排班再插入 | 安全，数据不重复 |
| 签到导入 | 按签到时间所在日期，先删旧记录再插入 | 安全，数据不重复 |
| 工作量导入 | 按详单内覆盖到的日期，先删旧记录再插入 | 安全，数据不重复 |

因此 RPA 失败后**直接整段重跑即可**，无需人工清理数据。

## 五、错误处理建议

| HTTP 码 | 含义 | RPA 处理 |
|--------|------|---------|
| 200 | 成功 | 记录响应 JSON 到日志 |
| 400 | 文件解析失败/格式错误（如 `{"detail":"未解析到有效数据"}`） | 保留原始文件到错误目录，告警人工检查 |
| 401 | token 无效或过期 | 重新执行步骤①登录后重试一次 |
| 403 | 权限不足或账号被禁用 | 告警管理员，停止重试 |
| 422 | 参数缺失（如 multipart 字段名不是 file） | 告警，属于配置错误 |
| 5xx / 连接超时 | 服务不可用 | 延迟 1~5 分钟重试 2~3 次 |

通用策略：任一步非 200 即中止本次任务并保留已下载文件，下次调度周期重跑。

## 六、Cyclone 配置要点

> ⚠️ Cyclone 的「Http(s)请求」组件请求体只支持键值对/文本，**不支持 multipart 文件上传**，无法直接用它传文件。请改用下方 Python 组件方式（登录、token、上传顺序脚本内部已处理好）。

### 方式 A：调用代码块组件（推荐）

1. 把 `rpa/upload_to_system.py` 拷贝到 RPA 机器固定位置（如 `D:\rpa\upload_to_system.py`）
2. 流程末尾添加「调用代码块」组件，脚本路径选择该文件，点「保存脚本文件并解析」
3. **方法名称选 `main`**（其余 http_post/login/run 等是内部函数，不要选）
4. `args` 两种填法任选：
   - **留空**：使用脚本顶部 `CONFIG` 里的配置（提前在文件里改好 api_base/账号密码/三个文件路径，文件路径可写 RPA 下载步骤的落地路径）
   - **传列表**：`["https://<服务器IP>", "rpa_bot", "<密码>", "排班.xlsx路径", "签到.csv路径", "工作量.xlsx路径"]`（没有的文件省略尾参即可，如只传排班就写 4 个元素）
5. **https 自签名证书**（如 `https://133.0.83.76`）：保持 `CONFIG["verify_ssl"] = False` 即可；若换成正式 CA 证书可改 `True`
6. 「输出结果」绑定流程变量，返回 dict：`{"success": true/false, "schedule_upload": {...}, "checkin_upload": {...}, "workload_upload": {...}}`，失败时含 `error` 字段
7. 后接条件组件判断 `输出结果.success`，false 时走告警分支

### 方式 B：执行系统命令组件

RPA 机器装有 Python 时，也可用「执行系统命令/CMD」组件调用：

```
python rpa\upload_to_system.py http://<服务器IP>:8000 rpa_bot <密码> "D:\download\排班出勤情况.xlsx" "D:\download\签入签出.csv"
```

退出码 0=成功、1=失败；stdout 最后一行为 `RESULT: {...}` JSON。

### 结果处理

- `RESULT` 中 `schedule_upload.message` / `checkin_upload.count` 存在即导入成功，可写入 RPA 日志
- `success=false` 时按第五节错误处理策略告警/重试（脚本本身无重试，重试交给 RPA 调度）
- 每次运行脚本内部重新登录，token 24 小时时效不影响每日调度

## 七、上线前验证

可用冒烟脚本在任意能装 curl 的机器上预验账号权限与文件格式（与 RPA 调用完全等价）：

```bash
export API_BASE=http://<服务器IP>:8000
export RPA_USER=rpa_bot RPA_PASS='******'
./test_file/rpa_upload_smoke.sh "test_file/排班出勤情况2026_7_27 09_25_57.xlsx" <签入签出.csv> "test_file/03客服代表工作量和操作情况统计表....XLSX"
```

也可直接用上传脚本自测（与 RPA 内运行完全一致）：

```bash
python3 rpa/upload_to_system.py http://<服务器IP>:8000 rpa_bot <密码> "排班.xlsx" "签到.csv" "工作量.xlsx"
```

验收清单：

- [ ] 脚本输出 PASS 且无 FAIL
- [ ] 「排班管理」对应日期出现排班数据
- [ ] 「签到记录」出现当日明细（count 与脚本一致）
- [ ] 「工作量详单」出现对应日期的指标数据
- [ ] 「考勤日报」状态/工时已自动计算
- [ ] 「操作日志」可见 rpa_bot 的 import_checkins / import_attendance_report / import_workloads 记录
- [ ] 同一文件重复执行一遍，页面数据无重复无报错
