from fastapi import APIRouter, HTTPException, Depends
from App.schema.farmer import FarmerInfo
from App.db import supabase
from App.routes.auth import get_current_user
from App.data.irrigation import get_wheat_stage
router = APIRouter()

@router.get("/farmer-info")
async def get_farmer_info(current_user: dict = Depends(get_current_user)):
    """Get farmer info for the authenticated user."""
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")

        response = (
            supabase.table("farmer_info")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="No farmer profile found")

        return {"data": response.data[0]}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

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
        _, sub_stage = get_wheat_stage(data["date_after_sowing"])
        data["sub_stage"] = sub_stage
        response = supabase.table("farmer_info").insert(data).execute()
        supabase.table("farmer_info").update({
        "status": "active"
    }).eq("user_id", current_user["id"]).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to save farmer info")

        return {"message": "Farmer info saved successfully", "data": response.data[0]}

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
