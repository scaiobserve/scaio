import os
import logging
from openai import OpenAI
from openai import OpenAIError

# Configure logger
logger = logging.getLogger(__name__)

class ContentAnalyzer:
    def __init__(self, api_key: str = None):
        """Initialize the OpenAI client with an API key."""
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        self.client = OpenAI(api_key=self.api_key)

    def analyze_bill(self, bill_title: str, bill_sponsor: str, bill_status: str, bill_summary: str) -> dict:
        """
        Send the bill information to the LLM to get an analysis.
        Returns a dict containing the summary bullets, impact score, and explanatory paragraph.
        """
        logger.info(f"Analyzing bill via LLM: '{bill_title}'")

        system_prompt = (
            "You are an expert South Carolina policy analyst. Analyze this legislation based on the provided details.\n"
            "Provide your response exactly in the following format:\n\n"
            "EXECUTIVE_SUMMARY:\n"
            "- [Bullet 1]\n"
            "- [Bullet 2]\n"
            "- [Bullet 3]\n\n"
            "IMPACT_SCORE: [A number from 1 to 10]\n\n"
            "IMPACT_EXPLANATION:\n"
            "[A short, 3-sentence paragraph explaining the specific impact this bill would have on SC local governments, manufacturers, or the regional tech economy.]"
        )

        user_prompt = (
            f"Bill Title: {bill_title}\n"
            f"Sponsor: {bill_sponsor}\n"
            f"Status: {bill_status}\n"
            f"Summary Text: {bill_summary}\n"
            "Please provide the analysis."
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o", # Changed from gpt-4 to gpt-4o for better availability
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=600
            )

            # Extract output text
            output_text = response.choices[0].message.content.strip()

            # Parse the response (naive parsing based on the strict prompt format)
            return self._parse_llm_response(output_text)

        except OpenAIError as e:
            logger.error(f"OpenAI API Error during bill analysis: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error formatting LLM output: {e}")
            return None

    def _parse_llm_response(self, text: str) -> dict:
        """
        Parse the formatted string returned by the LLM into a dictionary.
        """
        result = {
            "executive_summary": "",
            "impact_score": "N/A",
            "impact_explanation": ""
        }

        try:
            # Splitting by expected sections
            if "EXECUTIVE_SUMMARY:" in text and "IMPACT_SCORE:" in text:
                parts = text.split("IMPACT_SCORE:")
                exec_summary_part = parts[0].replace("EXECUTIVE_SUMMARY:", "").strip()
                result["executive_summary"] = exec_summary_part

                if "IMPACT_EXPLANATION:" in parts[1]:
                    score_parts = parts[1].split("IMPACT_EXPLANATION:")
                    result["impact_score"] = score_parts[0].strip()
                    result["impact_explanation"] = score_parts[1].strip()
                else:
                    result["impact_score"] = parts[1].strip()
            else:
                # If the LLM failed to follow the format exactly, just dump it in the explanation
                result["impact_explanation"] = text
                
        except Exception as e:
            logger.warning(f"Failed to cleanly parse LLM output: {e}")
            result["impact_explanation"] = text

        return result
