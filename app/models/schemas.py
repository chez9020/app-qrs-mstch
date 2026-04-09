from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class GuestStatus(str, Enum):
    VALID = "valid"
    CHECKED_IN = "checked_in"
    INVALID = "invalid"

class Guest(BaseModel):
    id: Optional[str] = None
    name: str
    email: Optional[str] = None 
    uuid: str
    qr_code_url: Optional[str] = None
    status: GuestStatus = GuestStatus.VALID
    scan_timestamp: Optional[datetime] = None
    created_at: datetime = datetime.utcnow()

class User(BaseModel):
    username: str
    email: Optional[str] = None
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class ValidationResponse(BaseModel):
    status: str
    message: str
    guest_name: Optional[str] = None
    timestamp: Optional[datetime] = None

class DashboardStats(BaseModel):
    total_guests: int
    checked_in_count: int
    attendance_rate: float
    recent_checkins: List[Guest]
