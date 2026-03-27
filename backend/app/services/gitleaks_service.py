import subprocess
import shutil
import json
import stat
import os
import sys
import tempfile
from pathlib import Path
from git import Repo

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPO_DIR = BASE_DIR / "repositories"
REPO_DIR.mkdir(exist_ok=True)

# Minimal gitleaks config that scans ALL files with common secret patterns
GITLEAKS_CONFIG = r"""
[extend]
useDefault = true

[[rules]]
id = "generic-api-key"
description = "Generic API Key"
regex = '''(?i)(api[_-]?key|apikey|secret[_-]?key|access[_-]?key)\s*[=:]\s*['"]?([a-zA-Z0-9_\-]{16,})['"]?'''
severity = "HIGH"

[[rules]]
id = "generic-password"
description = "Hardcoded Password"
regex = '''(?i)(password|passwd|pwd)\s*[=:]\s*['"]([^'"]{4,})['"]'''
severity = "HIGH"

[[rules]]
id = "generic-token"
description = "Hardcoded Token"
regex = '''(?i)(token|auth[_-]?token|bearer)\s*[=:]\s*['"]([a-zA-Z0-9_\-\.]{16,})['"]'''
severity = "HIGH"

[[rules]]
id = "aws-access-key"
description = "AWS Access Key"
regex = '''AKIA[0-9A-Z]{16}'''
severity = "CRITICAL"

[[rules]]
id = "private-key"
description = "Private Key"
regex = '''-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY'''
severity = "CRITICAL"

[[rules]]
id = "slack-token"
description = "Slack Token"
regex = '''xox[baprs]-([0-9a-zA-Z]{10,48})?'''
severity = "HIGH"

[[rules]]
id = "github-token"
description = "GitHub Token"
regex = '''ghp_[0-9a-zA-Z]{36}|github_pat_[0-9a-zA-Z_]{82}'''
severity = "HIGH"

[[rules]]
id = "hardcoded-string-assignment"
description = "Possible hardcoded secret in assignment"
regex = '''(?i)(secret|key|password|token|credential)\s*=\s*['"][^'"]{6,}['"]'''
severity = "MEDIUM"
"""


def _force_remove(path: Path):
    def _on_error(func, fpath, exc_info):
        try:
            os.chmod(fpath, stat.S_IWRITE)
            func(fpath)
        except Exception:
            pass
    shutil.rmtree(str(path), onerror=_on_error)


def clone_repo(url: str) -> Path:
    name = url.strip().rstrip("/").split("/")[-1].replace(".git", "")
    repo_path = REPO_DIR / name
    if repo_path.exists():
        _force_remove(repo_path)
    try:
        Repo.clone_from(url, repo_path, depth=50)
    except Exception as e:
        err = str(e)
        if any(w in err.lower() for w in ["timed out", "connection", "unable to access"]):
            raise Exception(f"Cannot reach GitHub — check your internet/VPN. Error: {err[:200]}")
        raise
    return repo_path


def _find_gitleaks() -> str:
    """Find gitleaks.exe — checks current dir, PATH, and common locations."""
    # Check right next to this project first (most common on Windows)
    local = BASE_DIR / "gitleaks.exe"
    if local.exists():
        return str(local)

    # Check PATH
    for name in ["gitleaks", "gitleaks.exe"]:
        p = shutil.which(name)
        if p:
            return p

    # Common Windows install locations
    for c in [
        r"C:\Windows\System32\gitleaks.exe",
        r"C:\Program Files\gitleaks\gitleaks.exe",
        r"C:\tools\gitleaks.exe",
        str(Path.home() / "gitleaks.exe"),
        str(Path.home() / "Downloads" / "gitleaks.exe"),
    ]:
        if Path(c).exists():
            return c

    return str(BASE_DIR / "gitleaks.exe")  # return full path even if not found yet


def _run_gitleaks_cmd(exe: str, source: Path, report_path: Path, no_git: bool, config_path: str = None) -> bool:
    if report_path.exists():
        report_path.unlink()
    cmd = [
        exe, "detect",
        "--source", str(source),
        "--report-path", str(report_path),
        "--report-format", "json",
        "--exit-code", "1",
        "--verbose",
    ]
    if no_git:
        cmd.append("--no-git")
    if config_path:
        cmd += ["--config", config_path]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return r.returncode in (0, 1)
    except FileNotFoundError:
        return False
    except (subprocess.TimeoutExpired, Exception):
        return False


def _load_findings(path: Path) -> list:
    if not path or not path.exists():
        return []
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").strip()
        if not raw:
            return []
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _normalize(findings: list, source: Path) -> list:
    seen = set()
    result = []
    for leak in findings:
        key = (leak.get("RuleID",""), leak.get("File",""), str(leak.get("StartLine","")))
        if key in seen:
            continue
        seen.add(key)
        # Clean up the file path — remove the absolute prefix
        file_path = leak.get("File","")
        try:
            file_path = str(Path(file_path).relative_to(source))
        except Exception:
            pass
        result.append({
            "rule_id":     leak.get("RuleID",""),
            "title":       leak.get("Description", "Secret detected"),
            "file":        file_path,
            "line":        leak.get("StartLine"),
            "description": leak.get("Description",""),
            "commit":      leak.get("Commit",""),
            "author":      leak.get("Author",""),
            "severity":    "high",
        })
    return result


def run_gitleaks(source: Path) -> dict:
    source = Path(source).resolve()
    exe = _find_gitleaks()

    report_file = source / "gl-files.json"
    report_git  = source / "gl-git.json"

    # Write custom config to a temp file so gitleaks finds all secret patterns
    config_file = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False, encoding="utf-8") as tf:
            tf.write(GITLEAKS_CONFIG)
            config_file = tf.name
    except Exception:
        config_file = None

    # Scan file contents (--no-git) — finds secrets in current files
    ok = _run_gitleaks_cmd(exe, source, report_file, no_git=True, config_path=config_file)

    if not ok:
        # Cleanup
        if config_file:
            try: os.unlink(config_file)
            except: pass
        return {
            "findings": [], "count": 0, "json_path": None,
            "error": "gitleaks not found or failed — check PATH",
        }

    # Also scan git history if real repo
    if (source / ".git").exists():
        _run_gitleaks_cmd(exe, source, report_git, no_git=False, config_path=config_file)

    if config_file:
        try: os.unlink(config_file)
        except: pass

    all_raw  = _load_findings(report_file) + _load_findings(report_git)
    findings = _normalize(all_raw, source)

    primary = report_file if report_file.exists() else report_git

    return {
        "findings":  findings,
        "count":     len(findings),
        "json_path": str(primary) if primary.exists() else None,
        "error":     None,
    }


def run_gitleaks_on_path(path: Path) -> dict:
    return run_gitleaks(path)
