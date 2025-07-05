# app/services/portfolio_analysis.py

from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.portfolio import Holding, UserProfile, PortfolioRecommendation
from app.services.recommendation_engine import AdvancedPortfolioModel
from collections import defaultdict
import logging
from datetime import datetime, date
import numpy as np

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class EnhancedPortfolioAnalyzer:
    """
    Production-grade portfolio analyzer with personalized insights
    """
    
    # Benchmark returns for comparison
    BENCHMARK_RETURNS = {
        "nifty_50": 0.12,
        "nifty_smallcap": 0.15,
        "nifty_midcap": 0.14,
        "gilt": 0.07,
        "corporate_bond": 0.08,
        "gold": 0.06
    }
    
    # Risk metrics thresholds
    RISK_THRESHOLDS = {
        "concentration_limit": 0.20,  # 20% max in single holding
        "sector_limit": 0.25,        # 25% max in single sector
        "asset_limit": 0.80          # 80% max in single asset class
    }

    @classmethod
    def analyze_comprehensive(cls, holdings: List[Holding], profile: UserProfile, db: Session) -> Dict:
        """
        Comprehensive portfolio analysis with personalized recommendations
        """
        try:
            logger.info("🔍 Starting comprehensive portfolio analysis...")
            
            # Basic portfolio metrics
            basic_analysis = cls._calculate_basic_metrics(holdings)
            
            # Risk analysis
            risk_analysis = cls._analyze_portfolio_risk(holdings, basic_analysis["total_portfolio_value"])
            
            # Performance analysis
            performance_analysis = cls._analyze_performance(holdings, profile)
            
            # Diversification analysis
            diversification_analysis = cls._analyze_diversification(holdings, basic_analysis)
            
            # Goal alignment analysis
            goal_alignment = cls._analyze_goal_alignment(holdings, profile, basic_analysis["total_portfolio_value"])
            
            # Generate personalized recommendations
            recommendations = cls._generate_recommendations(
                holdings, profile, basic_analysis, risk_analysis, performance_analysis, db
            )
            
            # Portfolio health score
            health_score = cls._calculate_health_score(
                risk_analysis, performance_analysis, diversification_analysis, goal_alignment
            )
            
            # Rebalancing suggestions
            rebalancing = cls._generate_rebalancing_suggestions(holdings, profile, basic_analysis)
            
            logger.info("✅ Comprehensive portfolio analysis completed")
            
            return {
                "analysis_date": datetime.now().isoformat(),
                "user_profile_summary": cls._get_profile_summary(profile),
                "portfolio_overview": basic_analysis,
                "risk_analysis": risk_analysis,
                "performance_analysis": performance_analysis,
                "diversification_analysis": diversification_analysis,
                "goal_alignment": goal_alignment,
                "health_score": health_score,
                "rebalancing_suggestions": rebalancing,
                "personalized_recommendations": recommendations,
                "action_items": cls._generate_action_items(risk_analysis, performance_analysis, goal_alignment),
                "tax_implications": cls._analyze_tax_implications(holdings, profile)
            }
            
        except Exception as e:
            logger.error(f"❌ Portfolio analysis failed: {e}")
            raise ValueError(f"Portfolio analysis failed: {str(e)}")

    @classmethod
    def _calculate_basic_metrics(cls, holdings: List[Holding]) -> Dict:
        """Calculate basic portfolio metrics"""
        total_invested = 0.0
        total_current_value = 0.0
        asset_type_value = defaultdict(float)
        sector_value = defaultdict(float)
        individual_analysis = []
        
        for holding in holdings:
            invested_value = holding.avg_buy_price * holding.quantity
            current_value = holding.current_price * holding.quantity
            gain_loss = current_value - invested_value
            gain_pct = ((gain_loss / invested_value) * 100) if invested_value else 0.0
            
            # Days held calculation
            days_held = (date.today() - holding.buy_date).days if holding.buy_date else 0
            
            total_invested += invested_value
            total_current_value += current_value
            asset_type_value[holding.asset_type] += current_value
            sector_value[holding.sector] += current_value
            
            individual_analysis.append({
                "name": holding.name,
                "symbol": holding.symbol,
                "asset_type": holding.asset_type,
                "sector": holding.sector,
                "quantity": holding.quantity,
                "avg_buy_price": holding.avg_buy_price,
                "current_price": holding.current_price,
                "invested_value": round(invested_value, 2),
                "current_value": round(current_value, 2),
                "gain_loss": round(gain_loss, 2),
                "gain_loss_pct": round(gain_pct, 2),
                "portfolio_weight": round((current_value / total_current_value) * 100, 2) if total_current_value else 0,
                "days_held": days_held,
                "holding_period": "Long Term" if days_held > 365 else "Short Term",
                "buy_date": holding.buy_date
            })
        
        overall_return_pct = ((total_current_value - total_invested) / total_invested * 100) if total_invested else 0
        
        return {
            "total_invested": round(total_invested, 2),
            "total_portfolio_value": round(total_current_value, 2),
            "overall_gain_loss": round(total_current_value - total_invested, 2),
            "overall_return_pct": round(overall_return_pct, 2),
            "number_of_holdings": len(holdings),
            "asset_allocation": {k: round((v/total_current_value)*100, 2) for k, v in asset_type_value.items()},
            "sector_allocation": {k: round((v/total_current_value)*100, 2) for k, v in sector_value.items()},
            "holdings_detail": individual_analysis
        }

    @classmethod
    def _analyze_portfolio_risk(cls, holdings: List[Holding], total_value: float) -> Dict:
        """Analyze portfolio risk metrics"""
        risk_flags = []
        concentration_risk = {}
        
        # Single holding concentration risk
        for holding in holdings:
            current_value = holding.current_price * holding.quantity
            weight = (current_value / total_value) * 100
            
            if weight > cls.RISK_THRESHOLDS["concentration_limit"] * 100:
                concentration_risk[holding.name] = {
                    "weight": round(weight, 2),
                    "risk_level": "HIGH" if weight > 30 else "MEDIUM",
                    "recommendation": f"Consider reducing exposure below {cls.RISK_THRESHOLDS['concentration_limit']*100}%"
                }
                risk_flags.append(f"High concentration in {holding.name} ({weight:.1f}%)")
        
        # Sector concentration analysis
        sector_weights = defaultdict(float)
        for holding in holdings:
            current_value = holding.current_price * holding.quantity
            sector_weights[holding.sector] += (current_value / total_value) * 100
        
        sector_risk = {}
        for sector, weight in sector_weights.items():
            if weight > cls.RISK_THRESHOLDS["sector_limit"] * 100:
                sector_risk[sector] = {
                    "weight": round(weight, 2),
                    "risk_level": "HIGH" if weight > 40 else "MEDIUM"
                }
                risk_flags.append(f"High sector concentration in {sector} ({weight:.1f}%)")
        
        # Asset class concentration
        asset_weights = defaultdict(float)
        for holding in holdings:
            current_value = holding.current_price * holding.quantity
            asset_weights[holding.asset_type] += (current_value / total_value) * 100
        
        asset_risk = {}
        for asset, weight in asset_weights.items():
            if weight > cls.RISK_THRESHOLDS["asset_limit"] * 100:
                asset_risk[asset] = {
                    "weight": round(weight, 2),
                    "risk_level": "HIGH"
                }
                risk_flags.append(f"Over-concentration in {asset} ({weight:.1f}%)")
        
        # Calculate portfolio risk score (0-100, higher = riskier)
        risk_score = min(100, max(0, 
            len(concentration_risk) * 20 + 
            len(sector_risk) * 15 + 
            len(asset_risk) * 25
        ))
        
        return {
            "risk_score": risk_score,
            "risk_level": "LOW" if risk_score < 30 else "MEDIUM" if risk_score < 60 else "HIGH",
            "concentration_risk": concentration_risk,
            "sector_risk": sector_risk,
            "asset_risk": asset_risk,
            "risk_flags": risk_flags,
            "diversification_score": max(0, 100 - risk_score)
        }

    @classmethod
    def _analyze_performance(cls, holdings: List[Holding], profile: UserProfile) -> Dict:
        """Analyze portfolio performance"""
        performance_metrics = {
            "winners": [],
            "losers": [],
            "top_performers": [],
            "underperformers": []
        }
        
        total_gain_loss = 0
        total_invested = 0
        
        for holding in holdings:
            invested_value = holding.avg_buy_price * holding.quantity
            current_value = holding.current_price * holding.quantity
            gain_loss = current_value - invested_value
            gain_pct = ((gain_loss / invested_value) * 100) if invested_value else 0
            
            total_gain_loss += gain_loss
            total_invested += invested_value
            
            holding_data = {
                "name": holding.name,
                "gain_loss": round(gain_loss, 2),
                "gain_pct": round(gain_pct, 2),
                "current_value": round(current_value, 2)
            }
            
            if gain_pct > 0:
                performance_metrics["winners"].append(holding_data)
                if gain_pct > 20:
                    performance_metrics["top_performers"].append(holding_data)
            else:
                performance_metrics["losers"].append(holding_data)
                if gain_pct < -10:
                    performance_metrics["underperformers"].append(holding_data)
        
        # Sort by performance
        performance_metrics["winners"].sort(key=lambda x: x["gain_pct"], reverse=True)
        performance_metrics["losers"].sort(key=lambda x: x["gain_pct"])
        performance_metrics["top_performers"].sort(key=lambda x: x["gain_pct"], reverse=True)
        performance_metrics["underperformers"].sort(key=lambda x: x["gain_pct"])
        
        overall_return = (total_gain_loss / total_invested * 100) if total_invested else 0
        
        # Performance vs benchmarks (simplified)
        benchmark_comparison = cls._compare_with_benchmarks(holdings, overall_return)
        
        return {
            "overall_return_pct": round(overall_return, 2),
            "total_gain_loss": round(total_gain_loss, 2),
            "winners_count": len(performance_metrics["winners"]),
            "losers_count": len(performance_metrics["losers"]),
            "win_rate": round((len(performance_metrics["winners"]) / len(holdings)) * 100, 2),
            "performance_breakdown": performance_metrics,
            "benchmark_comparison": benchmark_comparison,
            "performance_grade": cls._get_performance_grade(overall_return)
        }

    @classmethod
    def _analyze_diversification(cls, holdings: List[Holding], basic_analysis: Dict) -> Dict:
        """Analyze portfolio diversification"""
        asset_allocation = basic_analysis["asset_allocation"]
        sector_allocation = basic_analysis["sector_allocation"]
        
        # Calculate diversification metrics
        asset_concentration = max(asset_allocation.values()) if asset_allocation else 0
        sector_concentration = max(sector_allocation.values()) if sector_allocation else 0
        
        # Diversification score (higher is better)
        diversification_score = 100 - (asset_concentration + sector_concentration) / 2
        
        diversification_issues = []
        if asset_concentration > 80:
            diversification_issues.append(f"Over-concentrated in single asset class ({asset_concentration:.1f}%)")
        if sector_concentration > 40:
            diversification_issues.append(f"Over-concentrated in single sector ({sector_concentration:.1f}%)")
        if len(holdings) < 5:
            diversification_issues.append("Too few holdings for proper diversification")
        
        return {
            "diversification_score": round(max(0, diversification_score), 2),
            "asset_concentration": round(asset_concentration, 2),
            "sector_concentration": round(sector_concentration, 2),
            "number_of_assets": len(asset_allocation),
            "number_of_sectors": len(sector_allocation),
            "diversification_grade": cls._get_diversification_grade(diversification_score),
            "diversification_issues": diversification_issues,
            "recommendations": cls._get_diversification_recommendations(asset_allocation, sector_allocation)
        }

    @classmethod
    def _analyze_goal_alignment(cls, holdings: List[Holding], profile: UserProfile, portfolio_value: float) -> Dict:
        """Analyze how well portfolio aligns with user goals"""
        # Get ideal allocation from recommendation engine
        ideal_allocation = AdvancedPortfolioModel.allocate_portfolio(profile)
        
        # Current allocation
        current_allocation = defaultdict(float)
        for holding in holdings:
            current_value = holding.current_price * holding.quantity
            
            # Map asset types to standard categories
            if holding.asset_type in ["stock", "mutual_fund"]:
                current_allocation["equity"] += current_value
            elif holding.asset_type in ["bond", "fd"]:
                current_allocation["debt"] += current_value
            elif holding.asset_type == "gold":
                current_allocation["gold"] += current_value
            elif holding.asset_type == "etf":
                # Assume equity ETF for simplicity - in production, you'd check the underlying
                current_allocation["equity"] += current_value
        
        # Convert to percentages
        current_allocation_pct = {k: (v/portfolio_value)*100 for k, v in current_allocation.items()}
        ideal_allocation_pct = {k: v*100 for k, v in ideal_allocation.items()}
        
        # Calculate alignment score
        alignment_score = 100
        rebalancing_needed = []
        
        for asset in ["equity", "debt", "gold"]:
            current = current_allocation_pct.get(asset, 0)
            ideal = ideal_allocation_pct.get(asset, 0)
            deviation = abs(current - ideal)
            
            if deviation > 10:  # More than 10% deviation
                alignment_score -= deviation
                rebalancing_needed.append({
                    "asset": asset,
                    "current": round(current, 2),
                    "ideal": round(ideal, 2),
                    "deviation": round(deviation, 2),
                    "action": "Increase" if current < ideal else "Decrease"
                })
        
        alignment_score = max(0, alignment_score)
        
        # Goal progress analysis
        goal_progress = None
        if profile.goal_amount and profile.goal_amount > 0:
            progress_pct = (portfolio_value / profile.goal_amount) * 100
            goal_progress = {
                "target_amount": profile.goal_amount,
                "current_amount": portfolio_value,
                "progress_pct": round(progress_pct, 2),
                "shortfall": max(0, profile.goal_amount - portfolio_value),
                "on_track": progress_pct >= 80  # Consider on track if 80% or more achieved
            }
        
        return {
            "alignment_score": round(alignment_score, 2),
            "current_allocation": current_allocation_pct,
            "ideal_allocation": ideal_allocation_pct,
            "rebalancing_needed": rebalancing_needed,
            "goal_progress": goal_progress,
            "alignment_grade": cls._get_alignment_grade(alignment_score)
        }

    @classmethod
    def _generate_recommendations(cls, holdings: List[Holding], profile: UserProfile, 
                                basic_analysis: Dict, risk_analysis: Dict, 
                                performance_analysis: Dict, db: Session) -> Dict:
        """Generate personalized portfolio recommendations"""
        recommendations = {
            "immediate_actions": [],
            "strategic_moves": [],
            "risk_management": [],
            "tax_optimization": [],
            "fund_suggestions": []
        }
        
        # Immediate actions based on risk analysis
        if risk_analysis["risk_score"] > 70:
            recommendations["immediate_actions"].append("🚨 High portfolio risk detected - consider rebalancing")
            
        for holding_name, risk_info in risk_analysis["concentration_risk"].items():
            if risk_info["risk_level"] == "HIGH":
                recommendations["immediate_actions"].append(
                    f"📉 Reduce exposure to {holding_name} (currently {risk_info['weight']}%)"
                )
        
        # Performance-based recommendations
        if performance_analysis["overall_return_pct"] < 5:
            recommendations["strategic_moves"].append("📈 Consider reviewing underperforming holdings")
            
        for underperformer in performance_analysis["performance_breakdown"]["underperformers"][:3]:
            if underperformer["gain_pct"] < -20:
                recommendations["strategic_moves"].append(
                    f"⚠️ Review {underperformer['name']} (down {abs(underperformer['gain_pct']):.1f}%)"
                )
        
        # Risk management suggestions
        if basic_analysis["number_of_holdings"] < 5:
            recommendations["risk_management"].append("🎯 Increase diversification with 3-5 more holdings")
            
        if "emergency_fund" not in [h.name.lower() for h in holdings]:
            recommendations["risk_management"].append("🛡️ Consider adding emergency fund allocation")
        
        # Tax optimization
        long_term_holdings = [h for h in basic_analysis["holdings_detail"] if h["days_held"] > 365]
        if len(long_term_holdings) < len(holdings) * 0.7:
            recommendations["tax_optimization"].append("💰 Consider holding investments >1 year for LTCG benefits")
        
        # Generate fund suggestions using existing engine
        try:
            ideal_allocation = AdvancedPortfolioModel.allocate_portfolio(profile)
            # You can add fund suggestion logic here using your existing fund_picker service
            recommendations["fund_suggestions"].append("🎯 Use our recommendation engine for optimized fund selection")
        except Exception as e:
            logger.warning(f"Could not generate fund suggestions: {e}")
        
        return recommendations

    @classmethod
    def _generate_rebalancing_suggestions(cls, holdings: List[Holding], profile: UserProfile, basic_analysis: Dict) -> Dict:
        """Generate specific rebalancing suggestions"""
        ideal_allocation = AdvancedPortfolioModel.allocate_portfolio(profile)
        portfolio_value = basic_analysis["total_portfolio_value"]
        
        # Current allocation mapping
        current_allocation = {"equity": 0, "debt": 0, "gold": 0}
        for holding in holdings:
            current_value = holding.current_price * holding.quantity
            if holding.asset_type in ["stock", "mutual_fund", "etf"]:
                current_allocation["equity"] += current_value
            elif holding.asset_type in ["bond", "fd"]:
                current_allocation["debt"] += current_value
            elif holding.asset_type == "gold":
                current_allocation["gold"] += current_value
        
        rebalancing_actions = []
        rebalancing_required = False
        
        for asset, ideal_weight in ideal_allocation.items():
            current_value = current_allocation.get(asset, 0)
            current_weight = current_value / portfolio_value if portfolio_value > 0 else 0
            ideal_value = portfolio_value * ideal_weight
            difference = ideal_value - current_value
            
            if abs(difference) > portfolio_value * 0.05:  # 5% threshold
                rebalancing_required = True
                action = "BUY" if difference > 0 else "SELL"
                rebalancing_actions.append({
                    "asset": asset,
                    "action": action,
                    "amount": abs(difference),
                    "current_weight": round(current_weight * 100, 2),
                    "target_weight": round(ideal_weight * 100, 2),
                    "priority": "HIGH" if abs(difference) > portfolio_value * 0.15 else "MEDIUM"
                })
        
        return {
            "rebalancing_required": rebalancing_required,
            "rebalancing_actions": rebalancing_actions,
            "next_review_date": cls._calculate_next_review_date(profile),
            "rebalancing_cost_estimate": cls._estimate_rebalancing_cost(rebalancing_actions)
        }

    @classmethod
    def _calculate_health_score(cls, risk_analysis: Dict, performance_analysis: Dict, 
                              diversification_analysis: Dict, goal_alignment: Dict) -> Dict:
        """Calculate overall portfolio health score"""
        
        # Weighted scoring
        weights = {
            "risk": 0.25,
            "performance": 0.30,
            "diversification": 0.25,
            "goal_alignment": 0.20
        }
        
        risk_score = max(0, 100 - risk_analysis["risk_score"])  # Invert risk score
        performance_score = min(100, max(0, performance_analysis["overall_return_pct"] * 5))  # Scale performance
        diversification_score = diversification_analysis["diversification_score"]
        alignment_score = goal_alignment["alignment_score"]
        
        overall_score = (
            risk_score * weights["risk"] +
            performance_score * weights["performance"] +
            diversification_score * weights["diversification"] +
            alignment_score * weights["goal_alignment"]
        )
        
        return {
            "overall_score": round(overall_score, 2),
            "grade": cls._get_health_grade(overall_score),
            "component_scores": {
                "risk_management": round(risk_score, 2),
                "performance": round(performance_score, 2),
                "diversification": round(diversification_score, 2),
                "goal_alignment": round(alignment_score, 2)
            },
            "improvement_areas": cls._identify_improvement_areas(
                risk_score, performance_score, diversification_score, alignment_score
            )
        }

    # Helper methods for grades and analysis
    @classmethod
    def _get_performance_grade(cls, return_pct: float) -> str:
        if return_pct >= 15: return "A+"
        elif return_pct >= 12: return "A"
        elif return_pct >= 8: return "B"
        elif return_pct >= 5: return "C"
        else: return "D"

    @classmethod
    def _get_diversification_grade(cls, score: float) -> str:
        if score >= 80: return "Excellent"
        elif score >= 60: return "Good"
        elif score >= 40: return "Fair"
        else: return "Poor"

    @classmethod
    def _get_alignment_grade(cls, score: float) -> str:
        if score >= 85: return "Excellent"
        elif score >= 70: return "Good"
        elif score >= 50: return "Fair"
        else: return "Needs Attention"

    @classmethod
    def _get_health_grade(cls, score: float) -> str:
        if score >= 85: return "A"
        elif score >= 75: return "B"
        elif score >= 65: return "C"
        elif score >= 50: return "D"
        else: return "F"

    @classmethod
    def _get_profile_summary(cls, profile: UserProfile) -> Dict:
        return {
            "age": profile.age,
            "risk_appetite": profile.risk_appetite,
            "investment_goal": profile.investment_goal,
            "timeline_years": profile.goal_timeline_years,
            "employment_status": profile.employment_status
        }

    @classmethod
    def _compare_with_benchmarks(cls, holdings: List[Holding], portfolio_return: float) -> Dict:
        """Compare portfolio performance with relevant benchmarks"""
        # Simplified benchmark comparison
        relevant_benchmarks = {
            "Nifty 50": cls.BENCHMARK_RETURNS["nifty_50"] * 100,
            "Balanced Portfolio": 10.0,  # Assumption
            "Gold": cls.BENCHMARK_RETURNS["gold"] * 100
        }
        
        comparisons = {}
        for benchmark, benchmark_return in relevant_benchmarks.items():
            outperformance = portfolio_return - benchmark_return
            comparisons[benchmark] = {
                "benchmark_return": benchmark_return,
                "outperformance": round(outperformance, 2),
                "status": "Outperforming" if outperformance > 0 else "Underperforming"
            }
        
        return comparisons

    @classmethod
    def _generate_action_items(cls, risk_analysis: Dict, performance_analysis: Dict, goal_alignment: Dict) -> List[Dict]:
        """Generate actionable items for the user"""
        action_items = []
        
        # High priority actions
        if risk_analysis["risk_score"] > 70:
            action_items.append({
                "priority": "HIGH",
                "category": "Risk Management",
                "action": "Reduce portfolio concentration risk",
                "timeline": "Within 1 month"
            })
        
        if performance_analysis["overall_return_pct"] < 5:
            action_items.append({
                "priority": "MEDIUM",
                "category": "Performance",
                "action": "Review and replace underperforming holdings",
                "timeline": "Within 3 months"
            })
        
        if goal_alignment["alignment_score"] < 70:
            action_items.append({
                "priority": "MEDIUM",
                "category": "Goal Alignment",
                "action": "Rebalance portfolio to match risk profile",
                "timeline": "Within 2 months"
            })
        
        return action_items

    @classmethod
    def _analyze_tax_implications(cls, holdings: List[Holding], profile: UserProfile) -> Dict:
        """Analyze tax implications of current holdings"""
        stcg_holdings = []
        ltcg_holdings = []
        total_unrealized_gains = 0
        
        for holding in holdings:
            days_held = (date.today() - holding.buy_date).days if holding.buy_date else 0
            unrealized_gain = (holding.current_price - holding.avg_buy_price) * holding.quantity
            
            if unrealized_gain > 0:
                total_unrealized_gains += unrealized_gain
                
                if days_held <= 365:
                    stcg_holdings.append({
                        "name": holding.name,
                        "gain": unrealized_gain,
                        "days_held": days_held,
                        "days_to_ltcg": 365 - days_held
                    })
                else:
                    ltcg_holdings.append({
                        "name": holding.name,
                        "gain": unrealized_gain,
                        "days_held": days_held
                    })
        
        # Tax estimates (simplified)
        stcg_tax = sum(h["gain"] for h in stcg_holdings) * 0.20  # 15% STCG
        ltcg_tax = max(0, (sum(h["gain"] for h in ltcg_holdings) - 100000)) * 0.125  # 10% LTCG above 1L
        
        return {
            "total_unrealized_gains": round(total_unrealized_gains, 2),
            "stcg_holdings": len(stcg_holdings),
            "ltcg_holdings": len(ltcg_holdings),
            "estimated_stcg_tax": round(stcg_tax, 2),
            "estimated_ltcg_tax": round(ltcg_tax, 2),
            "tax_optimization_suggestions": [
                "Hold STCG positions for >1 year for better tax treatment" if stcg_holdings else None,
                "Consider tax-loss harvesting for loss-making positions",
                "Plan exits strategically to minimize tax impact"
            ]
        }

    @classmethod
    def _identify_improvement_areas(cls, risk_score: float, performance_score: float, 
                                  diversification_score: float, alignment_score: float) -> List[str]:
        """Identify areas needing improvement"""
        improvements = []
        
        if risk_score < 60:
            improvements.append("Risk Management - Reduce concentration and volatility")
        if performance_score < 60:
            improvements.append("Performance - Review and optimize holdings selection")
        if diversification_score < 60:
            improvements.append("Diversification - Spread investments across assets and sectors")
        if alignment_score < 60:
            improvements.append("Goal Alignment - Rebalance to match investment objectives")
        
        return improvements

    @classmethod
    def _calculate_next_review_date(cls, profile: UserProfile) -> str:
        """Calculate when portfolio should be reviewed next"""
        from datetime import datetime, timedelta
        
        # Review frequency based on profile
        if profile.age > 55 or profile.risk_appetite == "low":
            months = 3  # Quarterly
        elif profile.risk_appetite == "high":
            months = 6  # Semi-annually
        else:
            months = 12  # Annually
        
        next_review = datetime.now() + timedelta(days=months * 30)
        return next_review.strftime("%Y-%m-%d")

    @classmethod
    def _estimate_rebalancing_cost(cls, rebalancing_actions: List[Dict]) -> Dict:
        """Estimate cost of rebalancing"""
        # Simplified cost estimation
        total_transaction_value = sum(action["amount"] for action in rebalancing_actions)
        estimated_cost = total_transaction_value * 0.005  # 0.5% assumption
        
        return {
            "total_transaction_value": round(total_transaction_value, 2),
            "estimated_cost": round(estimated_cost, 2),
            "cost_percentage": round((estimated_cost / total_transaction_value * 100), 2) if total_transaction_value > 0 else 0,
            "cost_breakdown": {
                "brokerage": round(estimated_cost * 0.6, 2),
                "taxes": round(estimated_cost * 0.3, 2),
                "charges": round(estimated_cost * 0.1, 2)
            }
        }

    @classmethod
    def _get_diversification_recommendations(cls, asset_allocation: Dict, sector_allocation: Dict) -> List[str]:
        """Get diversification improvement recommendations"""
        recommendations = []
        
        # Asset allocation recommendations
        max_asset_weight = max(asset_allocation.values()) if asset_allocation else 0
        if max_asset_weight > 80:
            recommendations.append("Consider reducing over-concentration in single asset class")
        
        if len(asset_allocation) < 3:
            recommendations.append("Add more asset classes (equity, debt, gold) for better diversification")
        
        # Sector allocation recommendations
        max_sector_weight = max(sector_allocation.values()) if sector_allocation else 0
        if max_sector_weight > 40:
            recommendations.append("Reduce sector concentration by investing across multiple sectors")
        
        if len(sector_allocation) < 5:
            recommendations.append("Diversify across more sectors to reduce sector-specific risk")
        
        # General recommendations
        recommendations.append("Consider regular rebalancing to maintain target allocation")
        recommendations.append("Review and adjust allocation based on market conditions")