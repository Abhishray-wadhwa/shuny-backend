from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging
import traceback
from fastapi import Query
from typing import Any,Optional,Dict
from app.services.fund_picker import pick_funds
from app.models.mutual_fund import MutualFund  # Assuming this is your ORM model
from app.services.fund_suitability import FundSuitabilityEngine
from app.config import SessionLocal
from app.models.portfolio import (
    UserProfile,
    PortfolioRecommendation,
    PortfolioAnalysisRequest,
)
from app.services.recommendation_engine import AdvancedPortfolioModel
from app.services.llm_review_service import validate_and_explain_output
from app.services.flags import extract_flags
from app.services.llm_humanizer import generate_portfolio_story
from app.services.portfolio_analysis import EnhancedPortfolioAnalyzer
from app.services.monitoring_engine import MonitoringEngine
from app.services.holding_verdict_engine import HoldingVerdictEngine
from app.services.fund_suitability import FundSuitabilityEngine
from app.services.llm_review_service import validate_and_explain_output
from app.services.llm_humanizer import generate_portfolio_story
from app.services.flags import extract_flags
from pydantic import BaseModel
from app.models.portfolio import UserProfile

router = APIRouter()
logger = logging.getLogger(__name__)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def safe_convert_fund_to_dict(fund):
    """Safely convert a RecommendedFund to dictionary with guaranteed fund_code"""
    try:
        if fund is None:
            return {}
        
        # If it's already a dict, ensure fund_code exists
        if isinstance(fund, dict):
            result = fund.copy()
            if 'fund_code' not in result and 'code' in result:
                result['fund_code'] = result['code']
            elif 'fund_code' not in result:
                result['fund_code'] = result.get('name', 'UNKNOWN_CODE')
            return result
        
        # If it has a dict() method (Pydantic v1)
        if hasattr(fund, 'dict') and callable(getattr(fund, 'dict')):
            result = fund.dict()
            if 'fund_code' not in result and 'code' in result:
                result['fund_code'] = result['code']
            elif 'fund_code' not in result:
                result['fund_code'] = result.get('name', 'UNKNOWN_CODE')
            return result
        
        # If it has a model_dump() method (Pydantic v2)
        if hasattr(fund, 'model_dump') and callable(getattr(fund, 'model_dump')):
            result = fund.model_dump()
            if 'fund_code' not in result and 'code' in result:
                result['fund_code'] = result['code']
            elif 'fund_code' not in result:
                result['fund_code'] = result.get('name', 'UNKNOWN_CODE')
            return result
        
        # Manual conversion for custom objects
        if hasattr(fund, '__dict__'):
            result = fund.__dict__.copy()
            if 'fund_code' not in result and 'code' in result:
                result['fund_code'] = result['code']
            elif 'fund_code' not in result:
                result['fund_code'] = result.get('name', 'UNKNOWN_CODE')
            return result
        
        # Fallback: convert to string representation
        logger.warning(f"Could not convert fund to dict: {type(fund)}")
        return {
            "error": f"Could not convert fund type: {type(fund)}",
            "fund_code": "UNKNOWN_CODE"
        }
        
    except Exception as e:
        logger.error(f"Error converting fund to dict: {e}")
        return {
            "error": f"Conversion error: {str(e)}",
            "fund_code": "UNKNOWN_CODE"
        }


