# app/routes/admin_routes.py
import json
import os
from datetime import datetime, UTC  # 用于时间戳
from functools import wraps

from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from web3.exceptions import ContractLogicError
from werkzeug.utils import secure_filename

from .. import db
from ..models.models import CandidateDetails, Voter, User, VoterApplication
from ..utils.web3_utils import get_contract, get_w3
from app import scheduler  # 确保导入 scheduler 实例

admin_bp = Blueprint('admin_routes', __name__, url_prefix='/api/admin')


# --- Admin Auth Decorator ---
def admin_required(fn):
    @wraps(fn)
    @jwt_required()  # 首先确保有有效的JWT
    def wrapper(*args, **kwargs):
        current_user_identity = json.loads(get_jwt_identity())
        user_role = current_user_identity.get('role')
        user_id_from_token = current_user_identity.get('id')

        if user_role != 'admin':
            current_app.logger.warning(
                f"Non-admin user (ID: {user_id_from_token}, "
                f"Role: {user_role}) attempted admin action on {request.path}")
            return jsonify(success=False, message="Administration rights required."), 403

        # 从数据库再次确认角色
        admin_user_db = User.query.get(user_id_from_token)
        if not admin_user_db or admin_user_db.role != 'admin':
            current_app.logger.error(
                f"Admin role mismatch for user ID {user_id_from_token} (Token role: {user_role}, "
                f"DB role: {admin_user_db.role if admin_user_db else 'Not Found'}). "
                f"Potential security issue or outdated token.")
            return jsonify(success=False, message="Admin status verification failed."), 403

        # 将确认后的管理员用户对象传递给路由函数，如果需要的话
        kwargs['current_admin_user'] = admin_user_db
        return fn(*args, **kwargs)

    return wrapper


