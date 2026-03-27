import subprocess
import json
import requests
import re
from pathlib import Path
from datetime import datetime


def _zap_available() -> bool:
    try:
        r = subprocess.run(["zap.sh", "-version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


def _http_probe(target_url: str) -> list:
    """Lightweight DAST probe when ZAP is not available."""
    findings = []
    headers_to_check = [
        ("X-Content-Type-Options", "nosniff", "Missing X-Content-Type-Options header", "medium"),
        ("X-Frame-Options", None, "Missing X-Frame-Options header (clickjacking risk)", "medium"),
        ("Strict-Transport-Security", None, "Missing HSTS header", "high"),
        ("Content-Security-Policy", None, "Missing Content-Security-Policy header", "high"),
        ("X-XSS-Protection", None, "Missing X-XSS-Protection header", "low"),
        ("Referrer-Policy", None, "Missing Referrer-Policy header", "low"),
        ("Permissions-Policy", None, "Missing Permissions-Policy header", "low"),
    ]
    try:
        resp = requests.get(target_url, timeout=10, allow_redirects=True, verify=False)
        resp_headers = {k.lower(): v for k, v in resp.headers.items()}

        for header, expected_value, message, severity in headers_to_check:
            if header.lower() not in resp_headers:
                findings.append({
                    "type": "missing_header",
                    "title": message,
                    "description": f"The HTTP response is missing the security header: {header}",
                    "severity": severity,
                    "evidence": f"Header '{header}' not found in response",
                    "solution": f"Add '{header}' header to all HTTP responses",
                })
            elif expected_value and resp_headers[header.lower()] != expected_value:
                findings.append({
                    "type": "insecure_header",
                    "title": f"Incorrect value for {header}",
                    "description": f"Expected '{expected_value}', got '{resp_headers[header.lower()]}'",
                    "severity": "low",
                    "evidence": f"{header}: {resp_headers[header.lower()]}",
                    "solution": f"Set {header} to '{expected_value}'",
                })

        # Check cookies
        for cookie in resp.cookies:
            issues = []
            if not cookie.secure:
                issues.append("missing Secure flag")
            if not cookie.has_nonstandard_attr("HttpOnly"):
                issues.append("missing HttpOnly flag")
            if not cookie.has_nonstandard_attr("SameSite"):
                issues.append("missing SameSite attribute")
            if issues:
                findings.append({
                    "type": "insecure_cookie",
                    "title": f"Insecure cookie: {cookie.name}",
                    "description": f"Cookie has security issues: {', '.join(issues)}",
                    "severity": "medium",
                    "evidence": f"Cookie name: {cookie.name}",
                    "solution": "Set Secure, HttpOnly, and SameSite=Strict on cookies",
                })

        # Check for server info disclosure
        server = resp_headers.get("server", "")
        x_powered = resp_headers.get("x-powered-by", "")
        if server and any(v in server.lower() for v in ["apache", "nginx", "iis", "tomcat"]):
            findings.append({
                "type": "information_disclosure",
                "title": "Server version disclosure",
                "description": f"Server header reveals technology: {server}",
                "severity": "low",
                "evidence": f"Server: {server}",
                "solution": "Remove or obfuscate the Server header",
            })
        if x_powered:
            findings.append({
                "type": "information_disclosure",
                "title": "X-Powered-By disclosure",
                "description": f"X-Powered-By header reveals backend: {x_powered}",
                "severity": "low",
                "evidence": f"X-Powered-By: {x_powered}",
                "solution": "Remove the X-Powered-By header",
            })

        # Check HTTPS
        if target_url.startswith("http://"):
            findings.append({
                "type": "insecure_transport",
                "title": "Site accessible over HTTP",
                "description": "The site is accessible over unencrypted HTTP",
                "severity": "high",
                "evidence": f"Target URL uses http://",
                "solution": "Enforce HTTPS and redirect all HTTP traffic to HTTPS",
            })

        # Check for common sensitive paths
        sensitive_paths = [
            ("/.env", "critical", "Exposed .env file"),
            ("/.git/config", "critical", "Exposed Git config"),
            ("/admin", "medium", "Admin panel exposed"),
            ("/phpinfo.php", "medium", "phpinfo exposed"),
            ("/wp-admin", "medium", "WordPress admin exposed"),
            ("/api/swagger.json", "low", "API docs exposed"),
            ("/api/openapi.json", "low", "OpenAPI spec exposed"),
            ("/robots.txt", "info", "robots.txt found (check for sensitive paths)"),
        ]
        base = target_url.rstrip("/")
        for path, severity, title in sensitive_paths:
            if severity == "info":
                continue
            try:
                check = requests.get(base + path, timeout=5, verify=False)
                if check.status_code == 200 and len(check.content) > 10:
                    findings.append({
                        "type": "exposed_resource",
                        "title": title,
                        "description": f"Sensitive resource at {path} returned HTTP 200",
                        "severity": severity,
                        "evidence": f"GET {base + path} → 200 OK ({len(check.content)} bytes)",
                        "solution": f"Restrict access to {path} or remove it from the server",
                    })
            except Exception:
                pass

    except requests.RequestException as e:
        findings.append({
            "type": "probe_error",
            "title": "Could not reach target",
            "description": str(e),
            "severity": "info",
            "evidence": target_url,
            "solution": "Ensure the target URL is reachable and the protocol is correct",
        })

    return findings


def run_dast(target_url: str, report_dir: Path) -> dict:
    """Run DAST scan against a live URL."""
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "dast-report.json"

    if _zap_available():
        # Full ZAP spider + active scan
        try:
            zap_report = report_dir / "zap-report.json"
            cmd = [
                "zap.sh", "-cmd",
                "-quickurl", target_url,
                "-quickout", str(zap_report),
                "-quickprogress",
            ]
            subprocess.run(cmd, capture_output=True, timeout=300)
            if zap_report.exists():
                with open(zap_report) as f:
                    zap_data = json.load(f)
                # Parse ZAP output
                findings = _parse_zap_output(zap_data)
                with open(report_path, "w") as f:
                    json.dump({"tool": "zap", "findings": findings, "target": target_url}, f, indent=2)
        except Exception:
            findings = _http_probe(target_url)
            with open(report_path, "w") as f:
                json.dump({"tool": "http_probe", "findings": findings, "target": target_url}, f, indent=2)
    else:
        # Fallback to HTTP probe
        findings = _http_probe(target_url)
        with open(report_path, "w") as f:
            json.dump({
                "tool": "http_probe",
                "findings": findings,
                "target": target_url,
                "scanned_at": datetime.utcnow().isoformat(),
            }, f, indent=2)

    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        s = f.get("severity", "low")
        if s in severity_counts:
            severity_counts[s] += 1

    return {
        "findings": findings,
        "count": len(findings),
        "severity_counts": severity_counts,
        "json_path": str(report_path),
        "error": None,
    }


def _parse_zap_output(zap_data: dict) -> list:
    findings = []
    for site in zap_data.get("site", []):
        for alert in site.get("alerts", []):
            sev_map = {"0": "info", "1": "low", "2": "medium", "3": "high", "4": "critical"}
            findings.append({
                "type": "zap_alert",
                "title": alert.get("name", ""),
                "description": alert.get("desc", ""),
                "severity": sev_map.get(str(alert.get("riskcode", "1")), "low"),
                "evidence": alert.get("evidence", ""),
                "solution": alert.get("solution", ""),
                "cwe": alert.get("cweid", ""),
            })
    return findings