def convert_funds_to_dict(recommended_funds):
    """Convert RecommendedFund objects to dictionaries for LLM processing"""
    if not recommended_funds:
        return {}
    
    converted_funds = {}
    
    try:
        for asset_class, funds in recommended_funds.items():
            converted_funds[asset_class] = []
            
            # Handle both list and single fund cases
            if isinstance(funds, list):
                for fund in funds:
                    fund_dict = safe_convert_fund_to_dict(fund)
                    # Double-check fund_code exists
                    if 'fund_code' not in fund_dict:
                        fund_dict['fund_code'] = fund_dict.get('code', 'UNKNOWN_CODE')
                    converted_funds[asset_class].append(fund_dict)
            else:
                # Single fund case
                fund_dict = safe_convert_fund_to_dict(funds)
                if 'fund_code' not in fund_dict:
                    fund_dict['fund_code'] = fund_dict.get('code', 'UNKNOWN_CODE')
                converted_funds[asset_class].append(fund_dict)
                
    except Exception as e:
        logger.error(f"Error in convert_funds_to_dict: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Return empty structure on error
        return {"equity": [], "debt": [], "gold": []}
    
    return converted_funds


def create_recommended_fund_with_code(fund_data: dict) -> dict:
    """Helper to ensure fund_code is properly set in fund data"""
    if isinstance(fund_data, dict):
        result = fund_data.copy()
        # Ensure fund_code is present
        if 'fund_code' not in result and 'code' in result:
            result['fund_code'] = result['code']
        elif 'fund_code' not in result:
            result['fund_code'] = result.get('name', 'UNKNOWN_CODE')
        return result
    return fund_data


def safe_dict_conversion(obj):
    """Safely convert any object to dictionary - handles both Pydantic v1 and v2"""
    try:
        if obj is None:
            return {}
        
        if isinstance(obj, dict):
            return obj
        
        # Try Pydantic v2 first (model_dump)
        if hasattr(obj, 'model_dump') and callable(getattr(obj, 'model_dump')):
            result = obj.model_dump()
            if 'recommended_funds' in result:
                result['recommended_funds'] = convert_funds_to_dict(result['recommended_funds'])
            return result
        
        # Fall back to Pydantic v1 (dict)
        if hasattr(obj, 'dict') and callable(getattr(obj, 'dict')):
            result = obj.dict()
            if 'recommended_funds' in result:
                result['recommended_funds'] = convert_funds_to_dict(result['recommended_funds'])
            return result
        
        # Fallback to __dict__
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        
        return {"error": f"Could not convert {type(obj)} to dict"}
        
    except Exception as e:
        logger.error(f"Error in safe_dict_conversion: {e}")
        return {"error": f"Conversion failed: {str(e)}"}

# 🔹 Portfolio Recommendation Endpoint
@router.post("/recommend", response_model=PortfolioRecommendation)
def get_recommendation(profile: UserProfile, db: Session = Depends(get_db)):
    try:
        logger.info("🔍 Running AdvancedPortfolioModel for user profile...")
        
        # Step 1: Core engine logic - This returns a PortfolioRecommendation object
        recommendation_result = AdvancedPortfolioModel.recommend_portfolio(profile, db)

        if not recommendation_result:
            raise HTTPException(status_code=500, detail="Failed to generate recommendation")

        # Step 2: Safely convert to dict for LLM processing
        logger.info("Converting recommendation to dict format...")
        try:
            recommendation_dict = safe_dict_conversion(recommendation_result)
            logger.info("✅ Recommendation conversion completed successfully")
        except Exception as e:
            logger.error(f"❌ Recommendation conversion failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to process recommendation")

        # Step 3: LLM validation + humanization
        human_summary = "⚠️ LLM validation unavailable"
        try:
            llm_result = validate_and_explain_output(recommendation_dict)
            human_summary = llm_result.get("llm_feedback", human_summary)
            logger.info("✅ LLM validation completed")
        except Exception as e:
            logger.warning(f"⚠️ LLM validation failed: {e}")

        # Step 4: Generate flags for front-end
        flags = []
        try:
            flags = extract_flags(recommendation_dict)
            logger.info("✅ Flags extracted successfully")
        except Exception as e:
            logger.warning(f"⚠️ Flag extraction failed: {e}")

        # Step 5: Generate story summary
        story_summary = "⚠️ Story unavailable"
        try:
            story_result = generate_portfolio_story(recommendation_dict)
            story_summary = story_result.get("story", story_summary)
            logger.info("✅ Story generated successfully")
        except Exception as e:
            logger.warning(f"⚠️ Story generation failed: {e}")

        # Step 6: Alerts - Use the safe method and pass proper arguments
        alerts = []
        try:
            profile_dict = profile.dict() if hasattr(profile, 'dict') else profile

            # Fund-based alerts
            fund_alerts = MonitoringEngine.generate_alerts_safe(
                recommendation_result.recommended_funds,
                profile_dict
            )

            # Health alerts based on the entire recommendation structure
            recommendation_dict = safe_dict_conversion(recommendation_result)
            health_alerts = MonitoringEngine.check_recommendation_health(recommendation_dict)

            # Merge both alert lists
            alerts = fund_alerts + health_alerts

            logger.info("✅ All alerts generated successfully")
        except Exception as e:
            logger.warning(f"⚠️ Alert generation failed: {e}")

        logger.info("✅ Recommendation, story, flags, and alerts prepared.")

        # Step 7: Build response carefully
        try:
            # Get the base data from the original recommendation
            response_data = safe_dict_conversion(recommendation_result)
            
            # Add the additional fields
            response_data.update({
                "llm_feedback": human_summary,
                "flags": flags,
                "story": story_summary,
                "alerts": alerts
            })

            # Return the updated PortfolioRecommendation
            return PortfolioRecommendation(**response_data)
            
        except Exception as e:
            logger.error(f"Error building response: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail="Failed to build recommendation response")

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception("❌ Failed to generate recommendation.")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.post("/analyze/portfolio", response_model=Dict[str, Any])
def analyze_portfolio(
    data: PortfolioAnalysisRequest,
    db: Session = Depends(get_db)
):
    try:
        logger.info("🔍 Analyzing user portfolio...")

        # Step 1: Quantitative Analysis
        result = EnhancedPortfolioAnalyzer.analyze_comprehensive(data.holdings, data.profile, db)

        # Step 2: LLM Verdicts (Buy/Hold/Sell)
        try:
            verdicts = HoldingVerdictEngine.get_verdicts(data.holdings)
            result["verdicts"] = verdicts
            logger.info("✅ Step 2: LLM verdicts added.")
        except Exception as ve:
            logger.warning(f"⚠️ Could not generate LLM verdicts: {ve}")
            result["verdicts"] = []

        # Step 3: Alerts
        try:
            alerts = MonitoringEngine.generate_alerts_from_holdings(data.holdings)
            result["alerts"] = alerts
            logger.info("✅ Step 3: Monitoring alerts added.")
        except Exception as ae:
            logger.warning(f"⚠️ Could not generate monitoring alerts: {ae}")
            result["alerts"] = []

        # ===== FIXED: Ensure we return the expected structure =====
        return {
            "profile": data.profile.dict() if hasattr(data.profile, 'dict') else data.profile.model_dump(),
            "portfolio_analysis": result
        }

    except Exception as e:
        logger.exception("❌ Portfolio analysis failed.")
        raise HTTPException(status_code=500, detail=f"Portfolio analysis failed: {str(e)}")




# 🔹 Health Check Endpoint (Bonus)
@router.get("/health")
def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "service": "portfolio_recommendation_engine",
        "version": "1.0.0"
    }

@router.get("/funds/search")
def search_funds(
    asset_class: str = Query(..., description="equity, debt, gold"),
    keyword: Optional[str] = Query(None, description="Search fund by name"),
    goal_type: Optional[str] = None,
    timeline: Optional[int] = None,
    preference: Optional[str] = None,
    risk_level: str = "moderate",
    experience_level: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Search mutual funds with smart filtering logic.
    """
    try:
        # Get filtered, scored results
        results = pick_funds(
            db=db,
            asset_class=asset_class,
            risk_level=risk_level,
            goal_type=goal_type,
            timeline=timeline,
            preference=preference,
            experience_level=experience_level
        )

        # If keyword is provided, further filter by name
        if keyword:
            keyword_lower = keyword.lower()
            results = [r for r in results if keyword_lower in r["name"].lower()]

        # ===== FIXED: Ensure each result has fund_code =====
        for result in results:
            if isinstance(result, dict):
                if 'fund_code' not in result and 'code' in result:
                    result['fund_code'] = result['code']
                elif 'fund_code' not in result:
                    result['fund_code'] = result.get('name', 'UNKNOWN')

        return results
    except Exception as e:
        logger.error(f"❌ Fund search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fund search failed: {str(e)}")
@router.get("/funds/{code}")
def get_fund_by_code(code: str, db: Session = Depends(get_db)) -> Any:
    """
    Fetch a single fund by its code.
    """
    fund = db.query(MutualFund).filter(MutualFund.code == code).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    return {
        "fund_code": fund.code,  # ===== FIXED: Add fund_code field =====
        "code": fund.code,
        "name": fund.name,
        "category": fund.scheme_category,
        "risk_level": fund.risk_level,
        "aum": fund.aum,
        "nav": fund.nav,
        "expense_ratio": fund.expense_ratio,
        "rating": fund.rating,
        "risk_adjusted_return": fund.risk_adjusted_return,
        "return_5y": fund.return_5y
    }
class FundSuitabilityRequest(BaseModel):
    profile: UserProfile
    fund_code: str
@router.post("/funds/suitability")
def check_fund_suitability(
    request: FundSuitabilityRequest,
    db: Session = Depends(get_db)
):
    """
    Detailed LLM-backed analysis of fund suitability for a user profile.
    """
    profile = request.profile
    fund_code = request.fund_code

    fund = db.query(MutualFund).filter(MutualFund.code == fund_code).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    # Step 1: Rule-based analysis
    analysis = FundSuitabilityEngine.analyze(profile, fund)

    # Step 2: Get fund data from analysis result
    fund_data = analysis.get("fund_metadata", {})

    # Step 3: Get LLM-backed explanation
    llm_feedback = "⚠️ LLM validation unavailable"
    try:
        llm_result = validate_and_explain_output({
            "profile": profile.dict() if hasattr(profile, 'dict') else profile.model_dump(),
            "fund": fund_data
        })
        llm_feedback = llm_result.get("llm_feedback", llm_feedback)
    except Exception as e:
        logger.warning(f"LLM validation failed: {e}")

    # Step 4: Get flags
    flags = []
    try:
        flags = extract_flags({
            "fund": fund_data,
            "profile": profile.dict() if hasattr(profile, 'dict') else profile.model_dump()
        })
    except Exception as e:
        logger.warning(f"Flag extraction failed: {e}")

    # Step 5: Get story
    story = "⚠️ Story unavailable"
    try:
        story_result = generate_portfolio_story({
            "fund": fund_data,
            "profile": profile.dict() if hasattr(profile, 'dict') else profile.model_dump()
        })
        story = story_result.get("story", story)
    except Exception as e:
        logger.warning(f"Story generation failed: {e}")

    return {
        "fund": fund_data,
        "suitability_flags": analysis.get("suitability_flags", {}),
        "llm_feedback": llm_feedback,
        "flags": flags,
        "story": story
    }
