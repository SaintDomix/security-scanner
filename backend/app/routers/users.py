from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import User
from app.schemas.schemas import UserOut, SubscriptionUpgrade
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])

VALID_TIERS = {"free", "pro", "enterprise"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/upgrade", response_model=UserOut)
def upgrade_subscription(
    data: SubscriptionUpgrade,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.tier not in VALID_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {data.tier}")
    current_user.subscription_tier = data.tier
    db.commit()
    db.refresh(current_user)
    return current_user
