# -*- coding: utf-8 -*-
"""EasyTrader 远程交易服务一键启动脚本

用法:
    1. 复制配置文件:  cp .env.example .env
    2. 编辑 .env 填入券商信息和 API Key
    3. 启动服务:      python start_server.py

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
            # 去掉引号
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            # 环境变量优先，不覆盖
            if key and key not in os.environ:
                os.environ[key] = value


def get_required(key, label=None):
    value = os.environ.get(key, "").strip()
    if not value:
        label = label or key
        print(f"错误: 缺少必要配置 {label}，请在 .env 中设置 {key}")
        sys.exit(1)
    return value


def get_optional(key, default=""):
    return os.environ.get(key, default).strip()


def main():
    load_env()

    # ── 服务配置 ──
    port = int(get_optional("PORT", "1430"))
    api_key = get_optional("EASYTRADER_API_KEY")

    # ── 券商配置 ──
    broker = get_required("BROKER", "券商类型")

    config_path = get_optional("CONFIG_PATH")
    user = get_optional("USER")
    password = get_optional("PASSWORD")
    exe_path = get_optional("EXE_PATH")
    comm_password = get_optional("COMM_PASSWORD")

    # 检查登录参数：配置文件 或 账号密码 至少提供一组
    has_config = bool(config_path)
    has_credentials = bool(user and password)
    if not has_config and not has_credentials:
        print("错误: 请设置 CONFIG_PATH（配置文件路径）或 USER + PASSWORD（账号密码）")
        sys.exit(1)

    # ── 启动服务 ──
    from easytrader import server

    print(f"启动 EasyTrader 远程交易服务")
    print(f"  券商: {broker}")
    print(f"  端口: {port}")
    print(f"  API Key: {'已配置' if api_key else '未配置 (无认证保护)'}")
    print(f"  登录方式: {'配置文件 ' + config_path if has_config else '账号密码'}")
    print()

    # 先启动 Flask，在 prepare 接口中登录券商
    # 通过 /prepare 接口传入券商参数
    server.run(port=port, api_key=api_key or None)


if __name__ == "__main__":
    main()
