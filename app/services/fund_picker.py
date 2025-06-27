from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, case, desc, func
from app.models.mutual_fund import MutualFund
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

ASSET_CLASS_MAPPING = {
    "equity": [
        ("Large Cap", 0.9),
        ("Flexi Cap", 0.85),
        ("Index", 0.8),
        ("ELSS", 0.75),
        ("Mid Cap", 0.7),
        ("Small Cap", 0.6),
        ("Sectoral", 0.5),
        ("Thematic", 0.45)
    ],
    "debt": [
        ("Liquid", 0.95),
        ("Overnight", 0.9),
        ("Short Duration", 0.85),
        ("Corporate Bond", 0.8),
        ("Banking", 0.75),
        ("Gilt", 0.7),
        ("Credit Risk", 0.6),
        ("Long Duration", 0.5)
    ],
    "gold": [
        ("Gold", 1.0)
    ]
}

class FundFilter:
    """Encapsulates filter logic with priority scoring"""
    
    def __init__(self, condition, priority: int, name: str):
        self.condition = condition
        self.priority = priority  # Higher = more important
        self.name = name

def build_filter_chain(
    asset_class: str,
    risk_level: str,
    goal_type: Optional[str],
    timeline: Optional[int],
    preference: Optional[str],
    allowed_assets: Optional[List[str]],
    experience_level: Optional[str]
) -> List[FundFilter]:
    """Build prioritized filter chain"""
    
    filters = []
    
    # Priority 1: Asset class (mandatory)
    category_mappings = ASSET_CLASS_MAPPING.get(asset_class, [])
    if category_mappings:
        category_filters = []
        for category, _ in category_mappings:
            category_filters.append(MutualFund.scheme_category.ilike(f"%{category}%"))
        
        filters.append(FundFilter(
            condition=or_(*category_filters),
            priority=10,
            name="asset_class"
        ))
    
    # Priority 2: Basic safety (mandatory)
    filters.append(FundFilter(
        condition=and_(
            MutualFund.nav > 0,
            MutualFund.aum > 50  # Minimum viable AUM
        ),
        priority=9,
        name="basic_safety"
    ))
    
    # Priority 3: Goal-specific (high priority)
    if goal_type:
        if goal_type == "emergency_fund":
            filters.append(FundFilter(
                condition=or_(
                    MutualFund.scheme_category.ilike("%Liquid%"),
                    MutualFund.scheme_category.ilike("%Overnight%")
                ),
                priority=8,
                name="emergency_liquidity"
            ))
        elif goal_type == "retirement":
            filters.append(FundFilter(
                condition=MutualFund.exit_load <= 1.0,
                priority=7,
                name="retirement_suitable"
            ))
    
    # Priority 4: Timeline risk (medium priority)
    if timeline is not None:
        if timeline < 3:
            filters.append(FundFilter(
                condition=MutualFund.standard_deviation < 12,
                priority=6,
                name="short_term_stability"
            ))
        elif timeline > 7 and asset_class == "equity":
            filters.append(FundFilter(
                condition=or_(
                    MutualFund.return_5y > 8,
                    MutualFund.return_5y.is_(None)
                ),
                priority=6,
                name="long_term_growth"
            ))
    
    # Priority 5: Risk alignment (medium priority)
    risk_mapping = {
        "low": ["low", "low to moderate"],
        "moderate": ["moderate", "low to moderate", "moderately high"],
        "high": ["high", "very high", "moderately high"]
    }
    if risk_level in risk_mapping:
        filters.append(FundFilter(
            condition=MutualFund.risk_level.in_(risk_mapping[risk_level]),
            priority=5,
            name="risk_alignment"
        ))
    
    # Priority 6: Experience level (lower priority)
    if experience_level == "beginner":
        filters.append(FundFilter(
            condition=or_(
                MutualFund.scheme_category.ilike("%Large Cap%"),
                MutualFund.scheme_category.ilike("%Index%"),
                MutualFund.scheme_category.ilike("%Liquid%")
            ),
            priority=4,
            name="beginner_friendly"
        ))
    
    # Priority 7: Preferences (lowest priority)
    if preference:
        pref_conditions = []
        if "esg" in preference.lower():
            pref_conditions.append(
                or_(
                    MutualFund.name.ilike("%ESG%"),
                    MutualFund.name.ilike("%Sustainable%")
                )
            )
        if "tax" in preference.lower():
            pref_conditions.append(
                MutualFund.scheme_category.ilike("%ELSS%")
            )
        
        if pref_conditions:
            filters.append(FundFilter(
                condition=or_(*pref_conditions),
                priority=3,
                name="preferences"
            ))
    
    return sorted(filters, key=lambda x: x.priority, reverse=True)

