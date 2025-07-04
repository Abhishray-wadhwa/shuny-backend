from supabase import create_client
from datetime import datetime
import hashlib
import os
import logging

# Set up Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

logger = logging.getLogger(__name__)

def generate_user_fingerprint(raw_data: dict) -> str:
    key_fields = f"{raw_data.get('age')}_{raw_data.get('income')}_{raw_data.get('risk_appetite')}_{raw_data.get('investment_experience')}"
    return hashlib.md5(key_fields.encode('utf-8')).hexdigest()

def save_user_data_from_raw(raw_data: dict, email: str = None, name: str = None, user_id: int = None, save_user: bool = True):
    now = datetime.utcnow().isoformat()
    user_hash = generate_user_fingerprint(raw_data)

    if save_user and user_id is None:
        # Step 1: Check if user already exists with the same hash
        try:
            result = supabase.table("users").select("id").eq("user_hash", user_hash).limit(1).execute()
            if result.data and len(result.data) > 0:
                user_id = result.data[0]["id"]
                logger.info(f"✅ Existing user found with hash: {user_id}")
        except Exception as e:
            logger.warning(f"⚠️ Could not check for existing user: {e}")

        # Step 2: Insert new user if not found
        if user_id is None:
            user_profile = {
                "email": email or f"temp_user_{user_hash}@example.com",  # stable fallback email
                "name": name or "Anonymous",
                "age": raw_data.get("age"),
                "annual_income": raw_data.get("income"),
                "risk_profile": raw_data.get("risk_appetite"),
                "investment_experience": raw_data.get("investment_experience"),
                "user_hash": user_hash,
                "created_at": now,
                "updated_at": now
            }

            try:
                response = supabase.table("users").insert(user_profile).execute()
                user_id = response.data[0]["id"]
                logger.info(f"✅ New user created with ID: {user_id}")
            except Exception as e:
                logger.error(f"❌ Failed to store user profile: {e}")
                return None

    if user_id is None:
        logger.error("❌ user_id is missing; cannot proceed to save goal")
        return None

    # Insert goal
    goal_entry = {
        "user_id": user_id,
        "goal_name": raw_data.get("investment_goal"),
        "goal_type": "financial",
        "target_amount": raw_data.get("goal_amount"),
        "time_horizon": raw_data.get("goal_timeline_years"),
        "risk_tolerance": raw_data.get("risk_appetite"),
        "priority": raw_data.get("investment_personality"),
        "current_corpus": 0,
        "monthly_investment_capacity": raw_data.get("monthly_investment_capacity"),
        "is_active": True,
        "created_at": now,
        "updated_at": now
    }

    try:
        supabase.table("user_goals").insert(goal_entry).execute()
        logger.info("✅ Goal added to user")
    except Exception as e:
        logger.error(f"❌ Failed to store user goal: {e}")

    return user_id
