from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.schemas import GuestStatus, ValidationResponse
from app.services.db import get_db

import pytz

try:
    mx_tz = pytz.timezone('America/Mexico_City')
except (ImportError, pytz.UnknownTimeZoneError):
    mx_tz = None

router = APIRouter(prefix="/api/scanner", tags=["Scanner"])
collection_name = "guests"

class ScanRequest(BaseModel):
    uuid: str

@router.post("/validate", response_model=ValidationResponse)
async def validate_guest(scan: ScanRequest):
    uuid_to_check = scan.uuid
    db = get_db()
    
    timestamp = datetime.now(mx_tz) if mx_tz else datetime.now()
    
    doc_ref = db.collection(collection_name).document(uuid_to_check)
    doc = doc_ref.get()
    
    from fastapi.responses import JSONResponse
    
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache"
    }
    
    if not doc.exists:
        return JSONResponse(
            status_code=404,
            content={
                "status": "error",
                "message": "No registrado",
                "timestamp": timestamp.isoformat() if timestamp else None
            },
            headers=headers
        )
    
    guest_data = doc.to_dict()
    current_status = guest_data.get("status")
    
    if current_status == GuestStatus.VALID.value:
        # Check in the guest
        doc_ref.update({
            "status": GuestStatus.CHECKED_IN.value,
            "scan_timestamp": timestamp,
            "last_welcome_timestamp": timestamp
        })
        
        return {
            "status": "success",
            "message": f"Bienvenido {guest_data.get('name')}",
            "guest_name": guest_data.get('name'),
            "timestamp": timestamp
        }
    
    elif current_status == GuestStatus.CHECKED_IN.value:
        # Aunque ya entró, actualizamos el timestamp para que la pantalla de bienvenida lo detecte
        doc_ref.update({
            "last_welcome_timestamp": timestamp
        })

        return JSONResponse(
            status_code=409,
            content={
                "status": "warning",
                "message": "Ya utilizado",
                "guest_name": guest_data.get('name'),
                "timestamp": guest_data.get("scan_timestamp").isoformat() if guest_data.get("scan_timestamp") else None
            },
            headers=headers
        )
    else:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "Invitación inválida",
                "guest_name": guest_data.get('name'),
                "timestamp": timestamp.isoformat() if timestamp else None
            },
            headers=headers
        )
