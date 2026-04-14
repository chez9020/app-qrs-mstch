from fastapi import APIRouter, HTTPException
from typing import List
from google.cloud import firestore
import os

router = APIRouter(prefix="/api/antena", tags=["Antena"])

@router.get("/logs")
async def get_access_logs():
    try:
        # Aquí forzamos la conexión específicamente a la base de datos "bristol-db",
        # ya que la app por defecto se conecta a la principal "(default)"
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'shaq-brand-bot')
        db = firestore.Client(project=project_id, database="bristol-db")
        
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
