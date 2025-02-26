import sqlite3
import pandas as pd
import logging
import json
import os
import requests
import time
from typing import List, Dict, Any, Tuple
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ZeroStudyResearcher:
    def __init__(self):
        self.api_key = os.getenv('RESERVOIR_API_KEY')
        if not self.api_key:
            raise ValueError("RESERVOIR_API_KEY environment variable is not set")

        self.contract_address = '0xC14ea65f0a478C649B7a037bC0aD0a765b49196B'
        self.base_url = "https://api.reservoir.tools"
        self.db_file = "data/reservoir_data.db"

        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)

        # Initialize database
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with schema"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                # Create domains table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS domains (
                        name TEXT PRIMARY KEY,
                        owner TEXT,
                        world TEXT,
                        root_domain TEXT,
                        domain TEXT,
                        is_subdomain BOOLEAN,
                        member_count INTEGER,
                        mint_date TEXT
                    )
                """)
                # Create metadata table for last_updated
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise

    def load_saved_data(self) -> Tuple[List[Dict[str, Any]], datetime]:
        """Load data and timestamp from SQLite database"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                # Convert SQL rows to DataFrame then to dict for consistency
                df = pd.read_sql_query("SELECT * FROM domains", conn)
                domains_data = df.to_dict('records')

                # Get last updated timestamp
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM metadata WHERE key = 'last_updated'")
                result = cursor.fetchone()
                last_updated = datetime.fromisoformat(result[0]) if result else datetime(2000, 1, 1)

                logger.info(f"Loaded {len(domains_data)} domains from database (last updated: {last_updated})")
                return domains_data, last_updated
        except Exception as e:
            logger.error(f"Error loading saved data: {str(e)}")
            return [], datetime(2000, 1, 1)

    def save_data(self, domains_data: List[Dict[str, Any]]) -> None:
        """Save data with timestamp to SQLite database"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                # Convert to DataFrame for easier SQL insertion
                df = pd.DataFrame(domains_data)

                # Clear existing data
                cursor = conn.cursor()
                cursor.execute("DELETE FROM domains")

                # Insert new data
                df.to_sql('domains', conn, if_exists='append', index=False)

                # Update last_updated timestamp
                now = datetime.now().isoformat()
                cursor.execute("""
                    INSERT OR REPLACE INTO metadata (key, value) 
                    VALUES ('last_updated', ?)
                """, (now,))

                conn.commit()
                logger.info(f"Saved {len(domains_data)} domains to database")
        except Exception as e:
            logger.error(f"Error saving data: {str(e)}")
            raise

    def get_nft_data(self, force_refresh: bool = False) -> Tuple[List[Dict[str, Any]], datetime]:
        """Get domain data from NFT metadata using Reservoir API"""
        if not force_refresh:
            saved_data, last_updated = self.load_saved_data()
            if saved_data:
                return saved_data, last_updated

        try:
            url = f"{self.base_url}/tokens/v7"
            headers = {
                "accept": "*/*",
                "x-api-key": self.api_key
            }
            params = {
                "collection": self.contract_address,
                "limit": 2,  # Reduced limit due to strict rate limits
            }

            all_tokens = []
            continuation = None

            # Handle pagination with rate limits
            while True:
                if continuation:
                    params['continuation'] = continuation

                try:
                    logger.info(f"Fetching NFT data from Reservoir API{' with continuation' if continuation else ''}")
                    response = requests.get(url, headers=headers, params=params)

                    # Log response info
                    logger.info(f"API Response Status: {response.status_code}")
                    logger.info(f"API Response Headers: {dict(response.headers)}")

                    # Handle rate limits and errors
                    if response.status_code == 429:
                        logger.warning("Rate limit hit, waiting 60 seconds before retry...")
                        time.sleep(60)
                        continue
                    elif response.status_code == 401:
                        raise ValueError("Invalid Reservoir API key")
                    elif response.status_code != 200:
                        logger.error(f"API Error: {response.text}")
                        raise requests.exceptions.RequestException(
                            f"API returned status code {response.status_code}"
                        )

                    data = response.json()
                    tokens = data.get('tokens', [])

                    if not tokens:
                        break

                    all_tokens.extend(tokens)
                    logger.info(f"Added {len(tokens)} tokens (total: {len(all_tokens)})")

                    continuation = data.get('continuation')
                    if not continuation:
                        break

                    # Wait between requests to respect rate limits (2 requests per second)
                    time.sleep(0.5)  # 500ms delay between requests

                except requests.exceptions.RequestException as e:
                    logger.error(f"Request error: {str(e)}")
                    time.sleep(30)
                    continue

            # Process tokens into domain data
            domains_data = []
            domain_members = {}

            for token in all_tokens:
                try:
                    token_data = token.get('token', {})
                    name = token_data.get('name', '')
                    if not name or not isinstance(name, str) or not name.startswith('0://'):
                        continue

                    owner = token_data.get('owner', 'Unknown')
                    mint_date = token_data.get('mintedAt')

                    domain_parts = name[4:].split('.')
                    if not domain_parts:
                        continue

                    world = domain_parts[0]
                    root_domain = '.'.join(domain_parts[:-1]) if len(domain_parts) > 1 else world
                    domain = domain_parts[-1]

                    # Track members for parent domains
                    if len(domain_parts) > 1:
                        parent = '.'.join(domain_parts[:-1])
                        if parent not in domain_members:
                            domain_members[parent] = set()
                        domain_members[parent].add(name)

                    domains_data.append({
                        'name': name,
                        'owner': owner,
                        'world': world,
                        'root_domain': root_domain,
                        'domain': domain,
                        'is_subdomain': len(domain_parts) > 1,
                        'member_count': 0,  # Updated after all domains are processed
                        'mint_date': mint_date
                    })

                except Exception as e:
                    logger.error(f"Error processing token: {str(e)}")
                    continue

            # Update member counts
            for domain in domains_data:
                domain_name = domain['name'][4:]
                member_count = len(domain_members.get(domain_name, set()))
                domain['member_count'] = member_count

            logger.info(f"Processed {len(domains_data)} domains")

            # Save to database
            self.save_data(domains_data)
            return domains_data, datetime.now()

        except Exception as e:
            logger.error(f"Error fetching NFT data: {str(e)}")
            return [], datetime.now()

    def format_output(self, domain_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format domain data for better readability"""
        try:
            return {
                'name': domain_data['name'],
                'owner': domain_data['owner'],
                'world': domain_data['world'],
                'root_domain': domain_data['root_domain'],
                'domain': domain_data['domain'],
                'is_subdomain': domain_data['is_subdomain'],
                'member_count': domain_data['member_count'],
                'mint_date': domain_data.get('mint_date')
            }
        except KeyError as e:
            logger.error(f"Missing key in domain data: {e}")
            return {
                'name': domain_data.get('name', 'Unknown'),
                'owner': domain_data.get('owner', 'Unknown'),
                'world': domain_data.get('world', 'Unknown'),
                'root_domain': domain_data.get('root_domain', 'Unknown'),
                'domain': domain_data.get('domain', 'Unknown'),
                'is_subdomain': False,
                'member_count': 0,
                'mint_date': None
            }

def main():
    try:
        researcher = ZeroStudyResearcher()

        # Get and format domain data
        logger.info("Getting domain data...")
        domains_data, last_updated = researcher.get_nft_data() #modified to get last updated time
        formatted_data = [researcher.format_output(data) for data in domains_data]

        # Output results
        print("\nDomains Data:")
        print(json.dumps(formatted_data, indent=2))
        print(f"\nLast Updated: {last_updated}") #Display last updated time

    except Exception as e:
        logger.error(f"Research failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()