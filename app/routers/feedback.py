# feedback.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()
router = APIRouter()

# Setup Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

class FeedbackRequest(BaseModel):
    user_id: int  # matches `users.id` (bigint)
    feedback_text: str
    option_type: str

@router.post("/submit-feedback")
def submit_feedback(payload: FeedbackRequest):
    try:
        supabase.table("user_feedback").insert({
            "user_id": payload.user_id,
            "feedback_text": payload.feedback_text,
            "submitted_at": datetime.utcnow().isoformat(),
            "option_type": payload.option_type
        }).execute()
        return {"message": "✅ Feedback submitted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Failed to submit feedback: {e}")
