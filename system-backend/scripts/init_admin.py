# init_admin.py
import os
import sys

from dotenv import load_dotenv

from app import create_app, db
from app.models.models import User
from app.utils.web3_utils import get_ganache_accounts  # 确保 init_web3 在 get_w3 前被调用

# 将 system-backend 目录添加到 Python 路径
# 假设此脚本在 system-backend 的父目录运行，或者根据你的项目结构调整
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
backend_dir = os.path.join(project_root, 'system-backend')  # 如果脚本在项目根目录，则此路径正确
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv(os.path.join(backend_dir, '.env'))  # 加载 .env 文件

app = create_app()


def initialize_admin():
    with app.app_context():
        try:
            # 初始化 Web3，这样才能获取 Ganache 账户
            # init_web3(app) # create_app 内部应该已经调用了 init_web3

            admin_userid = '2025'
            admin_password = '2025'  # 明文密码，将在 User 模型中哈希
            admin_role = 'admin'

            # 检查管理员是否已存在
            existing_admin = User.query.filter_by(userid=admin_userid, role=admin_role).first()
            if existing_admin:
                print(f"Admin user '{admin_userid}' already exists.")
                # 可选：更新密码或以太坊地址
                # existing_admin.set_password(admin_password)
                # db.session.commit()
                # print(f"Admin user '{admin_userid}' password updated (if changed).")
                return

            # 获取 Ganache 的第一个账户作为管理员的以太坊地址
            ganache_accounts = get_ganache_accounts()  # 使用已封装的函数

            if not ganache_accounts:
                print("Error: No Ganache accounts found. Cannot set admin Ethereum address.")
                admin_eth_address = None
            else:
                admin_eth_address = ganache_accounts[0]
                print(f"Admin Ethereum address will be set to: {admin_eth_address}")

            # 检查该以太坊地址是否已被其他用户使用 (虽然管理员是第一个用户，以防万一)
            if admin_eth_address:
                addr_exists = User.query.filter_by(ethereum_address=admin_eth_address).first()
                if addr_exists:
                    print(f"Warning: Ethereum address {admin_eth_address} "
                          f"is already in use by user {addr_exists.userid}.")
                    print("Skipping admin creation to avoid conflict. Please resolve manually.")
                    return

            admin_user = User(
                userid=admin_userid,
                role=admin_role,
                ethereum_address=admin_eth_address
            )
            admin_user.set_password(admin_password)  # 哈希密码

            db.session.add(admin_user)
            db.session.commit()
            print(f"Admin user '{admin_userid}' created successfully with Ethereum address '{admin_eth_address}'.")

        except Exception as e:
            db.session.rollback()
            print(f"An error occurred during admin initialization: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    print("Initializing admin user...")
    initialize_admin()
    print("Admin initialization process finished.")