@admin_bp.route('/add_candidate', methods=['POST'])
@admin_required
def add_new_candidate(current_admin_user):
    try:
        contract = get_contract()
        w3 = get_w3()

        # 从合约获取当前投票阶段
        # getVotingStatus() 返回 (VotingPhase phase, uint startTime, uint endTime, uint currentTime)
        # VotingPhase: 0=Pending, 1=Active, 2=Concluded
        contract_status_data = contract.functions.getVotingStatus().call()
        current_phase_from_contract = contract_status_data[0]  # phase is the first element

        if current_phase_from_contract != 0:  # 0 is VotingPhase.Pending
            pending_phase_name = "Pending"  # 根据你的solidity enum定义
            active_phase_name = "Active"
            concluded_phase_name = "Concluded"

            phase_map = {0: pending_phase_name, 1: active_phase_name, 2: concluded_phase_name}
            current_phase_name = phase_map.get(current_phase_from_contract, "Unknown")

            current_app.logger.warning(
                f"Admin '{current_admin_user.userid}' attempted to add candidate "
                f"while voting phase is '{current_phase_name}' (not Pending).")
            return jsonify({
                "success": False,
                "message": f"Cannot add candidates. Voting phase is currently '{current_phase_name}'. "
                           f"Candidates can only be added during the '{pending_phase_name}' phase."
            }), 400  # Bad Request or 409 Conflict

        data = request.get_json()
        # ... (rest of your existing add_candidate logic)
        if not data or 'name' not in data:
            return jsonify({"success": False, "message": "Candidate name is required."}), 400

        candidate_name = data.get('name')
        description = data.get('description')
        image_url = data.get('image_url')
        slogan = data.get('slogan')

        if not isinstance(candidate_name, str) or not candidate_name.strip():
            return jsonify({"success": False, "message": "Candidate name must be a non-empty string."}), 400

        existing_candidate_db = CandidateDetails.query.filter_by(name=candidate_name).first()
        if existing_candidate_db:
            return jsonify(
                {"success": False,
                 "message": f"Candidate with name '{candidate_name}' already exists in database."}), 409

        tx_sender_account = w3.eth.default_account
        current_app.logger.info(
            f"Attempting to add candidate '{candidate_name}' to blockchain from admin account: {tx_sender_account}")
        tx_hash = contract.functions.addCandidate(candidate_name).transact({'from': tx_sender_account})
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if tx_receipt.status != 1:
            current_app.logger.error(
                f"Blockchain transaction failed for adding candidate '{candidate_name}'. Receipt: {tx_receipt}")
            return jsonify({
                "success": False,
                "message": f"Failed to add candidate '{candidate_name}' to blockchain. Transaction reverted.",
                "txHash": tx_hash.hex()
            }), 500

        new_candidate_db = CandidateDetails(name=candidate_name, description=description, image_url=image_url,
                                            slogan=slogan)
        db.session.add(new_candidate_db)
        db.session.commit()
        current_app.logger.info(
            f"Candidate '{candidate_name}' (ID: {new_candidate_db.id}) added by admin '{current_admin_user.userid}'. "
            f"TX: {tx_hash.hex()}")

        return jsonify({
            "success": True,
            "message": f"Candidate '{candidate_name}' added successfully.",
            "txHash": tx_hash.hex(),
            "db_id": new_candidate_db.id
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in add_new_candidate by admin {current_admin_user.userid}: {str(e)}",
                                 exc_info=True)
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500


@admin_bp.route('/upload_candidate_image', methods=['POST'])
@admin_required
def upload_candidate_image(current_admin_user):
    """上传候选人图片"""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "message": "未找到文件"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "message": "未选择文件"}), 400

        # 安全处理文件名
        filename = secure_filename(file.filename)

        # 使用时间戳确保文件名唯一
        timestamp = int(datetime.now(UTC).timestamp())
        name_parts = os.path.splitext(filename)
        unique_filename = f"{name_parts[0]}_{timestamp}{name_parts[1]}"

        # 确保上传目录存在
        def ensure_upload_dir(directory):
            """确保指定的上传目录存在"""
            if not os.path.exists(directory):
                os.makedirs(directory)
            return directory

        # 获取上传目录路径，确保它存在
        uploads_directory = os.path.join(current_app.root_path, 'uploads')
        candidates_upload_dir = os.path.join(uploads_directory, 'candidates')
        ensure_upload_dir(candidates_upload_dir)

        # 保存文件
        file_path = os.path.join(candidates_upload_dir, unique_filename)
        file.save(file_path)

        # 确定公开访问的URL
        base_url = current_app.config.get('BASE_URL')
        image_url = f"{base_url}/api/admin/uploads/candidates/{unique_filename}"

        current_app.logger.info(
            f"Admin '{current_admin_user.userid}' uploaded candidate image. File saved as: {file_path}")

        return jsonify({
            "success": True,
            "message": "图片上传成功",
            "image_url": image_url,
            "filename": unique_filename
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error in upload_candidate_image by admin {current_admin_user.userid}: {str(e)}",
                                 exc_info=True)
        return jsonify({"success": False, "message": f"上传失败: {str(e)}"}), 500


# 添加一个路由来提供上传的文件访问
@admin_bp.route('/uploads/candidates/<filename>', methods=['GET'])
def get_candidate_image(filename):
    """获取上传的候选人图片"""
    # 直接指向实际存储路径
    uploads_directory = os.path.join(current_app.root_path, 'uploads')
    candidates_upload_dir = os.path.join(uploads_directory, 'candidates')
    return send_from_directory(candidates_upload_dir, filename)


@admin_bp.route('/voter_applications', methods=['GET'])
@admin_required
def get_voter_applications(current_admin_user):
    """管理员获取选民申请列表"""
    # current_admin_user 可用于日志记录或特定权限检查（如果未来有更细粒度的管理员）
    current_app.logger.info(f"Admin '{current_admin_user.userid}' fetching voter applications.")
    try:
        # ... (内部逻辑保持不变) ...
        status_filter = request.args.get('status', 'pending')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        query = VoterApplication.query
        if status_filter and status_filter != 'all':
            query = query.filter(VoterApplication.status == status_filter)

        applications_pagination = query.order_by(VoterApplication.submitted_at.desc()).paginate(page=page,
                                                                                                per_page=per_page,
                                                                                                error_out=False)
        applications_list = [app.to_dict() for app in applications_pagination.items]

        return jsonify({
            "success": True,
            "applications": applications_list,
            "total": applications_pagination.total,
            "pages": applications_pagination.pages,
            "current_page": applications_pagination.page
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching voter applications by admin {current_admin_user.userid}: {str(e)}",
                                 exc_info=True)
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500


@admin_bp.route('/voter_applications/<int:application_id>/review', methods=['PUT'])
@admin_required
def review_voter_application(current_admin_user, application_id):
    """管理员审核选民申请 (批准/拒绝)"""
    current_app.logger.info(f"Admin '{current_admin_user.userid}' reviewing application ID {application_id}.")
    try:
        data = request.get_json()
        # ... (数据验证和基本逻辑保持不变) ...
        if not data or 'status' not in data:
            return jsonify({"success": False, "message": "New status ('approved' or 'rejected') is required."}), 400

        new_status = data.get('status')

        if new_status not in ['approved', 'rejected']:
            return jsonify({"success": False, "message": "Invalid status. Must be 'approved' or 'rejected'."}), 400

        application = VoterApplication.query.get(application_id)
        # ... (application 存在性和状态检查保持不变) ...
        if not application:
            return jsonify({"success": False, "message": f"Voter application with ID {application_id} not found."}), 404

        if application.status != 'pending':
            return jsonify({"success": False,
                            "message": f"Application is already '{application.status}', cannot review again."}), 409

        applicant_user = User.query.get(application.user_id)
        # ... (applicant_user 存在性和 ETH 地址检查保持不变) ...
        if not applicant_user:
            current_app.logger.error(f"User with ID {application.user_id} for application {application_id} not found!")
            return jsonify({"success": False, "message": "Applicant user not found for this application."}), 500

        if not applicant_user.ethereum_address and new_status == 'approved':
            current_app.logger.warning(
                f"User ID {applicant_user.id} (application {application_id}) has no ETH address. Cannot approve.")
            return jsonify({"success": False,
                            "message": "Applicant does not have an Ethereum address. Cannot approve application."}), 400

        application.status = new_status
        application.reviewed_by_admin_id = current_admin_user.id  # 使用当前管理员的 ID
        application.reviewed_at = datetime.now(UTC)  # 确保使用 UTC

        if new_status == 'approved':
            # ... (检查是否已是 Voter 的逻辑保持不变) ...
            existing_voter = Voter.query.filter_by(user_id=applicant_user.id).first()
            if existing_voter:
                current_app.logger.warning(
                    f"User ID {applicant_user.id} is already a voter (ID: {existing_voter.id}) "
                    f"but application {application_id} was approved by {current_admin_user.userid}.")
                db.session.commit()
                return jsonify({
                    "success": True,
                    "message": "Application status updated. User was already a voter.",
                    "application": application.to_dict()
                }), 200

            contract = get_contract()
            w3 = get_w3()
            # 链上注册交易仍由系统的 default_account (管理员账户) 发起
            admin_tx_account = w3.eth.default_account
            if not admin_tx_account:
                # ... (处理 admin_tx_account 未设置的逻辑保持不变) ...
                current_app.logger.error("Admin Ethereum account for sending transactions is not set.")
                db.session.commit()
                return jsonify({"success": False,
                                "message": "Admin Ethereum account not configured for blockchain transactions. "
                                           "Application status updated but voter not registered on chain."}), 500

            current_app.logger.info(
                f"Admin '{current_admin_user.userid}' approving application {application_id}. "
                f"Attempting to register voter ETH address '{applicant_user.ethereum_address}' "
                f"(User ID: {applicant_user.id}) on blockchain by system admin account {admin_tx_account}.")

            try:
                tx_hash = contract.functions.registerVoter(applicant_user.ethereum_address).transact(
                    {'from': admin_tx_account})
                tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

                if tx_receipt.status == 1:
                    new_voter_record = Voter(
                        user_id=applicant_user.id,
                        is_registered_on_chain=True,
                        chain_registration_tx_hash=tx_hash.hex(),
                        registered_on_chain_at=datetime.now(UTC)  # 确保使用 UTC
                    )
                    db.session.add(new_voter_record)
                    # ... (后续成功逻辑保持不变) ...
                    db.session.commit()
                    current_app.logger.info(
                        f"Voter ETH address '{applicant_user.ethereum_address}' "
                        f"successfully registered on blockchain and voter record created (ID: {new_voter_record.id}). "
                        f"TX Hash: {tx_hash.hex()}")
                    return jsonify({
                        "success": True,
                        "message": "Voter application approved. User registered on blockchain "
                                   "and voter record created.",
                        "application": application.to_dict(),
                        "voter_record": new_voter_record.to_dict(),
                        "txHash": tx_hash.hex()
                    }), 200
                else:
                    # ... (链上交易失败逻辑保持不变) ...
                    current_app.logger.error(
                        f"Blockchain transaction failed for registering voter '{applicant_user.ethereum_address}'. "
                        f"Receipt: {tx_receipt}")
                    application.admin_notes = ((application.admin_notes or "") +
                                               f"\n[System Note by {current_admin_user.userid}: "
                                               f"Blockchain registration failed. TX: {tx_hash.hex()}]")
                    db.session.commit()
                    return jsonify({
                        "success": False,
                        "message": "Application approved, but failed to register voter on blockchain. "
                                   "Transaction reverted.",
                        "application_status": "approved",
                        "blockchain_status": "failed",
                        "txHash": tx_hash.hex()
                    }), 500
            except Exception as chain_exc:
                # ... (链上异常处理逻辑保持不变) ...
                current_app.logger.error(
                    f"Exception during blockchain registration for user {applicant_user.id} "
                    f"by admin {current_admin_user.userid}: {str(chain_exc)}",
                    exc_info=True)
                application.admin_notes = ((application.admin_notes or "") +
                                           f"\n[System Note by {current_admin_user.userid}: "
                                           f"Blockchain registration threw exception: {str(chain_exc)}]")
                db.session.commit()
                return jsonify({
                    "success": False,
                    "message": f"Application approved, but an error occurred during blockchain registration: "
                               f"{str(chain_exc)}",
                    "application_status": "approved",
                    "blockchain_status": "exception"
                }), 500
        else:  # new_status == 'rejected'
            # ... (拒绝逻辑保持不变) ...
            db.session.commit()
            current_app.logger.info(
                f"Voter application ID {application_id} for user ID {applicant_user.id} was rejected by "
                f"admin '{current_admin_user.userid}'.")
            return jsonify({
                "success": True,
                "message": "Voter application rejected successfully.",
                "application": application.to_dict()
            }), 200

    except Exception as e:
        # ... (最外层异常处理保持不变) ...
        db.session.rollback()
        current_app.logger.error(
            f"Error reviewing voter application by admin "
            f"{current_admin_user.userid if 'current_admin_user' in locals() else 'Unknown'}: {str(e)}",
            exc_info=True)
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500


# --- Voting Activity Management ---
@admin_bp.route('/voting/period', methods=['POST'])
@admin_required
def set_voting_period(current_admin_user):
    """管理员设置投票周期 (开始和结束时间)
    并且自动安排或更新投票的自动启动任务。
    """
    try:
        data = request.get_json()
        start_time_ts = data.get('start_time_timestamp')  # 期望是 Unix 时间戳 (秒)
        end_time_ts = data.get('end_time_timestamp')  # 期望是 Unix 时间戳 (秒)

        if not all([isinstance(start_time_ts, int), isinstance(end_time_ts, int)]):
            return jsonify({"success": False,
                            "message": "start_time_timestamp and end_time_timestamp are required "
                                       "and must be integers."}), 400

        # 可以在这里添加额外的验证，例如 start_time_ts 是否在 end_time_ts 之前
        # 以及 start_time_ts 是否在当前时间的合理范围内（例如，不是太遥远的过去，虽然合约会检查）
        if start_time_ts >= end_time_ts:
            return jsonify({"success": False, "message": "Start time must be before end time."}), 400

        # 检查开始时间是否至少是当前时间 (或略晚于当前时间，给操作留出余地)
        # 这有助于防止立即设置一个已经过去的自动启动任务
        # 不过，合约的 setVotingPeriod 也有 block.timestamp 检查
        # current_browser_time_approx = int(datetime.now(UTC).timestamp()) # 这只是一个近似值
        # if start_time_ts < current_browser_time_approx - 60: # 允许一分钟的误差
        # return jsonify({"success": False, "message": "Scheduled start time appears to be in the past."}), 400

        contract = get_contract()
        w3 = get_w3()
        tx_sender_account = w3.eth.default_account

        current_app.logger.info(
            f"Admin '{current_admin_user.userid}' attempting to set voting period: Start {start_time_ts}, "
            f"End {end_time_ts}")

        # 1. 在区块链上设置投票周期
        tx_hash = contract.functions.setVotingPeriod(start_time_ts, end_time_ts).transact({'from': tx_sender_account})
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if tx_receipt.status == 1:
            current_app.logger.info(
                f"Voting period set successfully on blockchain by admin '{current_admin_user.userid}'. "
                f"TX: {tx_hash.hex()}")

            # 2. 成功设置链上周期后，安排或更新自动启动任务
            try:
                run_date = datetime.fromtimestamp(start_time_ts, tz=UTC)
                # 使用与投票活动相关的唯一标识符作为 job_id 的一部分会更好，
                # 但如果一个系统只有一个"当前"或"下一个"投票活动，基于时间戳也可以工作。
                # 为简单起见，我们继续使用基于 start_timestamp 的 job_id。
                job_id = f"auto_start_voting_{start_time_ts}"

                # 检查并移除已存在的同名作业（实现更新逻辑）
                if scheduler.get_job(job_id):
                    scheduler.remove_job(job_id)
                    current_app.logger.info(f"Removed existing auto-start job with ID '{job_id}' to reschedule.")

                # 添加新的调度任务
                # job_start_voting_on_contract 函数需要定义在 admin_routes.py 中或可被导入
                scheduler.add_job(
                    id=job_id,
                    func=job_start_voting_on_contract,  # 指向你的作业执行函数
                    trigger='date',
                    run_date=run_date,
                    args=[job_id]  # 或者传递一个更明确的 voting_activity_id
                )
                current_app.logger.info(
                    f"Successfully scheduled/updated auto-start for voting at {run_date} (Job ID: {job_id}).")

                return jsonify({
                    "success": True,
                    "message": "Voting period set successfully on blockchain and auto-start task scheduled/updated.",
                    "txHash": tx_hash.hex(),
                    "auto_start_job_id": job_id,
                    "auto_start_scheduled_at": run_date.isoformat()
                }), 200

            except Exception as schedule_err:
                current_app.logger.error(
                    f"Voting period set on blockchain,"
                    f" but failed to schedule/update auto-start task for start_time {start_time_ts} "
                    f"by admin {current_admin_user.userid}: {str(schedule_err)}",
                    exc_info=True)
                # 即使调度失败，链上周期设置成功了，所以仍然返回成功，但附带警告信息
                return jsonify({
                    "success": True,
                    "message": "Voting period set successfully on blockchain, "
                               "but an error occurred while scheduling the auto-start task. Please check server logs.",
                    "txHash": tx_hash.hex(),
                    "scheduling_error": str(schedule_err)
                }), 200  # 或者返回 207 Multi-Status 表示部分成功
        else:
            current_app.logger.error(
                f"Failed to set voting period on blockchain. TX: {tx_hash.hex()}, Receipt: {tx_receipt}")
            return jsonify({"success": False, "message": "Failed to set voting period on blockchain.",
                            "txHash": tx_hash.hex()}), 500
    except Exception as e:
        current_app.logger.error(f"Error in set_voting_period by admin {current_admin_user.userid}: {str(e)}",
                                 exc_info=True)
        # 检查是否是合约 revert 错误，并尝试提取 revert原因 (如果合约 revert 带有消息)
        if "revert" in str(e).lower():
            # 尝试从异常字符串中提取 revert原因
            reason = str(e)
            # 这里的错误解析可能需要根据实际的 web3.py 版本和异常结构调整
            try:
                # 先检查是否为特定的Web3异常类型
                if isinstance(e, ContractLogicError):
                    # 对于ContractLogicError，错误信息通常在str(e)中
                    error_str = str(e)
                    if "revert" in error_str.lower():
                        reason_details = error_str.split("revert")[-1].strip()
                        if reason_details:
                            reason = reason_details
                # 也可以处理其他可能的Web3异常类型
            except Exception as extract_err:
                current_app.logger.debug(f"Failed to extract revert reason: {extract_err}")
                pass  # 保留原始错误信息
            return jsonify(
                {"success": False,
                 "message": f"Failed to set voting period: Transaction reverted. Reason: {reason}"}), 400

        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500


@admin_bp.route('/voting/start', methods=['POST'])
@admin_required
def start_voting_process(current_admin_user):
    """管理员启动投票"""
    try:
        contract = get_contract()
        w3 = get_w3()
        tx_sender_account = w3.eth.default_account

        current_app.logger.info(f"Admin '{current_admin_user.userid}' attempting to start voting.")
        tx_hash = contract.functions.startVoting().transact({'from': tx_sender_account})
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if tx_receipt.status == 1:
            current_app.logger.info(
                f"Voting started successfully by admin '{current_admin_user.userid}'. TX: {tx_hash.hex()}")
            return jsonify({"success": True, "message": "Voting started successfully.", "txHash": tx_hash.hex()}), 200
        else:
            current_app.logger.error(f"Failed to start voting. TX: {tx_hash.hex()}, Receipt: {tx_receipt}")
            # 可以尝试从合约读取错误原因，如果合约 revert 带有消息
            return jsonify({"success": False,
                            "message": "Failed to start voting on blockchain. "
                                       "Check contract conditions (e.g., period set, enough candidates, time).",
                            "txHash": tx_hash.hex()}), 500
    except Exception as e:
        current_app.logger.error(f"Error starting voting by admin {current_admin_user.userid}: {str(e)}", exc_info=True)
        # 检查是否是合约 revert 错误，并尝试提取 revert原因
        if "revert" in str(e).lower():
            return jsonify(
                {"success": False, "message": f"Failed to start voting: Transaction reverted. {str(e)}"}), 400

        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500


@admin_bp.route('/voting/end', methods=['POST'])
@admin_required
def end_voting_process(current_admin_user):
    """管理员结束投票"""
    try:
        contract = get_contract()
        w3 = get_w3()
        tx_sender_account = w3.eth.default_account

        current_app.logger.info(f"Admin '{current_admin_user.userid}' attempting to end voting.")
        tx_hash = contract.functions.endVoting().transact({'from': tx_sender_account})
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if tx_receipt.status == 1:
            current_app.logger.info(
                f"Voting ended successfully by admin '{current_admin_user.userid}'. TX: {tx_hash.hex()}")
            return jsonify({"success": True, "message": "Voting ended successfully.", "txHash": tx_hash.hex()}), 200
        else:
            current_app.logger.error(f"Failed to end voting. TX: {tx_hash.hex()}, Receipt: {tx_receipt}")
            return jsonify({"success": False, "message": "Failed to end voting on blockchain. Ensure voting is active.",
                            "txHash": tx_hash.hex()}), 500
    except Exception as e:
        current_app.logger.error(f"Error ending voting by admin {current_admin_user.userid}: {str(e)}", exc_info=True)
        if "revert" in str(e).lower():
            return jsonify({"success": False, "message": f"Failed to end voting: Transaction reverted. {str(e)}"}), 400
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500


@admin_bp.route('/voting/extend', methods=['PUT'])  # Changed to PUT
@admin_required
def extend_voting_deadline_route(current_admin_user):  # Renamed function for clarity
    """管理员延长投票截止时间"""
    try:
        data = request.get_json()
        new_end_time_ts = data.get('new_end_time_timestamp')  # 期望是 Unix 时间戳 (秒)

        if not isinstance(new_end_time_ts, int):
            return jsonify(
                {"success": False, "message": "new_end_time_timestamp is required and must be an integer."}), 400

        contract = get_contract()
        w3 = get_w3()
        tx_sender_account = w3.eth.default_account

        current_app.logger.info(f"Admin '{current_admin_user.userid}' extending voting deadline to: {new_end_time_ts}")
        tx_hash = contract.functions.extendVotingDeadline(new_end_time_ts).transact({'from': tx_sender_account})
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if tx_receipt.status == 1:
            current_app.logger.info(
                f"Voting deadline extended successfully by admin '{current_admin_user.userid}'. TX: {tx_hash.hex()}")
            return jsonify(
                {"success": True, "message": "Voting deadline extended successfully.", "txHash": tx_hash.hex()}), 200
        else:
            current_app.logger.error(f"Failed to extend voting deadline. TX: {tx_hash.hex()}, Receipt: {tx_receipt}")
            return jsonify({"success": False,
                            "message": "Failed to extend voting deadline on blockchain. Check contract conditions.",
                            "txHash": tx_hash.hex()}), 500
    except Exception as e:
        current_app.logger.error(f"Error extending voting deadline by admin {current_admin_user.userid}: {str(e)}",
                                 exc_info=True)
        if "revert" in str(e).lower():
            return jsonify(
                {"success": False, "message": f"Failed to extend deadline: Transaction reverted. {str(e)}"}), 400
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500


@admin_bp.route('/voting/contract_status', methods=['GET'])
@admin_required
def get_contract_voting_status(current_admin_user):
    """获取合约的详细状态，供管理员前端页面使用"""
    try:
        contract = get_contract()
        # (phase, startTime, endTime, currentTime)
        status_data = contract.functions.getVotingStatus().call()

        # 新增：获取候选人数量
        candidate_count = contract.functions.getCandidatesCount().call()

        phase_map = {0: "Pending", 1: "Active", 2: "Concluded"}

        return jsonify({
            "success": True,
            "phase": phase_map.get(status_data[0], "Unknown"),
            "phase_code": status_data[0],
            "start_time": status_data[1],
            "end_time": status_data[2],
            "current_block_timestamp": status_data[3],
            "candidates_count": candidate_count  # 新增返回字段
        }), 200
    except Exception as e:
        current_app.logger.error(
            f"Error fetching contract voting status by admin {current_admin_user.userid}: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500


def job_start_voting_on_contract(voting_id_or_job_id):
    with current_app.app_context():
        try:
            current_app.logger.info(
                f"APScheduler: Attempting to auto-start voting via job (ID: {voting_id_or_job_id}).")
            contract = get_contract()
            w3 = get_w3()
            tx_sender_account = w3.eth.default_account

            status_data = contract.functions.getVotingStatus().call()
            current_phase_from_contract = status_data[0]
            contract_start_time = status_data[1]
            contract_end_time = status_data[2]
            current_block_time = status_data[3]

            if current_phase_from_contract == 0:  # VotingPhase.Pending
                current_app.logger.info(
                    f"Contract phase is Pending. Attempting to call startVoting() for job {voting_id_or_job_id}.")
                tx_hash = contract.functions.startVoting().transact({'from': tx_sender_account})
                current_app.logger.info(
                    f"APScheduler: Auto-start voting transaction sent for job {voting_id_or_job_id}. "
                    f"TX Hash: {tx_hash.hex()}")
            else:
                current_app.logger.warning(
                    f"APScheduler: Auto-start voting job {voting_id_or_job_id} skipped. "
                    f"Contract phase is not Pending (Phase: {current_phase_from_contract}). "
                    f"Current block time: {current_block_time}, Contract start: {contract_start_time}, "
                    f"Contract end: {contract_end_time}")

        except Exception as e:
            current_app.logger.error(
                f"APScheduler: Error in job_start_voting_on_contract (Job ID: {voting_id_or_job_id}): {str(e)}",
                exc_info=True)