def pick_funds(
    db: Session,
    asset_class: str,
    risk_level: str = "moderate",
    goal_type: Optional[str] = None,
    timeline: Optional[int] = None,
    preference: Optional[str] = None,
    allowed_assets: Optional[List[str]] = None,
    experience_level: Optional[str] = None,
    limit: int = 5
) -> List[Dict]:
    """
    Production-grade fund picker with adaptive filtering
    """
    
    try:
        # Build filter chain
        filter_chain = build_filter_chain(
            asset_class, risk_level, goal_type, timeline, 
            preference, allowed_assets, experience_level
        )
        
        if not filter_chain:
            logger.warning(f"No filters built for asset_class: {asset_class}")
            return []
        
        # Start with base query
        base_query = db.query(MutualFund)
        
        # Apply filters in priority order, but ensure minimum results
        applied_filters = []
        current_query = base_query
        min_results = max(limit * 2, 10)  # Ensure we have options
        
        for filter_obj in filter_chain:
            test_query = current_query.filter(filter_obj.condition)
            count = test_query.count()
            
            logger.debug(f"Filter '{filter_obj.name}' would return {count} results")
            
            # Apply filter if it doesn't reduce results below minimum
            # OR if it's a mandatory filter (priority >= 9)
            if count >= min_results or filter_obj.priority >= 9:
                current_query = test_query
                applied_filters.append(filter_obj.name)
                logger.debug(f"Applied filter: {filter_obj.name}")
            else:
                logger.debug(f"Skipped filter: {filter_obj.name} (would reduce to {count})")
                
                # For low-priority filters, if we have very few results, skip entirely
                if count == 0 and filter_obj.priority < 5:
                    continue
                # For medium-priority filters, apply if we have at least some results
                elif count > 0 and filter_obj.priority >= 5:
                    current_query = test_query
                    applied_filters.append(f"{filter_obj.name}_relaxed")
        
        # Build priority scoring for ranking
        category_mappings = ASSET_CLASS_MAPPING.get(asset_class, [])
        priority_cases = []
        for category, priority in category_mappings:
            priority_cases.append((
                MutualFund.scheme_category.ilike(f"%{category}%"), 
                priority
            ))
        
        priority_score = case(*priority_cases, else_=0.1) if priority_cases else 0.5
        
        # Enhanced ranking with multiple criteria
        final_query = current_query.order_by(
            # Primary: Category priority
            priority_score.desc(),
            # Secondary: Performance (handle nulls)
            case(
                (MutualFund.risk_adjusted_return.is_(None), 0),
                else_=MutualFund.risk_adjusted_return
            ).desc(),
            # Tertiary: Fund size (stability)
            MutualFund.aum.desc(),
            # Quaternary: Cost efficiency
            case(
                (MutualFund.expense_ratio.is_(None), 999),
                else_=MutualFund.expense_ratio
            ).asc(),
            # Final: Rating
            case(
                (MutualFund.rating.is_(None), 0),
                else_=MutualFund.rating
            ).desc()
        ).limit(limit)
        
        funds = final_query.all()
        
        logger.info(f"Fund search for {asset_class}: Applied filters {applied_filters}, returned {len(funds)} funds")
        
        # Format results
        results = []
        for fund in funds:
            fund_data = {
                "code": fund.code,
                "name": fund.name,
                "category": fund.scheme_category,
                "risk_level": fund.risk_level,
                "aum": fund.aum,
                "nav": fund.nav,
                "expense_ratio": fund.expense_ratio,
                "rating": fund.rating,
                "risk_adjusted_return": fund.risk_adjusted_return,
                "return_5y": fund.return_5y,
                "suitability": _analyze_suitability(fund, goal_type, timeline, preference),
                "selection_score": _calculate_selection_score(fund, applied_filters)
            }
            results.append(fund_data)
        
        # Final safety check
        if not results:
            logger.warning(f"No funds found for {asset_class} - using emergency fallback")
            return get_emergency_fallback_funds(db, asset_class, limit)
        
        return results
    
    except Exception as e:
        logger.error(f"Error in fund selection for {asset_class}: {str(e)}")
        return get_emergency_fallback_funds(db, asset_class, limit)

