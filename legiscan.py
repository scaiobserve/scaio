import os
import requests
import base64
import json
import logging

# Configure logger
logger = logging.getLogger(__name__)

class LegiScanAPI:
    def __init__(self, api_key: str = None):
        """Initialize the LegiScan API client with an API key."""
        self.api_key = api_key or os.environ.get("LEGISCAN_API_KEY")
        if not self.api_key:
            raise ValueError("LegiScan API key is required. Set LEGISCAN_API_KEY environment variable.")
        self.base_url = "https://api.legiscan.com/"

    def _call_api(self, operation: str, params: dict = None) -> dict:
        """Helper method to construct and make the API request."""
        if params is None:
            params = {}
        
        payload = {"key": self.api_key, "op": operation}
        payload.update(params)

        try:
            response = requests.get(self.base_url, params=payload)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "ERROR":
                logger.error(f"LegiScan API Error: {data.get('alert', {}).get('message', 'Unknown Error')}")
                return None
                
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Request Error fetching from LegiScan: {e}")
            return None
        except ValueError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return None

    def search_legislation(self, state: str, keywords: list, year: int = 1) -> list:
        """
        Search for legislation in a specific state matching a list of keywords.
        Args:
            state (str): State abbreviation (e.g., 'SC', 'US')
            keywords (list): List of strings to search for
            year (int): 1 = current session, 2 = recent sessions, 3 = prior years, 4 = all years
        Returns:
            list: A list of dicts containing combined bill info
        """
        if self.api_key.lower() == "mock":
            if state == "SC":
                logger.info("Using MOCK data for SC legislation search.")
                return [
                    {
                        "bill_id": 9999001,
                        "state": "SC",
                        "bill_number": "H5253",
                        "title": "A BILL REGARDING AI IN EDUCATION, REQUIRING PARENTAL CONSENT AND TEACHER OVERSIGHT",
                        "last_action": "Introduced in House",
                        "last_action_date": "2025-02-10",
                        "text_url": "https://legiscan.com/SC/text/H5253/id/9999001"
                    },
                    {
                        "bill_id": 9999002,
                        "state": "SC",
                        "bill_number": "S0963",
                        "title": "A BILL TO INTRODUCE REGULATIONS FOR HIGH-RISK AI SYSTEMS",
                        "last_action": "Introduced in Senate",
                        "last_action_date": "2026-02-26",
                        "text_url": "https://legiscan.com/SC/text/S0963/id/9999002"
                    },
                    {
                        "bill_id": 9999003,
                        "state": "SC",
                        "bill_number": "H0784",
                        "title": "A BILL TO REGULATE ENERGY AND WATER USAGE OF DATA CENTERS",
                        "last_action": "Passed House",
                        "last_action_date": "2025-03-01",
                        "text_url": "https://legiscan.com/SC/text/H0784/id/9999003"
                    },
                    {
                        "bill_id": 9999004,
                        "state": "SC",
                        "bill_number": "S0443",
                        "title": "A BILL REGARDING HEALTHCARE COVERAGE DECISIONS MADE USING AI",
                        "last_action": "In Committee",
                        "last_action_date": "2025-03-11",
                        "text_url": "https://legiscan.com/SC/text/S0443/id/9999004"
                    },
                    {
                        "bill_id": 9999005,
                        "state": "SC",
                        "bill_number": "H4657",
                        "title": "THE 'RIGHT TO COMPUTE' ACT",
                        "last_action": "Read second time",
                        "last_action_date": "2025-04-05",
                        "text_url": "https://legiscan.com/SC/text/H4657/id/9999005"
                    },
                    {
                        "bill_id": 9999006,
                        "state": "SC",
                        "bill_number": "S5085",
                        "title": "A RESOLUTION TO DECLARE 'AI WEEK'",
                        "last_action": "Adopted",
                        "last_action_date": "2026-03-30",
                        "text_url": "https://legiscan.com/SC/text/S5085/id/9999006"
                    }
                ]
            return []

        all_results = {}
        
        for keyword in keywords:
            logger.info(f"Searching LegiScan for '{keyword}' in {state}...")
            
            # LegiScan uses a solr query string
            # Example query: state:SC AND (artificial intelligence)
            query = f'state:{state} AND "{keyword}"'
            
            params = {
                "state": state,
                "query": query,
                "year": year
            }
            
            data = self._call_api("getSearch", params)
            if not data or "searchresult" not in data:
                continue

            results = data["searchresult"]
            
            # The API returns a 'summary' key and numbered keys for the results
            for key, item in results.items():
                if key == "summary":
                    continue
                
                bill_id = item.get("bill_id")
                
                # Check if we already found this bill (deduplication)
                if bill_id and bill_id not in all_results:
                    all_results[bill_id] = {
                        "bill_id": bill_id,
                        "state": item.get("state"),
                        "bill_number": item.get("bill_number"),
                        "title": item.get("title"),
                        "last_action": item.get("last_action"),
                        "last_action_date": item.get("last_action_date"),
                        "text_url": item.get("text_url")
                    }
                    
        return list(all_results.values())

    def get_bill_text(self, bill_id: int) -> dict:
        """
        Fetch the details of a specific bill, including sponsors and full text if available.
        LegiScan returns the bill text in base64 format inside the 'text' node.
        """
        logger.info(f"Fetching details for LegiScan Bill ID: {bill_id}")
        data = self._call_api("getBillText", {"id": bill_id})
        
        if not data or "text" not in data:
            return None
            
        text_info = data["text"]
        doc = text_info.get("doc", "")
        
        try:
            # Decode the base64 encoded text
            decoded_bytes = base64.b64decode(doc)
            # Try to decode as utf-8, ignore errors if it's a PDF/Word doc
            # This is a naive attempt; LegiScan may return PDFs. 
            # In a production app, we'd need more robust parsing based on mime_type
            decoded_text = decoded_bytes.decode("utf-8", errors="ignore")
            
            return {
                "date": text_info.get("date"),
                "mime_type": text_info.get("mime"),
                "text": decoded_text
            }
        except Exception as e:
            logger.error(f"Error decoding bill text for {bill_id}: {e}")
            return None
            
    def get_bill(self, bill_id: int) -> dict:
        """
        Fetch the full bill object from LegiScan.
        """
        if self.api_key.lower() == "mock":
            logger.info(f"Using MOCK data for get_bill ID: {bill_id}")
            mock_db = {
                9999001: {
                    "description": "Proposed legislation aims to establish safeguards for AI use in schools, requiring parental consent and outlining teacher oversight. It also encourages teaching AI tools' safe use and critical evaluation.",
                    "sponsors": [{"name": "Mock Education Committee", "party": "B", "sponsor_type_id": 1}]
                },
                9999002: {
                    "description": "Aims to introduce regulations for high-risk AI systems, mandating transparency, risk management, and impact assessments.",
                    "sponsors": [{"name": "Mock Tech Committee", "party": "B", "sponsor_type_id": 1}]
                },
                9999003: {
                    "description": "Addresses the energy and water usage of data centers (crucial for AI development), requiring 15-year contracts and reporting on resource consumption.",
                    "sponsors": [{"name": "Mock Infrastructure Committee", "party": "B", "sponsor_type_id": 1}]
                },
                9999004: {
                    "description": "Requires licensed physician supervision for health coverage decisions made using AI or automated tools.",
                    "sponsors": [{"name": "Mock Health Committee", "party": "B", "sponsor_type_id": 1}]
                },
                9999005: {
                    "description": "Focuses on protecting the right to own and use computational resources, aiming to prevent restrictive government action.",
                    "sponsors": [{"name": "Mock Commerce Committee", "party": "B", "sponsor_type_id": 1}]
                },
                9999006: {
                    "description": "A resolution declared March 30–April 2, 2026, as 'AI Week' to encourage public education on AI technologies.",
                    "sponsors": [{"name": "Mock Public Affairs Committee", "party": "B", "sponsor_type_id": 1}]
                }
            }
            
            bill_data = mock_db.get(bill_id, {"description": "Mock Bill Description", "sponsors": []})
            bill_data["bill_id"] = bill_id
            return bill_data

        logger.info(f"Fetching full bill object for LegiScan Bill ID: {bill_id}")
        data = self._call_api("getBill", {"id": bill_id})
        
        if not data or "bill" not in data:
            return None
            
        return data["bill"]
