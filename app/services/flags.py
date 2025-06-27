# app/services/flags.py

from typing import Dict, List, Any, Union
import logging

logger = logging.getLogger(__name__)

def extract_flags(recommendation_json: Dict) -> List[str]:
    """
    Evaluates the recommendation output and generates structured flags
    for downstream use (e.g., UI warnings, quality checks).
    Enhanced to work with new recommendation structure.
    """
    flags = []
    
    try:
        allocation = recommendation_json.get("recommended_allocation", {})
        funds = recommendation_json.get("recommended_funds", {})
        affordability_check = recommendation_json.get("affordability_check", {})
        investment_optimization = recommendation_json.get("investment_optimization", {})
        emergency_fund_status = recommendation_json.get("emergency_fund_status", {})
        
        # 1. Missing asset class checks
        if not funds.get("gold") or len(funds.get("gold", [])) == 0:
            flags.append("missing_gold")
        
        if not funds.get("equity") or len(funds.get("equity", [])) == 0:
            flags.append("missing_equity")
        
        if not funds.get("debt") or len(funds.get("debt", [])) == 0:
            flags.append("missing_debt")
        
        # 2. Allocation validation
        if allocation:
            total = sum(allocation.values())
            if abs(total - 1.0) > 0.02:  # Allow small rounding differences
                flags.append("allocation_sum_error")
                logger.warning(f"Allocation sum error: {total}")
        
        # 3. Fund quality checks
        high_expense_funds = []
        low_rating_funds = []
        
        for asset_class, fund_list in funds.items():
            if not isinstance(fund_list, list):
                continue
                
            for fund in fund_list:
                if not isinstance(fund, dict):
                    continue
                    
                # High expense ratio check (>2% for equity, >1.5% for debt)
                expense_ratio = fund.get("expense_ratio", 0)
                threshold = 2.0 if asset_class == "equity" else 1.5
                if expense_ratio > threshold:
                    high_expense_funds.append(f"{fund.get('name', 'Unknown')} ({expense_ratio}%)")
                
                # Low rating check
                rating = fund.get("rating")
                if rating and rating < 3:
                    low_rating_funds.append(f"{fund.get('name', 'Unknown')} ({rating}⭐)")
                
                # Check for fallback funds
                if fund.get("is_fallback", False):
                    flags.append("fallback_funds_used")
        
        if high_expense_funds:
            flags.append("high_expense_ratio")
            logger.info(f"High expense ratio funds: {high_expense_funds}")
        
        if low_rating_funds:
            flags.append("low_rating_funds")
            logger.info(f"Low rating funds: {low_rating_funds}")
        
        # 4. Portfolio diversity checks
        total_funds = sum(len(fund_list) if isinstance(fund_list, list) else 0 
                         for fund_list in funds.values())
        if total_funds < 2:
            flags.append("too_few_funds")
        elif total_funds > 8:
            flags.append("over_diversified")
        
        # 5. Affordability flags
        if affordability_check and affordability_check.get("affordability_issue", False):
            flags.append("affordability_issue")
            
            # Check investment ratio
            investment_ratio = affordability_check.get("investment_ratio_percent", 0)
            if investment_ratio > 30:
                flags.append("high_investment_ratio")
            elif investment_ratio < 10:
                flags.append("low_investment_ratio")
        
        # 6. Risk assessment flags
        portfolio_risk_score = recommendation_json.get("portfolio_risk_score", 0)
        if portfolio_risk_score > 80:
            flags.append("high_risk_portfolio")
        elif portfolio_risk_score < 20:
            flags.append("very_conservative_portfolio")
        
        # 7. Emergency fund flags
        if emergency_fund_status:
            gap = emergency_fund_status.get("gap", 0)
            months_covered = emergency_fund_status.get("months_covered", 0)
            
            if gap > 0:
                flags.append("emergency_fund_gap")
            
            if months_covered < 3:
                flags.append("inadequate_emergency_fund")
        
        # 8. Investment optimization flags
        if investment_optimization:
            investment_type = investment_optimization.get("investment_type", "")
            if investment_type == "lumpsum":
                flags.append("lumpsum_recommended")
            elif investment_type == "quarterly_sip":
                flags.append("quarterly_sip_recommended")
        
        # 9. Tax optimization flags
        tax_optimization = recommendation_json.get("tax_optimization", {})
        if tax_optimization:
            tax_bracket = tax_optimization.get("tax_bracket", "")
            if tax_bracket == "30%":
                flags.append("high_tax_bracket")
            
            if tax_optimization.get("elss_recommendation"):
                flags.append("elss_recommended")
        
        # 10. Performance flags
        expected_return = recommendation_json.get("expected_return_percent", 0)
        if expected_return < 8:
            flags.append("low_expected_return")
        elif expected_return > 15:
            flags.append("high_expected_return")
        
        # 11. Diversification flags
        diversification_score = recommendation_json.get("diversification_score", 0)
        if diversification_score < 60:
            flags.append("poor_diversification")
        elif diversification_score > 90:
            flags.append("excellent_diversification")
        
        # 12. Check for any alerts
        alerts = recommendation_json.get("alerts", [])
        if alerts and len(alerts) > 0:
            flags.append("has_alerts")
            
            # Check for specific alert types
            for alert in alerts:
                if isinstance(alert, dict):
                    alert_type = alert.get("type", "").lower()
                    if "underperform" in alert_type:
                        flags.append("underperforming_funds")
                    elif "expense" in alert_type:
                        flags.append("expense_alert")
                    elif "risk" in alert_type:
                        flags.append("risk_alert")
        
        # Remove duplicates and return
        unique_flags = list(set(flags))
        logger.info(f"Generated {len(unique_flags)} flags: {unique_flags}")
        return unique_flags
        
    except Exception as e:
        logger.error(f"Error extracting flags: {e}")
        return ["flag_extraction_error"]


