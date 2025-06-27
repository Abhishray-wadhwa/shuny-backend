# app/services/holding_verdict_engine.py

import json
import logging
from typing import List, Dict, Any, Union
from datetime import datetime, date
from app.models.portfolio import Holding
from app.services.llm_wrapper import call_openai_chat

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class HoldingVerdictEngine:
    @staticmethod
    def safe_serialize_holdings(holdings: List[Holding]) -> List[Dict[str, Any]]:
        """
        Safely convert Holding objects to dictionaries for LLM processing
        """
        serialized_holdings = []
        
        for holding in holdings:
            try:
                # Convert Holding to dict
                if hasattr(holding, 'dict') and callable(getattr(holding, 'dict')):
                    holding_dict = holding.dict()
                elif hasattr(holding, 'model_dump') and callable(getattr(holding, 'model_dump')):
                    holding_dict = holding.model_dump()
                elif isinstance(holding, dict):
                    holding_dict = holding.copy()
                else:
                    # Manual conversion
                    holding_dict = {
                        'name': getattr(holding, 'name', 'Unknown'),
                        'symbol': getattr(holding, 'symbol', 'N/A'),
                        'asset_type': getattr(holding, 'asset_type', 'unknown'),
                        'quantity': getattr(holding, 'quantity', 0),
                        'avg_buy_price': getattr(holding, 'avg_buy_price', 0),
                        'current_price': getattr(holding, 'current_price', 0),
                        'buy_date': getattr(holding, 'buy_date', None),
                        'sector': getattr(holding, 'sector', 'unknown'),
                        'current_value': getattr(holding, 'current_value', None),
                        'unrealized_pnl': getattr(holding, 'unrealized_pnl', None),
                        'unrealized_pnl_percent': getattr(holding, 'unrealized_pnl_percent', None)
                    }
                
                # Handle date serialization
                if 'buy_date' in holding_dict and holding_dict['buy_date']:
                    if isinstance(holding_dict['buy_date'], (date, datetime)):
                        holding_dict['buy_date'] = holding_dict['buy_date'].isoformat()
                
                # Calculate derived metrics if not present
                if not holding_dict.get('current_value') and holding_dict.get('quantity') and holding_dict.get('current_price'):
                    holding_dict['current_value'] = holding_dict['quantity'] * holding_dict['current_price']
                
                if not holding_dict.get('unrealized_pnl') and all(holding_dict.get(k) for k in ['quantity', 'avg_buy_price', 'current_price']):
                    holding_dict['unrealized_pnl'] = holding_dict['quantity'] * (holding_dict['current_price'] - holding_dict['avg_buy_price'])
                
                if not holding_dict.get('unrealized_pnl_percent') and holding_dict.get('avg_buy_price') and holding_dict.get('current_price'):
                    holding_dict['unrealized_pnl_percent'] = ((holding_dict['current_price'] - holding_dict['avg_buy_price']) / holding_dict['avg_buy_price']) * 100
                
                # Add holding period calculation
                if holding_dict.get('buy_date'):
                    try:
                        if isinstance(holding_dict['buy_date'], str):
                            buy_date = datetime.fromisoformat(holding_dict['buy_date'].replace('Z', '+00:00'))
                        else:
                            buy_date = holding_dict['buy_date']
                        
                        holding_period_days = (datetime.now() - buy_date).days
                        holding_dict['holding_period_days'] = holding_period_days
                        holding_dict['holding_period_years'] = round(holding_period_days / 365.25, 2)
                    except Exception as e:
                        logger.warning(f"Could not calculate holding period for {holding_dict.get('symbol')}: {e}")
                        holding_dict['holding_period_days'] = 0
                        holding_dict['holding_period_years'] = 0
                
                serialized_holdings.append(holding_dict)
                
            except Exception as e:
                logger.error(f"Error serializing holding {getattr(holding, 'symbol', 'Unknown')}: {e}")
                # Add minimal fallback entry
                serialized_holdings.append({
                    'name': str(holding),
                    'symbol': 'ERROR',
                    'error': f"Serialization failed: {str(e)}"
                })
        
        return serialized_holdings

    @staticmethod
    def get_verdicts(holdings: List[Holding]) -> List[Dict]:
        """
        Enhanced verdict generation with better error handling and more sophisticated analysis
        """
        if not holdings:
            logger.warning("No holdings provided for verdict generation")
            return []
        
        try:
            # Safely serialize holdings
            serialized_holdings = HoldingVerdictEngine.safe_serialize_holdings(holdings)
            
            if not serialized_holdings:
                logger.warning("No valid holdings could be serialized")
                return []
            
            # Build enhanced prompt
            prompt = f"""
You are a certified financial advisor with expertise in Indian markets. Analyze each holding and provide actionable investment advice.

For each holding, consider:
1. **Performance Analysis**: Current returns vs benchmark and time held
2. **Fundamental Analysis**: Asset quality, sector outlook, fund management (for MFs)
3. **Portfolio Context**: Position sizing, concentration risk, asset class balance
4. **Market Timing**: Current market conditions and valuations
5. **Tax Implications**: LTCG vs STCG, holding period optimization
6. **Risk Assessment**: Volatility, sector concentration, company/fund specific risks

Provide clear actionable advice: **BUY**, **HOLD**, or **SELL** for each asset.

**Output Format (JSON Array):**
[
  {{
    "symbol": "exact_symbol_from_input",
    "name": "holding_name",
    "action": "BUY/HOLD/SELL",
    "confidence": 0.85,
    "reason": "Detailed 2-3 line reasoning covering performance, fundamentals, and outlook",
    "key_metrics": {{
      "current_return_percent": 15.5,
      "holding_period_years": 2.3,
      "risk_level": "Medium"
    }},
    "next_review_months": 6,
    "alternative_suggestion": "Optional: Better alternative if SELL is recommended"
  }}
]

**Important Instructions:**
- Be specific and actionable in your reasoning
- Consider the Indian market context (tax laws, sectoral trends)
- For mutual funds, consider fund manager track record and expense ratios
- For stocks, consider business fundamentals and sector outlook
- Always include confidence score (0.1 to 1.0)
- If recommending SELL, suggest better alternatives when possible
- Keep reasoning concise but informative

**Holdings Data:**
{json.dumps(serialized_holdings, indent=2)}
            """

            # Call LLM with enhanced parameters
            response = call_openai_chat(
                system_prompt="""You are a professional investment analyst and certified financial planner specializing in Indian markets. 
                Provide evidence-based, actionable investment advice. Be specific about reasoning and always consider the investor's best interests.
                Focus on long-term wealth creation while managing downside risks.""",
                user_prompt=prompt,
                model="gpt-4o",
                temperature=0.2,  # Lower temperature for more consistent financial advice
                max_tokens=2000   # Increased for detailed analysis
            )
            
            # Parse and validate response
            try:
                parsed_verdicts = json.loads(response)
                
                # Validate structure
                if not isinstance(parsed_verdicts, list):
                    raise ValueError("Response is not a list")
                
                validated_verdicts = []
                for verdict in parsed_verdicts:
                    if not isinstance(verdict, dict):
                        continue
                    
                    # Ensure required fields
                    validated_verdict = {
                        "symbol": verdict.get("symbol", "Unknown"),
                        "name": verdict.get("name", "Unknown"),
                        "action": verdict.get("action", "HOLD").upper(),
                        "confidence": max(0.1, min(1.0, float(verdict.get("confidence", 0.5)))),
                        "reason": verdict.get("reason", "Analysis not available"),
                        "key_metrics": verdict.get("key_metrics", {}),
                        "next_review_months": int(verdict.get("next_review_months", 6)),
                        "alternative_suggestion": verdict.get("alternative_suggestion")
                    }
                    
                    # Validate action
                    if validated_verdict["action"] not in ["BUY", "HOLD", "SELL"]:
                        validated_verdict["action"] = "HOLD"
                    
                    validated_verdicts.append(validated_verdict)
                
                logger.info(f"✅ Generated {len(validated_verdicts)} holding verdicts successfully.")
                return validated_verdicts
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"Raw response: {response[:500]}...")
                return HoldingVerdictEngine.generate_fallback_verdicts(serialized_holdings)
            
        except Exception as e:
            logger.error(f"⚠️ Verdict generation failed: {e}")
            return HoldingVerdictEngine.generate_fallback_verdicts(holdings)

    @staticmethod
    def generate_fallback_verdicts(holdings: Union[List[Holding], List[Dict]]) -> List[Dict]:
        """
        Generate basic fallback verdicts when LLM fails
        """
        fallback_verdicts = []
        
        try:
            for holding in holdings:
                if isinstance(holding, dict):
                    symbol = holding.get("symbol", "Unknown")
                    name = holding.get("name", "Unknown")
                    pnl_percent = holding.get("unrealized_pnl_percent", 0)
                else:
                    symbol = getattr(holding, "symbol", "Unknown")
                    name = getattr(holding, "name", "Unknown")
                    pnl_percent = getattr(holding, "unrealized_pnl_percent", 0)
                
                # Simple rule-based verdict
                if pnl_percent > 20:
                    action = "HOLD"
                    reason = f"Good performance with {pnl_percent:.1f}% returns. Continue holding for long-term gains."
                elif pnl_percent < -15:
                    action = "HOLD"  # Conservative fallback
                    reason = f"Currently down {abs(pnl_percent):.1f}%. Holding to allow for recovery unless fundamentally weak."
                else:
                    action = "HOLD"
                    reason = f"Moderate performance ({pnl_percent:.1f}%). Maintaining position with regular review."
                
                fallback_verdicts.append({
                    "symbol": symbol,
                    "name": name,
                    "action": action,
                    "confidence": 0.5,
                    "reason": reason,
                    "key_metrics": {
                        "current_return_percent": pnl_percent,
                        "risk_level": "Unknown"
                    },
                    "next_review_months": 3,
                    "alternative_suggestion": None,
                    "is_fallback": True
                })
            
            logger.info(f"Generated {len(fallback_verdicts)} fallback verdicts")
            return fallback_verdicts
            
        except Exception as e:
            logger.error(f"Even fallback verdict generation failed: {e}")
            return []

    @staticmethod
    def get_portfolio_level_insights(holdings: List[Holding], verdicts: List[Dict]) -> Dict[str, Any]:
        """
        Generate portfolio-level insights based on individual verdicts
        """
        try:
            if not verdicts:
                return {}
            
            # Aggregate statistics
            actions = [v.get("action", "HOLD") for v in verdicts]
            buy_count = actions.count("BUY")
            hold_count = actions.count("HOLD")
            sell_count = actions.count("SELL")
            
            avg_confidence = sum(v.get("confidence", 0.5) for v in verdicts) / len(verdicts)
            
            # Portfolio health assessment
            health_score = 0
            if sell_count == 0:
                health_score += 40
            elif sell_count <= len(verdicts) * 0.2:  # Less than 20% sell recommendations
                health_score += 30
            else:
                health_score += 10
            
            health_score += min(30, hold_count * 5)  # Stable holdings are good
            health_score += min(30, buy_count * 3)   # Some opportunities are good
            
            return {
                "portfolio_action_summary": {
                    "buy_count": buy_count,
                    "hold_count": hold_count,
                    "sell_count": sell_count,
                    "total_holdings": len(verdicts)
                },
                "average_confidence": round(avg_confidence, 2),
                "portfolio_health_score": min(100, health_score),
                "overall_recommendation": (
                    "Strong portfolio with good holdings" if health_score >= 80 else
                    "Decent portfolio with some adjustments needed" if health_score >= 60 else
                    "Portfolio needs significant review and changes"
                ),
                "next_review_recommended": "1 month" if sell_count > 0 else "3 months"
            }
            
        except Exception as e:
            logger.error(f"Error generating portfolio insights: {e}")
            return {"error": "Could not generate portfolio-level insights"}