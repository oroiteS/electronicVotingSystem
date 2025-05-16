# app/utils/web3_utils.py
from web3 import Web3
import json
import os

w3_instance = None
contract_instance = None
ganache_accounts_list = []


def init_web3(app):
    global w3_instance, contract_instance, ganache_accounts_list

    rpc_url = app.config.get('GANACHE_RPC_URL')
    contract_address = app.config.get('CONTRACT_ADDRESS')

    raw_abi_path = app.config.get('CONTRACT_ABI_PATH')

    # system-backend 目录的路径
    backend_dir = os.path.abspath(os.path.join(app.root_path, '..'))
    # 将 raw_abi_path (它是相对于 config.py 即 backend_dir 的) 解析为绝对路径
    absolute_abi_path = os.path.abspath(os.path.join(backend_dir, raw_abi_path))

    if not rpc_url or not contract_address or not absolute_abi_path:
        raise ValueError("GANACHE_RPC_URL, CONTRACT_ADDRESS, or CONTRACT_ABI_PATH is not configured properly.")

    if not os.path.exists(absolute_abi_path):
        raise FileNotFoundError(
            f"Contract ABI file not found at: {absolute_abi_path}. Check CONTRACT_ABI_PATH in config.py and file "
            f"location.")

    w3_instance = Web3(Web3.HTTPProvider(rpc_url))

    if not w3_instance.is_connected():
        raise ConnectionError(f"Failed to connect to Ganache at {rpc_url}")

    with open(absolute_abi_path, 'r', encoding='utf-8') as f:
        contract_json = json.load(f)
        contract_abi = contract_json['abi']

    # 将字符串地址转换为校验和地址
    checksum_address = Web3.to_checksum_address(contract_address)
    contract_instance = w3_instance.eth.contract(address=checksum_address, abi=contract_abi)

    # 设置一个默认账户，用于发送交易，这里使用 Ganache 的第一个账户作为管理员
    if w3_instance.eth.accounts:
        w3_instance.eth.default_account = w3_instance.eth.accounts[0]
        ganache_accounts_list = w3_instance.eth.accounts
        app.logger.info(f"Default Ethereum account set to: {w3_instance.eth.default_account}")
        app.logger.info(f"Total Ganache accounts available: {len(ganache_accounts_list)}")
    else:
        print("Warning: No Ethereum accounts found in Ganache provider.")


def get_w3():
    if not w3_instance:
        raise RuntimeError("Web3 not initialized. Call init_web3 first within app context.")
    return w3_instance


def get_contract():
    if not contract_instance:
        raise RuntimeError("Contract not initialized. Call init_web3 first within app context.")
    return contract_instance


def get_ganache_accounts():
    """获取初始化时从 Ganache 获取的账户列表"""
    return ganache_accounts_list
