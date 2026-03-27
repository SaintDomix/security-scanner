from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    subscription_tier: str
    scans_today: int
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


# ── Scans ─────────────────────────────────────────────────────────────────────
class ScanCreate(BaseModel):
    repo_url: Optional[str] = None
    scan_mode: str = "full"   # sast | secrets | dast | full


class ScanOut(BaseModel):
    id: int
    scan_type: str
    target: str
    scan_mode: str
    status: str
    error_message: Optional[str]

    github_valid: Optional[bool]
    github_stars: Optional[int]
    github_language: Optional[str]
    github_description: Optional[str]

    gitleaks_findings: int
    semgrep_findings: int
    bearer_findings: int
    dast_findings: int

    critical_count: int
    high_count: int
    medium_count: int
    low_count: int

    gitleaks_report_path: Optional[str]
    semgrep_report_path: Optional[str]
    bearer_report_path: Optional[str]
    dast_report_path: Optional[str]

    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ScanListItem(BaseModel):
    id: int
    target: str
    scan_mode: str
    status: str
    gitleaks_findings: int
    semgrep_findings: int
    bearer_findings: int
    dast_findings: int
    critical_count: int
    high_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Subscription ───────────────────────────────────────────────────────────────
class SubscriptionUpgrade(BaseModel):
    tier: str  # pro | enterprise


# ── DAST ──────────────────────────────────────────────────────────────────────
class DastScanCreate(BaseModel):
    target_url: str
    scan_mode: str = "dast"
