import subprocess
import json
import shutil
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _find_bandit():
    """Find bandit — tries direct name, then python -m bandit."""
    for name in ["bandit", "bandit.exe"]:
        p = shutil.which(name)
        if p:
            return [p]
    return [sys.executable, "-m", "bandit"]


def run_bearer(source: Path) -> dict:
    """Run Bandit SAST scanner."""
    source = Path(source).resolve()
    report_path = source / "bandit-report.json"

    cmd = _find_bandit() + [
        "-r", str(source),
        "-f", "json",
        "-o", str(report_path),
        "--quiet",
        "-ll",   # only MEDIUM and above severity
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=180,
                       cwd=str(BASE_DIR))
    except FileNotFoundError:
        return {
            "findings": [], "count": 0,
            "severity_counts": {"critical":0,"high":0,"medium":0,"low":0},
            "json_path": None, "tool": "bandit",
            "error": "bandit not installed — run: pip install bandit",
        }
    except subprocess.TimeoutExpired:
        return {
            "findings": [], "count": 0,
            "severity_counts": {"critical":0,"high":0,"medium":0,"low":0},
            "json_path": None, "tool": "bandit", "error": "bandit timed out",
        }

    findings = []
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    if report_path.exists():
        try:
            data = json.loads(report_path.read_text(encoding="utf-8", errors="replace"))
            for item in data.get("results", []):
                sev_raw  = item.get("issue_severity", "LOW").upper()
                conf_raw = item.get("issue_confidence", "LOW").upper()
                if sev_raw == "HIGH" and conf_raw == "HIGH":
                    sev = "critical"
                elif sev_raw == "HIGH":
                    sev = "high"
                elif sev_raw == "MEDIUM":
                    sev = "medium"
                else:
                    sev = "low"
                severity_counts[sev] += 1
                findings.append({
                    "rule_id":     item.get("test_id", ""),
                    "title":       item.get("test_name", ""),
                    "file":        (lambda f: (str(__import__('pathlib').Path(f).relative_to(source)) if __import__('pathlib').Path(f).is_absolute() else f))(item.get("filename","")),
                    "line":        item.get("line_number"),
                    "description": item.get("issue_text", ""),
                    "severity":    sev,
                    "cwe_ids":     str(item.get("issue_cwe", {}).get("id", "")),
                    "more_info":   item.get("more_info", ""),
                })
        except Exception:
            pass

    return {
        "findings":        findings,
        "count":           len(findings),
        "severity_counts": severity_counts,
        "json_path":       str(report_path) if report_path.exists() else None,
        "tool":            "bandit",
        "error":           None,
    }
