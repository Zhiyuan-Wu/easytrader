# -*- coding: utf-8 -*-
import base64
import json
import os
import sys

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

PREFIX = "enc:"
_SALT = b"easytrader_credential_salt_v1"


def _derive_key(master_password: str) -> bytes:
    """Derive a Fernet-compatible key from master password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=480_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))


def encrypt_value(plaintext: str, master_password: str) -> str:
    """Encrypt a string value, returning PREFIX + ciphertext."""
    key = _derive_key(master_password)
    token = Fernet(key).encrypt(plaintext.encode())
    return PREFIX + token.decode()


def decrypt_value(ciphertext: str, master_password: str) -> str:
    """Decrypt a PREFIX + ciphertext string, returning plaintext."""
    if not ciphertext.startswith(PREFIX):
        return ciphertext
    key = _derive_key(master_password)
    token = ciphertext[len(PREFIX):]
    return Fernet(key).decrypt(token.encode()).decode()


def decrypt_config(config: dict, master_password: str) -> dict:
    """Decrypt all sensitive fields in a config dict in-place."""
    sensitive_keys = {"password", "comm_password"}
    for key in sensitive_keys:
        if key in config and isinstance(config[key], str) and config[key].startswith(PREFIX):
            config[key] = decrypt_value(config[key], master_password)
    return config


def get_master_password() -> str:
    """Get master password from env var or prompt."""
    password = os.environ.get("EASYTRADER_MASTER_PASSWORD", "")
    if password:
        return password
    if sys.stdin.isatty():
        from getpass import getpass
        return getpass("请输入主密码以解密配置文件: ")
    raise RuntimeError(
        "配置文件包含加密字段但未设置 EASYTRADER_MASTER_PASSWORD 环境变量，"
        "且无法交互式输入密码"
    )


def encrypt_config_file(config_path: str):
    """Encrypt sensitive fields in a JSON config file. Interactive CLI utility."""
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    sensitive_keys = {"password", "comm_password"}
    has_plain = any(
        key in config and isinstance(config[key], str) and not config[key].startswith(PREFIX)
        for key in sensitive_keys
    )
    if not has_plain:
        print("配置文件中没有需要加密的明文字段")
        return

    from getpass import getpass
    master_password = getpass("请设置主密码: ")
    confirm = getpass("请确认主密码: ")
    if master_password != confirm:
        print("两次输入的密码不一致")
        return

    for key in sensitive_keys:
        if key in config and isinstance(config[key], str) and not config[key].startswith(PREFIX):
            config[key] = encrypt_value(config[key], master_password)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    print(f"已加密 {config_path} 中的敏感字段")
