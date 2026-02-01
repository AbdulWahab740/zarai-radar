from fastapi import APIRouter, HTTPException, Depends
from App.schema.farmer import FarmerInfo
from App.db import supabase
from App.routes.auth import get_current_user

router = APIRouter()

@router.post("/farmer-info")
async def create_farmer_info(
    info: FarmerInfo,
    current_user: dict = Depends(get_current_user),
):
    """Create farmer info for the authenticated user. user_id and username are set from signup."""
    try:
        data = info.dict()
        # Set user_id and username from the signed-in user (signup table)
        data["user_id"] = current_user["id"]
        data["username"] = current_user["username"]
        response = supabase.table("farmer_info").insert(data).execute()

        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to save farmer info")

        return {"message": "Farmer info saved successfully", "data": response.data[0]}

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
