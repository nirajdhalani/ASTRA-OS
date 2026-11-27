# ASTRA OS

**ASTRA OS v0.1.1** is a web-first astrology chart workspace with a deterministic astronomical calculation layer and configurable Vedic, Western, KP and Jaimini conventions. It includes account registration, saved birth profiles, chart analysis, life-domain evidence reports and multilingual UI (English, Hindi and Gujarati).

See [`backend/README.md`](backend/README.md) for the full scope, limitations, clean-machine setup, API routes, tests, ephemeris setup and commercial deployment checklist.

## Quick start

```bash
cd backend
python -m venv .venv
# Activate the venv, then:
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env          # PowerShell: Copy-Item .env.example .env
python scripts/download_ephemeris.py
python -m pytest -q
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. First ephemeris download requires outbound network access.
