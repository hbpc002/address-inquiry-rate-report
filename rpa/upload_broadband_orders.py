#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RPA 自动上传脚本(纯Python标准库, 3.6+, 无需requests)

流程: 登录 -> 上传新客服无缝订单-原始表.XLSX(宽带营销原始数据)
输出: 全程ASCII日志, 最后一行 RESULT: {...}; 退出码 0=成功 1=失败

用法A(Cyclone Python组件粘贴): 修改下方 CONFIG 后整体粘贴执行
用法B(命令行):
  python upload_broadband_orders.py <API地址> <用户名> <密码> [新客服无缝订单-原始表.XLSX]
"""
import json
import ssl
import sys
import uuid
from urllib import request as urlrequest
from urllib import error as urlerror
from urllib.parse import urlencode

CONFIG = {
    "api_base": "http://<服务器IP>:8000",
    "username": "rpa_bot",
    "password": "CHANGE_ME",
    "orders_file": "",  # 例: r"D:\download\新客服无缝订单-原始表.XLSX", 留空跳过
    "verify_ssl": False,  # 自签名证书(https)保持 False; 正式CA证书可改 True
}

_SSL_CTX = None


def _ssl_context():
    global _SSL_CTX
    if CONFIG.get("verify_ssl"):
        return None
    if _SSL_CTX is None:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        _SSL_CTX = ctx
    return _SSL_CTX


def log(msg):
    print(msg)
    sys.stdout.flush()


def http_post(url, data=None, headers=None, timeout=60):
    req = urlrequest.Request(url, data=data, headers=headers or {}, method="POST")
    try:
        with urlrequest.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
            return resp.getcode(), resp.read().decode("utf-8", "replace")
    except urlerror.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def login(api_base, username, password):
    body = urlencode({"username": username, "password": password}).encode("utf-8")
    code, text = http_post(
        api_base + "/api/auth/login", data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
    if code != 200:
        raise RuntimeError("login failed http %s: %s" % (code, text[:200]))
    token = json.loads(text).get("access_token")
    if not token:
        raise RuntimeError("login ok but no access_token: %s" % text[:200])
    return token


def upload_file(api_base, endpoint, file_path, token, send_name):
    with open(file_path, "rb") as f:
        content = f.read()
    boundary = "----RPA%s" % uuid.uuid4().hex
    body = b"".join([
        ("--%s\r\n" % boundary).encode("ascii"),
        ('Content-Disposition: form-data; name="file"; filename="%s"\r\n'
         % send_name).encode("ascii"),
        b"Content-Type: application/octet-stream\r\n\r\n",
        content,
        ("\r\n--%s--\r\n" % boundary).encode("ascii"),
    ])
    headers = {
        "Content-Type": "multipart/form-data; boundary=%s" % boundary,
        "Authorization": "Bearer %s" % token,
    }
    return http_post(api_base + endpoint, data=body, headers=headers, timeout=300)


def run(api_base, username, password, orders_file):
    api_base = api_base.rstrip("/")
    if not orders_file:
        raise RuntimeError("no file to upload")
    log("STEP login: start (%s)" % api_base)
    token = login(api_base, username, password)
    log("STEP login: OK")
    result = {"login": "ok"}
    # 发送名固定为 ASCII, 避免 multipart 头中文文件名编码异常
    code, text = upload_file(
        api_base, "/api/broadband/orders/import",
        orders_file, token, "seamless_orders_raw.xlsx")
    if code != 200:
        raise RuntimeError("broadband orders upload failed http %s: %s" % (code, text[:300]))
    log("STEP broadband orders upload: OK %s" % text[:200])
    result["orders_upload"] = json.loads(text)
    return result


def main(args=None):
    args = list(args or [])
    if len(args) >= 4:
        api_base, username, password, orders_file = args[0], args[1], args[2], args[3]
    else:
        api_base = CONFIG["api_base"]
        username = CONFIG["username"]
        password = CONFIG["password"]
        orders_file = CONFIG["orders_file"]
    try:
        result = run(api_base, username, password, orders_file)
        result["success"] = True
    except Exception as e:
        result = {"success": False, "error": str(e)}
    log("RESULT: %s" % json.dumps(result, ensure_ascii=True))
    return result


# Cyclone「调用代码块」组件: 方法名称选 main, args留空则用CONFIG
# 命令行直接运行: python upload_broadband_orders.py <api> <user> <pass> [无缝订单原始表.XLSX]
if __name__ == "__main__":
    result = main(sys.argv[1:])
    sys.exit(0 if result.get("success") else 1)
