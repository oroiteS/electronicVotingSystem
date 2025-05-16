# app/routes/vote_routes.py
import json
import web3.exceptions
from flask import Blueprint, jsonify, current_app, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, UTC  # 用于时间戳

from .. import db  # 导入数据库实例
from ..models.models import CandidateDetails, Voter, Votes, User  # 导入模型
from ..utils.web3_utils import get_contract, get_w3

vote_bp = Blueprint('vote_bp', __name__, url_prefix='/api')


@vote_bp.route('/candidates', methods=['GET'])
def get_all_candidates():
    """获取所有的候选人信息 (从合约和数据库)"""
    try:
        contract = get_contract()
        candidates_list = []

        # 1. 从智能合约获取候选人数量
        candidate_count_on_chain = contract.functions.getCandidatesCount().call()

        current_app.logger.info(f"Found {candidate_count_on_chain} candidates on the smart contract.")

        # 2. 遍历从合约获取每个候选人的链上信息
        for i in range(candidate_count_on_chain):
            # getCandidate 返回 (string memory name, uint voteCount)
            name_on_chain, vote_count_on_chain = contract.functions.getCandidate(i).call()

            # 3. 从数据库中查找对应的候选人详细信息
            candidate_detail_db = CandidateDetails.query.filter_by(name=name_on_chain).first()

            candidate_info = {
                "id_on_chain": i,  # 候选人在合约数组中的索引
                "name": name_on_chain,
                "vote_count_from_chain": vote_count_on_chain,  # 来自合约的票数
                "description": candidate_detail_db.description if candidate_detail_db else None,
                "image_url": candidate_detail_db.image_url if candidate_detail_db else None,
                "slogan": candidate_detail_db.slogan if candidate_detail_db else None,
                "id": candidate_detail_db.id if candidate_detail_db else None,  # 数据库中的 ID
                # 保留 to_dict() 中的其他字段，如果前端需要它们
                "created_at": candidate_detail_db.created_at.isoformat()
                if candidate_detail_db and candidate_detail_db.created_at else None,
                "updated_at": candidate_detail_db.updated_at.isoformat()
                if candidate_detail_db and candidate_detail_db.updated_at else None,
            }

            if not candidate_detail_db:
                current_app.logger.warning(
                    f"Candidate '{name_on_chain}' (Chain Index: {i}) "
                    f"found on chain but not in local database CandidateDetails."
                )

            candidates_list.append(candidate_info)

        return jsonify({"success": True, "candidates": candidates_list}), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching all candidates: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": f"An error occurred while fetching candidates: {str(e)}"}), 500


