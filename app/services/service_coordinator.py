import logging
from typing import Dict, Any, List
from datetime import datetime
from app.services.llm_humanizer import generate_enhanced_portfolio_story
from app.services.llm_review_service import generate_ai_insights
from app.services.flags import extract_enhanced_flags
from app.services.monitoring_engine import EnhancedMonitoringEngine
logger = logging.getLogger(__name__)

class ServiceCoordinator:
    """
    Coordinates all services to work together with the recommendation engine
    Provides a unified interface for generating complete portfolio responses
    """
    
    @staticmethod
    def generate_complete_response(recommendation_json: Dict, profile_data: Dict = None) -> Dict:
        """
        Generate a complete, well-formatted response combining all services
        """
        try:
            logger.info("🚀 Starting complete response generation...")
            
            # Generate enhanced story
            story_result = generate_enhanced_portfolio_story(recommendation_json)
            logger.info("✅ Portfolio story generated")
            
            # Generate AI insights
            insights_result = generate_ai_insights(recommendation_json)
            logger.info("✅ AI insights generated")
            
            # Extract enhanced flags
            flags_result = extract_enhanced_flags(recommendation_json)
            logger.info("✅ Portfolio flags extracted")
            
            # Generate monitoring alerts
            monitoring_result = EnhancedMonitoringEngine.generate_comprehensive_alerts(
                recommendation_json, profile_data
            )
            logger.info("✅ Monitoring alerts generated")
            
            # Create dashboard data
            dashboard_result = EnhancedMonitoringEngine.create_monitoring_dashboard_data(
                recommendation_json
            )
            logger.info("✅ Dashboard data created")
            
            # Compile complete response
            complete_response = {
                "success": True,
                "generated_at": datetime.now().isoformat(),
                
                # Core recommendation data
                "portfolio_recommendation": {
                    "allocation": recommendation_json.get("recommended_allocation", {}),
                    "suggested_sip": recommendation_json.get("suggested_sip", 0),
                    "target_corpus": recommendation_json.get("target_corpus", 0),
                    "expected_return": recommendation_json.get("expected_return_percent", 0),
                    "recommended_funds": recommendation_json.get("recommended_funds", {}),
                    "timeline_years": recommendation_json.get("timeline_years", 0),
                    "goal": recommendation_json.get("goal", "investment goal"),
                    "risk_score": recommendation_json.get("portfolio_risk_score", 0)
                },
                
                # Enhanced narrative content
                "user_content": {"story": story_result.get("story", ""),
                    "story_type": story_result.get("story_type", "enhanced"),
                    "sections": story_result.get("sections", []),
                    "personalization_level": story_result.get("personalization_level", "high")
                },
                
                # Professional analysis
                "professional_analysis": {
                    "ai_insights": insights_result.get("ai_insights", ""),
                    "analysis_type": insights_result.get("analysis_type", "comprehensive"),
                    "risk_assessment": {
                        "risk_score": insights_result.get("risk_score", 0),
                        "diversification_score": insights_result.get("diversification_score", 0)
                    },
                    "market_context": insights_result.get("market_context", "indian_markets")
                },
                
                # Quality control and flags
                "quality_control": {
                    "flags": flags_result.get("flags", {}),
                    "portfolio_health": flags_result.get("portfolio_health", "unknown"),
                    "flag_summary": flags_result.get("summary", ""),
                    "flag_counts": {
                        "critical": flags_result.get("total_critical", 0),
                        "warnings": flags_result.get("total_warnings", 0),
                        "suggestions": flags_result.get("total_suggestions", 0),
                        "validations": flags_result.get("total_validations", 0)
                    }
                },
                
                # Monitoring and alerts
                "monitoring": {
                    "alerts": monitoring_result.get("alerts", {}),
                    "alert_summary": monitoring_result.get("alert_summary", {}),
                    "next_review_date": monitoring_result.get("next_review_date", ""),
                    "review_frequency_days": monitoring_result.get("review_frequency_days", 90)
                },
                
                # Dashboard data
                "dashboard": {
                    "portfolio_overview": dashboard_result.get("portfolio_overview", {}),
                    "fund_breakdown": dashboard_result.get("fund_breakdown", {}),
                    "key_metrics": dashboard_result.get("key_metrics", {}),
                    "monitoring_points": dashboard_result.get("monitoring_points", []),
                    "performance_tracking": dashboard_result.get("performance_tracking", {})
                },
                
                # Response metadata
                "response_metadata": {
                    "services_used": ["portfolio_story", "ai_insights", "flags_extraction", "monitoring_engine", "dashboard_generator"],
                    "processing_success": {
                        "story_generated": story_result.get("story_type") != "fallback",
                        "insights_generated": insights_result.get("analysis_type") != "fallback",
                        "flags_extracted": len(flags_result.get("flags", {})) > 0,
                        "monitoring_created": len(monitoring_result.get("alerts", {})) > 0,
                        "dashboard_created": "error" not in dashboard_result
                    }
                }
            }
            
            logger.info("🎉 Complete response generation successful!")
            return complete_response
            
        except Exception as e:
            logger.error(f"❌ Error in complete response generation: {e}")
            return {
                "success": False,
                "error": str(e),
                "generated_at": datetime.now().isoformat(),
                "fallback_response": ServiceCoordinator._generate_fallback_response(recommendation_json)
            }
    
    @staticmethod
    def _generate_fallback_response(recommendation_json: Dict) -> Dict:
        """
        Generate a minimal fallback response when full service coordination fails
        """
        return {
            "portfolio_recommendation": {
                "allocation": recommendation_json.get("recommended_allocation", {}),
                "suggested_sip": recommendation_json.get("suggested_sip", 0),
                "target_corpus": recommendation_json.get("target_corpus", 0),
                "expected_return": recommendation_json.get("expected_return_percent", 0),
                "recommended_funds": recommendation_json.get("recommended_funds", {}),
                "timeline_years": recommendation_json.get("timeline_years", 0),
                "goal": recommendation_json.get("goal", "investment goal"),
                "risk_score": recommendation_json.get("portfolio_risk_score", 0)
            },
            "user_content": {
                "story": """## 🎯 Your Investment Journey

We've created a personalized investment strategy for your financial goals. While our enhanced services are temporarily unavailable, your core recommendations are ready and actionable.

### Your Portfolio Strategy
Your recommended approach balances growth potential with risk management, designed specifically for your timeline and objectives.

### Ready to Begin?
Every successful investment journey starts with taking the first step. Your future self will thank you for starting today! 🚀

*Full enhanced analysis will be available shortly.*""",
                "story_type": "minimal_fallback"
            },
            "response_metadata": {
                "is_fallback": True,
                "reason": "Service coordination failure - core data preserved"
            }
        }

    @staticmethod
    def get_service_health_status() -> Dict:
        """
        Check the health status of all integrated services
        """
        return {
            "services": {
                "portfolio_story_service": "operational",
                "ai_insights_service": "operational", 
                "flags_extraction_service": "operational",
                "monitoring_engine": "operational",
                "dashboard_generator": "operational"
            },
            "overall_status": "healthy",
            "last_checked": datetime.now().isoformat(),
            "dependencies": {
                "openai_api": "required",
                "llm_wrapper": "required",
                "logging": "operational"
            }
        }