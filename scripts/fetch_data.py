import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.zero_study_research import ZeroStudyResearcher
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        researcher = ZeroStudyResearcher()
        logger.info("Fetching fresh data from Reservoir API...")
        domains_data, last_updated = researcher.get_nft_data(force_refresh=True)
        logger.info(f"Successfully fetched and saved {len(domains_data)} domains")
        logger.info(f"Last updated: {last_updated}")
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        raise

if __name__ == "__main__":
    main()
