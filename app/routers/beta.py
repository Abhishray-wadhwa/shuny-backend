from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from supabase import create_client
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
router = APIRouter()
router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class BetaAccessRequest(BaseModel):
    user_id: int
    email: EmailStr
    wants_access: bool

@router.post("/submit")
def submit_beta_access(data: BetaAccessRequest):
    try:
        supabase.table("beta_access_requests").insert({
            "user_id": data.user_id,
            "email": data.email,
            "wants_access": data.wants_access,
            "submitted_at": datetime.utcnow().isoformat()
        }).execute()
        return {"success": True, "message": "Beta access request submitted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit beta request: {e}")
