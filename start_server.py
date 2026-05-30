# -*- coding: utf-8 -*-
"""EasyTrader 远程交易服务一键启动脚本

用法:
    1. 复制配置文件:  cp .env.example .env
    2. 编辑 .env 填入 API Key
    3. 启动服务:      python start_server.py

服务启动后仅监听端口，不会自动登录券商客户端。
需由客户端调用 POST /prepare 传入券商类型和登录参数后才能执行交易。

配置通过 .env 文件读取，也可通过同名环境变量覆盖。
"""

import os
import sys


def load_env(path=".env"):
    """读取 .env 文件，将键值对注入环境变量（不覆盖已有的环境变量）。"""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value


def main():
    load_env()

    port = int(os.environ.get("PORT", "1430").strip())
    api_key = os.environ.get("EASYTRADER_API_KEY", "").strip() or None

    print("启动 EasyTrader 远程交易服务")
    print(f"  端口: {port}")
    print(f"  API Key: {'已配置' if api_key else '未配置 (无认证保护)'}")
    print()
    print("服务启动后，请由客户端调用 POST /prepare 登录券商客户端")
    print()

    from easytrader import server
    server.run(port=port, api_key=api_key)


if __name__ == "__main__":
    main()
