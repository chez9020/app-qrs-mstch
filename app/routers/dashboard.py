from datetime import datetime, time
from typing import Optional
from fastapi import APIRouter
from app.models.schemas import DashboardStats
from app.services.db import get_db

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])
collection_name = "guests"

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None,
    all_checkins: bool = False
):
    db = get_db()
    
    guests_ref = db.collection(collection_name)
    all_guests = [doc.to_dict() for doc in guests_ref.stream()]
    
    # Base filtering for all stats
    filtered_checked_in = [g for g in all_guests if g.get("status") == "checked_in"]
    
    # Apply date filters if provided
    if start_date or end_date:
        try:
            # Parse dates. Allow YYYY-MM-DD or ISO
            start_dt = None
            if start_date:
                if len(start_date) == 10:
                    start_dt = datetime.combine(datetime.fromisoformat(start_date).date(), time.min)
                else:
                    start_dt = datetime.fromisoformat(start_date)

            end_dt = None
            if end_date:
                if len(end_date) == 10:
                    end_dt = datetime.combine(datetime.fromisoformat(end_date).date(), time.max)
                else:
                    end_dt = datetime.fromisoformat(end_date)

            if start_dt:
                filtered_checked_in = [g for g in filtered_checked_in if g.get("scan_timestamp") and g["scan_timestamp"].replace(tzinfo=None) >= start_dt.replace(tzinfo=None)]
            if end_dt:
                filtered_checked_in = [g for g in filtered_checked_in if g.get("scan_timestamp") and g["scan_timestamp"].replace(tzinfo=None) <= end_dt.replace(tzinfo=None)]
        except Exception as e:
            print(f"Filter error: {e}")
            # fall back to unfiltered if dates are malformed

    total = len(all_guests)
    checked_in_count = len(filtered_checked_in)
    
    attendance_rate = (checked_in_count / total * 100) if total > 0 else 0
    
    # Sort by check-in time for recent checkins
    checked_in_sorted = sorted(
        filtered_checked_in,
        key=lambda x: x["scan_timestamp"] or datetime.min,
        reverse=True
    )
    
    # Slice if not all requested
    recent_checkins = checked_in_sorted if all_checkins else checked_in_sorted[:10]
    
    return DashboardStats(
        total_guests=total,
        checked_in_count=checked_in_count,
        attendance_rate=attendance_rate,
        recent_checkins=recent_checkins
    )
