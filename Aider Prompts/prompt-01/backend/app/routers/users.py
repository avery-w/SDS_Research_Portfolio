from fastapi import APIRouter, Depends
from app.deps.auth import get_current_user
router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", responses={401: {"description": "Missing/invalid auth"}})
async def me(user=Depends(get_current_user)):
    # Return safe profile fields
    return {"id": user.id, "email": user.email, "role": user.role, "is_active": user.is_active}
