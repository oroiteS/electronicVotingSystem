# app/__init__.py
import os
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from flask_apscheduler import APScheduler

from .utils import web3_utils

jwt = JWTManager()
db = SQLAlchemy()
scheduler = APScheduler()


def create_app():
    app = Flask(__name__)

    try:
        app.config.from_object('config')
    except ImportError:
        # 获取 system-backend 目录的路径
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        config_path = os.path.join(backend_dir, 'config.py')
        if os.path.exists(config_path):
            app.config.from_pyfile(config_path)
        else:
            import config
            app.config.from_object(config)

    db.init_app(app)
    jwt.init_app(app)
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        scheduler.init_app(app)
        scheduler.start()
    # 允许跨域请求
    # 初始化CORS，仅允许来自前端源的请求
    CORS(app, resources={r"/api/*": {"origins": "http://localhost:8080"}})

    # --- 配置日志 (移到扩展初始化之后，确保 app.logger 可用) ---
    if not app.debug and not app.testing:  # 仅在非调试和非测试模式下启用文件日志
        log_dir = os.path.join(app.root_path, '..', 'logs')  # logs 文件夹在 system-backend 目录下
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)  # 使用 makedirs 以创建可能不存在的父目录
            except OSError as e:
                app.logger.error(f"Error creating log directory {log_dir}: {e}")

        if os.path.exists(log_dir):  # 再次检查，如果创建失败则不添加处理器
            file_handler = RotatingFileHandler(
                os.path.join(log_dir, 'voting_app.log'),
                maxBytes=10240,
                backupCount=10,
                encoding='utf-8'
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)  # 文件日志级别
            app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)  # 应用自身的日志级别
    app.logger.info('Voting App starting up...')

    # 初始化 Web3 连接
    with app.app_context():
        try:
            web3_utils.init_web3(app)
            app.logger.info("Web3 initialized successfully.")
        except Exception as e:
            app.logger.error(f"Failed to initialize Web3: {e}", exc_info=True)

    # 注册蓝图（模块化路由）
    from app.routes.vote_routes import vote_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.user_routes import user_bp
    from app.routes.auth_routes import auth_bp

    app.register_blueprint(vote_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(auth_bp)

    return app
