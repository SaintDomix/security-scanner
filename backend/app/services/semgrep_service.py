import subprocess
import json
import shutil
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _find_semgrep():
    for name in ["semgrep", "semgrep.exe"]:
        p = shutil.which(name)
        if p:
            return [p]
    return [sys.executable, "-m", "semgrep"]


def _run_semgrep(cmd_prefix: list, config: str, source: Path, report_path: Path) -> bool:
    """Run semgrep with a specific config, return True on success."""
    if report_path.exists():
        report_path.unlink()
    cmd = cmd_prefix + [
        "scan",
        "--config", config,
        "--json",
        "--output", str(report_path),
        str(source),
        "--no-git-ignore",
        "--timeout", "30",
        "--max-memory", "1024",
        "--disable-version-check",
        "--quiet",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return r.returncode in (0, 1)
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return False


def _load_results(path: Path) -> list:
    if not path or not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return data.get("results", [])
    except Exception:
        return []


def run_semgrep(source: Path) -> dict:
    source = Path(source).resolve()
    cmd = _find_semgrep()

    # Run multiple targeted rulesets and merge — better than "auto" which downloads everything
    configs = [
        ("p/secrets",        source / "semgrep-secrets.json"),
        ("p/python",         source / "semgrep-python.json"),
        ("p/security-audit", source / "semgrep-security.json"),
    ]

    all_results = []
    any_ran = False

    for config, report_path in configs:
        ok = _run_semgrep(cmd, config, source, report_path)
        if ok:
            any_ran = True
            all_results.extend(_load_results(report_path))

    if not any_ran:
        return {
            "findings": [], "count": 0,
            "severity_counts": {"critical":0,"high":0,"medium":0,"low":0},
            "json_path": None,
            "error": "semgrep not found — run: pip install semgrep",
        }

    # Deduplicate by (rule_id, path, line)
    seen = set()
    unique = []
    for r in all_results:
        key = (r.get("check_id",""), r.get("path",""), str(r.get("start",{}).get("line","")))
        if key not in seen:
            seen.add(key)
            unique.append(r)

    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    normalized = []
    for r in unique:
        sev_raw = r.get("extra", {}).get("severity", "").lower()
        if sev_raw in ("error", "critical"):
            sev = "critical"; severity_counts["critical"] += 1
        elif sev_raw == "warning":
            sev = "high";     severity_counts["high"] += 1
        elif sev_raw == "info":
            sev = "low";      severity_counts["low"] += 1
        else:
            sev = "medium";   severity_counts["medium"] += 1

        # Clean up file path
        file_path = r.get("path","")
        try:
            file_path = str(Path(file_path).relative_to(source))
        except Exception:
            pass

        normalized.append({
            "rule_id":  r.get("check_id",""),
            "file":     file_path,
            "line":     r.get("start",{}).get("line"),
            "message":  r.get("extra",{}).get("message",""),
            "severity": sev,
        })

    # Use first existing report as the json_path
    primary = next((str(rp) for _, rp in configs if rp.exists()), None)

    return {
        "findings":        normalized,
        "count":           len(normalized),
        "severity_counts": severity_counts,
        "json_path":       primary,
        "error":           None,
    }