@vote_bp.route('/voting_status', methods=['GET'])
def get_voting_status_route():
    """获取公共投票状态信息 (与新版合约对齐)"""
    try:
        contract = get_contract()

        # 调用新合约的 getVotingStatus()
        # 返回: (VotingPhase phase, uint startTime, uint endTime, uint currentTimeFromContract)
        status_data = contract.functions.getVotingStatus().call()

        phase_code = status_data[0]
        start_time_ts = status_data[1]
        end_time_ts = status_data[2]
        # current_block_ts_from_contract = status_data[3] # 合约返回的当前区块时间戳

        # 为了与旧前端或简单逻辑兼容，我们可以派生 isStarted 和 isEnded
        # VotingPhase: 0=Pending, 1=Active, 2=Concluded
        is_started = False
        is_ended = False
        phase_string = "Unknown"

        if phase_code == 0:  # Pending
            phase_string = "Pending"
            # is_started is false
            # is_ended is false (unless an end_time was set and passed, but phase should be Concluded then)
        elif phase_code == 1:  # Active
            phase_string = "Active"
            is_started = True
            is_ended = False  # If phase is Active, it cannot be ended yet by definition of the phase
        elif phase_code == 2:  # Concluded
            phase_string = "Concluded"
            is_started = True  # It must have started to be concluded
            is_ended = True

        # 如果需要，也可以使用服务器的当前时间进行一些辅助判断，
        # 但主要还是依赖合约的 phase
        # current_server_timestamp = int(datetime.now(timezone.utc).timestamp())

        return jsonify({
            "success": True,
            "phase": phase_string,  # "Pending", "Active", "Concluded"
            "phase_code": phase_code,  # 0, 1, 2
            "isStarted": is_started,  # 派生出的状态，方便前端简单使用
            "isEnded": is_ended,  # 派生出的状态
            "startTime": start_time_ts,  # 合约中设置的开始时间戳 (秒)
            "endTime": end_time_ts,  # 合约中设置的结束时间戳 (秒)
            # "votingDeadlineTimestamp": end_time_ts, # 为了兼容旧前端可能使用的字段名
            # "currentTimeOnContract": current_block_ts_from_contract # 可以选择是否暴露这个
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching voting status from new contract: {e}", exc_info=True)
        # 返回一个默认的"安全"状态或错误
        return jsonify({
            "success": False,
            "message": f"Error retrieving voting status: {str(e)}",
            "phase": "Error",
            "phase_code": -1,
            "isStarted": False,
            "isEnded": True,  # 发生错误时，通常假设投票不可用
            "startTime": 0,
            "endTime": 0
        }), 500


@vote_bp.route('/election_deadline', methods=['GET'])
def get_election_deadline():
    """获取合约的 votingDeadline"""
    try:
        contract = get_contract()
        deadline_timestamp = contract.functions.votingDeadline().call()
        return jsonify({"success": True, "votingDeadlineTimestamp": deadline_timestamp}), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching election deadline: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500


@vote_bp.route('/vote', methods=['POST'])
@jwt_required()  # <--- 需要登录才能投票
def cast_vote():
    """选民投票"""
    try:
        data = request.get_json()
    except Exception as e:
        current_app.logger.error(f"Error parsing JSON: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Invalid JSON data."}), 400
    try:
        current_user_identity_str = get_jwt_identity()
        current_user_identity = json.loads(current_user_identity_str)
        user_db_id = current_user_identity.get('id')
        if not data or 'candidate_index_on_chain' not in data:
            return jsonify(
                {"success": False, "message": "Candidate index (candidate_index_on_chain) is required."}), 400
        candidate_index = data.get('candidate_index_on_chain')  # 这是用户投票的候选人索引

        # 1. 从数据库获取 User 和关联的 Voter 记录
        user = User.query.get(user_db_id)
        if not user:
            return jsonify({"success": False, "message": "Authenticated user not found."}), 404

        if not user.ethereum_address:  # 投票者必须有以太坊地址
            return jsonify({"success": False, "message": "User does not have an Ethereum address for voting."}), 403

        voter_record = Voter.query.filter_by(user_id=user.id).first()
        if not voter_record:
            return jsonify({"success": False, "message": "User is not registered as a voter."}), 403
        if not voter_record.is_registered_on_chain:
            return jsonify({"success": False, "message": "Voter is not registered on the blockchain."}), 403

        voter_eth_address = user.ethereum_address  # 使用当前登录用户的以太坊地址

        # 2. 检查数据库中该选民是否已投票
        existing_vote_db = Votes.query.filter_by(voter_id=voter_record.id).first()
        if existing_vote_db:
            current_app.logger.warning(
                f"Voter (User ID {user.id}, Voter Record ID {voter_record.id}) already has "
                f"vote ID {existing_vote_db.id} in DB. Contract should prevent re-vote unless revoked.")
            return jsonify({"success": False, "message": "Voter has already voted (according to DB)."}), 409

        contract = get_contract()
        w3 = get_w3()

        # 3. 调用智能合约的 vote 函数
        current_app.logger.info(
            f"User '{user.userid}' (ETH: {voter_eth_address}, VoterRecordID: {voter_record.id}) "
            f"attempting to vote for candidate index {candidate_index}.")

        # 确保 candidate_index 是整数类型，因为前端可能传来字符串
        try:
            candidate_index_int = int(candidate_index)
        except ValueError:
            return jsonify({"success": False, "message": "Invalid candidate_index_on_chain format."}), 400

        tx_hash = contract.functions.vote(candidate_index_int).transact({'from': voter_eth_address, 'gas': 500000})
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if tx_receipt.status != 1:
            current_app.logger.error(
                f"Blockchain transaction failed for voting. Voter ETH: {voter_eth_address}, "
                f"Candidate Index: {candidate_index_int}. Receipt: {tx_receipt}")
            # 尝试从合约 revert 原因中获取更具体的信息 (如果 web3.py 版本支持且合约返回了原因)
            # 注意：这部分的错误提取可能需要根据实际合约和 web3 版本进行调整
            error_message = "Failed to cast vote on blockchain. Transaction reverted."
            # if 'message' in tx_receipt: # 这通常不直接在 receipt 中，而是通过捕获异常
            #     error_message += f" Reason: {tx_receipt['message']}"
            return jsonify({"success": False, "message": error_message,
                            "txHash": tx_hash.hex()}), 500

        current_app.logger.info(
            f"Vote successfully cast on blockchain by User '{user.userid}' (ETH: {voter_eth_address}). "
            f"TX Hash: {tx_hash.hex()}")

        # 4. 在数据库中记录投票
        # --- CORRECTED PART ---
        # 获取被投票候选人的姓名
        try:
            # 合约的 getCandidate 函数需要一个 uint _candidateId 参数
            # candidate_index_int 是我们刚刚成功投票的候选人索引
            candidate_name_on_chain, _ = contract.functions.getCandidate(candidate_index_int).call()
        except Exception as e_get_candidate:
            current_app.logger.error(
                f"Failed to get candidate name from contract after voting for index {candidate_index_int}. "
                f"User: {user.userid}. Error: {str(e_get_candidate)}")
            # 即使无法获取候选人名字，我们可能仍然想记录投票，但标记候选人信息缺失
            # 或者，如果候选人姓名对你至关重要，则返回错误
            return jsonify(
                {"success": False,
                 "message": f"Vote cast on chain, but failed to retrieve candidate details post-transaction: "
                            f"{str(e_get_candidate)}"}), 500

        # 使用获取到的 candidate_name_on_chain
        voted_candidate_name = candidate_name_on_chain
        # --- END OF CORRECTION ---

        candidate_detail_db = CandidateDetails.query.filter_by(name=voted_candidate_name).first()
        if not candidate_detail_db:
            # ... (处理候选人不在数据库的逻辑保持不变) ...
            current_app.logger.error(
                f"Voted candidate '{voted_candidate_name}' (index {candidate_index_int}) not found in DB details "
                f"for user {user.userid}.")
            # 这是一个潜在的数据不一致问题：候选人在链上存在但在数据库 CandidateDetails 中没有对应记录
            # 你可能需要决定如何处理这种情况。例如，创建一个临时的 CandidateDetails 记录，或返回错误。
            # 为了保持一致性，如果候选人必须在数据库中存在，这里应该返回错误。
            return jsonify({"success": False,
                            "message": f"Data inconsistency: Candidate '{voted_candidate_name}' "
                                       f"(voted on chain) not found in local database details."}), 500

        new_vote_db = Votes(
            voter_id=voter_record.id,  # 使用 Voter 表的 ID
            candidate_id=candidate_detail_db.id,
            transaction_hash=tx_hash.hex(),
            block_number=tx_receipt.blockNumber,
            voted_at_on_chain=datetime.now(UTC)
        )
        db.session.add(new_vote_db)
        db.session.commit()
        current_app.logger.info(
            f"Vote by User '{user.userid}' (VoterRecordID {voter_record.id}) for Candidate '{candidate_detail_db.name}'"
            f"(ID {candidate_detail_db.id}) recorded in database (VoteID: {new_vote_db.id}).")

        return jsonify({
            "success": True,
            "message": "Vote cast successfully on blockchain and recorded in database.",
            "txHash": tx_hash.hex(),
            "blockNumber": tx_receipt.blockNumber,
            "db_vote_id": new_vote_db.id
        }), 201

    except web3.exceptions.ContractLogicError as e_contract_logic:  # 捕获合约 revert
        db.session.rollback()
        user_identity_str = get_jwt_identity()
        user_display_name = 'Unknown'
        if user_identity_str:
            try:
                user_identity_dict = json.loads(user_identity_str)
                user_display_name = user_identity_dict.get('userid', 'Unknown_ID_In_Token')
            except json.JSONDecodeError:
                user_display_name = 'Invalid_Token_Format'

        revert_reason = str(e_contract_logic)
        if "Already voted" in revert_reason:
            error_message_to_user = "You have already voted."
        elif "Voting is not active" in revert_reason:
            error_message_to_user = "Voting is not currently active."
        # 可以添加更多特定 revert 原因的处理
        else:
            error_message_to_user = f"Blockchain transaction failed: {revert_reason}"

        current_app.logger.warning(
            f"ContractLogicError while casting vote for user {user_display_name}. Reason: {revert_reason}. "
            f"Input candidate_index: {data.get('candidate_index_on_chain', 'N/A')}")
        return jsonify({"success": False, "message": error_message_to_user,
                        "details": revert_reason}), 400  # 400 Bad Request or 409 Conflict for already voted

    except Exception as e:  # 通用异常捕获
        db.session.rollback()
        user_identity_str = get_jwt_identity()
        user_display_name = 'Unknown'
        if user_identity_str:
            try:
                user_identity_dict = json.loads(user_identity_str)
                user_display_name = user_identity_dict.get('userid', 'Unknown_ID_In_Token')
            except json.JSONDecodeError:
                user_display_name = 'Invalid_Token_Format'

        current_app.logger.error(
            f"Error casting vote for user {user_display_name}: {str(e)}",
            exc_info=True)
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500


@vote_bp.route('/revoke_vote', methods=['POST'])
@jwt_required()  # <--- 需要登录才能撤销
def revoke_vote():
    """选民撤销投票"""
    try:
        current_user_identity = json.loads(get_jwt_identity())
        user_db_id = current_user_identity.get('id')

        user = User.query.get(user_db_id)
        if not user:
            return jsonify({"success": False, "message": "Authenticated user not found."}), 404

        if not user.ethereum_address:
            return jsonify(
                {"success": False, "message": "User does not have an Ethereum address for revoking vote."}), 403

        voter_record = Voter.query.filter_by(user_id=user.id).first()
        if not voter_record:
            return jsonify({"success": False, "message": "User is not registered as a voter."}), 403
        # is_registered_on_chain 检查由合约处理 (voters[msg.sender].isRegistered)

        voter_eth_address = user.ethereum_address

        # 2. 检查数据库中该选民是否有投票记录
        vote_to_revoke_db = Votes.query.filter_by(voter_id=voter_record.id).first()
        if not vote_to_revoke_db:
            return jsonify({"success": False, "message": "No vote found in database for this voter to revoke."}), 404

        contract = get_contract()
        w3 = get_w3()

        # 3. 调用智能合约的 revokeVote 函数
        current_app.logger.info(
            f"User '{user.userid}' (ETH: {voter_eth_address}, "
            f"VoterRecordID: {voter_record.id}) attempting to revoke vote.")

        tx_hash = contract.functions.revokeVote().transact({'from': voter_eth_address, 'gas': 300000})
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if tx_receipt.status != 1:
            # ... (错误处理保持不变) ...
            current_app.logger.error(
                f"Blockchain transaction failed for revoking vote. Voter ETH: {voter_eth_address}. "
                f"Receipt: {tx_receipt}")
            return jsonify({"success": False, "message": "Failed to revoke vote on blockchain. Transaction reverted.",
                            "txHash": tx_hash.hex()}), 500

        current_app.logger.info(
            f"Vote successfully revoked on blockchain by User '{user.userid}' (ETH: {voter_eth_address}). "
            f"TX Hash: {tx_hash.hex()}")

        # 4. 从数据库中删除该投票记录
        db_vote_id_deleted = vote_to_revoke_db.id
        db.session.delete(vote_to_revoke_db)
        db.session.commit()
        current_app.logger.info(
            f"Vote record (ID: {db_vote_id_deleted}) for User '{user.userid}' "
            f"(VoterRecordID {voter_record.id}) deleted from database.")

        return jsonify({
            "success": True,
            "message": "Vote successfully revoked on blockchain and removed from database.",
            "txHash": tx_hash.hex(),
            "blockNumber": tx_receipt.blockNumber
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Error revoking vote for user {get_jwt_identity().get('userid') if get_jwt_identity() else 'Unknown'}:"
            f" {str(e)}",
            exc_info=True)
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500
