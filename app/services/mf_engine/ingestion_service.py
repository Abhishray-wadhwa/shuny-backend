# invest_ai_engine/app/services/mf_engine/ingestion_service.py

import requests
import time
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.mutual_fund import MutualFund
from app.config import SessionLocal

MFAPI_BASE = "https://api.mfapi.in/mf"
RATE_LIMIT_SECONDS = 0.8  # ~1 request per second to avoid rate-limiting

def fetch_all_fund_codes():
    try:
        resp = requests.get(MFAPI_BASE)
        if resp.status_code == 200:
            return resp.json()  # [{ schemeCode, schemeName }, ...]
    except Exception as e:
        print("Failed to fetch all fund codes:", str(e))
    return []

def fetch_fund_metadata(fund_code):
    try:
        resp = requests.get(f"{MFAPI_BASE}/{fund_code}")
        if resp.status_code == 200:
            data = resp.json()
            meta = data.get("meta", {})
            nav_data = data.get("data", [{}])[0]

            return {
                "code": str(fund_code),
                "name": str(meta.get("scheme_name")) or "",
                "fund_house": str(meta.get("fund_house")) or "",
                "scheme_type": str(meta.get("scheme_type")) or "",
                "scheme_category": str(meta.get("scheme_category")) or "",
                "nav": float(nav_data.get("nav", 0.0)),
                "nav_date": str(datetime.strptime(nav_data.get("date"), "%d-%m-%Y").date()) if nav_data.get("date") else None,
                "aum": None,  # Not available via MFAPI — you can later update this from another source
                "expense_ratio": None,  # Same as above
                "risk_level": None,  # You can derive this later from category
                "is_active": True,  # Default to True if not deactivated
                "last_updated": datetime.utcnow()
            }
    except Exception as e:
        print(f"❌ Error fetching fund {fund_code}: {e}")
    return None

def store_fund_data(session: Session, fund_data: dict):
    fund_code = str(fund_data["code"])
    fund = session.get(MutualFund, fund_code)

    if fund:
        # Update existing
        fund.name = fund_data["name"]
        fund.fund_house = fund_data["fund_house"]
        fund.scheme_type = fund_data["scheme_type"]
        fund.scheme_category = fund_data["scheme_category"]
        fund.nav = fund_data["nav"]
        fund.nav_date = fund_data["nav_date"]
        fund.last_updated = fund_data["last_updated"]
    else:
        # Insert new
        fund = MutualFund(**fund_data)
        session.add(fund)

def ingest_all():
    db = SessionLocal()
    try:
        all_funds = fetch_all_fund_codes()
        print(f"Found {len(all_funds)} funds. Starting ingestion...")

        for i, fund_meta in enumerate(all_funds):
            code = fund_meta.get("schemeCode")
            fund_data = fetch_fund_metadata(code)
            if fund_data:
                store_fund_data(db, fund_data)
                print(f"[{i+1}] Stored: {fund_data['name']} ({code})")
            else:
                print(f"[{i+1}] Skipped: {code}")

            time.sleep(RATE_LIMIT_SECONDS)

            if i > 0 and i % 50 == 0:
                db.commit()  # Batch commit
                print(f"--- Committed batch of 50 funds ---")

        db.commit()
        print("✅ All fund data committed to DB.")
    except Exception as e:
        db.rollback()
        print("❌ Error during ingestion:", str(e))
    finally:
        db.close()

if __name__ == "__main__":
    ingest_all()
