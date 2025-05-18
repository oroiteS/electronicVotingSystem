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


def create_app(init_scheduler=True):
    app = Flask(__name__)

    # Load config
    try:
        app.config.from_object('config')
    except ImportError:
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        config_path = os.path.join(backend_dir, 'config.py')
        if os.path.exists(config_path):
            app.config.from_pyfile(config_path)
        else:
            import config
            app.config.from_object(config)

    db.init_app(app)
    jwt.init_app(app)

    if init_scheduler:
        if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            scheduler.init_app(app)
            scheduler.start()
            app.logger.info("APScheduler initialized and started.")
        elif app.debug:
            app.logger.info("APScheduler not started in debug reloader sub-process.")
    else:
        app.logger.info("APScheduler initialization skipped for this app instance.")

    CORS(app, resources={r"/api/*": {"origins": "http://localhost:8080"}})

    # --- 配置日志 ---
    log_level = logging.INFO
    app.logger.setLevel(log_level)

    is_main_process_or_not_debug = not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true'

    if not app.debug and is_main_process_or_not_debug: 
        log_dir = os.path.join(app.root_path, '..', 'logs')
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except OSError as e:
                print(f"Error creating log directory {log_dir}: {e}")

        if os.path.exists(log_dir):
            file_handler = RotatingFileHandler(
                os.path.join(log_dir, 'voting_app.log'),
                maxBytes=10240,
                backupCount=10,
                encoding='utf-8'
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            app.logger.addHandler(file_handler)
            app.logger.info("RotatingFileHandler added for non-debug mode.")

    # 确保主启动信息只打印一次
    if is_main_process_or_not_debug:
        app.logger.info('Voting App starting up...')

    # 初始化 Web3 连接 
    with app.app_context():
        try:
            web3_utils.init_web3(app)
            # 日志放里面，确保只在成功后打印
            if is_main_process_or_not_debug:  # 只在主进程的第一次create_app时打印
                app.logger.info("Web3 initialized successfully.")
        except Exception as e:
            app.logger.error(f"Failed to initialize Web3: {e}", exc_info=True)

    # 注册蓝图
    from app.routes.vote_routes import vote_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.user_routes import user_bp
    from app.routes.auth_routes import auth_bp

    app.register_blueprint(vote_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(auth_bp)

    return app
