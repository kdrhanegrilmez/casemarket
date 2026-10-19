from fastapi import APIRouter,Depends

from core.dependencies import get_current_user
from schemas.auth import UserPublic
router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.get("/me",response_model=UserPublic)
def read_current_user(
        current_user: dict =Depends(get_current_user),
):
    return current_user