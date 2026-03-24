import asyncio
from web3 import Web3
from typing import List, Dict, Optional
import logging

class Web3Crawler:
    def __init__(self, rpc_endpoint: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_endpoint))
        self.logger = logging.getLogger(__name__)

    async def crawl_contracts(self,
                            start_block: int,
                            end_block: Optional[int] = None,
                            filters: Optional[Dict] = None) -> List[Dict]:
        """Crawls blockchain for smart contracts matching specified filters

        Args:
            start_block: Starting block number
            end_block: Ending block number (defaults to latest)
            filters: Dict of contract criteria to filter by

        Returns:
            List of matching contract data
        """
        if not end_block:
            end_block = self.w3.eth.block_number

        contracts = []
        
        for block_num in range(start_block, end_block + 1):
            try:
                block = self.w3.eth.get_block(block_num, full_transactions=True)
                
                for tx in block.transactions:
                    # Look for contract creation transactions
                    if tx['to'] is None and tx['input']:
                        contract_data = {
                            'address': self.w3.eth.get_transaction_receipt(tx['hash'])['contractAddress'],
                            'creator': tx['from'],
                            'block': block_num,
                            'timestamp': block.timestamp,
                            'bytecode': tx['input']
                        }

                        if self._matches_filters(contract_data, filters):
                            contracts.append(contract_data)
                            
                            self.logger.info(
                                f"Found matching contract at {contract_data['address']}"
                            )

            except Exception as e:
                self.logger.error(f"Error processing block {block_num}: {str(e)}")
                continue

            # Let other tasks run
            await asyncio.sleep(0)
            
        return contracts

    def _matches_filters(self, contract_data: Dict, filters: Optional[Dict]) -> bool:
        """Check if contract matches all specified filters"""
        if not filters:
            return True

        for key, value in filters.items():
            if key not in contract_data:
                return False
            if contract_data[key] != value:
                return False

        return True

    async def analyze_contract(self, address: str) -> Dict:
        """Analyzes a specific contract address for key metrics"""
        try:
            code = self.w3.eth.get_code(address)
            balance = self.w3.eth.get_balance(address)
            tx_count = self.w3.eth.get_transaction_count(address)

            return {
                'address': address,
                'code_size': len(code),
                'balance': balance,
                'transaction_count': tx_count
            }

        except Exception as e:
            self.logger.error(f"Error analyzing contract {address}: {str(e)}")
            return {}

    async def get_contract_events(self,
                                address: str,
                                from_block: int,
                                to_block: Optional[int] = None) -> List[Dict]:
        """Fetches all events emitted by a contract"""
        try:
            contract = self.w3.eth.contract(address=address)
            events = await contract.events.get_all_entries(
                fromBlock=from_block,
                toBlock=to_block or 'latest'
            )
            return [dict(evt) for evt in events]

        except Exception as e:
            self.logger.error(f"Error getting events for {address}: {str(e)}")
            return []
