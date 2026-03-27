import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.models.database import get_db, SessionLocal
from app.models.models import User, Scan
from app.schemas.schemas import ScanOut, ScanListItem
from app.utils.auth import get_current_user
from app.utils.limits import check_and_increment_scan
from app.services.github_service import validate_github_repo
from app.services.gitleaks_service import run_gitleaks, clone_repo
from app.services.semgrep_service import run_semgrep
from app.services.bearer_service import run_bearer
from app.services.dast_service import run_dast
from app.services.pdf_service import generate_scan_report

router = APIRouter(prefix="/api/scans", tags=["scans"])

BASE_DIR   = Path(__file__).resolve().parent.parent.parent  # = backend/
REPO_DIR   = BASE_DIR / "repositories"
REPORT_DIR = BASE_DIR / "reports"
REPO_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)


# ── Background scan worker ─────────────────────────────────────────────────────
def _do_scan(scan_id: int, source_path: Optional[Path],
             target_url: Optional[str], scan_mode: str):
    """Runs entirely in background — opens its own DB session."""
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return

        scan.status = "running"
        db.commit()

        gl_findings = []
        sem_findings = []
        br_findings = []
        dast_findings_list = []
        gl_count = sem_count = br_count = dast_count = 0
        crit = high = med = low = 0

        # ── Gitleaks (secrets) ─────────────────────────────────────────────
        if scan_mode in ("secrets", "full") and source_path and source_path.exists():
            try:
                gl = run_gitleaks(source_path)
                gl_findings = gl["findings"]
                gl_count = gl["count"]
                scan.gitleaks_findings = gl_count
                if gl.get("json_path"):
                    scan.gitleaks_report_path = gl["json_path"]
                high += gl_count
            except Exception as e:
                scan.error_message = f"Gitleaks error: {str(e)[:200]}"

        # ── Semgrep (SAST) ─────────────────────────────────────────────────
        if scan_mode in ("sast", "full") and source_path and source_path.exists():
            try:
                sem = run_semgrep(source_path)
                sem_findings = sem["findings"]
                sem_count = sem["count"]
                scan.semgrep_findings = sem_count
                if sem.get("json_path"):
                    scan.semgrep_report_path = sem["json_path"]
                sc = sem.get("severity_counts", {})
                crit += sc.get("critical", 0)
                high += sc.get("high", 0)
                med  += sc.get("medium", 0)
                low  += sc.get("low", 0)
            except Exception as e:
                scan.error_message = f"Semgrep error: {str(e)[:200]}"

        # ── Bandit (SAST) ──────────────────────────────────────────────────
        if scan_mode in ("sast", "full") and source_path and source_path.exists():
            try:
                br = run_bearer(source_path)
                br_findings = br["findings"]
                br_count = br["count"]
                scan.bearer_findings = br_count
                if br.get("json_path"):
                    scan.bearer_report_path = br["json_path"]
                sc = br.get("severity_counts", {})
                crit += sc.get("critical", 0)
                high += sc.get("high", 0)
                med  += sc.get("medium", 0)
                low  += sc.get("low", 0)
            except Exception as e:
                if not scan.error_message:
                    scan.error_message = f"Bandit error: {str(e)[:200]}"

        # ── DAST ───────────────────────────────────────────────────────────
        if scan_mode in ("dast", "full") and target_url:
            try:
                dast_dir = REPORT_DIR / f"dast_{scan_id}"
                dast = run_dast(target_url, dast_dir)
                dast_findings_list = dast["findings"]
                dast_count = dast["count"]
                scan.dast_findings = dast_count
                if dast.get("json_path"):
                    scan.dast_report_path = dast["json_path"]
                sc = dast.get("severity_counts", {})
                crit += sc.get("critical", 0)
                high += sc.get("high", 0)
                med  += sc.get("medium", 0)
                low  += sc.get("low", 0)
            except Exception as e:
                if not scan.error_message:
                    scan.error_message = f"DAST error: {str(e)[:200]}"

        scan.critical_count = crit
        scan.high_count     = high
        scan.medium_count   = med
        scan.low_count      = low

        # ── PDF report ─────────────────────────────────────────────────────
        scan_data = {
            "target":            scan.target,
            "scan_mode":         scan_mode,
            "gitleaks_findings": gl_count,
            "semgrep_findings":  sem_count,
            "bearer_findings":   br_count,
            "dast_findings":     dast_count,
            "gitleaks":          gl_findings[:100],
            "semgrep":           sem_findings[:100],
            "bearer":            br_findings[:100],
            "dast":              dast_findings_list[:100],
        }
        pdf_path = generate_scan_report(scan_id, scan_data)
        scan.gitleaks_report_path = pdf_path   # primary download link

        scan.status       = "completed"
        scan.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        try:
            scan = db.query(Scan).filter(Scan.id == scan_id).first()
            if scan:
                scan.status        = "failed"
                scan.error_message = str(e)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/github", response_model=ScanOut)
