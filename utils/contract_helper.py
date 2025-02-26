from web3 import Web3
import os
import logging

logger = logging.getLogger(__name__)

class ContractHelper:
    def __init__(self):
        # Connect to an Ethereum node (using environment variables)
        self.w3 = Web3(Web3.HTTPProvider(os.getenv('WEB3_PROVIDER_URI', 'http://localhost:8545')))

        # Contract addresses loaded from environment
        self.contracts = {
            'registry': '0x08ECf3f191C745a4dD2A18ec91D8301A54d75E7b',
            'root_registrar': '0x67611d0445f26a635a7D1cb87a3A687B95Ce4a05',
            'sub_registrar': '0x9071cf975E24dB9D619f1DF83B5B3EFA2C4BD09e'
        }

        # Contract ABIs
        self.registry_abi = [
            {"type": "function", "name": "getDomain", "inputs": [{"type": "string"}]},
            {"type": "function", "name": "getSubdomains", "inputs": [{"type": "string"}]},
            {"type": "function", "name": "owner", "inputs": [{"type": "bytes32"}]},
            {"type": "function", "name": "memberCount", "inputs": [{"type": "string"}], "outputs": [{"type": "uint256"}]}
        ]

        # Initialize contracts
        try:
            self.registry = self.w3.eth.contract(
                address=self.w3.to_checksum_address(self.contracts['registry']),
                abi=self.registry_abi
            )
        except Exception as e:
            logger.error(f"Failed to initialize contracts: {str(e)}")
            raise

    def get_domains_data(self):
        """
        Fetch domain data from smart contract with proper error handling
        """
        try:
            domains = self.registry.functions.getAllDomains().call()
            domain_data = []

            for domain in domains:
                try:
                    # Get domain hash
                    domain_hash = Web3.keccak(text=domain)

                    data = {
                        'domain': domain,
                        'owner': self.registry.functions.owner(domain_hash).call(),
                        'members': self.registry.functions.memberCount(domain).call(),
                        'payment_amount': self.w3.from_wei(
                            self.registry.functions.getPaymentAmount(domain).call(), 
                            'ether'
                        ),
                        'payment_type': (
                            'STAKE' 
                            if self.registry.functions.getPaymentType(domain).call() == 1 
                            else 'DIRECT'
                        )
                    }
                    domain_data.append(data)
                    logger.info(f"Successfully fetched data for domain: {domain}")
                except Exception as e:
                    logger.error(f"Error processing domain {domain}: {str(e)}")
                    continue

            return domain_data

        except Exception as e:
            logger.error(f"Error fetching domain data: {str(e)}")
            raise