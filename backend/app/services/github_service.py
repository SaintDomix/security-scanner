import os
import re
import requests
from typing import Optional, Dict

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


def _headers():
    h = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def parse_github_url(url: str) -> Optional[tuple]:
    url = url.strip().rstrip("/")
    m = re.search(r"github\.com[:/]([^/]+)/([^/.\s]+?)(?:\.git)?$", url)
    if m:
        return m.group(1), m.group(2)
    return None


def validate_github_repo(url: str) -> Dict:
    """
    Validate a GitHub repo URL via the API.
    If the API is unreachable (timeout, network block), we skip validation
    and return valid=True so the scan can still proceed via git clone.
    """
    parsed = parse_github_url(url)
    if not parsed:
        return {"valid": False, "error": "Not a valid GitHub URL format"}

    owner, repo = parsed

    try:
        r = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=_headers(),
            timeout=8,      # short timeout — don't block the scan
        )
        if r.status_code == 404:
            return {"valid": False, "error": "Repository not found or is private"}
        if r.status_code == 403:
            return {"valid": False, "error": "GitHub API rate limit hit — set GITHUB_TOKEN in .env"}
        if r.status_code != 200:
            # Unknown error from GitHub — still allow the scan to try
            return {
                "valid": True,
                "stars": None, "language": None,
                "description": f"GitHub API returned {r.status_code} — proceeding anyway",
            }

        data = r.json()
        return {
            "valid":          True,
            "stars":          data.get("stargazers_count", 0),
            "language":       data.get("language"),
            "description":    data.get("description"),
            "default_branch": data.get("default_branch", "main"),
            "clone_url":      data.get("clone_url"),
            "size_kb":        data.get("size", 0),
        }

    except requests.exceptions.Timeout:
        # GitHub API timed out (network block, VPN, firewall)
        # Don't fail the scan — let git clone try directly
        return {
            "valid":       True,
            "stars":       None,
            "language":    None,
            "description": "GitHub API unreachable — scan will proceed via git clone",
        }

    except requests.exceptions.ConnectionError:
        # No internet or GitHub blocked
        return {
            "valid":       True,
            "stars":       None,
            "language":    None,
            "description": "GitHub API unreachable — scan will proceed via git clone",
        }

    except Exception as e:
        # Any other error — still allow scan to proceed
        return {
            "valid":       True,
            "stars":       None,
            "language":    None,
            "description": f"GitHub API check skipped: {str(e)[:100]}",
        }