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
    
    if not doc.exists:
        return ValidationResponse(
            status="error",
            message="No registrado",
            timestamp=timestamp
        )
    
    guest_data = doc.to_dict()
    current_status = guest_data.get("status")
    
    if current_status == GuestStatus.VALID.value:
        # Check in the guest
        doc_ref.update({
            "status": GuestStatus.CHECKED_IN.value,
            "scan_timestamp": timestamp
        })
        
        return ValidationResponse(
            status="success",
            message=f"Bienvenido {guest_data.get('name')}",
            guest_name=guest_data.get('name'),
            timestamp=timestamp
        )
    
    elif current_status == GuestStatus.CHECKED_IN.value:
        return ValidationResponse(
            status="warning",
            message="Ya utilizado",
            guest_name=guest_data.get('name'),
            timestamp=guest_data.get("scan_timestamp")
        )
    
    else:
        return ValidationResponse(
            status="error",
            message="Invitación inválida",
            guest_name=guest_data.get('name'),
            timestamp=timestamp
        )
