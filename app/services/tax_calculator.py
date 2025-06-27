# app/services/tax_calculator.py

from typing import Dict, List
from datetime import datetime, date,timedelta
from app.models.portfolio import Holding, UserProfile
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class TaxCalculator:
    """
    Comprehensive tax calculator for Indian tax laws
    """
    
    # Indian tax rates (FY 2024-25)
    TAX_RATES = {
        "equity": {
            "stcg": Decimal('0.15'),  # 15% for equity STCG
            "ltcg": Decimal('0.10'),  # 10% for equity LTCG above 1L
            "ltcg_threshold": Decimal('100000')  # Rs 1 lakh exemption
        },
        "debt": {
            "stcg": "slab_rate",  # As per user's tax slab
            "ltcg": Decimal('0.20')   # 20% with indexation
        },
        "gold": {
            "stcg": "slab_rate",
            "ltcg": Decimal('0.20')   # 20% with indexation
        }
    }
    
    # Tax slabs for FY 2024-25 (new regime)
    TAX_SLABS_NEW = [
        (0, 300000, Decimal('0')),
        (300001, 600000, Decimal('0.05')),
        (600001, 900000, Decimal('0.10')),
        (900001, 1200000, Decimal('0.15')),
        (1200001, 1500000, Decimal('0.20')),
        (1500001, float('inf'), Decimal('0.30'))
    ]
    
    # Tax slabs for FY 2024-25 (old regime)
    TAX_SLABS_OLD = [
        (0, 250000, Decimal('0')),
        (250001, 500000, Decimal('0.05')),
        (500001, 1000000, Decimal('0.20')),
        (1000001, float('inf'), Decimal('0.30'))
    ]
    
    def analyze_tax_implications(self, holdings: List[Holding], profile: UserProfile) -> Dict:
        """Comprehensive tax analysis of portfolio"""
        
        current_date = date.today()
        tax_analysis = {
            "unrealized_gains": {
                "stcg": Decimal('0'),
                "ltcg": Decimal('0'),
                "total": Decimal('0')
            },
            "tax_liability": {
                "stcg_tax": Decimal('0'),
                "ltcg_tax": Decimal('0'),
                "total_tax": Decimal('0')
            },
            "holdings_analysis": [],
            "tax_optimization_opportunities": [],
            "harvest_candidates": []
        }
        
        for holding in holdings:
            holding_analysis = self._analyze_holding_tax(holding, current_date, profile)
            tax_analysis["holdings_analysis"].append(holding_analysis)
            
            # Aggregate gains
            if holding_analysis["is_short_term"]:
                tax_analysis["unrealized_gains"]["stcg"] += holding_analysis["unrealized_gain"]
            else:
                tax_analysis["unrealized_gains"]["ltcg"] += holding_analysis["unrealized_gain"]
        
        # Calculate total gains
        tax_analysis["unrealized_gains"]["total"] = (
            tax_analysis["unrealized_gains"]["stcg"] + 
            tax_analysis["unrealized_gains"]["ltcg"]
        )
        
        # Calculate tax liability
        tax_analysis["tax_liability"] = self._calculate_tax_liability(
            tax_analysis["unrealized_gains"], profile
        )
        
        # Generate optimization opportunities
        tax_analysis["tax_optimization_opportunities"] = self._generate_tax_optimization_opportunities(
            holdings, tax_analysis, profile
        )
        
        # Identify tax loss harvesting candidates
        tax_analysis["harvest_candidates"] = self._identify_harvest_candidates(holdings, current_date)
        
        return tax_analysis
    
    def _analyze_holding_tax(self, holding: Holding, current_date: date, profile: UserProfile) -> Dict:
        """Analyze tax implications for a single holding"""
        
        purchase_date = holding.purchase_date.date() if isinstance(holding.purchase_date, datetime) else holding.purchase_date
        holding_period = (current_date - purchase_date).days
        
        # Determine if short-term or long-term
        is_short_term = self._is_short_term_holding(holding.asset_type, holding_period)
        
        # Calculate unrealized gain/loss
        current_value = Decimal(str(holding.current_price)) * Decimal(str(holding.quantity))
        invested_value = Decimal(str(holding.avg_buy_price)) * Decimal(str(holding.quantity))
        unrealized_gain = current_value - invested_value
        
        # Calculate applicable tax rate
        tax_rate = self._get_applicable_tax_rate(holding.asset_type, is_short_term, profile)
        
        # Calculate potential tax
        potential_tax = Decimal('0')
        if unrealized_gain > 0:
            if holding.asset_type.lower() == "equity" and not is_short_term:
                # LTCG exemption for equity
                taxable_gain = max(unrealized_gain - self.TAX_RATES["equity"]["ltcg_threshold"], Decimal('0'))
                potential_tax = taxable_gain * tax_rate
            else:
                potential_tax = unrealized_gain * tax_rate
        
        return {
            "symbol": holding.symbol,
            "name": holding.name,
            "holding_period_days": holding_period,
            "is_short_term": is_short_term,
            "invested_value": float(invested_value),
            "current_value": float(current_value),
            "unrealized_gain": unrealized_gain,
            "tax_rate": float(tax_rate),
            "potential_tax": float(potential_tax),
            "asset_type": holding.asset_type,
            "purchase_date": purchase_date.isoformat(),
            "ltcg_eligible_date": self._get_ltcg_eligible_date(purchase_date, holding.asset_type).isoformat()
        }
    
    def _is_short_term_holding(self, asset_type: str, holding_period_days: int) -> bool:
        """Determine if holding is short-term based on asset type and holding period"""
        
        thresholds = {
            "equity": 365,      # 1 year for equity
            "mutual_fund": 365, # 1 year for equity mutual funds
            "etf": 365,         # 1 year for equity ETFs
            "debt": 1095,       # 3 years for debt
            "gold": 1095,       # 3 years for gold
            "real_estate": 730, # 2 years for real estate
            "commodity": 1095   # 3 years for commodities
        }
        
        threshold = thresholds.get(asset_type.lower(), 365)
        return holding_period_days <= threshold
    
    def _get_applicable_tax_rate(self, asset_type: str, is_short_term: bool, profile: UserProfile) -> Decimal:
        """Get applicable tax rate based on asset type and holding period"""
        
        asset_type_lower = asset_type.lower()
        
        if asset_type_lower == "equity":
            if is_short_term:
                return self.TAX_RATES["equity"]["stcg"]
            else:
                return self.TAX_RATES["equity"]["ltcg"]
        
        elif asset_type_lower in ["debt", "fd"]:
            if is_short_term:
                return self._get_slab_rate(profile)
            else:
                return self.TAX_RATES["debt"]["ltcg"]
        
        elif asset_type_lower == "gold":
            if is_short_term:
                return self._get_slab_rate(profile)
            else:
                return self.TAX_RATES["gold"]["ltcg"]
        
        else:
            # Default to slab rate for other assets
            return self._get_slab_rate(profile)
    
    def _get_slab_rate(self, profile: UserProfile) -> Decimal:
        """Calculate marginal tax rate based on user's income and tax regime"""
        
        annual_income = profile.annual_income or Decimal('0')
        tax_regime = getattr(profile, 'tax_regime', 'new')  # Default to new regime
        
        if tax_regime == 'new':
            slabs = self.TAX_SLABS_NEW
        else:
            slabs = self.TAX_SLABS_OLD
        
        for min_income, max_income, rate in slabs:
            if min_income <= annual_income <= max_income:
                return rate
        
        return Decimal('0.30')  # Highest slab rate
    
    def _calculate_tax_liability(self, unrealized_gains: Dict, profile: UserProfile) -> Dict:
        """Calculate total tax liability on unrealized gains"""
        
        stcg_tax = Decimal('0')
        ltcg_tax = Decimal('0')
        
        # STCG tax (typically at slab rate or fixed rate)
        if unrealized_gains["stcg"] > 0:
            stcg_tax = unrealized_gains["stcg"] * Decimal('0.15')  # Simplified - assuming equity
        
        # LTCG tax (with exemption for equity)
        if unrealized_gains["ltcg"] > 0:
            taxable_ltcg = max(unrealized_gains["ltcg"] - self.TAX_RATES["equity"]["ltcg_threshold"], Decimal('0'))
            ltcg_tax = taxable_ltcg * self.TAX_RATES["equity"]["ltcg"]
        
        return {
            "stcg_tax": stcg_tax,
            "ltcg_tax": ltcg_tax,
            "total_tax": stcg_tax + ltcg_tax,
            "effective_tax_rate": self._calculate_effective_tax_rate(
                unrealized_gains["total"], stcg_tax + ltcg_tax
            )
        }
    
    def _calculate_effective_tax_rate(self, total_gain: Decimal, total_tax: Decimal) -> Decimal:
        """Calculate effective tax rate"""
        if total_gain > 0:
            return (total_tax / total_gain * 100).quantize(Decimal('0.01'))
        return Decimal('0')
    
    def _generate_tax_optimization_opportunities(self, holdings: List[Holding], 
                                               tax_analysis: Dict, profile: UserProfile) -> List[Dict]:
        """Generate tax optimization strategies"""
        
        opportunities = []
        
        # Tax loss harvesting opportunities
        loss_holdings = [h for h in holdings if self._calculate_unrealized_gain(h) < 0]
        if loss_holdings:
            total_losses = sum(abs(self._calculate_unrealized_gain(h)) for h in loss_holdings)
            opportunities.append({
                "strategy": "tax_loss_harvesting",
                "description": "Realize losses to offset taxable gains",
                "potential_benefit": f"Offset up to ₹{total_losses:,.0f} in gains",
                "holdings_count": len(loss_holdings),
                "priority": "high" if total_losses > 50000 else "medium"
            })
        
        # LTCG threshold optimization
        ltcg_near_threshold = [
            h for h in holdings 
            if not self._is_short_term_holding(h.asset_type, (date.today() - h.purchase_date.date()).days)
            and self._calculate_unrealized_gain(h) > 0
            and self._calculate_unrealized_gain(h) < self.TAX_RATES["equity"]["ltcg_threshold"]
        ]
        
        if ltcg_near_threshold:
            opportunities.append({
                "strategy": "ltcg_threshold_optimization",
                "description": "Realize LTCG gains within ₹1L exemption limit",
                "potential_benefit": "Utilize annual LTCG exemption",
                "holdings_count": len(ltcg_near_threshold),
                "priority": "medium"
            })
        
        # Asset allocation for tax efficiency
        if profile.risk_appetite and profile.risk_appetite.lower() in ["conservative", "moderate"]:
            opportunities.append({
                "strategy": "debt_fund_optimization",
                "description": "Consider debt funds over FDs for better tax efficiency",
                "potential_benefit": "Lower tax rate on LTCG vs interest income",
                "priority": "low"
            })
        
        return opportunities
    
    def _identify_harvest_candidates(self, holdings: List[Holding], current_date: date) -> List[Dict]:
        """Identify holdings suitable for tax loss harvesting"""
        
        candidates = []
        
        for holding in holdings:
            unrealized_gain = self._calculate_unrealized_gain(holding)
            
            if unrealized_gain < 0:  # Loss-making holdings
                holding_period = (current_date - holding.purchase_date.date()).days
                is_short_term = self._is_short_term_holding(holding.asset_type, holding_period)
                
                candidates.append({
                    "symbol": holding.symbol,
                    "name": holding.name,
                    "unrealized_loss": float(abs(unrealized_gain)),
                    "loss_percentage": float((unrealized_gain / (holding.avg_buy_price * holding.quantity)) * 100),
                    "holding_period_days": holding_period,
                    "is_short_term": is_short_term,
                    "recommendation": self._get_harvest_recommendation(holding, unrealized_gain, is_short_term)
                })
        
        # Sort by loss amount (descending)
        candidates.sort(key=lambda x: x["unrealized_loss"], reverse=True)
        
        return candidates
    
    def _get_harvest_recommendation(self, holding: Holding, unrealized_gain: Decimal, is_short_term: bool) -> str:
        """Get recommendation for tax loss harvesting"""
        
        loss_amount = abs(unrealized_gain)
        
        if loss_amount > 50000:
            return "Strong candidate - significant loss to harvest"
        elif loss_amount > 20000:
            return "Good candidate - moderate loss amount"
        elif is_short_term and loss_amount > 10000:
            return "Consider harvesting - short-term loss can offset gains"
        else:
            return "Monitor - small loss amount"
    
    def _calculate_unrealized_gain(self, holding: Holding) -> Decimal:
        """Calculate unrealized gain/loss for a holding"""
        current_value = Decimal(str(holding.current_price)) * Decimal(str(holding.quantity))
        invested_value = Decimal(str(holding.avg_buy_price)) * Decimal(str(holding.quantity))
        return current_value - invested_value
    
    def _get_ltcg_eligible_date(self, purchase_date: date, asset_type: str) -> date:
        """Get the date when holding becomes eligible for LTCG"""
        
        thresholds = {
            "equity": 365,
            "mutual_fund": 365,
            "etf": 365,
            "debt": 1095,
            "gold": 1095,
            "real_estate": 730,
            "commodity": 1095
        }
        
        threshold_days = thresholds.get(asset_type.lower(), 365)
        return purchase_date + timedelta(days=threshold_days + 1)
    
    def calculate_tax_on_sale(self, holding: Holding, sale_price: Decimal, 
                            sale_date: date, profile: UserProfile) -> Dict:
        """Calculate tax implications of selling a specific holding"""
        
        purchase_date = holding.purchase_date.date() if isinstance(holding.purchase_date, datetime) else holding.purchase_date
        holding_period = (sale_date - purchase_date).days
        
        is_short_term = self._is_short_term_holding(holding.asset_type, holding_period)
        
        # Calculate actual gain/loss
        sale_value = sale_price * Decimal(str(holding.quantity))
        invested_value = Decimal(str(holding.avg_buy_price)) * Decimal(str(holding.quantity))
        actual_gain = sale_value - invested_value
        
        # Calculate tax
        tax_rate = self._get_applicable_tax_rate(holding.asset_type, is_short_term, profile)
        
        tax_amount = Decimal('0')
        if actual_gain > 0:
            if holding.asset_type.lower() == "equity" and not is_short_term:
                # Apply LTCG exemption
                taxable_gain = max(actual_gain - self.TAX_RATES["equity"]["ltcg_threshold"], Decimal('0'))
                tax_amount = taxable_gain * tax_rate
            else:
                tax_amount = actual_gain * tax_rate
        
        return {
            "holding_name": holding.name,
            "sale_value": float(sale_value),
            "invested_value": float(invested_value),
            "actual_gain": float(actual_gain),
            "gain_percentage": float((actual_gain / invested_value) * 100) if invested_value > 0 else 0,
            "holding_period_days": holding_period,
            "is_short_term": is_short_term,
            "tax_rate": float(tax_rate),
            "tax_amount": float(tax_amount),
            "net_proceeds": float(sale_value - tax_amount),
            "effective_tax_rate": float((tax_amount / actual_gain) * 100) if actual_gain > 0 else 0
        }
    
    def estimate_annual_tax_liability(self, holdings: List[Holding], profile: UserProfile) -> Dict:
        """Estimate annual tax liability based on current portfolio"""
        
        tax_analysis = self.analyze_tax_implications(holdings, profile)
        
        # Project annual liability based on current unrealized gains
        annual_estimate = {
            "current_unrealized_gains": float(tax_analysis["unrealized_gains"]["total"]),
            "potential_tax_liability": float(tax_analysis["tax_liability"]["total_tax"]),
            "quarterly_estimates": self._calculate_quarterly_estimates(tax_analysis),
            "advance_tax_due": self._calculate_advance_tax(tax_analysis, profile),
            "recommendations": [
                "Consider tax loss harvesting before year end",
                "Review portfolio for tax-efficient rebalancing",
                "Utilize annual LTCG exemption limit strategically"
            ]
        }
        
        return annual_estimate
    
    def _calculate_quarterly_estimates(self, tax_analysis: Dict) -> List[Dict]:
        """Calculate quarterly tax estimates"""
        
        total_tax = tax_analysis["tax_liability"]["total_tax"]
        quarterly_tax = total_tax / 4
        
        quarters = []
        for i in range(4):
            quarter_end = date.today().replace(month=(i+1)*3, day=1) + timedelta(days=31)
            quarter_end = quarter_end.replace(day=1) - timedelta(days=1)  # Last day of quarter
            
            quarters.append({
                "quarter": f"Q{i+1}",
                "due_date": quarter_end.isoformat(),
                "estimated_tax": float(quarterly_tax),
                "payment_due": float(quarterly_tax * Decimal('0.25'))  # 25% of annual tax
            })
        
        return quarters
    
    def _calculate_advance_tax(self, tax_analysis: Dict, profile: UserProfile) -> Dict:
        """Calculate advance tax requirements"""
        
        annual_tax_liability = tax_analysis["tax_liability"]["total_tax"]
        
        if annual_tax_liability < 10000:
            return {
                "required": False,
                "reason": "Annual tax liability below ₹10,000 threshold"
            }
        
        advance_tax_schedule = [
            {"installment": 1, "due_date": "2024-06-15", "percentage": 15},
            {"installment": 2, "due_date": "2024-09-15", "percentage": 45},
            {"installment": 3, "due_date": "2024-12-15", "percentage": 75},
            {"installment": 4, "due_date": "2025-03-15", "percentage": 100}
        ]
        
        for installment in advance_tax_schedule:
            installment["amount"] = float(annual_tax_liability * Decimal(str(installment["percentage"] / 100)))
        
        return {
            "required": True,
            "annual_liability": float(annual_tax_liability),
            "installments": advance_tax_schedule,
            "next_due_installment": self._get_next_due_installment(advance_tax_schedule)
        }
    
    def _get_next_due_installment(self, schedule: List[Dict]) -> Dict:
        """Get the next due advance tax installment"""
        
        current_date = date.today()
        
        for installment in schedule:
            due_date = datetime.strptime(installment["due_date"], "%Y-%m-%d").date()
            if due_date >= current_date:
                return installment
        
        return None  # All installments are past due