# SecureScanner v2

A full-stack security scanning platform with **SAST**, **Secret Detection**, and **DAST** scanning.

## Stack
- **Backend**: Python · FastAPI · SQLite · JWT auth
- **Frontend**: React · Vite · React Router
- **Scanners**: Gitleaks · Semgrep · Bearer · OWASP ZAP (DAST)

---

## Quick Start (Windows)

### 1. Install Prerequisites

#### Python 3.11+
1. Go to https://www.python.org/downloads/
2. Download Python 3.11 or 3.12 (latest stable)
3. Run installer — **check "Add Python to PATH"**
4. Verify: open CMD and type `python --version`

#### Node.js 20+
1. Go to https://nodejs.org/
2. Download LTS version
3. Run installer (keep all defaults)
4. Verify: `node --version` and `npm --version`

#### Git (needed for repo cloning)
1. Go to https://git-scm.com/download/win
2. Download and install (keep defaults)
3. Verify: `git --version`

---

### 2. Install Security Tools

#### Gitleaks (Secret Scanner)
1. Go to https://github.com/gitleaks/gitleaks/releases/latest
2. Download `gitleaks_X.X.X_windows_x64.zip`
3. Extract `gitleaks.exe`
4. Move it to `C:\Windows\System32\` (or any folder in your PATH)
5. Verify: `gitleaks version`

#### Semgrep (SAST)
```
pip install semgrep
```
Verify: `semgrep --version`

#### Bearer (SAST + Privacy)
1. Go to https://github.com/Bearer/bearer/releases/latest
2. Download `bearer_X.X.X_windows_amd64.zip`
3. Extract `bearer.exe`
4. Move it to `C:\Windows\System32\` or add folder to PATH
5. Verify: `bearer version`

**Alternative — Bearer via npm (easier on Windows):**
```
npm install -g @bearer/cli
```

#### OWASP ZAP (DAST — optional but recommended)
1. Go to https://www.zaproxy.org/download/
2. Download "Windows Installer"
3. Install with defaults
4. ZAP is auto-detected if `zap.sh` or `zap.bat` is in PATH
5. Without ZAP, the DAST scan uses a lightweight HTTP probe (still useful)

---

### 3. Setup the App

Double-click `setup.bat` — it will:
- Create Python virtual environment
- Install all Python packages
- Install all npm packages
- Create the `.env` config file

---

### 4. Configure Environment

Open `backend\.env` in Notepad and set:

```env
# REQUIRED — change this to a random string (32+ chars)
SECRET_KEY=replace-this-with-a-long-random-secret-key-here

# OPTIONAL — add your GitHub token for higher API rate limits
# Get one at: https://github.com/settings/tokens
# Needed to scan private repos
GITHUB_TOKEN=ghp_your_token_here

# Default settings — leave as-is
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite:///./securescanner.db
FRONTEND_URL=http://localhost:5173
```

**How to generate a SECRET_KEY:**
- Open CMD and run: `python -c "import secrets; print(secrets.token_hex(32))"`
- Copy the output into `.env`

---

### 5. Run the App

Double-click `start.bat`

This opens two terminal windows:
- **Backend** at http://localhost:8000
- **Frontend** at http://localhost:5173

The browser opens automatically at http://localhost:5173

---

## Running Manually (alternative)

**Terminal 1 — Backend:**
```bat
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload
```

**Terminal 2 — Frontend:**
```bat
cd frontend
npm run dev
```

---

## API Documentation

FastAPI auto-generates interactive docs:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Features

### Authentication
- Register / Login with JWT Bearer tokens
- Protected routes (private pages require login)
- Session persisted in localStorage

### Subscription Tiers
| Feature | Free | Pro | Enterprise |
|---------|------|-----|------------|
| Scans/day | 3 | 50 | Unlimited |
| SAST (Semgrep) | ✓ | ✓ | ✓ |
| Secrets (Gitleaks) | ✓ | ✓ | ✓ |
| Bearer SAST | ✓ | ✓ | ✓ |
| DAST scanning | ✗ | ✓ | ✓ |
| GitHub validation | ✓ | ✓ | ✓ |

### Scan Types
- **GitHub URL** — clone and scan a public (or private with token) repo
- **ZIP Upload** — upload your project as a .zip file
- **DAST** — scan a live URL for HTTP security issues (Pro+)

### Scan Modes
- **Full** — Gitleaks + Semgrep + Bearer (+ DAST if URL provided)
- **SAST Only** — Semgrep + Bearer
- **Secrets Only** — Gitleaks
- **DAST Only** — Live HTTP probe

### Reports
- PDF report generated for every scan
- Severity breakdown: Critical / High / Medium / Low
- File paths and line numbers for each finding
- Remediation guidance

---

## Project Structure

```
securescanner/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + CORS
│   │   ├── models/
│   │   │   ├── models.py        # SQLAlchemy ORM models
│   │   │   └── database.py      # DB session
│   │   ├── schemas/
│   │   │   └── schemas.py       # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── auth.py          # POST /api/auth/register|login
│   │   │   ├── users.py         # GET /api/users/me, POST upgrade
│   │   │   └── scans.py         # POST /api/scans/github|upload|dast, GET list/detail
│   │   ├── services/
│   │   │   ├── github_service.py  # GitHub API validation
│   │   │   ├── gitleaks_service.py
│   │   │   ├── semgrep_service.py
│   │   │   ├── bearer_service.py
│   │   │   ├── dast_service.py    # ZAP + HTTP probe
│   │   │   └── pdf_service.py     # ReportLab PDF generation
│   │   └── utils/
│   │       ├── auth.py            # JWT + bcrypt
│   │       └── limits.py          # Daily scan quota
│   ├── reports/                   # Generated PDFs stored here
│   ├── repositories/              # Cloned repos (auto-cleaned)
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── Register.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── SastScan.jsx       # GitHub URL + ZIP upload scan
│   │   │   ├── DastScan.jsx       # Live DAST scan
│   │   │   ├── ScanDetail.jsx     # Real-time polling + results
│   │   │   ├── History.jsx        # Search + filter + pagination
│   │   │   ├── Pricing.jsx        # Tier upgrade
│   │   │   └── Settings.jsx
│   │   ├── context/AuthContext.jsx
│   │   ├── utils/api.js
│   │   ├── components/layout/Layout.jsx
│   │   ├── App.jsx                # Routes + private/public guards
│   │   └── index.css              # Design system CSS vars
│   └── package.json
├── setup.bat     # Windows one-click setup
├── start.bat     # Windows one-click start
├── start.sh      # Linux/Mac start
└── README.md
```

---
