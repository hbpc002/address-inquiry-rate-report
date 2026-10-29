"""验证 Docker/CI 配置能避免依赖层被反复重建。

历史问题：后端和前端镜像共用默认的 GHA 缓存 scope，后构建的前端会覆盖
后端的缓存索引，导致下一轮后端重新执行 pip install，生成新的约 100MB
依赖层，部署端每次更新都要整层重拉。

本测试解析 GitHub Actions 工作流和 backend Dockerfile，断言：
- 两个镜像使用彼此独立的缓存 scope；
- 依赖安装层保持在应用代码层之前；
- 基础镜像固定 digest，且只拷贝运行所需代码；
- .dockerignore 排除会频繁变化的非运行文件。
"""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "docker.yml"
BACKEND_DOCKERFILE = ROOT / "backend" / "Dockerfile"
BACKEND_DOCKERIGNORE = ROOT / "backend" / ".dockerignore"


def _workflow_steps():
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return data["jobs"]["build-and-push"]["steps"]


def _build_step(image: str) -> dict:
    for step in _workflow_steps():
        uses = step.get("uses", "")
        name = step.get("name", "")
        if uses.startswith("docker/build-push-action") and image in name:
            return step.get("with", {})
    raise AssertionError(f"未找到 {image} 镜像的构建步骤")


def _cache_lines(step: dict) -> list[str]:
    lines = []
    for key in ("cache-from", "cache-to"):
        lines.extend(step.get(key, "").splitlines())
    return [line.strip() for line in lines if line.strip()]


def test_backend_and_frontend_use_distinct_gha_scopes():
    backend = _build_step("backend")
    frontend = _build_step("frontend")

    assert "type=gha,scope=backend" in backend["cache-from"]
    assert "type=gha,mode=max,scope=backend" in backend["cache-to"]
    assert "type=gha,scope=frontend" in frontend["cache-from"]
    assert "type=gha,mode=max,scope=frontend" in frontend["cache-to"]


def test_every_gha_cache_entry_has_an_explicit_scope():
    for image in ("backend", "frontend"):
        for line in _cache_lines(_build_step(image)):
            if "type=gha" in line:
                assert re.search(r"(?<![\w-])scope=[\w-]+", line), (
                    f"{image} 的 GHA 缓存缺少显式 scope: {line}"
                )


def test_registry_cache_is_isolated_per_image():
    backend = _build_step("backend")
    frontend = _build_step("frontend")

    for key in ("cache-from", "cache-to"):
        assert "-backend:buildcache" in backend[key]
        assert "-frontend:buildcache" in frontend[key]

    assert "ignore-error=true" in backend["cache-to"]
    assert "ignore-error=true" in frontend["cache-to"]


def test_backend_base_image_is_pinned_by_digest():
    first_from = next(
        line.strip()
        for line in BACKEND_DOCKERFILE.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("FROM ")
    )
    assert re.match(r"FROM python:3\.11-slim@sha256:[0-9a-f]{64}$", first_from), (
        f"基础镜像未固定 digest: {first_from}"
    )


def test_backend_dependencies_install_before_app_code():
    content = BACKEND_DOCKERFILE.read_text(encoding="utf-8")
    assert content.index("COPY requirements.txt") < content.index("pip install")
    assert content.index("pip install") < content.index("COPY app/ ./app/")


def test_backend_dockerfile_copies_only_runtime_code():
    content = BACKEND_DOCKERFILE.read_text(encoding="utf-8")
    assert "COPY app/ ./app/" in content
    assert "COPY . ." not in content
    for excluded in ("COPY tests/", "COPY nohup.out", "COPY uploads/"):
        assert excluded not in content


def test_backend_dockerignore_excludes_volatile_files():
    entries = {
        line.strip()
        for line in BACKEND_DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    expected = {
        "tests/",
        ".pytest_cache/",
        "nohup.out",
        "uploads/",
        "test_file/",
        "*.xlsx",
        "*.xls",
    }
    missing = expected - entries
    assert not missing, f".dockerignore 缺少排除项: {sorted(missing)}"
