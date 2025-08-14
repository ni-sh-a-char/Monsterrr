# Monsterrr

Autonomous AI system for GitHub organization management.

## Overview
Monsterrr is a multi-agent, always-on system that discovers, creates, and maintains open-source projects for the `ni_sh_a.char` GitHub organization. It leverages the Groq LLM API for all reasoning and code generation, and automates repository management, issue triage, and project scaffolding.

## Features
- **Idea Generator Agent:** Fetches trending project ideas, summarizes and ranks them with Groq, and stores results. Loads and validates all required `.env` variables before any operation.
- **Creator Agent:** Creates new repos, scaffolds code, commits boilerplate, and opens starter issues. Loads and validates all required `.env` variables before any operation. Fails fast if credentials are missing or invalid.
-- **Maintainer Agent:** Monitors repos, responds to issues, auto-closes stale tickets, suggests fixes with Groq, and now plans and executes exactly 3 meaningful contributions per day (repo creation or feature branch) using Groq LLM. All actions are logged and auditable. Supports dry-run mode for safe testing. On Render, the agent creates and replaces a daily JSON plan in `logs/daily_plan_<date>.json`.
-- **Scheduler:** Runs daily jobs and sends a daily status report email with quantifiable metrics (number of ideas processed, repos created, issues handled, PRs merged/open, etc.).
- **FastAPI API:** Webhooks, manual triggers, and status endpoints.
- **Production-ready:** Robust error handling, retries, logging, and CI/CD. All agents use structured logging and retry logic for Groq and GitHub API calls.

## Installation & Setup
1. Clone the repo and install dependencies:
	```sh
	git clone <your-org>/Monsterrr.git
	cd Monsterrr
	pip install -r requirements.txt
	```
2. Edit `.env` with your keys and SMTP credentials:
	```sh
	# Edit .env with your keys and SMTP credentials
	# All agents require GROQ_API_KEY, GROQ_MODEL, GITHUB_TOKEN, GITHUB_ORG, SMTP_HOST, SMTP_USER, SMTP_PASS, STATUS_REPORT_RECIPIENTS, DRY_RUN, MAX_AUTO_CREATIONS_PER_DAY, and DAILY_ACTIVITY_MODE to be set.
	# Agents will fail fast and log errors if any required variable is missing or invalid.
	```

## Running Locally

### Render Deployment
Monsterrr is ready for deployment on [Render](https://render.com/). The scheduler runs automatically and ensures:
- **Exactly 3 contributions are planned and executed daily** (repo creation or feature branch).
- **A daily JSON plan is created and replaced in `logs/daily_plan_<date>.json`** for audit and review.
- **All actions are logged and daily status reports are sent.**
- **Daily status reports include quantifiable metrics:**
	- Number of ideas processed
	- Number of repositories created
	- Number of issues detected and handled
	- Number of PRs merged and open
	- All actions taken by Monsterrr

> **Caution:**
> Monsterrr is designed for full transparency. If any metric is missing or zero, it will be shown in the daily report. For best results, ensure your organization has active ideas, issues, and PRs to process. All daily activity is quantifiable and auditable.

#### Local Development
Start the API locally:
```sh
uvicorn main:app --reload
```

Start the scheduler:
```sh
python scheduler.py
```

**Daily Planning & Execution:**
Monsterrr will automatically plan and execute exactly 3 contributions per day (repo creation or feature branch) using Groq LLM. All actions are logged to `logs/daily_plan_<date>.json` for audit. To run in dry-run mode (log actions, no changes), set `DRY_RUN=true` in `.env`.

Run agents manually for diagnostics:
```sh
python agents/idea_agent.py
python agents/creator_agent.py
python agents/maintainer_agent.py
```
All agents will log credential validation and fail fast if `.env` is missing required values.

### SMTP Troubleshooting


If emails are not being sent:
- Double-check your `.env` for correct `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, and `SMTP_PASS` (Gmail requires an App Password, not your main password).
- On startup, Monsterrr logs a "SMTP connectivity check" result. If it fails, check the error log for details.
- If using Gmail, ensure "2-Step Verification" is enabled and you generated an App Password for "Mail".
- Some providers (Zoho, Outlook, etc.) may require different ports or security settings.
- If you see a traceback in the logs, use it to diagnose the problem or ask for help.

### Credential Validation & Error Handling
All agents load and validate `.env` before any operation. If any required credential or config is missing or invalid, agents will log a clear error and exit immediately. GitHub and Groq API calls use robust error handling and retry logic. See logs for details on failures and diagnostics.

## Running in Docker
Build and run (dev):
```sh
docker build -t monsterrr:dev --target dev .
docker run --env-file .env -p 8000:8000 monsterrr:dev
```



## Deployment to Render
1. Push code to your GitHub org.
2. Connect Render to the repo.
3. Add all required .env variables in the Render dashboard (see `.env` for reference).
4. Render will run the API service using:
	```sh
	uvicorn main:app --host 0.0.0.0 --port 8000
	```
	and install dependencies with:
	```sh
	pip install -r requirements.txt
	```
5. The scheduler and agents will run automatically in the background.
6. All environment variables are loaded at startup using `python-dotenv`.
7. For production, reload is disabled and all credentials are validated at startup.

**Render Start Command:**
```
uvicorn main:app --host 0.0.0.0 --port 8000
```

## .env Variables
```
# ==== Groq API ====
GROQ_API_KEY=sk-your-groq-key-here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TEMPERATURE=0.2
GROQ_MAX_TOKENS=2048

# ==== GitHub ====
GITHUB_TOKEN=ghp-your-pat-here
GITHUB_ORG=your-org-slug

# ==== Email (SMTP) ====
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password

# ==== Status Reports ====
STATUS_REPORT_RECIPIENTS=you@example.com,teammate@example.com

# ==== Daily Activity Mode ====
DAILY_ACTIVITY_MODE=enabled   # enabled/disabled (default: enabled)
DRY_RUN=false                 # true for dry-run mode (logs only, no actions)
MAX_AUTO_CREATIONS_PER_DAY=3  # Number of contributions per day (default: 3)
```

## Weekly Status Report Example
```
Subject: Monsterrr Weekly Status Report

New repositories created: 2
Issues opened: 5 | Issues closed: 4
Top 3 project ideas:
  - OpenHealth NER (https://github.com/ni_sh_a.char/OpenHealth-NER)
  - DevOps Insights (https://github.com/ni_sh_a.char/DevOps-Insights)
  - PyData Visualizer (https://github.com/ni_sh_a.char/PyData-Visualizer)
PR activity: 3 merged, 1 open
Next week: [Groq-generated plan]
```

## UptimeRobot Setup (Recommended for Render Free Tier)
To keep Monsterrr awake and running on Render's free tier, set up UptimeRobot to ping your `/health` endpoint every 5–10 minutes:

1. Go to [UptimeRobot](https://uptimerobot.com/) and create a free account.
2. Click "Add New Monitor" > Type: HTTP(s).
3. Set the URL to `https://your-monsterrr-url.onrender.com/health`.
4. Set monitoring interval to 5 minutes.
5. Save and enable the monitor.

This will keep your Render service active and Monsterrr running 24/7.

## Testing
Run all tests:
```sh
pytest --cov=monsterrr
```
Lint and format:
```sh
flake8 monsterrr && black monsterrr
```

## Audit Logging
All daily plans and actions are saved to `logs/daily_plan_<date>.json` for full auditability. Set `DRY_RUN=true` to test planning and execution logic without making changes to GitHub.
