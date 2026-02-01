from pydantic import BaseModel

class FarmerInfo(BaseModel):
    """Farm details; user_id and username are set from the authenticated user."""
    province: str
    district: str
    crop: str
    phone: str
    stage: str
    area: str
