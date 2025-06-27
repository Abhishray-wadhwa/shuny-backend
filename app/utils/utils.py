# app/routers/recommendation.py or a shared helper module

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
