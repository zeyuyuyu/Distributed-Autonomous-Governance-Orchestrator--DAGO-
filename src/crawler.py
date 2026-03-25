import asyncio
from web3 import Web3
from aiohttp import ClientSession
from typing import List, Dict, Optional
from datetime import datetime
import logging
from ratelimit import limits, sleep_and_retry

class Web3Crawler:
    def __init__(self, rpc_endpoints: List[str], requests_per_second: int = 5):
        self.rpcs = rpc_endpoints
        self.current_rpc = 0
        self.web3_instances = [Web3(Web3.HTTPProvider(rpc)) for rpc in rpc_endpoints]
        self.requests_per_second = requests_per_second
        self.logger = logging.getLogger(__name__)

    @sleep_and_retry
    @limits(calls=5, period=1)
    async def _make_request(self, method: str, params: List) -> Optional[Dict]:
        w3 = self.web3_instances[self.current_rpc]
        try:
            result = await w3.eth.call_method(method, params)
            return result
        except Exception as e:
            self.logger.error(f'Error making request: {e}')
            # Rotate to next RPC endpoint
            self.current_rpc = (self.current_rpc + 1) % len(self.rpcs)
            return None

    async def scan_contracts(self, start_block: int, end_block: int) -> List[Dict]:
        """Scan blockchain for contract deployments and interactions"""
        contracts = []
        
        for block_num in range(start_block, end_block + 1):
            try:
                block = await self._make_request(
                    'eth_getBlockByNumber',
                    [hex(block_num), True]
                )
                
                if not block:
                    continue

                for tx in block['transactions']:
                    # Look for contract creations
                    if tx['to'] is None and tx['input'] != '0x':
                        contract_addr = Web3.toChecksumAddress(
                            Web3.keccak(rlp.encode([tx['from'], tx['nonce']]))[12:]
                        )
                        
                        contracts.append({
                            'address': contract_addr,
                            'creator': tx['from'],
                            'creation_block': block_num,
                            'creation_tx': tx['hash'],
                            'timestamp': datetime.fromtimestamp(block['timestamp'])
                        })
                        
                        self.logger.info(
                            f'Found contract deployment at {contract_addr}'
                        )

            except Exception as e:
                self.logger.error(
                    f'Error scanning block {block_num}: {str(e)}'
                )
                continue

        return contracts

    async def get_contract_code(self, address: str) -> Optional[str]:
        """Fetch contract bytecode and runtime code"""
        try:
            code = await self._make_request(
                'eth_getCode',
                [Web3.toChecksumAddress(address), 'latest']
            )
            return code
        except Exception as e:
            self.logger.error(f'Error fetching code for {address}: {e}')
            return None

    async def analyze_contract(self, address: str) -> Dict:
        """Analyze contract code and interaction patterns"""
        code = await self.get_contract_code(address)
        if not code or code == '0x':
            return {'error': 'No code at address'}

        # Basic analysis of bytecode
        analysis = {
            'address': address,
            'code_size': len(code) // 2 - 1,  # Convert hex to bytes
            'is_contract': True,
            'features': []
        }

        # Detect common patterns
        if 'delegatecall' in code:
            analysis['features'].append('proxy_capabilities')
        if 'transfer' in code:
            analysis['features'].append('token_capabilities') 

        return analysis

async def main():
    # Example usage
    crawler = Web3Crawler([
        'https://mainnet.infura.io/v3/YOUR-PROJECT-ID',
        'https://eth-mainnet.alchemyapi.io/v2/YOUR-API-KEY'
    ])
    
    contracts = await crawler.scan_contracts(15000000, 15000100)
    for contract in contracts:
        analysis = await crawler.analyze_contract(contract['address'])
        print(f'Contract Analysis: {analysis}')

if __name__ == '__main__':
    asyncio.run(main())