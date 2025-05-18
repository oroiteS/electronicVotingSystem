# app/routes/auth_routes.py
import json
from datetime import timedelta

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from .. import db
from ..models.models import User
from ..utils.web3_utils import get_ganache_accounts, get_w3

auth_bp = Blueprint('auth_routes', __name__, url_prefix='/api/auth')


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Request body must be JSON."}), 400

    userid = data.get('userid')
    password = data.get('password')

    if not userid or not password:
        return jsonify({"success": False, "message": "Userid and password are required."}), 400

    user = User.query.filter_by(userid=userid).first()

    if user and user.check_password(password):
        # 用户身份验证通过，创建 access token
        # 我们可以在 token 中存储用户 ID 和角色
        identity_data = {"id": user.id, "userid": user.userid, "role": user.role}
        # 设置 token 过期时间，例如1天
        expires = timedelta(days=1)
        access_token = create_access_token(identity=json.dumps(identity_data), expires_delta=expires)
        current_app.logger.info(f"User '{userid}' logged in successfully.")
        return jsonify(success=True, access_token=access_token, user=user.to_dict(include_eth_address=True)), 200
    else:
        current_app.logger.warning(f"Login attempt failed for userid '{userid}'.")
        return jsonify({"success": False, "message": "Invalid userid or password."}), 401


@auth_bp.route('/available_eth_addresses', methods=['GET'])
def get_available_eth_addresses_for_registration():
    """获取 Ganache 中尚未被任何用户（users表）使用的地址列表"""
    try:
        all_ganache_accounts = get_ganache_accounts()
        if not all_ganache_accounts:
            return jsonify({"success": True, "available_addresses": [], "message": "No Ganache accounts found."}), 200

        # 查询数据库中所有已分配给用户的以太坊地址
        used_addresses_query = db.session.query(User.ethereum_address).filter(User.ethereum_address.isnot(None)).all()
        used_addresses = {addr[0] for addr in used_addresses_query if addr[0]}  # 转换为 set 方便查找

        # 筛选出未被使用的地址
        available_addresses = [addr for addr in all_ganache_accounts if addr not in used_addresses]

        admin_eth_address = get_w3().eth.default_account
        if admin_eth_address in available_addresses:
            available_addresses.remove(admin_eth_address)

        return jsonify({"success": True, "available_addresses": available_addresses}), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching available Ethereum addresses: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500


@auth_bp.route('/register', methods=['POST'])
def register_user():
    """普通用户注册"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Request body must be JSON."}), 400

        userid = data.get('userid')
        password = data.get('password')
        selected_eth_address = data.get('ethereum_address')  # 用户从前端选择的地址

        if not userid or not password or not selected_eth_address:
            return jsonify({"success": False, "message": "Userid, password, and ethereum_address are required."}), 400
        if not isinstance(userid, str) or not userid.strip():
            return jsonify({"success": False, "message": "Userid must be a non-empty string."}), 400
        if not isinstance(userid, str) or len(password) < 6:  # 简单密码长度校验
            return jsonify({"success": False, "message": "Password must be a string of at least 6 characters."}), 400

        w3 = get_w3()
        if not w3.is_address(selected_eth_address):
            return jsonify({"success": False, "message": "Invalid Ethereum address format."}), 400

        # 1. 检查 userid 是否已存在
        existing_user_userid = User.query.filter_by(userid=userid).first()
        if existing_user_userid:
            return jsonify({"success": False, "message": f"Userid '{userid}' already exists."}), 409

        # 2. 检查以太坊地址是否已被占用 (双重检查，前端获取列表时已经筛选过一次)
        existing_user_eth = User.query.filter_by(ethereum_address=selected_eth_address).first()
        if existing_user_eth:
            return jsonify(
                {"success": False, "message": f"Ethereum address '{selected_eth_address}' is already taken."}), 409

        # 3. 再次验证所选地址是否仍在 Ganache 列表中 (以防万一)
        all_ganache_accounts = get_ganache_accounts()
        # 进一步筛选，排除已在 User 表中被占用的
        used_addresses_in_db_query = db.session.query(User.ethereum_address).filter(
            User.ethereum_address.isnot(None)).all()
        used_addresses_in_db = {addr[0] for addr in used_addresses_in_db_query if addr[0]}

        truly_available_system_addresses = [addr for addr in all_ganache_accounts if addr not in used_addresses_in_db]

        if selected_eth_address not in truly_available_system_addresses:
            return jsonify({"success": False,
                            "message": f"Selected Ethereum address '{selected_eth_address}'"
                                       f" is not available or not a valid system address."}), 400

        new_user = User(
            userid=userid,
            ethereum_address=selected_eth_address,
            role='user'  # 新注册用户默认为 'user'
        )
        new_user.set_password(password)  # 哈希密码

        db.session.add(new_user)
        db.session.commit()

        current_app.logger.info(
            f"New user '{userid}' registered successfully with ETH address '{selected_eth_address}'.")
        return jsonify({
            "success": True,
            "message": "User registered successfully.",
            "user": new_user.to_dict(include_eth_address=True)  # 返回用户信息
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error during user registration: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500


# 获取当前用户信息的接口 (需要登录)
@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user_profile():
    """获取当前登录用户的信息"""
    current_user_identity = json.loads(get_jwt_identity()) 
    user_id_from_token = current_user_identity.get('id')

    user = User.query.get(user_id_from_token)
    if not user:
        return jsonify({"success": False, "message": "User not found (token might be outdated)."}), 404

    # 为了安全，不直接返回 password_hash
    return jsonify({"success": True, "user": user.to_dict(include_eth_address=True, include_voter_status=True)}), 200