def get_flag_descriptions() -> Dict[str, str]:
    """
    Returns human-readable descriptions for all possible flags.
    Useful for frontend display.
    """
    return {
        # Asset class flags
        "missing_gold": "No gold funds recommended - consider adding for inflation protection",
        "missing_equity": "No equity funds recommended - may limit growth potential",
        "missing_debt": "No debt funds recommended - may increase portfolio volatility",
        
        # Quality flags
        "high_expense_ratio": "Some funds have high expense ratios - consider lower-cost alternatives",
        "low_rating_funds": "Some funds have low ratings - review fund quality",
        "fallback_funds_used": "Limited fund options available - some recommendations are alternatives",
        
        # Portfolio structure flags
        "too_few_funds": "Very few funds recommended - may lack diversification",
        "over_diversified": "Many funds recommended - consider simplifying portfolio",
        "allocation_sum_error": "Portfolio allocation doesn't sum to 100% - review calculations",
        
        # Affordability flags
        "affordability_issue": "Recommended SIP may exceed affordable limit",
        "high_investment_ratio": "Investment amount is high relative to income",
        "low_investment_ratio": "Investment amount is conservative - consider increasing if possible",
        
        # Risk flags
        "high_risk_portfolio": "High-risk portfolio - ensure you're comfortable with volatility",
        "very_conservative_portfolio": "Very conservative portfolio - may limit long-term growth",
        
        # Emergency fund flags
        "emergency_fund_gap": "Emergency fund is below recommended level",
        "inadequate_emergency_fund": "Emergency fund covers less than 3 months of expenses",
        
        # Investment strategy flags
        "lumpsum_recommended": "Lumpsum investment recommended over SIP",
        "quarterly_sip_recommended": "Quarterly SIP recommended over monthly",
        
        # Tax flags
        "high_tax_bracket": "In high tax bracket - consider tax-efficient investments",
        "elss_recommended": "ELSS funds recommended for tax savings",
        
        # Performance flags
        "low_expected_return": "Lower expected returns - consider more growth-oriented allocation",
        "high_expected_return": "High expected returns - ensure risk tolerance matches",
        
        # Diversification flags
        "poor_diversification": "Portfolio may need better diversification",
        "excellent_diversification": "Well-diversified portfolio structure",
        
        # Alert flags
        "has_alerts": "Portfolio has monitoring alerts - review recommendations",
        "underperforming_funds": "Some funds may be underperforming",
        "expense_alert": "High expense ratio alert triggered",
        "risk_alert": "Risk management alert triggered",
        
        # Error flags
        "flag_extraction_error": "Error occurred while analyzing portfolio - please review manually"
    }