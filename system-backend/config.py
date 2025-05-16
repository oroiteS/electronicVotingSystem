# config.py
from datetime import timedelta
import os

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # system-backend目录
# 上传文件存储目录
UPLOADS_DIRECTORY = os.path.join(BASE_DIR, 'uploads')
# API基础URL，用于构建图片访问地址
BASE_URL = 'http://127.0.0.1:5000'  # 根据你的实际部署环境修改

# ganache配置
GANACHE_RPC_URL = 'http://127.0.0.1:7545'
CONTRACT_ADDRESS = '区块链地址'
CONTRACT_ABI_PATH = '合约地址'
ADMIN_ACCOUNT_PRIVATE_KEY = '管理员私钥'

# sqlalchemy配置
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:你的密码@localhost:3306/voting'
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = False

# JWT配置
JWT_SECRET_KEY = 'this is a secret key'
JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=1)

# 配置作业存储
SCHEDULER_JOB_STORES = {
    'default': {
        'type': 'sqlalchemy',
        'url': SQLALCHEMY_DATABASE_URI
    }
}

SCHEDULER_JOB_DEFAULTS = {
    'coalesce': False,
    'max_instances': 3
}
