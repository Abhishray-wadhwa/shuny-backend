from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean
from app.config import Base
from datetime import datetime

class MutualFund(Base):
    __tablename__ = "mutual_funds"

    code = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)

    # Fund metadata
    fund_house = Column(String, nullable=True)        # e.g., Axis Mutual Fund
    scheme_type = Column(String, nullable=True)        # e.g., Open Ended
    scheme_category = Column(String, nullable=True)    # e.g., Large Cap, Mid Cap, ELSS

    # Investment data
    nav = Column(Float, nullable=True)
    nav_date = Column(String, nullable=True)
    expense_ratio = Column(Float, nullable=True)       # Optional, if you can get it
    aum = Column(Float, nullable=True)                 # Assets Under Management (in Cr)
    risk_level = Column(String, nullable=True)         # Low, Moderate, High (if parsable)
    return_1y = Column(Float, nullable=True)
    return_3y = Column(Float, nullable=True)
    return_5y = Column(Float, nullable=True)
    expected_return = Column(Float, nullable=True)  # derived
    # Meta
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=datetime.utcnow)
    exit_load = Column(Float, nullable=True)
    standard_deviation = Column(Float, nullable=True)
    risk_adjusted_return = Column(Float, nullable=True)
    rating = Column(Integer, nullable=True)
    portfolio_turnover  = Column(Float, nullable=True)
    fund_manager_tenure  = Column(Float, nullable=True)

