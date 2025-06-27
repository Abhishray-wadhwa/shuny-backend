from app.models.portfolio import UserProfile
from app.models.mutual_fund import MutualFund
from typing import Dict

class FundSuitabilityEngine:
    @staticmethod
    def analyze(profile: UserProfile, fund) -> Dict:  # Made fund parameter generic
        result = {
            "suitable": True,
            "issues": [],
            "reasons": [],
            "fund_metadata": {}  # ===== FIXED: Add missing fund_metadata =====
        }

        # Add fund metadata for compatibility
        try:
            result["fund_metadata"] = {
                "fund_code": getattr(fund, 'code', 'N/A'),  # ===== FIXED: Add fund_code field =====
                "code": getattr(fund, 'code', 'N/A'),
                "name": getattr(fund, 'name', 'N/A'),
                "category": getattr(fund, 'scheme_category', 'N/A'),
                "risk_level": getattr(fund, 'risk_level', 'N/A'),
                "aum": getattr(fund, 'aum', 0),
                "nav": getattr(fund, 'nav', 0),
                "expense_ratio": getattr(fund, 'expense_ratio', 0),
                "rating": getattr(fund, 'rating', None),
                "return_5y": getattr(fund, 'return_5y', None)
            }
        except Exception:
            result["fund_metadata"] = {
                "fund_code": "N/A", 
                "error": "Could not extract fund metadata"
            }

        # Risk level match
        fund_risk = getattr(fund, 'risk_level', '').lower()
        if profile.risk_appetite == "low" and fund_risk not in ["low", "low to moderate"]:
            result["suitable"] = False
            result["issues"].append("Risk Mismatch")
            result["reasons"].append(f"User is low risk, but fund is {fund_risk}")

        if profile.risk_appetite == "medium" and fund_risk == "high":
            result["issues"].append("High risk fund for moderate profile")
            result["reasons"].append("Moderate risk profile may not prefer high-risk funds")

        # Timeline mismatch
        if profile.goal_timeline_years < 3 and fund_risk in ["high", "moderately high"]:
            result["suitable"] = False
            result["issues"].append("Short Timeline, High Risk")
            result["reasons"].append("High-risk fund not ideal for short-term goals")

        # Goal alignment
        scheme_category = getattr(fund, 'scheme_category', '') or ''
        if profile.investment_goal == "emergency_fund" and "liquid" not in scheme_category.lower():
            result["suitable"] = False
            result["issues"].append("Liquidity Mismatch")
            result["reasons"].append("Emergency fund goal should align with Liquid/Overnight category")

        # Expense ratio
        expense_ratio = getattr(fund, 'expense_ratio', None)
        if expense_ratio and expense_ratio > 1.5:
            result["issues"].append("High expense ratio")
            result["reasons"].append(f"Expense ratio is {expense_ratio}%")

        # ===== FIXED: Add suitability_flags for API compatibility =====
        result["suitability_flags"] = {
            "suitable": result["suitable"],
            "risk_match": profile.risk_appetite == "low" and fund_risk in ["low", "low to moderate"],
            "timeline_appropriate": not (profile.goal_timeline_years < 3 and fund_risk in ["high", "moderately high"]),
            "goal_aligned": not (profile.investment_goal == "emergency_fund" and "liquid" not in scheme_category.lower()),
            "reasonable_expense": not (expense_ratio and expense_ratio > 1.5)
        }

        return result

