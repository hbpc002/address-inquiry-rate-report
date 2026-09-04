"""验证 Docker 镜像内置的 nginx 反代配置对 SSE 已启用透传。

历史问题：/api 反代未关闭 proxy_buffering，导致智能体对话的 SSE 事件被
nginx 缓冲、请求结束后才一次性发给浏览器，表现为"长时间空白后整体出现"。
本测试解析两个 Dockerfile 中通过 printf 生成的 nginx 配置，断言 /api 块
包含实时透传所需的指令。
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

# 生产部署使用的镜像源（docker-compose.yml + build.sh）
_PRIMARY_DOCKERFILES = [ROOT / "frontend" / "Dockerfile"]
# 遗留的单体镜像部署路径（docker-compose.deploy.yml）
_LEGACY_DOCKERFILES = [ROOT / "Dockerfile"]


def _extract_nginx_conf(path: Path) -> str:
    """从 Dockerfile 的 `printf '<conf>' > ...` 提取 nginx 配置并还原换行。"""
    raw = path.read_text(encoding="utf-8")
    m = re.search(r"printf '([^']*)' >\s*\S*default\.conf", raw)
    assert m, f"{path.name}: 未找到 printf 生成的 nginx 配置"
    body = m.group(1)
    # 还原转义的 `\n`；输出中不能出现未转义的真实换行被 printf 破坏
    conf = body.replace("\\n", "\n")
    return conf


def _api_block(conf: str) -> str:
    """从 nginx 配置中提取 location /api 块。"""
    # 定位第一个 location /api 块（含花括号）
    idx = conf.find("location /api {")
    assert idx != -1, "nginx 配置中缺少 location /api 块"
    # 找到块的结束花括号（同一 indentation 级别）
    open_pos = conf.find("{", idx)
    depth = 0
    for i in range(open_pos, len(conf)):
        if conf[i] == "{":
            depth += 1
        elif conf[i] == "}":
            depth -= 1
            if depth == 0:
                return conf[idx:i + 1]
    raise AssertionError("location /api 块未闭合")


def _assert_sse_passthrough(path: Path):
    conf = _extract_nginx_conf(path)
    block = _api_block(conf)
    # 关键：关闭缓冲，SSE 事件实时透传
    assert "proxy_buffering off" in block, f"{path.name} 缺少 proxy_buffering off"
    assert "proxy_cache off" in block, f"{path.name} 缺少 proxy_cache off"
    # SSE 需 HTTP/1.1 且清除 Connection，避免 keep-alive 缓冲
    assert "proxy_http_version 1.1" in block, f"{path.name} 缺少 proxy_http_version 1.1"
    assert 'proxy_set_header Connection ""' in block, f"{path.name} 缺少 Connection 透传"
    # 长连接不超时，复杂查询可能较久
    assert "proxy_read_timeout" in block, f"{path.name} 缺少 proxy_read_timeout"
    assert "proxy_send_timeout" in block, f"{path.name} 缺少 proxy_send_timeout"
    # 反代目标不应被改动
    assert "proxy_pass" in block, f"{path.name} 缺少 proxy_pass"


def test_frontend_dockerfile_sse_passthrough():
    """生产前端镜像（nginx 反代 → schedule-api:8000）必须启用 SSE 透传。"""
    for path in _PRIMARY_DOCKERFILES:
        assert path.exists(), f"缺少 {path}"
        _assert_sse_passthrough(path)


def test_legacy_dockerfile_sse_passthrough():
    """遗留单体镜像（nginx 反代 → localhost:8000）同样应启用 SSE 透传。"""
    for path in _LEGACY_DOCKERFILES:
        assert path.exists(), f"缺少 {path}"
        _assert_sse_passthrough(path)


def test_api_block_proxy_target_preserved():
    """确保改动未破坏反代目标配置。"""
    conf = _extract_nginx_conf(_PRIMARY_DOCKERFILES[0])
    assert "http://schedule-api:8000" in _api_block(conf)
    legacy = _extract_nginx_conf(_LEGACY_DOCKERFILES[0])
    assert "http://localhost:8000" in _api_block(legacy)


def test_static_block_unaffected():
    """/static 块不应被 /api 的 SSE 改动波及（保持原有行为）。"""
    conf = _extract_nginx_conf(_PRIMARY_DOCKERFILES[0])
    # 全配置应只含一次 (proxy_buffering off / 1.1 / Connection)，均在 /api 内
    assert conf.count("proxy_buffering off") == 1
    assert conf.count("proxy_http_version 1.1") == 1
