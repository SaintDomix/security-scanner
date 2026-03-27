from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    subscription_tier = Column(String, default="free")  # free, pro, enterprise
    scans_today = Column(Integer, default=0)
    last_scan_date = Column(String, nullable=True)  # YYYY-MM-DD
    created_at = Column(DateTime, default=datetime.utcnow)

    scans = relationship("Scan", back_populates="owner")


class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Input
    scan_type = Column(String, nullable=False)   # "url" or "upload"
    target = Column(String, nullable=False)       # URL or filename
    scan_mode = Column(String, default="sast")    # sast, secrets, dast, full

    # Status
    status = Column(String, default="pending")    # pending, running, completed, failed
    error_message = Column(Text, nullable=True)

    # GitHub info
    github_valid = Column(Boolean, nullable=True)
    github_stars = Column(Integer, nullable=True)
    github_language = Column(String, nullable=True)
    github_description = Column(Text, nullable=True)

    # Tool results
    gitleaks_findings = Column(Integer, default=0)
    gitleaks_report_path = Column(String, nullable=True)

    semgrep_findings = Column(Integer, default=0)
    semgrep_report_path = Column(String, nullable=True)

    bearer_findings = Column(Integer, default=0)
    bearer_report_path = Column(String, nullable=True)

    dast_findings = Column(Integer, default=0)
    dast_report_path = Column(String, nullable=True)

    # Severity summary
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="scans")
