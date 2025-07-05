from sqlalchemy.orm import Session
from app.models.portfolio import UserProfile
from app.models.portfolio import InvestmentOptimization
from app.models.portfolio import AffordabilityCheck
from app.models.portfolio import PortfolioRecommendation
from app.models.portfolio import TaxOptimization
from app.services.fund_picker import pick_funds
from app.services.fund_picker import get_emergency_fallback_funds 
from datetime import datetime
import numpy_financial as npf

class AdvancedPortfolioModel:
    # Historical asset class returns (adjust based on economic cycles)
    ASSET_RETURNS = {
        "equity": {"long_term": 0.12, "medium_term": 0.10, "short_term": 0.08},
        "debt": {"long_term": 0.075, "medium_term": 0.07, "short_term": 0.065},
        "gold": 0.06
    }
    
    # Inflation matrix based on location and goal type
    INFLATION_MATRIX = {
        "metro": {"default": 0.065, "education": 0.08, "retirement": 0.07},
        "tier_1": {"default": 0.06, "education": 0.075, "retirement": 0.065},
        "tier_2": {"default": 0.055, "education": 0.07, "retirement": 0.06},
        "town": {"default": 0.05, "education": 0.065, "retirement": 0.055},
        "rural": {"default": 0.045, "education": 0.06, "retirement": 0.05}
    }
    
    # Behavioral adjustment factors
    BEHAVIOR_ADJUSTMENTS = {
        "panic_sell": {"equity": -0.15, "gold": +0.05},
        "buy_more": {"equity": +0.1, "debt": -0.05}
    }

    @classmethod
    def get_inflation_rate(cls, profile: UserProfile) -> float:
        """Dynamic inflation based on location and goal type"""
        base_rate = cls.INFLATION_MATRIX.get(profile.location, {}).get("default", 0.06)
        
        # Education and retirement have specialized inflation rates
        if profile.investment_goal in ["child_education", "retirement", "early_retirement"]:
            return cls.INFLATION_MATRIX.get(profile.location, {}).get(
                "education" if "education" in profile.investment_goal else "retirement", 
                base_rate
            )
        return base_rate

    @classmethod
    def calculate_goal_corpus(cls, profile: UserProfile) -> float:
        """Inflation-adjusted goal amount with dynamic rate"""
        inflation_rate = cls.get_inflation_rate(profile)
        return round(profile.goal_amount * ((1 + inflation_rate) ** profile.goal_timeline_years), 2)

    @classmethod
    def get_expected_return(cls, asset_class: str, years: int) -> float:
        """Time-adjusted expected returns"""
        if asset_class == "gold":
            return cls.ASSET_RETURNS["gold"]
        
        term = "long_term" if years > 7 else "medium_term" if years > 3 else "short_term"
        return cls.ASSET_RETURNS[asset_class][term]

    @classmethod
    def determine_base_equity(cls, profile: UserProfile) -> float:
        """Enhanced with income-based risk capacity"""
        # Existing risk tolerance logic...
        if profile.risk_tolerance_score is not None:
            if profile.risk_tolerance_score >= 80:
                base_equity = 0.85
            elif profile.risk_tolerance_score >= 60:
                base_equity = 0.7
            elif profile.risk_tolerance_score >= 40:
                base_equity = 0.5
            else:
                base_equity = 0.3
        else:
            base_equity = {
                "low": 0.3,
                "medium": 0.6,
                "high": 0.85
            }[profile.risk_appetite]
        
        # 🔥 NEW: Income-based risk capacity adjustment
        if profile.income:
            if profile.income > 2000000:  # High income (>20L)
                base_equity *= 1.15  # Can afford more risk
            elif profile.income > 1000000:  # Upper middle (10-20L)
                base_equity *= 1.05
            elif profile.income < 500000:  # Lower income (<5L)
                base_equity *= 0.85  # Need more stability
        
        # Existing employment adjustments...
        if profile.employment_status == "retired":
            base_equity *= 0.6
        elif profile.employment_status == "student":
            base_equity *= 1.2
        
        return min(max(base_equity, 0.1), 0.95)    

    @classmethod
    def apply_behavioral_adjustments(cls, allocation: dict, profile: UserProfile) -> dict:
        """Adjust for investor psychology patterns"""
        if profile.market_reactions in cls.BEHAVIOR_ADJUSTMENTS:
            adjustments = cls.BEHAVIOR_ADJUSTMENTS[profile.market_reactions]
            for asset, adj in adjustments.items():
                allocation[asset] = max(0, allocation[asset] + adj)
        
        # Normalize after adjustments
        total = sum(allocation.values())
        return {k: v/total for k, v in allocation.items()}

    @classmethod
    def allocate_portfolio(cls, profile: UserProfile) -> dict:
        """Sophisticated allocation with glide path and preferences"""
        base_equity = cls.determine_base_equity(profile)
        
        # Glide path adjustment (reduce equity as goal approaches)
        glide_factor = max(0.5, 1 - (profile.goal_timeline_years / 30))
        equity = base_equity * glide_factor
        
        # Gold allocation (higher for inflation-hedge goals)
        gold = 0.05
        if profile.investment_goal in ["retirement", "early_retirement"]:
            gold = 0.08
        elif profile.investment_goal in ["child_education", "wealth_growth"]:
            gold = 0.07
        
        # Debt allocation
        debt = 1 - equity - gold
        
        # Preference-based tilting
        if profile.preference:
            if "esg" in profile.preference.lower():
                equity *= 1.1  # Increase equity for ESG-focused funds
            if "tax" in profile.preference.lower():
                debt *= 1.15  # Increase debt for tax-efficient instruments
        
        allocation = {
            "equity": equity,
            "debt": debt,
            "gold": gold
        }
        
        # Liquidity overlay
        if profile.need_liquidity or profile.expected_large_expense:
            allocation["debt"] += 0.1
            # Reduce proportionally from other assets
            reduction_factor = 0.1 / (allocation["equity"] + allocation["gold"])
            allocation["equity"] *= (1 - reduction_factor)
            allocation["gold"] *= (1 - reduction_factor)
        
        # Apply behavioral adjustments
        allocation = cls.apply_behavioral_adjustments(allocation, profile)
        
        # Final normalization
        total = sum(allocation.values())
        return {k: round(v/total, 2) for k, v in allocation.items()}

    @classmethod
    def calculate_sip_amount(cls, profile: UserProfile, allocation: dict) -> float:
        """Dynamic SIP calculation with blended returns"""
        blended_return = 0
        for asset, weight in allocation.items():
            asset_return = cls.get_expected_return(asset, profile.goal_timeline_years)
            blended_return += weight * asset_return
        
        corpus = cls.calculate_goal_corpus(profile)
        n = profile.goal_timeline_years * 12
        r = blended_return / 12
        
        # Use numpy financial for accurate SIP calculation
        sip = -npf.pmt(r, n, 0, corpus)
        return round(sip, 2)

    @classmethod
    def validate_affordability(cls, profile: UserProfile, suggested_sip: float) -> dict:
        """Critical: Prevent impossible SIP recommendations"""
        if not profile.income or profile.income <= 0:
            return {
                "affordability_issue": False,
                "suggested_sip": suggested_sip,
                "warning": "Income information needed for accurate recommendations"
            }
        
        # Use disposable income if available, otherwise conservative 20% rule
        monthly_income = profile.income / 12
        if hasattr(profile, 'disposable_income') and profile.disposable_income > 0:
            max_affordable = min(profile.disposable_income, monthly_income * 0.25)  # Cap at 25%
        else:
            max_affordable = monthly_income * 0.20  # Conservative default
        
        investment_ratio_percent = (suggested_sip * 12 / profile.income) * 100
        
        if suggested_sip > max_affordable:
            affordable_sip = max_affordable
            timeline_extension = suggested_sip / affordable_sip
            
            return {
                "affordability_issue": True,
                "suggested_sip": round(affordable_sip, 0),
                "original_sip": suggested_sip,
                "timeline_multiplier": round(timeline_extension, 1),
                "max_affordable_amount": round(max_affordable, 0),
                "investment_ratio_percent": round(investment_ratio_percent, 1),
                "warning": f"⚠️ Suggested SIP (₹{suggested_sip:,.0f}) exceeds affordable limit. Realistic SIP: ₹{affordable_sip:,.0f}"
            }
        
        return {
            "affordability_issue": False, 
            "suggested_sip": suggested_sip,
            "investment_ratio_percent": round(investment_ratio_percent, 1),
            "max_affordable_amount": round(max_affordable, 0)
        }


    @classmethod
    def get_tax_bracket(cls, income: float) -> str:
        """Determine highest marginal tax bracket for optimization based on FY 2025-26 Indian tax regime"""
        # FY 2025-26 New Tax Regime (Progressive slabs)
        if income <= 400000:  # Up to 4 lakh
            return "0%"
        elif income <= 800000:  # 4 lakh to 8 lakh
            return "5%"
        elif income <= 1200000:  # 8 lakh to 12 lakh
            return "10%"
        elif income <= 1600000:  # 12 lakh to 16 lakh
            return "15%"
        elif income <= 2000000:  # 16 lakh to 20 lakh
            return "20%"
        elif income <= 2400000:  # 20 lakh to 24 lakh
            return "25%"
        else:  # Above 24 lakh
            return "30%"

    @classmethod
    def calculate_effective_tax_rate(cls, income: float) -> float:
        """Calculate effective tax rate based on FY 2025-26 progressive tax slabs"""
        if income <= 400000:
            return 0.0
        elif income <= 1200000:
            # Due to rebate of Rs. 60,000, effective tax is zero up to 12 lakh
            return 0.0
        else:
            # Calculate progressive tax
            tax = 0
            # 4-8 lakh: 5%
            tax += min(income - 400000, 400000) * 0.05
            # 8-12 lakh: 10%
            if income > 800000:
                tax += min(income - 800000, 400000) * 0.10
            # 12-16 lakh: 15%
            if income > 1200000:
                tax += min(income - 1200000, 400000) * 0.15
            # 16-20 lakh: 20%
            if income > 1600000:
                tax += min(income - 1600000, 400000) * 0.20
            # 20-24 lakh: 25%
            if income > 2000000:
                tax += min(income - 2000000, 400000) * 0.25
            # Above 24 lakh: 30%
            if income > 2400000:
                tax += (income - 2400000) * 0.30
            
            # Apply rebate of Rs. 60,000 if income <= 12 lakh
            if income <= 1200000:
                tax = max(0, tax - 60000)
            
            return tax / income if income > 0 else 0.0

    @classmethod
    def apply_tax_optimization(cls, allocation: dict, profile: UserProfile) -> dict:
        """Tax-efficient allocation based on FY 2025-26 Indian income tax brackets"""
        if not profile.income:
            return allocation
        
        marginal_tax_bracket = cls.get_tax_bracket(profile.income)
        effective_tax_rate = cls.calculate_effective_tax_rate(profile.income)
        
        # High marginal tax bracket (30%): Favor tax-efficient instruments
        if marginal_tax_bracket == "30%" and profile.goal_timeline_years > 3:
            # Increase equity (LTCG benefits) and ELSS exposure
            allocation["equity"] *= 1.08
            # Add note for ELSS consideration for Section 80C benefits
        
        # Upper-medium marginal tax bracket (25%): Strong tax optimization
        elif marginal_tax_bracket == "25%" and profile.goal_timeline_years > 3:
            allocation["equity"] *= 1.06
            # Consider tax-saving instruments and equity for LTCG benefits
        
        # Medium-high marginal tax bracket (20%): Moderate tax optimization
        elif marginal_tax_bracket == "20%" and profile.goal_timeline_years > 2:
            allocation["equity"] *= 1.05
            # Consider tax-saving instruments
        
        # Lower-medium marginal tax bracket (15%): Light tax optimization
        elif marginal_tax_bracket == "15%" and profile.goal_timeline_years > 2:
            allocation["equity"] *= 1.03
            # Some focus on tax efficiency
        
        # High effective tax rate (above 12%): Focus on tax efficiency
        if effective_tax_rate > 0.12:
            allocation["equity"] *= 1.04
            # Consider tax-efficient debt instruments
        
        # Young, high-income earners (above 16 lakh - where 20% bracket starts): More aggressive equity allocation
        if profile.age < 35 and profile.income > 1600000:
            allocation["equity"] *= 1.1
            allocation["gold"] *= 0.9
        
        # Ultra-high income earners (above 50 lakh): Consider surcharge implications
        if profile.income > 5000000:
            # At this level, surcharge applies - focus heavily on tax-efficient long-term instruments
            # Surcharge rates: 10% (50L-1Cr), 15% (1Cr-2Cr), 25% (2Cr-5Cr), 25% (above 5Cr in new regime)
            allocation["equity"] *= 1.12
            allocation["gold"] *= 0.85
        
        # Very high income earners (above 24 lakh): Maximize LTCG benefits
        if profile.income > 2400000 and profile.goal_timeline_years > 1:
            allocation["equity"] *= 1.08
            # At 30% bracket, LTCG at 12.5% (after 1 lakh exemption) is very beneficial
        
        # Income in no-tax zone (up to 12 lakh due to rebate): Focus on growth
        if profile.income <= 1200000:
            # No immediate tax benefit needed, focus on wealth creation
            if profile.age < 40:
                allocation["equity"] *= 1.02
        
        # Normalize to ensure total allocation equals 1
        total = sum(allocation.values())
        return {k: v/total for k, v in allocation.items()}

    @classmethod
    def generate_behavioral_notes(cls, profile: UserProfile, allocation: dict) -> list:
        """Enhanced human-like coaching based on behavior patterns"""
        notes = []
        
        # Experience-based guidance (more detailed)
        if hasattr(profile, 'investment_experience'):
            if profile.investment_experience == "beginner":
                notes.append("📚 Beginner Strategy: Start with large-cap and index funds for stability")
                notes.append("🎯 Success Tip: Focus on consistent SIP rather than timing the market")
                if allocation.get("equity", 0) > 0.6:
                    notes.append("🚀 Your portfolio is growth-oriented - perfect for long-term wealth building")
            
            elif profile.investment_experience == "intermediate":
                notes.append("📈 Intermediate Strategy: Mix of large-cap stability with mid-cap growth potential")
                notes.append("🧠 Market Wisdom: Consider rebalancing annually to maintain target allocation")
            
            elif profile.investment_experience == "advanced":
                notes.append("🚀 Advanced Strategy: Mid-cap and small-cap funds for higher growth potential")
                if allocation.get("equity", 0) > 0.7:
                    notes.append("⚡ High equity allocation suits your risk profile and experience")
                notes.append("🎯 Pro Tip: Consider tactical allocation adjustments based on market cycles")

        # Income-based personalized advice
        if profile.income:
            monthly_income = profile.income / 12
            # 🔥 FIX: Remove reference to suggested_sip from allocation
            
            if profile.income > 2000000:  # High income
                notes.append("💰 High Income Strategy: Consider additional tax-saving instruments like PPF/ELSS")
            elif profile.income < 500000:  # Lower income
                notes.append("🛡️ Building Wealth: Every rupee counts - consistency will compound over time")
                notes.append("📊 Smart Approach: Start small and increase SIP by 10-15% annually")

        # Employment status insights
        if profile.employment_status == "retired":
            if allocation["equity"] > 0.4:
                notes.append("⚠️ Retirement Portfolio: Consider reducing equity exposure for capital preservation")
            notes.append("🏦 Retirement Strategy: Maintain 2-3 years of expenses in liquid funds")
        
        elif profile.employment_status == "student":
            notes.append("🎓 Student Advantage: Long time horizon allows for aggressive growth strategy")
            notes.append("📚 Learning Opportunity: Use this time to understand market cycles")
        
        elif profile.employment_status == "self_employed":
            notes.append("💼 Self-Employed Strategy: Build larger emergency fund (12 months expenses)")
            notes.append("📊 Cash Flow Tip: Consider quarterly SIP to match irregular income")

        # Behavioral finance insights
        if hasattr(profile, 'market_reactions'):
            if profile.market_reactions == "panic_sell":
                notes.append("🧠 Behavioral Insight: Market downturns are temporary - stay invested for best results")
                notes.append("📈 Historical Fact: Markets recover 100% of the time over long periods")
            elif profile.market_reactions == "buy_more":
                notes.append("🎯 Smart Investor: Your instinct to buy during dips is wealth-building behavior")

        # Goal-specific strategic advice
        goal_advice = {
            "retirement": "🏖️ Retirement Goal: Balance growth with stability as you approach target date",
            "child_education": "🎓 Education Goal: Start aggressive, move conservative closer to admission",
            "house": "🏠 Home Goal: Keep significant portion in debt funds 2-3 years before purchase",
            "emergency_fund": "🛡️ Emergency Strategy: 100% liquid/overnight funds for immediate access",
            "wealth_growth": "🚀 Wealth Building: Time is your biggest advantage - stay equity-heavy",
            "wedding": "💒 Wedding Goal: Balanced approach with flexibility for changing timelines"
        }
        
        if profile.investment_goal in goal_advice:
            notes.append(goal_advice[profile.investment_goal])

        # Risk-adjusted insights
        if profile.risk_appetite == "high" and allocation.get("equity", 0) < 0.7:
            notes.append("🎯 Risk Mismatch: Your high risk appetite suggests higher equity allocation possible")
        elif profile.risk_appetite == "low" and allocation.get("equity", 0) > 0.4:
            notes.append("⚖️ Balanced Approach: Moderate equity exposure balances growth with your comfort level")

        # Timeline-based strategy notes
        if profile.goal_timeline_years < 3:
            notes.append("⏰ Short Timeline: Focus on capital preservation over growth")
        elif profile.goal_timeline_years > 10:
            notes.append("🎯 Long Timeline Advantage: Equity volatility smooths out over decades")

        return notes
    @classmethod
    def optimize_investment_frequency(cls, profile: UserProfile, base_sip: float) -> dict:
        """Optimize based on investment frequency preference"""
        if not hasattr(profile, 'investment_frequency'):
            return {"sip": base_sip, "frequency": "monthly"}
        
        if profile.investment_frequency == "lumpsum":
            # Calculate equivalent lumpsum
            years = profile.goal_timeline_years
            lumpsum = base_sip * 12 * years * 0.85  # Adjust for lumpsum advantage
            return {
                "investment_type": "lumpsum",
                "amount": round(lumpsum, 0),
                "note": "💰 Lumpsum investment can be more efficient if you have the corpus"
            }
        
        elif profile.investment_frequency == "quarterly":
            quarterly_sip = base_sip * 3 * 1.02  # Slight adjustment for frequency
            return {
                "investment_type": "quarterly_sip",
                "amount": round(quarterly_sip, 0),
                "note": "📅 Quarterly SIP: Good for irregular income patterns"
            }
        
        return {"investment_type": "monthly_sip", "amount": base_sip}
    @classmethod
    def recommend_portfolio(cls, profile: UserProfile, db: Session) -> PortfolioRecommendation:
        """Human-like financial advice engine"""
        try:
            # Validation
            if not profile.goal_amount or profile.goal_amount <= 0:
                raise ValueError("Valid goal amount is required for recommendations")
            
            # Core calculations
            corpus = cls.calculate_goal_corpus(profile)
            allocation = cls.allocate_portfolio(profile)
            allocation = cls.apply_tax_optimization(allocation, profile)
            base_sip = cls.calculate_sip_amount(profile, allocation)
            affordability = cls.validate_affordability(profile, base_sip)
            final_sip = affordability.get("suggested_sip", base_sip)
            frequency_opt = cls.optimize_investment_frequency(profile, final_sip)
            
            # Generate insights
            expected_return_pct = (
                sum(cls.get_expected_return(a, profile.goal_timeline_years) * w 
                    for a, w in allocation.items()) * 100
            )

            notes = [
                f"🎯 Inflation-adjusted Goal Corpus: ₹{corpus:,.2f}",
                f"💸 Suggested Monthly SIP: ₹{final_sip:,.2f}",
                f"📈 Expected Portfolio Return: {expected_return_pct:.1f}%"
            ]
            
            if affordability.get("affordability_issue"):
                notes.append(affordability.get("warning", ""))
                if affordability.get("timeline_multiplier", 1) > 1.2:
                    notes.append(f"⏰ Consider extending timeline by {affordability['timeline_multiplier']:.1f}x for affordability")

            # Append behavioral insights
            notes.extend(cls.generate_behavioral_notes(profile, allocation))
            
            if profile.income:
                investment_ratio = affordability.get("investment_ratio_percent", 0)
                notes.append(f"📊 Investment ratio: {investment_ratio:.1f}% of annual income (healthy: 15-25%)")
                
                if investment_ratio > 25:
                    notes.append("⚠️ High investment ratio - ensure emergency fund is adequate")
            
            # Tax efficiency guidance
            if profile.goal_timeline_years > 3:
                notes.append("💰 Tax tip: Equity funds held >1 year qualify for lower LTCG tax (10% over ₹1L)")
            
            # Fund recommendations with error handling
            recommended_funds = {}
            fund_warnings = []

            for asset, weight in allocation.items():
                if weight > 0.05:  # Only recommend for significant allocations
                    try:
                        print(f"🔍 Fetching funds for {asset} (weight: {weight:.2%})")
                        
                        funds = pick_funds(
                            db=db,
                            asset_class=asset,
                            risk_level=profile.risk_appetite,
                            goal_type=profile.investment_goal,
                            timeline=profile.goal_timeline_years,
                            preference=profile.preference,
                            allowed_assets=profile.preferred_assets,
                            experience_level=getattr(profile, 'investment_experience', None),
                            limit=3
                        )
                        
                        if not funds:
                            # Final safety net - get any funds for this asset class
                            print(f"⚠️ No funds returned for {asset}, trying emergency fallback")
                            emergency_funds = get_emergency_fallback_funds(db, asset, 2)
                            
                            if emergency_funds:
                                funds = emergency_funds
                                fund_warnings.append(f"Limited {asset} fund options available - showing best alternatives")
                            else:
                                fund_warnings.append(f"No {asset} funds available in database")
                                funds = []
                        
                        # Check for fallback funds and add appropriate notes
                        fallback_count = sum(1 for f in funds if f.get("is_fallback", False))
                        if fallback_count > 0:
                            fund_warnings.append(f"Some {asset} recommendations are fallback options due to strict filter criteria")
                        
                        recommended_funds[asset] = funds
                        print(f"✅ Found {len(funds)} funds for {asset} (fallbacks: {fallback_count})")
                        
                    except Exception as e:
                        print(f"❌ Error fetching funds for {asset}: {e}")
                        fund_warnings.append(f"Technical error retrieving {asset} funds - please try again")
                        recommended_funds[asset] = []

            # Add fund warnings to notes
            if fund_warnings:
                notes.extend([f"🔍 Fund Selection: {warning}" for warning in fund_warnings])

            # Add fund availability summary
            total_funds = sum(len(funds) for funds in recommended_funds.values())
            if total_funds > 0:
                notes.append(f"📊 Found {total_funds} fund recommendations across your portfolio allocation")
            else:
                notes.append("⚠️ Limited fund data available - consider manual fund selection")

            # Enhanced fund quality analysis
            fund_quality_score = 0
            total_weightage = 0

            for asset, funds in recommended_funds.items():
                asset_weight = allocation.get(asset, 0)
                if funds and asset_weight > 0:
                    # Calculate average rating for this asset class
                    valid_ratings = [f.get("rating", 0) for f in funds if f.get("rating")]
                    if valid_ratings:
                        avg_rating = sum(valid_ratings) / len(valid_ratings)
                        fund_quality_score += avg_rating * asset_weight
                        total_weightage += asset_weight

            portfolio_fund_quality = round(fund_quality_score / max(total_weightage, 0.01), 1) if total_weightage > 0 else 0

            if portfolio_fund_quality >= 4:
                notes.append(f"⭐ Excellent fund quality score: {portfolio_fund_quality}/5")
            elif portfolio_fund_quality >= 3:
                notes.append(f"👍 Good fund quality score: {portfolio_fund_quality}/5")
            else:
                notes.append(f"📊 Fund quality score: {portfolio_fund_quality}/5 - consider alternatives")
                        
            # Create structured objects
            investment_optimization = InvestmentOptimization(
                investment_type=frequency_opt.get("investment_type", "monthly_sip"),
                amount=frequency_opt.get("amount", final_sip),
                frequency=frequency_opt.get("frequency"),
                note=frequency_opt.get("note"),
                step_up_suggestion=frequency_opt.get("step_up_suggestion")
            )
            
            affordability_check = AffordabilityCheck(
                affordability_issue=affordability.get("affordability_issue", False),
                suggested_sip=affordability.get("suggested_sip", final_sip),
                original_sip=affordability.get("original_sip"),
                timeline_multiplier=affordability.get("timeline_multiplier"),
                warning=affordability.get("warning"),
                max_affordable_amount=affordability.get("max_affordable_amount"),
                investment_ratio_percent=affordability.get("investment_ratio_percent")
            )
            
            # Tax optimization analysis
            tax_optimization = None
            if profile.income:
                tax_bracket = cls.get_tax_bracket(profile.income)
                
                tax_optimization = TaxOptimization(
                    tax_bracket=tax_bracket,
                    elss_recommendation=min(150000, final_sip * 12 * 0.3) if profile.goal_timeline_years >= 3 else None,
                    ltcg_benefit_applicable=profile.goal_timeline_years > 1,
                    tax_saving_amount=None,
                    notes=["Consider ELSS for tax savings under 80C"] if profile.goal_timeline_years >= 3 else []
                )
            
            # Emergency fund status
            emergency_fund_status = {
                "required": profile.emergency_fund_needed,
                "current": profile.existing_emergency_fund or 0,
                "gap": profile.emergency_fund_gap,
                "months_covered": round((profile.existing_emergency_fund or 0) / max(1, profile.monthly_expenses or profile.income/12 * 0.7), 1)
            }
            
            # Calculate risk and diversification scores
            portfolio_risk_score = min(100, max(0, int(
                allocation.get("equity", 0) * 80 + 
                allocation.get("debt", 0) * 20 + 
                allocation.get("gold", 0) * 40
            )))
            
            diversification_score = min(100, max(0, int(
                100 - abs(50 - portfolio_risk_score) * 2
            )))
            
            # Create and return the structured response
            recommendation = PortfolioRecommendation(
                recommended_allocation=allocation,
                target_corpus=corpus,
                suggested_sip=final_sip,
                recommended_funds=recommended_funds,
                notes=notes,
                investment_optimization=investment_optimization,
                affordability_check=affordability_check,
                tax_optimization=tax_optimization,
                emergency_fund_status=emergency_fund_status,
                expected_return_percent=round(expected_return_pct, 2),
                portfolio_risk_score=portfolio_risk_score,
                diversification_score=diversification_score
            )
            
            return recommendation
            
        except Exception as e:
            # Fallback for any calculation errors
            print(f"Error in portfolio recommendation: {e}")
            raise ValueError(f"Could not generate portfolio recommendation: {str(e)}")