from fastapi import APIRouter, HTTPException
from typing import List
from app.services.db import get_db

router = APIRouter(prefix="/api/antena", tags=["Antena"])

@router.get("/logs")
async def get_access_logs():
    try:
        db = get_db()
        logs_ref = db.collection("access_logs")
        docs = logs_ref.order_by("Timestamp", direction="DESCENDING").stream()
        
        logs = []
        for doc in docs:
            d = doc.to_dict()
            # Convert timestamp to string if necessary
            if "Timestamp" in d and hasattr(d["Timestamp"], "isoformat"):
                d["Timestamp"] = d["Timestamp"].isoformat()
            # The exact property name in the screenshot is "Timestamp", but we also check lowercases just in case
            logs.append(d)
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
