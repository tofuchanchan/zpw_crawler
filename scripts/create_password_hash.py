from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.zpw_crawler.auth import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 Streamlit 登录密码哈希")
    parser.add_argument("--username", default="admin", help="登录用户名")
    parser.add_argument("--password", help="登录密码；不传则安全提示输入")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Password: ")
    password_confirm = args.password or getpass.getpass("Confirm password: ")
    if password != password_confirm:
        raise SystemExit("两次密码不一致")

    print("[auth.users]")
    print(f'{args.username} = "{hash_password(password)}"')


if __name__ == "__main__":
    main()
