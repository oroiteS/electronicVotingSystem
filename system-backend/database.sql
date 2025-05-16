-- 创建数据库
CREATE DATABASE IF NOT EXISTS voting CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE voting;

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    userid VARCHAR(100) NOT NULL UNIQUE,             -- 用户登录名，唯一
    password_hash VARCHAR(255) NOT NULL,             -- 哈希后的密码
    role VARCHAR(20) NOT NULL DEFAULT 'user',        -- 角色 ('admin', 'user')
    ethereum_address VARCHAR(42) UNIQUE NULL,        -- 用户的以太坊钱包地址，可以唯一，用户注册时选择
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建候选人详情表
CREATE TABLE IF NOT EXISTS candidate_details (
    id INT AUTO_INCREMENT PRIMARY KEY,     -- 内部主键，自增长
    name VARCHAR(255) NOT NULL UNIQUE,    -- 链上候选人的名字，作为关联键，必须唯一
    description TEXT,                     -- 候选人详细描述
    image_url VARCHAR(255),               -- 候选人图片链接
    slogan VARCHAR(255),                  -- 候选人标语
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP  -- 更新时间
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建选民信息表
CREATE TABLE IF NOT EXISTS voter_applications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,                            -- 申请人ID，外键关联 users.id
    status VARCHAR(50) DEFAULT 'pending',            -- 申请状态 ('pending', 'approved', 'rejected')
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_by_admin_id INT NULL,                   -- 审核管理员ID，外键关联 users.id (role='admin')
    reviewed_at TIMESTAMP NULL,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by_admin_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建选民表
CREATE TABLE IF NOT EXISTS voters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,                     -- 对应的用户ID，外键关联 users.id，一个用户只能是一个选民记录
    
    is_registered_on_chain BOOLEAN DEFAULT FALSE,    -- 是否已在智能合约中成功注册
    chain_registration_tx_hash VARCHAR(66) NULL,     -- 在链上注册选民的交易哈希
    registered_on_chain_at TIMESTAMP NULL,           -- 在链上成功注册的时间

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 记录创建时间 (通常是申请被批准并准备上链的时间)
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建投票记录表
CREATE TABLE IF NOT EXISTS votes (
    id INT AUTO_INCREMENT PRIMARY KEY,         -- 内部主键，自增长

    voter_id INT NOT NULL,                     -- 投票的选民ID (外键，关联 voters.id)
    candidate_id INT NOT NULL,                 -- 被投票的候选人ID (外键，关联 candidate_details.id)
    
    -- 链上投票的交易信息
    transaction_hash VARCHAR(66) UNIQUE NOT NULL, -- 投票交易在区块链上的哈希，必须唯一
    block_number BIGINT,                       -- 投票交易被打包的区块号
    voted_at_on_chain TIMESTAMP NULL,          -- 投票在链上确认的时间 (可以从区块时间戳获取，或后端记录)

    -- 审计信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 记录创建时间 (通常是后端接收到投票请求并准备上链的时间)
    
    -- 外键约束
    FOREIGN KEY (voter_id) REFERENCES voters(id) ON DELETE RESTRICT, 
    FOREIGN KEY (candidate_id) REFERENCES candidate_details(id) ON DELETE RESTRICT,

    -- 确保一个选民只能投一次票 (在当前单一选举的假设下)
    UNIQUE KEY uq_voter_election (voter_id) 
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;