from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Literal, Any, Union
from datetime import date
from enum import Enum

# Enhanced enums for better type safety
class EmploymentStatus(str, Enum):
    STUDENT = "student"
    WORKING_PROFESSIONAL = "working_professional" 
    SELF_EMPLOYED = "self_employed"
    RETIRED = "retired"
    UNEMPLOYED = "unemployed"
    HOMEMAKER = "homemaker"

class LocationType(str, Enum):
    METRO = "metro"
    TIER_1 = "tier_1"
    TIER_2 = "tier_2" 
    TOWN = "town"
    RURAL = "rural"

class InvestmentExperience(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class RiskAppetite(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

class SavingHabit(str, Enum):
    DISCIPLINED = "disciplined"
    OCCASIONAL = "occasional"
    INCONSISTENT = "inconsistent"
    NONE = "none"

class MarketReaction(str, Enum):
    PANIC_SELL = "panic_sell"
    HOLD = "hold"
    BUY_MORE = "buy_more"
    SEEK_ADVICE = "seek_advice"
    IGNORE = "ignore"

class AssetType(str, Enum):
    MUTUAL_FUNDS = "mutual_funds"
    ETFS = "etfs"
    STOCKS = "stocks"
    FD = "fd"
    GOLD = "gold"
    REIT = "reit"
    BONDS = "bonds"
    PPF = "ppf"
    EPF = "epf"
    NSC = "nsc"
    CRYPTOCURRENCY = "cryptocurrency"
    REAL_ESTATE = "real_estate"

class InvestmentGoal(str, Enum):
    EMERGENCY_FUND = "emergency_fund"
    WEDDING = "wedding"
    HOUSE = "house"
    CHILD_EDUCATION = "child_education"
    RETIREMENT = "retirement"
    WEALTH_GROWTH = "wealth_growth"
    VACATION = "vacation"
    CAR = "car"
    EARLY_RETIREMENT = "early_retirement"
    DEBT_REPAYMENT = "debt_repayment"
    MEDICAL_EXPENSES = "medical_expenses"
    BUSINESS_STARTUP = "business_startup"
    LUXURY_PURCHASE = "luxury_purchase"

class InvestmentFrequency(str, Enum):
    MONTHLY_SIP = "monthly_sip"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    LUMPSUM = "lumpsum"
    AD_HOC = "ad_hoc"
    WEEKLY = "weekly"

class GoalPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class UserProfile(BaseModel):
    # Basic Demographics
    age: int = Field(..., ge=18, le=100, description="Age of the investor")
    income: float = Field(..., gt=0, description="Annual income in INR")
    employment_status: EmploymentStatus
    location: LocationType
    user_id: Optional[int] = None 
    # Personal Details (optional for comprehensive profiling)
    name: Optional[str] = Field(None, description="Full name of the user")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    gender: Optional[Literal["male", "female", "other", "prefer_not_to_say"]] = None
    marital_status: Optional[Literal["single", "married", "divorced", "widowed"]] = None
    
    # Investment Experience & Risk Profile
    investment_experience: InvestmentExperience = Field(
        InvestmentExperience.BEGINNER, 
        description="Investment experience level"
    )
    
    risk_appetite: RiskAppetite
    saving_habit: SavingHabit
    market_reactions: MarketReaction
    preferred_assets: List[AssetType] = Field(default_factory=list)
    
    # Risk Assessment Questions (enhanced)
    risk_tolerance_score: Optional[int] = Field(None, ge=0, le=100, description="Granular risk score")
    loss_comfort_level: Optional[float] = Field(None, description="Max % loss they can handle")
    investment_knowledge_score: Optional[int] = Field(None, ge=0, le=10, description="Self-assessed knowledge score")
    
    # Investment Goals & Timeline
    investment_goal: InvestmentGoal
    goal_amount: Optional[float] = Field(None, description="Target amount for goal")
    goal_timeline_years: int = Field(..., ge=1, le=50, description="Investment timeline in years")
    goal_priority: GoalPriority = Field(GoalPriority.MEDIUM)
    
    # Secondary Goals (for comprehensive planning)
    secondary_goals: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Additional financial goals")
    
    # Investment Preferences
    preference: Optional[str] = Field(None, description="Preferences like ESG, tax-saving, shariah, etc.")
    esg_preference: Optional[bool] = Field(False, description="Environmental, Social, Governance investing preference")
    tax_saving_priority: Optional[bool] = Field(False, description="Tax saving is a priority")
    shariah_compliant: Optional[bool] = Field(False, description="Requires Shariah compliant investments")
    
    # Liquidity & Frequency Preferences
    need_liquidity: bool = Field(False, description="Needs high liquidity")
    expected_large_expense: Optional[bool] = Field(False, description="Expecting large expenses soon")
    
    investment_frequency: InvestmentFrequency = Field(
        InvestmentFrequency.MONTHLY_SIP,
        description="Preferred investment frequency"
    )
    
    allow_auto_invest: bool = Field(False, description="Allow automatic investment")
    auto_increase_sip: Optional[bool] = Field(False, description="Auto increase SIP annually")
    
    # Financial Situation
    monthly_expenses: Optional[float] = Field(None, gt=0, description="Monthly expenses for emergency fund calculation")
    existing_emergency_fund: Optional[float] = Field(0, ge=0, description="Current emergency fund amount")
    other_income_sources: Optional[float] = Field(0, ge=0, description="Income from other sources")
    debt_obligations: Optional[float] = Field(0, ge=0, description="Monthly debt payments (EMIs)")
    
    # Current Investments & Assets
    current_investments: Dict[str, float] = Field(
        default_factory=lambda: {"equity": 0, "debt": 0, "gold": 0, "real_estate": 0, "cash": 0}
    )
    total_assets: Optional[float] = Field(None, description="Total current assets")
    total_liabilities: Optional[float] = Field(None, description="Total current liabilities")
    
    # Family & Dependents
    dependents: int = Field(0, ge=0, description="Number of dependents")
    spouse_income: Optional[float] = Field(0, description="Spouse annual income")
    children_count: Optional[int] = Field(0, description="Number of children")
    parent_support: Optional[bool] = Field(False, description="Supporting parents financially")
    
    # Health & Insurance
    health_conditions: List[str] = Field(default_factory=list, description="Any health conditions affecting finances")
    life_insurance_coverage: Optional[float] = Field(0, description="Current life insurance coverage")
    health_insurance_coverage: Optional[float] = Field(0, description="Current health insurance coverage")
    
    # Advanced Preferences
    excluded_sectors: List[str] = Field(default_factory=list, description="Sectors to avoid")
    preferred_fund_houses: Optional[List[str]] = Field(default_factory=list, description="Preferred AMCs")
    
    # Behavioral Finance Factors
    investment_style: Optional[Literal["conservative", "moderate", "aggressive", "very_aggressive"]] = None
    decision_making_style: Optional[Literal["analytical", "intuitive", "seek_advice", "follow_trends"]] = None
    information_consumption: Optional[List[Literal["news", "research_reports", "social_media", "advisor", "friends"]]] = Field(default_factory=list)
    
    # Technology & Digital Preferences
    app_usage_comfort: Optional[Literal["very_comfortable", "comfortable", "somewhat_comfortable", "not_comfortable"]] = None
    digital_investment_preference: Optional[bool] = Field(True, description="Prefers digital investment platforms")
    
    # Additional Metadata
    form_completion_date: Optional[date] = Field(None, description="When the profile was completed")
    profile_version: Optional[str] = Field("1.0", description="Profile schema version")
    data_source: Optional[str] = Field("web_form", description="Source of profile data")
    
    # Custom fields for flexibility
    custom_fields: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional custom data")
    
    @validator('goal_amount')
    def validate_goal_amount(cls, v, values):
        """Ensure goal amount is reasonable"""
        if v is not None and v <= 0:
            raise ValueError('Goal amount must be positive')
        return v
    
    @validator('investment_frequency')
    def validate_frequency_with_goal(cls, v, values):
        """Validate frequency makes sense for timeline"""
        timeline = values.get('goal_timeline_years', 1)
        if v == InvestmentFrequency.LUMPSUM and timeline > 10:
            pass  # Could add warning logic here
        return v
    
    @validator('email')
    def validate_email(cls, v):
        """Basic email validation"""
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v
    
    @validator('age')
    def validate_retirement_goal_age(cls, v, values):
        """Validate retirement goal with age"""
        goal = values.get('investment_goal')
        if goal in [InvestmentGoal.RETIREMENT, InvestmentGoal.EARLY_RETIREMENT] and v >= 55:
            pass  # Could add specific logic for older investors
        return v
    
    @property
    def disposable_income(self) -> float:
        """Calculate disposable income for investment capacity"""
        monthly_income = self.income / 12
        monthly_debt = self.debt_obligations or 0
        estimated_expenses = self.monthly_expenses or (monthly_income * 0.7)
        spouse_contrib = (self.spouse_income or 0) / 12 * 0.3  # Assume 30% contribution
        return max(0, monthly_income + spouse_contrib - estimated_expenses - monthly_debt)
    
    @property
    def emergency_fund_needed(self) -> float:
        """Calculate required emergency fund"""
        monthly_expenses = self.monthly_expenses or (self.income / 12 * 0.7)
        multiplier = {
            EmploymentStatus.STUDENT: 3,
            EmploymentStatus.WORKING_PROFESSIONAL: 6,
            EmploymentStatus.SELF_EMPLOYED: 12,
            EmploymentStatus.RETIRED: 9,
            EmploymentStatus.UNEMPLOYED: 12,
            EmploymentStatus.HOMEMAKER: 6
        }.get(self.employment_status, 6)
        return monthly_expenses * multiplier
    
    @property
    def emergency_fund_gap(self) -> float:
        """Gap in emergency fund"""
        return max(0, self.emergency_fund_needed - (self.existing_emergency_fund or 0))
    
    @property
    def net_worth(self) -> float:
        """Calculate net worth"""
        assets = self.total_assets or sum(self.current_investments.values())
        liabilities = self.total_liabilities or 0
        return assets - liabilities
    
    @property
    def debt_to_income_ratio(self) -> float:
        """Calculate debt to income ratio"""
        annual_debt = (self.debt_obligations or 0) * 12
        return (annual_debt / self.income) * 100 if self.income else 0
    
    @property
    def investment_capacity_percentage(self) -> float:
        """What percentage of income can be invested"""
        return (self.disposable_income * 12 / self.income) * 100
    
    # Utility methods for better data handling
    def get_risk_score(self) -> int:
        """Get comprehensive risk score"""
        if self.risk_tolerance_score:
            return self.risk_tolerance_score
        
        # Calculate based on risk appetite and other factors
        base_scores = {
            RiskAppetite.VERY_LOW: 10,
            RiskAppetite.LOW: 25,
            RiskAppetite.MEDIUM: 50,
            RiskAppetite.HIGH: 75,
            RiskAppetite.VERY_HIGH: 90
        }
        
        score = base_scores.get(self.risk_appetite, 50)
        
        # Adjust based on age (younger = higher risk tolerance)
        if self.age < 30:
            score += 10
        elif self.age > 50:
            score -= 10
            
        # Adjust based on experience
        if self.investment_experience == InvestmentExperience.BEGINNER:
            score -= 15
        elif self.investment_experience == InvestmentExperience.EXPERT:
            score += 15
            
        return max(0, min(100, score))
    
    def to_dict_for_api(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for API consumption"""
        return self.dict(exclude_none=True, by_alias=True)


# ===== FIXED: RecommendedFund with better fund_code handling =====
class RecommendedFund(BaseModel):
    code: str
    name: str
    category: str
    risk_level: str
    aum: float
    nav: float
    expense_ratio: float
    rating: Optional[int] = None
    risk_adjusted_return: Optional[float] = None
    return_5y: Optional[float] = None
    suitability: Optional[Dict[str, bool]] = Field(default_factory=dict)
    
    # Optional fields
    min_sip_amount: Optional[float] = Field(None, description="Minimum SIP amount")
    fund_manager: Optional[str] = Field(None, description="Fund manager name")
    inception_date: Optional[date] = Field(None, description="Fund launch date")
    benchmark: Optional[str] = Field(None, description="Benchmark index")
    
    # ===== FIXED: Make fund_code computed property instead of required field =====
    @property
    def fund_code(self) -> str:
        """Always return code as fund_code"""
        return self.code
    
    # ===== FIXED: Add dict method that includes fund_code =====
    def dict(self, **kwargs):
        """Override dict to include fund_code"""
        result = super().dict(**kwargs)
        result['fund_code'] = self.code
        return result
    
    def model_dump(self, **kwargs):
        """Override model_dump to include fund_code for Pydantic v2"""
        result = super().model_dump(**kwargs)
        result['fund_code'] = self.code
        return result


class InvestmentOptimization(BaseModel):
    """Investment frequency optimization"""
    investment_type: Literal["monthly_sip", "quarterly_sip", "lumpsum", "hybrid"]
    amount: float
    frequency: Optional[str] = None
    note: Optional[str] = None
    step_up_suggestion: Optional[Dict[str, Any]] = None


class AffordabilityCheck(BaseModel):
    """Affordability validation"""
    affordability_issue: bool
    suggested_sip: float
    original_sip: Optional[float] = None
    timeline_multiplier: Optional[float] = None
    warning: Optional[str] = None
    max_affordable_amount: Optional[float] = None
    investment_ratio_percent: Optional[float] = None


class TaxOptimization(BaseModel):
    """Tax optimization insights"""
    tax_bracket: str
    elss_recommendation: Optional[float] = None
    ltcg_benefit_applicable: bool = False
    tax_saving_amount: Optional[float] = None
    notes: List[str] = Field(default_factory=list)


class PortfolioRecommendation(BaseModel):
    recommended_allocation: Dict[str, float]
    target_corpus: float
    suggested_sip: float
    recommended_funds: Dict[str, List[RecommendedFund]]
    notes: List[str]
    user_id: Optional[int] = None 

    
    # Enhanced fields
    investment_optimization: Optional[InvestmentOptimization] = None
    affordability_check: Optional[AffordabilityCheck] = None
    tax_optimization: Optional[TaxOptimization] = None
    emergency_fund_status: Optional[Dict[str, Any]] = None
    
    # LLM and UI fields
    flags: Optional[List[str]] = Field(default_factory=list)
    llm_feedback: Optional[str] = None
    story: Optional[str] = None
    
    # Risk and performance metrics
    expected_return_percent: Optional[float] = None
    portfolio_risk_score: Optional[int] = Field(None, ge=0, le=100)
    diversification_score: Optional[int] = Field(None, ge=0, le=100)
    alerts: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Monitoring alerts")

    @property
    def investment_ratio(self) -> Optional[float]:
        """Calculate investment to income ratio"""
        if hasattr(self, '_profile_income') and self._profile_income:
            return (self.suggested_sip * 12 / self._profile_income) * 100
        return None


class Holding(BaseModel):
    name: str
    symbol: str
    asset_type: Literal["stock", "mutual_fund", "etf", "bond", "gold"]
    quantity: float = Field(..., gt=0)
    avg_buy_price: float = Field(..., gt=0)
    current_price: float = Field(..., gt=0)
    buy_date: date
    sector: str = Field(default="unknown")
    
    # Auto-calculated fields
    current_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_percent: Optional[float] = None
    
    @validator('current_value', always=True)
    def calculate_current_value(cls, v, values):
        """Auto-calculate current value"""
        quantity = values.get('quantity')
        current_price = values.get('current_price')
        if quantity and current_price:
            return quantity * current_price
        return v
    
    @validator('unrealized_pnl', always=True)
    def calculate_pnl(cls, v, values):
        """Auto-calculate P&L"""
        quantity = values.get('quantity')
        avg_buy_price = values.get('avg_buy_price')
        current_price = values.get('current_price')
        if all([quantity, avg_buy_price, current_price]):
            return quantity * (current_price - avg_buy_price)
        return v
    
    @validator('unrealized_pnl_percent', always=True)
    def calculate_pnl_percent(cls, v, values):
        """Auto-calculate P&L percentage"""
        avg_buy_price = values.get('avg_buy_price')
        current_price = values.get('current_price')
        if avg_buy_price and current_price:
            return ((current_price - avg_buy_price) / avg_buy_price) * 100
        return v


class PortfolioAnalysisRequest(BaseModel):
    profile: UserProfile
    holdings: List[Holding]
    
    include_tax_analysis: bool = Field(True, description="Include tax optimization analysis")
    include_rebalancing: bool = Field(True, description="Include rebalancing suggestions")
    benchmark_comparison: Optional[str] = Field(None, description="Compare against benchmark")


# ===== FIXED: PortfolioAnalysisResponse =====
class PortfolioAnalysisResponse(BaseModel):
    current_allocation: Dict[str, float]
    target_allocation: Dict[str, float]
    rebalancing_required: bool
    rebalancing_suggestions: List[str] = Field(default_factory=list)
    portfolio_health_score: int = Field(..., ge=0, le=100)
    risk_analysis: Dict[str, Any] = Field(default_factory=dict)
    performance_analysis: Dict[str, Any] = Field(default_factory=dict)
    recommendations: PortfolioRecommendation
    
    # Additional fields that might be returned
    verdicts: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    alerts: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


# Utility function to handle flexible profile data input
def create_user_profile_from_form_data(form_data: Dict[str, Any]) -> UserProfile:
    """
    Create UserProfile from flexible form data, handling missing fields gracefully
    """
    # Map any alternative field names to expected names
    field_mapping = {
        'annual_income': 'income',
        'job_status': 'employment_status',
        'city_type': 'location',
        'risk_level': 'risk_appetite',
        'investment_timeline': 'goal_timeline_years',
        'goal_type': 'investment_goal',
        'target_amount': 'goal_amount'
    }
    
    # Apply field mapping
    mapped_data = {}
    for key, value in form_data.items():
        mapped_key = field_mapping.get(key, key)
        mapped_data[mapped_key] = value
    
    # Ensure required fields have defaults
    defaults = {
        'age': 25,
        'income': 500000,
        'employment_status': 'working_professional',
        'location': 'metro',
        'investment_experience': 'beginner',
        'risk_appetite': 'medium',
        'saving_habit': 'occasional',
        'market_reactions': 'hold',
        'investment_goal': 'wealth_growth',
        'goal_timeline_years': 5,
        'investment_frequency': 'monthly_sip'
    }
    
    # Fill in missing required fields with defaults
    for key, default_value in defaults.items():
        if key not in mapped_data or mapped_data[key] is None:
            mapped_data[key] = default_value
    
    # Handle enum conversion
    enum_fields = {
        'employment_status': EmploymentStatus,
        'location': LocationType,
        'investment_experience': InvestmentExperience,
        'risk_appetite': RiskAppetite,
        'saving_habit': SavingHabit,
        'market_reactions': MarketReaction,
        'investment_goal': InvestmentGoal,
        'investment_frequency': InvestmentFrequency,
        'goal_priority': GoalPriority
    }
    
    for field, enum_class in enum_fields.items():
        if field in mapped_data and isinstance(mapped_data[field], str):
            try:
                mapped_data[field] = enum_class(mapped_data[field])
            except ValueError:
                # If enum value is invalid, use first enum value as default
                mapped_data[field] = list(enum_class)[0]
    
    return UserProfile(**mapped_data)