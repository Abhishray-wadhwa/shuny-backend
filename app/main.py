from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # ✅ Import CORS middleware

from app.routers import recommendation
from app.config import Base, engine
from app.models.mutual_fund import MutualFund  # Needed to register model class

app = FastAPI()

# ✅ Enable CORS for frontend on localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
    "https://shuny.in",
    "https://www.shuny.in",],  # React app origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Invest AI Engine is live!"}

# ✅ Register the router under a clean prefix
app.include_router(recommendation.router, prefix="/recommendation")