async def scan_github(
    background_tasks: BackgroundTasks,
    repo_url:  str           = Form(...),
    scan_mode: str           = Form("full"),
    dast_url:  Optional[str] = Form(None),
    current_user: User       = Depends(get_current_user),
    db: Session              = Depends(get_db),
):
    check_and_increment_scan(current_user, db)

    gh = validate_github_repo(repo_url)

    scan = Scan(
        owner_id          = current_user.id,
        scan_type         = "url",
        target            = repo_url,
        scan_mode         = scan_mode,
        github_valid      = gh.get("valid", False),
        github_stars      = gh.get("stars"),
        github_language   = gh.get("language"),
        github_description= gh.get("description"),
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    if not gh.get("valid"):
        scan.status        = "failed"
        scan.error_message = gh.get("error", "Invalid GitHub repository")
        db.commit()
        db.refresh(scan)
        return scan

    scan_id   = scan.id
    effective_dast_url = dast_url  # may be None

    def bg():
        try:
            repo_path = clone_repo(repo_url)
        except Exception as e:
            db2 = SessionLocal()
            s = db2.query(Scan).filter(Scan.id == scan_id).first()
            if s:
                s.status = "failed"
                s.error_message = f"Clone failed: {str(e)[:400]}"
                db2.commit()
            db2.close()
            return
        _do_scan(scan_id, repo_path, effective_dast_url, scan_mode)

    background_tasks.add_task(bg)
    return scan


@router.post("/upload", response_model=ScanOut)
async def scan_upload(
    background_tasks: BackgroundTasks,
    file:      UploadFile     = File(...),
    scan_mode: str            = Form("sast"),
    dast_url:  Optional[str]  = Form(None),
    current_user: User        = Depends(get_current_user),
    db: Session               = Depends(get_db),
):
    check_and_increment_scan(current_user, db)

    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are accepted")

    safe_name    = file.filename.replace(".zip", "").replace(" ", "_")
    extract_path = REPO_DIR / safe_name
    zip_path     = REPO_DIR / file.filename

    with open(zip_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    with zipfile.ZipFile(zip_path, "r") as zr:
        zr.extractall(extract_path)

    os.remove(zip_path)

    scan = Scan(
        owner_id  = current_user.id,
        scan_type = "upload",
        target    = file.filename,
        scan_mode = scan_mode,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    scan_id       = scan.id
    effective_path = extract_path
    effective_dast = dast_url

    background_tasks.add_task(_do_scan, scan_id, effective_path, effective_dast, scan_mode)
    return scan


@router.post("/dast", response_model=ScanOut)
async def scan_dast(
    background_tasks: BackgroundTasks,
    target_url:   str    = Form(...),
    current_user: User   = Depends(get_current_user),
    db: Session          = Depends(get_db),
):
    if current_user.subscription_tier == "free":
        raise HTTPException(
            status_code=403,
            detail="DAST scanning requires a Pro or Enterprise subscription",
        )
    check_and_increment_scan(current_user, db)

    scan = Scan(
        owner_id  = current_user.id,
        scan_type = "dast",
        target    = target_url,
        scan_mode = "dast",
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    scan_id = scan.id
    background_tasks.add_task(_do_scan, scan_id, None, target_url, "dast")
    return scan


@router.get("", response_model=List[ScanListItem])
@router.get("/", response_model=List[ScanListItem], include_in_schema=False)
def list_scans(
    current_user:  User          = Depends(get_current_user),
    db:            Session       = Depends(get_db),
    limit:         int           = 20,
    offset:        int           = 0,
    status_filter: Optional[str] = None,
    mode_filter:   Optional[str] = None,
    search:        Optional[str] = None,
):
    q = db.query(Scan).filter(Scan.owner_id == current_user.id)
    if status_filter:
        q = q.filter(Scan.status == status_filter)
    if mode_filter:
        q = q.filter(Scan.scan_mode == mode_filter)
    if search:
        q = q.filter(Scan.target.ilike(f"%{search}%"))
    return q.order_by(Scan.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/{scan_id}", response_model=ScanOut)
def get_scan(
    scan_id:      int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    scan = db.query(Scan).filter(
        Scan.id == scan_id,
        Scan.owner_id == current_user.id
    ).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.get("/{scan_id}/report")
def download_report(
    scan_id:      int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    scan = db.query(Scan).filter(
        Scan.id == scan_id,
        Scan.owner_id == current_user.id
    ).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    path = scan.gitleaks_report_path
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Report not yet generated")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"scan_{scan_id}_report.pdf",
    )


@router.delete("/{scan_id}")
def delete_scan(
    scan_id:      int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    scan = db.query(Scan).filter(
        Scan.id == scan_id,
        Scan.owner_id == current_user.id
    ).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    db.delete(scan)
    db.commit()
    return {"message": "Scan deleted"}


@router.get("/{scan_id}/findings")
def get_findings(
    scan_id:      int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    """Return parsed findings from all scan tool JSON reports."""
    import json as _json

    scan = db.query(Scan).filter(
        Scan.id == scan_id,
        Scan.owner_id == current_user.id
    ).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    def _read_json(path):
        if not path:
            return None
        p = Path(path)
        if not p.exists():
            return None
        try:
            return _json.loads(p.read_text(encoding="utf-8", errors="replace").strip() or "null")
        except Exception:
            return None

    def _clean_path(file_str):
        """Strip absolute prefix, keep only relative path from repo name onward."""
        if not file_str:
            return file_str
        try:
            p = Path(file_str)
            # Try to make relative to repositories folder
            rel = p.relative_to(BASE_DIR / "repositories")
            # Remove the first component (repo name) to get just the file path
            parts = rel.parts
            return str(Path(*parts[1:])) if len(parts) > 1 else str(rel)
        except Exception:
            # Fallback: just take everything after "repositories\"
            s = str(file_str).replace("\\", "/").replace("\\", "/")
            if "repositories" in s:
                return s.split("repositories")[-1].lstrip("/\\").split("/", 1)[-1]
            return file_str

    # ── Gitleaks ──────────────────────────────────────────────────────────
    def load_gitleaks():
        results = []
        seen = set()
        # Search all possible gitleaks JSON files in repos folder
        repo_dir = BASE_DIR / "repositories"
        if repo_dir.exists():
            for fname in ["gl-files.json", "gl-git.json", "gitleaks-report.json"]:
                for jf in repo_dir.rglob(fname):
                    try:
                        data = _json.loads(jf.read_text(encoding="utf-8", errors="replace").strip() or "[]")
                        items = data if isinstance(data, list) else []
                        for item in items:
                            key = (item.get("RuleID",""), item.get("File",""), str(item.get("StartLine","")))
                            if key not in seen:
                                seen.add(key)
                                results.append({
                                    "rule_id":     item.get("RuleID",""),
                                    "title":       item.get("Description","Secret detected"),
                                    "file":        _clean_path(item.get("File","")),
                                    "line":        item.get("StartLine"),
                                    "description": item.get("Description",""),
                                    "commit":      item.get("Commit",""),
                                    "severity":    "high",
                                })
                    except Exception:
                        pass
        return results

    # ── Semgrep ───────────────────────────────────────────────────────────
    def load_semgrep():
        results = []
        seen = set()
        repo_dir = BASE_DIR / "repositories"
        if not repo_dir.exists():
            return results
        for fname in ["semgrep-secrets.json", "semgrep-python.json", "semgrep-security.json", "semgrep-auto.json", "semgrep-report.json"]:
            for jf in repo_dir.rglob(fname):
                try:
                    data = _json.loads(jf.read_text(encoding="utf-8", errors="replace"))
                    for r in data.get("results", []):
                        key = (r.get("check_id",""), r.get("path",""), str(r.get("start",{}).get("line","")))
                        if key not in seen:
                            seen.add(key)
                            sev_raw = r.get("extra",{}).get("severity","").lower()
                            sev = "critical" if sev_raw in ("error","critical") else "high" if sev_raw=="warning" else "low" if sev_raw=="info" else "medium"
                            results.append({
                                "rule_id": r.get("check_id",""),
                                "file":    _clean_path(r.get("path","")),
                                "line":    r.get("start",{}).get("line"),
                                "message": r.get("extra",{}).get("message",""),
                                "severity": sev,
                            })
                except Exception:
                    pass
        return results

    # ── Bandit ────────────────────────────────────────────────────────────
    def load_bandit():
        results = []
        # First try the stored path directly
        stored = scan.bearer_report_path
        sources = []
        if stored and Path(stored).exists():
            sources.append(Path(stored))
        # Also search repositories folder
        repo_dir = BASE_DIR / "repositories"
        if repo_dir.exists():
            sources.extend(repo_dir.rglob("bandit-report.json"))

        seen = set()
        for jf in sources:
            try:
                data = _json.loads(jf.read_text(encoding="utf-8", errors="replace"))
                for item in data.get("results", []):
                    key = (item.get("test_id",""), item.get("filename",""), str(item.get("line_number","")))
                    if key not in seen:
                        seen.add(key)
                        sev_raw  = item.get("issue_severity","LOW").upper()
                        conf_raw = item.get("issue_confidence","LOW").upper()
                        sev = "critical" if sev_raw=="HIGH" and conf_raw=="HIGH" else "high" if sev_raw=="HIGH" else "medium" if sev_raw=="MEDIUM" else "low"
                        results.append({
                            "rule_id":     item.get("test_id",""),
                            "title":       item.get("test_name",""),
                            "file":        _clean_path(item.get("filename","")),
                            "line":        item.get("line_number"),
                            "description": item.get("issue_text",""),
                            "severity":    sev,
                            "cwe_ids":     str(item.get("issue_cwe",{}).get("id","")),
                            "more_info":   item.get("more_info",""),
                        })
            except Exception:
                pass
        return results

    # ── DAST ──────────────────────────────────────────────────────────────
    def load_dast():
        p = scan.dast_report_path
        if not p:
            return []
        pth = Path(p)
        if not pth.exists():
            # Search in reports folder
            for jf in (BASE_DIR / "reports").rglob("dast-report.json"):
                try:
                    data = _json.loads(jf.read_text(encoding="utf-8", errors="replace"))
                    return data.get("findings", [])
                except Exception:
                    pass
            return []
        try:
            data = _json.loads(pth.read_text(encoding="utf-8", errors="replace"))
            return data.get("findings", [])
        except Exception:
            return []

    return {
        "gitleaks": load_gitleaks(),
        "semgrep":  load_semgrep(),
        "bandit":   load_bandit(),
        "dast":     load_dast(),
    }
