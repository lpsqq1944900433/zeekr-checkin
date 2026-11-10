#!/usr/bin/env python3
"""管理本仓库映射到青龙的六条任务；只使用 Python 标准库。"""

import argparse
import json
import secrets
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
API = "http://127.0.0.1:5700/api"
AUTH_FILE = BASE / "data" / "config" / "auth.json"
LOGIN_FILE = BASE / "data" / "panel-login.txt"
TASKS = [
    ("zeekr_0001_all.js", "极氪签到·凌晨场", "1 0 * * *"),
    ("zeekr_0010_claim.js", "极氪签到·凌晨补领", "10 0 * * *"),
    ("zeekr_0810_all.js", "极氪签到·早间场", "10 8 * * *"),
    ("zeekr_0820_claim.js", "极氪签到·早间补领", "20 8 * * *"),
    ("zeekr_2130_all.js", "极氪签到·晚间场", "30 21 * * *"),
    ("zeekr_2140_claim.js", "极氪签到·晚间补领", "40 21 * * *"),
]


def command(entry):
    return f"task zeekr-local/run.js -- {entry}"


def request(method, endpoint, data=None, token=None):
    headers = {"Content-Type": "application/json", "User-Agent": "ZeekrLocalSetup/1.0"}
    if token:
        headers["Authorization"] = "Bearer " + token
    payload = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(API + endpoint, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"青龙 API {method} {endpoint} 返回 HTTP {error.code}") from None
    if result.get("code") != 200:
        raise RuntimeError(f"青龙 API {method} {endpoint} 失败，状态码 {result.get('code')}")
    return result.get("data")


def wait_ready():
    for attempt in range(60):
        try:
            return request("GET", "/system")
        except (OSError, RuntimeError):
            if attempt == 59:
                raise RuntimeError("青龙未就绪，请先运行 docker compose up -d 并检查容器日志。") from None
            time.sleep(2)


def login(initialize=False):
    system = wait_ready()
    if not system.get("isInitialized"):
        if not initialize:
            raise RuntimeError("面板尚未初始化，请先运行本脚本的 install 命令。")
        # 在发送初始化请求前先保存随机密码，便于中途退出后恢复。
        if LOGIN_FILE.exists():
            values = LOGIN_FILE.read_text(encoding="utf-8").splitlines()
            credentials = dict(line.split("=", 1) for line in values if "=" in line)
            credentials = {key: credentials[key] for key in ("username", "password")}
        else:
            credentials = {"username": "admin", "password": secrets.token_urlsafe(24)}
            LOGIN_FILE.write_text(
                "url=http://127.0.0.1:5700\n"
                f"username={credentials['username']}\npassword={credentials['password']}\n",
                encoding="utf-8",
            )
        request("PUT", "/user/init", credentials)
        # 该镜像版本的密码更新通过异步文件写入完成。
        for _ in range(30):
            auth = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
            if auth.get("password") == credentials["password"]:
                break
            time.sleep(0.1)
    auth = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    credentials = {key: auth[key] for key in ("username", "password")}
    result = request("POST", "/user/login", credentials)
    return result["token"]


def get_tasks(token):
    data = request("GET", "/crons", token=token)
    return data if isinstance(data, list) else data["data"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["install", "status", "run"])
    parser.add_argument("entry", nargs="?", choices=[item[0] for item in TASKS])
    args = parser.parse_args()
    if args.action == "run" and not args.entry:
        parser.error("run 需要指定入口文件名")
    token = login(initialize=args.action == "install")
    tasks = get_tasks(token)
    if args.action == "install":
        for entry, name, schedule in TASKS:
            matches = [task for task in tasks if task["command"] == command(entry)]
            if len(matches) > 1:
                raise RuntimeError(f"发现重复任务：{entry}，请先在面板核对。")
            if matches:
                print(f"保留已有任务（含自定义时间/启停状态）：{name}")
            else:
                created = request("POST", "/crons", {
                    "name": name, "command": command(entry), "schedule": schedule,
                }, token=token)
                tasks.append(created)
                print(f"已创建：{name} | {schedule}")
        print(f"登录信息保存在本机（不输出密码）：{LOGIN_FILE}")
        tasks = get_tasks(token)
    if args.action == "run":
        matches = [task for task in tasks if task["command"] == command(args.entry)]
        if len(matches) != 1:
            raise RuntimeError("未找到唯一任务，请先 install 或检查面板重复项。")
        request("PUT", "/crons/run", [matches[0]["id"]], token=token)
        print(f"已提交运行：{matches[0]['name']}（ID {matches[0]['id']}），请查看面板任务日志。")
        return
    for entry, _, _ in TASKS:
        matches = [task for task in tasks if task["command"] == command(entry)]
        for task in matches:
            print(json.dumps({key: task.get(key) for key in (
                "id", "name", "command", "schedule", "isDisabled", "status", "log_path",
            )}, ensure_ascii=False))
    count = sum(task["command"] in {command(item[0]) for item in TASKS} for task in tasks)
    if count != 6:
        raise RuntimeError(f"当前应有 6 条本机任务，实际为 {count} 条。")
    print("已确认 6 条本机极氪任务；时间使用容器 Asia/Shanghai 时区。")


if __name__ == "__main__":
    # Windows 控制台也使用 UTF-8，便于输出中文任务名称。
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"操作失败：{error}", file=sys.stderr)
        sys.exit(1)