def _analyze_suitability(
    fund: MutualFund, 
    goal_type: Optional[str], 
    timeline: Optional[int], 
    preference: Optional[str]
) -> Dict:
    """Analyze fund suitability for user profile"""
    suitability = {}
    
    # Goal suitability
    if goal_type == "retirement" and fund.expense_ratio and fund.expense_ratio < 0.5:
        suitability["low_cost"] = True
    
    # Timeline suitability
    if timeline and timeline > 10 and fund.return_5y and fund.return_5y > 12:
        suitability["long_term_performer"] = True
    
    # Preference match
    if preference and fund.name:
        if "esg" in preference.lower() and ("ESG" in fund.name or "Sustainable" in fund.name):
            suitability["esg_aligned"] = True
        if "tax" in preference.lower() and "ELSS" in (fund.scheme_category or ""):
            suitability["tax_efficient"] = True
    
    # Quality indicators
    if fund.rating and fund.rating >= 4:
        suitability["high_rated"] = True
    if fund.aum and fund.aum > 5000:
        suitability["large_fund"] = True
    
    return suitability

def _calculate_selection_score(fund: MutualFund, applied_filters: List[str]) -> float:
    """Calculate a selection confidence score"""
    score = 0.5  # Base score
    
    # Bonus for meeting strict criteria
    if "risk_alignment" in applied_filters:
        score += 0.1
    if "preferences" in applied_filters:
        score += 0.1
    if "beginner_friendly" in applied_filters:
        score += 0.1
    
    # Quality bonuses
    if fund.rating and fund.rating >= 4:
        score += 0.15
    if fund.aum and fund.aum > 1000:
        score += 0.1
    if fund.risk_adjusted_return and fund.risk_adjusted_return > 10:
        score += 0.1
    
    return min(1.0, score)

def get_emergency_fallback_funds(db: Session, asset_class: str, limit: int) -> List[Dict]:
    """Emergency fallback - guaranteed to return something"""
    logger.warning(f"Using emergency fallback for {asset_class}")
    
    # Ultra-simple query
    query = db.query(MutualFund).filter(
        MutualFund.nav > 0
    )
    
    # Basic asset class matching
    if asset_class == "equity":
        query = query.filter(
            or_(
                MutualFund.scheme_category.ilike("%Large Cap%"),
                MutualFund.scheme_category.ilike("%Equity%")
            )
        )
    elif asset_class == "debt":
        query = query.filter(
            or_(
                MutualFund.scheme_category.ilike("%Liquid%"),
                MutualFund.scheme_category.ilike("%Debt%")
            )
        )
    elif asset_class == "gold":
        query = query.filter(MutualFund.scheme_category.ilike("%Gold%"))
    
    funds = query.order_by(
        MutualFund.aum.desc(),
        MutualFund.rating.desc()
    ).limit(max(2, limit//2)).all()
    
    return [{
        "code": fund.code,
        "name": fund.name,
        "category": fund.scheme_category,
        "risk_level": fund.risk_level,
        "aum": fund.aum,
        "nav": fund.nav,
        "expense_ratio": fund.expense_ratio,
        "rating": fund.rating,
        "risk_adjusted_return": fund.risk_adjusted_return,
        "return_5y": fund.return_5y,
        "suitability": {"emergency_pick": True},
        "selection_score": 0.3
    } for fund in funds]