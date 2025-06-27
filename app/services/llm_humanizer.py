# app/services/llm_humanizer.py

import os
import json
import logging
from typing import Dict, Any
from openai import OpenAIError, OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(OpenAIError)
)
def _call_story_llm(prompt: str) -> str:
    logger.info("🧠 Calling OpenAI for portfolio storytelling...")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a financial advisor who explains portfolios like a friendly, smart mentor. Write in a conversational tone that builds confidence and educates the user."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.6,
        max_tokens=1500,  # Increased for more detailed stories
    )

    return response.choices[0].message.content.strip()

def safe_extract_story_data(recommendation_json: Dict) -> Dict[str, Any]:
    """
    Safely extract relevant data for story generation from the enhanced recommendation JSON
    """
    try:
        # Core portfolio data
        story_data = {
            "allocation": recommendation_json.get("recommended_allocation", {}),
            "target_corpus": recommendation_json.get("target_corpus", 0),
            "suggested_sip": recommendation_json.get("suggested_sip", 0),
            "expected_return_percent": recommendation_json.get("expected_return_percent", 0),
            "portfolio_risk_score": recommendation_json.get("portfolio_risk_score", 0),
            "diversification_score": recommendation_json.get("diversification_score", 0)
        }
        
        # Fund summary (avoid passing full fund objects)
        funds = recommendation_json.get("recommended_funds", {})
        fund_summary = {}
        for asset_class, fund_list in funds.items():
            if isinstance(fund_list, list) and fund_list:
                fund_summary[asset_class] = {
                    "count": len(fund_list),
                    "sample_names": [f.get("name", "Unknown") for f in fund_list[:2] if isinstance(f, dict)],
                    "avg_rating": round(sum(f.get("rating", 0) for f in fund_list if isinstance(f, dict) and f.get("rating", 0) > 0) / max(1, len([f for f in fund_list if isinstance(f, dict) and f.get("rating", 0) > 0])), 1) if any(isinstance(f, dict) and f.get("rating", 0) > 0 for f in fund_list) else None
                }
        story_data["fund_summary"] = fund_summary
        
        # Enhanced insights
        affordability_check = recommendation_json.get("affordability_check", {})
        if affordability_check:
            story_data["affordability"] = {
                "has_issue": affordability_check.get("affordability_issue", False),
                "investment_ratio": affordability_check.get("investment_ratio_percent", 0),
                "timeline_impact": affordability_check.get("timeline_multiplier", 1)
            }
        
        investment_optimization = recommendation_json.get("investment_optimization", {})
        if investment_optimization:
            story_data["investment_style"] = {
                "type": investment_optimization.get("investment_type", "monthly_sip"),
                "amount": investment_optimization.get("amount", 0),
                "special_note": investment_optimization.get("note")
            }
        
        tax_optimization = recommendation_json.get("tax_optimization", {})
        if tax_optimization:
            story_data["tax_benefits"] = {
                "bracket": tax_optimization.get("tax_bracket", ""),
                "elss_amount": tax_optimization.get("elss_recommendation", 0),
                "ltcg_applicable": tax_optimization.get("ltcg_benefit_applicable", False)
            }
        
        emergency_fund = recommendation_json.get("emergency_fund_status", {})
        if emergency_fund:
            story_data["emergency_fund"] = {
                "months_covered": emergency_fund.get("months_covered", 0),
                "gap_amount": emergency_fund.get("gap", 0)
            }
        
        # Key notes (first few for context)
        notes = recommendation_json.get("notes", [])
        story_data["key_insights"] = notes[:3] if notes else []
        
        return story_data
        
    except Exception as e:
        logger.error(f"Error extracting story data: {e}")
        return {
            "allocation": recommendation_json.get("recommended_allocation", {}),
            "suggested_sip": recommendation_json.get("suggested_sip", 0),
            "error": "Limited data available for story generation"
        }

def generate_portfolio_story(recommendation_json: Dict) -> Dict:
    """
    Humanizes a portfolio recommendation into a friendly narrative for the user.
    Enhanced to work with the new recommendation structure.
    Returns {'story': string}
    """
    try:
        # Safely extract story-relevant data
        story_data = safe_extract_story_data(recommendation_json)
        
        prompt = f"""
Create a personalized, engaging portfolio story for an investor based on their recommendation. 

**Your Task:**
Write a friendly, professional narrative that:
1. **Welcomes** the investor and acknowledges their financial goals
2. **Explains the strategy** - why this allocation makes sense for them
3. **Highlights key benefits** - what this portfolio aims to achieve
4. **Addresses practical aspects** - SIP amount, timeline, tax benefits
5. **Builds confidence** - why this approach will work for their situation
6. **Motivates action** - encouraging them to start their investment journey

**Tone & Style:**
- Conversational and encouraging (like a trusted financial advisor)
- Avoid heavy jargon, use simple language
- Include specific numbers and percentages to make it concrete
- Use emojis sparingly but effectively
- Make it feel personal and tailored

**Structure:**
- Start with a warm greeting and goal acknowledgment
- Explain the asset allocation strategy
- Highlight the recommended funds/approach
- Discuss the investment amount and timeline
- Address any special considerations (tax benefits, affordability, emergency fund)
- End with an encouraging call to action

**Use markdown formatting** for better readability.

**Portfolio Data:**
```json
{json.dumps(story_data, indent=2)}
```

Write the story in 300-500 words. Make it inspiring and actionable.
        """

        story = _call_story_llm(prompt)
        logger.info("✅ Portfolio storytelling generated successfully.")
        return {"story": story}

    except Exception as e:
        logger.warning(f"⚠️ Failed to generate portfolio story: {e}")
        return {"story": "⚠️ Sorry, we couldn't generate your portfolio summary story. Please try again."}