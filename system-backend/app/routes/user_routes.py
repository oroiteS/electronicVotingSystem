# app/routes/user_routes.py
import json

from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from .. import db
from ..models.models import User, VoterApplication, Voter  # 需要 Voter 模型来检查是否已是选民

user_bp = Blueprint('user_routes', __name__, url_prefix='/api/user')


@user_bp.route('/apply_voter', methods=['POST'])
@jwt_required()  # <--- 需要登录才能申请
def apply_to_be_voter():
    """注册用户申请成为选民"""
    try:
        current_user_identity = json.loads(get_jwt_identity())
        user_db_id = current_user_identity.get('id')  # 从JWT获取用户ID

        user = User.query.get(user_db_id)
        if not user:  # 理论上 @jwt_required 保证了用户存在，但以防万一
            return jsonify({"success": False, "message": "Authenticated user not found in database."}), 404

        if user.role == 'admin':
            return jsonify({"success": False, "message": "Admin users cannot apply to be voters."}), 403

        if not user.ethereum_address:
            return jsonify({"success": False,
                            "message": "User does not have an Ethereum address associated. "
                                       "Please update user profile or re-login."}), 400

        existing_voter_record = Voter.query.filter_by(user_id=user.id).first()
        if existing_voter_record:
            return jsonify({"success": False, "message": "User is already a registered voter."}), 409

        existing_application = VoterApplication.query.filter_by(user_id=user.id) \
            .filter(VoterApplication.status.in_(['pending', 'approved'])).first()
        if existing_application:
            return jsonify({
                "success": False,
                "message": f"User already has a '{existing_application.status}' voter application."
            }), 409

        new_application = VoterApplication(
            user_id=user.id,
            status='pending'
        )
        db.session.add(new_application)
        db.session.commit()

        current_app.logger.info(
            f"User ID {user.id} ({user.userid}) submitted voter application ID {new_application.id}.")
        return jsonify({
            "success": True,
            "message": "Voter application submitted successfully.",
            "application": new_application.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error submitting voter application: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500
