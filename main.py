import os
import json
import logging
from dotenv import load_dotenv

from legiscan import LegiScanAPI
from analyzer import ContentAnalyzer
from generator import MarkdownGenerator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Keywords to track
KEYWORDS = [
    "artificial intelligence",
    "machine learning",
    "algorithm",
    "biometric",
    "data privacy",
    "autonomous"
]

# States/Entities to search (SC = South Carolina, US = Congress)
STATES_TO_SEARCH = ["SC", "US"]

# File to store processed bills to avoid redundant API calls
CACHE_FILE = "processed_bills.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

def main():
    logger.info("Starting Legislative Watchdog Engine Run...")

    # Ensure API keys are present
    if not os.environ.get("LEGISCAN_API_KEY"):
        logger.error("LEGISCAN_API_KEY missing from environment.")
        return
        
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY missing from environment.")
        return

    try:
        legiscan_client = LegiScanAPI()
        analyzer = ContentAnalyzer()
        generator = MarkdownGenerator(output_dir="drafts")
    except ValueError as e:
        logger.error(f"Initialization error: {e}")
        return

    all_bills = []

    # 1. DATA INGESTION
    for state in STATES_TO_SEARCH:
        logger.info(f"--- Querying LegiScan for state: {state} ---")
        bills = legiscan_client.search_legislation(state=state, keywords=KEYWORDS, year=1) # year 1 = current session
        logger.info(f"Found {len(bills)} deduplicated bills matching keywords in {state}.")
        all_bills.extend(bills)

    if not all_bills:
        logger.info("No new bills found matching the keywords. Exiting.")
        return

    logger.info(f"Total bills to process across all jurisdictions: {len(all_bills)}")

    # 2. LLM ANALYSIS & 3. OUTPUT GENERATION
    processed_cache = load_cache()
    new_drafts_count = 0

    for idx, bill in enumerate(all_bills):
        bill_id = str(bill.get("bill_id"))
        last_action_date = bill.get("last_action_date")
        
        # Check cache: Only process if bill is new or its status/action changed
        if bill_id in processed_cache and processed_cache[bill_id] == last_action_date:
            logger.info(f"Skipping Bill {bill.get('bill_number')} (Already processed for action date {last_action_date}).")
            continue

        logger.info(f"Processing Bill {idx+1}/{len(all_bills)}: {bill.get('bill_number')} - {bill.get('title')[:30]}...")
        
        # Get extra details (Sponsor(s) and full text) from LegiScan
        full_bill = legiscan_client.get_bill(bill_id)
        
        sponsor_name = "Unknown Sponsor"
        bill_summary_text = "No additional summary provided."
        
        if full_bill:
            # Try to grab the primary sponsor
            sponsors = full_bill.get("sponsors", [])
            if sponsors:
                primary_sponsor = next((s for s in sponsors if s.get("sponsor_type_id") == 1), sponsors[0])
                sponsor_name = primary_sponsor.get("name", "Unknown Sponsor")
                
            # Grab description as summary
            bill_summary_text = full_bill.get("description", bill_summary_text)

        # We can also attempt to read full bill text if description is insufficient, 
        # but LegiScan `description` is usually decent for this summary level.
        
        # Perform LLM analysis
        analysis = analyzer.analyze_bill(
            bill_title=bill.get("title"),
            bill_sponsor=sponsor_name,
            bill_status=bill.get("last_action", "Unknown"),
            bill_summary=bill_summary_text
        )
        
        if not analysis:
            logger.warning(f"Failed to analyze bill {bill.get('bill_number')}. Skipping output generation.")
            continue
            
        # Generate Markdown draft
        output_path = generator.generate_draft(bill_info=bill, analysis=analysis)
        
        if output_path:
            # Update cache on success
            processed_cache[bill_id] = last_action_date
            save_cache(processed_cache)
            new_drafts_count += 1

    logger.info(f"Legislative Watchdog Engine Run Completed successfully. Drafted {new_drafts_count} new updates.")

if __name__ == "__main__":
    main()
