# app/services/llm_review_service.py

import logging
import json
from typing import Dict, Any
from app.services.llm_wrapper import call_openai_chat

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def safe_extract_validation_data(recommendation_json: Dict) -> Dict[str, Any]:
    """
    Safely extract relevant data for validation from the enhanced recommendation JSON
    """
    try:
        validation_data = {
            "allocation": recommendation_json.get("recommended_allocation", {}),
            "target_corpus": recommendation_json.get("target_corpus", 0),
            "suggested_sip": recommendation_json.get("suggested_sip", 0),
            "expected_return_percent": recommendation_json.get("expected_return_percent", 0),
            "portfolio_risk_score": recommendation_json.get("portfolio_risk_score", 0),
            "diversification_score": recommendation_json.get("diversification_score", 0)
        }
        
        # Fund quality analysis
        funds = recommendation_json.get("recommended_funds", {})
        fund_analysis = {}
        total_funds = 0
        for asset_class, fund_list in funds.items():
            if isinstance(fund_list, list) and fund_list:
                total_funds += len(fund_list)
                expense_ratios = [f.get("expense_ratio", 0) for f in fund_list if isinstance(f, dict) and f.get("expense_ratio")]
                ratings = [f.get("rating", 0) for f in fund_list if isinstance(f, dict) and f.get("rating")]
                
                fund_analysis[asset_class] = {
                    "count": len(fund_list),
                    "avg_expense_ratio": round(sum(expense_ratios) / len(expense_ratios), 3) if expense_ratios else None,
                    "avg_rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
                    "has_high_expense": any(er > 2.0 for er in expense_ratios) if expense_ratios else False,
                    "has_low_rating": any(r < 3 for r in ratings) if ratings else False
                }
        
        validation_data["fund_analysis"] = fund_analysis
        validation_data["total_fund_count"] = total_funds
        
        # Risk and affordability checks
        affordability_check = recommendation_json.get("affordability_check", {})
        if affordability_check:
            validation_data["affordability_issues"] = {
                "has_issue": affordability_check.get("affordability_issue", False),
                "investment_ratio": affordability_check.get("investment_ratio_percent", 0),
                "timeline_extension": affordability_check.get("timeline_multiplier", 1)
            }
        
        # Tax optimization
        tax_optimization = recommendation_json.get("tax_optimization", {})
        if tax_optimization:
            validation_data["tax_efficiency"] = {
                "bracket": tax_optimization.get("tax_bracket", ""),
                "elss_eligible": tax_optimization.get("elss_recommendation", 0) > 0,
                "ltcg_applicable": tax_optimization.get("ltcg_benefit_applicable", False)
            }
        
        # Emergency fund status
        emergency_fund = recommendation_json.get("emergency_fund_status", {})
        if emergency_fund:
            validation_data["emergency_fund"] = {
                "months_covered": emergency_fund.get("months_covered", 0),
                "adequate": emergency_fund.get("months_covered", 0) >= 6
            }
        
        # Key notes for context
        notes = recommendation_json.get("notes", [])
        validation_data["warning_notes"] = [note for note in notes if "⚠️" in note or "warning" in note.lower()][:3]
        
        return validation_data
        
    except Exception as e:
        logger.error(f"Error extracting validation data: {e}")
        return {
            "allocation": recommendation_json.get("recommended_allocation", {}),
            "suggested_sip": recommendation_json.get("suggested_sip", 0),
            "error": "Limited data available for validation"
        }

def validate_and_explain_output(recommendation_json: Dict) -> Dict:
    """
    Validates the recommendation JSON and returns humanized explanation using OpenAI GPT.
    Enhanced to work with the new recommendation structure.
    """
    try:
        # Safely extract validation-relevant data
        validation_data = safe_extract_validation_data(recommendation_json)
        
        # Build enhanced user prompt
        user_prompt = f"""
You are a certified financial planner reviewing an AI-generated investment recommendation. Analyze the portfolio and provide professional feedback.

**Your Analysis Should Cover:**

1. **✅ VALIDATION CHECKS:**
   - Is the asset allocation balanced and appropriate?
   - Are the fund selections quality (expense ratios, ratings)?
   - Is the SIP amount realistic and affordable?
   - Are there any red flags or concerns?

2. **⚠️ RISK ASSESSMENT:**
   - Portfolio risk level appropriateness
   - Diversification quality
   - Any concentration risks
   - Missing elements (emergency fund, insurance)

3. **💡 PROFESSIONAL INSIGHTS:**
   - What this portfolio aims to achieve
   - Key strengths of the strategy
   - Potential improvements or considerations
   - Timeline and goal alignment

4. **📋 SUMMARY VERDICT:**
   - Overall recommendation quality (Excellent/Good/Needs Improvement)
   - Top 2-3 action items for the investor
   - Confidence level in this recommendation

**Guidelines:**
- Be professional but accessible
- Use specific numbers from the data
- Highlight both positives and areas for improvement
- Keep it concise but comprehensive (300-400 words)
- Use markdown formatting for clarity

**Portfolio Analysis Data:**
```json
{json.dumps(validation_data, indent=2)}
```

Provide your professional analysis:
        """

        # Call GPT through shared wrapper
        feedback = call_openai_chat(
            system_prompt="You are a certified financial planner with 15+ years of experience. Provide thorough, professional analysis of investment recommendations.",
            user_prompt=user_prompt,
            model="gpt-4o",
            temperature=0.3,  # Lower temperature for more consistent analysis
            max_tokens=1200   # Increased for comprehensive analysis
        )

        logger.info("✅ LLM successfully validated and provided professional feedback.")
        return {"llm_feedback": feedback}

    except Exception as e:
        logger.warning(f"⚠️ LLM validation failed: {e}")
        return {
            "llm_feedback": "⚠️ Professional validation temporarily unavailable. The recommendation has been generated using proven algorithms, but we recommend consulting with a financial advisor for personalized review."
        }