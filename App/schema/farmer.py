from pydantic import BaseModel

class FarmerInfo(BaseModel):
    """Farm details; user_id and username are set from the authenticated user."""
    province: str
    district: str
    crop: str
    phone: str
    stage: str
    area: int
    crop_start_date: str
    soil_type: str
    irrigation_type: str
    days_after_sowing: int
    latitude: float | None = None
    longitude: float | None = None

