import json
from web3 import Web3
from typing import List, Dict, Any
import asyncio
import logging

class BlockchainCrawler:
    def __init__(self, rpc_url: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.logger = logging.getLogger(__name__)
        self.watched_contracts: Dict[str, Dict] = {}
        self.last_processed_block = self.w3.eth.block_number
    
    async def add_contract_to_watch(self, 
                                   address: str, 
                                   abi_path: str,
                                   events_of_interest: List[str]) -> None:
        """Add a smart contract to monitor for specific events"""
        try:
            with open(abi_path, 'r') as f:
                contract_abi = json.load(f)
            
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(address),
                abi=contract_abi
            )
            
            self.watched_contracts[address] = {
                'contract': contract,
                'events': events_of_interest
            }
            self.logger.info(f'Added contract {address} to watch list')
        except Exception as e:
            self.logger.error(f'Failed to add contract {address}: {str(e)}')
    
    async def process_event(self, event: Dict[str, Any]) -> None:
        """Process a smart contract event"""
        event_name = event['event']
        event_args = dict(event['args'])
        tx_hash = event['transactionHash'].hex()
        
        self.logger.info(f'New event {event_name} detected:')
        self.logger.info(f'Transaction: {tx_hash}')
        self.logger.info(f'Arguments: {event_args}')
        
        # Here you can add custom logic to handle different types of events
        # For example, storing in database, triggering actions, etc.
    
    async def scan_blocks(self, interval: int = 15) -> None:
        """Continuously scan for new blocks and process events"""
        while True:
            try:
                current_block = self.w3.eth.block_number
                
                if current_block > self.last_processed_block:
                    for block_num in range(self.last_processed_block + 1, current_block + 1):
                        for address, contract_data in self.watched_contracts.items():
                            contract = contract_data['contract']
                            events_of_interest = contract_data['events']
                            
                            for event_name in events_of_interest:
                                event_filter = getattr(contract.events, event_name).create_filter(
                                    fromBlock=block_num,
                                    toBlock=block_num
                                )
                                
                                for event in event_filter.get_all_entries():
                                    await self.process_event(event)
                    
                    self.last_processed_block = current_block
                    self.logger.info(f'Processed up to block {current_block}')
                
                await asyncio.sleep(interval)
            
            except Exception as e:
                self.logger.error(f'Error in block scanning: {str(e)}')
                await asyncio.sleep(interval)
    
    async def start_monitoring(self, interval: int = 15) -> None:
        """Start the blockchain monitoring process"""
        self.logger.info('Starting blockchain monitoring...')
        await self.scan_blocks(interval)

# Example usage:
'''
if __name__ == '__main__':
    crawler = BlockchainCrawler('https://mainnet.infura.io/v3/YOUR-PROJECT-ID')
    
    async def main():
        await crawler.add_contract_to_watch(
            '0x123...', # Contract address
            'abi/contract.json',
            ['Transfer', 'Approval'] # Events to monitor
        )
        await crawler.start_monitoring()
    
    asyncio.run(main())
'''
