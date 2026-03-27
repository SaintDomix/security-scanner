from datetime import date
from fastapi import HTTPException
from app.models.models import User

DAILY_LIMITS = {
    "free": 3,
    "pro": 50,
    "enterprise": 9999,
}


def check_and_increment_scan(user: User, db) -> None:
    today = str(date.today())
    if user.last_scan_date != today:
        user.scans_today = 0
        user.last_scan_date = today

    limit = DAILY_LIMITS.get(user.subscription_tier, 3)
    if user.scans_today >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily scan limit reached ({limit} scans/day on {user.subscription_tier} plan). Upgrade for more.",
        )
    user.scans_today += 1
    db.commit()
