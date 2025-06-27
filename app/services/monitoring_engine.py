# app/services/monitoring_engine.py

import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MonitoringEngine:
    """
    Engine for generating portfolio monitoring alerts and notifications
    """
    
    @staticmethod
    def generate_alerts_safe(recommended_funds: Dict[str, List], profile: Dict) -> List[Dict]:
        """
        Safely generate alerts for recommended funds
        
        Args:
            recommended_funds: Dictionary of asset class -> list of funds
            profile: User profile dictionary
            
        Returns:
            List of alert dictionaries
        """
        try:
            return MonitoringEngine._generate_alerts_internal(recommended_funds, profile)
        except Exception as e:
            logger.error(f"Error generating alerts: {e}")
            return []
    
    @staticmethod
    def _generate_alerts_internal(recommended_funds: Dict[str, List], profile: Dict) -> List[Dict]:
        """
        Internal method to generate alerts
        """
        alerts = []
        
        # Check for high expense ratios
        for asset_class, funds in recommended_funds.items():
            for fund in funds:
                # Handle both dict and object types
                if isinstance(fund, dict):
                    expense_ratio = fund.get('expense_ratio', 0)
                    fund_name = fund.get('name', 'Unknown Fund')
                else:
                    expense_ratio = getattr(fund, 'expense_ratio', 0)
                    fund_name = getattr(fund, 'name', 'Unknown Fund')
                
                if expense_ratio > 2.0:
                    alerts.append({
                        "type": "high_expense_ratio",
                        "severity": "warning",
                        "message": f"High expense ratio detected in {fund_name}: {expense_ratio}%",
                        "fund_name": fund_name,
                        "asset_class": asset_class,
                        "timestamp": datetime.now().isoformat()
                    })
        
        # Check for risk alignment
        user_risk_tolerance = profile.get('risk_tolerance', 'moderate') if isinstance(profile, dict) else getattr(profile, 'risk_tolerance', 'moderate')
        
        if user_risk_tolerance == 'conservative':
            # Check if equity allocation is too high
            equity_funds = recommended_funds.get('equity', [])
            if len(equity_funds) > 2:
                alerts.append({
                    "type": "risk_mismatch",
                    "severity": "info",
                    "message": f"Conservative investor with {len(equity_funds)} equity funds - consider reducing equity exposure",
                    "timestamp": datetime.now().isoformat()
                })
        
        return alerts
    
    @staticmethod
    def generate_alerts_from_holdings(holdings: List[Dict]) -> List[Dict]:
        """
        Generate alerts from existing portfolio holdings
        
        Args:
            holdings: List of current portfolio holdings
            
        Returns:
            List of alert dictionaries
        """
        alerts = []
        
        try:
            total_value = sum(holding.get('current_value', 0) for holding in holdings)
            
            for holding in holdings:
                current_value = holding.get('current_value', 0)
                purchase_value = holding.get('purchase_value', current_value)
                
                # Calculate percentage of portfolio
                portfolio_percentage = (current_value / total_value * 100) if total_value > 0 else 0
                
                # Alert for overconcentration
                if portfolio_percentage > 40:
                    alerts.append({
                        "type": "overconcentration",
                        "severity": "warning",
                        "message": f"High concentration in {holding.get('name', 'Unknown')}: {portfolio_percentage:.1f}% of portfolio",
                        "holding_name": holding.get('name', 'Unknown'),
                        "percentage": portfolio_percentage,
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Alert for significant losses
                if purchase_value > 0:
                    loss_percentage = ((current_value - purchase_value) / purchase_value) * 100
                    if loss_percentage < -20:
                        alerts.append({
                            "type": "significant_loss",
                            "severity": "alert",
                            "message": f"Significant loss in {holding.get('name', 'Unknown')}: {loss_percentage:.1f}%",
                            "holding_name": holding.get('name', 'Unknown'),
                            "loss_percentage": loss_percentage,
                            "timestamp": datetime.now().isoformat()
                        })
        
        except Exception as e:
            logger.error(f"Error generating alerts from holdings: {e}")
        
        return alerts
    
    @staticmethod
    def check_portfolio_health(portfolio_data: Dict) -> Dict:
        """
        Perform comprehensive portfolio health check
        
        Args:
            portfolio_data: Dictionary containing portfolio information
            
        Returns:
            Dictionary with health check results
        """
        health_score = 100
        issues = []
        recommendations = []
        
        try:
            # Check diversification
            asset_classes = portfolio_data.get('asset_allocation', {})
            if len(asset_classes) < 2:
                health_score -= 20
                issues.append("Insufficient diversification")
                recommendations.append("Consider adding more asset classes")
            
            # Check expense ratios
            funds = portfolio_data.get('funds', [])
            high_expense_funds = [f for f in funds if f.get('expense_ratio', 0) > 2.0]
            if high_expense_funds:
                health_score -= 10 * len(high_expense_funds)
                issues.append(f"{len(high_expense_funds)} funds with high expense ratios")
                recommendations.append("Consider switching to lower-cost alternatives")
            
            # Ensure score doesn't go below 0
            health_score = max(0, health_score)
            
            return {
                "health_score": health_score,
                "status": "healthy" if health_score >= 80 else "needs_attention" if health_score >= 60 else "poor",
                "issues": issues,
                "recommendations": recommendations,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error checking portfolio health: {e}")
            return {
                "health_score": 0,
                "status": "error",
                "issues": ["Unable to assess portfolio health"],
                "recommendations": ["Please check your portfolio data"],
                "timestamp": datetime.now().isoformat()
            }
    @staticmethod
    def check_recommendation_health(recommendation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate alerts based on PortfolioRecommendation structure.
        """
        alerts = []

        try:
            # Check portfolio risk score
            risk_score = recommendation.get("portfolio_risk_score", 50)
            if risk_score >= 80:
                alerts.append({
                    "type": "high_risk",
                    "severity": "warning",
                    "message": f"High portfolio risk score: {risk_score}/100",
                    "timestamp": datetime.now().isoformat()
                })

            # Diversification check
            diversification = recommendation.get("diversification_score", 100)
            if diversification < 50:
                alerts.append({
                    "type": "low_diversification",
                    "severity": "info",
                    "message": f"Diversification score is low: {diversification}/100",
                    "timestamp": datetime.now().isoformat()
                })

            # Emergency fund gap
            ef_status = recommendation.get("emergency_fund_status", {})
            if ef_status and ef_status.get("gap", 0) > 0:
                alerts.append({
                    "type": "emergency_fund_gap",
                    "severity": "warning",
                    "message": f"Emergency fund gap of ₹{ef_status['gap']:,}",
                    "timestamp": datetime.now().isoformat()
                })

            # Affordability issue
            aff = recommendation.get("affordability_check", {})
            if aff.get("affordability_issue", False):
                alerts.append({
                    "type": "affordability_issue",
                    "severity": "warning",
                    "message": f"SIP of ₹{aff['original_sip']} exceeds affordability. Suggested: ₹{aff['suggested_sip']}",
                    "timestamp": datetime.now().isoformat()
                })

            # High expense ratio funds
            for asset_class, funds in recommendation.get("recommended_funds", {}).items():
                for fund in funds:
                    expense = fund.get("expense_ratio", 0)
                    if expense > 2.0:
                        alerts.append({
                            "type": "high_expense_ratio",
                            "severity": "warning",
                            "message": f"High expense ratio ({expense}%) in {fund.get('name', 'Unknown')}",
                            "timestamp": datetime.now().isoformat()
                        })

        except Exception as e:
            logger.error(f"Error in check_recommendation_health: {e}")

        return alerts
# Legacy function for backward compatibility
def generate_alerts_safe(recommended_funds: Dict[str, List], profile: Dict) -> List[Dict]:
    """Legacy function - use MonitoringEngine.generate_alerts_safe instead"""
    return MonitoringEngine.generate_alerts_safe(recommended_funds, profile)