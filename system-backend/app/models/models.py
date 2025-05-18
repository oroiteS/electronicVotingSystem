# app/models/models.py

from datetime import datetime, UTC

from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash, check_password_hash

from app import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    userid = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # 'admin' or 'user'
    ethereum_address = db.Column(db.String(42), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # 密码处理
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.userid} ({self.role})>'

    def to_dict(self, include_eth_address=True, include_voter_status=True, include_has_voted_status=True):  # 添加新参数
        data = {
            'id': self.id,
            'userid': self.userid,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_eth_address:
            data['ethereum_address'] = self.ethereum_address

        if include_voter_status:
            data['is_voter'] = False  # 默认值
            data['voter_is_registered_on_chain'] = False  # 默认值
            has_voted_in_db = False  # 用户投票状态的默认值 (基于数据库)

            if self.voter_record:  # self.voter_record 是 Voter 与 User 的反向引用
                data['is_voter'] = True
                data['voter_is_registered_on_chain'] = self.voter_record.is_registered_on_chain

                # 检查数据库中该选民是否有投票记录
                if include_has_voted_status:  # 仅当请求时才检查
                    vote_cast_by_user = Votes.query.filter_by(voter_id=self.voter_record.id).first()
                    if vote_cast_by_user:
                        has_voted_in_db = True

            if include_has_voted_status:
                # 添加用户是否已投票的状态 (基于数据库)
                data['has_voted'] = has_voted_in_db

            # voter_application_status 的逻辑保持不变
            latest_pending_or_approved_app = VoterApplication.query.filter_by(user_id=self.id) \
                .filter(VoterApplication.status.in_(['pending', 'approved'])) \
                .order_by(VoterApplication.submitted_at.desc()).first()

            if latest_pending_or_approved_app:
                data['voter_application_status'] = latest_pending_or_approved_app.status
                data['voter_application_id'] = latest_pending_or_approved_app.id
            else:
                latest_rejected_app = VoterApplication.query.filter_by(user_id=self.id) \
                    .filter_by(status='rejected') \
                    .order_by(VoterApplication.submitted_at.desc()).first()
                if latest_rejected_app:
                    data['voter_application_status'] = 'rejected'  # type:ignore
                    data['voter_application_id'] = latest_rejected_app.id
                else:
                    data['voter_application_status'] = None

        return data


class CandidateDetails(db.Model):
    __tablename__ = 'candidate_details'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    slogan = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    votes_received = db.relationship('Votes', backref='candidate_detail', lazy='dynamic')

    def __repr__(self):
        return f'<CandidateDetail {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'image_url': self.image_url,
            'slogan': self.slogan,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class VoterApplication(db.Model):
    __tablename__ = 'voter_applications'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(50), default='pending')  # 'pending', 'approved', 'rejected'
    submitted_at = db.Column(db.DateTime, default=func.current_timestamp())
    reviewed_by_admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('applications', lazy='dynamic'))
    reviewed_by_admin = db.relationship('User', foreign_keys=[reviewed_by_admin_id])

    def __repr__(self):
        return f'<VoterApplication ID: {self.id}, UserID: {self.user_id}, Status: {self.status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_userid': self.user.userid if self.user else None,  # 添加申请者用户名
            'user_ethereum_address': self.user.ethereum_address if self.user else None,  # 添加申请者ETH地址
            'status': self.status,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'reviewed_by_admin_id': self.reviewed_by_admin_id,
            'reviewed_by_admin_userid': self.reviewed_by_admin.userid if self.reviewed_by_admin else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
        }


class Voter(db.Model):
    __tablename__ = 'voters'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)

    is_registered_on_chain = db.Column(db.Boolean, default=False, nullable=False)
    chain_registration_tx_hash = db.Column(db.String(66), nullable=True)
    registered_on_chain_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=func.current_timestamp(), nullable=False)
    updated_at = db.Column(db.DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp(),
                           nullable=False)

    user = db.relationship('User',
                           backref=db.backref('voter_record', uselist=False, lazy='joined'))  # uselist=False 因为是一对一
    votes_cast = db.relationship('Votes', backref='voter_profile', lazy='dynamic')

    def __repr__(self):
        if self.user:
            return f'<Voter for User: {self.user.userid}>'
        return f'<Voter ID: {self.id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'userid': self.user.userid if self.user else None,
            'ethereum_address': self.user.ethereum_address if self.user else None,
            'is_registered_on_chain': self.is_registered_on_chain,
            'chain_registration_tx_hash': self.chain_registration_tx_hash,
            'registered_on_chain_at': self.registered_on_chain_at.isoformat() if self.registered_on_chain_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Votes(db.Model):
    __tablename__ = 'votes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    voter_id = db.Column(db.Integer, db.ForeignKey('voters.id'), nullable=False)  # 指向 voters 表的 id
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate_details.id'), nullable=False)
    transaction_hash = db.Column(db.String(66), unique=True, nullable=False)
    block_number = db.Column(db.BigInteger)
    voted_at_on_chain = db.Column(db.TIMESTAMP, nullable=True)  # SQLAlchemy 的 DateTime 类型通常映射到 TIMESTAMP
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))  # 使用 SQLAlchemy 的 DateTime

    def __repr__(self):
        return f'<Vote {self.id} - VoterRecordID {self.voter_id} for CandidateID {self.candidate_id}>'

    def to_dict(self):
        return {
            "id": self.id,
            "voter_id": self.voter_id,  # 这是 voters 表的 id
            "user_id": self.voter_profile.user_id if self.voter_profile else None,  # 从关联的 voter_profile 获取 user_id
            "userid": self.voter_profile.user.userid if self.voter_profile and self.voter_profile.user else None,
            "voter_ethereum_address":
                self.voter_profile.user.ethereum_address if self.voter_profile and self.voter_profile.user else None,
            "candidate_id": self.candidate_id,
            "candidate_name": self.candidate_detail.name if self.candidate_detail else None,
            "transaction_hash": self.transaction_hash,
            "block_number": self.block_number,
            "voted_at_on_chain": self.voted_at_on_chain.isoformat() if self.voted_at_on_chain else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
